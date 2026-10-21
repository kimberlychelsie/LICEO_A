"""Server-authoritative lookup for resumable student assessments."""


def find_resumable_assessment_exam_id(cursor, enrollment_id):
    if not enrollment_id:
        return None

    cursor.execute(
        """
        SELECT r.exam_id
        FROM exam_results r
        JOIN exams e ON e.exam_id = r.exam_id
        JOIN enrollments en
          ON en.enrollment_id = r.enrollment_id
         AND en.section_id = e.section_id
        LEFT JOIN individual_extensions ext
          ON ext.item_id = e.exam_id
         AND ext.enrollment_id = r.enrollment_id
         AND ext.item_type IN ('exam', 'quiz')
        WHERE r.enrollment_id = %s
          AND r.status = 'in_progress'
          AND LOWER(COALESCE(e.status, '')) = 'published'
          AND COALESCE(e.year_id, en.year_id) = en.year_id
          AND NOW() < r.started_at + (e.duration_mins * INTERVAL '1 minute')
          AND (
              COALESCE(ext.new_due_date, e.scheduled_start) IS NULL
              OR NOW() < COALESCE(ext.new_due_date, e.scheduled_start)
                         + (e.duration_mins * INTERVAL '1 minute')
          )
        ORDER BY r.started_at DESC, r.result_id DESC
        LIMIT 1
        """,
        (enrollment_id,),
    )
    row = cursor.fetchone()
    if not row:
        return None
    return row.get("exam_id") if isinstance(row, dict) else row[0]
