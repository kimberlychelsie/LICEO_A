import os
import sys

# Add the project root to sys.path so we can import db.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import psycopg2
from psycopg2.extras import RealDictCursor
from db import get_db_connection

def inspect_table(table_name):
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{table_name}'")
        columns = cur.fetchall()
        if not columns:
            print(f"\nTable {table_name} DOES NOT EXIST.")
            return

        print(f"\nColumns in {table_name}:")
        for col in columns:
            print(f"  - {col['column_name']} ({col['data_type']})")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error inspecting {table_name}: {e}")

if __name__ == "__main__":
    # Check current tables
    tables = ['sections', 'subjects', 'school_years', 'users', 'branches', 'schedules', 'section_teachers']
    for t in tables:
        inspect_table(t)
