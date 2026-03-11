import psycopg2
db_url = 'postgresql://postgres:puixywJTqFOFSPxiXAgSZRYiyyUqaXvH@switchyard.proxy.rlwy.net:25993/railway'

try:
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    # Get all teachers with grade_level but no grade_level_id
    cur.execute("SELECT user_id, grade_level, branch_id FROM users WHERE role = 'teacher' AND grade_level IS NOT NULL AND grade_level_id IS NULL")
    teachers = cur.fetchall()
    
    print(f"Found {len(teachers)} teachers to update on Railway.")

    for uid, gname, bid in teachers:
        # Find matching grade_level_id in the same branch
        cur.execute("SELECT id FROM grade_levels WHERE name = %s AND branch_id = %s", (gname, bid))
        row = cur.fetchone()
        if row:
            cur.execute("UPDATE users SET grade_level_id = %s WHERE user_id = %s", (row[0], uid))
            print(f"Updated Railway user {uid} to grade_level_id {row[0]}")
        else:
            # Try finding in general (fallback)
            cur.execute("SELECT id FROM grade_levels WHERE name = %s LIMIT 1", (gname,))
            row = cur.fetchone()
            if row:
                cur.execute("UPDATE users SET grade_level_id = %s WHERE user_id = %s", (row[0], uid))
                print(f"Updated Railway user {uid} to grade_level_id {row[0]} (fallback)")

    conn.commit()
    print("Railway Data Sync Complete.")
    cur.close()
    conn.close()
except Exception as e:
    print(f"Railway Sync Error: {e}")
