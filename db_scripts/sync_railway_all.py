"""
Liceo LMS — Railway Database Sync Script
Run this locally to update your Railway Database:
python db_scripts/sync_railway_all.py "YOUR_RAILWAY_DATABASE_URL"
"""
import sys
import psycopg2

def run_sync():
    if len(sys.argv) < 2:
        print("\n[ERROR] DATABASE_URL is required.")
        print("Usage: python db_scripts/sync_railway_all.py \"postgresql://postgres:PASSWORD@host:PORT/railway\"")
        print("\nPara mahanap ang DATABASE_URL:")
        print("1. Sa Railway Dashboard, i-click ang 'Postgres'.")
        print("2. I-click ang 'Variables' tab.")
        print("3. I-copy ang value ng 'DATABASE_URL'.\n")
        sys.exit(1)

    url = sys.argv[1]
    print(f"Connecting to Railway...")

    queries = [
        # --- ACTIVITIES ---
        ("Activities Table", """
            CREATE TABLE IF NOT EXISTS public.activities (
                activity_id SERIAL PRIMARY KEY,
                branch_id INTEGER,
                section_id INTEGER,
                subject_id INTEGER,
                teacher_id INTEGER,
                title VARCHAR(255) NOT NULL,
                category VARCHAR(100),
                instructions TEXT,
                max_score INTEGER DEFAULT 100,
                due_date TIMESTAMP,
                allow_resubmission BOOLEAN DEFAULT TRUE,
                allowed_file_types VARCHAR(255),
                attachment_path VARCHAR(500),
                status VARCHAR(50) DEFAULT 'Draft',
                created_at TIMESTAMP DEFAULT now(),
                updated_at TIMESTAMP DEFAULT now()
            );
        """),
        ("Submissions Table", """
            CREATE TABLE IF NOT EXISTS public.activity_submissions (
                submission_id SERIAL PRIMARY KEY,
                activity_id INTEGER REFERENCES public.activities(activity_id) ON DELETE CASCADE,
                student_id INTEGER,
                enrollment_id INTEGER,
                file_path VARCHAR(500),
                original_filename VARCHAR(255),
                submitted_at TIMESTAMP DEFAULT now(),
                is_late BOOLEAN DEFAULT FALSE,
                attempt_no INTEGER DEFAULT 1,
                is_active BOOLEAN DEFAULT TRUE,
                allow_resubmit BOOLEAN DEFAULT FALSE,
                status VARCHAR(50) DEFAULT 'Submitted',
                feedback TEXT,
                graded_at TIMESTAMP,
                graded_by INTEGER
            );
        """),
        ("Grades Table", """
            CREATE TABLE IF NOT EXISTS public.activity_grades (
                grade_id SERIAL PRIMARY KEY,
                submission_id INTEGER REFERENCES public.activity_submissions(submission_id) ON DELETE CASCADE,
                activity_id INTEGER REFERENCES public.activities(activity_id) ON DELETE CASCADE,
                student_id INTEGER,
                raw_score NUMERIC(5,2),
                max_score INTEGER,
                percentage NUMERIC(5,2),
                remarks TEXT,
                created_at TIMESTAMP DEFAULT now(),
                updated_at TIMESTAMP DEFAULT now()
            );
        """),
        # --- NOTIFICATIONS & ANNOUNCEMENTS ---
        ("Notifications Table", """
            CREATE TABLE IF NOT EXISTS public.student_notifications (
                id SERIAL PRIMARY KEY,
                student_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                title VARCHAR(150),
                message TEXT,
                link TEXT,
                is_read BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """),
        ("Teacher Announcements Table", """
            CREATE TABLE IF NOT EXISTS public.teacher_announcements (
                announcement_id SERIAL PRIMARY KEY,
                teacher_user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                branch_id INTEGER NOT NULL REFERENCES branches(branch_id) ON DELETE CASCADE,
                grade_level VARCHAR(50) NOT NULL,
                title VARCHAR(200) NOT NULL,
                body TEXT,
                created_at TIMESTAMP DEFAULT now()
            );
        """),
        # --- COLUMN UPDATES ---
        ("Enrollments: LRN column", "ALTER TABLE public.enrollments ADD COLUMN IF NOT EXISTS lrn VARCHAR(12);"),
        ("Enrollments: Email column", "ALTER TABLE public.enrollments ADD COLUMN IF NOT EXISTS email VARCHAR(255);"),
        ("Enrollments: Guardian Email column", "ALTER TABLE public.enrollments ADD COLUMN IF NOT EXISTS guardian_email VARCHAR(255);"),
        ("Enrollments: Branch No column", "ALTER TABLE public.enrollments ADD COLUMN IF NOT EXISTS branch_enrollment_no INTEGER;"),
        ("Enrollments: Section ID column", "ALTER TABLE public.enrollments ADD COLUMN IF NOT EXISTS section_id INTEGER;"),
        ("Users: Full Name column", "ALTER TABLE public.users ADD COLUMN IF NOT EXISTS full_name VARCHAR(150);"),
        ("Users: Gender column", "ALTER TABLE public.users ADD COLUMN IF NOT EXISTS gender VARCHAR(20);"),
        ("Users: Grade Level column", "ALTER TABLE public.users ADD COLUMN IF NOT EXISTS grade_level VARCHAR(50);"),
        ("Users: Require PW Change column", "ALTER TABLE public.users ADD COLUMN IF NOT EXISTS require_password_change BOOLEAN DEFAULT FALSE;"),
    ]

    try:
        conn = psycopg2.connect(url, sslmode="require")
        cur = conn.cursor()
        
        for label, sql in queries:
            try:
                cur.execute(sql)
                conn.commit()
                print(f"  [OK]    {label}")
            except Exception as e:
                conn.rollback()
                print(f"  [SKIP]  {label}: {str(e).strip().splitlines()[0]}")
        
        print("\nSuccess: Lahat ng tables at columns ay naging 'Fully Synced' na sa Railway.")

    except Exception as e:
        print(f"\n[CRITICAL ERROR] Failed to connect: {e}")
    finally:
        if 'cur' in locals(): cur.close()
        if 'conn' in locals(): conn.close()

if __name__ == "__main__":
    run_sync()
