import psycopg2

urls = [
    "postgresql://postgres:puixywJTqFOFSPxiXAgSZRYiyyUqaXvH@switchyard.proxy.rlwy.net:25993/railway",
    "postgresql://postgres:liceo123@127.0.0.1:5432/liceo_db",
    "postgresql://postgres:password@127.0.0.1:5432/liceo_db",
    "postgresql://postgres:root@127.0.0.1:5432/liceo_db",
    "postgresql://postgres:admin@127.0.0.1:5432/liceo_db",
    "postgresql://postgres:@127.0.0.1:5432/liceo_db",
]

for u in urls:
    try:
        print("Trying", u)
        conn = psycopg2.connect(u)
        cur = conn.cursor()
        cur.execute("ALTER TABLE sections ADD COLUMN IF NOT EXISTS capacity INTEGER NOT NULL DEFAULT 50")
        conn.commit()
        print("Success on", u)
        conn.close()
    except Exception as e:
        print("Failed on", u, str(e))
