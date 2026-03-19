"""
Railway Migration — run with the Railway DATABASE_URL:
    python migrate_railway.py "postgresql://postgres:PASSWORD@host:PORT/railway"
"""
import sys
import psycopg2

if len(sys.argv) < 2:
    print("Usage: python migrate_railway.py \"postgresql://postgres:...@.../railway\"")
    sys.exit(1)

DATABASE_URL = sys.argv[1]

MIGRATIONS = [
    ("lrn column", "ALTER TABLE public.enrollments ADD COLUMN IF NOT EXISTS lrn character varying(12);"),
    ("email column", "ALTER TABLE public.enrollments ADD COLUMN IF NOT EXISTS email character varying(255);"),
    ("guardian_email column", "ALTER TABLE public.enrollments ADD COLUMN IF NOT EXISTS guardian_email character varying(255);"),
    ("branch_code column", "ALTER TABLE public.branches ADD COLUMN IF NOT EXISTS branch_code character varying(20);"),
    ("doc_type column", "ALTER TABLE public.enrollment_documents ADD COLUMN IF NOT EXISTS doc_type character varying(255);"),

    # ── Grading Period System ─────────────────────────────────────────────
    ("grading_period on activities",
     "ALTER TABLE public.activities ADD COLUMN IF NOT EXISTS grading_period VARCHAR(10);"),
    ("grading_period on exams",
     "ALTER TABLE public.exams ADD COLUMN IF NOT EXISTS grading_period VARCHAR(10);"),

    ("grading_weights table", """
        CREATE TABLE IF NOT EXISTS public.grading_weights (
            weight_id         SERIAL PRIMARY KEY,
            teacher_id        INTEGER NOT NULL REFERENCES public.users(user_id) ON DELETE CASCADE,
            branch_id         INTEGER NOT NULL REFERENCES public.branches(branch_id) ON DELETE CASCADE,
            section_id        INTEGER NOT NULL REFERENCES public.sections(section_id) ON DELETE CASCADE,
            subject_id        INTEGER NOT NULL REFERENCES public.subjects(subject_id) ON DELETE CASCADE,
            grading_period    VARCHAR(10) NOT NULL,
            quiz_pct          NUMERIC(5,2) NOT NULL DEFAULT 0,
            exam_pct          NUMERIC(5,2) NOT NULL DEFAULT 0,
            activity_pct      NUMERIC(5,2) NOT NULL DEFAULT 0,
            participation_pct NUMERIC(5,2) NOT NULL DEFAULT 0,
            attendance_pct    NUMERIC(5,2) NOT NULL DEFAULT 0,
            updated_at        TIMESTAMP DEFAULT NOW(),
            CONSTRAINT uq_grading_weights UNIQUE (teacher_id, section_id, subject_id, grading_period)
        );
    """),

    ("participation_scores table", """
        CREATE TABLE IF NOT EXISTS public.participation_scores (
            id             SERIAL PRIMARY KEY,
            teacher_id     INTEGER NOT NULL REFERENCES public.users(user_id) ON DELETE CASCADE,
            enrollment_id  INTEGER NOT NULL REFERENCES public.enrollments(enrollment_id) ON DELETE CASCADE,
            section_id     INTEGER NOT NULL REFERENCES public.sections(section_id) ON DELETE CASCADE,
            subject_id     INTEGER NOT NULL REFERENCES public.subjects(subject_id) ON DELETE CASCADE,
            grading_period VARCHAR(10) NOT NULL,
            score          NUMERIC(5,2) NOT NULL DEFAULT 0,
            updated_at     TIMESTAMP DEFAULT NOW(),
            CONSTRAINT uq_participation UNIQUE (enrollment_id, subject_id, grading_period)
        );
    """),

    ("attendance_scores table", """
        CREATE TABLE IF NOT EXISTS public.attendance_scores (
            id             SERIAL PRIMARY KEY,
            teacher_id     INTEGER NOT NULL REFERENCES public.users(user_id) ON DELETE CASCADE,
            enrollment_id  INTEGER NOT NULL REFERENCES public.enrollments(enrollment_id) ON DELETE CASCADE,
            section_id     INTEGER NOT NULL REFERENCES public.sections(section_id) ON DELETE CASCADE,
            subject_id     INTEGER NOT NULL REFERENCES public.subjects(subject_id) ON DELETE CASCADE,
            grading_period VARCHAR(10) NOT NULL,
            score          NUMERIC(5,2) NOT NULL DEFAULT 0,
            updated_at     TIMESTAMP DEFAULT NOW(),
            CONSTRAINT uq_attendance UNIQUE (enrollment_id, subject_id, grading_period)
        );
    """),
]

print(f"Connecting to Railway...\n")
conn = psycopg2.connect(DATABASE_URL, sslmode="require")
cursor = conn.cursor()
success = 0

for label, sql in MIGRATIONS:
    try:
        cursor.execute(sql)
        conn.commit()
        print(f"  OK    — {label}")
        success += 1
    except Exception as e:
        conn.rollback()
        msg = str(e).strip().splitlines()[0]
        print(f"  SKIP  — {label}: {msg}")

cursor.close()
conn.close()
print(f"\nDone. {success}/{len(MIGRATIONS)} migrations applied on Railway.")
