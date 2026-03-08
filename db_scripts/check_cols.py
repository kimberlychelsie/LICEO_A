import psycopg2

def check():
    conn = psycopg2.connect(host="127.0.0.1", port=5432, dbname="liceo_db", user="liceo_db", password="liceo123")
    cur = conn.cursor()
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='grade_levels';")
    print("Columns in grade_levels:")
    for row in cur.fetchall():
        print(" -", row[0])
    cur.close()
    conn.close()

if __name__ == "__main__":
    check()
