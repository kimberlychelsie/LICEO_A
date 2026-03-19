import os
import sys
import psycopg2

def apply_migration():
    """
    Applies the missing columns to the enrollments table on both Railway and Local DB.
    """
    columns_to_add = [
        ("enroll_type", "VARCHAR(50)"),
        ("enroll_date", "DATE"),
        ("remarks", "TEXT"),
        ("birthplace", "VARCHAR(255)"),
        ("father_name", "VARCHAR(100)"),
        ("father_contact", "VARCHAR(20)"),
        ("father_occupation", "VARCHAR(100)"),
        ("mother_name", "VARCHAR(100)"),
        ("mother_contact", "VARCHAR(20)"),
        ("mother_occupation", "VARCHAR(100)"),
        ("school_year", "VARCHAR(20)")
    ]

    def process_db(conn_string, label):
        print(f"--- {label} Migration ---")
        try:
            print(f"Connecting to {label}...")
            conn = psycopg2.connect(conn_string, connect_timeout=15)
            conn.autocommit = True
            with conn.cursor() as cur:
                for col_name, col_type in columns_to_add:
                    try:
                        cur.execute(f"ALTER TABLE public.enrollments ADD COLUMN {col_name} {col_type};")
                        print(f"  [+] Added: {col_name}")
                    except psycopg2.errors.DuplicateColumn:
                        print(f"  [.] Exists: {col_name}")
                    except Exception as e:
                        print(f"  [!] Error adding {col_name}: {e}")
            print(f"Successfully finished {label} updates.")
        except Exception as e:
            print(f"  [!] {label} connection/general error: {e}")
        finally:
            if 'conn' in locals(): conn.close()

    # 1. Railway
    railway_url = os.environ.get("DATABASE_URL") or "postgresql://postgres:puixywJTqFOFSPxiXAgSZRYiyyUqaXvH@switchyard.proxy.rlwy.net:25993/railway"
    process_db(railway_url, "Railway")

    # 2. Local
    local_url = "host=127.0.0.1 port=5432 dbname=liceo_db user=liceo_db password=liceo123"
    process_db(local_url, "Local")

if __name__ == "__main__":
    apply_migration()
