import os
import psycopg2
from psycopg2 import extras

def debug_db():
    host = os.getenv("DB_HOST", "127.0.0.1")
    port = int(os.getenv("DB_PORT", "5432"))
    database = os.getenv("DB_NAME", "liceo_db")
    user = os.getenv("DB_USER", "liceo_db")
    password = os.getenv("DB_PASSWORD", "1234")

    print(f"Connecting to {database} as {user}...")
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            dbname=database,
            user=user,
            password=password,
        )
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
            # Check table existence
            cur.execute("SELECT tablename FROM pg_catalog.pg_tables WHERE tablename = 'daily_attendance'")
            table = cur.fetchone()
            if not table:
                print("Table 'daily_attendance' does NOT exist.")
            else:
                print("Table 'daily_attendance' exists.")
                
                # Try a simple select
                try:
                    cur.execute("SELECT 1 FROM daily_attendance LIMIT 1")
                    print("SELECT on daily_attendance successful.")
                except Exception as e:
                    print(f"SELECT on daily_attendance failed: {e}")
                    conn.rollback()

            # Check current user and privileges
            cur.execute("SELECT current_user")
            print(f"Current User: {cur.fetchone()['current_user']}")
            
            cur.execute("SELECT table_name, grantee, privilege_type FROM information_schema.table_privileges WHERE table_name = 'daily_attendance'")
            privs = cur.fetchall()
            print("Privileges on daily_attendance:")
            for p in privs:
                print(f"  {p['grantee']}: {p['privilege_type']}")

        conn.close()
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    debug_db()
