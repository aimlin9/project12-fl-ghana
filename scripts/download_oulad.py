"""
OULAD Raw Dataset Downloader (Proposal D2)
=============================================
Downloads and extracts the real Open University Learning Analytics Dataset (OULAD)
into data/oulad_raw/. This is a one-time setup step required before
scripts/partition_oulad.py can build real school-node databases.

As of this writing, the OU has retired public direct-download access to OULAD —
both the original host (analyse.kmi.open.ac.uk) and its successor
(research.stem.open.ac.uk) now only serve an "OU staff access" landing page, with
no public dataset URL. If OULAD download links change again in the future, update
OULAD_URL below. Until then, this script will fail fast with a clear message —
use `python scripts/partition_oulad.py --synthetic` instead, which needs no
download and produces the same school-partition schema.

Usage:
    python scripts/download_oulad.py
    python scripts/download_oulad.py --output data/oulad_raw
"""
import argparse
import os
import sys
import urllib.request
import urllib.error
import zipfile

OULAD_URL = "http://schools.stem.open.ac.uk/cdn/files/anonymisedData.zip"
SYNTHETIC_FALLBACK_HINT = (
    "OULAD is not publicly downloadable right now — the OU's dataset host "
    "currently redirects to a staff-only landing page with no public zip link.\n"
    "Use the synthetic fallback instead, which needs no download:\n"
    "    python scripts/partition_oulad.py --nodes 3 --output data/partitions/ --synthetic"
)
EXPECTED_STUDENT_INFO_ROWS = 32593
REQUIRED_FILES = [
    "courses.csv", "studentInfo.csv", "studentRegistration.csv",
    "assessments.csv", "studentAssessment.csv", "studentVle.csv", "vle.csv",
]


def download_with_resume(url, dest_path, max_attempts=8, chunk_timeout=90):
    """Download url to dest_path, resuming with HTTP Range requests on stalls.

    The OULAD host has been observed to cut off long-lived single-shot downloads
    partway through, so this fetches in a resumable retry loop rather than one
    urlopen() call.
    """
    for attempt in range(1, max_attempts + 1):
        existing = os.path.getsize(dest_path) if os.path.exists(dest_path) else 0
        req = urllib.request.Request(url)
        if existing:
            req.add_header("Range", f"bytes={existing}-")

        try:
            with urllib.request.urlopen(req, timeout=chunk_timeout) as resp:
                mode = "ab" if existing else "wb"
                with open(dest_path, mode) as f:
                    while True:
                        chunk = resp.read(1024 * 1024)
                        if not chunk:
                            break
                        f.write(chunk)
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            print(f"  [attempt {attempt}] interrupted ({e}) at "
                  f"{os.path.getsize(dest_path) if os.path.exists(dest_path) else 0} bytes — retrying...")
            continue

        # Verify we actually have a complete, valid zip
        if zipfile.is_zipfile(dest_path):
            return True
        print(f"  [attempt {attempt}] incomplete after this pass — retrying...")

    return False


def main():
    parser = argparse.ArgumentParser(description="Download and extract the real OULAD dataset")
    parser.add_argument("--output", type=str, default="data/oulad_raw",
                         help="Output directory for extracted CSVs (default: data/oulad_raw)")
    parser.add_argument("--force", action="store_true", help="Re-download even if files already exist")
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)
    zip_path = os.path.join(args.output, "anonymisedData.zip")

    already_have_all = all(
        os.path.exists(os.path.join(args.output, f)) for f in REQUIRED_FILES
    )
    if already_have_all and not args.force:
        print(f"OULAD CSVs already present in {args.output} — use --force to re-download.")
        return

    print(f"Downloading OULAD dataset from {OULAD_URL}")
    print(f"  -> {zip_path}")
    ok = download_with_resume(OULAD_URL, zip_path)
    if not ok:
        print("ERROR: Failed to download a complete zip after all retries.", file=sys.stderr)
        print(f"\n{SYNTHETIC_FALLBACK_HINT}", file=sys.stderr)
        sys.exit(1)

    print("Extracting...")
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(args.output)

    missing = [f for f in REQUIRED_FILES if not os.path.exists(os.path.join(args.output, f))]
    if missing:
        print(f"ERROR: Missing expected files after extraction: {missing}", file=sys.stderr)
        sys.exit(1)

    with open(os.path.join(args.output, "studentInfo.csv"), encoding="utf-8") as f:
        row_count = sum(1 for _ in f) - 1  # minus header

    print(f"studentInfo.csv rows: {row_count} (expected {EXPECTED_STUDENT_INFO_ROWS})")
    if row_count != EXPECTED_STUDENT_INFO_ROWS:
        print("WARNING: Row count does not match the known OULAD release — "
              "verify you downloaded the correct dataset version.", file=sys.stderr)

    print(f"\nDone. OULAD CSVs ready in {args.output}")
    print("Next: python scripts/partition_oulad.py --nodes 3 --output data/partitions/")


if __name__ == "__main__":
    main()
