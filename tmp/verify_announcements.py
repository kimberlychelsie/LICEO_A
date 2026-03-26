import psycopg2

URL = "postgresql://postgres:puixywJTqFOFSPxiXAgSZRYiyyUqaXvH@switchyard.proxy.rlwy.net:25993/railway"

def verify():
    conn = psycopg2.connect(URL)
    cur = conn.cursor()
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'teacher_announcements' AND table_schema = 'public'")
    cols = [r[0] for r in cur.fetchall()]
    print("\n".join(cols))
    conn.close()

if __name__ == "__main__":
    verify()
