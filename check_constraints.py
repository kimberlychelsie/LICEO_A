import db
conn = db.get_db_connection()
cursor = conn.cursor()
cursor.execute("SELECT conname FROM pg_constraint WHERE conrelid = 'enrollments'::regclass;")
print(cursor.fetchall())
