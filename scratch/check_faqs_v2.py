from db import get_db_connection
import psycopg2.extras

def check_faqs():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    print("--- ALL FAQs ---")
    cur.execute("SELECT id, question, branch_id FROM chatbot_faqs")
    rows = cur.fetchall()
    for row in rows:
        print(f"ID: {row['id']} | Branch: {row['branch_id']} | Q: {row['question']}")
    
    print("\n--- BRANCH 1 FAQs ---")
    cur.execute("SELECT id, question FROM chatbot_faqs WHERE branch_id = 1")
    rows = cur.fetchall()
    for row in rows:
        print(f"ID: {row['id']} | Q: {row['question']}")
        
    cur.close()
    conn.close()

if __name__ == "__main__":
    check_faqs()
