import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from db import get_db_connection

def find_sequences():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT relname 
            FROM pg_class 
            WHERE relkind = 'S' AND relname LIKE '%schedules%';
        """)
        seqs = cur.fetchall()
        print("\nFound Sequences:")
        for s in seqs:
            print(f"  - {s[0]}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    find_sequences()
