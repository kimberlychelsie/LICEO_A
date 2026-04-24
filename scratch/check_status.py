from db import get_db_connection
import psycopg2.extras

db = get_db_connection()
cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
cur.execute("SELECT enrollment_id, student_name, status FROM enrollments WHERE enrollment_id = 1")
row = cur.fetchone()
print(row)
cur.close()
db.close()
