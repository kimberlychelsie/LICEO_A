import sys
sys.path.insert(0, r"c:\LICEO_A")
from dotenv import load_dotenv
load_dotenv()
from db import get_db_connection
import psycopg2.extras

db = get_db_connection()
cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
cur.execute("""
SELECT column_name FROM information_schema.columns
WHERE table_name='inventory_items' AND column_name IN ('size_price_step','parent_item_id','is_set_piece')
ORDER BY column_name
""")
print("cols:", [r["column_name"] for r in cur.fetchall()])
cur.close()
db.close()
