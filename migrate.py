"""
One-time migration script.
Run: python migrate.py
Uses your existing .env DATABASE_URL to connect to Railway Postgres.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

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
