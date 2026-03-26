import psycopg2
from db import get_db_connection

db = get_db_connection()
cursor = db.cursor()
cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'enrollments';")
columns = [row[0] for row in cursor.fetchall()]
print("Total columns:", len(columns))
print(columns)
cursor.close()
db.close()
