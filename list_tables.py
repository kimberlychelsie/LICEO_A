from db import get_db_connection
db = get_db_connection()
cur = db.cursor()
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
for r in cur.fetchall():
    print(r[0])
cur.close()
db.close()
