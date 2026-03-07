"""
Railway DB Setup:
- Deletes Liceo de Liliw branch (branch_id=2) and all related data
- Creates branch_admin account for Liceo de Majayjay (branch_id=1)

Run: python setup_railway_branches.py "postgresql://postgres:...@.../railway"
"""
import psycopg2
import psycopg2.extras
import sys
import secrets
import string
from werkzeug.security import generate_password_hash

if len(sys.argv) < 2:
    URL = input("Paste Railway DATABASE_URL: ").strip()
else:
    URL = sys.argv[1]

conn = psycopg2.connect(URL, sslmode="require")
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

print("=== Railway Branch Setup ===\n")

# ── 1. Delete Liliw branch (branch_id=2) ──────────────────────
print("Step 1: Removing Liceo de Liliw branch...")
LILIW_ID = 2

delete_steps = [
    ("enrollment_documents (liliw)", """
        DELETE FROM enrollment_documents
        WHERE enrollment_id IN (SELECT enrollment_id FROM enrollments WHERE branch_id=%s)
    """, (LILIW_ID,)),
    ("student_accounts (liliw)", "DELETE FROM student_accounts WHERE branch_id=%s", (LILIW_ID,)),
    ("reservations (liliw)", "DELETE FROM reservations WHERE branch_id=%s", (LILIW_ID,)),
    ("payments (liliw)", "DELETE FROM payments WHERE branch_id=%s", (LILIW_ID,)),
    ("enrollments (liliw)", "DELETE FROM enrollments WHERE branch_id=%s", (LILIW_ID,)),
    ("chatbot_faqs (liliw)", "DELETE FROM chatbot_faqs WHERE branch_id=%s", (LILIW_ID,)),
    ("inventory (liliw)", "DELETE FROM inventory_items WHERE branch_id=%s", (LILIW_ID,)),
    ("users (liliw)", "DELETE FROM users WHERE branch_id=%s", (LILIW_ID,)),
    ("sections (liliw)", "DELETE FROM sections WHERE branch_id=%s", (LILIW_ID,)),
    ("grade_levels (liliw)", "DELETE FROM grade_levels WHERE branch_id=%s", (LILIW_ID,)),
    ("branches (liliw)", "DELETE FROM branches WHERE branch_id=%s", (LILIW_ID,)),
]

for label, sql, params in delete_steps:
    try:
        cur.execute(sql, params)
        conn.commit()
        print(f"  OK  [{cur.rowcount:2d} rows] — {label}")
    except Exception as e:
        conn.rollback()
        print(f"  SKIP             — {label}: {str(e).strip().splitlines()[0]}")

# ── 2. Create branch_admin for Majayjay ───────────────────────
print("\nStep 2: Creating branch_admin for Liceo de Majayjay...")

# Check if admin already exists
cur.execute("SELECT username FROM users WHERE branch_id=1 AND role='branch_admin'")
existing = cur.fetchone()

if existing:
    print(f"  SKIP — branch_admin already exists: {existing['username']}")
else:
    def gen_password(n=10):
        chars = string.ascii_letters + string.digits
        return ''.join(secrets.choice(chars) for _ in range(n))

    username   = "liceo_de_majayjay_admin"
    temp_pass  = gen_password()
    hashed     = generate_password_hash(temp_pass)

    try:
        cur.execute("""
            INSERT INTO users (branch_id, username, password, role, require_password_change)
            VALUES (%s, %s, %s, 'branch_admin', TRUE)
        """, (1, username, hashed))
        conn.commit()
        print(f"  OK  — Created branch_admin successfully")
        print(f"\n  ┌─────────────────────────────────────────┐")
        print(f"  │  Branch Admin Credentials (Majayjay)    │")
        print(f"  │                                         │")
        print(f"  │  Username : {username:<28}│")
        print(f"  │  Password : {temp_pass:<28}│")
        print(f"  │                                         │")
        print(f"  │  ⚠ User must change password on login  │")
        print(f"  └─────────────────────────────────────────┘")
    except Exception as e:
        conn.rollback()
        print(f"  ERROR — {str(e).strip()}")

# ── 3. Final state ────────────────────────────────────────────
print("\n=== Final State ===")
cur.execute("SELECT branch_id, branch_name, status FROM branches ORDER BY branch_id")
for b in cur.fetchall():
    print(f"  Branch [{b['branch_id']}] {b['branch_name']} — {b['status']}")

cur.execute("SELECT user_id, username, role, branch_id FROM users ORDER BY user_id")
for u in cur.fetchall():
    print(f"  User   [{u['user_id']}] {u['username']:<30} role={u['role']} branch={u['branch_id']}")

cur.close()
conn.close()
print("\nDone.")
