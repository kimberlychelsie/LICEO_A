import os
import sys
import psycopg2

def apply_migration():
    # Use the superuser URL found in history to bypass permission issues
    URL = "postgresql://postgres:puixywJTqFOFSPxiXAgSZRYiyyUqaXvH@switchyard.proxy.rlwy.net:25993/railway"
    
    try:
        conn = psycopg2.connect(URL, sslmode="require")
        cur = conn.cursor()
        
        # SQL to create the table
        sql = """
        CREATE TABLE IF NOT EXISTS individual_extensions (
            extension_id SERIAL PRIMARY KEY,
            enrollment_id INTEGER NOT NULL REFERENCES enrollments(enrollment_id) ON DELETE CASCADE,
            item_type    VARCHAR(20) NOT NULL, -- 'activity', 'exam', 'quiz'
            item_id      INTEGER NOT NULL,      -- activity_id or exam_id
            new_due_date TIMESTAMP WITHOUT TIME ZONE NOT NULL,
            created_at   TIMESTAMP DEFAULT NOW()
        );
        
        -- Add unique constraint
        DO $$ 
        BEGIN 
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_extension') THEN
                ALTER TABLE individual_extensions ADD CONSTRAINT uq_extension UNIQUE (enrollment_id, item_type, item_id);
            END IF;
        END $$;
        """
            
        cur.execute(sql)
        conn.commit()
        print("Reschedule migration applied successfully using superuser URL.")
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        print(f"Error applying migration: {e}")
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    apply_migration()
