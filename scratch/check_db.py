import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

host = os.getenv('DB_HOST', '127.0.0.1')
port = os.getenv('DB_PORT', '5432')
dbname = os.getenv('DB_NAME', 'liceo_db')
user = os.getenv('DB_USER', 'liceo_db')
password = os.getenv('DB_PASSWORD', '1234')

print(f"Connecting to DB {dbname} as {user}...")
conn = psycopg2.connect(host=host, port=port, dbname=dbname, user=user, password=password)
cur = conn.cursor()

cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='swafo_records'")
cols = [r[0] for r in cur.fetchall()]
print("swafo_records columns:", cols)

if 'submitted_at' not in cols:
    print("Adding missing column 'submitted_at' to swafo_records...")
    cur.execute("ALTER TABLE swafo_records ADD COLUMN IF NOT EXISTS submitted_at TIMESTAMP WITHOUT TIME ZONE;")
    conn.commit()
    print("Column 'submitted_at' added successfully!")
else:
    print("Column 'submitted_at' already exists.")

conn.close()
