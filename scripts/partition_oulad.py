"""
OULAD Data Partitioning Script
===============================
Partitions data into school-specific SQLite databases for FL simulation.
Matches the reproducibility checklist command:
    python scripts/partition_oulad.py --nodes 3 --output data/partitions/

Usage:
    python scripts/partition_oulad.py --nodes 3 --output data/partitions/
    python scripts/partition_oulad.py --nodes 5 --output data/partitions/
"""
import argparse
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.generate_data import generate_school_data, NUM_RECORDS


# Ordered list of available school node names
SCHOOL_NAMES = ["school_alpha", "school_beta", "school_gamma", "school_delta", "school_epsilon"]


def main():
    parser = argparse.ArgumentParser(
        description="Partition student data into school node SQLite databases for federated learning."
    )
    parser.add_argument(
        "--nodes", type=int, default=3, choices=[3, 4, 5],
        help="Number of school nodes to generate (3–5, default: 3)"
    )
    parser.add_argument(
        "--output", type=str, default="data/partitions/",
        help="Output directory for SQLite databases (default: data/partitions/)"
    )
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)
    schools = SCHOOL_NAMES[: args.nodes]

    print("=" * 60)
    print(f"Partitioning data into {args.nodes} school nodes")
    print(f"Output directory: {os.path.abspath(args.output)}")
    print("=" * 60)

    for school_name in schools:
        num_records = NUM_RECORDS.get(school_name, 500)
        generate_school_data(school_name, num_records, output_dir=args.output)

    print(f"\nDone — {args.nodes} school databases created.")


if __name__ == "__main__":
    main()
