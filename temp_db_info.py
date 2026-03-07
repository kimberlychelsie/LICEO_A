from db import get_db_connection
conn = get_db_connection()
c = conn.cursor()
c.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='enrollments';")
for row in c.fetchall():
    print(row[0], row[1])
