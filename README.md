# Cross-School Federated Learning for Privacy-Preserving Student Progress Tracking

**Project 12 — Group 7 | CS Department 2026**

A privacy-preserving federated learning (FL) system for Ghanaian district school networks.
Schools collaboratively train a student at-risk prediction model without any raw student data
ever leaving the school server. All communication is encrypted with Paillier homomorphic
encryption; local training is protected by Opacus DP-SGD.

---

## Stack

| Layer | Technology |
|---|---|
| FL Framework | Flower 1.8.0 |
| ML Training | PyTorch 2.3.0 — 8→64→32→1 MLP |
| Differential Privacy | Opacus 1.4.0 (DP-SGD, ε≤3.0, δ=1e-5) |
| Secure Aggregation | python-paillier 1.5.0 (2048-bit Paillier) |
| Backend API | FastAPI 0.111.0 + uvicorn |
| Admin Dashboard | React 18.3.1 + Chart.js 4 + Vite 5 |
| Database | SQLite (per-node student data + fl_metrics + pending_updates) |
| Synthetic Data | CTGAN ≥0.7.4 + KS-test validation |
| Containerisation | Docker Compose 26.1.0 |
| Language | Python 3.11.9 |

---

## Directory Structure

```
project12-fl-ghana/
├── requirements.txt              # Pinned Python dependencies (Python 3.11)
├── docker-compose.yml            # Multi-container FL simulation
├── deploy_client.sh              # Raspberry Pi 4 deployment script
│
├── client/
│   ├── client.py                 # Flower NumPyClient (DP-SGD + Paillier)
│   ├── model.py                  # PyTorch MLP (8→64→32→1 Sigmoid)
│   └── database.py               # SQLite loader with feature normalisation
│
├── server/
│   ├── main.py                   # FastAPI REST API + simulation runner
│   └── strategy.py               # PaillierFedAvg custom Flower strategy
│
├── security/
│   ├── crypto.py                 # Paillier encrypt/decrypt/homomorphic sum
│   └── privacy.py                # Opacus DP-SGD wrappers (conditional import)
│
├── dashboard/                    # React 18.3.1 admin portal
│   ├── src/
│   │   ├── App.jsx               # Root component + polling loop
│   │   ├── api.js                # FastAPI fetch wrappers
│   │   └── components/
│   │       ├── DistrictView.jsx  # District officer view (convergence, metrics)
│   │       ├── SchoolAdminView.jsx # Per-node status + privacy budget
│   │       ├── ConfigPanel.jsx   # Config form + Start FL Simulation button
│   │       ├── ConvergenceChart.jsx
│   │       ├── CommOverheadChart.jsx
│   │       └── PrivacyAccuracyScatter.jsx
│   └── package.json
│
├── scripts/
│   ├── partition_oulad.py        # Step 3 — generate school SQLite partitions
│   ├── generate_data.py          # Core data generator (called by partition_oulad)
│   ├── generate_synthetic.py     # CTGAN minority-class augmentation + KS test
│   ├── run_fl_simulation.py      # Step 5 — standalone FL runner (no FastAPI needed)
│   ├── train_baseline.py         # Centralised baseline (Proposal Obj.1 comparison)
│   ├── privacy_accuracy_sweep.py # DP noise sweep → results/privacy_accuracy_tradeoff.json
│   ├── generate_charts.py        # Matplotlib paper charts (E1 visuals 2, 3, 4)
│   ├── run_client.py             # Docker/Pi single-client runner
│   └── sync_daemon.py            # Nightly cron sync daemon (02:00, D1 Component 5)
│
├── docker/
│   ├── Dockerfile.server
│   ├── Dockerfile.client
│   └── Dockerfile.dashboard
│
├── data/
│   └── partitions/               # School SQLite databases (created by Step 3)
│       ├── school_alpha.db
│       ├── school_beta.db
│       └── school_gamma.db       # (+ school_delta.db, school_epsilon.db for 5-node)
│
├── logs/                         # Runtime logs (git-ignored)
│   ├── fl_metrics.db             # Round metrics: f1, loss, accuracy, latency, epsilon, comm_mb
│   ├── crypto_audit.jsonl        # Cryptographic audit log (Proposal Obj.2)
│   └── pending_updates.db        # Offline node queue (D1 Component 5)
│
└── results/                      # Generated outputs (git-ignored)
    ├── baseline_metrics.json     # Centralised baseline F1, Accuracy, AUC-ROC
    ├── privacy_accuracy_tradeoff.json
    └── charts/                   # Matplotlib charts for paper
```

---

## Reproducibility Setup (matches Proposal D1 Checklist)

### Step 1 — Clone and enter the repository
```bash
git clone https://github.com/[group-repo]/project12-fl-ghana
cd project12-fl-ghana
```

### Step 2 — Create virtual environment and install dependencies
```bash
python3.11 -m venv .venv

# Windows
.venv\Scripts\activate
# Linux / Pi
source .venv/bin/activate

pip install -r requirements.txt
```

### Step 3 — Generate school data partitions
```bash
python scripts/partition_oulad.py --nodes 3 --output data/partitions/
# Use --nodes 5 for the full 5-school configuration
```

### Step 4 — Docker multi-node simulation (optional)
```bash
docker-compose up --build
# Launches 1 server + 1 React dashboard + 3 FL client containers
```

### Step 5 — Standalone FL simulation (no Docker required)
```bash
# Fast test (no encryption, no DP)
python scripts/run_fl_simulation.py --rounds 5 --nodes 3 --dp False --paillier False

# Full proposal configuration (slow — 2048-bit Paillier)
python scripts/run_fl_simulation.py --rounds 50 --nodes 3 --dp True --paillier True

# Speed test with smaller key (for development)
python scripts/run_fl_simulation.py --rounds 10 --nodes 3 --dp True --paillier True --paillier-key-bits 512
```

### Step 6 — Open the React admin dashboard
```bash
# Terminal 1 — FastAPI backend
python -m uvicorn server.main:app --host 0.0.0.0 --port 8000

# Terminal 2 — React dev server
cd dashboard && npm install && npm run dev
```
Open **http://localhost:3000** — click **▶ Start FL Simulation** on the District View.

### Step 7 — Raspberry Pi physical deployment
```bash
scp -r . pi@192.168.1.X:/home/pi/fl_client/
ssh pi@192.168.1.X "bash /home/pi/fl_client/deploy_client.sh"
```

---

## Research Analysis Scripts

```bash
# Generate centralised baseline (Proposal Obj.1)
python scripts/train_baseline.py

# Privacy-accuracy sweep (Proposal E1, Visual #3)
python scripts/privacy_accuracy_sweep.py --rounds 10

# Generate all matplotlib charts for paper/report (Proposal E1, Visuals 2–4)
python scripts/generate_charts.py

# CTGAN synthetic data for class-imbalance augmentation (Proposal D2)
python scripts/generate_synthetic.py --all --samples 300
```

---

## Key Design Decisions

| Decision | Justification |
|---|---|
| FedAvg weighted by local dataset size | Prevents large nodes dominating aggregation |
| Paillier applied to flattened weight *updates* (Δw), not full weights | Reduces ciphertext size; server sees only aggregate |
| Opacus DP-SGD with σ=1.1, clip=1.0 | Proposal D3 spec: target ε≤3.0 per round |
| Graceful node dropout | Offline nodes stored in pending_updates; retransmit at next window |
| Non-IID data splits by school archetype | Simulates realistic Ghanaian school demographic variation |
| React dashboard (port 3000) + FastAPI API (port 8000) | Decoupled; dashboard polls /api/telemetry every 3 s |

---

## Success Metrics (Proposal E3)

| # | Criterion | Target |
|---|---|---|
| 1 | FL F1-score vs centralised baseline | Within 5 percentage points |
| 2 | Zero plaintext gradient transmission | 0 plaintext across 50 rounds |
| 3 | Per-round training latency on Pi 4 | < 120 seconds |
| 4 | Communication overhead per round | < 50 MB per node |
| 5 | Dashboard SUS usability score | ≥ 70 (Good) |
