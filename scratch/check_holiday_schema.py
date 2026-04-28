import psycopg2
from db import get_db_connection

def check_schema():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'holidays'")
        columns = cur.fetchall()
        for col in columns:
            print(col)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    check_schema()
