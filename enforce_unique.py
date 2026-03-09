import db
conn = db.get_db_connection()
cursor = conn.cursor()

# Check if constraint exists
cursor.execute("SELECT conname FROM pg_constraint WHERE conrelid = 'enrollments'::regclass;")
constraints = [r[0] for r in cursor.fetchall()]

if 'uq_enrollments_branch_no' not in constraints:
    print("Adding unique constraint...")
    cursor.execute("ALTER TABLE public.enrollments ADD CONSTRAINT uq_enrollments_branch_no UNIQUE (branch_id, branch_enrollment_no);")
    conn.commit()
    print("Done.")
else:
    print("Constraint already exists.")

cursor.close()
conn.close()
