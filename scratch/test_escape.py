import sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()
from db import get_db_connection
import psycopg2.extras

conn = get_db_connection()
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

branch_id = 11
cur.execute("""
    SELECT count(*) FROM users WHERE branch_id = %s AND (role = 'teacher' OR user_roles ILIKE '%%teacher%%')
""", (branch_id,))
print("Result with %%teacher%%:", cur.fetchone())
conn.close()
