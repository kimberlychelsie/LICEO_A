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
        
        # Delete dependencies first to avoid foreign key violations (if any don't have CASCADE)
        cursor.execute("DELETE FROM enrollment_documents;")
        print(f"Deleted {cursor.rowcount} rows from enrollment_documents")
        
        cursor.execute("DELETE FROM enrollment_books;")
        print(f"Deleted {cursor.rowcount} rows from enrollment_books")

        cursor.execute("DELETE FROM enrollment_uniforms;")
        print(f"Deleted {cursor.rowcount} rows from enrollment_uniforms")

        # Delete from the main enrollments table
        cursor.execute("DELETE FROM enrollments;")
        print(f"Deleted {cursor.rowcount} rows from enrollments")

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
