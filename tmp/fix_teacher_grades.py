import psycopg2
conn = psycopg2.connect('dbname=liceo_db user=liceo_db password=liceo123 host=127.0.0.1 port=5432')
cur = conn.cursor()

# Get all teachers with grade_level but no grade_level_id
cur.execute("SELECT user_id, grade_level, branch_id FROM users WHERE role = 'teacher' AND grade_level IS NOT NULL AND grade_level_id IS NULL")
teachers = cur.fetchall()

for uid, gname, bid in teachers:
    # Find matching grade_level_id in the same branch
    cur.execute("SELECT id FROM grade_levels WHERE name = %s AND branch_id = %s", (gname, bid))
    row = cur.fetchone()
    if row:
        cur.execute("UPDATE users SET grade_level_id = %s WHERE user_id = %s", (row[0], uid))
        print(f"Updated user {uid} to grade_level_id {row[0]}")
    else:
        # Try finding in general (if branch_id is null in grade_levels or something)
        cur.execute("SELECT id FROM grade_levels WHERE name = %s LIMIT 1", (gname,))
        row = cur.fetchone()
        if row:
            cur.execute("UPDATE users SET grade_level_id = %s WHERE user_id = %s", (row[0], uid))
            print(f"Updated user {uid} to grade_level_id {row[0]} (fallback)")

conn.commit()
cur.close()
conn.close()
