import os
import sys

# Add parent directory to sys.path to easily import db.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from db import get_db_connection

def create_tables():
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Create activities table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS public.activities (
                activity_id SERIAL PRIMARY KEY,
                branch_id INTEGER,
                section_id INTEGER,
                subject_id INTEGER,
                teacher_id INTEGER,
                title CHARACTER VARYING(255) NOT NULL,
                category CHARACTER VARYING(100),
                instructions TEXT,
                max_score INTEGER DEFAULT 100,
                due_date TIMESTAMP WITHOUT TIME ZONE,
                allow_resubmission BOOLEAN DEFAULT TRUE,
                allowed_file_types CHARACTER VARYING(255),
                attachment_path CHARACTER VARYING(500),
                status CHARACTER VARYING(50) DEFAULT 'Draft',
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
                updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now()
            );
        """)
        
        # Create activity_submissions table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS public.activity_submissions (
                submission_id SERIAL PRIMARY KEY,
                activity_id INTEGER REFERENCES public.activities(activity_id) ON DELETE CASCADE,
                student_id INTEGER,
                enrollment_id INTEGER,
                file_path CHARACTER VARYING(500),
                original_filename CHARACTER VARYING(255),
                submitted_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
                is_late BOOLEAN DEFAULT FALSE,
                attempt_no INTEGER DEFAULT 1,
                is_active BOOLEAN DEFAULT TRUE,
                status CHARACTER VARYING(50) DEFAULT 'Submitted',
                feedback TEXT,
                graded_at TIMESTAMP WITHOUT TIME ZONE,
                graded_by INTEGER
            );
        """)
        
        # Create activity_grades table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS public.activity_grades (
                grade_id SERIAL PRIMARY KEY,
                submission_id INTEGER REFERENCES public.activity_submissions(submission_id) ON DELETE CASCADE,
                activity_id INTEGER REFERENCES public.activities(activity_id) ON DELETE CASCADE,
                student_id INTEGER,
                raw_score NUMERIC(5,2),
                max_score INTEGER,
                percentage NUMERIC(5,2),
                remarks TEXT,
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
                updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now()
            );
        """)
        
        conn.commit()
        print("Activities tables created successfully.")
    except Exception as e:
        conn.rollback()
        print("Error creating tables:", e)
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    create_tables()
