import psycopg2
import psycopg2.extras
import sys

if len(sys.argv) < 2:
    URL = input("Paste Railway DATABASE_URL: ").strip()
else:
    URL = sys.argv[1]

conn = psycopg2.connect(URL, sslmode="require")
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

cur.execute("SELECT branch_id, branch_name, status FROM branches ORDER BY branch_id")
branches = cur.fetchall()
print("=== Branches ===")
for b in branches:
    print(f"  [{b['branch_id']}] {b['branch_name']:<30} status={b['status']}")

cur.execute("SELECT user_id, username, role, branch_id FROM users ORDER BY user_id")
users = cur.fetchall()
print("\n=== Users ===")
for u in users:
    print(f"  [{u['user_id']}] {u['username']:<30} role={u['role']:<15} branch={u['branch_id']}")

cur.close()
conn.close()
