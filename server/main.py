import os
import json
import socket
import sqlite3
import sys
import threading
import time
import uvicorn
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import flwr as fl

from server.strategy import (
    telemetry_data, PaillierFedAvg, _get_metrics_db_path, _build_default_clients
)

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    # Windows consoles often default to a legacy codepage that can't render
    # the em-dashes used in this project's log output.
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

app = FastAPI(title="Cross-School Federated Learning — API")

# CORS: allow React dev server (port 3000) and production build
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class ConfigModel(BaseModel):
    use_dp: str
    use_paillier: str
    local_epochs: int
    lr: float
    total_rounds: int
    num_nodes: int = 3
    paillier_key_bits: int = 2048
    noise_multiplier: float = 1.1
    max_grad_norm: float = 1.0



@app.get("/api/telemetry")
def get_telemetry():
    # Keep startup clean: do not rehydrate old rounds from logs/fl_metrics.db.
    # Historical metrics remain available through /api/metrics, but telemetry
    # starts empty until a new simulation run populates it.

    return JSONResponse(content=telemetry_data)


@app.post("/api/config")
def update_config(config: ConfigModel):
    if telemetry_data["simulation_running"]:
        raise HTTPException(status_code=400, detail="Cannot update config while simulation is running")

    num_nodes = max(3, min(5, config.num_nodes))
    from server.strategy import SCHOOL_NAMES_ALL
    schools = SCHOOL_NAMES_ALL[:num_nodes]

    # Rebuild clients dict — always reset status to Idle on config save
    existing = telemetry_data["clients"]
    new_clients = {}
    for s in schools:
        prev = existing.get(s, {})
        new_clients[s] = {
            "status": "Idle",
            "last_active": prev.get("last_active", "-"),
            "last_latency": prev.get("last_latency", 0.0),
            "last_epsilon": prev.get("last_epsilon", 0.0),
        }
    telemetry_data["clients"] = new_clients

    telemetry_data["config"]["use_dp"]            = config.use_dp
    telemetry_data["config"]["use_paillier"]      = config.use_paillier
    telemetry_data["config"]["local_epochs"]      = config.local_epochs
    telemetry_data["config"]["lr"]                = config.lr
    telemetry_data["config"]["total_rounds"]      = config.total_rounds
    telemetry_data["config"]["num_nodes"]         = num_nodes
    telemetry_data["config"]["paillier_key_bits"] = config.paillier_key_bits
    telemetry_data["config"]["noise_multiplier"]  = config.noise_multiplier
    telemetry_data["config"]["max_grad_norm"]     = config.max_grad_norm

    return {"status": "success", "config": telemetry_data["config"]}


# ---------------------------------------------------------------------------
# Client status
# ---------------------------------------------------------------------------

@app.get("/api/client/{school_name}/status")
def get_client_status(school_name: str):
    if school_name not in telemetry_data["clients"]:
        raise HTTPException(status_code=404, detail="School node not found")
    return {"status": telemetry_data["clients"][school_name]["status"]}


@app.post("/api/client/{school_name}/toggle")
def toggle_client_status(school_name: str):
    if school_name not in telemetry_data["clients"]:
        raise HTTPException(status_code=404, detail="School node not found")
    current = telemetry_data["clients"][school_name]["status"]
    new_status = "Idle" if current == "Offline" else "Offline"
    telemetry_data["clients"][school_name]["status"] = new_status
    return {"status": "success", "client": school_name, "new_status": new_status}


# ---------------------------------------------------------------------------
# Live training progress (intermediate epoch accuracy)
# ---------------------------------------------------------------------------

@app.post("/api/progress")
def post_training_progress(payload: dict):
    accuracy = payload.get("accuracy")
    school = payload.get("school")
    if accuracy is not None:
        if "_live_per_school" not in telemetry_data:
            telemetry_data["_live_per_school"] = {}
        key = school if school else "_unknown"
        telemetry_data["_live_per_school"][key] = float(accuracy)
        vals = list(telemetry_data["_live_per_school"].values())
        telemetry_data["live_accuracy"] = float(sum(vals) / len(vals))
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Pending updates (node dropout tolerance — Proposal D1, Component 5)
# ---------------------------------------------------------------------------

def _get_pending_db_path():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.makedirs(os.path.join(root, "logs"), exist_ok=True)
    return os.path.join(root, "logs", "pending_updates.db")


def _init_pending_db():
    conn = sqlite3.connect(_get_pending_db_path())
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pending_updates (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            school_name TEXT    NOT NULL,
            round_id    INTEGER NOT NULL,
            update_json TEXT    NOT NULL,
            queued_at   TEXT    NOT NULL,
            transmitted INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()


_init_pending_db()


@app.get("/api/pending-updates")
def get_pending_updates():
    conn = sqlite3.connect(_get_pending_db_path())
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT school_name, round_id, queued_at, transmitted FROM pending_updates ORDER BY id DESC LIMIT 50"
    ).fetchall()
    conn.close()
    return {"pending": [dict(r) for r in rows]}


@app.post("/api/client/{school_name}/queue-update")
def queue_client_update(school_name: str, payload: dict):
    """Called by a client that was offline and now wants to submit a queued update."""
    if school_name not in telemetry_data["clients"]:
        raise HTTPException(status_code=404, detail="School node not found")
    conn = sqlite3.connect(_get_pending_db_path())
    conn.execute(
        "INSERT INTO pending_updates (school_name, round_id, update_json, queued_at) VALUES (?, ?, ?, ?)",
        (school_name, payload.get("round_id", 0), json.dumps(payload), time.strftime("%Y-%m-%dT%H:%M:%S"))
    )
    conn.commit()
    conn.close()
    return {"status": "queued", "school_name": school_name}


# ---------------------------------------------------------------------------
# fl_metrics read endpoint (for React dashboard charts)
# ---------------------------------------------------------------------------

@app.get("/api/baseline")
def get_baseline_metrics():
    """Serve centralised baseline metrics for dashboard comparison (Proposal Obj.1)."""
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "results", "baseline_metrics.json"
    )
    if not os.path.exists(path):
        return JSONResponse(status_code=404, content={"detail": "Run python scripts/train_baseline.py first"})
    with open(path, "r") as f:
        return JSONResponse(content=json.load(f))


@app.get("/api/privacy-sweep")
def get_privacy_sweep():
    """Serve the privacy-accuracy sweep results for the React dashboard scatter plot."""
    results_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "results", "privacy_accuracy_tradeoff.json"
    )
    if not os.path.exists(results_path):
        return JSONResponse(status_code=404, content={"detail": "Run privacy_accuracy_sweep.py first"})
    with open(results_path, "r") as f:
        return JSONResponse(content=json.load(f))


@app.get("/api/metrics")
def get_fl_metrics():
    db_path = _get_metrics_db_path()
    if not os.path.exists(db_path):
        return {"metrics": []}
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM fl_metrics ORDER BY round_id, node_id"
    ).fetchall()
    conn.close()
    return {"metrics": [dict(r) for r in rows]}


# ---------------------------------------------------------------------------
# Simulation runner
# ---------------------------------------------------------------------------

def _port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def run_fl_simulation():
    if _port_in_use(8088):
        print("[Simulation] ERROR: Port 8088 is already in use. Previous run may not have exited cleanly.")
        print("[Simulation] Wait a few seconds and try again, or restart the server process.")
        telemetry_data["simulation_running"] = False
        return

    telemetry_data["simulation_running"] = True
    telemetry_data["_stop_requested"] = False
    telemetry_data["rounds"] = []
    telemetry_data["_db_rounds_loaded"] = False
    telemetry_data["live_accuracy"] = None
    telemetry_data["last_round_metrics"] = {}
    telemetry_data["_live_per_school"] = {}
    telemetry_data["source"] = "dashboard"

    # Reset client stats and transient statuses for a clean slate
    for school in telemetry_data["clients"]:
        status = telemetry_data["clients"][school]["status"]
        telemetry_data["clients"][school]["last_latency"] = 0.0
        telemetry_data["clients"][school]["last_epsilon"] = 0.0
        telemetry_data["clients"][school]["last_active"] = "-"
        if status not in ("Offline", "Idle"):
            telemetry_data["clients"][school]["status"] = "Idle"

    school_names = list(telemetry_data["clients"].keys())
    key_bits = int(telemetry_data["config"].get("paillier_key_bits", 2048))
    print(f"[Simulation] Starting Flower server on port 8088 for nodes: {school_names}")
    strategy = PaillierFedAvg(school_names=school_names, key_length=key_bits)

    server_error = {"occurred": False}

    def start_server_thread():
        try:
            fl.server.start_server(
                # 0.0.0.0, not 127.0.0.1: in docker-compose the school clients run in
                # separate containers and reach this one over the bridge network at
                # server:8088 — a loopback-only bind would refuse those connections.
                server_address="0.0.0.0:8088",
                config=fl.server.ServerConfig(
                    num_rounds=int(telemetry_data["config"]["total_rounds"])
                ),
                strategy=strategy,
            )
        except Exception as e:
            print("[Simulation Server Error]", e)
            server_error["occurred"] = True

    server_thread = threading.Thread(target=start_server_thread, daemon=True)
    server_thread.start()

    # Poll until server port is accepting connections (max 10s)
    for _ in range(20):
        try:
            with socket.create_connection(("127.0.0.1", 8088), timeout=0.5):
                break
        except OSError:
            time.sleep(0.5)

    if server_error["occurred"]:
        telemetry_data["simulation_running"] = False
        return

    print("[Simulation] Launching clients...")
    client_threads = []

    def start_client_thread(school_name):
        try:
            from client.client import StudentFLClient
            client = StudentFLClient(school_name)
            fl.client.start_numpy_client(server_address="127.0.0.1:8088", client=client)
        except Exception as e:
            print(f"[Simulation Client Error — {school_name}]", e)
            if telemetry_data["clients"].get(school_name, {}).get("status") != "Offline":
                telemetry_data["clients"][school_name]["status"] = "Failed"

    for school in school_names:
        if telemetry_data["clients"][school]["status"] != "Offline":
            t = threading.Thread(target=start_client_thread, args=(school,), daemon=True)
            t.start()
            client_threads.append(t)

    server_thread.join()

    # Fix: only reset transient statuses (Active/Failed) back to Idle.
    # Do NOT set Idle clients to Offline — that would block the next simulation run.
    for school in telemetry_data["clients"]:
        if telemetry_data["clients"][school]["status"] not in ("Offline", "Idle"):
            telemetry_data["clients"][school]["status"] = "Idle"

    telemetry_data["simulation_running"] = False
    telemetry_data["source"] = None
    print("[Simulation] Ended.")


# ---------------------------------------------------------------------------
# CLI simulation bridge — lets `scripts/run_fl_simulation.py` (a separate
# process from this FastAPI server) report live progress into telemetry_data
# so the dashboard reflects CLI-launched runs exactly like dashboard-launched
# ones, and so the dashboard's Stop button can halt a CLI run too.
# ---------------------------------------------------------------------------

@app.post("/api/telemetry/cli-start")
def cli_start(payload: dict):
    if telemetry_data["simulation_running"]:
        raise HTTPException(status_code=400, detail="A simulation is already tracked as running")
    school_names = payload.get("school_names") or list(telemetry_data["clients"].keys())
    config = payload.get("config") or {}

    telemetry_data["clients"] = _build_default_clients(school_names)
    telemetry_data["config"].update(config)
    telemetry_data["rounds"] = []
    telemetry_data["simulation_running"] = True
    telemetry_data["_stop_requested"] = False
    telemetry_data["live_accuracy"] = None
    telemetry_data["last_round_metrics"] = {}
    telemetry_data["_live_per_school"] = {}
    telemetry_data["source"] = "cli"
    return {"status": "ok"}


@app.post("/api/telemetry/cli-round")
def cli_round(payload: dict):
    round_metrics = payload.get("round_metrics")
    clients = payload.get("clients") or {}
    if round_metrics:
        telemetry_data["rounds"].append(round_metrics)
        telemetry_data["live_accuracy"] = None
        telemetry_data["_live_per_school"] = {}
    for name, info in clients.items():
        if name in telemetry_data["clients"]:
            telemetry_data["clients"][name].update(info)
    return {"status": "ok"}


@app.post("/api/telemetry/cli-end")
def cli_end():
    telemetry_data["simulation_running"] = False
    telemetry_data["source"] = None
    return {"status": "ok"}


@app.get("/api/telemetry/cli-stop-check")
def cli_stop_check():
    return {"stop_requested": bool(telemetry_data.get("_stop_requested", False))}


@app.post("/api/stop")
def stop_simulation():
    if not telemetry_data["simulation_running"]:
        raise HTTPException(status_code=400, detail="No simulation is running")
    telemetry_data["_stop_requested"] = True
    return {"status": "stopping"}


@app.post("/api/start")
def start_simulation(background_tasks: BackgroundTasks):
    if telemetry_data["simulation_running"]:
        raise HTTPException(status_code=400, detail="Simulation is already running")
    if _port_in_use(8088):
        raise HTTPException(status_code=503, detail="Port 8088 in use from a previous run — wait a few seconds then retry")
    background_tasks.add_task(run_fl_simulation)
    return {"status": "started"}


if __name__ == "__main__":
    uvicorn.run("server.main:app", host="0.0.0.0", port=8000, reload=False)
