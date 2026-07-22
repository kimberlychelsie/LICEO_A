import psycopg2

DATABASE_URL = "postgresql://postgres:puixywJTqFOFSPxiXAgSZRYiyyUqaXvH@switchyard.proxy.rlwy.net:25993/railway"

conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = True
cur = conn.cursor()

print("Connected to Railway DB. Running migration...")

# Step 1: Add new split-name columns
add_sql = """
ALTER TABLE enrollments
ADD COLUMN IF NOT EXISTS student_first_name  VARCHAR(100),
ADD COLUMN IF NOT EXISTS student_middle_name VARCHAR(100),
ADD COLUMN IF NOT EXISTS student_last_name   VARCHAR(100),
ADD COLUMN IF NOT EXISTS father_first_name   VARCHAR(100),
ADD COLUMN IF NOT EXISTS father_middle_name  VARCHAR(100),
ADD COLUMN IF NOT EXISTS father_last_name    VARCHAR(100),
ADD COLUMN IF NOT EXISTS mother_first_name   VARCHAR(100),
ADD COLUMN IF NOT EXISTS mother_middle_name  VARCHAR(100),
ADD COLUMN IF NOT EXISTS mother_last_name    VARCHAR(100),
ADD COLUMN IF NOT EXISTS guardian_first_name  VARCHAR(100),
ADD COLUMN IF NOT EXISTS guardian_middle_name VARCHAR(100),
ADD COLUMN IF NOT EXISTS guardian_last_name   VARCHAR(100);
"""
cur.execute(add_sql)
print("Step 1 done: Added new name columns.")

# Step 2: Drop old combined name columns
drop_sql = """
ALTER TABLE enrollments
DROP COLUMN IF EXISTS student_name,
DROP COLUMN IF EXISTS father_name,
DROP COLUMN IF EXISTS mother_name,
DROP COLUMN IF EXISTS guardian_name;
"""
cur.execute(drop_sql)
print("Step 2 done: Dropped old combined name columns.")

# Verify
cur.execute("""
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_name = 'enrollments' 
      AND (column_name LIKE '%first_name%' OR column_name LIKE '%last_name%' OR column_name LIKE '%middle_name%')
    ORDER BY column_name
""")
cols = [r[0] for r in cur.fetchall()]
print("New name columns in enrollments table:")
for c in cols:
    print(f"  - {c}")

cur.close()
conn.close()
print("\nMigration complete!")
