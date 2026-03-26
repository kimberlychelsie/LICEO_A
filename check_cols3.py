import psycopg2
import psycopg2.extras

db_url = "postgresql://postgres:puixywJTqFOFSPxiXAgSZRYiyyUqaXvH@switchyard.proxy.rlwy.net:25993/railway"
db = psycopg2.connect(db_url)
cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'enrollments';")
columns = sorted([row["column_name"] for row in cursor.fetchall()])
print("Railway DB cols:", columns)

cursor.close()
db.close()
