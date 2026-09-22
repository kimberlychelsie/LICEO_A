import sys, os
sys.path.insert(0, os.path.abspath("."))
import dotenv
dotenv.load_dotenv()
import db, psycopg2.extras, json

conn = db.get_db_connection()
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# 1. Update all users with role = 'student' to have user_roles = '["student"]'
cur.execute("UPDATE users SET user_roles = %s WHERE role = 'student'", (json.dumps(["student"]),))
print("Updated student user_roles count:", cur.rowcount)

# 2. Remove parent_student links where parent_id belongs to a student user account
cur.execute("DELETE FROM parent_student WHERE parent_id IN (SELECT user_id FROM users WHERE role = 'student')")
print("Removed invalid parent_student links for student accounts count:", cur.rowcount)

conn.commit()
cur.close()
conn.close()
print("Done cleaning student accounts!")
