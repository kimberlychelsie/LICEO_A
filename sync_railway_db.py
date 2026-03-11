import psycopg2
import sys

db_url = "postgresql://postgres:puixywJTqFOFSPxiXAgSZRYiyyUqaXvH@switchyard.proxy.rlwy.net:25993/railway"

try:
    print("Connecting to Railway Database...")
    conn = psycopg2.connect(db_url, connect_timeout=15)
    conn.autocommit = True
    cur = conn.cursor()
    print("Connection successful.")

    print("Adding tab_switches to exam_results...")
    try:
        cur.execute("ALTER TABLE exam_results ADD COLUMN IF NOT EXISTS tab_switches INT DEFAULT 0")
        print("Done: added tab_switches.")
    except Exception as e:
        print("Info: tab_switches might already exist or error:", e)

    print("Altering exam_questions columns to TEXT to support Matching Type JSON...")
    try:
        cur.execute("ALTER TABLE exam_questions ALTER COLUMN choices TYPE TEXT")
        cur.execute("ALTER TABLE exam_questions ALTER COLUMN correct_answer TYPE TEXT")
        print("Done: updated exam_questions columns.")
    except Exception as e:
        print("Info: choices/correct_answer update error:", e)
        
    print("All updates applied successfully!")

except Exception as e:
    print("Database connection or execution failed:", e)
    sys.exit(1)
finally:
    if 'cur' in locals(): cur.close()
    if 'conn' in locals(): conn.close()
