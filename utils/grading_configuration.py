LEGACY_WEIGHTS = {
    "language": {"name": "Language / Values", "ww": 0.30, "pt": 0.50, "qa": 0.20},
    "science_math": {"name": "Science / Math", "ww": 0.40, "pt": 0.40, "qa": 0.20},
    "skills": {"name": "Skills / Technical", "ww": 0.20, "pt": 0.60, "qa": 0.20},
}


def dynamic_grading_schema_available(cursor):
    """Return whether teacher-owned top-level grading weights are available."""
    cursor.execute(
        "SELECT to_regclass('public.teacher_grading_weights') IS NOT NULL AS available"
    )
    row = cursor.fetchone()
    return bool(row.get("available") if isinstance(row, dict) else row[0])


def get_assignment_grading_weights(
    cursor, teacher_id, branch_id, year_id, section_id, subject_id, period
):
    """Load teacher-owned WW/PT/QA weights for one class-record term.

    Legacy subject categories remain a read-only fallback so existing class records
    continue to calculate normally until the teacher saves a term configuration.
    """
    if dynamic_grading_schema_available(cursor):
        cursor.execute(
            """
            SELECT weight_id, ww_pct, pt_pct, qa_pct
            FROM teacher_grading_weights
            WHERE teacher_id=%s AND branch_id=%s AND year_id=%s
              AND section_id=%s AND subject_id=%s AND grading_period=%s
            LIMIT 1
            """,
            (teacher_id, branch_id, year_id, section_id, subject_id, period),
        )
        row = cursor.fetchone()
        if row:
            return {
                "weight_id": row["weight_id"],
                "code": "teacher_configured",
                "name": "Teacher configured",
                "ww": float(row["ww_pct"]) / 100,
                "pt": float(row["pt_pct"]) / 100,
                "qa": float(row["qa_pct"]) / 100,
                "configured": True,
                "dynamic": True,
            }

    cursor.execute("SELECT deped_category FROM subjects WHERE subject_id=%s", (subject_id,))
    row = cursor.fetchone()
    code = (row.get("deped_category") if row else None) or "language"
    legacy = LEGACY_WEIGHTS.get(code, LEGACY_WEIGHTS["language"])
    return {
        "weight_id": None,
        "code": code,
        "name": f"Default - {legacy['name']}",
        "configured": False,
        "dynamic": False,
        **legacy,
    }
