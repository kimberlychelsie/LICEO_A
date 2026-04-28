import db
conn = db.get_db_connection()
cur = conn.cursor()
try:
    cur.execute("CREATE TABLE IF NOT EXISTS test_table (id SERIAL PRIMARY KEY)")
    conn.commit()
    print("Table created successfully.")
    cur.execute("DROP TABLE test_table")
    conn.commit()
except Exception as e:
    conn.rollback()
    print(f"Failed: {e}")
finally:
    cur.close()
    conn.close()
