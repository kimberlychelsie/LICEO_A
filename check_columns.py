import db
conn = db.get_db_connection()
cursor = conn.cursor()
tables = ['billing', 'enrollment_documents', 'enrollment_books', 'enrollment_uniforms', 'payments', 'parent_student', 'student_accounts', 'reservations', 'reservation_items']
for t in tables:
    cursor.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{t}';")
    cols = [r[0] for r in cursor.fetchall()]
    print(f"{t}: {cols}")
