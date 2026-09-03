import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import db

import psycopg2.extras
conn = db.get_db_connection()
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

cur.execute("SELECT * FROM grade_levels WHERE branch_id = 7")
for r in cur.fetchall():
    print(r)

cur.close()
conn.close()
