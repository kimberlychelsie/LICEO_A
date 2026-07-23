"""
Migration: Fix grading_period values in Railway DB
Updates old "1st Grading", "2nd Grading", etc. → "1st", "2nd", "3rd"
Affects tables: activities, exams, grading_period_ranges
"""

import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = "postgresql://postgres:puixywJTqFOFSPxiXAgSZRYiyyUqaXvH@switchyard.proxy.rlwy.net:25993/railway"

FIX_SQL = [
    (
        "activities",
        """
        UPDATE activities
        SET grading_period = CASE
            WHEN grading_period ILIKE '%1st%' THEN '1st'
            WHEN grading_period ILIKE '%2nd%' THEN '2nd'
            WHEN grading_period ILIKE '%3rd%' THEN '3rd'
            WHEN grading_period ILIKE '%4th%' THEN '4th'
            ELSE grading_period
        END
        WHERE grading_period IS NOT NULL
          AND grading_period NOT IN ('1st', '2nd', '3rd', '4th')
        """
    ),
    (
        "exams (incl. quizzes)",
        """
        UPDATE exams
        SET grading_period = CASE
            WHEN grading_period ILIKE '%1st%' THEN '1st'
            WHEN grading_period ILIKE '%2nd%' THEN '2nd'
            WHEN grading_period ILIKE '%3rd%' THEN '3rd'
            WHEN grading_period ILIKE '%4th%' THEN '4th'
            ELSE grading_period
        END
        WHERE grading_period IS NOT NULL
          AND grading_period NOT IN ('1st', '2nd', '3rd', '4th')
        """
    ),
    (
        "grading_period_ranges",
        """
        UPDATE grading_period_ranges
        SET period_name = CASE
            WHEN period_name ILIKE '%1st%' THEN '1st'
            WHEN period_name ILIKE '%2nd%' THEN '2nd'
            WHEN period_name ILIKE '%3rd%' THEN '3rd'
            WHEN period_name ILIKE '%4th%' THEN '4th'
            ELSE period_name
        END
        WHERE period_name IS NOT NULL
          AND period_name NOT IN ('1st', '2nd', '3rd', '4th')
        """
    ),
]

def run():
    print("Connecting to Railway database...")
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    cur = conn.cursor()

    try:
        print("\n--- Starting migration ---\n")
        for table_label, sql in FIX_SQL:
            cur.execute(sql)
            rows_affected = cur.rowcount
            print(f"[OK]  [{table_label}]  {rows_affected} row(s) updated")

        conn.commit()
        print("\n[DONE] Migration committed successfully.")

    except Exception as e:
        conn.rollback()
        print(f"\n[ERROR] Rolled back: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    run()
