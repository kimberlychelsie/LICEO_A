import sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()
from db import get_db_connection
import psycopg2.extras

db = get_db_connection()
cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# Find user who is librarian with teacher role added, or any user with user_roles ILIKE '%teacher%'
cursor.execute("SELECT user_id, full_name, role, user_roles, branch_id FROM users WHERE (role = 'teacher' OR user_roles ILIKE '%%teacher%%')")
users = cursor.fetchall()
print(f"Found {len(users)} teacher accounts for API test:")
for u in users:
    print(f"  User ID: {u['user_id']}, Name: {u['full_name']}, Primary Role: {u['role']}, Multi-Roles: {u['user_roles']}")

    # Test the query inside branch_admin_api_get_all_subjects
    cursor.execute(
        """SELECT 1 FROM users
           WHERE user_id=%s AND branch_id=%s AND (role='teacher' OR user_roles ILIKE '%%teacher%%')
             AND COALESCE(is_archived, FALSE) = FALSE""",
        (u['user_id'], u['branch_id']),
    )
    found = cursor.fetchone()
    print(f"    Check in API get-all-subjects: {'PASSED (Teacher found)' if found else 'FAILED'}")

db.close()
