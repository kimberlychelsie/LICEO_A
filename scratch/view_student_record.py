import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import db

import psycopg2.extras
conn = db.get_db_connection()
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
cur.execute("SELECT * FROM enrollments WHERE student_first_name = 'Junterial' AND student_last_name = 'Sierra'")
r = cur.fetchone()
if r:
    for k, v in r.items():
        print(f"{k}: {v}")
else:
    print("Student not found.")
cur.close()
conn.close()
