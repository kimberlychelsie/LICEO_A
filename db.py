import os
import logging
import psycopg2

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def get_db_connection():
    """
    Returns a new PostgreSQL database connection using environment variables:
    DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT
    """

    # Prefer IPv4 loopback to avoid ::1 (IPv6) surprises on Windows
    host = os.getenv("DB_HOST", "127.0.0.1")
    port = int(os.getenv("DB_PORT", "5432"))

    database = os.getenv("DB_NAME", "liceo_db1")
    user = os.getenv("DB_USER", "liceo_db1")
    password = os.getenv("DB_PASSWORD", "1234")

    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            dbname=database,
            user=user,
            password=password,
        )

        # ✅ Force UTC so NOW() always stores UTC consistently
        with conn.cursor() as cur:
            cur.execute("SET timezone = 'UTC'")
            
            # Simple migration for exams table
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'exams'")
            existing_cols = [r[0] for r in cur.fetchall()]
            if 'grading_period' not in existing_cols:
                cur.execute("ALTER TABLE exams ADD COLUMN grading_period VARCHAR(50)")
            if 'is_visible' not in existing_cols:
                cur.execute("ALTER TABLE exams ADD COLUMN is_visible BOOLEAN DEFAULT FALSE")
            if 'batch_id' not in existing_cols:
                cur.execute("ALTER TABLE exams ADD COLUMN batch_id VARCHAR(20)")
            conn.commit()

            # Simple migration for activities table
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'activities'")
            act_cols = [r[0] for r in cur.fetchall()]
            if 'grading_period' not in act_cols:
                cur.execute("ALTER TABLE activities ADD COLUMN grading_period VARCHAR(50)")
            if 'batch_id' not in act_cols:
                cur.execute("ALTER TABLE activities ADD COLUMN batch_id VARCHAR(20)")
            conn.commit()

            # Simple migration for attendance_scores table
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'attendance_scores'")
            att_cols = [r[0] for r in cur.fetchall()]
            if 'teacher_id' not in att_cols:
                cur.execute("ALTER TABLE attendance_scores ADD COLUMN teacher_id INTEGER")
            
            # Add unique constraint uq_attendance if missing
            cur.execute("""
                SELECT constraint_name 
                FROM information_schema.table_constraints 
                WHERE table_name = 'attendance_scores' AND constraint_name = 'uq_attendance'
            """)
            if not cur.fetchone():
                cur.execute("""
                    ALTER TABLE attendance_scores 
                    ADD CONSTRAINT uq_attendance UNIQUE (enrollment_id, section_id, subject_id, grading_period)
                """)
            conn.commit()

            # Profile image migration
            try:
                cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'users'")
                user_cols = [r[0] for r in cur.fetchall()]
                if 'profile_image' not in user_cols:
                    cur.execute("ALTER TABLE users ADD COLUMN profile_image VARCHAR(255)")
                if 'email' not in user_cols:
                    cur.execute("ALTER TABLE users ADD COLUMN email VARCHAR(255)")
                conn.commit()
            except Exception as e:
                logger.warning(f"Could not migrate users table: {e}")
                conn.rollback()  # Rollback failed transaction block
            
            try:
                cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'enrollments'")
                enr_cols = [r[0] for r in cur.fetchall()]
                if 'profile_image' not in enr_cols:
                    cur.execute("ALTER TABLE enrollments ADD COLUMN profile_image VARCHAR(255)")
                conn.commit()
            except Exception as e:
                logger.warning(f"Could not migrate enrollments profile_image: {e}")
                conn.rollback()
                
            # School years migration
            try:
                cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'school_years'")
                sy_cols = [r[0] for r in cur.fetchall()]
                if sy_cols:  # If table exists
                    if 'branch_id' not in sy_cols:
                        cur.execute("ALTER TABLE school_years ADD COLUMN branch_id INTEGER")
                    if 'is_active' not in sy_cols:
                        cur.execute("ALTER TABLE school_years ADD COLUMN is_active BOOLEAN DEFAULT FALSE")
                    conn.commit()
            except Exception as e:
                logger.warning(f"Could not migrate school_years table: {e}")
                conn.rollback()

            # Enrollments year_id migration
            try:
                cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'enrollments'")
                enr_c = [r[0] for r in cur.fetchall()]
                if 'year_id' not in enr_c:
                    if 'school_year_id' in enr_c:
                        cur.execute("ALTER TABLE enrollments RENAME COLUMN school_year_id TO year_id")
                    else:
                        cur.execute("ALTER TABLE enrollments ADD COLUMN year_id INTEGER")
                conn.commit()
            except Exception as e:
                logger.warning(f"Could not migrate enrollments year_id: {e}")
                conn.rollback()

            # Sections year_id migration
            try:
                cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'sections'")
                sec_c = [r[0] for r in cur.fetchall()]
                if 'year_id' not in sec_c:
                    cur.execute("ALTER TABLE sections ADD COLUMN year_id INTEGER")
                conn.commit()
            except Exception as e:
                logger.warning(f"Could not migrate sections year_id: {e}")
                conn.rollback()
                
            # student_accounts migration
            try:
                cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'student_accounts'")
                sa_cols = [r[0] for r in cur.fetchall()]
                if sa_cols:
                    if 'email' not in sa_cols:
                        cur.execute("ALTER TABLE student_accounts ADD COLUMN email VARCHAR(255)")
                    conn.commit()
            except Exception as e:
                logger.warning(f"Could not migrate student_accounts table: {e}")
                conn.rollback()

            try:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS individual_extensions (
                        extension_id SERIAL PRIMARY KEY,
                        enrollment_id INTEGER NOT NULL REFERENCES enrollments(enrollment_id) ON DELETE CASCADE,
                        item_type VARCHAR(20) NOT NULL,
                        item_id INTEGER NOT NULL,
                        new_due_date TIMESTAMP WITHOUT TIME ZONE NOT NULL,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                """)
                cur.execute("""
                    SELECT constraint_name 
                    FROM information_schema.table_constraints 
                    WHERE table_name = 'individual_extensions' AND constraint_name = 'uq_extension'
                """)
                if not cur.fetchone():
                    cur.execute("""
                        ALTER TABLE individual_extensions 
                        ADD CONSTRAINT uq_extension UNIQUE (enrollment_id, item_type, item_id)
                    """)
                conn.commit()
            except Exception as e:
                logger.warning(f"Could not migrate individual_extensions table: {e}")
                conn.rollback()

            # ONE-TIME CLEANUP: Delete test Teacher9 accounts directly on boot
            try:
                cur.execute("DELETE FROM users WHERE role='teacher' AND username ILIKE '%Teacher9%'")
                conn.commit()
            except Exception as e:
                conn.rollback()
                
        # Commit successful things
        conn.commit()

        return conn

    except psycopg2.OperationalError as e:
        logger.error(
            "DB connection failed. Check DB_NAME/DB_USER/DB_PASSWORD/DB_HOST/DB_PORT. "
            "Using host=%s port=%s db=%s user=%s",
            host, port, database, user
        )
        raise

    except Exception:
        logger.exception("Unexpected error connecting to DB")
        raise


def is_branch_active(branch_id):
    """
    Returns True if branch status is 'active' (or branch does not exist),
    False if status is anything else (e.g. 'inactive').
    """
    if not branch_id:
        return True

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT status FROM branches WHERE branch_id = %s", (branch_id,))
        row = cur.fetchone()
        if not row:
            return True
        status = row[0]
        return str(status or "").strip().lower() == "active"
    except Exception:
        logger.exception("Failed to check branch status")
        return True
    finally:
        try:
            cur.close()
        except Exception:
            pass
        conn.close()