import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import db

def migrate():
    conn = db.get_db_connection()
    cur = conn.cursor()
    try:
        # Check if pathway column exists
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='subjects' AND column_name='pathway'
        """)
        exists = cur.fetchone()
        if not exists:
            print("Adding 'pathway' column to 'subjects' table...")
            cur.execute("ALTER TABLE subjects ADD COLUMN pathway VARCHAR(255) DEFAULT NULL")
            conn.commit()
            print("Column 'pathway' added successfully!")
        else:
            print("Column 'pathway' already exists.")
    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    migrate()
