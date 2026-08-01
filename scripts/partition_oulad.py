"""
OULAD Data Partitioning Script (Proposal D2/D4)
==================================================
Partitions the REAL OULAD dataset into school-like node SQLite databases,
split by student registration quarter (code_presentation) — matching the
proposal's D2 dataset plan and D4 experimental design.

OULAD has exactly 4 real registration quarters: 2013B, 2013J, 2014B, 2014J.
    --nodes 3 -> alpha=2013B, beta=2013J, gamma=2014B        (2014J held in reserve)
    --nodes 4 -> alpha=2013B, beta=2013J, gamma=2014B, delta=2014J   (1:1 quarter mapping)
    --nodes 5 -> same as 4, plus 2014J (the largest quarter, 11,260 students) is
                 split by code_module group into delta/epsilon so a genuine 5th
                 non-IID split exists. Documented adaptation: OULAD only has
                 4 real quarters, not 5.

Requires data/oulad_raw/ populated first:
    python scripts/download_oulad.py

Usage:
    python scripts/partition_oulad.py --nodes 3 --output data/partitions/
    python scripts/partition_oulad.py --nodes 5 --output data/partitions/
    python scripts/partition_oulad.py --nodes 3 --synthetic   # fast fully-synthetic dev/demo fallback
"""
import argparse
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.oulad_features import load_oulad_enrollments, FEATURE_COLS

SCHOOL_NAMES = ["school_alpha", "school_beta", "school_gamma", "school_delta", "school_epsilon"]

QUARTER_MAP_3 = {"2013B": "school_alpha", "2013J": "school_beta", "2014B": "school_gamma"}
QUARTER_MAP_4 = {**QUARTER_MAP_3, "2014J": "school_delta"}


def _write_school_db(school_name, rows, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    db_path = os.path.join(output_dir, f"{school_name}.db")
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    conn.execute(f"""
        CREATE TABLE students (
            student_id INTEGER PRIMARY KEY AUTOINCREMENT,
            {', '.join(c + ' REAL' for c in FEATURE_COLS)},
            at_risk INTEGER
        )
    """)
    conn.executemany(
        f"INSERT INTO students ({', '.join(FEATURE_COLS)}, at_risk) "
        f"VALUES ({', '.join('?' for _ in FEATURE_COLS)}, ?)",
        [tuple(r[c] for c in FEATURE_COLS) + (r["at_risk"],) for r in rows],
    )
    conn.commit()

    total, at_risk = conn.execute("SELECT COUNT(*), SUM(at_risk) FROM students").fetchone()
    conn.close()
    pct = (at_risk / total * 100) if total else 0.0
    print(f"  {school_name}: {total} records, {at_risk} at-risk ({pct:.1f}%)")


def partition_real_oulad(nodes, output_dir, raw_dir="data/oulad_raw"):
    if not os.path.exists(os.path.join(raw_dir, "studentInfo.csv")):
        print(f"ERROR: {raw_dir}/studentInfo.csv not found.")
        print("Run: python scripts/download_oulad.py")
        sys.exit(1)

    print("Loading and feature-engineering OULAD enrollments (streams studentVle.csv once)...")
    rows = load_oulad_enrollments(raw_dir)
    print(f"Loaded {len(rows)} enrollments.")

    buckets = {name: [] for name in SCHOOL_NAMES[:nodes]}

    if nodes == 5:
        q_2014j_modules = sorted({r["code_module"] for r in rows if r["code_presentation"] == "2014J"})
        half = max(len(q_2014j_modules) // 2, 1)
        delta_modules = set(q_2014j_modules[:half])
        for r in rows:
            if r["code_presentation"] == "2014J":
                school = "school_delta" if r["code_module"] in delta_modules else "school_epsilon"
            else:
                school = QUARTER_MAP_3.get(r["code_presentation"])
            if school in buckets:
                buckets[school].append(r)
    else:
        quarter_map = QUARTER_MAP_4 if nodes == 4 else QUARTER_MAP_3
        for r in rows:
            school = quarter_map.get(r["code_presentation"])
            if school in buckets:
                buckets[school].append(r)

    print(f"\nPartitioning into {nodes} school nodes by registration quarter:")
    for school_name, school_rows in buckets.items():
        _write_school_db(school_name, school_rows, output_dir)


def partition_synthetic(nodes, output_dir):
    from scripts.generate_data import generate_school_data, NUM_RECORDS
    for school_name in SCHOOL_NAMES[:nodes]:
        num_records = NUM_RECORDS.get(school_name, 500)
        generate_school_data(school_name, num_records, output_dir=output_dir)


def main():
    parser = argparse.ArgumentParser(
        description="Partition the real OULAD dataset into school node SQLite databases for federated learning."
    )
    parser.add_argument(
        "--nodes", type=int, default=3, choices=[3, 4, 5],
        help="Number of school nodes to generate (3-5, default: 3)"
    )
    parser.add_argument(
        "--output", type=str, default="data/partitions/",
        help="Output directory for SQLite databases (default: data/partitions/)"
    )
    parser.add_argument(
        "--raw-dir", type=str, default="data/oulad_raw",
        help="Directory containing the extracted OULAD CSVs (default: data/oulad_raw)"
    )
    parser.add_argument(
        "--synthetic", action="store_true",
        help="Use the fast fully-synthetic generator instead of real OULAD data "
             "(dev/demo fallback that skips the OULAD download)"
    )
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    print("=" * 60)
    print(f"Partitioning data into {args.nodes} school nodes")
    print(f"Output directory: {os.path.abspath(args.output)}")
    print(f"Source: {'SYNTHETIC (fallback)' if args.synthetic else 'real OULAD dataset'}")
    print("=" * 60)

    if args.synthetic:
        partition_synthetic(args.nodes, args.output)
    else:
        partition_real_oulad(args.nodes, args.output, raw_dir=args.raw_dir)

    print(f"\nDone — {args.nodes} school databases created.")


if __name__ == "__main__":
    main()
