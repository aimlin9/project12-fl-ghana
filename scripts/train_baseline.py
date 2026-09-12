"""
Centralised Baseline Training Script
=====================================
Trains the same MLP architecture on fully pooled data from all school nodes.
Computes F1-score, Accuracy, and AUC-ROC as the centralised baseline for
comparing against federated performance (Objective 1).

Usage:
    python scripts/train_baseline.py
"""
import os
import sys
import json
import sqlite3
import numpy as np
import torch
from sklearn.metrics import f1_score, accuracy_score, roc_auc_score

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    # Windows consoles often default to a legacy codepage that can't render
    # the em-dashes used in this script's output.
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from client.model import get_model


def load_all_data(db_dir="data/partitions", test_split=0.2, seed=42):
    """Load and pool data from all school SQLite databases."""
    all_X = []
    all_y = []

    for f in sorted(os.listdir(db_dir)):
        if not f.endswith(".db"):
            continue

        school = f.replace(".db", "")
        db_path = os.path.join(db_dir, f)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT attendance_rate, quiz_score, assignment_submission_rate,
                   login_frequency, days_since_last_activity, course_difficulty,
                   prior_score, engagement_index, at_risk
            FROM students
        """)
        records = cursor.fetchall()
        conn.close()

        data = np.array(records, dtype=np.float32)
        X = data[:, :-1]
        y = data[:, -1:]

        # Normalise identically to client/database.py
        X[:, 1] /= 100.0   # quiz_score
        X[:, 3] /= 30.0    # login_frequency
        X[:, 4] /= 60.0    # days_since_last_activity
        X[:, 5] /= 5.0     # course_difficulty
        X[:, 6] /= 100.0   # prior_score
        X[:, 7] /= 100.0   # engagement_index

        all_X.append(X)
        all_y.append(y)
        print(f"  Loaded {len(X)} records from {school}")

    X = np.concatenate(all_X)
    y = np.concatenate(all_y)

    # Shuffle with fixed seed for reproducibility
    np.random.seed(seed)
    indices = np.arange(len(X))
    np.random.shuffle(indices)
    X, y = X[indices], y[indices]

    split = int(len(X) * (1.0 - test_split))
    return X[:split], y[:split], X[split:], y[split:]


def train_baseline(seed=42, save=True, verbose=True):
    """Train centralised baseline and save results.

    seed controls both the train/test shuffle and Adam/init randomness elsewhere
    in the run — used by scripts/statistical_comparison.py to produce independent
    (centralised, federated) F1 pairs for the paired significance test.
    """
    if verbose:
        print("=" * 60)
        print("CENTRALISED BASELINE TRAINING")
        print("=" * 60)

    torch.manual_seed(seed)
    X_train, y_train, X_test, y_test = load_all_data(seed=seed)
    if verbose:
        print(f"\nPooled dataset: {len(X_train)} train, {len(X_test)} test samples")

    # Convert to tensors
    X_train_t = torch.tensor(X_train)
    y_train_t = torch.tensor(y_train)
    X_test_t = torch.tensor(X_test)
    y_test_t = torch.tensor(y_test)

    train_ds = torch.utils.data.TensorDataset(X_train_t, y_train_t)
    train_loader = torch.utils.data.DataLoader(train_ds, batch_size=32, shuffle=True)

    num_pos = float(y_train_t.sum())
    num_neg = float(len(y_train_t) - num_pos)
    pos_weight = torch.tensor([num_neg / max(num_pos, 1.0)])

    model = get_model()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    criterion = torch.nn.BCEWithLogitsLoss(pos_weight=pos_weight)

    # 50 FL rounds × 3 local epochs per round = 150 total epochs
    total_epochs = 50 * 3
    if verbose:
        print(f"\nTraining for {total_epochs} epochs (50 rounds × 3 local epochs)...\n")

    for epoch in range(total_epochs):
        model.train()
        for X_batch, y_batch in train_loader:
            optimizer.zero_grad()
            outputs = model(X_batch)
            loss = criterion(outputs, y_batch)
            loss.backward()
            optimizer.step()

        if verbose and ((epoch + 1) % 30 == 0 or epoch == 0):
            model.eval()
            with torch.no_grad():
                logits = model(X_test_t)
                test_loss = criterion(logits, y_test_t).item()
                pred_labels = (torch.sigmoid(logits) >= 0.5).float().numpy()
                f1 = f1_score(y_test, pred_labels, average="macro", zero_division=0)
                acc = accuracy_score(y_test, pred_labels)
            print(f"  Epoch {epoch+1:>3}/{total_epochs} — Loss: {test_loss:.4f}  Acc: {acc:.4f}  F1: {f1:.4f}")

    # Final evaluation
    model.eval()
    with torch.no_grad():
        logits = model(X_test_t)
        pred_probs = torch.sigmoid(logits).numpy()
        pred_labels = (pred_probs >= 0.5).astype(float)

    f1 = f1_score(y_test, pred_labels, average="macro", zero_division=0)
    acc = accuracy_score(y_test, pred_labels)
    try:
        auc = roc_auc_score(y_test, pred_probs)
    except ValueError:
        auc = 0.0

    if verbose:
        print(f"\n{'=' * 60}")
        print(f"  F1-score (macro) : {f1:.4f}")
        print(f"  Accuracy         : {acc:.4f}")
        print(f"  AUC-ROC          : {auc:.4f}")
        print(f"{'=' * 60}")

    results = {
        "model": "StudentMLP",
        "architecture": "8 -> 64 (ReLU) -> 32 (ReLU) -> 1 (logit, BCEWithLogitsLoss)",
        "seed": seed,
        "train_samples": int(len(X_train)),
        "test_samples": int(len(X_test)),
        "total_epochs": total_epochs,
        "optimizer": "Adam",
        "learning_rate": 0.01,
        "batch_size": 32,
        "f1_score_macro": round(float(f1), 4),
        "accuracy": round(float(acc), 4),
        "auc_roc": round(float(auc), 4),
    }

    if save:
        os.makedirs("results", exist_ok=True)
        with open("results/baseline_metrics.json", "w") as f:
            json.dump(results, f, indent=2)
        if verbose:
            print(f"\nResults saved to results/baseline_metrics.json")

    return results


if __name__ == "__main__":
    train_baseline()
