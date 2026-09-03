import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import db

import psycopg2.extras
conn = db.get_db_connection()
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

print("--- ELECTIVE SUBJECTS ---")
cur.execute("SELECT subject_id, name, subject_type, track, pathway FROM subjects WHERE subject_type = 'ELECTIVE'")
for r in cur.fetchall():
    print(r)

print("\n--- SECTION TEACHERS (ASSIGNMENTS) ---")
cur.execute("""
    SELECT st.id, s.name AS subject_name, sec.section_name, st.subject_id
    FROM section_teachers st
    JOIN subjects s ON st.subject_id = s.subject_id
    JOIN sections sec ON st.section_id = sec.section_id
    WHERE s.subject_type = 'ELECTIVE'
""")
for r in cur.fetchall():
    print(r)

print("\n--- SHS ELECTIVE OFFERINGS ---")
cur.execute("SELECT * FROM shs_elective_offerings")
for r in cur.fetchall():
    print(r)

cur.close()
conn.close()
