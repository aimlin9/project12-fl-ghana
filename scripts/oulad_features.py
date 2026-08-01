"""
OULAD Feature Engineering (Proposal D2/D3)
=============================================
Transforms the raw OULAD CSVs (data/oulad_raw/, see scripts/download_oulad.py)
into per-enrollment records matching the 8-feature student-at-risk schema
consumed by client/database.py and scripts/train_baseline.py:

    attendance_rate, quiz_score, assignment_submission_rate, login_frequency,
    days_since_last_activity, course_difficulty, prior_score, engagement_index, at_risk

One output row = one studentInfo.csv row (a code_module + code_presentation +
id_student enrollment) — 32,593 rows total, matching the proposal's dataset size.

OULAD has no direct "attendance", "difficulty", or "prior score" field, so these
are documented proxies derived from VLE click logs (studentVle.csv) and assessment
records (studentAssessment.csv / assessments.csv):

    attendance_rate             distinct VLE-active days / module_presentation_length
    quiz_score                  mean score of TMA/CMA assessments (excludes final Exam)
    assignment_submission_rate  # non-Exam assessments submitted / # scheduled
    login_frequency             avg VLE clicks per week, clipped to 30
    days_since_last_activity    module_presentation_length - last active day, clipped to [0, 60]
    course_difficulty           per-code_module pass-rate quintile (1 easiest - 5 hardest)
    prior_score                 score of the student's earliest-dated submitted assessment
    engagement_index            total VLE clicks, min-max normalised to 0-100
    at_risk                     1 if final_result in {Withdrawn, Fail} else 0

Usage (library, not a CLI):
    from scripts.oulad_features import load_oulad_enrollments
    rows = load_oulad_enrollments(raw_dir="data/oulad_raw")
"""
import csv
import os
from collections import defaultdict

FEATURE_COLS = [
    "attendance_rate", "quiz_score", "assignment_submission_rate", "login_frequency",
    "days_since_last_activity", "course_difficulty", "prior_score", "engagement_index",
]

AT_RISK_RESULTS = {"Withdrawn", "Fail"}
QUIZ_TYPES = {"TMA", "CMA"}


def _read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _load_courses(raw_dir):
    rows = _read_csv(os.path.join(raw_dir, "courses.csv"))
    return {
        (r["code_module"], r["code_presentation"]): int(r["module_presentation_length"])
        for r in rows
    }


def _load_module_difficulty(student_info_rows):
    """Rank each code_module by overall pass rate -> difficulty bucket 1 (easiest) - 5 (hardest)."""
    totals = defaultdict(int)
    passes = defaultdict(int)
    for r in student_info_rows:
        totals[r["code_module"]] += 1
        if r["final_result"] in ("Pass", "Distinction"):
            passes[r["code_module"]] += 1

    pass_rates = {m: passes[m] / totals[m] for m in totals}
    ordered = sorted(pass_rates, key=lambda m: pass_rates[m], reverse=True)  # easiest first
    n = len(ordered)
    return {module: 1 + min(4, (idx * 5) // n) for idx, module in enumerate(ordered)}


def _load_assessment_index(raw_dir):
    """Map id_assessment -> (code_module, code_presentation, assessment_type), and count
    non-Exam assessments scheduled per (code_module, code_presentation)."""
    rows = _read_csv(os.path.join(raw_dir, "assessments.csv"))
    index = {}
    non_exam_counts = defaultdict(int)
    for r in rows:
        key = (r["code_module"], r["code_presentation"])
        index[r["id_assessment"]] = (r["code_module"], r["code_presentation"], r["assessment_type"])
        if r["assessment_type"] != "Exam":
            non_exam_counts[key] += 1
    return index, non_exam_counts


def _load_assessment_scores(raw_dir, assessment_index):
    """Aggregate per (code_module, code_presentation, id_student):
    submitted_count, quiz_scores (TMA/CMA), earliest (date, score) submission."""
    rows = _read_csv(os.path.join(raw_dir, "studentAssessment.csv"))
    agg = defaultdict(lambda: {"submitted": 0, "quiz_scores": [], "earliest": (None, None)})

    for r in rows:
        info = assessment_index.get(r["id_assessment"])
        if info is None or not r["score"]:
            continue
        code_module, code_presentation, assessment_type = info
        score = float(r["score"])
        key = (code_module, code_presentation, r["id_student"])
        entry = agg[key]

        if assessment_type != "Exam":
            entry["submitted"] += 1
        if assessment_type in QUIZ_TYPES:
            entry["quiz_scores"].append(score)

        if r["date_submitted"]:
            date_submitted = int(r["date_submitted"])
            earliest_date, _ = entry["earliest"]
            if earliest_date is None or date_submitted < earliest_date:
                entry["earliest"] = (date_submitted, score)

    return agg


def _stream_vle_aggregates(raw_dir):
    """Single pass over studentVle.csv (~10.6M rows) -> per-enrollment VLE stats.
    Uses csv.reader (not DictReader) and plain tuples for speed — the whole
    450MB+ file is never held in memory at once, only the aggregated result.
    """
    path = os.path.join(raw_dir, "studentVle.csv")
    agg = defaultdict(lambda: {"days": set(), "total_clicks": 0, "last_date": None})

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        idx = {name: i for i, name in enumerate(header)}
        cm_i, cp_i, sid_i = idx["code_module"], idx["code_presentation"], idx["id_student"]
        date_i, click_i = idx["date"], idx["sum_click"]

        for row in reader:
            key = (row[cm_i], row[cp_i], row[sid_i])
            entry = agg[key]
            day = int(row[date_i])
            entry["days"].add(day)
            entry["total_clicks"] += int(row[click_i])
            if entry["last_date"] is None or day > entry["last_date"]:
                entry["last_date"] = day

    return agg


def load_oulad_enrollments(raw_dir="data/oulad_raw"):
    """Return one dict per (code_module, code_presentation, id_student) enrollment
    with the 8 model features + at_risk label, plus code_module/code_presentation
    for downstream quarter-based partitioning.
    """
    student_info = _read_csv(os.path.join(raw_dir, "studentInfo.csv"))
    course_lengths = _load_courses(raw_dir)
    module_difficulty = _load_module_difficulty(student_info)
    assessment_index, non_exam_counts = _load_assessment_index(raw_dir)
    assessment_agg = _load_assessment_scores(raw_dir, assessment_index)

    print("  Scanning studentVle.csv (~10.6M rows, one pass)...")
    vle_agg = _stream_vle_aggregates(raw_dir)

    all_clicks = [v["total_clicks"] for v in vle_agg.values()]
    click_min, click_max = (min(all_clicks), max(all_clicks)) if all_clicks else (0, 1)
    click_range = max(click_max - click_min, 1)

    rows = []
    for r in student_info:
        code_module = r["code_module"]
        code_presentation = r["code_presentation"]
        id_student = r["id_student"]
        key = (code_module, code_presentation, id_student)

        duration = course_lengths.get((code_module, code_presentation), 240)
        vle = vle_agg.get(key)
        asmt = assessment_agg.get(key)

        if vle:
            active_days = len(vle["days"])
            total_clicks = vle["total_clicks"]
            last_date = vle["last_date"]
        else:
            active_days, total_clicks, last_date = 0, 0, None

        attendance_rate = min(active_days / max(duration, 1), 1.0)
        login_frequency = min(total_clicks / max(duration / 7.0, 1e-6), 30.0)
        days_since_last_activity = (
            max(0.0, min(60.0, duration - last_date)) if last_date is not None else 60.0
        )
        engagement_index = 100.0 * (total_clicks - click_min) / click_range

        non_exam_total = non_exam_counts.get((code_module, code_presentation), 0)
        if asmt:
            submitted = asmt["submitted"]
            quiz_scores = asmt["quiz_scores"]
            _, earliest_score = asmt["earliest"]
        else:
            submitted, quiz_scores, earliest_score = 0, [], None

        assignment_submission_rate = min(submitted / max(non_exam_total, 1), 1.0)
        quiz_score = sum(quiz_scores) / len(quiz_scores) if quiz_scores else 0.0
        prior_score = earliest_score if earliest_score is not None else quiz_score

        rows.append({
            "code_module": code_module,
            "code_presentation": code_presentation,
            "id_student": id_student,
            "attendance_rate": round(attendance_rate, 4),
            "quiz_score": round(quiz_score, 2),
            "assignment_submission_rate": round(assignment_submission_rate, 4),
            "login_frequency": round(login_frequency, 2),
            "days_since_last_activity": round(days_since_last_activity, 2),
            "course_difficulty": module_difficulty.get(code_module, 3),
            "prior_score": round(prior_score, 2),
            "engagement_index": round(engagement_index, 2),
            "at_risk": 1 if r["final_result"] in AT_RISK_RESULTS else 0,
        })

    return rows
