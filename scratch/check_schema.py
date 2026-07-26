from db import get_db_connection
import psycopg2.extras
db = get_db_connection()
cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

for tbl in ['activities', 'activity_grades', 'activity_submissions', 'exams', 'exam_results', 'participation_scores', 'attendance_scores']:
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name=%s ORDER BY column_name", (tbl,))
    print(f"{tbl}: {[r['column_name'] for r in cur.fetchall()]}")

cur.close()
db.close()
