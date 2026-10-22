LEGACY_WEIGHTS = {
    "language": {"name": "Language / Values", "ww": 0.30, "pt": 0.50, "qa": 0.20},
    "science_math": {"name": "Science / Math", "ww": 0.40, "pt": 0.40, "qa": 0.20},
    "skills": {"name": "Skills / Technical", "ww": 0.20, "pt": 0.60, "qa": 0.20},
}


def dynamic_grading_schema_available(cursor):
    cursor.execute("""
        SELECT (to_regclass('public.grading_categories') IS NOT NULL
           AND to_regclass('public.teacher_component_distributions') IS NOT NULL) AS available
    """)
    row = cursor.fetchone()
    return bool(row.get("available") if isinstance(row, dict) else row[0])


def get_assignment_grading_weights(
    cursor, branch_id, year_id, section_id, subject_id
):
    if dynamic_grading_schema_available(cursor):
        cursor.execute("""
            SELECT gc.category_id, gc.code, gc.name, gc.ww_pct, gc.pt_pct, gc.qa_pct
            FROM section_teachers st
            JOIN sections sec ON sec.section_id = st.section_id
            JOIN grading_categories gc ON gc.category_id = st.grading_category_id
            WHERE st.section_id = %s
              AND st.subject_id = %s
              AND st.year_id = %s
              AND sec.branch_id = %s
              AND gc.branch_id = %s
              AND gc.year_id = %s
              AND gc.is_active = TRUE
            ORDER BY st.id
            LIMIT 1
        """, (section_id, subject_id, year_id, branch_id, branch_id, year_id))
        row = cursor.fetchone()
        if row:
            return {
                "category_id": row["category_id"],
                "code": row["code"],
                "name": row["name"],
                "ww": float(row["ww_pct"]) / 100,
                "pt": float(row["pt_pct"]) / 100,
                "qa": float(row["qa_pct"]) / 100,
                "dynamic": True,
            }

    cursor.execute("SELECT deped_category FROM subjects WHERE subject_id=%s", (subject_id,))
    row = cursor.fetchone()
    code = (row.get("deped_category") if row else None) or "language"
    legacy = LEGACY_WEIGHTS.get(code, LEGACY_WEIGHTS["language"])
    return {"category_id": None, "code": code, "dynamic": False, **legacy}


def get_teacher_component_distribution(
    cursor, teacher_id, branch_id, year_id, section_id, subject_id, period
):
    if not dynamic_grading_schema_available(cursor):
        return None
    cursor.execute("""
        SELECT ww_quiz_pct, ww_monthly_exam_pct,
               pt_activity_pct, pt_participation_pct, pt_attendance_pct,
               qa_periodical_exam_pct
        FROM teacher_component_distributions
        WHERE teacher_id=%s AND branch_id=%s AND year_id=%s
          AND section_id=%s AND subject_id=%s AND grading_period=%s
    """, (teacher_id, branch_id, year_id, section_id, subject_id, period))
    row = cursor.fetchone()
    return dict(row) if row else None
