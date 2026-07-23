from db import get_db_connection
conn = get_db_connection()
cur = conn.cursor()
cur.execute("SELECT table_name FROM information_schema.columns WHERE column_name='enrollment_id'")
print([r[0] for r in cur.fetchall()])
