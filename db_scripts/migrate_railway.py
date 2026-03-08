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
