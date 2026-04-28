import psycopg2

DATABASE_URL = "postgresql://postgres:puixywJTqFOFSPxiXAgSZRYiyyUqaXvH@switchyard.proxy.rlwy.net:25993/railway"

def update_grade_levels():
    print("Updating grade levels on Railway...")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        cur = conn.cursor()
        
        # 1. Delete ALL previous attempts and generic grades
        cur.execute("""
            DELETE FROM grade_levels 
            WHERE name IN (
                'Grade 11', 'Grade 12', 
                '11-GAS', '11-STEM', '11-HUMSS', 
                '12-GAS', '12-STEM', '12-HUMSS',
                'GRADE 11-GAS', 'GRADE 11-STEM', 'GRADE 11-HUMSS',
                'GRADE 12-GAS', 'GRADE 12-STEM', 'GRADE 12-HUMSS',
                'Grade 11-Gas', 'Grade 11-Stem', 'Grade 11-Humms',
                'Grade 12-Gas', 'Grade 12-Stem', 'Grade 12-Humms'
            )
        """)
        print("Deleted old grades and previous strand attempts.")
        
        # 2. Insert new strands with 'Grade ' prefix and ALL CAPS strands
        cur.execute("""
            INSERT INTO grade_levels (name, display_order, branch_id) VALUES 
            ('Grade 11-GAS', 15, 1),
            ('Grade 11-STEM', 16, 1),
            ('Grade 11-HUMSS', 17, 1),
            ('Grade 12-GAS', 18, 1),
            ('Grade 12-STEM', 19, 1),
            ('Grade 12-HUMSS', 20, 1)
        """)
        print("Inserted new strands (GAS, STEM, HUMSS) with 'Grade ' prefix.")
        
        cur.close()
        conn.close()
        print("Update complete.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    update_grade_levels()
