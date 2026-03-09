import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor

def main():
    URL = os.environ.get("DATABASE_URL") or (sys.argv[1] if len(sys.argv) > 1 else "").strip() or input("Paste DATABASE_URL: ").strip()
    if not URL:
        sys.exit("DATABASE_URL required (env, argv, or prompt).")
    conn = psycopg2.connect(URL, sslmode="require")
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    # Check recent enrollments that don't have a student account created yet
    cursor.execute("""
        SELECT e.enrollment_id, e.branch_id, e.status, e.student_name, e.grade_level
        FROM enrollments e
        WHERE e.status IN ('approved', 'pending')
        ORDER BY e.created_at DESC
        LIMIT 5;
    """)
    enrollments = cursor.fetchall()
    print("--- RECENT ENROLLMENTS ---")
    for e in enrollments:
        print(e)
        # Check their documents
        eid = e['enrollment_id']
        cursor.execute("SELECT * FROM enrollment_documents WHERE enrollment_id=%s", (eid,))
        docs = cursor.fetchall()
        print(f"Documents for enrollment {eid}: {len(docs)}")
        
        # Check what happens if we simulate student account creation
        cursor.execute("SELECT branch_code FROM branches WHERE branch_id=%s", (e['branch_id'],))
        brow = cursor.fetchone()
        branch_code = brow['branch_code'] if (brow and brow.get('branch_code')) else f"B{e['branch_id']}"
        print(f"Branch code: {branch_code}")

    # Check student_accounts schema
    cursor.execute("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = 'student_accounts';
    """)
    print("\n--- STUDENT_ACCOUNTS SCHEMA ---")
    for col in cursor.fetchall():
        print(col)

    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()
