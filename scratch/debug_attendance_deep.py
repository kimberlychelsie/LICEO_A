
from db import get_db_connection
import psycopg2.extras

def debug_attendance():
    db = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        # Check active year for branch 1
        cur.execute("SELECT year_id, label FROM school_years WHERE branch_id = 1 AND is_active = TRUE")
        active_year = cur.fetchone()
        print(f"Active Year for Branch 1: {active_year}")
        
        # Check section_teachers for year 11
        cur.execute("SELECT * FROM section_teachers WHERE year_id = 11")
        st = cur.fetchall()
        print("\n--- SECTION_TEACHERS (Year 11) ---")
        for row in st:
            print(row)
            
        # Check students in section 8
        cur.execute("SELECT enrollment_id, student_name, section_id, year_id, status FROM enrollments WHERE section_id = 8")
        students = cur.fetchall()
        print("\n--- STUDENTS IN SECTION 8 ---")
        for s in students:
            print(s)
            
        # Check if any attendance exists for section 8
        cur.execute("SELECT COUNT(*) FROM daily_attendance WHERE enrollment_id IN (SELECT enrollment_id FROM enrollments WHERE section_id = 8)")
        att_count = cur.fetchone()
        print(f"\nAttendance records for Section 8: {att_count}")

    finally:
        cur.close()
        db.close()

if __name__ == "__main__":
    debug_attendance()
