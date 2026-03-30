import psycopg2
import os
import json

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:puixywJTqFOFSPxiXAgSZRYiyyUqaXvH@switchyard.proxy.rlwy.net:25993/railway")

def check_student_data():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT dob, enroll_date FROM enrollments WHERE student_name ILIKE '%Mamaril%' LIMIT 1")
        row = cur.fetchone()
        if row:
            print(f"DOB: {row['dob']} (Type: {type(row['dob'])})")
            print(f"Enroll Date: {row['enroll_date']} (Type: {type(row['enroll_date'])})")
        else:
            print("Student not found.")
        conn.close()
    except Exception as e:
        print(f"Error checking student data: {e}")

if __name__ == "__main__":
    import psycopg2.extras
    check_student_data()
