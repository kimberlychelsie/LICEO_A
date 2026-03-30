import psycopg2
import os
from dotenv import load_dotenv

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:puixywJTqFOFSPxiXAgSZRYiyyUqaXvH@switchyard.proxy.rlwy.net:25993/railway")

def check_enrollments_types():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'enrollments' AND table_schema = 'public'")
        cols = cur.fetchall()
        for col, dtype in cols:
            print(f"{col}: {dtype}")
        conn.close()
    except Exception as e:
        print(f"Error checking types: {e}")

if __name__ == "__main__":
    check_enrollments_types()
