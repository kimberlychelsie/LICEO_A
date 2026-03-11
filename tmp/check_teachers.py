import psycopg2
conn = psycopg2.connect('dbname=liceo_db user=liceo_db password=liceo123 host=127.0.0.1 port=5432')
cur = conn.cursor()
cur.execute("SELECT user_id, username, role, grade_level, grade_level_id FROM users WHERE role = 'teacher'")
for row in cur.fetchall():
    print(row)
cur.close()
conn.close()
