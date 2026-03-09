
from db import get_db_connection
import psycopg2.extras

def check_sync():
    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        # Check enrollment #3 (from screenshot)
        cursor.execute("SELECT * FROM enrollments WHERE branch_enrollment_no = 3")
        enrollment = cursor.fetchone()
        if not enrollment:
            print("Enrollment #3 not found")
            return
        
        eid = enrollment['enrollment_id']
        print(f"Enrollment ID: {eid}, Name: {enrollment['student_name']}")

        cursor.execute("SELECT * FROM billing WHERE enrollment_id = %s", (eid,))
        bill = cursor.fetchone()
        if bill:
            print(f"Bill: Total={bill['total_amount']}, Books={bill['books_fee']}, Uniform={bill['uniform_fee']}, Balance={bill['balance']}, Status={bill['status']}")
        else:
            print("No bill found")

        cursor.execute("""
            SELECT r.reservation_id, r.status, COALESCE(SUM(ri.line_total), 0) as total
            FROM reservations r
            LEFT JOIN reservation_items ri ON r.reservation_id = ri.reservation_id
            WHERE r.student_user_id IN (
                SELECT user_id FROM users WHERE enrollment_id = %s
                UNION
                SELECT u.user_id FROM users u JOIN student_accounts sa ON u.username = sa.username WHERE sa.enrollment_id = %s
            )
            GROUP BY r.reservation_id, r.status
        """, (eid, eid))
        res = cursor.fetchall()
        print("Reservations:")
        for r in res:
            print(f"  ID: {r['reservation_id']}, Status: {r['status']}, Total: {r['total']}")

    finally:
        cursor.close()
        db.close()

if __name__ == "__main__":
    check_sync()
