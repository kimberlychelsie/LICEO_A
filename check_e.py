from db import get_db_connection
conn=get_db_connection()
cur=conn.cursor()
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='enrollments'")
print([r[0] for r in cur.fetchall()])
