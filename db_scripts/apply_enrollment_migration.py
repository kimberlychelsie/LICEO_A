import os
import sys
import psycopg2

def apply_migration():
    """
    Applies the missing columns to the enrollments table on both Railway and Local DB.
    """
    # SQL to add missing columns if they don't exist
    migration_sql = """
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='enrollments' AND column_name='enroll_type') THEN
            ALTER TABLE public.enrollments ADD COLUMN enroll_type VARCHAR(50);
        END IF;

        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='enrollments' AND column_name='enroll_date') THEN
            ALTER TABLE public.enrollments ADD COLUMN enroll_date DATE;
        END IF;

        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='enrollments' AND column_name='remarks') THEN
            ALTER TABLE public.enrollments ADD COLUMN remarks TEXT;
        END IF;

        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='enrollments' AND column_name='birthplace') THEN
            ALTER TABLE public.enrollments ADD COLUMN birthplace VARCHAR(255);
        END IF;

        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='enrollments' AND column_name='father_name') THEN
            ALTER TABLE public.enrollments ADD COLUMN father_name VARCHAR(100);
        END IF;

        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='enrollments' AND column_name='father_contact') THEN
            ALTER TABLE public.enrollments ADD COLUMN father_contact VARCHAR(20);
        END IF;

        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='enrollments' AND column_name='father_occupation') THEN
            ALTER TABLE public.enrollments ADD COLUMN father_occupation VARCHAR(100);
        END IF;

        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='enrollments' AND column_name='mother_name') THEN
            ALTER TABLE public.enrollments ADD COLUMN mother_name VARCHAR(100);
        END IF;

        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='enrollments' AND column_name='mother_contact') THEN
            ALTER TABLE public.enrollments ADD COLUMN mother_contact VARCHAR(20);
        END IF;

        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='enrollments' AND column_name='mother_occupation') THEN
            ALTER TABLE public.enrollments ADD COLUMN mother_occupation VARCHAR(100);
        END IF;

        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='enrollments' AND column_name='school_year') THEN
            ALTER TABLE public.enrollments ADD COLUMN school_year VARCHAR(20);
        END IF;
    END
    $$;
    """

    # 1. Try Railway
    print("--- Railway Migration ---")
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL env var not found.")
        url = input("Paste your Railway Public Connection URL (it looks like postgresql://...): ").strip()
    
    if url:
        try:
            conn = psycopg2.connect(url, sslmode="require")
            with conn.cursor() as cur:
                cur.execute(migration_sql)
            conn.commit()
            print("Successfully updated Railway database.")
        except Exception as e:
            print(f"Error updating Railway: {e}")
        finally:
            if 'conn' in locals(): conn.close()
    else:
        print("Skipped Railway (no URL provided).")

    # 2. Try Local
    print("\n--- Local Migration ---")
    try:
        conn = psycopg2.connect(host="127.0.0.1", port=5432, dbname="liceo_db", user="liceo_db", password="liceo123")
        with conn.cursor() as cur:
            cur.execute(migration_sql)
        conn.commit()
        print("Successfully updated local database.")
    except Exception as e:
        print(f"Error updating local: {e}")
    finally:
        if 'conn' in locals(): conn.close()

if __name__ == "__main__":
    apply_migration()
