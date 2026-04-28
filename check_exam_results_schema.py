from db import get_db_connection
import psycopg2.extras
db = get_db_connection()
cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
cur.execute("SELECT * FROM exam_results LIMIT 0")
print(cur.description)
cur.close()
db.close()
