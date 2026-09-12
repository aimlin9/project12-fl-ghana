"""
Standalone FL simulation runner (Proposal D1, Step 5).

Usage:
    python scripts/run_fl_simulation.py --rounds 50 --nodes 3 --dp True --paillier True
    python scripts/run_fl_simulation.py --rounds 10 --nodes 5 --dp False --paillier True --lr 0.005

This script runs a complete Flower FL simulation WITHOUT requiring the FastAPI server.
Results are saved to logs/fl_metrics.db and printed to console.
"""

import argparse
import json
import os
import sys
import threading
import time
import socket
import urllib.request
import urllib.error

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    # Windows consoles often default to a legacy codepage that can't render
    # the em-dashes used in this script's log output.
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch
import flwr as fl
from server.strategy import PaillierFedAvg, SCHOOL_NAMES_ALL, telemetry_data, _build_default_clients

DASHBOARD_URL = "http://127.0.0.1:8000"


def wait_for_port(host, port, max_wait=10.0):
    """Poll until the given host:port accepts connections or timeout."""
    deadline = time.time() + max_wait
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.5)
    return False


def _post_json(path, payload, timeout=1.5):
    """Best-effort POST to the FastAPI dashboard server. Never raises."""
    try:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{DASHBOARD_URL}{path}", data=data,
            headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def _get_json(path, timeout=1.0):
    try:
        with urllib.request.urlopen(f"{DASHBOARD_URL}{path}", timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def _dashboard_is_up():
    return _get_json("/api/telemetry") is not None


class DashboardBridge:
    """Mirrors this process's local telemetry_data onto a running FastAPI
    dashboard server (if one is reachable at DASHBOARD_URL), and relays the
    dashboard's Stop button back into this process's own stop flag.

    The CLI script and the FastAPI server run in separate OS processes, so
    each has its own copy of `telemetry_data` — this bridge is what makes a
    CLI-launched run visible on the dashboard in real time, exactly like a
    dashboard-launched run.
    """

    def __init__(self, school_names, config):
        self.enabled = _dashboard_is_up()
        self._pushed_rounds = 0
        self._stop_event = threading.Event()
        self._watch_thread = None
        if self.enabled:
            print("[FL] Dashboard detected at localhost:8000 — this run will appear live on it.")
            _post_json("/api/telemetry/cli-start", {
                "school_names": school_names,
                "config": config,
            })
        else:
            print("[FL] No dashboard detected at localhost:8000 — running in standalone mode.")

    def start_watching(self):
        if not self.enabled:
            return
        self._watch_thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._watch_thread.start()

    def _watch_loop(self):
        while not self._stop_event.is_set():
            self._push_new_rounds()
            status = _get_json("/api/telemetry/cli-stop-check")
            if status and status.get("stop_requested"):
                telemetry_data["_stop_requested"] = True
            time.sleep(1.0)

    def _push_new_rounds(self):
        rounds = telemetry_data.get("rounds", [])
        while self._pushed_rounds < len(rounds):
            round_metrics = rounds[self._pushed_rounds]
            _post_json("/api/telemetry/cli-round", {
                "round_metrics": round_metrics,
                "clients": telemetry_data.get("clients", {}),
            })
            self._pushed_rounds += 1

    def stop(self):
        if not self.enabled:
            return
        self._stop_event.set()
        if self._watch_thread:
            self._watch_thread.join(timeout=2.0)
        self._push_new_rounds()
        _post_json("/api/telemetry/cli-end", {})


def run_simulation(rounds, nodes, use_dp, use_paillier, lr, epochs, key_bits=2048, seed=42):
    torch.manual_seed(seed)  # controls initial model weights, matching the seed used for the data split
    school_names = SCHOOL_NAMES_ALL[:nodes]
    print(f"\n[FL] Starting simulation — rounds={rounds}, nodes={nodes}, "
          f"dp={use_dp}, paillier={use_paillier}, lr={lr}, epochs={epochs}")
    print(f"[FL] School nodes: {school_names}\n")

    # Sync telemetry so strategy picks up correct config
    telemetry_data["clients"] = _build_default_clients(school_names)
    telemetry_data["config"]["use_dp"]       = str(use_dp)
    telemetry_data["config"]["use_paillier"] = str(use_paillier)
    telemetry_data["config"]["lr"]           = lr
    telemetry_data["config"]["local_epochs"] = epochs
    telemetry_data["config"]["total_rounds"] = rounds
    telemetry_data["config"]["num_nodes"]    = nodes
    telemetry_data["config"]["paillier_key_bits"] = key_bits

    bridge = DashboardBridge(school_names, dict(telemetry_data["config"]))

    strategy = PaillierFedAvg(school_names=school_names, key_length=key_bits)

    server_error = {"msg": None}

    def run_server():
        try:
            fl.server.start_server(
                server_address="127.0.0.1:8088",
                config=fl.server.ServerConfig(num_rounds=rounds),
                strategy=strategy,
            )
        except Exception as exc:
            server_error["msg"] = str(exc)
            print(f"[FL SERVER ERROR] {exc}")

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    if not wait_for_port("127.0.0.1", 8088, max_wait=10.0):
        if server_error["msg"]:
            print(f"[FL] Server failed to start: {server_error['msg']}")
        else:
            print("[FL] Timed out waiting for server — check if port 8088 is already in use.")
        bridge.stop()
        sys.exit(1)

    print("[FL] Server ready. Launching client threads...")
    client_threads = []

    def run_client(school_name):
        try:
            from client.client import StudentFLClient
            client = StudentFLClient(school_name, seed=seed)
            fl.client.start_numpy_client(server_address="127.0.0.1:8088", client=client)
        except Exception as exc:
            print(f"[FL CLIENT ERROR — {school_name}] {exc}")

    bridge.start_watching()

    for school in school_names:
        t = threading.Thread(target=run_client, args=(school,), daemon=True)
        t.start()
        client_threads.append(t)

    server_thread.join()
    bridge.stop()

    print("\n[FL] Simulation complete.")
    print(f"[FL] Metrics saved to logs/fl_metrics.db — view with: sqlite3 logs/fl_metrics.db 'SELECT * FROM fl_metrics;'")

    # Print final round summary if available
    if telemetry_data["rounds"]:
        last = telemetry_data["rounds"][-1]
        print(f"\n[FL] Final round {last.get('round', '?')} summary:")
        print(f"     F1:       {last.get('f1_score', 'N/A')}")
        print(f"     Accuracy: {last.get('accuracy', 'N/A')}")
        print(f"     AUC-ROC:  {last.get('auc_roc', 'N/A')}")
        print(f"     Comm(MB): {last.get('comm_overhead_mb', 'N/A')}")
        return last
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Run FL simulation directly from the command line"
    )
    parser.add_argument("--rounds",           type=int,   default=50,    help="Number of FL rounds (default: 50)")
    parser.add_argument("--nodes",            type=int,   default=3,     help="Number of school nodes 3-5 (default: 3)")
    parser.add_argument("--dp",               type=str,   default="True", help="Enable DP-SGD: True/False (default: True)")
    parser.add_argument("--paillier",         type=str,   default="True", help="Enable Paillier: True/False (default: True)")
    parser.add_argument("--paillier-key-bits",type=int,   default=2048,  help="Paillier key size in bits (default: 2048; use 512 for speed testing)")
    parser.add_argument("--lr",               type=float, default=0.01,  help="Learning rate (default: 0.01)")
    parser.add_argument("--epochs",           type=int,   default=3,     help="Local epochs per round (default: 3)")
    args = parser.parse_args()

    nodes = max(3, min(5, args.nodes))
    use_dp       = args.dp.lower() not in ("false", "0", "no")
    use_paillier = args.paillier.lower() not in ("false", "0", "no")
    key_bits     = args.paillier_key_bits

    if use_paillier and key_bits < 2048:
        print(f"[WARNING] Using {key_bits}-bit Paillier key — for security use 2048 bits.")

    run_simulation(args.rounds, nodes, use_dp, use_paillier, args.lr, args.epochs, key_bits=key_bits)


if __name__ == "__main__":
    main()
