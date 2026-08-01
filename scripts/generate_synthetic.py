"""
Synthetic Data Generation with CTGAN (Proposal D2)
====================================================
Trains a CTGAN model on OULAD-partitioned school data to generate synthetic
minority-class (at_risk=1) records for class-imbalance augmentation.

Validation: KS test (p > 0.05) required on all features before data is used.

Usage:
    python scripts/generate_synthetic.py --school school_alpha --samples 300
    python scripts/generate_synthetic.py --all --samples 200
"""
import argparse
import os
import sys
import sqlite3

import numpy as np
import pandas as pd
from scipy.stats import ks_2samp

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


FEATURE_COLS = [
    "attendance_rate",
    "quiz_score",
    "assignment_submission_rate",
    "login_frequency",
    "days_since_last_activity",
    "course_difficulty",
    "prior_score",
    "engagement_index",
    "at_risk",
]

SCHOOLS = ["school_alpha", "school_beta", "school_gamma", "school_delta", "school_epsilon"]


def load_school_df(school_name, db_dir="data/partitions"):
    db_path = os.path.join(db_dir, f"{school_name}.db")
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query(
        f"SELECT {', '.join(FEATURE_COLS)} FROM students", conn
    )
    conn.close()
    return df


def validate_synthetic(real_df, synthetic_df, alpha=0.05):
    """Run KS test on each feature. Return True if all p-values > alpha."""
    results = {}
    passed = True
    for col in FEATURE_COLS:
        stat, p_val = ks_2samp(real_df[col].values, synthetic_df[col].values)
        results[col] = {"ks_stat": round(stat, 4), "p_value": round(p_val, 4), "pass": p_val > alpha}
        if p_val <= alpha:
            passed = False
    return passed, results


def save_synthetic(synthetic_df, school_name, output_dir="data/synthetic"):
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, f"SYNTHETIC_{school_name}.csv")
    synthetic_df.to_csv(out_path, index=False)
    print(f"  Saved {len(synthetic_df)} synthetic records -> {out_path}")
    return out_path


def generate_for_school(school_name, num_samples=300, db_dir="data/partitions"):
    print(f"\n{'=' * 55}")
    print(f"  CTGAN synthesis for: {school_name}")
    print(f"{'=' * 55}")

    try:
        from ctgan import CTGAN
    except ImportError:
        print("  ERROR: ctgan package not installed. Run: pip install 'ctgan>=0.7.4'")
        return None

    real_df = load_school_df(school_name, db_dir)
    minority = real_df[real_df["at_risk"] == 1]
    print(f"  Real records: {len(real_df)} total, {len(minority)} at_risk=1")

    # Train CTGAN on minority class only for targeted augmentation
    ctgan = CTGAN(epochs=300, verbose=False)
    discrete_cols = ["at_risk", "course_difficulty"]
    ctgan.fit(minority, discrete_cols)

    synthetic_df = ctgan.sample(num_samples)
    # Clip values to realistic ranges
    synthetic_df["attendance_rate"]           = synthetic_df["attendance_rate"].clip(0.0, 1.0)
    synthetic_df["quiz_score"]                = synthetic_df["quiz_score"].clip(0.0, 100.0)
    synthetic_df["assignment_submission_rate"] = synthetic_df["assignment_submission_rate"].clip(0.0, 1.0)
    synthetic_df["login_frequency"]           = synthetic_df["login_frequency"].clip(0, 30)
    synthetic_df["days_since_last_activity"]  = synthetic_df["days_since_last_activity"].clip(0, 60)
    synthetic_df["course_difficulty"]         = synthetic_df["course_difficulty"].clip(1, 5).round()
    synthetic_df["prior_score"]               = synthetic_df["prior_score"].clip(0.0, 100.0)
    synthetic_df["engagement_index"]          = synthetic_df["engagement_index"].clip(0.0, 100.0)
    synthetic_df["at_risk"]                   = 1  # Force minority class label

    passed, ks_results = validate_synthetic(minority, synthetic_df)

    print(f"\n  KS Test Results (threshold p > 0.05):")
    for col, res in ks_results.items():
        mark = "PASS" if res["pass"] else "FAIL"
        print(f"    [{mark}] {col:35s}  stat={res['ks_stat']:.4f}  p={res['p_value']:.4f}")

    if not passed:
        print("\n  WARNING: Some features failed KS test. Synthetic data NOT saved.")
        print("  Consider increasing CTGAN epochs or reducing num_samples.")
        return None

    print(f"\n  All KS tests passed — synthetic data is distribution-compatible.")
    return save_synthetic(synthetic_df, school_name)


def main():
    parser = argparse.ArgumentParser(description="Generate CTGAN synthetic student data")
    parser.add_argument("--school", type=str, default=None, help="School name (e.g. school_alpha)")
    parser.add_argument("--all", action="store_true", help="Generate for all schools")
    parser.add_argument("--samples", type=int, default=300, help="Number of synthetic samples per school")
    parser.add_argument("--db-dir", type=str, default="data/partitions")
    args = parser.parse_args()

    if args.all:
        targets = [s for s in SCHOOLS if os.path.exists(os.path.join(args.db_dir, f"{s}.db"))]
    elif args.school:
        targets = [args.school]
    else:
        parser.print_help()
        sys.exit(1)

    results = {}
    for school in targets:
        path = generate_for_school(school, num_samples=args.samples, db_dir=args.db_dir)
        results[school] = "saved" if path else "failed_ks_test"

    print(f"\n{'=' * 55}")
    print("Summary:")
    for school, status in results.items():
        print(f"  {school:30s} -> {status}")


if __name__ == "__main__":
    main()
