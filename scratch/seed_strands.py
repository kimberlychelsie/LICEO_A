from db import get_db_connection
import psycopg2.extras

def seed_strands_to_existing():
    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        # Get generic Grade 11
        cursor.execute("SELECT enrollment_id FROM enrollments WHERE grade_level = 'Grade 11' AND branch_id = 1 ORDER BY enrollment_id")
        g11_rows = cursor.fetchall()
        
        strands_11 = ['11-GAS', '11-STEM', '11-HUMSS']
        for i, row in enumerate(g11_rows):
            strand = strands_11[i % 3]
            cursor.execute("UPDATE enrollments SET grade_level = %s WHERE enrollment_id = %s", (strand, row['enrollment_id']))
            print(f"Updated Enrollment {row['enrollment_id']} to {strand}")

        # Get generic Grade 12
        cursor.execute("SELECT enrollment_id FROM enrollments WHERE grade_level = 'Grade 12' AND branch_id = 1 ORDER BY enrollment_id")
        g12_rows = cursor.fetchall()
        
        strands_12 = ['12-GAS', '12-STEM', '12-HUMSS']
        for i, row in enumerate(g12_rows):
            strand = strands_12[i % 3]
            cursor.execute("UPDATE enrollments SET grade_level = %s WHERE enrollment_id = %s", (strand, row['enrollment_id']))
            print(f"Updated Enrollment {row['enrollment_id']} to {strand}")

        db.commit()
        print("Done seeding strands.")
            
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        cursor.close()
        db.close()

if __name__ == "__main__":
    seed_strands_to_existing()
