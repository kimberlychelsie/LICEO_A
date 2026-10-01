import sys
import os
sys.path.insert(0, 'c:/LICEO_A')

# Load .env manually
env_path = 'c:/LICEO_A/.env'
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())

from db import get_db_connection

conn = get_db_connection()
cur = conn.cursor()
try:
    cur.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name = 'section_teachers'"
    )
    cols = [r[0] for r in cur.fetchall()]
    print("Current section_teachers columns:", cols)

    changed = False

    if "term_name" not in cols:
        cur.execute("ALTER TABLE section_teachers ADD COLUMN term_name VARCHAR(50)")
        print("Added term_name column")
        changed = True
    else:
        print("term_name already exists - OK")

    if "is_archived" not in cols:
        cur.execute("ALTER TABLE section_teachers ADD COLUMN is_archived BOOLEAN DEFAULT FALSE")
        print("Added is_archived column")
        changed = True
    else:
        print("is_archived already exists - OK")

    if changed:
        conn.commit()
        print("Migration committed!")
    else:
        print("No changes needed.")

except Exception as e:
    conn.rollback()
    print("ERROR:", e)
finally:
    cur.close()
    conn.close()
