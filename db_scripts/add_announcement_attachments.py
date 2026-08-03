import sys
import os

# Add parent directory to path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import get_db_connection

def migrate():
    db = get_db_connection()
    cur = db.cursor()
    try:
        print("Adding file_path and file_name columns to teacher_announcements...")
        cur.execute("""
            ALTER TABLE teacher_announcements
            ADD COLUMN IF NOT EXISTS file_path VARCHAR(255),
            ADD COLUMN IF NOT EXISTS file_name VARCHAR(255);
        """)
        db.commit()
        print("Migration successful!")
    except Exception as e:
        db.rollback()
        print(f"Error during migration: {e}")
    finally:
        cur.close()
        db.close()

if __name__ == "__main__":
    migrate()
