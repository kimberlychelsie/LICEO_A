import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor

URL = os.environ.get("DATABASE_URL") or input("Paste DATABASE_URL: ").strip() or None
if not URL:
    sys.exit("Set DATABASE_URL env or paste when prompted.")

def main():
    conn = psycopg2.connect(URL, sslmode="require")
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    enrollment_id = 3
    branch_id = 1
    username = "LDMAJ_0003_TEST"
    hashed_password = "hashed_pw"

    print("Attempting to insert into student_accounts...")
    try:
        cursor.execute("""
            INSERT INTO student_accounts
                (enrollment_id, branch_id, username, password, is_active, require_password_change)
            VALUES
                (%s, %s, %s, %s, TRUE, TRUE)
        """, (enrollment_id, branch_id, username, hashed_password))
        print("Insert successful!")
        conn.rollback() # don't actually save this
    except Exception as e:
        print("Error during insert:")
        print(e)
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    main()
