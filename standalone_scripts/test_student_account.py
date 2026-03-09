import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash
import secrets
import string

URL = os.environ.get("DATABASE_URL") or input("Paste DATABASE_URL: ").strip() or None
if not URL:
    sys.exit("Set DATABASE_URL env or paste when prompted.")

def generate_password(length=8):
    characters = string.ascii_letters + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))

def main():
    conn = psycopg2.connect(URL, sslmode="require")
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    enrollment_id = 3
    branch_id = 1

    try:
        cursor.execute("""
            SELECT *
            FROM enrollments
            WHERE enrollment_id=%s AND branch_id=%s AND status='approved'
        """, (enrollment_id, branch_id))
        enrollment = cursor.fetchone()

        if not enrollment:
            print("Enrollment not found or not approved")
            return

        cursor.execute("SELECT branch_code FROM branches WHERE branch_id=%s", (branch_id,))
        brow = cursor.fetchone()
        branch_code = (brow["branch_code"] if brow and brow.get("branch_code") else "").strip().upper()
        if not branch_code:
            branch_code = f"B{branch_id}"

        branch_no = enrollment.get("branch_enrollment_no") or enrollment_id
        try:
            num = int(branch_no)
            branch_no_str = f"{num:04d}"
        except Exception:
            branch_no_str = str(branch_no)

        username = f"{branch_code}_{branch_no_str}"
        temp_password = generate_password()
        hashed_password = generate_password_hash(temp_password)
        print(f"Username will be: {username}")
        
        try:
            cursor.execute("""
                INSERT INTO student_accounts
                  (enrollment_id, branch_id, username, password, is_active, require_password_change)
                VALUES
                  (%s, %s, %s, %s, TRUE, TRUE)
            """, (enrollment_id, enrollment["branch_id"], username, hashed_password))
            print("Insert to student_accounts SUCCESS")
        except Exception as e:
            print(f"FAILED to insert to student_accounts: {e}")
            conn.rollback()

    except Exception as e:
        print(f"Outer exception: {e}")
    finally:
        conn.rollback() # Don't save
        cursor.close()
        conn.close()

if __name__ == "__main__":
    main()
