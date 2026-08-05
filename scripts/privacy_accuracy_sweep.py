"""
Privacy-Accuracy Trade-off Sweep (Proposal E1, Visual #3)
===========================================================
Trains the MLP with different DP-SGD noise multipliers and records
epsilon vs F1-score / Accuracy to produce the scatter plot described
in the project proposal.

Results are saved to: results/privacy_accuracy_tradeoff.json

Usage:
    python scripts/privacy_accuracy_sweep.py
    python scripts/privacy_accuracy_sweep.py --rounds 10 --epochs 3
"""
import argparse
import json
import os
import sys

import numpy as np
import torch
from sklearn.metrics import f1_score, accuracy_score, roc_auc_score

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client.model import get_model
from client.database import load_data
from security.privacy import make_private_training, get_privacy_spent


# Noise multiplier → approximate epsilon after 50 rounds
# Higher noise = more privacy (lower epsilon) but lower accuracy
# Extended past 3.0 (the original range) to actually find the point where accuracy
# starts degrading — at sigma<=3.0 the model is robust enough that F1 barely moves,
# which made the trade-off chart look flat rather than showing a real trend.
NOISE_MULTIPLIERS = [0.5, 0.8, 1.0, 1.1, 1.3, 1.5, 2.0, 3.0, 5.0, 8.0, 12.0, 20.0]


def evaluate_model(model, test_loader, device, pos_weight=None):
    model.eval()
    pw = torch.tensor([pos_weight]) if pos_weight else None
    criterion = torch.nn.BCEWithLogitsLoss(pos_weight=pw.to(device) if pw is not None else None)
    total_loss = 0.0
    all_probs, all_preds, all_labels = [], [], []

    with torch.no_grad():
        for X_batch, y_batch in test_loader:
            X_batch, y_batch = X_batch.to(device), y_batch.to(device)
            logits = model(X_batch)
            total_loss += criterion(logits, y_batch).item() * len(X_batch)
            probs  = torch.sigmoid(logits).squeeze(1).cpu().numpy()
            preds  = (probs >= 0.5).astype(float)
            labels = y_batch.squeeze(1).cpu().numpy()
            all_probs.extend(probs.tolist())
            all_preds.extend(preds.tolist())
            all_labels.extend(labels.tolist())

    all_preds  = np.array(all_preds)
    all_labels = np.array(all_labels)
    all_probs  = np.array(all_probs)

    n = max(len(all_labels), 1)
    avg_loss = total_loss / n
    acc      = float(accuracy_score(all_labels, all_preds))
    f1       = float(f1_score(all_labels, all_preds, average="macro", zero_division=0))
    try:
        auc = float(roc_auc_score(all_labels, all_probs))
    except ValueError:
        auc = 0.0
    return avg_loss, acc, f1, auc


def run_sweep(school="school_alpha", num_rounds=10, local_epochs=3, lr=0.01, delta=1e-5):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    train_loader, test_loader, _, _, pos_w = load_data(school)
    pos_w = min(pos_w, 10.0)

    results = []
    print(f"\nPrivacy-Accuracy sweep on {school} — {num_rounds} rounds × {local_epochs} epochs\n")
    print(f"{'Noise sd':>10}  {'Epsilon':>10}  {'Accuracy':>10}  {'F1 (macro)':>12}  {'AUC-ROC':>10}")
    print("-" * 60)

    for noise_mult in NOISE_MULTIPLIERS:
        model     = get_model().to(device)
        optimizer = torch.optim.Adam(model.parameters(), lr=lr)
        pos_weight_t = torch.tensor([pos_w]).to(device)
        criterion = torch.nn.BCEWithLogitsLoss(pos_weight=pos_weight_t)

        model, optimizer, dp_loader, engine = make_private_training(
            model, optimizer, train_loader,
            noise_multiplier=noise_mult, max_grad_norm=1.0
        )

        model.train()
        for _ in range(num_rounds * local_epochs):
            for X_batch, y_batch in dp_loader:
                X_batch, y_batch = X_batch.to(device), y_batch.to(device)
                optimizer.zero_grad()
                logits = model(X_batch)
                loss = criterion(logits, y_batch)
                loss.backward()
                optimizer.step()

        epsilon = get_privacy_spent(engine, delta=delta)
        _, acc, f1, auc = evaluate_model(model, test_loader, device, pos_weight=pos_w)

        print(f"{noise_mult:>10.2f}  {epsilon:>10.4f}  {acc:>10.4f}  {f1:>12.4f}  {auc:>10.4f}")

        results.append({
            "noise_multiplier": noise_mult,
            "epsilon":          round(epsilon, 4),
            "accuracy":         round(acc, 4),
            "f1_score_macro":   round(f1, 4),
            "auc_roc":          round(auc, 4),
            "delta":            delta,
            "num_rounds":       num_rounds,
            "local_epochs":     local_epochs,
        })

    return results


def main():
    parser = argparse.ArgumentParser(description="Privacy-Accuracy trade-off sweep")
    parser.add_argument("--school",  default="school_gamma")
    parser.add_argument("--rounds",  type=int, default=10,  help="FL rounds to simulate per config")
    parser.add_argument("--epochs",  type=int, default=3,   help="Local epochs per round")
    parser.add_argument("--lr",      type=float, default=0.01)
    parser.add_argument("--delta",   type=float, default=1e-5)
    args = parser.parse_args()

    results = run_sweep(
        school=args.school,
        num_rounds=args.rounds,
        local_epochs=args.epochs,
        lr=args.lr,
        delta=args.delta,
    )

    os.makedirs("results", exist_ok=True)
    out_path = "results/privacy_accuracy_tradeoff.json"
    with open(out_path, "w") as f:
        json.dump({"sweep": results}, f, indent=2)

    print(f"\nResults saved -> {out_path}")
    print("Use this data for the privacy-accuracy scatter plot (Proposal E1, Visual #3).")


if __name__ == "__main__":
    main()
