import os
import sys
sys.path.append(os.getcwd())
import db
import psycopg2.extras

def check_schema():
    conn = db.get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    tables = ['sections', 'grade_levels', 'enrollments']
    for table in tables:
        print(f"\n--- Columns in {table} ---")
        try:
            cur.execute(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{table}'")
            columns = cur.fetchall()
            for col in columns:
                print(f"{col['column_name']}: {col['data_type']}")
        except Exception as e:
            print(f"Error checking {table}: {e}")
            
    cur.close()
    conn.close()

if __name__ == "__main__":
    check_schema()
