"""
Cleans up Railway DB test data.
Deletes everything except superadmin, then resets sequences.
Run: python cleanup_railway.py "postgresql://postgres:PASSWORD@host:PORT/railway"
"""
import psycopg2
import psycopg2.extras
import sys

if len(sys.argv) < 2:
    URL = input("Paste Railway DATABASE_URL: ").strip()
else:
    URL = sys.argv[1]

conn = psycopg2.connect(URL, sslmode="require")
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

print("=== Railway DB Cleanup ===\n")

steps = [
    # 1. Delete documents linked to test enrollments
    ("enrollment_documents",    "DELETE FROM enrollment_documents WHERE enrollment_id IN (SELECT enrollment_id FROM enrollments WHERE branch_id IS NOT NULL)"),
    # 2. Delete student accounts
    ("student_accounts",        "DELETE FROM student_accounts"),
    # 3. Delete parent-student links
    ("parent_student",          "DELETE FROM parent_student"),
    # 4. Delete reservations (if any)
    ("reservations",            "DELETE FROM reservations"),
    # 5. Delete payments (if any)
    ("payments",                "DELETE FROM payments"),
    # 6. Delete enrollments
    ("enrollments",             "DELETE FROM enrollments"),
    # 7. Delete all users EXCEPT superadmin (user_id=1)
    ("users (keep superadmin)", "DELETE FROM users WHERE user_id != 1"),
]

for label, sql in steps:
    try:
        cur.execute(sql)
        count = cur.rowcount
        conn.commit()
        print(f"  OK  [{count:3d} rows] — {label}")
    except Exception as e:
        conn.rollback()
        print(f"  SKIP             — {label}: {str(e).strip().splitlines()[0]}")

# Reset sequences so next IDs start fresh
print("\nResetting sequences...")
sequences = [
    ("enrollments_enrollment_id_seq", 1),
    ("users_user_id_seq",             2),   # superadmin is 1, next starts at 2
    ("student_accounts_account_id_seq", 1),
    ("enrollment_documents_doc_id_seq", 1),
]
for seq_name, restart_val in sequences:
    try:
        cur.execute(f"ALTER SEQUENCE {seq_name} RESTART WITH {restart_val}")
        conn.commit()
        print(f"  OK  — {seq_name} restarted at {restart_val}")
    except Exception as e:
        conn.rollback()
        print(f"  SKIP — {seq_name}: {str(e).strip().splitlines()[0]}")

# Final check
cur.execute("SELECT user_id, username, role FROM users ORDER BY user_id")
remaining = cur.fetchall()
print(f"\n=== Remaining users: {len(remaining)} ===")
for r in remaining:
    print(f"  [{r['user_id']}] {r['username']:<30} {r['role']}")

cur.close()
conn.close()
print("\nDone.")
