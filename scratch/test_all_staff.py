import sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()
from db import get_db_connection
import psycopg2.extras

db = get_db_connection()
cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

branch_id = 11

query_role_cond = "(u.role IN ('registrar', 'cashier', 'librarian', 'teacher') OR u.user_roles ILIKE '%%registrar%%' OR u.user_roles ILIKE '%%cashier%%' OR u.user_roles ILIKE '%%librarian%%' OR u.user_roles ILIKE '%%teacher%%')"
params = [branch_id]

query = f"""
    SELECT
        u.user_id, u.username, u.role, u.full_name, u.gender,
        u.email, COALESCE(g.name, u.grade_level) AS grade_level, u.status
    FROM users u
    LEFT JOIN grade_levels g ON u.grade_level_id = g.id
    WHERE u.branch_id = %s AND {query_role_cond} AND COALESCE(u.is_archived, FALSE) = FALSE
"""

try:
    cursor.execute(query, tuple(params))
    accounts = cursor.fetchall()
    print(f"Accounts count for all_staff: {len(accounts)}")
    for a in accounts:
        print(f"  ID: {a['user_id']}, Username: {a['username']}, Role: {a['role']}, FullName: {a['full_name']}")
except Exception as e:
    import traceback
    print("ERROR:")
    traceback.print_exc()

db.close()
