import psycopg2
from db import get_db_connection

def migrate():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Check if status column exists
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'holidays' AND column_name = 'status'")
        if not cur.fetchone():
            print("Adding status column to holidays table...")
            cur.execute("ALTER TABLE holidays ADD COLUMN status VARCHAR(20) DEFAULT 'active'")
            conn.commit()
            print("Migration successful.")
        else:
            print("Status column already exists.")
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    migrate()
