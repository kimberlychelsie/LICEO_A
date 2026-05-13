
from db import get_db_connection
import psycopg2.extras

def check_enrollments():
    db = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("SELECT enrollment_id, student_name, grade_level, section_id, branch_id, year_id, status FROM enrollments LIMIT 10")
        rows = cur.fetchall()
        print("--- ENROLLMENTS SAMPLE ---")
        for r in rows:
            print(r)
            
        cur.execute("SELECT section_id, section_name, branch_id, year_id FROM sections LIMIT 10")
        sections = cur.fetchall()
        print("\n--- SECTIONS SAMPLE ---")
        for s in sections:
            print(s)
            
        cur.execute("SELECT * FROM section_teachers LIMIT 10")
        st = cur.fetchall()
        print("\n--- SECTION_TEACHERS SAMPLE ---")
        for row in st:
            print(row)
            
    finally:
        cur.close()
        db.close()

if __name__ == "__main__":
    check_enrollments()
