
import os
import sys
import psycopg2

URL = os.environ.get("DATABASE_URL") or (sys.argv[1] if len(sys.argv) > 1 else "").strip() or input("Paste DATABASE_URL: ").strip()
if not URL:
    sys.exit("DATABASE_URL required (env, argv, or prompt).")

def check_table(table_name):
    print(f"\nTABLE: {table_name}")
    try:
        conn = psycopg2.connect(URL, sslmode="require")
        cur = conn.cursor()
        cur.execute(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_schema='public' AND table_name = '{table_name}' ORDER BY column_name")
        cols = cur.fetchall()
        if not cols:
            print("  NOT FOUND")
        for col in cols:
            print(f"  - {col[0]} ({col[1]})")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"  ERROR: {e}")

tables = ["sections", "student_accounts", "enrollments", "enrollment_documents", "grade_levels", "users"]
for t in tables:
    check_table(t)
