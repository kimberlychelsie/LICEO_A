import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv()
import psycopg2

conn = psycopg2.connect(
    host=os.getenv("DB_HOST", "127.0.0.1"),
    port=int(os.getenv("DB_PORT", "5432")),
    dbname=os.getenv("DB_NAME", "liceo_db"),
    user=os.getenv("DB_USER", "liceo_db"),
    password=os.getenv("DB_PASSWORD", "liceo123")
)
cur = conn.cursor()

cur.execute("SELECT DISTINCT branch_id FROM grade_levels WHERE branch_id IS NOT NULL;")
branches = [r[0] for r in cur.fetchall()]

shs_strands = [
    "Grade 11-GAS",
    "Grade 11-STEM",
    "Grade 11-HUMSS",
    "Grade 11-ABM",
    "Grade 11-TVL",
    "Grade 12-GAS",
    "Grade 12-STEM",
    "Grade 12-HUMSS",
    "Grade 12-ABM",
    "Grade 12-TVL"
]

added_total = 0

for b_id in branches:
    cur.execute("SELECT name FROM grade_levels WHERE branch_id = %s;", (b_id,))
    existing_names = set(r[0].lower() for r in cur.fetchall())
    
    cur.execute("SELECT COALESCE(MAX(display_order), 0) FROM grade_levels WHERE branch_id = %s;", (b_id,))
    max_disp = cur.fetchone()[0]
    
    for strand in shs_strands:
        if strand.lower() not in existing_names:
            max_disp += 1
            cur.execute(
                "INSERT INTO grade_levels (name, display_order, branch_id) VALUES (%s, %s, %s);",
                (strand, max_disp, b_id)
            )
            print(f"Inserted '{strand}' into branch {b_id} (display_order: {max_disp})")
            added_total += 1

conn.commit()
cur.close()
conn.close()
print(f"Successfully inserted {added_total} SHS grade levels across all branches.")
