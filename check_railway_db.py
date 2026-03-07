import psycopg2
import psycopg2.extras

URL = input("Paste Railway DATABASE_URL: ").strip()

conn = psycopg2.connect(URL, sslmode="require")
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

cur.execute("SELECT user_id, username, role, branch_id FROM users ORDER BY user_id")
rows = cur.fetchall()
print(f"Total users: {len(rows)}")
for r in rows:
    print(f"  [{r['user_id']}] {r['username']:<30}  role={r['role']:<15}  branch={r['branch_id']}")

cur.execute("SELECT COUNT(*) as c FROM enrollments")
enroll_count = cur.fetchone()["c"]
print(f"\nTotal enrollments: {enroll_count}")

cur.close()
conn.close()
