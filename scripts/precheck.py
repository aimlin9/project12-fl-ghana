"""
Presentation Pre-flight Check (run this before every demo)
===========================================================
Validates the full environment so there are no surprises on the day.

Usage:
    python scripts/precheck.py
    python scripts/precheck.py --fix    # auto-regenerate missing data files
"""
import argparse
import importlib
import json
import os
import socket
import sqlite3
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASS = "\033[32m[PASS]\033[0m"
FAIL = "\033[31m[FAIL]\033[0m"
WARN = "\033[33m[WARN]\033[0m"
INFO = "\033[36m[INFO]\033[0m"

issues = []
warnings = []


def check(label, ok, msg_fail="", msg_pass="", warn=False):
    if ok:
        print(f"  {PASS} {label}" + (f" — {msg_pass}" if msg_pass else ""))
    else:
        tag = WARN if warn else FAIL
        print(f"  {tag} {label}" + (f" — {msg_fail}" if msg_fail else ""))
        (warnings if warn else issues).append(label)
    return ok


# ---------------------------------------------------------------------------
# 1. Python version
# ---------------------------------------------------------------------------
def check_python():
    print("\n[1] Python environment")
    v = sys.version_info
    check("Python 3.11", v.major == 3 and v.minor == 11,
          f"found {v.major}.{v.minor} — project targets 3.11",
          f"{v.major}.{v.minor}.{v.micro}")


# ---------------------------------------------------------------------------
# 2. Critical packages
# ---------------------------------------------------------------------------
REQUIRED_PACKAGES = [
    ("torch",           "PyTorch"),
    ("flwr",            "Flower"),
    ("fastapi",         "FastAPI"),
    ("uvicorn",         "Uvicorn"),
    ("phe",             "python-paillier"),
    ("numpy",           "NumPy"),
    ("sklearn",         "scikit-learn"),
    ("scipy",           "SciPy"),
    ("pandas",          "Pandas"),
    ("matplotlib",      "Matplotlib"),
]
OPTIONAL_PACKAGES = [
    ("opacus",          "Opacus (DP-SGD)"),
    ("ctgan",           "CTGAN (synthetic data)"),
]

def check_packages():
    print("\n[2] Required packages")
    for mod, name in REQUIRED_PACKAGES:
        try:
            m = importlib.import_module(mod)
            ver = getattr(m, "__version__", "?")
            check(name, True, msg_pass=ver)
        except ImportError:
            check(name, False, f"not installed — pip install {mod}")

    print("\n    Optional packages")
    for mod, name in OPTIONAL_PACKAGES:
        try:
            m = importlib.import_module(mod)
            ver = getattr(m, "__version__", "?")
            check(name, True, msg_pass=ver, warn=False)
        except ImportError:
            check(name, False, f"not installed — DP / CTGAN features disabled", warn=True)


# ---------------------------------------------------------------------------
# 3. Data partitions
# ---------------------------------------------------------------------------
SCHOOLS = ["school_alpha", "school_beta", "school_gamma"]
EXPECTED_COLS = {
    "attendance_rate", "quiz_score", "assignment_submission_rate",
    "login_frequency", "days_since_last_activity", "course_difficulty",
    "prior_score", "engagement_index", "at_risk",
}

def check_data(fix=False):
    print("\n[3] Data partitions")
    parts_dir = os.path.join(ROOT, "data", "partitions")
    for school in SCHOOLS:
        db_path = os.path.join(parts_dir, f"{school}.db")
        if not os.path.exists(db_path):
            ok = check(f"{school}.db exists", False,
                       "missing — run: python scripts/generate_data.py")
            if fix and not ok:
                print(f"         Auto-generating {school}...")
                subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "generate_data.py")],
                               cwd=ROOT, check=False)
            continue

        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cols = {r[1] for r in conn.execute("PRAGMA table_info(students)")}
            total, at_risk_count = conn.execute(
                "SELECT COUNT(*), SUM(at_risk) FROM students"
            ).fetchone()
            conn.close()

            missing_cols = EXPECTED_COLS - cols
            check(f"{school}.db schema",  not missing_cols,
                  f"missing columns: {missing_cols}")
            check(f"{school}.db records", total >= 400,
                  f"only {total} rows — expected ≥ 400")
            pct = at_risk_count / total * 100 if total else 0
            check(f"{school}.db at-risk %", 0 < pct < 70,
                  f"{pct:.1f}% — unexpected balance",
                  f"{at_risk_count}/{total} at-risk ({pct:.1f}%)")
        except Exception as e:
            check(f"{school}.db readable", False, str(e))


# ---------------------------------------------------------------------------
# 4. Result files
# ---------------------------------------------------------------------------
def check_results(fix=False):
    print("\n[4] Pre-computed result files")
    baseline = os.path.join(ROOT, "results", "baseline_metrics.json")
    sweep    = os.path.join(ROOT, "results", "privacy_accuracy_tradeoff.json")

    ok_bl = check("results/baseline_metrics.json", os.path.exists(baseline),
                  "missing — run: python scripts/train_baseline.py", warn=False)
    if fix and not ok_bl:
        print("         Auto-running train_baseline.py...")
        subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "train_baseline.py")],
                       cwd=ROOT, check=False)

    ok_sw = check("results/privacy_accuracy_tradeoff.json", os.path.exists(sweep),
                  "missing — run: python scripts/privacy_accuracy_sweep.py (takes ~10 min)", warn=True)

    charts_dir = os.path.join(ROOT, "results", "charts")
    for chart in ["chart_convergence.png", "chart_privacy_accuracy.png", "chart_comm_overhead.png"]:
        check(f"results/charts/{chart}", os.path.exists(os.path.join(charts_dir, chart)),
              "missing — run: python scripts/generate_charts.py", warn=True)


# ---------------------------------------------------------------------------
# 5. Dashboard build
# ---------------------------------------------------------------------------
def check_dashboard():
    print("\n[5] React dashboard")
    dash_dir = os.path.join(ROOT, "dashboard")
    pkg_json = os.path.join(dash_dir, "package.json")
    node_mods = os.path.join(dash_dir, "node_modules")
    vite_cfg  = os.path.join(dash_dir, "vite.config.js")

    check("dashboard/package.json exists", os.path.exists(pkg_json),
          "dashboard source missing")
    check("dashboard/node_modules exists", os.path.exists(node_mods),
          "run: cd dashboard && npm install", warn=False)
    check("dashboard/vite.config.js exists", os.path.exists(vite_cfg),
          "Vite config missing")


# ---------------------------------------------------------------------------
# 6. Network ports
# ---------------------------------------------------------------------------
def _port_free(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) != 0

def check_ports():
    print("\n[6] Network ports")
    check("Port 8000 (FastAPI) free", _port_free(8000),
          "already in use — kill the process holding 8000 first")
    check("Port 8088 (Flower gRPC) free", _port_free(8088),
          "already in use — previous sim may still be running", warn=True)
    check("Port 3000 (React dev) free", _port_free(3000),
          "already in use", warn=True)


# ---------------------------------------------------------------------------
# 7. Key source files
# ---------------------------------------------------------------------------
def check_source():
    print("\n[7] Critical source files")
    files = [
        ("server/main.py",          "FastAPI server"),
        ("server/strategy.py",      "FedAvg strategy"),
        ("client/client.py",        "FL client"),
        ("client/database.py",      "SQLite data loader"),
        ("client/model.py",         "PyTorch MLP"),
        ("security/crypto.py",      "Paillier encryption"),
        ("security/privacy.py",     "DP-SGD (Opacus)"),
        ("scripts/run_client.py",   "Client launcher"),
        ("dashboard/src/App.jsx",   "React app root"),
    ]
    for rel, label in files:
        check(label, os.path.exists(os.path.join(ROOT, rel)),
              f"{rel} missing")


# ---------------------------------------------------------------------------
# 8. Quick import smoke-test
# ---------------------------------------------------------------------------
def check_imports():
    print("\n[8] Import smoke-test")
    sys.path.insert(0, ROOT)
    tests = [
        ("server.strategy",    "Server strategy"),
        ("client.model",       "PyTorch model"),
        ("client.database",    "Database loader"),
        ("security.crypto",    "Paillier crypto"),
        ("security.privacy",   "DP module"),
    ]
    for mod, label in tests:
        try:
            importlib.import_module(mod)
            check(label, True)
        except Exception as e:
            check(label, False, str(e))


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
def print_summary():
    print("\n" + "=" * 55)
    if not issues and not warnings:
        print("  ALL CHECKS PASSED — you're ready to present!")
    else:
        if issues:
            print(f"  {len(issues)} BLOCKING issue(s) — fix before presenting:")
            for i in issues:
                print(f"    • {i}")
        if warnings:
            print(f"  {len(warnings)} warning(s) — dashboard may show partial data:")
            for w in warnings:
                print(f"    ~ {w}")
    print("=" * 55)
    print()
    print("  Quick-start demo order:")
    print("    1. python scripts/train_baseline.py       (once)")
    print("    2. python server/main.py                  (keep running)")
    print("    3. cd dashboard && npm run dev            (keep running)")
    print("    4. Open http://localhost:3000")
    print("    5. Click 'Start FL Simulation' in the dashboard")
    print("    6. For offline-node demo: click the red toggle on a school card")
    print()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fix", action="store_true",
                        help="Auto-run generators for missing data/baseline files")
    args = parser.parse_args()

    print("=" * 55)
    print("  FL Ghana — Presentation Pre-flight Check")
    print("=" * 55)

    check_python()
    check_packages()
    check_data(fix=args.fix)
    check_results(fix=args.fix)
    check_dashboard()
    check_ports()
    check_source()
    check_imports()
    print_summary()

    sys.exit(1 if issues else 0)


if __name__ == "__main__":
    main()
