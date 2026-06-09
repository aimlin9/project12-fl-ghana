"""
Simulated School Data Generator
================================
Generates non-IID student performance SQLite databases for each school node.
Supports 3–5 school configurations with distinct demographic profiles.

Usage:
    python scripts/generate_data.py
"""
import os
import sqlite3
import numpy as np

SCHOOLS = ["school_alpha", "school_beta", "school_gamma"]
NUM_RECORDS = {
    "school_alpha": 600,
    "school_beta": 550,
    "school_gamma": 500,
    "school_delta": 480,
    "school_epsilon": 520,
}

# School archetype profiles (non-IID distributions)
SCHOOL_PROFILES = {
    "school_alpha":   {"attendance": 0.92, "quiz": 75.0, "logins": 12.0},  # Urban
    "school_beta":    {"attendance": 0.85, "quiz": 82.0, "logins": 8.0},   # Suburban
    "school_gamma":   {"attendance": 0.72, "quiz": 60.0, "logins": 4.0},   # Rural
    "school_delta":   {"attendance": 0.78, "quiz": 68.0, "logins": 6.0},   # Peri-urban
    "school_epsilon": {"attendance": 0.88, "quiz": 78.0, "logins": 10.0},  # Semi-urban
}


def generate_school_data(school_name, num_records, output_dir="data/partitions"):
    """Generate a single school's SQLite database with synthetic student data."""
    os.makedirs(output_dir, exist_ok=True)
    np.random.seed(42 + hash(school_name) % 100)

    profile = SCHOOL_PROFILES.get(school_name, {"attendance": 0.80, "quiz": 70.0, "logins": 7.0})
    avg_attendance = profile["attendance"]
    avg_quiz = profile["quiz"]
    avg_logins = profile["logins"]

    # Generate features
    attendance = np.clip(np.random.normal(avg_attendance, 0.08, num_records), 0.1, 1.0)
    quiz_score = np.clip(np.random.normal(avg_quiz, 12.0, num_records), 0.0, 100.0)
    assignment_rate = np.clip(np.random.normal(attendance - 0.05, 0.1, num_records), 0.0, 1.0)
    logins = np.clip(np.random.normal(avg_logins, 3.0, num_records), 0.0, 30.0)
    days_inactive = np.clip(np.random.exponential(15.0 - attendance * 10.0, num_records), 0.0, 60.0)
    difficulty = np.clip(np.random.normal(3.0, 0.8, num_records), 1.0, 5.0)
    prior_score = np.clip(np.random.normal(quiz_score - 5.0, 10.0, num_records), 0.0, 100.0)
    engagement = np.clip(attendance * logins * 2.0 + np.random.normal(5.0, 2.0, num_records), 0.0, 100.0)

    # Compute risk target with a logistic function
    logit = (
        -3.0
        - 8.0 * (attendance - 0.8)
        - 0.08 * (quiz_score - 70.0)
        - 6.0 * (assignment_rate - 0.8)
        - 0.2 * (logins - 8.0)
        + 0.08 * (days_inactive - 10.0)
        + 0.5 * (difficulty - 3.0)
        - 0.04 * (prior_score - 65.0)
        - 0.05 * (engagement - 20.0)
    )

    prob = 1.0 / (1.0 + np.exp(-logit))
    at_risk = (np.random.rand(num_records) < prob).astype(int)

    db_path = os.path.join(output_dir, f"{school_name}.db")
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE students (
            student_id INTEGER PRIMARY KEY AUTOINCREMENT,
            attendance_rate REAL,
            quiz_score REAL,
            assignment_submission_rate REAL,
            login_frequency REAL,
            days_since_last_activity REAL,
            course_difficulty REAL,
            prior_score REAL,
            engagement_index REAL,
            at_risk INTEGER
        )
    """)

    for i in range(num_records):
        cursor.execute("""
            INSERT INTO students (
                attendance_rate, quiz_score, assignment_submission_rate,
                login_frequency, days_since_last_activity, course_difficulty,
                prior_score, engagement_index, at_risk
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            float(attendance[i]),
            float(quiz_score[i]),
            float(assignment_rate[i]),
            float(logins[i]),
            float(days_inactive[i]),
            float(difficulty[i]),
            float(prior_score[i]),
            float(engagement[i]),
            int(at_risk[i])
        ))

    conn.commit()

    # Verify records and class balance
    cursor.execute("SELECT COUNT(*), SUM(at_risk) FROM students")
    total, active_risk = cursor.fetchone()
    print(f"Generated {db_path}: {total} records, {active_risk} at-risk ({active_risk/total*100:.1f}%)")
    conn.close()


if __name__ == "__main__":
    for school in SCHOOLS:
        generate_school_data(school, NUM_RECORDS[school])
    print("Data generation complete.")
