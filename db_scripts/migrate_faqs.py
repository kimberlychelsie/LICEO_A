from db import get_db_connection
import sys

def migrate():
    db = get_db_connection()
    cur = db.cursor()
    try:
        cur.execute("SELECT id, question FROM chatbot_faqs")
        rows = cur.fetchall()
        for row in rows:
            q = row[1]
            if '|' not in q:
                new_q = f"General|{q}"
                cur.execute("UPDATE chatbot_faqs SET question = %s WHERE id = %s", (new_q, row[0]))
        db.commit()
        print("Successfully migrated existing questions.")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        cur.close()
        db.close()

if __name__ == "__main__":
    migrate()
