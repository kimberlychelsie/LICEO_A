import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import db
conn = db.get_db_connection()
cur = conn.cursor()
cur.execute("SELECT * FROM branches")
for r in cur.fetchall():
    print(r)
cur.close()
conn.close()
