"""
Standalone FL simulation runner (Proposal D1, Step 5).

Usage:
    python scripts/run_fl_simulation.py --rounds 50 --nodes 3 --dp True --paillier True
    python scripts/run_fl_simulation.py --rounds 10 --nodes 5 --dp False --paillier True --lr 0.005

This script runs a complete Flower FL simulation WITHOUT requiring the FastAPI server.
Results are saved to logs/fl_metrics.db and printed to console.
"""

import argparse
import os
import sys
import threading
import time
import socket

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import flwr as fl
from server.strategy import PaillierFedAvg, SCHOOL_NAMES_ALL, telemetry_data, _build_default_clients


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


def run_simulation(rounds, nodes, use_dp, use_paillier, lr, epochs, key_bits=2048):
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
        sys.exit(1)

    print("[FL] Server ready. Launching client threads...")
    client_threads = []

    def run_client(school_name):
        try:
            from client.client import StudentFLClient
            client = StudentFLClient(school_name)
            fl.client.start_numpy_client(server_address="127.0.0.1:8088", client=client)
        except Exception as exc:
            print(f"[FL CLIENT ERROR — {school_name}] {exc}")

    for school in school_names:
        t = threading.Thread(target=run_client, args=(school,), daemon=True)
        t.start()
        client_threads.append(t)

    server_thread.join()

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
