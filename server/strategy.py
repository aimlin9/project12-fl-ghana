import os
import sqlite3
import torch
import flwr as fl
import numpy as np
import json
import time
from datetime import datetime, timezone
from typing import List, Tuple, Union, Dict, Optional
from flwr.common import (
    Parameters, FitRes, EvaluateRes, Scalar, ndarrays_to_parameters
)
from flwr.server.client_proxy import ClientProxy

from client.model import get_model
from security.crypto import (
    generate_keys, serialize_public_key, deserialize_encrypted, homomorphic_sum, decrypt_weights
)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def get_flat_weights(model):
    params = []
    with torch.no_grad():
        for param in model.parameters():
            params.append(param.data.cpu().numpy().flatten())
    return np.concatenate(params)


def set_flat_weights(model, flat_weights):
    with torch.no_grad():
        idx = 0
        for param in model.parameters():
            shape = param.shape
            size = param.numel()
            param.data.copy_(
                torch.tensor(flat_weights[idx:idx + size], dtype=torch.float32).reshape(shape)
            )
            idx += size


def _global_weights_to_ndarrays(model, global_weights):
    """Convert flat global_weights array into per-layer ndarrays matching model shape."""
    ndarrays = []
    idx = 0
    for param in model.parameters():
        size = param.numel()
        shape = param.shape
        ndarrays.append(global_weights[idx:idx + size].reshape(shape))
        idx += size
    return ndarrays


# ---------------------------------------------------------------------------
# Shared telemetry data accessible by FastAPI
# ---------------------------------------------------------------------------

def _build_default_clients(school_names):
    return {
        name: {"status": "Idle", "last_active": "-", "last_latency": 0.0, "last_epsilon": 0.0}
        for name in school_names
    }


DEFAULT_SCHOOLS = ["school_alpha", "school_beta", "school_gamma"]
SCHOOL_NAMES_ALL = ["school_alpha", "school_beta", "school_gamma", "school_delta", "school_epsilon"]

telemetry_data = {
    "rounds": [],
    "clients": _build_default_clients(DEFAULT_SCHOOLS),
    "config": {
        "use_dp": "True",
        "use_paillier": "True",
        "local_epochs": 3,
        "lr": 0.01,
        "total_rounds": 10,
        "num_nodes": 3,
        "paillier_key_bits": 2048,
        "noise_multiplier": 1.1,
        "max_grad_norm": 1.0,
    },
    "simulation_running": False,
    "live_accuracy": None,
    "_stop_requested": False,
}


# ---------------------------------------------------------------------------
# fl_metrics SQLite helpers  (Proposal D2: fl_metrics table)
# ---------------------------------------------------------------------------

def _get_metrics_db_path():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.makedirs(os.path.join(root, "logs"), exist_ok=True)
    return os.path.join(root, "logs", "fl_metrics.db")


def _init_metrics_db():
    conn = sqlite3.connect(_get_metrics_db_path())
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fl_metrics (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            round_id   INTEGER NOT NULL,
            node_id    TEXT    NOT NULL,
            f1         REAL,
            loss       REAL,
            accuracy   REAL,
            latency_s  REAL,
            comm_mb    REAL,
            epsilon    REAL,
            timestamp  TEXT
        )
    """)
    conn.commit()
    conn.close()


def _log_round_metrics(round_id, node_id, f1, loss, accuracy, latency_s, comm_mb, epsilon):
    conn = sqlite3.connect(_get_metrics_db_path())
    conn.execute(
        """INSERT INTO fl_metrics
           (round_id, node_id, f1, loss, accuracy, latency_s, comm_mb, epsilon, timestamp)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (round_id, node_id, f1, loss, accuracy, latency_s, comm_mb, epsilon,
         datetime.now(timezone.utc).isoformat())
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Strategy
# ---------------------------------------------------------------------------

class PaillierFedAvg(fl.server.strategy.Strategy):
    def __init__(self, key_length=2048, school_names=None):
        super().__init__()
        self.model = get_model()
        self.global_weights = get_flat_weights(self.model)
        self.key_length = key_length
        self.public_key = None
        self.private_key = None
        self.current_round = 0
        self.school_names = school_names or DEFAULT_SCHOOLS

        _init_metrics_db()

    def initialize_parameters(self, client_manager):
        ndarrays = [p.data.cpu().numpy() for p in self.model.parameters()]
        return ndarrays_to_parameters(ndarrays)

    def configure_fit(self, server_round: int, parameters: Parameters, client_manager) -> List[Tuple[ClientProxy, fl.common.FitIns]]:
        if telemetry_data.get("_stop_requested"):
            telemetry_data["simulation_running"] = False
            raise RuntimeError("Simulation stopped by user.")

        self.current_round = server_round

        if self.public_key is None and telemetry_data["config"]["use_paillier"] == "True":
            print(f"[Server Strategy] Generating Paillier key pair ({self.key_length}-bit)...")
            start = time.perf_counter()
            self.public_key, self.private_key = generate_keys(self.key_length)
            print(f"[Server Strategy] Key pair generated in {time.perf_counter() - start:.2f}s")

        config = {
            "use_dp":              telemetry_data["config"]["use_dp"],
            "use_paillier":        telemetry_data["config"]["use_paillier"],
            "local_epochs":        str(telemetry_data["config"]["local_epochs"]),
            "lr":                  str(telemetry_data["config"]["lr"]),
            "dp_noise_multiplier": str(telemetry_data["config"]["noise_multiplier"]),
            "dp_max_grad_norm":    str(telemetry_data["config"]["max_grad_norm"]),
        }

        if telemetry_data["config"]["use_paillier"] == "True":
            config["public_key_n"] = serialize_public_key(self.public_key)

        params = ndarrays_to_parameters(_global_weights_to_ndarrays(self.model, self.global_weights))
        fit_ins = fl.common.FitIns(params, config)

        online_count = sum(
            1 for info in telemetry_data["clients"].values()
            if info.get("status") != "Offline"
        )
        # Round 1 can race ahead of client gRPC registration: the TCP port accepts
        # connections before ClientManager.num_available() reflects registered clients,
        # so sampling immediately can select 0 clients and silently no-op the round.
        # wait_for() blocks (briefly) until the expected client count has registered.
        client_manager.wait_for(num_clients=max(online_count, 1), timeout=10)

        available = client_manager.num_available()
        sample_count = min(available, max(online_count, 1))
        clients = client_manager.sample(
            num_clients=sample_count,
            min_num_clients=max(1, min(2, sample_count)),
        )

        for client in clients:
            cid = client.cid
            if cid in telemetry_data["clients"]:
                telemetry_data["clients"][cid]["status"] = "Active"
                telemetry_data["clients"][cid]["last_active"] = time.strftime("%H:%M:%S")

        return [(client, fit_ins) for client in clients]

    def aggregate_fit(
        self,
        server_round: int,
        results: List[Tuple[ClientProxy, FitRes]],
        failures: List[Union[Tuple[ClientProxy, FitRes], BaseException]]
    ) -> Tuple[Optional[Parameters], Dict[str, Scalar]]:
        if not results:
            print("[Server Strategy] No client results received.")
            return None, {}

        print(f"[Server Strategy] Aggregating round {server_round} "
              f"({len(results)} succeeded, {len(failures)} failed)...")

        use_paillier = telemetry_data["config"]["use_paillier"] == "True"

        client_updates = []
        total_samples = 0
        client_latencies = []
        client_epsilons = []
        active_schools = []
        comm_overhead_bytes = 0

        for client, fit_res in results:
            metrics = fit_res.metrics
            school_name = metrics.get("school_name", client.cid)
            active_schools.append(school_name)

            num_samples = fit_res.num_examples
            total_samples += num_samples

            latency = float(metrics.get("training_latency", 0.0)) + float(metrics.get("encryption_latency", 0.0))
            epsilon = float(metrics.get("epsilon", 0.0))
            client_latencies.append(latency)
            client_epsilons.append(epsilon)

            if school_name in telemetry_data["clients"]:
                telemetry_data["clients"][school_name]["last_latency"] = latency
                telemetry_data["clients"][school_name]["last_epsilon"] = epsilon

            if use_paillier:
                encrypted_str = metrics.get("encrypted_update")
                if encrypted_str is None:
                    print(f"[Server Strategy] WARNING: Missing encrypted_update from {school_name}, skipping.")
                    continue
                comm_overhead_bytes += len(encrypted_str)
                encrypted_update = deserialize_encrypted(self.public_key, json.loads(encrypted_str))
                client_updates.append((encrypted_update, num_samples))
            else:
                plaintext_str = metrics.get("plaintext_update")
                if plaintext_str is None:
                    print(f"[Server Strategy] WARNING: Missing plaintext_update from {school_name}, skipping.")
                    continue
                comm_overhead_bytes += len(plaintext_str)
                plaintext_update = np.array(json.loads(plaintext_str))
                client_updates.append((plaintext_update, num_samples))

        if not client_updates:
            print("[Server Strategy] All updates missing — skipping aggregation.")
            return None, {}

        # Update client statuses
        for school in telemetry_data["clients"]:
            if school in active_schools:
                telemetry_data["clients"][school]["status"] = "Idle"
            elif telemetry_data["clients"][school]["status"] == "Active":
                telemetry_data["clients"][school]["status"] = "Failed"

        # Aggregate
        start_agg = time.perf_counter()

        if use_paillier:
            # Paillier supports scalar multiplication: E(w) * s = E(w * s).
            # So we can apply FedAvg weights BEFORE homomorphic summation:
            # weighted_sum = sum_i( E(update_i) * (n_i / total) )
            # Then a single decryption gives the correct FedAvg average.
            print("[Server Strategy] Applying FedAvg weights to encrypted tensors...")
            weighted_enc_updates = [
                [ew * (n / total_samples) for ew in enc_update]
                for enc_update, n in client_updates
            ]
            print("[Server Strategy] Performing homomorphic summation of weighted tensors...")
            summed_encrypted = homomorphic_sum(weighted_enc_updates)
            print("[Server Strategy] Decrypting aggregated tensor using server private key...")
            avg_update = np.array(decrypt_weights(self.private_key, summed_encrypted))
        else:
            avg_update = np.zeros_like(client_updates[0][0])
            for update, n in client_updates:
                avg_update += update * (n / total_samples)

        aggregation_latency = time.perf_counter() - start_agg
        print(f"[Server Strategy] Aggregation completed in {aggregation_latency:.2f}s")

        self.global_weights = self.global_weights + avg_update

        params = ndarrays_to_parameters(_global_weights_to_ndarrays(self.model, self.global_weights))

        comm_overhead_mb = float(comm_overhead_bytes) / (1024 * 1024)


        telemetry_data["last_round_metrics"] = {
            "round":          server_round,
            "active_clients": len(results),
            "failed_clients": len(failures),
            "avg_latency":    float(np.mean(client_latencies)) if client_latencies else 0.0,
            "max_epsilon":    float(np.max(client_epsilons)) if client_epsilons else 0.0,
            "comm_overhead_mb": comm_overhead_mb,
            "agg_latency":    aggregation_latency,
            "is_encrypted":   use_paillier,
        }

        # Cryptographic audit log
        audit_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
        os.makedirs(audit_dir, exist_ok=True)
        audit_entry = {
            "round_id":               server_round,
            "timestamp":              datetime.now(timezone.utc).isoformat(),
            "num_clients_succeeded":  len(results),
            "num_clients_failed":     len(failures),
            "encryption_enabled":     use_paillier,
            "key_size_bits":          self.key_length if use_paillier else 0,
            "all_updates_encrypted":  use_paillier and all(
                r[1].metrics.get("is_encrypted") == "True" for r in results
            ),
            "plaintext_exposure_count": sum(
                1 for r in results if r[1].metrics.get("is_encrypted") != "True"
            ),
            "aggregation_latency_s":  round(aggregation_latency, 4),
            "comm_overhead_mb":       round(comm_overhead_mb, 4),
        }
        with open(os.path.join(audit_dir, "crypto_audit.jsonl"), "a") as f:
            f.write(json.dumps(audit_entry) + "\n")

        return params, {}

    def configure_evaluate(self, server_round: int, parameters: Parameters, client_manager) -> List[Tuple[ClientProxy, fl.common.EvaluateIns]]:
        params = ndarrays_to_parameters(_global_weights_to_ndarrays(self.model, self.global_weights))
        evaluate_ins = fl.common.EvaluateIns(params, {})
        available = client_manager.num_available()
        online_count = max(1, sum(
            1 for info in telemetry_data["clients"].values()
            if info.get("status") != "Offline"
        ))
        sample_count = min(available, online_count)
        clients = client_manager.sample(num_clients=sample_count, min_num_clients=1)
        return [(client, evaluate_ins) for client in clients]

    def aggregate_evaluate(
        self,
        server_round: int,
        results: List[Tuple[ClientProxy, EvaluateRes]],
        failures: List[Union[Tuple[ClientProxy, EvaluateRes], BaseException]]
    ) -> Tuple[Optional[float], Dict[str, Scalar]]:
        if not results:
            return None, {}

        total_loss = 0.0
        total_examples = 0
        accuracies = []
        f1_scores = []
        auc_roc_scores = []

        round_metrics = telemetry_data.get("last_round_metrics", {})
        round_metrics.setdefault("round", server_round)
        comm_mb = round_metrics.get("comm_overhead_mb", 0.0)
        max_epsilon = round_metrics.get("max_epsilon", 0.0)

        for client, eval_res in results:
            num_examples = eval_res.num_examples
            total_examples += num_examples
            total_loss += eval_res.loss * num_examples

            m = eval_res.metrics
            accuracies.append(float(m.get("accuracy", 0.0)))
            f1_scores.append(float(m.get("f1_score", 0.0)))
            auc_roc_scores.append(float(m.get("auc_roc", 0.0)))

            school_name = m.get("school_name", client.cid)
            latency = float(round_metrics.get("avg_latency", 0.0))

            _log_round_metrics(
                round_id=server_round,
                node_id=school_name,
                f1=float(m.get("f1_score", 0.0)),
                loss=eval_res.loss,
                accuracy=float(m.get("accuracy", 0.0)),
                latency_s=latency,
                comm_mb=comm_mb,
                epsilon=float(m.get("epsilon_at_eval", max_epsilon)),
            )

        avg_loss = total_loss / total_examples if total_examples else 0.0
        avg_accuracy = float(np.mean(accuracies))
        avg_f1 = float(np.mean(f1_scores))
        avg_auc = float(np.mean([v for v in auc_roc_scores if v > 0.0])) if any(v > 0.0 for v in auc_roc_scores) else 0.0

        print(f"[Server Strategy] Eval round {server_round} — "
              f"Loss: {avg_loss:.4f}, Acc: {avg_accuracy:.4f}, F1: {avg_f1:.4f}, AUC: {avg_auc:.4f}")

        round_metrics["loss"] = avg_loss
        round_metrics["accuracy"] = avg_accuracy
        round_metrics["f1_score"] = avg_f1
        round_metrics["auc_roc"] = avg_auc
        telemetry_data["rounds"].append(round_metrics)
        telemetry_data["live_accuracy"] = None
        telemetry_data["_live_per_school"] = {}

        return avg_loss, {"accuracy": avg_accuracy, "f1_score": avg_f1, "auc_roc": avg_auc}

    def evaluate(self, server_round: int, parameters: Parameters) -> Optional[Tuple[float, Dict[str, Scalar]]]:
        return None
