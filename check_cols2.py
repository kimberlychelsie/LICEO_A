import psycopg2
import psycopg2.extras
from db import get_db_connection

db = get_db_connection()
cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
cursor.execute("SELECT * FROM enrollments LIMIT 1;")
row = cursor.fetchone()
if row:
    print("Columns in dict:", list(row.keys()))
else:
    print("No rows, but description:", [desc[0] for desc in cursor.description])
cursor.close()
db.close()
