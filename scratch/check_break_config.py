import sys
sys.path.insert(0, r'c:\LICEO_A')
from db import get_db_connection
import json

conn = get_db_connection()
cur = conn.cursor()
cur.execute("SELECT setting_key, setting_value, updated_at FROM system_settings WHERE setting_key LIKE '%break%'")
rows = cur.fetchall()
if not rows:
    print("NO BREAK CONFIG FOUND IN DB!")
else:
    for r in rows:
        print(f"Key: {r[0]}")
        print(f"Updated: {r[2]}")
        print(f"Value: {r[1][:200] if r[1] else None}")
        print("---")
cur.close()
conn.close()
