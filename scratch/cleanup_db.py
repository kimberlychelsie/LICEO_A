import os
import psycopg2
from dotenv import load_dotenv

# Load .env if it exists
load_dotenv()

def cleanup_database():
    host = os.getenv("DB_HOST", "127.0.0.1")
    port = int(os.getenv("DB_PORT", "5432"))
    database = os.getenv("DB_NAME", "liceo_db")
    user = os.getenv("DB_USER", "liceo_db")
    password = os.getenv("DB_PASSWORD", "1234")

    print(f"Connecting to database {database} on {host}...")
    
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            dbname=database,
            user=user,
            password=password
        )
        conn.autocommit = True
        cur = conn.cursor()

        # 1. Get all tables in the public schema
        cur.execute("""
            SELECT tablename 
            FROM pg_catalog.pg_tables 
            WHERE schemaname = 'public'
        """)
        tables = [r[0] for r in cur.fetchall()]
        
        print(f"Found tables: {', '.join(tables)}")

        # 2. Transactional tables that should be completely wiped
        # We use DELETE and run multiple passes to handle foreign key dependencies
        to_wipe = [t for t in tables if t not in ['users', 'branches', 'grade_levels', 'subjects']]
        
        for i in range(3): # Run 3 passes to handle nested dependencies
            print(f"Cleanup pass {i+1}...")
            for table in to_wipe:
                try:
                    # Check if table still has data
                    cur.execute(f"SELECT 1 FROM {table} LIMIT 1")
                    if not cur.fetchone():
                        continue
                        
                    print(f"  Cleaning table: {table}...")
                    cur.execute(f"DELETE FROM {table}")
                    # Reset sequence if it exists
                    try:
                        cur.execute(f"ALTER SEQUENCE {table}_{table}_id_seq RESTART WITH 1")
                    except:
                        pass
                except Exception as e:
                    # Only print warning on the last pass
                    if i == 2:
                        print(f"  Warning: Could not clean {table}: {e}")
                    conn.rollback()
        
        # 3. Clean up the users table but KEEP the superadmin
        try:
            print("Cleaning up users table (keeping super_admin)...")
            cur.execute("DELETE FROM users WHERE role != 'super_admin'")
        except Exception as e:
            print(f"  Warning: Could not clean users: {e}")
            conn.rollback()
        
        # 4. Optional: Clean up configuration tables if requested
        # User said "lahat ng data and accounts", so maybe branches and subjects should stay?
        # If they want a FRESH start, maybe truncate them too?
        # But usually branches/subjects are 'configuration'.
        # I'll keep them for now unless they say otherwise.
        
        print("Cleanup complete.")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error during cleanup: {e}")

if __name__ == "__main__":
    cleanup_database()
