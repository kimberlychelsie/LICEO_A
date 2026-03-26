import psycopg2
import sys

URL = "postgresql://postgres:puixywJTqFOFSPxiXAgSZRYiyyUqaXvH@switchyard.proxy.rlwy.net:25993/railway"

def column_exists(cur, table, column):
    cur.execute(f"SELECT 1 FROM information_schema.columns WHERE table_name = '{table}' AND column_name = '{column}'")
    return cur.fetchone() is not None

def constraint_exists(cur, table, constraint):
    cur.execute(f"SELECT 1 FROM information_schema.table_constraints WHERE table_name = '{table}' AND constraint_name = '{constraint}'")
    return cur.fetchone() is not None

def migrate():
    try:
        conn = psycopg2.connect(URL)
        conn.autocommit = False
        cur = conn.cursor()

        print("Checking tables...")

        # 1. teacher_announcements
        if not column_exists(cur, 'teacher_announcements', 'year_id'):
            cur.execute("SELECT count(*) FROM teacher_announcements")
            count = cur.fetchone()[0]
            not_null = " NOT NULL" if count == 0 else ""
            print(f"Adding year_id to teacher_announcements ({not_null})...")
            cur.execute(f"ALTER TABLE teacher_announcements ADD COLUMN year_id INTEGER{not_null}")
        else:
            print("year_id already exists in teacher_announcements")

        # 2. grading_weights
        if not column_exists(cur, 'grading_weights', 'year_id'):
            print("Adding year_id to grading_weights...")
            cur.execute("ALTER TABLE grading_weights ADD COLUMN year_id integer")
        
        if not constraint_exists(cur, 'grading_weights', 'grading_weights_full_unique'):
            print("Adding unique constraint to grading_weights...")
            cur.execute("ALTER TABLE grading_weights ADD CONSTRAINT grading_weights_full_unique UNIQUE (teacher_id, section_id, subject_id, grading_period, year_id)")

        # 3. attendance_scores
        if not column_exists(cur, 'attendance_scores', 'year_id'):
            print("Adding year_id to attendance_scores...")
            cur.execute("ALTER TABLE attendance_scores ADD COLUMN year_id integer")
        
        if not constraint_exists(cur, 'attendance_scores', 'attendance_scores_unique'):
            print("Adding unique constraint to attendance_scores...")
            cur.execute("ALTER TABLE attendance_scores ADD CONSTRAINT attendance_scores_unique UNIQUE (enrollment_id, subject_id, grading_period, year_id)")
        
        if not column_exists(cur, 'attendance_scores', 'updated_at'):
            print("Adding updated_at to attendance_scores...")
            cur.execute("ALTER TABLE attendance_scores ADD COLUMN updated_at timestamp with time zone")

        # 4. participation_scores
        if not column_exists(cur, 'participation_scores', 'year_id'):
            print("Adding year_id to participation_scores...")
            cur.execute("ALTER TABLE participation_scores ADD COLUMN year_id integer")
        
        if not constraint_exists(cur, 'participation_scores', 'participation_scores_unique'):
            print("Adding unique constraint to participation_scores...")
            cur.execute("ALTER TABLE participation_scores ADD CONSTRAINT participation_scores_unique UNIQUE (enrollment_id, subject_id, grading_period, year_id)")
        
        if not column_exists(cur, 'participation_scores', 'updated_at'):
            print("Adding updated_at to participation_scores...")
            cur.execute("ALTER TABLE participation_scores ADD COLUMN updated_at timestamp with time zone")

        # 5. posted_grades
        if not column_exists(cur, 'posted_grades', 'section_id'):
            print("Adding section_id to posted_grades...")
            cur.execute("ALTER TABLE posted_grades ADD COLUMN section_id integer")
        
        if not column_exists(cur, 'posted_grades', 'year_id'):
            print("Adding year_id to posted_grades...")
            cur.execute("ALTER TABLE posted_grades ADD COLUMN year_id integer")
        
        if not column_exists(cur, 'posted_grades', 'posted_by'):
            print("Adding posted_by to posted_grades...")
            cur.execute("ALTER TABLE posted_grades ADD COLUMN posted_by integer")
        
        if not constraint_exists(cur, 'posted_grades', 'posted_grades_section_id_fkey'):
            print("Adding foreign key to posted_grades...")
            cur.execute("ALTER TABLE posted_grades ADD CONSTRAINT posted_grades_section_id_fkey FOREIGN KEY (section_id) REFERENCES sections(section_id) ON DELETE CASCADE")
        
        if not constraint_exists(cur, 'posted_grades', 'posted_grades_unique'):
            print("Adding unique constraint to posted_grades...")
            cur.execute("ALTER TABLE posted_grades ADD CONSTRAINT posted_grades_unique UNIQUE (enrollment_id, subject_id, grading_period, year_id)")

        # 6. GRANT
        print("Granting permissions...")
        try:
            cur.execute("GRANT USAGE, SELECT ON SEQUENCE posted_grades_grade_id_seq TO liceo_db")
        except Exception as e:
            print(f"Grant failed (maybe user doesn't exist or sequence doesn't exist): {e}")
            # We continue because this might be optional or already granted.
        
        conn.commit()
        print("Migration successful.")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Migration failed: {e}")
        # rollback is handled by the connection context or explicitly
        sys.exit(1)

if __name__ == "__main__":
    migrate()
