from db import get_db_connection
import psycopg2.extras

def check():
    db = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'users'")
        cols = [r['column_name'] for r in cur.fetchall()]
        print(f"Users columns: {cols}")
        
        cur.execute("SELECT * FROM users LIMIT 1")
        row = cur.fetchone()
        print(f"Sample user row: {row}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        cur.close()
        db.close()

if __name__ == "__main__":
    check()
