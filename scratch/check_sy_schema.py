import sys
import os

# Add parent directory to path so we can import db
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import get_db_connection

def check_schema():
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'school_years';")
    columns = cursor.fetchall()
    for col in columns:
        print(f"{col[0]}: {col[1]}")
    cursor.close()
    db.close()

if __name__ == "__main__":
    check_schema()
