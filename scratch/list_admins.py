import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import db
conn = db.get_db_connection()
cur = conn.cursor()
cur.execute("SELECT username, password, role FROM users WHERE role = 'branch_admin' OR role = 'registrar' LIMIT 10")
rows = cur.fetchall()
for row in rows:
    print(f"Username: {row[0]}, Password: {row[1]}, Role: {row[2]}")
cur.close()
conn.close()
