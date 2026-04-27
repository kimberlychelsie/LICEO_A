import os
import psycopg2

def grant_all():
    host = os.getenv("DB_HOST", "127.0.0.1")
    port = int(os.getenv("DB_PORT", "5432"))
    database = os.getenv("DB_NAME", "liceo_db")
    
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            dbname=database,
            user="postgres",
            password="1234",
        )
        print("Connected as postgres.")
        with conn.cursor() as cur:
            print("Granting ALL privileges on ALL tables in public schema to liceo_db...")
            cur.execute("GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO liceo_db;")
            print("Granting ALL privileges on ALL sequences in public schema to liceo_db...")
            cur.execute("GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO liceo_db;")
            conn.commit()
            print("All permissions granted.")
        conn.close()
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    grant_all()
