"""Optional event history support for the grade approval workflow."""


def grade_history_available(cursor):
    cursor.execute(
        "SELECT to_regclass('public.grade_submission_history') IS NOT NULL AS available"
    )
    row = cursor.fetchone()
    if isinstance(row, dict):
        return bool(row.get("available"))
    return bool(row and row[0])


def record_grade_history(
    cursor,
    request_id,
    event_type,
    from_status,
    to_status,
    actor_user_id,
    actor_role,
    remarks=None,
):
    """Record an event when the additive history migration is installed."""
    if not grade_history_available(cursor):
        return False
    cursor.execute(
        """
        INSERT INTO grade_submission_history (
            request_id, event_type, from_status, to_status,
            actor_user_id, actor_role, remarks
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            request_id,
            event_type,
            from_status,
            to_status,
            actor_user_id,
            actor_role,
            remarks,
        ),
    )
    return True


def fetch_grade_history(cursor, request_id):
    if not request_id or not grade_history_available(cursor):
        return [], False
    cursor.execute(
        """
        SELECT h.event_id, h.event_type, h.from_status, h.to_status,
               h.actor_role, h.remarks, h.created_at,
               u.full_name AS actor_name
        FROM grade_submission_history h
        LEFT JOIN users u ON u.user_id = h.actor_user_id
        WHERE h.request_id = %s
        ORDER BY h.created_at ASC, h.event_id ASC
        """,
        (request_id,),
    )
    return cursor.fetchall() or [], True
