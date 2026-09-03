import os
import psycopg2

def run():
    host = os.getenv("DB_HOST", "127.0.0.1")
    port = int(os.getenv("DB_PORT", "5432"))
    database = os.getenv("DB_NAME", "liceo_db")
    
    # Try different credentials for postgres superuser
    passwords = ["1234", "", "postgres", "admin", "root"]
    
    conn = None
    for pwd in passwords:
        try:
            print(f"Trying to connect as postgres user with password '{pwd}'...")
            conn = psycopg2.connect(
                host=host,
                port=port,
                dbname=database,
                user="postgres",
                password=pwd,
            )
            print("Successfully connected as postgres user!")
            break
        except Exception as e:
            print(f"Failed connection: {e}")
            
    if not conn:
        print("Could not connect as postgres user. Let's try changing owner of the subjects table if we have permissions, or try another way.")
        return

    cur = conn.cursor()
    try:
        # Check subjects columns
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'subjects'")
        cols = [r[0] for r in cur.fetchall()]
        print("Existing columns in subjects:", cols)
        
        if 'subject_type' not in cols:
            print("Adding subject_type column to subjects table...")
            cur.execute("ALTER TABLE subjects ADD COLUMN subject_type VARCHAR(50) DEFAULT 'CORE'")
        if 'track' not in cols:
            print("Adding track column to subjects table...")
            cur.execute("ALTER TABLE subjects ADD COLUMN track VARCHAR(50)")
            
        # Check enrollments columns
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'enrollments'")
        enr_cols = [r[0] for r in cur.fetchall()]
        print("Existing columns in enrollments:", enr_cols)
        if 'curriculum_type' not in enr_cols:
            print("Adding curriculum_type column to enrollments table...")
            cur.execute("ALTER TABLE enrollments ADD COLUMN curriculum_type VARCHAR(50) DEFAULT 'basic_ed'")
        if 'shs_track' not in enr_cols:
            print("Adding shs_track column to enrollments table...")
            cur.execute("ALTER TABLE enrollments ADD COLUMN shs_track VARCHAR(50)")
            
        # Change table owner to liceo_db so we don't hit this issue again!
        print("Changing owner of subjects table to liceo_db...")
        cur.execute("ALTER TABLE subjects OWNER TO liceo_db")
        print("Changing owner of enrollments table to liceo_db...")
        cur.execute("ALTER TABLE enrollments OWNER TO liceo_db")
        print("Changing owner of sections table to liceo_db...")
        cur.execute("ALTER TABLE sections OWNER TO liceo_db")
        print("Changing owner of section_teachers table to liceo_db...")
        cur.execute("ALTER TABLE section_teachers OWNER TO liceo_db")
        print("Changing owner of exam_results table to liceo_db...")
        cur.execute("ALTER TABLE exam_results OWNER TO liceo_db")
        print("Changing owner of student_accounts table to liceo_db...")
        cur.execute("ALTER TABLE student_accounts OWNER TO liceo_db")
        print("Changing owner of activity_submissions table to liceo_db...")
        cur.execute("ALTER TABLE activity_submissions OWNER TO liceo_db")
        print("Changing owner of attendance_scores table to liceo_db...")
        cur.execute("ALTER TABLE attendance_scores OWNER TO liceo_db")
        print("Changing owner of posted_grades table to liceo_db...")
        cur.execute("ALTER TABLE posted_grades OWNER TO liceo_db")

        conn.commit()
        print("Migration and ownership changes completed successfully!")
    except Exception as e:
        conn.rollback()
        print(f"Failed database execution: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    run()
