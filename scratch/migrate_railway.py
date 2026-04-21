import psycopg2
import os

# Railway Connection String
DATABASE_URL = "postgresql://postgres:puixywJTqFOFSPxiXAgSZRYiyyUqaXvH@switchyard.proxy.rlwy.net:25993/railway"

def run_migration():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        print("Running: ALTER TABLE announcements ADD COLUMN IF NOT EXISTS audience TEXT NOT NULL DEFAULT 'all';")
        cur.execute("ALTER TABLE announcements ADD COLUMN IF NOT EXISTS audience TEXT NOT NULL DEFAULT 'all';")
        conn.commit()
        print("Migration successful on Railway!")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_migration()
