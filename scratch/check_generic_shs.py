from db import get_db_connection
import psycopg2.extras

def check_shs_enrollments():
    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cursor.execute("""
            SELECT e.enrollment_id, e.student_name, e.grade_level, s.section_name
            FROM enrollments e
            LEFT JOIN sections s ON e.section_id = s.section_id
            WHERE e.grade_level IN ('Grade 11', 'Grade 12')
              AND e.status NOT IN ('rejected', 'cancelled')
        """)
        rows = cursor.fetchall()
        
        print(f"Found {len(rows)} generic SHS enrollments:")
        for r in rows:
            print(f"ID: {r['enrollment_id']} | Name: {r['student_name']} | Grade: {r['grade_level']} | Section: {r['section_name'] or 'None'}")
            
    finally:
        cursor.close()
        db.close()

if __name__ == "__main__":
    check_shs_enrollments()
