import psycopg2
import os
from dotenv import load_dotenv

# Use the environment variable for DATABASE_URL if available, otherwise use the one from check_all_columns.py
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:puixywJTqFOFSPxiXAgSZRYiyyUqaXvH@switchyard.proxy.rlwy.net:25993/railway")

def check_enrollments_columns():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'enrollments' AND table_schema = 'public'")
        cols = [r[0] for r in cur.fetchall()]
        print(f"Enrollments Columns: {', '.join(cols)}")
        conn.close()
    except Exception as e:
        print(f"Error checking columns: {e}")

if __name__ == "__main__":
    check_enrollments_columns()
