from db import get_db_connection
import logging

def create_announcements_table():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS system_announcements (
                id SERIAL PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                message TEXT NOT NULL,
                priority VARCHAR(20) DEFAULT 'normal', -- normal, vital, critical
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
        conn.commit()
        print("Table 'system_announcements' created or already exists.")
    except Exception as e:
        conn.rollback()
        print(f"Error creating table: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    create_announcements_table()
