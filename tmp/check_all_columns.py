import psycopg2

URL = "postgresql://postgres:puixywJTqFOFSPxiXAgSZRYiyyUqaXvH@switchyard.proxy.rlwy.net:25993/railway"

def check():
    try:
        conn = psycopg2.connect(URL)
        cur = conn.cursor()
        tables = ['teacher_announcements', 'grading_weights', 'attendance_scores', 'participation_scores', 'posted_grades']
        for table in tables:
            cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table}' AND table_schema = 'public'")
            cols = [r[0] for r in cur.fetchall()]
            print(f"Table: {table}")
            print(f"Columns: {', '.join(cols)}")
            print("-" * 20)
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check()
