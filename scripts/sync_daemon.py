"""
Nightly Sync Daemon (Proposal D1, Component 5)
================================================
Scheduled cron entry: 0 2 * * *   (triggers at 02:00 nightly)

On Linux/Pi:  crontab -e  →  0 2 * * * /usr/bin/python3 /home/pi/fl_client/scripts/sync_daemon.py
On Windows:   Task Scheduler → Action: python scripts/sync_daemon.py

Behaviour
---------
1. Check internet / FL server connectivity.
2. If online: trigger a Flower client round immediately.
   Also flush any pending_updates stored from previous offline periods.
3. If offline: queue a synthetic "ping" marker for later retransmission.
   The actual model update will be sent on the next successful window.

Usage:
    python scripts/sync_daemon.py --school school_alpha --server 127.0.0.1:8000
"""
import argparse
import json
import socket
import sqlite3
import sys
import os
import time
from datetime import datetime

import urllib.request
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PENDING_DB = os.path.join("logs", "pending_updates.db")


def _init_pending_db():
    os.makedirs("logs", exist_ok=True)
    conn = sqlite3.connect(PENDING_DB)
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


def is_server_reachable(host, port, timeout=3):
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except OSError:
        return False


def flush_pending_updates(school_name, api_base):
    """Retransmit any updates that were queued while the node was offline."""
    if not os.path.exists(PENDING_DB):
        return 0

    conn = sqlite3.connect(PENDING_DB)
    rows = conn.execute(
        "SELECT id, round_id, update_json FROM pending_updates "
        "WHERE school_name = ? AND transmitted = 0 ORDER BY id",
        (school_name,)
    ).fetchall()

    sent = 0
    for row_id, round_id, update_json in rows:
        try:
            payload = json.dumps({
                "school_name": school_name,
                "round_id": round_id,
                **json.loads(update_json),
            }).encode()
            req = urllib.request.Request(
                f"{api_base}/api/client/{school_name}/queue-update",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=5)
            conn.execute("UPDATE pending_updates SET transmitted = 1 WHERE id = ?", (row_id,))
            conn.commit()
            sent += 1
            print(f"  [FLUSH] Retransmitted queued update for round {round_id}")
        except Exception as e:
            print(f"  [FLUSH] Failed to retransmit round {round_id}: {e}")
            break

    conn.close()
    return sent


def queue_offline_marker(school_name, round_estimate):
    """Store an offline marker so the server knows this node missed a round."""
    conn = sqlite3.connect(PENDING_DB)
    conn.execute(
        "INSERT INTO pending_updates (school_name, round_id, update_json, queued_at) VALUES (?, ?, ?, ?)",
        (school_name, round_estimate, json.dumps({"type": "offline_marker"}),
         datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()


def trigger_fl_round(school_name, fl_server_address):
    """Start a Flower client that connects to the FL server for one training round."""
    import flwr as fl
    from client.client import StudentFLClient

    print(f"  [SYNC] Connecting to Flower server at {fl_server_address}...")
    client = StudentFLClient(school_name)
    fl.client.start_numpy_client(server_address=fl_server_address, client=client)
    print(f"  [SYNC] Round complete.")


def main():
    parser = argparse.ArgumentParser(description="Nightly FL sync daemon")
    parser.add_argument("--school",    required=True,          help="e.g. school_alpha")
    parser.add_argument("--server",    default="127.0.0.1:8000", help="FastAPI server host:port")
    parser.add_argument("--fl-server", default="127.0.0.1:8088", help="Flower gRPC server host:port")
    args = parser.parse_args()

    _init_pending_db()

    api_host, api_port_str = args.server.rsplit(":", 1)
    fl_host, fl_port_str   = args.fl_server.rsplit(":", 1)
    api_base = f"http://{args.server}"

    print(f"[{datetime.utcnow().isoformat()}] Sync daemon starting for {args.school}")

    if not is_server_reachable(api_host, api_port_str):
        print(f"  FastAPI server unreachable at {args.server} — node is OFFLINE.")
        queue_offline_marker(args.school, round_estimate=0)
        sys.exit(0)

    # Flush any updates queued while offline
    sent = flush_pending_updates(args.school, api_base)
    if sent:
        print(f"  Flushed {sent} pending update(s).")

    if not is_server_reachable(fl_host, fl_port_str):
        print(f"  Flower server unreachable at {args.fl_server} — skipping training round.")
        sys.exit(0)

    try:
        trigger_fl_round(args.school, args.fl_server)
    except Exception as e:
        print(f"  [ERROR] Training round failed: {e}")
        sys.exit(1)

    print(f"[{datetime.utcnow().isoformat()}] Sync daemon complete.")


if __name__ == "__main__":
    main()
