import db
conn = db.get_db_connection()
cur = conn.cursor()
cur.execute("SELECT tableowner FROM pg_tables WHERE tablename = 'teacher_announcements'")
print(cur.fetchone())
cur.close()
conn.close()
