import psycopg2

DATABASE_URL = "postgresql://postgres:puixywJTqFOFSPxiXAgSZRYiyyUqaXvH@switchyard.proxy.rlwy.net:25993/railway"

conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = True
cur = conn.cursor()

print("Adding UNIQUE constraints for participation_scores and attendance_scores...")

try:
    cur.execute("""
        ALTER TABLE participation_scores
        ADD CONSTRAINT participation_scores_unique_idx UNIQUE (enrollment_id, subject_id, grading_period);
    """)
    print("Added unique constraint to participation_scores")
except Exception as e:
    print("Could not add to participation_scores:", e)

try:
    cur.execute("""
        ALTER TABLE attendance_scores
        ADD CONSTRAINT attendance_scores_unique_idx UNIQUE (enrollment_id, subject_id, grading_period);
    """)
    print("Added unique constraint to attendance_scores")
except Exception as e:
    print("Could not add to attendance_scores:", e)

cur.close()
conn.close()
print("Done.")
