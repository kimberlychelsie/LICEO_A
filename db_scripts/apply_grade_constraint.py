import os
import psycopg2

def apply_constraints():
    try:
        # Try postgres user first for local
        conn = psycopg2.connect(host="127.0.0.1", port=5432, dbname="liceo_db", user="postgres", password="password")
    except:
        try:
            # Maybe password is postgres
            conn = psycopg2.connect(host="127.0.0.1", port=5432, dbname="liceo_db", user="postgres", password="postgres")
        except:
            print("Could not connect as postgres user locally.")
            return

    cur = conn.cursor()
    try:
        print("Connected as postgres. Dropping old constraint...")
        cur.execute("ALTER TABLE public.grade_levels DROP CONSTRAINT IF EXISTS grade_levels_name_key;")
        
        print("Adding new composite constraint...")
        cur.execute("ALTER TABLE public.grade_levels ADD CONSTRAINT grade_levels_name_branch_key UNIQUE (name, branch_id);")
        
        conn.commit()
        print("Successfully updated grade_levels constraints!")
        
    except Exception as e:
        conn.rollback()
        print(f"Error applying constraints: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    apply_constraints()
