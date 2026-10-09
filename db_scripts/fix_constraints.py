import psycopg2
import os

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is required.")

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
