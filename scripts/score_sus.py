"""
SUS Usability Scorer (Proposal D2/E1, Visual #6)
====================================================
Scores a Google Forms CSV export of the System Usability Scale (SUS,
Brooke 1996) questionnaire — see sus_study/sus_questionnaire.md for the
10-item instrument this expects.

Standard SUS scoring:
    Odd items  (1,3,5,7,9):  contribution = response - 1
    Even items (2,4,6,8,10): contribution = 5 - response
    SUS score = sum(contributions) * 2.5      -> 0-100 scale per participant

A score >= 68 is considered "above average"; this project's target is >= 70
("Good", per the standard SUS adjective scale), matching Proposal E3 #5.

Usage:
    python scripts/score_sus.py path/to/google_form_export.csv

Expects a CSV with one row per participant and (at least) 10 numeric columns
(1-5) for the 10 SUS items, in the order given in sus_questionnaire.md. A
leading "Timestamp" column (Google Forms' default) is fine — it's ignored.
If there are more than 10 numeric columns, the script uses the LAST 10
(assumes any earlier ones are metadata, not survey items).
"""
import argparse
import csv
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.generate_charts import apply_style, save, RESULTS_DIR  # reuse the shared dark chart style

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

TARGET_SUS = 70.0


def load_responses(csv_path):
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))

    header, data_rows = rows[0], rows[1:]

    # Find numeric columns per row; use the last 10 numeric values in each row
    # as the 10 SUS item responses (handles a leading Timestamp/metadata column).
    responses = []
    for row in data_rows:
        if not row or not any(cell.strip() for cell in row):
            continue
        numeric_vals = []
        for cell in row:
            try:
                v = float(cell.strip())
                numeric_vals.append(v)
            except (ValueError, AttributeError):
                continue
        if len(numeric_vals) < 10:
            print(f"  WARNING: skipping row with only {len(numeric_vals)} numeric values: {row}")
            continue
        responses.append(numeric_vals[-10:])

    return responses


def score_sus(items):
    """items: list of 10 responses (1-5), in question order 1-10."""
    if len(items) != 10:
        raise ValueError(f"Expected 10 items, got {len(items)}")
    total = 0.0
    for i, r in enumerate(items):
        if not (1 <= r <= 5):
            raise ValueError(f"Item {i+1} response {r} out of range 1-5")
        if i % 2 == 0:   # items 1,3,5,7,9 (0-indexed: 0,2,4,6,8) -> odd items
            total += (r - 1)
        else:             # items 2,4,6,8,10 -> even items
            total += (5 - r)
    return total * 2.5


def main():
    parser = argparse.ArgumentParser(description="Score a SUS Google Forms CSV export")
    parser.add_argument("csv_path", help="Path to the exported Google Forms CSV")
    parser.add_argument("--dpi", type=int, default=150)
    args = parser.parse_args()

    responses = load_responses(args.csv_path)
    if not responses:
        print("ERROR: no valid participant rows found in the CSV.", file=sys.stderr)
        sys.exit(1)

    scores = [round(score_sus(r), 2) for r in responses]
    n = len(scores)
    mean_score = float(np.mean(scores))
    median_score = float(np.median(scores))

    print("=" * 55)
    print(f"SUS SCORES  (n={n} participants)")
    print("=" * 55)
    for i, s in enumerate(scores, 1):
        adj = ("Excellent" if s >= 85 else "Good" if s >= 70 else
               "OK" if s >= 50 else "Poor")
        print(f"  Participant {i:>2}: {s:>5.1f}  ({adj})")
    print("-" * 55)
    print(f"  Mean SUS score:   {mean_score:.2f}")
    print(f"  Median SUS score: {median_score:.2f}")
    print(f"  Target (Proposal E3 #5): >= {TARGET_SUS}")
    print(f"  Result: {'PASS — target met' if mean_score >= TARGET_SUS else 'below target'}")
    print("=" * 55)

    os.makedirs(RESULTS_DIR, exist_ok=True)
    out_path = os.path.join(RESULTS_DIR, "sus_scores.json")
    with open(out_path, "w") as f:
        json.dump({
            "n_participants": n,
            "scores": scores,
            "mean": round(mean_score, 2),
            "median": round(median_score, 2),
            "target": TARGET_SUS,
            "meets_target": mean_score >= TARGET_SUS,
        }, f, indent=2)
    print(f"\nResults saved -> {out_path}")

    # Chart: bar per participant + mean line + target reference line
    apply_style()
    fig, ax = plt.subplots(figsize=(8, 5))
    fig.patch.set_facecolor("#0b0f19")

    colors = ["#10b981" if s >= TARGET_SUS else "#f59e0b" if s >= 50 else "#ef4444" for s in scores]
    ax.bar(range(1, n + 1), scores, color=colors, zorder=3)
    ax.axhline(TARGET_SUS, color="#f97316", linestyle="--", linewidth=1.5,
               label=f"Target: SUS = {TARGET_SUS:.0f} (Good)", zorder=2)
    ax.axhline(mean_score, color="#6366f1", linestyle=":", linewidth=1.5,
               label=f"Mean: {mean_score:.1f}", zorder=2)

    ax.set_xlabel("Participant")
    ax.set_ylabel("SUS Score (0-100)")
    ax.set_title(f"Dashboard Usability — SUS Scores (n={n})", pad=14, fontsize=12, fontweight="bold")
    ax.set_xticks(range(1, n + 1))
    ax.set_ylim(0, 100)
    ax.legend(loc="lower right", fontsize=9)
    ax.grid(True, axis="y")

    save(fig, "chart_sus.png", args.dpi)


if __name__ == "__main__":
    main()
