from dotenv import load_dotenv
load_dotenv()
from db import get_db_connection
import psycopg2.extras

def check_branches_table():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("SELECT * FROM branches LIMIT 1")
        row = cur.fetchone()
        if row:
            print("Columns in branches table:", list(row.keys()))
        else:
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'branches'")
            cols = cur.fetchall()
            print("Columns in branches table:", [c['column_name'] for c in cols])
    except Exception as e:
        print("Error checking branches table:", e)
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    check_branches_table()
