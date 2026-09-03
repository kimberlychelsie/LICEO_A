import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import db

conn = db.get_db_connection()
cur = conn.cursor()
cur.execute("""
    SELECT s.section_id, s.section_name, g.name AS grade_level 
    FROM sections s
    JOIN grade_levels g ON s.grade_level_id = g.id
""")
for r in cur.fetchall():
    print(r)
cur.close()
conn.close()
