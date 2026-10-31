import psycopg2
import psycopg2.extras

conn = psycopg2.connect(host='127.0.0.1', port=5432, dbname='liceo_db', user='liceo_db', password='liceo123')
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

try:
    # Find branch 10 and year 30 if they exist locally (may not match prod)
    cur.execute("SELECT branch_id, branch_name FROM branches ORDER BY branch_id")
    branches = cur.fetchall()
    print("Branches:", [(b['branch_id'], b['branch_name']) for b in branches])

    cur.execute("SELECT year_id, branch_id, label, is_active FROM school_years ORDER BY year_id DESC LIMIT 10")
    years = cur.fetchall()
    print("\nRecent school years:", [(y['year_id'], y['branch_id'], y['label'], y['is_active']) for y in years])

    # Check grading_policies for any active policy per branch/year
    cur.execute("""
        SELECT gp.policy_id, gp.branch_id, b.branch_name, gp.year_id, sy.label,
               gp.status, gp.policy_version
        FROM grading_policies gp
        JOIN branches b ON b.branch_id = gp.branch_id
        JOIN school_years sy ON sy.year_id = gp.year_id
        WHERE gp.status = 'active'
        ORDER BY gp.branch_id, gp.year_id
    """)
    active_policies = cur.fetchall()
    print("\nActive grading policies:")
    for p in active_policies:
        print(f"  branch={p['branch_id']} ({p['branch_name']}), year={p['year_id']} ({p['label']}), policy_id={p['policy_id']}")

    # Check for branches with active school years but NO active grading policy
    cur.execute("""
        SELECT sy.branch_id, b.branch_name, sy.year_id, sy.label
        FROM school_years sy
        JOIN branches b ON b.branch_id = sy.branch_id
        WHERE sy.is_active = TRUE
          AND NOT EXISTS (
              SELECT 1 FROM grading_policies gp
              WHERE gp.branch_id = sy.branch_id AND gp.year_id = sy.year_id AND gp.status = 'active'
          )
        ORDER BY sy.branch_id
    """)
    missing = cur.fetchall()
    print("\nBranches with active year but NO active grading policy:")
    for m in missing:
        print(f"  branch={m['branch_id']} ({m['branch_name']}), year={m['year_id']} ({m['label']})")

    # Check grade_submission_requests status in active years
    cur.execute("""
        SELECT gsr.branch_id, b.branch_name, gsr.year_id, sy.label, gsr.status, COUNT(*) as cnt
        FROM grade_submission_requests gsr
        JOIN branches b ON b.branch_id = gsr.branch_id
        JOIN school_years sy ON sy.year_id = gsr.year_id AND sy.is_active = TRUE
        WHERE gsr.status IN ('approved_for_posting', 'posted')
        GROUP BY gsr.branch_id, b.branch_name, gsr.year_id, sy.label, gsr.status
        ORDER BY gsr.branch_id
    """)
    approved_posted = cur.fetchall()
    print("\nApproved/posted grade submissions in active years:")
    for row in approved_posted:
        print(f"  branch={row['branch_id']} ({row['branch_name']}), year={row['year_id']} ({row['label']}), status={row['status']}, count={row['cnt']}")

except Exception as e:
    import traceback
    print("ERROR:", e)
    traceback.print_exc()
finally:
    cur.close()
    conn.close()
