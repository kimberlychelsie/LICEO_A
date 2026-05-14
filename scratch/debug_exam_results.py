import psycopg2
from psycopg2.extras import RealDictCursor

def check_enrollments():
    conn = psycopg2.connect("postgresql://liceo_db:1234@localhost:5432/liceo_db")
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # List all exams
    cur.execute("SELECT exam_id, title, section_id, branch_id FROM exams")
    exams = cur.fetchall()
    print("Available Exams:")
    for ex in exams:
        print(f" - ID: {ex['exam_id']}, Title: {ex['title']}, Section: {ex['section_id']}")
    
    exam_id = 56 # Default to 56 but we might need to change it
    if exams:
        exam_id = exams[0]['exam_id'] # Use the first one if 56 doesn't exist
        print(f"Using exam_id: {exam_id}")
    
    # Get exam details
    cur.execute("SELECT exam_id, section_id, branch_id, class_mode FROM exams WHERE exam_id = %s", (exam_id,))
    exam = cur.fetchone()
    print(f"Exam Info: {exam}")
    
    if exam:
        # Check enrollments for this section
        cur.execute("""
            SELECT enrollment_id, student_name, section_id, branch_id, status 
            FROM enrollments 
            WHERE section_id = %s
        """, (exam['section_id'],))
        enrollments = cur.fetchall()
        print(f"Total Enrollments in Section {exam['section_id']}: {len(enrollments)}")
        for e in enrollments:
            print(f" - {e['student_name']} (ID: {e['enrollment_id']}, Status: {e['status']}, Branch: {e['branch_id']})")
            
        # Run the actual query from the route
        cur.execute("""
            SELECT
                e.enrollment_id, e.student_name, e.grade_level,
                r.result_id, r.score, r.total_points, COALESCE(r.status, 'Not Taken') AS status,
                r.submitted_at, r.started_at, r.tab_switches,
                (SELECT COUNT(*) FROM exam_tab_switches ts WHERE ts.result_id = r.result_id) AS switch_count,
                ext.new_due_date AS individual_extension,
                COALESCE(esp.is_allowed, %s) AS is_allowed
            FROM enrollments e
            LEFT JOIN exam_results r ON e.enrollment_id = r.enrollment_id AND r.exam_id = %s
            LEFT JOIN exam_student_permissions esp ON esp.enrollment_id = e.enrollment_id AND esp.exam_id = %s
            LEFT JOIN individual_extensions ext ON ext.enrollment_id = e.enrollment_id 
                 AND ext.item_id = %s AND ext.item_type = %s
            WHERE e.section_id = %s AND e.status IN ('approved', 'enrolled')
            AND e.branch_id = %s
            ORDER BY e.student_name ASC
        """, (exam['class_mode'] != 'Face-to-Face', exam_id, exam_id, exam_id, 'quiz', exam['section_id'], exam['branch_id']))
        results = cur.fetchall()
        print(f"Query Results: {len(results)}")
        
    cur.close()
    conn.close()

if __name__ == "__main__":
    check_enrollments()
