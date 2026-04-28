import db
conn = db.get_db_connection()
cur = conn.cursor()
try:
    cur.execute("ALTER TABLE teacher_announcements ADD COLUMN section_id INTEGER REFERENCES sections(section_id) ON DELETE CASCADE")
    conn.commit()
    print("Column section_id added to teacher_announcements.")
except Exception as e:
    conn.rollback()
    print(f"Migration failed or already applied: {e}")
finally:
    cur.close()
    conn.close()
