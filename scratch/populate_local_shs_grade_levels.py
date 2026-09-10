import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv()
import db

conn = db.get_db_connection()
cur = conn.cursor()

# Get all active branches
cur.execute("SELECT branch_id, branch_name FROM branches;")
branches = cur.fetchall()

shs_strands = [
    ("Grade 11-STEM", 22),
    ("Grade 11-HUMSS", 23),
    ("Grade 11-GAS", 24),
    ("Grade 11-ABM", 25),
    ("Grade 11-TVL", 26),
    ("Grade 12-STEM", 27),
    ("Grade 12-HUMSS", 28),
    ("Grade 12-GAS", 29),
    ("Grade 12-ABM", 30),
    ("Grade 12-TVL", 31),
]

added_count = 0
for b in branches:
    b_id = b[0]
    b_name = b[1]
    
    # Get existing grade level names
    cur.execute("SELECT LOWER(name) FROM grade_levels WHERE branch_id = %s;", (b_id,))
    existing = set(r[0] for r in cur.fetchall())
    
    for strand_name, disp_order in shs_strands:
        if strand_name.lower() not in existing:
            cur.execute("""
                INSERT INTO grade_levels (name, display_order, branch_id)
                VALUES (%s, %s, %s);
            """, (strand_name, disp_order, b_id))
            print(f"Added '{strand_name}' for branch '{b_name}' (ID: {b_id})")
            added_count += 1

conn.commit()
cur.close()
conn.close()
print(f"Successfully added {added_count} SHS grade levels to local database without deleting any data.")
