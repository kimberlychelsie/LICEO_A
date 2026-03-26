import os
from dotenv import load_dotenv
load_dotenv()

from db import get_db_connection
import psycopg2.extras

def check():
    db = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'users'")
        cols = [r['column_name'] for r in cur.fetchall()]
        print(f"Users columns: {cols}")
        
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'student_accounts'")
        sa_cols = [r['column_name'] for r in cur.fetchall()]
        print(f"Student Accounts columns: {sa_cols}")
        
        # Check SMTP env vars
        print(f"SMTP_USER: {os.getenv('SMTP_USER')}")
        print(f"SMTP_PASS: {'SET' if os.getenv('SMTP_PASS') else 'MISSING'}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        cur.close()
        db.close()

if __name__ == "__main__":
    check()
