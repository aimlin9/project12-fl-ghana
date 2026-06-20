#!/usr/bin/env bash
# Raspberry Pi 4 client deployment script (Proposal D1, Step 7).
# Run on the Pi AFTER copying the client/ directory via scp:
#   scp -r client/ scripts/ requirements.txt data/ pi@192.168.1.X:/home/pi/fl_client/
#   ssh pi@192.168.1.X "bash /home/pi/fl_client/deploy_client.sh school_alpha 192.168.1.1"
#
# Arguments:
#   $1  school name   (e.g. school_alpha)
#   $2  server IP     (e.g. 192.168.1.1)

set -euo pipefail

SCHOOL="${1:-school_alpha}"
SERVER_IP="${2:-127.0.0.1}"
FL_PORT="8088"
INSTALL_DIR="/home/pi/fl_client"

echo "=== Project 12 — FL Client Deployment ==="
echo "School : $SCHOOL"
echo "Server : $SERVER_IP:$FL_PORT"
echo "Dir    : $INSTALL_DIR"
echo ""

# 1. System packages (Pi OS Bookworm / Bullseye)
echo "[1/5] Installing system packages..."
sudo apt-get update -qq
sudo apt-get install -y python3.11 python3.11-venv python3.11-dev \
    build-essential libssl-dev libffi-dev sqlite3 --no-install-recommends

# 2. Python venv
echo "[2/5] Creating Python 3.11 virtual environment..."
cd "$INSTALL_DIR"
python3.11 -m venv .venv
.venv/bin/pip install --upgrade pip -q

# 3. Install dependencies (Pi-compatible subset — no ctgan, lighter opacus)
echo "[3/5] Installing Python dependencies..."
.venv/bin/pip install \
    flwr==1.8.0 \
    torch==2.3.0 \
    opacus==1.4.0 \
    phe==1.5.0 \
    scikit-learn==1.5.0 \
    pandas==2.2.2 \
    numpy==1.26.4 \
    scipy==1.13.1 \
    -q

# 4. Verify data partition exists
echo "[4/5] Checking data partition for $SCHOOL..."
DB_PATH="$INSTALL_DIR/data/partitions/${SCHOOL}.db"
if [ ! -f "$DB_PATH" ]; then
    echo "  WARNING: $DB_PATH not found."
    echo "  Run 'python scripts/partition_oulad.py --nodes 3 --output data/partitions/' on the server first,"
    echo "  then copy the correct .db file to this Pi."
fi

# 5. Install cron job for nightly sync
echo "[5/5] Installing nightly cron sync daemon (02:00 nightly)..."
CRON_CMD="0 2 * * * $INSTALL_DIR/.venv/bin/python $INSTALL_DIR/scripts/sync_daemon.py --school $SCHOOL --server $SERVER_IP:8000 --fl-server $SERVER_IP:$FL_PORT >> $INSTALL_DIR/logs/sync.log 2>&1"
# Only add if not already present
(crontab -l 2>/dev/null | grep -v "sync_daemon" ; echo "$CRON_CMD") | crontab -

echo ""
echo "=== Deployment complete ==="
echo "To start the client manually:"
echo "  $INSTALL_DIR/.venv/bin/python scripts/run_client.py --school $SCHOOL --server $SERVER_IP:$FL_PORT"
