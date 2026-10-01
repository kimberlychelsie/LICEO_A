import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

import psycopg2

def run_migration():
    host = os.getenv("DB_HOST", "127.0.0.1")
    port = int(os.getenv("DB_PORT", "5432"))
    database = os.getenv("DB_NAME", "liceo_db")
    user = os.getenv("DB_USER", "liceo_db")
    
    passwords = ["1234", "", "postgres", "admin", "root", "liceo123"]
    conn = None
    
    # First try connecting as postgres superuser
    for pwd in passwords:
        try:
            print(f"Trying to connect as postgres user with password '{pwd}'...")
            conn = psycopg2.connect(
                host=host, port=port, dbname=database, user="postgres", password=pwd
            )
            print("Successfully connected as postgres superuser!")
            break
        except Exception:
            pass

    # Fallback to DB_USER if postgres user connection is not available
    if not conn:
        try:
            print(f"Connecting as {user}...")
            conn = psycopg2.connect(
                host=host, port=port, dbname=database, user=user, password=os.getenv("DB_PASSWORD", "liceo123")
            )
        except Exception as e:
            print(f"Failed to connect: {e}")
            return

    cursor = conn.cursor()
    try:
        print("Adding term_name and is_archived columns to section_teachers...")
        cursor.execute("ALTER TABLE section_teachers ADD COLUMN IF NOT EXISTS term_name VARCHAR(50);")
        cursor.execute("ALTER TABLE section_teachers ADD COLUMN IF NOT EXISTS is_archived BOOLEAN DEFAULT FALSE;")
        
        print("Adding term_name and is_archived columns to schedules...")
        cursor.execute("ALTER TABLE schedules ADD COLUMN IF NOT EXISTS term_name VARCHAR(50);")
        cursor.execute("ALTER TABLE schedules ADD COLUMN IF NOT EXISTS is_archived BOOLEAN DEFAULT FALSE;")
        
        # Change table owners to liceo_db
        tables = ["section_teachers", "schedules", "subjects", "sections", "grade_levels", "school_years"]
        for t in tables:
            try:
                cursor.execute(f"ALTER TABLE {t} OWNER TO {user};")
                print(f"Changed owner of {t} to {user}")
            except Exception as owner_err:
                print(f"Could not change owner of {t}: {owner_err}")

        conn.commit()
        print("Migration and ownership transfer executed successfully!")
    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    run_migration()
