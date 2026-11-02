import json
import logging
from flask import session

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# SQL fragment: identifies the LATEST enrollment per student identity.
# An enrollment is "superseded" if a newer row (higher enrollment_id) exists
# in the SAME branch with the same LRN  — or, when LRN is absent, with the
# same first/middle/last name and the same guardian e-mail.
# We EXCLUDE superseded rows so that only the current re-enrollment is linked.
# ─────────────────────────────────────────────────────────────────────────────
_NOT_SUPERSEDED = """
    AND NOT EXISTS (
        SELECT 1
        FROM   enrollments newer
        WHERE  newer.branch_id      = e.branch_id
          AND  newer.enrollment_id  > e.enrollment_id
          AND  (
               -- prefer LRN match when available
               (e.lrn IS NOT NULL AND e.lrn <> ''
                AND newer.lrn = e.lrn)
               OR
               -- fall back to name + guardian e-mail when LRN is absent
               ((e.lrn IS NULL OR e.lrn = '')
                AND newer.student_first_name  = e.student_first_name
                AND newer.student_last_name   = e.student_last_name
                AND newer.student_middle_name IS NOT DISTINCT FROM e.student_middle_name
                AND LOWER(TRIM(newer.guardian_email)) = LOWER(TRIM(e.guardian_email)))
               )
    )
"""


def sync_user_parent_links(db, cursor, user_id):
    """
    Synchronizes parent_student links and user_roles for a user based on email & branch_id.

    Rules:
    1. A parent_student link is valid ONLY IF student's guardian_email matches user's email (case-insensitive, trimmed)
       AND student's branch_id matches user's branch_id (if user has a branch_id).
    2. Any parent_student links for this user that do NOT satisfy both criteria are removed.
       Superseded (old re-enrollment) rows are also removed — only the latest enrollment
       per student identity is kept.
    3. If user's email matches student guardian_email in the SAME branch, parent_student link
       is created — but ONLY for the most-recent enrollment per student identity.
    4. If no valid parent_student links remain for user (and user's primary role != 'parent'),
       'parent' role is removed from user_roles.
    5. If user IS linked to valid student(s) in this branch, 'parent' role is added to user_roles.
    6. If the user is currently logged in:
       - Update session['roles'].
       - If 'parent' role was lost and active session['role'] == 'parent', switch active
         session['role'] back to user's primary role.
    """
    cursor.execute("SELECT user_id, email, branch_id, role, user_roles FROM users WHERE user_id = %s", (user_id,))
    u = cursor.fetchone()
    if not u:
        return {"links_count": 0, "has_parent_role": False, "switched_role": None}

    email = (u.get("email") or "").strip().lower()
    user_branch_id = u.get("branch_id")
    primary_role = u.get("role") or "staff"

    user_roles_list = []
    ur_raw = u.get("user_roles")
    if ur_raw:
        try:
            user_roles_list = json.loads(ur_raw) if isinstance(ur_raw, str) else list(ur_raw)
        except Exception:
            user_roles_list = [primary_role]
    else:
        user_roles_list = [primary_role]

    if primary_role not in user_roles_list:
        user_roles_list.insert(0, primary_role)

    # Student logins also have a shadow row in users for shared foreign keys.
    # They are never eligible for automatic Parent Mode based on email.
    if primary_role == "student":
        if session.get("user_id") == user_id:
            session["roles"] = ["student"]
            session["role"] = "student"
        return {
            "links_count": 0,
            "has_parent_role": False,
            "user_roles": ["student"],
            "switched_role": "student",
        }

    # Define generic system/admin email prefixes that should NEVER be auto-linked to student accounts
    BLOCKED_SYSTEM_EMAIL_PREFIXES = (
        'admin@', 'superadmin@', 'registrar@', 'info@', 'system@', 'support@', 'test@', 'demo@'
    )
    is_blocked_system_email = email.startswith(BLOCKED_SYSTEM_EMAIL_PREFIXES)

    # ─── 1. Clean up stale / superseded parent_student links for this user ────
    # A link is invalid if:
    #   (a) guardian_email doesn't match, OR branch doesn't match, OR
    #   (b) it points to an old superseded enrollment (a newer re-enrollment exists).
    if email and not is_blocked_system_email:
        if user_branch_id is not None:
            cursor.execute(
                """
                DELETE FROM parent_student
                WHERE parent_id = %s
                  AND student_id NOT IN (
                      SELECT e.enrollment_id
                      FROM   enrollments e
                      WHERE  LOWER(TRIM(e.guardian_email)) = %s
                        AND  e.branch_id = %s
                """ + _NOT_SUPERSEDED + """
                  )
                """,
                (user_id, email, user_branch_id),
            )
        else:
            cursor.execute(
                """
                DELETE FROM parent_student
                WHERE parent_id = %s
                  AND student_id NOT IN (
                      SELECT e.enrollment_id
                      FROM   enrollments e
                      WHERE  LOWER(TRIM(e.guardian_email)) = %s
                """ + _NOT_SUPERSEDED + """
                  )
                """,
                (user_id, email),
            )
    else:
        # User has no email or is a system/admin email -> remove all auto parent_student links
        cursor.execute("DELETE FROM parent_student WHERE parent_id = %s", (user_id,))

    # ─── 2. Insert links for the LATEST enrollment per student identity ────────
    if email and not is_blocked_system_email:
        if user_branch_id is not None:
            cursor.execute(
                """
                INSERT INTO parent_student (parent_id, student_id, relationship)
                SELECT %s, e.enrollment_id, 'guardian'
                FROM   enrollments e
                WHERE  LOWER(TRIM(e.guardian_email)) = %s
                  AND  e.branch_id = %s
                """ + _NOT_SUPERSEDED + """
                ON CONFLICT DO NOTHING
                """,
                (user_id, email, user_branch_id),
            )

    # ─── 3. Count valid links left for this user ──────────────────────────────
    cursor.execute("SELECT COUNT(*) AS cnt FROM parent_student WHERE parent_id = %s", (user_id,))
    cnt_row = cursor.fetchone()
    link_count = cnt_row["cnt"] if cnt_row else 0

    has_parent_role = False
    if link_count > 0:
        has_parent_role = True
        if "parent" not in user_roles_list:
            user_roles_list.append("parent")
    else:
        if primary_role != "parent" and "parent" in user_roles_list:
            user_roles_list = [r for r in user_roles_list if r != "parent"]

    cursor.execute("UPDATE users SET user_roles = %s WHERE user_id = %s", (json.dumps(user_roles_list), user_id))

    # ─── 4. If current session belongs to this user, sync session state ───────
    switched_role = None
    if session.get("user_id") == user_id:
        session["roles"] = user_roles_list
        if not has_parent_role and session.get("role") == "parent":
            session["role"] = primary_role
            switched_role = primary_role

    return {
        "links_count": link_count,
        "has_parent_role": has_parent_role,
        "user_roles": user_roles_list,
        "switched_role": switched_role
    }


def sync_all_users_for_enrollment_guardian_email(db, cursor, guardian_email, branch_id=None):
    """
    Finds all users whose email matches guardian_email (and branch_id) and re-syncs their parent links.
    Useful when a student's guardian_email is updated.
    """
    if not guardian_email:
        return
    clean_email = guardian_email.strip().lower()
    if branch_id is not None:
        cursor.execute("SELECT user_id FROM users WHERE LOWER(TRIM(email)) = %s AND branch_id = %s", (clean_email, branch_id))
    else:
        cursor.execute("SELECT user_id FROM users WHERE LOWER(TRIM(email)) = %s", (clean_email,))
    rows = cursor.fetchall()
    for r in rows:
        sync_user_parent_links(db, cursor, r["user_id"])
