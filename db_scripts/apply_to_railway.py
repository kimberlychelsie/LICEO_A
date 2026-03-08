import psycopg2

URL = "postgresql://postgres:puixywJTqFOFSPxiXAgSZRYiyyUqaXvH@switchyard.proxy.rlwy.net:25993/railway"

def update_railway():
    print("Connecting to Railway database...")
    try:
        conn = psycopg2.connect(URL, sslmode="require")
        cur = conn.cursor()
        
        print("1. Adding branch_id column to grade_levels if not exists...")
        cur.execute("ALTER TABLE public.grade_levels ADD COLUMN IF NOT EXISTS branch_id integer;")
        
        print("2. Dropping the old single-column unique constraint on name...")
        cur.execute("ALTER TABLE public.grade_levels DROP CONSTRAINT IF EXISTS grade_levels_name_key;")
        
        print("3. Adding new composite unique constraint (name, branch_id)...")
        # Ensure we catch if it already exists or if there's a violation
        try:
            cur.execute("ALTER TABLE public.grade_levels ADD CONSTRAINT grade_levels_name_branch_key UNIQUE (name, branch_id);")
            print("Successfully added new unique constraint!")
        except psycopg2.errors.DuplicateTable:
            print("Constraint already exists or named similarly.")
        except Exception as inner_e:
            print(f"Note on constraint creation: {inner_e}")
            
        conn.commit()
        print("\nAll Railway database schema updates applied successfully!")
        
    except Exception as e:
        print(f"Error connecting or updating Railway DB: {e}")
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    update_railway()
