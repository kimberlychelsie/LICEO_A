import os
import sys
import psycopg2

def main():
    URL = os.environ.get("DATABASE_URL") or (sys.argv[1] if len(sys.argv) > 1 else "").strip() or input("Paste DATABASE_URL: ").strip()
    if not URL:
        sys.exit("DATABASE_URL required (env, argv, or prompt).")
    print("Connecting to Railway database...")
    conn = psycopg2.connect(URL, sslmode="require")
    cursor = conn.cursor()

    try:
        print("Executing deletions...")
        cursor.execute("BEGIN;")
        
        cursor.execute("DELETE FROM parent_student;")
        print(f"Deleted {cursor.rowcount} rows from parent_student")

        cursor.execute("DELETE FROM student_accounts;")
        print(f"Deleted {cursor.rowcount} rows from student_accounts")

        cursor.execute("DELETE FROM users WHERE role = 'parent';")
        print(f"Deleted {cursor.rowcount} rows from users (parents)")

        cursor.execute("COMMIT;")
        print("Successfully committed changes.")
    except Exception as e:
        print(f"Error occurred: {e}")
        cursor.execute("ROLLBACK;")
        print("Rolled back changes.")
    finally:
        cursor.close()
        conn.close()
        print("Connection closed.")

if __name__ == "__main__":
    main()
