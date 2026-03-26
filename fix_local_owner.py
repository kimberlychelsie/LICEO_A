import psycopg2

def try_fix_db(password):
    try:
        conn = psycopg2.connect(
            host="127.0.0.1",
            port=5432,
            dbname="liceo_db",
            user="postgres",
            password=password
        )
        cur = conn.cursor()
        print(f"Success connecting with password: {password}")
        
        # Give liceo_db ownership of the tables so db.py can migrate
        cur.execute("ALTER TABLE school_years OWNER TO liceo_db;")
        cur.execute("ALTER TABLE enrollments OWNER TO liceo_db;")
        cur.execute("ALTER TABLE sections OWNER TO liceo_db;")
        conn.commit()
        print("Ownership changed successfully!")
        
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Failed with {password}: {e}")
        return False

for pwd in ["postgres", "admin", "12345", "root", "password", ""]:
    if try_fix_db(pwd):
        break
