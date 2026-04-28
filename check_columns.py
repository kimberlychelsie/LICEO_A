import db
conn = db.get_db_connection()
cur = conn.cursor()
cur.execute("SELECT * FROM teacher_announcements LIMIT 0")
print([desc[0] for desc in cur.description])
cur.close()
conn.close()
