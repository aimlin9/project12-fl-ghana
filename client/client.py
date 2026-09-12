import os
import flwr as fl
import torch
import numpy as np
import json
import time
import urllib.request
from sklearn.metrics import f1_score, roc_auc_score, balanced_accuracy_score, roc_curve

from client.model import get_model
from client.database import load_data
from security.crypto import deserialize_public_key, encrypt_weights, serialize_encrypted
from security.privacy import make_private_training, get_privacy_spent

# In docker-compose each school runs in its own container while FastAPI runs in
# the separate "server" container, so 127.0.0.1 (this container's own loopback)
# never reaches it — docker-compose.yml sets DASHBOARD_API_URL=http://server:8000
# for that case. Same-host runs (CLI or dashboard-launched) keep the default.
DASHBOARD_API_URL = os.environ.get("DASHBOARD_API_URL", "http://127.0.0.1:8000")


def get_flat_weights(model):
    params = []
    with torch.no_grad():
        for param in model.parameters():
            params.append(param.cpu().numpy().flatten())
    return np.concatenate(params)


def set_flat_weights(model, flat_weights):
    idx = 0
    with torch.no_grad():
        for param in model.parameters():
            shape = param.shape
            size = param.numel()
            w = torch.tensor(flat_weights[idx:idx + size], dtype=torch.float32).reshape(shape)
            param.copy_(w)
            idx += size


def get_client_status(school_name):
    try:
        url = f"{DASHBOARD_API_URL}/api/client/{school_name}/status"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=0.5) as response:
            data = json.loads(response.read().decode())
            return data.get("status", "Idle")
    except Exception:
        return "Idle"


class StudentFLClient(fl.client.NumPyClient):
    def __init__(self, school_name, db_dir="data/partitions", batch_size=32, seed=42):
        self.school_name = school_name
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = get_model().to(self.device)
        self.train_loader, self.test_loader, self.num_train, self.num_test, pos_w = load_data(
            school_name, db_dir=db_dir, batch_size=batch_size, seed=seed
        )
        self.pos_weight = torch.tensor([pos_w], dtype=torch.float32)
        # Track whether the model has already been wrapped by Opacus
        self._dp_wrapped = False
        self._privacy_engine = None
        self._dp_train_loader = None   # Opacus Poisson-sampled loader (saved after Round 1)
        print(f"[{self.school_name}] Initialized with {self.num_train} train / {self.num_test} test samples.")

    def _post_epoch_accuracy(self):
        """Evaluate on test set after each epoch and POST result to dashboard."""
        probs_list, targets_list = [], []
        with torch.no_grad():
            for X_b, y_b in self.test_loader:
                logits = self.model(X_b.to(self.device))
                probs = torch.sigmoid(logits).squeeze(1).cpu().numpy()
                probs_list.extend(probs.tolist())
                targets_list.extend(y_b.squeeze(1).numpy().tolist())
        targets_arr = np.array(targets_list)
        probs_arr   = np.array(probs_list)
        if len(np.unique(targets_arr)) > 1:
            fpr, tpr, thresh = roc_curve(targets_arr, probs_arr)
            threshold = float(thresh[int(np.argmax(tpr - fpr))])
        else:
            threshold = 0.25
        preds = (probs_arr >= threshold).tolist()
        acc = float(balanced_accuracy_score(targets_arr, preds))
        try:
            data = json.dumps({"accuracy": acc, "school": self.school_name}).encode()
            req = urllib.request.Request(
                f"{DASHBOARD_API_URL}/api/progress", data=data,
                headers={"Content-Type": "application/json"}, method="POST"
            )
            urllib.request.urlopen(req, timeout=0.5)
        except Exception:
            pass

    def get_parameters(self, config):
        return [p.detach().cpu().numpy() for p in self.model.parameters()]

    def fit(self, parameters, config):
        status = get_client_status(self.school_name)
        if status == "Offline":
            print(f"[{self.school_name}] Simulated Network Error: School server is OFFLINE.")
            raise ConnectionError(f"Simulated network dropout for {self.school_name}")

        # Load global weights into model
        flat_global = np.concatenate([p.flatten() for p in parameters])
        set_flat_weights(self.model, flat_global)

        use_dp      = config.get("use_dp", "True") == "True"
        use_paillier = config.get("use_paillier", "True") == "True"
        public_key_n = config.get("public_key_n", "")
        epochs      = int(config.get("local_epochs", 3))
        lr          = float(config.get("lr", 0.01))
        noise_mult  = float(config.get("dp_noise_multiplier", 1.1))
        max_grad    = float(config.get("dp_max_grad_norm", 1.0))

        old_weights = get_flat_weights(self.model)

        self.model.train()
        optimizer = torch.optim.Adam(self.model.parameters(), lr=lr)
        criterion = torch.nn.BCEWithLogitsLoss(pos_weight=self.pos_weight.to(self.device))

        if use_dp:
            if not self._dp_wrapped:
                # Wrap the model with Opacus exactly once
                self.model, optimizer, train_loader, self._privacy_engine = make_private_training(
                    self.model, optimizer, self.train_loader,
                    noise_multiplier=noise_mult, max_grad_norm=max_grad
                )
                self._dp_train_loader = train_loader  # Save Poisson-sampled loader for future rounds
                self._dp_wrapped = True
            else:
                # Round 2+: must reuse the Opacus Poisson DataLoader and a DPOptimizer;
                # the GradSampleModule's forbid_accumulation_hook requires Poisson batches.
                from opacus.optimizers import DPOptimizer
                train_loader = self._dp_train_loader
                base_opt = torch.optim.Adam(self.model.parameters(), lr=lr)
                try:
                    sr = self._dp_train_loader.batch_sampler.sample_rate
                    expected_bs = max(1, round(sr * len(self._dp_train_loader.dataset)))
                except AttributeError:
                    expected_bs = 32
                optimizer = DPOptimizer(
                    optimizer=base_opt,
                    noise_multiplier=noise_mult,
                    max_grad_norm=max_grad,
                    expected_batch_size=expected_bs,
                )
        else:
            train_loader = self.train_loader

        start_time = time.perf_counter()

        for _ in range(epochs):
            for X_batch, y_batch in train_loader:
                X_batch = X_batch.to(self.device)
                y_batch = y_batch.to(self.device)
                optimizer.zero_grad()
                outputs = self.model(X_batch)
                loss = criterion(outputs, y_batch)
                loss.backward()
                optimizer.step()
            self._post_epoch_accuracy()

        training_latency = time.perf_counter() - start_time

        new_weights = get_flat_weights(self.model)
        epsilon = get_privacy_spent(self._privacy_engine) if (use_dp and self._privacy_engine) else 0.0
        weight_update = new_weights - old_weights

        metrics = {
            "training_latency": training_latency,
            "epsilon":          epsilon,
            "school_name":      self.school_name,
        }

        if use_paillier:
            if not public_key_n:
                raise ValueError("Paillier enabled but public_key_n was not provided in config.")
            pub_key = deserialize_public_key(public_key_n)
            start_enc = time.perf_counter()
            encrypted_update = encrypt_weights(pub_key, weight_update)
            metrics["encryption_latency"] = time.perf_counter() - start_enc
            metrics["encrypted_update"]   = json.dumps(serialize_encrypted(encrypted_update))
            metrics["is_encrypted"]       = "True"
        else:
            metrics["plaintext_update"]   = json.dumps(weight_update.tolist())
            metrics["encryption_latency"] = 0.0
            metrics["is_encrypted"]       = "False"

        return self.get_parameters(config), self.num_train, metrics

    def evaluate(self, parameters, config):
        status = get_client_status(self.school_name)
        if status == "Offline":
            print(f"[{self.school_name}] Simulated Network Error: School server is OFFLINE.")
            raise ConnectionError(f"Simulated network dropout for {self.school_name}")

        flat_global = np.concatenate([p.flatten() for p in parameters])
        set_flat_weights(self.model, flat_global)

        self.model.eval()
        criterion = torch.nn.BCEWithLogitsLoss(pos_weight=self.pos_weight.to(self.device))

        total_loss = 0.0
        all_probs   = []
        all_targets = []

        with torch.no_grad():
            for X_batch, y_batch in self.test_loader:
                X_batch = X_batch.to(self.device)
                y_batch = y_batch.to(self.device)
                logits = self.model(X_batch)                          # raw logit, shape (batch, 1)
                loss = criterion(logits, y_batch)
                total_loss += loss.item() * len(X_batch)

                # Apply sigmoid to convert logit → probability
                probs  = torch.sigmoid(logits).squeeze(1).cpu().numpy()   # (batch,)
                labels = y_batch.squeeze(1).cpu().numpy()                  # (batch,)

                all_probs.extend(probs.tolist())
                all_targets.extend(labels.tolist())

        num_test = max(self.num_test, len(all_targets))
        avg_loss = total_loss / num_test if num_test > 0 else 0.0

        all_targets = np.array(all_targets)
        all_probs   = np.array(all_probs)

        # Find optimal threshold via Youden's J (maximises sensitivity + specificity)
        if len(np.unique(all_targets)) > 1:
            fpr, tpr, thresholds = roc_curve(all_targets, all_probs)
            optimal_idx = int(np.argmax(tpr - fpr))
            threshold = float(thresholds[optimal_idx])
        else:
            threshold = 0.25
        all_preds = (all_probs >= threshold).astype(float)

        accuracy = float(balanced_accuracy_score(all_targets, all_preds))
        f1       = float(f1_score(all_targets, all_preds, average="macro", zero_division=0))

        try:
            auc_roc = float(roc_auc_score(all_targets, all_probs))
        except ValueError:
            auc_roc = 0.0

        print(f"[{self.school_name}] Eval — Loss: {avg_loss:.4f}, Acc: {accuracy:.4f}, "
              f"F1: {f1:.4f}, AUC: {auc_roc:.4f}")

        return float(avg_loss), num_test, {
            "accuracy":     accuracy,
            "f1_score":     f1,
            "auc_roc":      auc_roc,
            "school_name":  self.school_name,
        }
