import sys
import dotenv
dotenv.load_dotenv()
sys.path.insert(0, '.')
from db import get_db_connection

db = get_db_connection()
c = db.cursor()
c.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'users'")
print("USERS COLS:", [r[0] for r in c.fetchall()])
c.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'branches'")
print("BRANCHES COLS:", [r[0] for r in c.fetchall()])
db.close()
