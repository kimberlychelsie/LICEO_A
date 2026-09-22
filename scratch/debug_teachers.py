import sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()
import traceback
from db import get_db_connection
import psycopg2.extras

def test_queries():
    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    branch_id = 1 # or test for all branches
    try:
        # 1. Fetch branches
        cursor.execute("SELECT branch_id FROM branches")
        branches = [b["branch_id"] for b in cursor.fetchall()]
        print(f"Branches: {branches}")

        for branch_id in branches:
            print(f"Testing branch_id={branch_id}")
            cursor.execute(
                "SELECT id, name FROM grade_levels WHERE branch_id = %s ORDER BY display_order",
                (branch_id,)
            )
            grades = cursor.fetchall() or []

            query = """
                SELECT
                    u.user_id, u.username, u.first_name, u.middle_name, u.last_name, u.full_name, u.gender, u.email,
                    COALESCE(u.status, 'active') AS status,
                    COALESCE(u.is_swafo, FALSE) AS is_swafo,
                    adv_sec.section_name AS advisory_section,
                    adv_grade.name AS advisory_grade,
                    (
                        SELECT STRING_AGG(DISTINCT g.name || ' - ' || s.section_name || ' (' || sub.name || ')', ', ')
                        FROM section_teachers st
                        JOIN sections s ON st.section_id = s.section_id
                        JOIN grade_levels g ON s.grade_level_id = g.id
                        JOIN subjects sub ON st.subject_id = sub.subject_id
                        WHERE st.teacher_id = u.user_id
                    ) AS assigned_sections
                FROM users u
                LEFT JOIN sections adv_sec ON adv_sec.teacher_id = u.user_id AND adv_sec.branch_id = u.branch_id
                LEFT JOIN grade_levels adv_grade ON adv_sec.grade_level_id = adv_grade.id
                WHERE u.branch_id = %s AND (u.role = 'teacher' OR u.user_roles ILIKE '%%teacher%%') AND COALESCE(u.is_archived, FALSE) = FALSE
                ORDER BY u.full_name
            """
            cursor.execute(query, (branch_id,))
            teachers = cursor.fetchall() or []
            print(f"Branch {branch_id} teachers count: {len(teachers)}")

            cursor.execute("""
                SELECT
                    COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE COALESCE(status,'active') = 'active') AS active_count,
                    COUNT(*) FILTER (
                        WHERE EXISTS (SELECT 1 FROM sections s WHERE s.teacher_id = users.user_id)
                    ) AS advisory_count,
                    COUNT(*) FILTER (
                        WHERE NOT EXISTS (SELECT 1 FROM sections s WHERE s.teacher_id = users.user_id)
                          AND EXISTS (SELECT 1 FROM section_teachers st WHERE st.teacher_id = users.user_id)
                    ) AS subject_count
                FROM users WHERE branch_id = %s AND (role = 'teacher' OR user_roles ILIKE '%%teacher%%')
                  AND COALESCE(is_archived, FALSE) = FALSE
            """, (branch_id,))
            stats = cursor.fetchone()

            cursor.execute("SELECT is_active FROM branches WHERE branch_id = %s", (branch_id,))
            brow = cursor.fetchone()
            is_branch_active_status = brow["is_active"] if (brow and "is_active" in brow) else True

    except Exception as e:
        print("EXCEPTION CAUGHT:")
        traceback.print_exc()

if __name__ == "__main__":
    test_queries()
