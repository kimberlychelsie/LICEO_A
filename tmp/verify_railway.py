import psycopg2
import sys

URL = "postgresql://postgres:puixywJTqFOFSPxiXAgSZRYiyyUqaXvH@switchyard.proxy.rlwy.net:25993/railway"

def verify():
    try:
        conn = psycopg2.connect(URL)
        cur = conn.cursor()

        tables_to_check = {
            'teacher_announcements': ['year_id'],
            'grading_weights': ['year_id'],
            'attendance_scores': ['year_id', 'updated_at'],
            'participation_scores': ['year_id', 'updated_at'],
            'posted_grades': ['section_id', 'year_id', 'posted_by']
        }

        for table, cols in tables_to_check.items():
            print(f"Verifying {table}...")
            cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table}'")
            existing_cols = [r[0] for r in cur.fetchall()]
            for col in cols:
                if col in existing_cols:
                    print(f"  [OK] {col} exists")
                else:
                    print(f"  [FAIL] {col} missing")

        cur.close()
        conn.close()
    except Exception as e:
        print(f"Verification failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    verify()
