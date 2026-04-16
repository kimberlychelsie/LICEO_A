from db import get_db_connection
import psycopg2.extras

def debug_data():
    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        print("--- GRADE LEVELS ---")
        cursor.execute("SELECT name, display_order, branch_id FROM grade_levels ORDER BY display_order")
        for row in cursor.fetchall():
            print(row)
            
        print("\n--- ENROLLMENT GRADE LEVELS ---")
        cursor.execute("SELECT DISTINCT grade_level FROM enrollments")
        for row in cursor.fetchall():
            print(f"'{row['grade_level']}'")
            
    finally:
        cursor.close()
        db.close()

if __name__ == "__main__":
    debug_data()
