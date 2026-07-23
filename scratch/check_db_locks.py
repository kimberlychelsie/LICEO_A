"""
Check: any blocking locks or long-running queries on Railway DB?
"""
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = "postgresql://postgres:puixywJTqFOFSPxiXAgSZRYiyyUqaXvH@switchyard.proxy.rlwy.net:25993/railway"

def run():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    print("=== Long-running queries (>5s) ===")
    cur.execute("""
        SELECT pid, now() - pg_stat_activity.query_start AS duration, query, state
        FROM pg_stat_activity
        WHERE (now() - pg_stat_activity.query_start) > interval '5 seconds'
          AND state != 'idle'
        ORDER BY duration DESC
    """)
    rows = cur.fetchall()
    if rows:
        for r in rows:
            print(f"  PID={r['pid']} state={r['state']} duration={r['duration']}")
            print(f"  Query: {r['query'][:200]}")
            print()
    else:
        print("  None found.")

    print("\n=== Blocking locks ===")
    cur.execute("""
        SELECT bl.pid AS blocked_pid, a.query AS blocked_query,
               kl.pid AS blocking_pid, ka.query AS blocking_query
        FROM pg_catalog.pg_locks bl
        JOIN pg_catalog.pg_stat_activity a ON a.pid = bl.pid
        JOIN pg_catalog.pg_locks kl ON kl.transactionid = bl.transactionid AND kl.pid != bl.pid
        JOIN pg_catalog.pg_stat_activity ka ON ka.pid = kl.pid
        WHERE NOT bl.granted
    """)
    locks = cur.fetchall()
    if locks:
        for l in locks:
            print(f"  BLOCKED PID={l['blocked_pid']}: {l['blocked_query'][:100]}")
            print(f"  BLOCKING PID={l['blocking_pid']}: {l['blocking_query'][:100]}")
    else:
        print("  No blocking locks.")

    print("\n=== Total connections ===")
    cur.execute("SELECT count(*) as cnt FROM pg_stat_activity")
    print(f"  {cur.fetchone()['cnt']} active connections")

    cur.close()
    conn.close()
    print("\n[DONE]")

if __name__ == "__main__":
    run()
