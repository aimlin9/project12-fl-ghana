import flwr as fl
import torch
import numpy as np
import json
import time
import urllib.request
from sklearn.metrics import f1_score

from client.model import get_model
from client.database import load_data
from security.crypto import deserialize_public_key, encrypt_weights, serialize_encrypted
from security.privacy import make_private_training, get_privacy_spent

# Helper to flatten model weights
def get_flat_weights(model):
    params = []
    with torch.no_grad():
        for param in model.parameters():
            params.append(param.cpu().numpy().flatten())
    return np.concatenate(params)

# Helper to restore model weights from flat list
def set_flat_weights(model, flat_weights):
    idx = 0
    with torch.no_grad():
        for param in model.parameters():
            shape = param.shape
            size = param.numel()
            w = torch.tensor(flat_weights[idx:idx+size], dtype=torch.float32).reshape(shape)
            param.copy_(w)
            idx += size

# Query FastAPI server for simulated status (Online/Offline)
def get_client_status(school_name):
    try:
        url = f"http://127.0.0.1:8000/api/client/{school_name}/status"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=0.5) as response:
            data = json.loads(response.read().decode())
            return data.get("status", "Idle")
    except Exception:
        # Default to Idle if backend server is not running
        return "Idle"

class StudentFLClient(fl.client.NumPyClient):
    def __init__(self, school_name, db_dir="data/partitions", batch_size=32):
        self.school_name = school_name
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = get_model().to(self.device)
        self.train_loader, self.test_loader, self.num_train, self.num_test = load_data(
            school_name, db_dir=db_dir, batch_size=batch_size
        )
        print(f"[{self.school_name}] Initialized with {self.num_train} train samples, {self.num_test} test samples.")

    def get_parameters(self, config):
       return [p.detach().cpu().numpy() for p in self.model.parameters()]

    def fit(self, parameters, config):
        # 0. Check simulated online status from server
        status = get_client_status(self.school_name)
        if status == "Offline":
            print(f"[{self.school_name}] Simulated Network Error: School server is OFFLINE.")
            raise ConnectionError(f"Simulated network dropout for {self.school_name}")

        # 1. Update model with global weights
        flat_global = np.concatenate([p.flatten() for p in parameters])
        set_flat_weights(self.model, flat_global)
        
        # 2. Parse config flags
        use_dp = config.get("use_dp", "True") == "True"
        use_paillier = config.get("use_paillier", "True") == "True"
        public_key_n = config.get("public_key_n", "")
        
        epochs = int(config.get("local_epochs", 3))
        lr = float(config.get("lr", 0.01))
        
        # Keep copy of old weights to compute the update
        old_weights = get_flat_weights(self.model)
        
        # 3. Local training
        self.model.train()
        
        optimizer = torch.optim.Adam(self.model.parameters(), lr=lr)
        criterion = torch.nn.BCELoss()
        
        privacy_engine = None
        if use_dp:
            noise_mult = float(config.get("dp_noise_multiplier", 1.1))
            max_grad = float(config.get("dp_max_grad_norm", 1.0))
            self.model, optimizer, train_loader, privacy_engine = make_private_training(
                self.model, optimizer, self.train_loader, noise_multiplier=noise_mult, max_grad_norm=max_grad
            )
        else:
            train_loader = self.train_loader
            
        start_time = time.perf_counter()
        
        for epoch in range(epochs):
            for X_batch, y_batch in train_loader:
                X_batch, y_batch = X_batch.to(self.device), y_batch.to(self.device)
                optimizer.zero_grad()
                outputs = self.model(X_batch)
                loss = criterion(outputs, y_batch)
                loss.backward()
                optimizer.step()
                
        training_latency = time.perf_counter() - start_time
        
        if use_dp and privacy_engine is not None:
            new_weights = get_flat_weights(self.model)
            epsilon = get_privacy_spent(privacy_engine)
        else:
            new_weights = get_flat_weights(self.model)
            epsilon = 0.0
            
        # Compute update (difference)
        weight_update = new_weights - old_weights
        
        # 4. Encryption
        metrics = {
            "training_latency": training_latency,
            "epsilon": epsilon,
            "school_name": self.school_name
        }
        
        if use_paillier:
            if not public_key_n:
                raise ValueError("Paillier is enabled but public_key_n was not provided in config.")
            
            # Encrypt updates
            pub_key = deserialize_public_key(public_key_n)
            start_encrypt = time.perf_counter()
            encrypted_update = encrypt_weights(pub_key, weight_update)
            encrypt_latency = time.perf_counter() - start_encrypt
            
            # Serialize encrypted update to JSON
            serialized = serialize_encrypted(encrypted_update)
            metrics["encrypted_update"] = json.dumps(serialized)
            metrics["encryption_latency"] = encrypt_latency
            metrics["is_encrypted"] = "True"
        else:
            metrics["plaintext_update"] = json.dumps(weight_update.tolist())
            metrics["encryption_latency"] = 0.0
            metrics["is_encrypted"] = "False"
            
        return self.get_parameters(config), self.num_train, metrics

    def evaluate(self, parameters, config):
        # 0. Check simulated online status from server
        status = get_client_status(self.school_name)
        if status == "Offline":
            print(f"[{self.school_name}] Simulated Network Error: School server is OFFLINE.")
            raise ConnectionError(f"Simulated network dropout for {self.school_name}")

        # 1. Update model weights
        flat_global = np.concatenate([p.flatten() for p in parameters])
        set_flat_weights(self.model, flat_global)
        
        # 2. Evaluate model
        self.model.eval()
        criterion = torch.nn.BCELoss()
        
        total_loss = 0.0
        all_preds = []
        all_targets = []
        
        with torch.no_grad():
            for X_batch, y_batch in self.test_loader:
                X_batch, y_batch = X_batch.to(self.device), y_batch.to(self.device)
                outputs = self.model(X_batch)
                loss = criterion(outputs, y_batch)
                total_loss += loss.item() * len(X_batch)
                
                preds = (outputs >= 0.5).float().cpu().numpy()
                all_preds.extend(preds)
                all_targets.extend(y_batch.cpu().numpy())
                
        avg_loss = total_loss / self.num_test
        accuracy = np.mean(np.array(all_preds) == np.array(all_targets))
        f1 = f1_score(all_targets, all_preds, average="macro", zero_division=0)
        
        print(f"[{self.school_name}] Evaluation - Loss: {avg_loss:.4f}, Accuracy: {accuracy:.4f}, F1-score: {f1:.4f}")
        
        return float(avg_loss), self.num_test, {
            "accuracy": float(accuracy),
            "f1_score": float(f1),
            "school_name": self.school_name
        }
