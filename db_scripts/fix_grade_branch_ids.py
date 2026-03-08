import psycopg2
import os

URL = "postgresql://postgres:puixywJTqFOFSPxiXAgSZRYiyyUqaXvH@switchyard.proxy.rlwy.net:25993/railway"

def fix_null_branch_ids():
    # Fix on Railway
    print("Fixing Railway DB...")
    try:
        conn = psycopg2.connect(URL, sslmode="require")
        cur = conn.cursor()
        cur.execute("UPDATE public.grade_levels SET branch_id = 1 WHERE branch_id IS NULL;")
        conn.commit()
        print(f"Railway DB updated. Rows affected: {cur.rowcount}")
    except Exception as e:
        print(f"Railway DB error: {e}")
    finally:
        if 'cur' in locals(): cur.close()
        if 'conn' in locals(): conn.close()

    # Fix on Local
    print("\nFixing Local DB...")
    try:
        conn = psycopg2.connect(host="127.0.0.1", port=5432, dbname="liceo_db", user="liceo_db", password="liceo123")
        cur = conn.cursor()
        cur.execute("UPDATE public.grade_levels SET branch_id = 1 WHERE branch_id IS NULL;")
        conn.commit()
        print(f"Local DB updated. Rows affected: {cur.rowcount}")
    except Exception as e:
        print(f"Local DB error: {e}")
    finally:
        if 'cur' in locals(): cur.close()
        if 'conn' in locals(): conn.close()

if __name__ == "__main__":
    fix_null_branch_ids()
