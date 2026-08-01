"""
Statistical Significance Test: Federated vs Centralised (Proposal D4)
=========================================================================
The proposal's D4 calls for a paired t-test (Cohen's d effect size, Wilcoxon
signed-rank fallback if normality fails) comparing centralised vs federated
F1-scores "across 5 independent random partitions." Real OULAD only has 4
fixed registration quarters, so there is no way to draw 5 independent RANDOM
school-quarter partitions the way that language assumed for synthetic data.

Instead, this script holds the school/quarter assignment fixed (school_alpha
=2013B, school_beta=2013J, school_gamma=2014B — the same partition_oulad.py
--nodes 3 mapping used everywhere else) and draws 5 independent bootstrap
resamples of the train/test split + training randomness (different seeds).
For each seed it trains both a centralised baseline and a federated 3-node
model on real OULAD data, producing 5 paired (centralised F1, federated F1)
observations for the significance test.

DP-SGD and Paillier are left OFF for this comparison: Objective 1 (the F1
parity claim this test evaluates) is specifically about FedAvg vs centralised
accuracy: the privacy-mechanism cost is Objective 2's concern, tested
separately by privacy_accuracy_sweep.py.

Usage:
    python scripts/statistical_comparison.py --seeds 5 --rounds 50
"""
import argparse
import json
import os
import sys

import numpy as np
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.train_baseline import train_baseline
from scripts.run_fl_simulation import run_simulation


def run_one_seed(seed, rounds, nodes, lr, epochs):
    print(f"\n{'#' * 60}")
    print(f"  SEED {seed}")
    print(f"{'#' * 60}")

    print(f"\n[{seed}] Training centralised baseline...")
    baseline_result = train_baseline(seed=seed, save=False, verbose=False)
    centralised_f1 = baseline_result["f1_score_macro"]
    print(f"[{seed}] Centralised F1: {centralised_f1:.4f}")

    print(f"\n[{seed}] Running federated simulation ({rounds} rounds, {nodes} nodes, no DP/Paillier)...")
    fed_result = run_simulation(
        rounds=rounds, nodes=nodes, use_dp=False, use_paillier=False,
        lr=lr, epochs=epochs, seed=seed,
    )
    federated_f1 = fed_result["f1_score"] if fed_result else None
    print(f"[{seed}] Federated F1:   {federated_f1:.4f}" if federated_f1 is not None else
          f"[{seed}] WARNING: no federated result recorded")

    return centralised_f1, federated_f1


def main():
    parser = argparse.ArgumentParser(description="Federated vs centralised statistical comparison")
    parser.add_argument("--seeds",  type=int, default=5, help="Number of independent bootstrap seeds (default: 5)")
    parser.add_argument("--rounds", type=int, default=50, help="FL rounds per seed (default: 50, matches D4)")
    parser.add_argument("--nodes",  type=int, default=3)
    parser.add_argument("--lr",     type=float, default=0.01)
    parser.add_argument("--epochs", type=int, default=3, help="Local epochs per round")
    args = parser.parse_args()

    seeds = [42 + i for i in range(args.seeds)]
    centralised_f1s, federated_f1s = [], []

    for seed in seeds:
        c_f1, f_f1 = run_one_seed(seed, args.rounds, args.nodes, args.lr, args.epochs)
        centralised_f1s.append(c_f1)
        federated_f1s.append(f_f1)

    if any(f is None for f in federated_f1s):
        print("\nERROR: one or more seeds produced no federated result — aborting statistical test.")
        sys.exit(1)

    centralised_f1s = np.array(centralised_f1s)
    federated_f1s = np.array(federated_f1s)
    diffs = centralised_f1s - federated_f1s

    # Paired t-test
    t_stat, t_pvalue = stats.ttest_rel(centralised_f1s, federated_f1s)

    # Cohen's d for paired samples: mean difference / std of differences
    cohens_d = float(np.mean(diffs) / np.std(diffs, ddof=1)) if np.std(diffs, ddof=1) > 0 else 0.0

    # Shapiro-Wilk normality test on the differences (D4: decides t-test vs Wilcoxon)
    shapiro_stat, shapiro_p = stats.shapiro(diffs)
    normal = bool(shapiro_p > 0.05)

    # Wilcoxon signed-rank as the non-parametric fallback
    try:
        wilcoxon_stat, wilcoxon_p = stats.wilcoxon(centralised_f1s, federated_f1s)
    except ValueError as e:
        wilcoxon_stat, wilcoxon_p = None, None
        print(f"\nWilcoxon test not computable: {e}")

    print(f"\n{'=' * 60}")
    print("STATISTICAL COMPARISON — Federated vs Centralised F1")
    print(f"{'=' * 60}")
    print(f"  Seeds:                {seeds}")
    print(f"  Centralised F1s:      {[round(float(x), 4) for x in centralised_f1s]}")
    print(f"  Federated F1s:        {[round(float(x), 4) for x in federated_f1s]}")
    print(f"  Mean diff (cen-fed):  {np.mean(diffs):.4f}")
    print(f"  Paired t-test:        t={t_stat:.4f}, p={t_pvalue:.4f}")
    print(f"  Cohen's d:            {cohens_d:.4f}")
    print(f"  Shapiro-Wilk normality: W={shapiro_stat:.4f}, p={shapiro_p:.4f} "
          f"({'normal' if normal else 'NOT normal — use Wilcoxon result'})")
    if wilcoxon_stat is not None:
        print(f"  Wilcoxon signed-rank: W={wilcoxon_stat:.4f}, p={wilcoxon_p:.4f}")
    print(f"{'=' * 60}")

    recommended = "paired t-test" if normal else "Wilcoxon signed-rank"
    recommended_p = t_pvalue if normal else wilcoxon_p
    print(f"\n  Recommended test (per D4 decision rule): {recommended}")
    if recommended_p is not None:
        print(f"  Result: {'statistically significant difference' if recommended_p < 0.05 else 'no statistically significant difference'} "
              f"(alpha=0.05, p={recommended_p:.4f})")

    results = {
        "seeds": seeds,
        "centralised_f1": [round(float(x), 4) for x in centralised_f1s],
        "federated_f1": [round(float(x), 4) for x in federated_f1s],
        "mean_diff": round(float(np.mean(diffs)), 4),
        "paired_ttest": {"t_stat": round(float(t_stat), 4), "p_value": round(float(t_pvalue), 4)},
        "cohens_d": round(cohens_d, 4),
        "shapiro_wilk": {"stat": round(float(shapiro_stat), 4), "p_value": round(float(shapiro_p), 4), "normal": normal},
        "wilcoxon": (
            {"stat": round(float(wilcoxon_stat), 4), "p_value": round(float(wilcoxon_p), 4)}
            if wilcoxon_stat is not None else None
        ),
        "recommended_test": recommended,
        "config": {"rounds": args.rounds, "nodes": args.nodes, "lr": args.lr, "local_epochs": args.epochs,
                   "use_dp": False, "use_paillier": False},
    }

    os.makedirs("results", exist_ok=True)
    out_path = "results/statistical_comparison.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved -> {out_path}")


if __name__ == "__main__":
    main()
