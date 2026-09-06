import sys
sys.path.append('.')
from dotenv import load_dotenv
load_dotenv()
import psycopg2
import psycopg2.extras
from db import get_db_connection

def main():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    query = """
        SELECT
            tc.table_name, 
            kcu.column_name, 
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name,
            rc.delete_rule
        FROM 
            information_schema.table_constraints AS tc 
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
              AND tc.table_schema = kcu.table_schema
            JOIN information_schema.referential_constraints AS rc
              ON tc.constraint_name = rc.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu
              ON ccu.constraint_name = rc.constraint_name
              AND ccu.table_schema = tc.table_schema
        WHERE ccu.table_name = 'users' AND ccu.column_name = 'user_id';
    """
    cur.execute(query)
    rows = cur.fetchall()
    print(f"Found {len(rows)} foreign keys referencing users(user_id):")
    for r in rows:
        print(f" - Table '{r['table_name']}' (col '{r['column_name']}') -> users.user_id | ON DELETE: {r['delete_rule']}")
        
    cur.close()
    conn.close()

if __name__ == '__main__':
    main()
