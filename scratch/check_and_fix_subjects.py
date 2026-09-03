import os
import psycopg2

def run():
    host = os.getenv("DB_HOST", "127.0.0.1")
    port = int(os.getenv("DB_PORT", "5432"))
    database = os.getenv("DB_NAME", "liceo_db")
    user = os.getenv("DB_USER", "liceo_db")
    password = os.getenv("DB_PASSWORD", "1234")

    conn = psycopg2.connect(
        host=host,
        port=port,
        dbname=database,
        user=user,
        password=password,
    )
    cur = conn.cursor()
    
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
        
    conn.commit()
    print("Done!")
    cur.close()
    conn.close()

if __name__ == '__main__':
    run()
