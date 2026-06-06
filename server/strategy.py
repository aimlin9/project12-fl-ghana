import torch
import flwr as fl
import numpy as np
import json
import time
from typing import List, Tuple, Union, Dict, Optional
from flwr.common import (
    Parameters, FitRes, EvaluateRes, Scalar, ndarrays_to_parameters, parameters_to_ndarrays
)
from flwr.server.client_proxy import ClientProxy

from client.model import get_model
from security.crypto import (
    generate_keys, serialize_public_key, deserialize_encrypted, homomorphic_sum, decrypt_weights
)

# Helper to flatten model weights
def get_flat_weights(model):
    params = []
    for param in model.parameters():
        params.append(param.data.cpu().numpy().flatten())
    return np.concatenate(params)

# Helper to restore weights from flat list
def set_flat_weights(model, flat_weights):
    idx = 0
    for param in model.parameters():
        shape = param.shape
        size = param.numel()
        param.data.copy_(torch.tensor(flat_weights[idx:idx+size]).reshape(shape))
        idx += size

# Shared telemetry data accessible by FastAPI
telemetry_data = {
    "rounds": [],
    "clients": {
        "school_alpha": {"status": "Idle", "last_active": "-", "last_latency": 0.0, "last_epsilon": 0.0},
        "school_beta": {"status": "Idle", "last_active": "-", "last_latency": 0.0, "last_epsilon": 0.0},
        "school_gamma": {"status": "Idle", "last_active": "-", "last_latency": 0.0, "last_epsilon": 0.0}
    },
    "config": {
        "use_dp": "True",
        "use_paillier": "True",
        "local_epochs": 3,
        "lr": 0.01,
        "total_rounds": 10
    },
    "simulation_running": False
}

class PaillierFedAvg(fl.server.strategy.Strategy):
    def __init__(self, key_length=1024):
        super().__init__()
        self.model = get_model()
        self.global_weights = get_flat_weights(self.model)
        self.key_length = key_length
        self.public_key = None
        self.private_key = None
        
        # Track rounds
        self.current_round = 0
        
    def initialize_parameters(self, client_manager):
        """Initialize global model parameters."""
        # Convert our flat weights array into list of parameters (1 array for each layer)
        # However, to be compatible, we can just return our model's initial weights as parameters
        ndarrays = [p.data.cpu().numpy() for p in self.model.parameters()]
        return ndarrays_to_parameters(ndarrays)

    def configure_fit(self, server_round: int, parameters: Parameters, client_manager) -> List[Tuple[ClientProxy, fl.common.FitIns]]:
        """Configure the next round of training."""
        self.current_round = server_round
        
        # Regenerate keys at startup or round 1
        if self.public_key is None and telemetry_data["config"]["use_paillier"] == "True":
            print("[Server Strategy] Generating Paillier key pair (2048-bit)...")
            start = time.perf_counter()
            self.public_key, self.private_key = generate_keys(self.key_length)
            print(f"[Server Strategy] Key pair generated in {time.perf_counter() - start:.2f}s")
            
        # Broadcast config
        config = {
            "use_dp": telemetry_data["config"]["use_dp"],
            "use_paillier": telemetry_data["config"]["use_paillier"],
            "local_epochs": str(telemetry_data["config"]["local_epochs"]),
            "lr": str(telemetry_data["config"]["lr"]),
        }
        
        if telemetry_data["config"]["use_paillier"] == "True":
            config["public_key_n"] = serialize_public_key(self.public_key)
            
        # Restore global weights to Parameters format
        ndarrays = []
        idx = 0
        for param in self.model.parameters():
            size = param.numel()
            shape = param.shape
            w = self.global_weights[idx:idx+size].reshape(shape)
            ndarrays.append(w)
            idx += size
            
        params = ndarrays_to_parameters(ndarrays)
        fit_ins = fl.common.FitIns(params, config)
        
        clients = client_manager.sample(num_clients=len(telemetry_data["clients"]), min_num_clients=1)
        
        # Update client statuses to Active
        for client in clients:
            # client.cid is client identity
            # Let's map cid to school_name
            # For simplicity, client.cid will be 'school_alpha', 'school_beta', etc.
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
        """Aggregate fit results."""
        if not results:
            print("[Server Strategy] No client results received.")
            return None, {}
            
        print(f"[Server Strategy] Aggregating fit results for round {server_round} ({len(results)} clients succeeded, {len(failures)} failed)...")
        
        # Parse configurations
        use_paillier = telemetry_data["config"]["use_paillier"] == "True"
        
        # Collect client updates and sample sizes
        client_updates = []
        total_samples = 0
        client_latencies = []
        client_epsilons = []
        active_schools = []
        
        # Calculate communication overhead (approximate size of JSON data payload)
        comm_overhead_bytes = 0
        
        for client, fit_res in results:
            metrics = fit_res.metrics
            school_name = metrics.get("school_name", client.cid)
            active_schools.append(school_name)
            
            num_samples = fit_res.num_examples
            total_samples += num_samples
            
            # Latency and Epsilon tracking
            latency = float(metrics.get("training_latency", 0.0)) + float(metrics.get("encryption_latency", 0.0))
            epsilon = float(metrics.get("epsilon", 0.0))
            client_latencies.append(latency)
            client_epsilons.append(epsilon)
            
            # Telemetry update per client
            if school_name in telemetry_data["clients"]:
                telemetry_data["clients"][school_name]["last_latency"] = latency
                telemetry_data["clients"][school_name]["last_epsilon"] = epsilon
                
            if use_paillier:
                # Retrieve encrypted weight update from metrics
                encrypted_str = metrics.get("encrypted_update")
                comm_overhead_bytes += len(encrypted_str)
                serialized_update = json.loads(encrypted_str)
                encrypted_update = deserialize_encrypted(self.public_key, serialized_update)
                client_updates.append((encrypted_update, num_samples))
            else:
                # Retrieve plaintext update
                plaintext_str = metrics.get("plaintext_update")
                comm_overhead_bytes += len(plaintext_str)
                plaintext_update = np.array(json.loads(plaintext_str))
                client_updates.append((plaintext_update, num_samples))
                
        # Update client statuses based on metrics school_name
        for school in telemetry_data["clients"]:
            if school in active_schools:
                telemetry_data["clients"][school]["status"] = "Idle"
            elif telemetry_data["clients"][school]["status"] == "Active":
                telemetry_data["clients"][school]["status"] = "Failed"
                
        # Aggregate weights
        start_agg = time.perf_counter()
        
        if use_paillier:
            # Homomorphic sum: sum of updates
            print("[Server Strategy] Performing homomorphic addition of encrypted weight tensors...")
            encrypted_updates_list = [update for update, _ in client_updates]
            summed_encrypted = homomorphic_sum(encrypted_updates_list)
            
            # Decrypt summed updates
            print("[Server Strategy] Decrypting aggregated tensor using server private key...")
            summed_plaintext = decrypt_weights(self.private_key, summed_encrypted)
            summed_plaintext = np.array(summed_plaintext)
            
            # Average the update (divided by number of clients)
            # Since Paillier sums them: sum_updates / num_clients
            avg_update = summed_plaintext / len(client_updates)
        else:
            # Standard FedAvg on plaintext updates (weighted by number of examples)
            weighted_updates = np.zeros_like(client_updates[0][0])
            for update, num_samples in client_updates:
                weighted_updates += update * (num_samples / total_samples)
            avg_update = weighted_updates
            
        aggregation_latency = time.perf_counter() - start_agg
        print(f"[Server Strategy] Aggregation and decryption completed in {aggregation_latency:.2f}s")
        
        # Apply average update to global weights
        self.global_weights = self.global_weights + avg_update
        
        # Convert global weights to parameter object
        ndarrays = []
        idx = 0
        for param in self.model.parameters():
            size = param.numel()
            shape = param.shape
            w = self.global_weights[idx:idx+size].reshape(shape)
            ndarrays.append(w)
            idx += size
            
        params = ndarrays_to_parameters(ndarrays)
        
        # Save aggregate round metrics (will be supplemented by evaluate)
        telemetry_data["last_round_metrics"] = {
            "round": server_round,
            "active_clients": len(results),
            "failed_clients": len(failures),
            "avg_latency": float(np.mean(client_latencies)) if client_latencies else 0.0,
            "max_epsilon": float(np.max(client_epsilons)) if client_epsilons else 0.0,
            "comm_overhead_mb": float(comm_overhead_bytes) / (1024 * 1024),
            "agg_latency": aggregation_latency,
            "is_encrypted": use_paillier
        }
        
        return params, {}

    def configure_evaluate(self, server_round: int, parameters: Parameters, client_manager) -> List[Tuple[ClientProxy, fl.common.EvaluateIns]]:
        """Configure evaluation."""
        config = {}
        # Convert global weights to Parameter object
        ndarrays = []
        idx = 0
        for param in self.model.parameters():
            size = param.numel()
            shape = param.shape
            w = self.global_weights[idx:idx+size].reshape(shape)
            ndarrays.append(w)
            idx += size
            
        params = ndarrays_to_parameters(ndarrays)
        evaluate_ins = fl.common.EvaluateIns(params, config)
        
        clients = client_manager.sample(num_clients=len(telemetry_data["clients"]), min_num_clients=1)
        return [(client, evaluate_ins) for client in clients]

    def aggregate_evaluate(
        self,
        server_round: int,
        results: List[Tuple[ClientProxy, EvaluateRes]],
        failures: List[Union[Tuple[ClientProxy, EvaluateRes], BaseException]]
    ) -> Tuple[Optional[float], Dict[str, Scalar]]:
        """Aggregate evaluation metrics."""
        if not results:
            return None, {}
            
        # Compute weighted average of client metrics
        total_loss = 0.0
        total_examples = 0
        accuracies = []
        f1_scores = []
        
        for client, eval_res in results:
            loss = eval_res.loss
            num_examples = eval_res.num_examples
            total_examples += num_examples
            total_loss += loss * num_examples
            
            accuracies.append(eval_res.metrics.get("accuracy", 0.0))
            f1_scores.append(eval_res.metrics.get("f1_score", 0.0))
            
        avg_loss = total_loss / total_examples
        avg_accuracy = np.mean(accuracies)
        avg_f1 = np.mean(f1_scores)
        
        print(f"[Server Strategy] Evaluation Round {server_round} aggregated - Loss: {avg_loss:.4f}, Accuracy: {avg_accuracy:.4f}, F1-score: {avg_f1:.4f}")
        
        # Save complete round metrics to telemetry
        round_metrics = telemetry_data.get("last_round_metrics", {})
        round_metrics["loss"] = float(avg_loss)
        round_metrics["accuracy"] = float(avg_accuracy)
        telemetry_data["rounds"].append(round_metrics)
        
        return avg_loss, {"accuracy": avg_accuracy, "f1_score": avg_f1}

    def evaluate(self, server_round: int, parameters: Parameters) -> Optional[Tuple[float, Dict[str, Scalar]]]:
        """Evaluate global model parameters on server side. Not used, so return None."""
        return None
