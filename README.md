# Cross-School Federated Learning for Privacy-Preserving Student Progress Tracking

This project implements a privacy-preserving federated learning (FL) system designed for Ghanaian district school networks. It operates entirely offline, enabling secure collaborative student progress prediction models without transferring raw student data.

## Features

- **Distributed Client Model**: Trains PyTorch Multi-Layer Perceptron (MLP) binary classifiers locally on school servers to identify students at risk of falling behind.
- **SQLite Local Storage**: Simulates isolated, school-specific databases with distinct demographics (non-IID data distributions based on Open University Learning Analytics Dataset patterns).
- **Secure Aggregation**: Implements Paillier homomorphic encryption via `python-paillier (phe)`. The server decrypts only the aggregated weight updates and has zero plaintext access to individual client updates.
- **Differential Privacy (DP-SGD)**: Integrates Opacus to clip gradients and inject Gaussian noise, mitigating membership inference attacks.
- **Wow Moment Node Dropout Control**: Toggle connectivity status of individual schools on-the-fly to test Flower's strategy dropout handling and queued synchronization.
- **Premium Glassmorphism Dashboard**: A dark-mode dashboard displaying live accuracy, macro F1-scores, network overhead, privacy spent, and real-time client round telemetry.

---

## Directory Structure

```
project12-fl-ghana/
├── requirements.txt
├── docker-compose.yml
├── README.md
├── server/
│   ├── main.py            # FastAPI dashboard server & API
│   ├── strategy.py        # Flower custom strategy (FedAvg + homomorphic decryption)
│   └── templates/         # Dashboard UI assets (vanilla JS & CSS, Chart.js)
│       └── dashboard.html
├── client/
│   ├── client.py          # Flower client logic + Paillier encryptor
│   ├── model.py           # PyTorch MLP model
│   └── database.py        # Local SQLite data loader
├── security/
│   ├── crypto.py          # Paillier encryption/decryption utilities
│   └── privacy.py         # Opacus DP-SGD wrappers
└── scripts/
    ├── generate_data.py   # Generates simulated school SQLite databases
    ├── run_client.py      # Independent client node runner (for Docker Compose)
    └── run_simulation.py  # Local server launcher
```

---

## Getting Started

Ensure you are inside the virtual environment:
```powershell
# To activate the existing virtual environment on Windows
& "C:\Users\Duncan\Desktop\FEDERATED SCHOOL\venv\Scripts\Activate.ps1"
```

### 1. Generate local SQLite databases
Generate local student performance datasets for School Alpha, School Beta, and School Gamma:
```bash
python scripts/generate_data.py
```

### 2. Run the simulation
Start the FastAPI backend and web server:
```bash
python scripts/run_simulation.py
```

### 3. Open dashboard in a browser
Navigate to: **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

Click **Start FL Simulation** to begin training rounds. Toggle the **Toggle Connectivity** button on any client to simulate dropouts and watch the Flower strategy adapt.

---

## Running with Docker Compose

To test the multi-container configuration:
```bash
# Build and start all services
docker-compose up --build
```
This launches 1 FastAPI server and 3 client containers that wait for the server.
1. Open **[http://localhost:8000](http://localhost:8000)**.
2. Click **Start FL Simulation**. The client containers will detect the server starting up, connect, and perform the training rounds.
