"""
One-time migration script.
Run: python migrate.py
Uses your existing .env DATABASE_URL to connect to Railway Postgres.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from db import get_db_connection

MIGRATIONS = [
    # Add lrn column if not exists
    """
    ALTER TABLE public.enrollments
        ADD COLUMN IF NOT EXISTS lrn character varying(12);
    """,
    # Add email column if not exists
    """
    ALTER TABLE public.enrollments
        ADD COLUMN IF NOT EXISTS email character varying(255);
    """,
    # Add guardian_email column if not exists
    """
    ALTER TABLE public.enrollments
        ADD COLUMN IF NOT EXISTS guardian_email character varying(255);
    """,
    # Add branch_code to branches if not exists
    """
    ALTER TABLE public.branches
        ADD COLUMN IF NOT EXISTS branch_code character varying(20);
    """,
    # ── Grading Period System ─────────────────────────────────────────────
    """
    ALTER TABLE public.activities ADD COLUMN IF NOT EXISTS grading_period VARCHAR(10);
    """,
    """
    ALTER TABLE public.exams ADD COLUMN IF NOT EXISTS grading_period VARCHAR(10);
    """,
    """
    CREATE TABLE IF NOT EXISTS public.grading_weights (
        weight_id         SERIAL PRIMARY KEY,
        teacher_id        INTEGER NOT NULL,
        branch_id         INTEGER NOT NULL,
        section_id        INTEGER NOT NULL,
        subject_id        INTEGER NOT NULL,
        grading_period    VARCHAR(10) NOT NULL,
        quiz_pct          NUMERIC(5,2) NOT NULL DEFAULT 0,
        exam_pct          NUMERIC(5,2) NOT NULL DEFAULT 0,
        activity_pct      NUMERIC(5,2) NOT NULL DEFAULT 0,
        participation_pct NUMERIC(5,2) NOT NULL DEFAULT 0,
        attendance_pct    NUMERIC(5,2) NOT NULL DEFAULT 0,
        updated_at        TIMESTAMP DEFAULT NOW(),
        CONSTRAINT uq_grading_weights UNIQUE (teacher_id, section_id, subject_id, grading_period)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS public.participation_scores (
        id             SERIAL PRIMARY KEY,
        teacher_id     INTEGER NOT NULL,
        enrollment_id  INTEGER NOT NULL,
        section_id     INTEGER NOT NULL,
        subject_id     INTEGER NOT NULL,
        grading_period VARCHAR(10) NOT NULL,
        score          NUMERIC(5,2) NOT NULL DEFAULT 0,
        updated_at     TIMESTAMP DEFAULT NOW(),
        CONSTRAINT uq_participation UNIQUE (enrollment_id, subject_id, grading_period)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS public.attendance_scores (
        id             SERIAL PRIMARY KEY,
        teacher_id     INTEGER NOT NULL,
        enrollment_id  INTEGER NOT NULL,
        section_id     INTEGER NOT NULL,
        subject_id     INTEGER NOT NULL,
        grading_period VARCHAR(10) NOT NULL,
        score          NUMERIC(5,2) NOT NULL DEFAULT 0,
        updated_at     TIMESTAMP DEFAULT NOW(),
        CONSTRAINT uq_attendance UNIQUE (enrollment_id, subject_id, grading_period)
    );
    """,
]

def run():
    db = get_db_connection()
    cursor = db.cursor()
    success = 0
    for i, sql in enumerate(MIGRATIONS, 1):
        try:
            cursor.execute(sql)
            db.commit()
            label = sql.strip().split('\n')[0][:70]
            print(f"  [{i}/{len(MIGRATIONS)}] OK  — {label}")
            success += 1
        except Exception as e:
            db.rollback()
            print(f"  [{i}/{len(MIGRATIONS)}] SKIP — {str(e).strip()}")

    cursor.close()
    db.close()
    print(f"\nDone. {success}/{len(MIGRATIONS)} migrations applied.")

if __name__ == "__main__":
    print("Running migrations on Railway DB...\n")
    run()
