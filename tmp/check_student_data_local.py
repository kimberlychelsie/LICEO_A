import psycopg2
import psycopg2.extras
import os

def check_student_data_local():
    # From db.py defaults
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
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT enrollment_id, student_name, dob, enroll_date FROM enrollments WHERE grade_level = 'Grade 8' LIMIT 5")
        rows = cur.fetchall()
        for row in rows:
            print(f"ID: {row['enrollment_id']}, Name: {row['student_name']}, DOB: {row['dob']} (Type: {type(row['dob'])})")
        conn.close()
    except Exception as e:
        print(f"Error checking student data: {e}")

if __name__ == "__main__":
    check_student_data_local()
