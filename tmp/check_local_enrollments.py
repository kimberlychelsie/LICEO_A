import psycopg2
import os

def check_local_enrollments_columns():
    host = os.getenv("DB_HOST", "127.0.0.1")
    port = int(os.getenv("DB_PORT", "5432"))
    database = os.getenv("DB_NAME", "liceo_db")
    user = os.getenv("DB_USER", "liceo_db")
    password = os.getenv("DB_PASSWORD", "liceo123")

    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            dbname=database,
            user=user,
            password=password,
        )
        cur = conn.cursor()
        cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'enrollments' AND table_schema = 'public'")
        cols = cur.fetchall()
        print("Local Enrollments Columns:")
        for col, dtype in cols:
            print(f"{col}: {dtype}")
        conn.close()
    except Exception as e:
        print(f"Error checking local columns: {e}")

if __name__ == "__main__":
    check_local_enrollments_columns()
