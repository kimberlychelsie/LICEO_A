from db import get_db_connection
import psycopg2.extras

def check_parents():
    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cursor.execute("SELECT username FROM users WHERE role='parent' LIMIT 5")
        parents = cursor.fetchall()
        for p in parents:
            print(p['username'])
    finally:
        cursor.close()
        db.close()

if __name__ == "__main__":
    check_parents()
