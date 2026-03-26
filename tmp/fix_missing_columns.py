import psycopg2

URL = "postgresql://postgres:puixywJTqFOFSPxiXAgSZRYiyyUqaXvH@switchyard.proxy.rlwy.net:25993/railway"

def fix():
    commands = [
        "ALTER TABLE teacher_announcements ADD COLUMN year_id INTEGER",
        "ALTER TABLE grading_weights ADD COLUMN year_id integer",
        "ALTER TABLE grading_weights ADD CONSTRAINT grading_weights_full_unique UNIQUE (teacher_id, section_id, subject_id, grading_period, year_id)",
        "ALTER TABLE attendance_scores ADD COLUMN year_id integer",
        "ALTER TABLE attendance_scores ADD CONSTRAINT attendance_scores_unique UNIQUE (enrollment_id, subject_id, grading_period, year_id)",
        "ALTER TABLE attendance_scores ADD COLUMN updated_at timestamp with time zone",
        "ALTER TABLE participation_scores ADD COLUMN year_id integer",
        "ALTER TABLE participation_scores ADD CONSTRAINT participation_scores_unique UNIQUE (enrollment_id, subject_id, grading_period, year_id)",
        "ALTER TABLE participation_scores ADD COLUMN updated_at timestamp with time zone",
        "ALTER TABLE posted_grades ADD COLUMN section_id integer",
        "ALTER TABLE posted_grades ADD COLUMN year_id integer",
        "ALTER TABLE posted_grades ADD COLUMN posted_by integer",
        "ALTER TABLE posted_grades ADD CONSTRAINT posted_grades_section_id_fkey FOREIGN KEY (section_id) REFERENCES sections(section_id) ON DELETE CASCADE",
        "ALTER TABLE posted_grades ADD CONSTRAINT posted_grades_unique UNIQUE (enrollment_id, subject_id, grading_period, year_id)"
    ]

    try:
        conn = psycopg2.connect(URL)
        cur = conn.cursor()
        for cmd in commands:
            print(f"Executing: {cmd}")
            try:
                cur.execute(cmd)
                conn.commit()
                print("  Success")
            except Exception as e:
                conn.rollback()
                if "already exists" in str(e).lower():
                    print("  Skipped: Already exists")
                else:
                    print(f"  Failed: {e}")
        
        # Finally try to make teacher_announcements.year_id NOT NULL if it was just added
        # and table is empty.
        try:
            cur.execute("SELECT count(*) FROM teacher_announcements")
            if cur.fetchone()[0] == 0:
                print("Setting teacher_announcements.year_id to NOT NULL...")
                cur.execute("ALTER TABLE teacher_announcements ALTER COLUMN year_id SET NOT NULL")
                conn.commit()
        except:
            conn.rollback()

        conn.close()
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    fix()
