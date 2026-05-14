import psycopg2
from psycopg2.extras import RealDictCursor

def check_st_bernadette():
    conn = psycopg2.connect("postgresql://liceo_db:1234@localhost:5432/liceo_db")
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("SELECT section_id, branch_id, year_id FROM sections WHERE section_name = 'St. Bernadette'")
    sections = cur.fetchall()
    print(f"Sections named 'St. Bernadette': {sections}")
    
    for s in sections:
        cur.execute("SELECT enrollment_id, student_name, status FROM enrollments WHERE section_id = %s", (s['section_id'],))
        enr = cur.fetchall()
        print(f"Enrollments for Section {s['section_id']}: {enr}")
        
    cur.close()
    conn.close()

if __name__ == "__main__":
    check_st_bernadette()
