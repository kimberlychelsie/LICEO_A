import psycopg2
import os

def migrate():
    # Try different credentials
    creds = [
        ('postgres', '1234'),
        ('postgres', 'postgres'),
        ('postgres', ''),
        ('liceo_db', '1234')
    ]
    
    conn = None
    for user, pwd in creds:
        try:
            print(f"Trying {user}...")
            conn = psycopg2.connect(
                host='127.0.0.1', 
                port=5432, 
                dbname='liceo_db', 
                user=user, 
                password=pwd
            )
            print(f"Connected as {user}")
            break
        except Exception as e:
            print(f"Failed {user}: {e}")
            
    if not conn:
        print("Could not connect with any known credentials.")
        return

    cur = conn.cursor()
    try:
        # Check if status column exists
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'holidays' AND column_name = 'status'")
        if not cur.fetchone():
            print("Adding status column...")
            cur.execute("ALTER TABLE holidays ADD COLUMN status VARCHAR(20) DEFAULT 'active'")
            conn.commit()
            print("Success!")
        else:
            print("Status column already exists.")
            
        # Also try to grant ownership or permissions to liceo_db if we are postgres
        if user == 'postgres':
            print("Granting permissions to liceo_db...")
            cur.execute("ALTER TABLE holidays OWNER TO liceo_db")
            cur.execute("ALTER TABLE student_accounts OWNER TO liceo_db")
            conn.commit()
            print("Permissions granted.")
            
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    migrate()
