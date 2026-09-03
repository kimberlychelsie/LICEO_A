import db
conn = db.get_db_connection()
cur = conn.cursor()
cur.execute("SELECT tableowner FROM pg_tables WHERE tablename = 'subjects'")
print("Subjects Owner:", cur.fetchone())
cur.execute("SELECT usename FROM pg_user")
print("PG Users:", cur.fetchall())
cur.close()
conn.close()
