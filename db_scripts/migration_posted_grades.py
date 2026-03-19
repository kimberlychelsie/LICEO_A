import os
import sys
import psycopg2
from psycopg2 import extras

# Add parent directory to sys.path to easily import db.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from db import get_db_connection

def migrate():
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # 1. Add units to subjects
        # print("Adding units column to subjects...")
        # cur.execute("ALTER TABLE public.subjects ADD COLUMN IF NOT EXISTS units INTEGER DEFAULT 3;")
        
        # 2. Create posted_grades table
        print("Creating posted_grades table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS public.posted_grades (
                id SERIAL PRIMARY KEY,
                enrollment_id INTEGER NOT NULL,
                section_id INTEGER NOT NULL,
                subject_id INTEGER NOT NULL,
                grading_period CHARACTER VARYING(10) NOT NULL,
                grade NUMERIC(5,2) NOT NULL,
                posted_by INTEGER,
                posted_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
                UNIQUE(enrollment_id, subject_id, grading_period)
            );
        """)
        
        conn.commit()
        print("Migration completed successfully.")
    except Exception as e:
        conn.rollback()
        print("Migration failed:", e)
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    migrate()
