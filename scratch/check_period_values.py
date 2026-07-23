"""
Check: what grading_period values actually exist in Railway DB?
"""
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = "postgresql://postgres:puixywJTqFOFSPxiXAgSZRYiyyUqaXvH@switchyard.proxy.rlwy.net:25993/railway"

def run():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    print("=== activities.grading_period distinct values ===")
    cur.execute("SELECT DISTINCT grading_period, COUNT(*) as cnt FROM activities GROUP BY grading_period ORDER BY grading_period")
    for r in cur.fetchall():
        print(f"  [{repr(r['grading_period'])}]  count={r['cnt']}")

    print("\n=== exams.grading_period distinct values ===")
    cur.execute("SELECT DISTINCT grading_period, COUNT(*) as cnt FROM exams GROUP BY grading_period ORDER BY grading_period")
    for r in cur.fetchall():
        print(f"  [{repr(r['grading_period'])}]  count={r['cnt']}")

    print("\n=== grading_period_ranges.period_name distinct values ===")
    cur.execute("SELECT DISTINCT period_name, COUNT(*) as cnt FROM grading_period_ranges GROUP BY period_name ORDER BY period_name")
    for r in cur.fetchall():
        print(f"  [{repr(r['period_name'])}]  count={r['cnt']}")

    cur.close()
    conn.close()
    print("\n[DONE]")

if __name__ == "__main__":
    run()
