import psycopg2
from db import get_db_connection

def fix_local_db():
    conn = get_db_connection()
    cur = conn.cursor()
    print("Checking school_years table...")
    
    try:
        cur.execute("ALTER TABLE school_years ADD COLUMN branch_id INTEGER;")
        print("Added branch_id")
    except Exception as e:
        print("branch_id:", e)
        conn.rollback()

    try:
        cur.execute("ALTER TABLE school_years ADD COLUMN is_active BOOLEAN DEFAULT FALSE;")
        print("Added is_active")
    except Exception as e:
        print("is_active:", e)
        conn.rollback()

    try:
        cur.execute("ALTER TABLE school_years ADD COLUMN year_id SERIAL PRIMARY KEY;")
        print("Added year_id")
    except Exception as e:
        print("year_id:", e)
        conn.rollback()

    conn.commit()
    print("Done adjusting school_years!")

    cur.close()
    conn.close()

if __name__ == "__main__":
    fix_local_db()
