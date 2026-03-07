from db import get_db_connection

conn = get_db_connection()
with conn.cursor() as cur:
    cur.execute("ALTER TABLE enrollments ADD COLUMN IF NOT EXISTS can_enroll_continuing BOOLEAN DEFAULT false;")
conn.commit()
print("Column added")
