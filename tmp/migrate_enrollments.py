import psycopg2
import os

def migrate_enrollments_local():
    host = os.getenv("DB_HOST", "127.0.0.1")
    port = int(os.getenv("DB_PORT", "5432"))
    database = os.getenv("DB_NAME", "liceo_db")
    user = os.getenv("DB_USER", "liceo_db")
    password = os.getenv("DB_PASSWORD", "liceo123")

    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            dbname=database,
            user=user,
            password=password,
        )
        cur = conn.cursor()
        
        # Check existing columns
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'enrollments' AND table_schema = 'public'")
        existing_cols = [r[0] for r in cur.fetchall()]
        
        new_cols = [
            ("father_name", "VARCHAR(255)"),
            ("mother_name", "VARCHAR(255)"),
            ("enroll_type", "VARCHAR(255)"),
            ("enroll_date", "DATE"),
            ("birthplace", "VARCHAR(255)"),
            ("remarks", "TEXT"),
            ("father_contact", "VARCHAR(255)"),
            ("mother_contact", "VARCHAR(255)"),
            ("father_occupation", "VARCHAR(255)"),
            ("mother_occupation", "VARCHAR(255)"),
            ("school_year", "VARCHAR(255)")
        ]
        
        for col_name, col_type in new_cols:
            if col_name not in existing_cols:
                print(f"Adding column {col_name} to enrollments...")
                cur.execute(f"ALTER TABLE enrollments ADD COLUMN {col_name} {col_type}")
        
        conn.commit()
        print("Migration completed successfully.")
        conn.close()
    except Exception as e:
        print(f"Migration error: {e}")

if __name__ == "__main__":
    migrate_enrollments_local()
