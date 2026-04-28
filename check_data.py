import db
conn = db.get_db_connection()
cur = conn.cursor()
cur.execute("SELECT grade_level, title FROM teacher_announcements LIMIT 10")
for row in cur.fetchall():
    print(row)
cur.close()
conn.close()
