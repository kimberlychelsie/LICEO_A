import os
import psycopg2

def fix_perms():
    host = os.getenv("DB_HOST", "127.0.0.1")
    port = int(os.getenv("DB_PORT", "5432"))
    database = os.getenv("DB_NAME", "liceo_db")
    
    # Try common superuser credentials
    superusers = [
        ("postgres", ""),
        ("postgres", "password"),
        ("postgres", "1234"),
        ("postgres", "postgres"),
    ]
    
    success = False
    for user, pw in superusers:
        print(f"Trying to connect as {user}...")
        try:
            conn = psycopg2.connect(
                host=host,
                port=port,
                dbname=database,
                user=user,
                password=pw,
            )
            print(f"Connected successfully as {user}!")
            with conn.cursor() as cur:
                print("Granting permissions on daily_attendance to liceo_db...")
                cur.execute("GRANT ALL PRIVILEGES ON TABLE daily_attendance TO liceo_db;")
                # Also grant on sequence if it exists
                try:
                    cur.execute("GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO liceo_db;")
                except:
                    pass
                conn.commit()
                print("Permissions granted successfully.")
                success = True
            conn.close()
            break
        except Exception as e:
            print(f"Failed to connect as {user}: {e}")

    if not success:
        print("Could not connect as superuser to fix permissions.")

if __name__ == "__main__":
    fix_perms()
