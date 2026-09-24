import os
import json
import logging
import psycopg2

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

_MIGRATIONS_RUN = False

def get_db_connection():
    """
    Returns a new PostgreSQL database connection using environment variables:
    DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT
    """

    # Prefer IPv4 loopback to avoid ::1 (IPv6) surprises on Windows
    host = os.getenv("DB_HOST", "127.0.0.1")
    port = int(os.getenv("DB_PORT", "5432"))

    database = os.getenv("DB_NAME", "liceo_db")
    user = os.getenv("DB_USER", "liceo_db")
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
            
        global _MIGRATIONS_RUN
        if not _MIGRATIONS_RUN:
            cur = conn.cursor()
            
            # Simple migration for exams table
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'exams'")
            existing_cols = [r[0] for r in cur.fetchall()]
            if 'grading_period' not in existing_cols:
                cur.execute("ALTER TABLE exams ADD COLUMN grading_period VARCHAR(50)")
            if 'is_visible' not in existing_cols:
                cur.execute("ALTER TABLE exams ADD COLUMN is_visible BOOLEAN DEFAULT FALSE")
            if 'batch_id' not in existing_cols:
                cur.execute("ALTER TABLE exams ADD COLUMN batch_id VARCHAR(20)")
            if 'is_archived' not in existing_cols:
                cur.execute("ALTER TABLE exams ADD COLUMN is_archived BOOLEAN DEFAULT FALSE")
            if 'class_mode' not in existing_cols:
                cur.execute("ALTER TABLE exams ADD COLUMN class_mode VARCHAR(20) DEFAULT 'Virtual'")
            conn.commit()

            # Simple migration for activities table
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'activities'")
            act_cols = [r[0] for r in cur.fetchall()]
            if 'grading_period' not in act_cols:
                cur.execute("ALTER TABLE activities ADD COLUMN grading_period VARCHAR(50)")
            if 'batch_id' not in act_cols:
                cur.execute("ALTER TABLE activities ADD COLUMN batch_id VARCHAR(20)")
            if 'is_archived' not in act_cols:
                cur.execute("ALTER TABLE activities ADD COLUMN is_archived BOOLEAN DEFAULT FALSE")
            conn.commit()

            # Simple migration for attendance_scores table
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'attendance_scores'")
            att_cols = [r[0] for r in cur.fetchall()]
            if 'teacher_id' not in att_cols:
                cur.execute("ALTER TABLE attendance_scores ADD COLUMN teacher_id INTEGER")
            if 'total_days' not in att_cols:
                cur.execute("ALTER TABLE attendance_scores ADD COLUMN total_days INTEGER DEFAULT 10")
            
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

            # Profile image and name split migration
            try:
                cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'users'")
                user_cols = [r[0] for r in cur.fetchall()]
                if 'profile_image' not in user_cols:
                    cur.execute("ALTER TABLE users ADD COLUMN profile_image VARCHAR(255)")
                if 'email' not in user_cols:
                    cur.execute("ALTER TABLE users ADD COLUMN email VARCHAR(255)")
                if 'first_name' not in user_cols:
                    cur.execute("ALTER TABLE users ADD COLUMN first_name VARCHAR(255)")
                if 'middle_name' not in user_cols:
                    cur.execute("ALTER TABLE users ADD COLUMN middle_name VARCHAR(255)")
                if 'last_name' not in user_cols:
                    cur.execute("ALTER TABLE users ADD COLUMN last_name VARCHAR(255)")
                if 'user_roles' not in user_cols:
                    cur.execute("ALTER TABLE users ADD COLUMN user_roles TEXT")
                conn.commit()

                # Backfill split name columns from full_name if first_name is empty
                cur.execute("SELECT user_id, full_name FROM users WHERE first_name IS NULL AND full_name IS NOT NULL AND TRIM(full_name) <> ''")
                unfilled = cur.fetchall()
                if unfilled:
                    for row in unfilled:
                        uid = row[0]
                        fname = (row[1] or "").strip()
                        if fname:
                            parts = fname.split()
                            if len(parts) == 1:
                                first, middle, last = parts[0], None, None
                            elif len(parts) == 2:
                                first, middle, last = parts[0], None, parts[1]
                            else:
                                first = parts[0]
                                last = parts[-1]
                                middle = " ".join(parts[1:-1])
                            cur.execute(
                                "UPDATE users SET first_name=%s, middle_name=%s, last_name=%s WHERE user_id=%s",
                                (first, middle, last, uid)
                            )
                    conn.commit()

                # Backfill/sync parent user names in users table from linked student enrollments
                cur.execute("""
                    UPDATE users u
                    SET 
                        first_name = COALESCE(NULLIF(TRIM(u.first_name), ''), NULLIF(TRIM(e.guardian_first_name), '')),
                        middle_name = COALESCE(NULLIF(TRIM(u.middle_name), ''), NULLIF(TRIM(e.guardian_middle_name), '')),
                        last_name = COALESCE(NULLIF(TRIM(u.last_name), ''), NULLIF(TRIM(e.guardian_last_name), '')),
                        full_name = COALESCE(
                            NULLIF(TRIM(u.full_name), ''),
                            NULLIF(TRIM(CONCAT_WS(' ', NULLIF(TRIM(e.guardian_first_name), ''), NULLIF(TRIM(e.guardian_middle_name), ''), NULLIF(TRIM(e.guardian_last_name), ''))), '')
                        )
                    FROM parent_student ps
                    JOIN enrollments e ON ps.student_id = e.enrollment_id
                    WHERE u.user_id = ps.parent_id
                      AND u.role = 'parent'
                      AND (
                          u.full_name IS NULL 
                          OR TRIM(u.full_name) = '' 
                          OR u.first_name IS NULL 
                          OR u.last_name IS NULL
                      )
                """)
                conn.commit()

                # Multi-role migration & Auto-linking by email match
                try:
                    # 1. Backfill user_roles for users where user_roles is NULL
                    cur.execute("SELECT user_id, role, user_roles FROM users WHERE user_roles IS NULL OR TRIM(user_roles) = ''")
                    rows = cur.fetchall()
                    for uid, r, ur in rows:
                        roles = [r] if r else []
                        cur.execute("UPDATE users SET user_roles = %s WHERE user_id = %s", (json.dumps(roles), uid))
                    conn.commit()

                    # 2. Auto-link parent role by email match (if user email matches guardian_email)
                    cur.execute("""
                        SELECT u.user_id, u.user_roles, e.enrollment_id
                        FROM users u
                        JOIN enrollments e ON LOWER(TRIM(u.email)) = LOWER(TRIM(e.guardian_email))
                        WHERE u.email IS NOT NULL AND TRIM(u.email) <> ''
                    """)
                    matches = cur.fetchall()
                    for uid, ur_json, eid in matches:
                        cur.execute("""
                            INSERT INTO parent_student (parent_id, student_id, relationship)
                            VALUES (%s, %s, 'guardian')
                            ON CONFLICT DO NOTHING
                        """, (uid, eid))
                        
                        try:
                            roles_list = json.loads(ur_json) if ur_json else []
                        except Exception:
                            roles_list = []
                        if 'parent' not in roles_list:
                            roles_list.append('parent')
                            cur.execute("UPDATE users SET user_roles = %s WHERE user_id = %s", (json.dumps(roles_list), uid))
                    conn.commit()

                    # 3. Ensure any user who has linked children in parent_student has 'parent' in user_roles
                    cur.execute("""
                        SELECT DISTINCT u.user_id, u.user_roles
                        FROM users u
                        JOIN parent_student ps ON u.user_id = ps.parent_id
                    """)
                    ps_matches = cur.fetchall()
                    for uid, ur_json in ps_matches:
                        try:
                            roles_list = json.loads(ur_json) if ur_json else []
                        except Exception:
                            roles_list = []
                        if 'parent' not in roles_list:
                            roles_list.append('parent')
                            cur.execute("UPDATE users SET user_roles = %s WHERE user_id = %s", (json.dumps(roles_list), uid))
                    conn.commit()
                except Exception as e:
                    logger.warning(f"Could not auto-link multi-role parent accounts: {e}")
                    conn.rollback()

            except Exception as e:
                logger.warning(f"Could not migrate users table or backfill names: {e}")
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

            # Branches location migration
            try:
                cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'branches'")
                branch_cols = [r[0] for r in cur.fetchall()]
                if branch_cols:
                    if 'latitude' not in branch_cols:
                        cur.execute("ALTER TABLE branches ADD COLUMN latitude NUMERIC(10, 7)")
                    if 'longitude' not in branch_cols:
                        cur.execute("ALTER TABLE branches ADD COLUMN longitude NUMERIC(10, 7)")
                    conn.commit()
            except Exception as e:
                logger.warning(f"Could not migrate branches table: {e}")
                conn.rollback()

            # Enrollments migrations (Missing columns found)
            try:
                cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'enrollments'")
                enr_c = [r[0] for r in cur.fetchall()]
                
                # Existing migration logic
                if 'year_id' not in enr_c:
                    if 'school_year_id' in enr_c:
                        cur.execute("ALTER TABLE enrollments RENAME COLUMN school_year_id TO year_id")
                    else:
                        cur.execute("ALTER TABLE enrollments ADD COLUMN year_id INTEGER")
                
                # New required columns for inline editing and details
                optional_cols = [
                    ("father_name", "VARCHAR(255)"),
                    ("mother_name", "VARCHAR(255)"),
                    ("enroll_type", "VARCHAR(255)"),
                    ("enroll_date", "DATE"),
                    ("birthplace", "VARCHAR(255)"),
                    ("remarks", "TEXT"),
                    ("father_contact", "VARCHAR(255)"),
                    ("mother_contact", "VARCHAR(255)"),
                    ("father_occupation", "VARCHAR(255)"),
                    ("mother_occupation", "VARCHAR(255)"),
                    ("school_year", "VARCHAR(255)"),
                    ("rejection_reason", "TEXT"),
                    ("rejected_at", "TIMESTAMP"),
                    ("academic_status", "VARCHAR(50)")
                ]
                for col_name, col_type in optional_cols:
                    if col_name not in enr_c:
                        cur.execute(f"ALTER TABLE enrollments ADD COLUMN {col_name} {col_type}")
                
                conn.commit()
            except Exception as e:
                logger.warning(f"Could not migrate enrollments table: {e}")
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

            # section_teachers is_archived migration
            try:
                cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'section_teachers'")
                st_cols = [r[0] for r in cur.fetchall()]
                if 'is_archived' not in st_cols:
                    cur.execute("ALTER TABLE section_teachers ADD COLUMN is_archived BOOLEAN DEFAULT FALSE")
                conn.commit()
            except Exception as e:
                logger.warning(f"Could not migrate section_teachers is_archived: {e}")
                conn.rollback()

            # ── Grading year_id consistency (posted_grades + sections backfill) ──
            # The teacher grading flow uses:
            # - sections.year_id when recomputing grades
            # - posted_grades(year_id) for ON CONFLICT upserts
            try:
                # 1) Ensure posted_grades.year_id exists
                cur.execute("""
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name='posted_grades' AND column_name='year_id'
                """)
                has_posted_year = cur.fetchone() is not None
                if not has_posted_year:
                    cur.execute("ALTER TABLE posted_grades ADD COLUMN year_id INTEGER")

                # 2) Backfill sections.year_id from enrollments.year_id (best-effort)
                cur.execute("""
                    UPDATE sections s
                    SET year_id = sub.year_id
                    FROM (
                        SELECT section_id, MAX(year_id) AS year_id
                        FROM enrollments
                        WHERE year_id IS NOT NULL AND year_id <> 0
                        GROUP BY section_id
                    ) sub
                    WHERE s.section_id = sub.section_id
                      AND (s.year_id IS NULL OR s.year_id = 0)
                """)

                # 3) Backfill posted_grades.year_id from enrollments.year_id, fallback to sections.year_id
                cur.execute("""
                    UPDATE posted_grades pg
                    SET year_id = e.year_id
                    FROM enrollments e
                    WHERE pg.enrollment_id = e.enrollment_id
                      AND (pg.year_id IS NULL OR pg.year_id = 0)
                      AND e.year_id IS NOT NULL AND e.year_id <> 0
                """)
                cur.execute("""
                    UPDATE posted_grades pg
                    SET year_id = s.year_id
                    FROM sections s
                    WHERE pg.section_id = s.section_id
                      AND (pg.year_id IS NULL OR pg.year_id = 0)
                      AND s.year_id IS NOT NULL AND s.year_id <> 0
                """)

                # 4) Replace old unique constraint so teacher_post_grades ON CONFLICT works
                #    routes/teacher.py uses:
                #    ON CONFLICT (enrollment_id, subject_id, grading_period, year_id)
                cur.execute("""
                    SELECT 1
                    FROM information_schema.table_constraints
                    WHERE table_name='posted_grades'
                      AND constraint_name='posted_grades_enrollment_id_subject_id_grading_period_key'
                """)
                has_old_unique = cur.fetchone() is not None
                if has_old_unique:
                    cur.execute("""
                        ALTER TABLE posted_grades
                        DROP CONSTRAINT posted_grades_enrollment_id_subject_id_grading_period_key
                    """)

                cur.execute("""
                    SELECT 1
                    FROM information_schema.table_constraints
                    WHERE table_name='posted_grades'
                      AND constraint_name='posted_grades_enrollment_id_subject_id_grading_period_year_id_key'
                """)
                has_new_unique = cur.fetchone() is not None
                if not has_new_unique:
                    cur.execute("""
                        ALTER TABLE posted_grades
                        ADD CONSTRAINT posted_grades_enrollment_id_subject_id_grading_period_year_id_key
                        UNIQUE (enrollment_id, subject_id, grading_period, year_id)
                    """)

                conn.commit()
            except Exception as e:
                logger.warning(f"Could not ensure posted_grades/year_id consistency: {e}")
                conn.rollback()
                
            # student_accounts migration
            try:
                cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'student_accounts'")
                sa_cols = [r[0] for r in cur.fetchall()]
                if sa_cols:
                    if 'email' not in sa_cols:
                        cur.execute("ALTER TABLE student_accounts ADD COLUMN email VARCHAR(255)")
                    if 'require_password_change' not in sa_cols:
                        cur.execute("ALTER TABLE student_accounts ADD COLUMN require_password_change BOOLEAN DEFAULT FALSE")
                    if 'last_password_change' not in sa_cols:
                        cur.execute("ALTER TABLE student_accounts ADD COLUMN last_password_change TIMESTAMP")
                    if 'profile_image' not in sa_cols:
                        cur.execute("ALTER TABLE student_accounts ADD COLUMN profile_image VARCHAR(255)")
                    conn.commit()
            except Exception as e:
                logger.warning(f"Could not migrate student_accounts table: {e}")
                conn.rollback()

            try:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS individual_extensions (
                        extension_id SERIAL PRIMARY KEY,
                        enrollment_id INTEGER NOT NULL REFERENCES enrollments(enrollment_id) ON DELETE CASCADE,
                        student_id INTEGER,
                        item_type VARCHAR(20) NOT NULL,
                        item_id INTEGER NOT NULL,
                        new_due_date TIMESTAMP WITHOUT TIME ZONE NOT NULL,
                        year_id INTEGER,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                """)
                cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'individual_extensions'")
                ext_cols = [r[0] for r in cur.fetchall()]
                if 'student_id' not in ext_cols:
                    cur.execute("ALTER TABLE individual_extensions ADD COLUMN student_id INTEGER")
                if 'year_id' not in ext_cols:
                    cur.execute("ALTER TABLE individual_extensions ADD COLUMN year_id INTEGER")
                    cur.execute("""
                        UPDATE individual_extensions ie
                        SET year_id = e.year_id
                        FROM enrollments e
                        WHERE ie.enrollment_id = e.enrollment_id AND ie.year_id IS NULL
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

            # SWAFO migrations
            try:
                cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'users'")
                u_cols = [r[0] for r in cur.fetchall()]
                if 'is_swafo' not in u_cols:
                    cur.execute("ALTER TABLE users ADD COLUMN is_swafo BOOLEAN DEFAULT FALSE")
                if 'is_dc' not in u_cols:
                    cur.execute("ALTER TABLE users ADD COLUMN is_dc BOOLEAN DEFAULT FALSE")
                
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS swafo_records (
                        record_id SERIAL PRIMARY KEY,
                        enrollment_id INTEGER UNIQUE REFERENCES enrollments(enrollment_id) ON DELETE CASCADE,
                        student_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
                        family_members JSONB DEFAULT '[]'::jsonb,
                        health_info JSONB DEFAULT '{}'::jsonb,
                        education_history JSONB DEFAULT '[]'::jsonb,
                        summer_subjects JSONB DEFAULT '[]'::jsonb,
                        religion_info JSONB DEFAULT '{}'::jsonb,
                        vocation_info JSONB DEFAULT '{}'::jsonb,
                        general_info JSONB DEFAULT '{}'::jsonb,
                        status VARCHAR(50) DEFAULT 'Draft',
                        teacher_notes TEXT,
                        reviewed_by INTEGER REFERENCES users(user_id),
                        reviewed_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                cur.execute("""
                    CREATE TABLE IF NOT EXISTS swafo_discipline_log (
                        log_id SERIAL PRIMARY KEY,
                        enrollment_id INTEGER REFERENCES enrollments(enrollment_id) ON DELETE CASCADE,
                        student_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
                        branch_id INTEGER,
                        logged_by INTEGER REFERENCES users(user_id),
                        reported_by INTEGER REFERENCES users(user_id),
                        incident_date DATE NOT NULL,
                        incident_type VARCHAR(100),
                        offense_level VARCHAR(50),
                        severity VARCHAR(50),
                        description TEXT,
                        action_taken TEXT,
                        status VARCHAR(50) DEFAULT 'Pending',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'swafo_discipline_log'")
                dl_cols = [r[0] for r in cur.fetchall()]
                if 'branch_id' not in dl_cols:
                    cur.execute("ALTER TABLE swafo_discipline_log ADD COLUMN branch_id INTEGER")
                if 'logged_by' not in dl_cols:
                    cur.execute("ALTER TABLE swafo_discipline_log ADD COLUMN logged_by INTEGER")
                if 'incident_type' not in dl_cols:
                    cur.execute("ALTER TABLE swafo_discipline_log ADD COLUMN incident_type VARCHAR(100)")
                if 'severity' not in dl_cols:
                    cur.execute("ALTER TABLE swafo_discipline_log ADD COLUMN severity VARCHAR(50)")
                if 'offense_level' not in dl_cols:
                    cur.execute("ALTER TABLE swafo_discipline_log ADD COLUMN offense_level VARCHAR(50)")
                if 'referred_to_swafo' not in dl_cols:
                    cur.execute("ALTER TABLE swafo_discipline_log ADD COLUMN referred_to_swafo BOOLEAN DEFAULT FALSE")
                if 'referral_reason' not in dl_cols:
                    cur.execute("ALTER TABLE swafo_discipline_log ADD COLUMN referral_reason TEXT")
                if 'status' not in dl_cols:
                    cur.execute("ALTER TABLE swafo_discipline_log ADD COLUMN status VARCHAR(50) DEFAULT 'Pending'")
                
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS swafo_parent_conferences (
                        conference_id SERIAL PRIMARY KEY,
                        branch_id INTEGER,
                        enrollment_id INTEGER REFERENCES enrollments(enrollment_id) ON DELETE CASCADE,
                        discipline_log_id INTEGER REFERENCES swafo_discipline_log(log_id) ON DELETE SET NULL,
                        scheduled_by INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
                        title VARCHAR(255) NOT NULL,
                        conference_date DATE NOT NULL,
                        conference_time VARCHAR(50),
                        meeting_type VARCHAR(50) DEFAULT 'in_person',
                        meeting_location VARCHAR(255),
                        agenda TEXT,
                        status VARCHAR(50) DEFAULT 'scheduled',
                        parent_notes TEXT,
                        minutes_of_meeting TEXT,
                        agreements TEXT,
                        parent_acknowledged_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
            except Exception as e:
                logger.warning(f"Could not migrate SWAFO tables: {e}")
                conn.rollback()

            # exam_student_permissions migration
            try:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS exam_student_permissions (
                        permission_id SERIAL PRIMARY KEY,
                        exam_id INTEGER NOT NULL REFERENCES exams(exam_id) ON DELETE CASCADE,
                        enrollment_id INTEGER NOT NULL REFERENCES enrollments(enrollment_id) ON DELETE CASCADE,
                        is_allowed BOOLEAN DEFAULT TRUE,
                        UNIQUE (exam_id, enrollment_id)
                    )
                """)
                conn.commit()
            except Exception as e:
                logger.warning(f"Could not migrate exam_student_permissions table: {e}")
                conn.rollback()

            # password_reset_tokens migration
            try:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS password_reset_tokens (
                      id SERIAL PRIMARY KEY,
                      token_hash TEXT NOT NULL UNIQUE,
                      user_id INTEGER NULL REFERENCES users(user_id) ON DELETE CASCADE,
                      student_account_id INTEGER NULL REFERENCES student_accounts(account_id) ON DELETE CASCADE,
                      email TEXT NOT NULL,
                      created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                      expires_at TIMESTAMP NOT NULL,
                      used_at TIMESTAMP NULL
                    )
                """)
                conn.commit()
            except Exception as e:
                logger.warning(f"Could not migrate password_reset_tokens table: {e}")
                conn.rollback()

            # parent_notifications migration
            try:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS parent_notifications (
                        notif_id SERIAL PRIMARY KEY,
                        parent_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                        student_id INTEGER REFERENCES enrollments(enrollment_id) ON DELETE CASCADE,
                        title VARCHAR(255) NOT NULL,
                        message TEXT NOT NULL,
                        link VARCHAR(255),
                        is_read BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                """)
                conn.commit()
            except Exception as e:
                logger.warning(f"Could not migrate parent_notifications table: {e}")
                conn.rollback()

            # schedules migration (is_archived)
            try:
                cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'schedules'")
                sch_cols = [r[0] for r in cur.fetchall()]
                if sch_cols:
                    if 'is_archived' not in sch_cols:
                        cur.execute("ALTER TABLE schedules ADD COLUMN is_archived BOOLEAN DEFAULT FALSE")
                    conn.commit()
                else: 
                    # If table logic is missing elsewhere, skip for now but log
                    logger.warning("Schedules table not found during migration check.")
            except Exception as e:
                logger.warning(f"Could not migrate schedules table: {e}")
                conn.rollback()

            # Add ON DELETE CASCADE for enrollments related tables
            try:
                # 1. Clean up orphaned records to allow constraints
                cur.execute("DELETE FROM student_accounts WHERE enrollment_id IS NOT NULL AND enrollment_id NOT IN (SELECT enrollment_id FROM enrollments)")
                cur.execute("DELETE FROM activity_submissions WHERE enrollment_id IS NOT NULL AND enrollment_id NOT IN (SELECT enrollment_id FROM enrollments)")
                cur.execute("DELETE FROM exam_results WHERE enrollment_id IS NOT NULL AND enrollment_id NOT IN (SELECT enrollment_id FROM enrollments)")
                cur.execute("DELETE FROM attendance_scores WHERE enrollment_id IS NOT NULL AND enrollment_id NOT IN (SELECT enrollment_id FROM enrollments)")
                cur.execute("DELETE FROM posted_grades WHERE enrollment_id IS NOT NULL AND enrollment_id NOT IN (SELECT enrollment_id FROM enrollments)")

                # 2. Add CASCADE to student_accounts
                cur.execute("""
                    ALTER TABLE student_accounts
                    DROP CONSTRAINT IF EXISTS student_accounts_enrollment_id_fkey,
                    ADD CONSTRAINT student_accounts_enrollment_id_fkey
                    FOREIGN KEY (enrollment_id) REFERENCES enrollments(enrollment_id) ON DELETE CASCADE
                """)

                # 3. Add CASCADE to activity_submissions
                cur.execute("""
                    ALTER TABLE activity_submissions
                    DROP CONSTRAINT IF EXISTS activity_submissions_enrollment_id_fkey,
                    ADD CONSTRAINT activity_submissions_enrollment_id_fkey
                    FOREIGN KEY (enrollment_id) REFERENCES enrollments(enrollment_id) ON DELETE CASCADE
                """)

                # 4. Add CASCADE to exam_results
                cur.execute("""
                    ALTER TABLE exam_results
                    DROP CONSTRAINT IF EXISTS exam_results_enrollment_id_fkey,
                    ADD CONSTRAINT exam_results_enrollment_id_fkey
                    FOREIGN KEY (enrollment_id) REFERENCES enrollments(enrollment_id) ON DELETE CASCADE
                """)

                # 5. Add CASCADE to attendance_scores
                cur.execute("""
                    ALTER TABLE attendance_scores
                    DROP CONSTRAINT IF EXISTS attendance_scores_enrollment_id_fkey,
                    ADD CONSTRAINT attendance_scores_enrollment_id_fkey
                    FOREIGN KEY (enrollment_id) REFERENCES enrollments(enrollment_id) ON DELETE CASCADE
                """)

                # 6. Add CASCADE to posted_grades
                cur.execute("""
                    ALTER TABLE posted_grades
                    DROP CONSTRAINT IF EXISTS posted_grades_enrollment_id_fkey,
                    ADD CONSTRAINT posted_grades_enrollment_id_fkey
                    FOREIGN KEY (enrollment_id) REFERENCES enrollments(enrollment_id) ON DELETE CASCADE
                """)
                conn.commit()
            except Exception as e:
                logger.warning(f"Could not add ON DELETE CASCADE to enrollment-related tables: {e}")
                conn.rollback()

            # announcements migration
            try:
                cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'announcements'")
                ann_cols = [r[0] for r in cur.fetchall()]
                if ann_cols:
                    if 'audience' not in ann_cols:
                        cur.execute("ALTER TABLE announcements ADD COLUMN audience TEXT NOT NULL DEFAULT 'all'")
                    conn.commit()
            except Exception as e:
                logger.warning(f"Could not migrate announcements table: {e}")
                conn.rollback()

            # holidays migration
            try:
                cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'holidays'")
                h_cols = [r[0] for r in cur.fetchall()]
                if h_cols:
                    if 'status' not in h_cols:
                        cur.execute("ALTER TABLE holidays ADD COLUMN status VARCHAR(20) DEFAULT 'active'")
                    conn.commit()
            except Exception as e:
                logger.warning(f"Could not migrate holidays table: {e}")
                conn.rollback()

            # ── Activity Submissions attachments migration ──
            try:
                cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'activity_submissions'")
                sub_cols = [r[0] for r in cur.fetchall()]
                if 'attachments' not in sub_cols:
                    cur.execute("ALTER TABLE activity_submissions ADD COLUMN attachments JSONB")
                if 'is_viewed' not in sub_cols:
                    cur.execute("ALTER TABLE activity_submissions ADD COLUMN is_viewed BOOLEAN DEFAULT FALSE")
                
                conn.commit()
            except Exception as e:
                logger.warning(f"Could not migrate activity_submissions: {e}")
                conn.rollback()

            # ── Inventory Items image_url / uniform catalog migration ──
            try:
                cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'inventory_items'")
                inv_cols = [r[0] for r in cur.fetchall()]
                if 'image_url' not in inv_cols:
                    cur.execute("ALTER TABLE inventory_items ADD COLUMN image_url TEXT")
                if 'parent_item_id' not in inv_cols:
                    cur.execute("ALTER TABLE inventory_items ADD COLUMN parent_item_id INTEGER")
                if 'is_set_piece' not in inv_cols:
                    cur.execute("ALTER TABLE inventory_items ADD COLUMN is_set_piece BOOLEAN DEFAULT FALSE")
                if 'size_price_step' not in inv_cols:
                    cur.execute("ALTER TABLE inventory_items ADD COLUMN size_price_step NUMERIC(12,2) DEFAULT 20")

                # Auto-populate uniform images from static folder if missing
                uniform_images = {
                    'Pre-Elementary Boys Set': '/static/img/PRE_ELEM_BOYS_SET.jpg',
                    'Pre-Elementary Girls Set': '/static/img/PRE_ELEM_GIRLS_SET.jpg',
                    'Elementary G4-6 Boys Set': '/static/img/ELEM_G4to6_BOYS_SET.jpg',
                    'JHS Boys Uniform Set': '/static/img/JHS_BOYS_SET.jpg',
                    'JHS Girls Uniform Set': '/static/img/JHS_GIRLS_SET.jpg',
                    'SHS Boys Uniform Set': '/static/img/SHS_BOYS_SET.jpg',
                    'SHS Girls Uniform Set': '/static/img/SHS_GIRLS_SET.jpg',
                    'PE Uniform': '/static/img/PE_SET.jpg'
                }
                
                for item_name, img_path in uniform_images.items():
                    cur.execute("""
                        UPDATE inventory_items 
                        SET image_url = %s 
                        WHERE item_name = %s AND (image_url IS NULL OR image_url = '')
                    """, (img_path, item_name))
                
                conn.commit()
            except Exception as e:
                logger.warning(f"Could not migrate inventory_items catalog columns: {e}")
                conn.rollback()

            # ── Financial year_id migration ──
            try:
                cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'billing'")
                bill_cols = [r[0] for r in cur.fetchall()]
                if 'year_id' not in bill_cols:
                    cur.execute("ALTER TABLE billing ADD COLUMN year_id INTEGER")
                    # Backfill from enrollments
                    cur.execute("""
                        UPDATE billing b
                        SET year_id = e.year_id
                        FROM enrollments e
                        WHERE b.enrollment_id = e.enrollment_id
                          AND b.year_id IS NULL
                    """)
                
                cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'payments'")
                pay_cols = [r[0] for r in cur.fetchall()]
                if 'year_id' not in pay_cols:
                    cur.execute("ALTER TABLE payments ADD COLUMN year_id INTEGER")
                    # Backfill from billing
                    cur.execute("""
                        UPDATE payments p
                        SET year_id = b.year_id
                        FROM billing b
                        WHERE p.bill_id = b.bill_id
                          AND p.year_id IS NULL
                    """)
                
                if 'target_type' not in pay_cols:
                    cur.execute("ALTER TABLE payments ADD COLUMN target_type VARCHAR(50) DEFAULT 'general'")
                if 'target_id' not in pay_cols:
                    cur.execute("ALTER TABLE payments ADD COLUMN target_id INTEGER")

                conn.commit()
            except Exception as e:
                logger.warning(f"Could not migrate financial tables: {e}")
                conn.rollback()

            # SEED GRADE LEVELS: Ensure Grade 11 & Grade 12 exist in grade_levels table
            try:
                grades_to_add = [
                    ('Grade 11', 13.0),
                    ('Grade 12', 14.0)
                ]
                for g_name, g_order in grades_to_add:
                    cur.execute("SELECT id FROM grade_levels WHERE name = %s AND branch_id IS NULL", (g_name,))
                    if not cur.fetchone():
                        cur.execute("INSERT INTO grade_levels (name, display_order) VALUES (%s, %s)", (g_name, g_order))
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.warning(f"Grade levels seeding failed: {e}")

            # ONE-TIME CLEANUP: Delete test Teacher9 accounts directly on boot
            try:
                cur.execute("DELETE FROM users WHERE role='teacher' AND username ILIKE '%Teacher9%'")
                conn.commit()
            except Exception as e:
                conn.rollback()
            # ── grade_overrides table (teacher manual component score edits) ──
            try:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS grade_overrides (
                        id               SERIAL PRIMARY KEY,
                        enrollment_id    INTEGER NOT NULL REFERENCES enrollments(enrollment_id) ON DELETE CASCADE,
                        section_id       INTEGER NOT NULL,
                        subject_id       INTEGER NOT NULL,
                        grading_period   VARCHAR(20) NOT NULL,
                        year_id          INTEGER NOT NULL,
                        override_ww      NUMERIC(6,2),
                        override_pt      NUMERIC(6,2),
                        override_qa      NUMERIC(6,2),
                        override_note    TEXT,
                        overridden_by    INTEGER,
                        overridden_at    TIMESTAMP DEFAULT NOW(),
                        UNIQUE (enrollment_id, subject_id, grading_period, year_id)
                    )
                """)
                conn.commit()
            except Exception as e:
                logger.warning(f"Could not create grade_overrides table: {e}")
                conn.rollback()

            # ── grade_submission_requests table (Grade review/approval workflow) ──
            try:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS grade_submission_requests (
                        id                      SERIAL PRIMARY KEY,
                        section_id              INTEGER NOT NULL REFERENCES sections(section_id) ON DELETE CASCADE,
                        subject_id              INTEGER NOT NULL REFERENCES subjects(subject_id) ON DELETE CASCADE,
                        grading_period          VARCHAR(20) NOT NULL,
                        year_id                 INTEGER NOT NULL,
                        branch_id               INTEGER NOT NULL,
                        status                  VARCHAR(30) DEFAULT 'draft',
                        submitted_by            INTEGER REFERENCES users(user_id),
                        submitted_at            TIMESTAMP,
                        registrar_approved_by   INTEGER REFERENCES users(user_id),
                        registrar_approved_at   TIMESTAMP,
                        admin_approved_by       INTEGER REFERENCES users(user_id),
                        admin_approved_at       TIMESTAMP,
                        rejection_remarks       TEXT,
                        rejected_by             INTEGER REFERENCES users(user_id),
                        rejected_at             TIMESTAMP,
                        UNIQUE (section_id, subject_id, grading_period, year_id)
                    )
                """)
                conn.commit()
            except Exception as e:
                logger.warning(f"Could not create grade_submission_requests table: {e}")
                conn.rollback()

            # ── uniform_orders and uniform_order_items tables migration ──
            try:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS uniform_orders (
                        order_id            SERIAL PRIMARY KEY,
                        order_number        VARCHAR(50) UNIQUE NOT NULL,
                        enrollment_id       INTEGER NOT NULL REFERENCES enrollments(enrollment_id) ON DELETE CASCADE,
                        student_user_id     INTEGER,
                        branch_id           INTEGER NOT NULL,
                        year_id             INTEGER,
                        total_amount        NUMERIC(10,2) NOT NULL DEFAULT 0.00,
                        payment_status      VARCHAR(20) DEFAULT 'Unpaid',
                        order_status        VARCHAR(30) DEFAULT 'For Ordering',
                        created_by_user_id  INTEGER,
                        bill_id             INTEGER,
                        created_at          TIMESTAMP DEFAULT NOW(),
                        onsite_arrived_at   TIMESTAMP,
                        claimed_at          TIMESTAMP
                    )
                """)
                conn.commit()

                cur.execute("""
                    CREATE TABLE IF NOT EXISTS uniform_order_items (
                        item_id             SERIAL PRIMARY KEY,
                        order_id            INTEGER NOT NULL REFERENCES uniform_orders(order_id) ON DELETE CASCADE,
                        inventory_item_id   INTEGER,
                        item_name           VARCHAR(255) NOT NULL,
                        size_label          VARCHAR(50),
                        unit_price          NUMERIC(10,2) NOT NULL DEFAULT 0.00,
                        quantity            INTEGER NOT NULL DEFAULT 1,
                        line_total          NUMERIC(10,2) NOT NULL DEFAULT 0.00,
                        created_at          TIMESTAMP DEFAULT NOW()
                    )
                """)
                conn.commit()

                # Migration for missing columns in uniform_orders
                cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'uniform_orders'")
                uo_cols = [r[0] for r in cur.fetchall()]
                if uo_cols:
                    if 'created_by_user_id' not in uo_cols:
                        cur.execute("ALTER TABLE uniform_orders ADD COLUMN created_by_user_id INTEGER")
                    if 'bill_id' not in uo_cols:
                        cur.execute("ALTER TABLE uniform_orders ADD COLUMN bill_id INTEGER")
                    if 'onsite_arrived_at' not in uo_cols:
                        cur.execute("ALTER TABLE uniform_orders ADD COLUMN onsite_arrived_at TIMESTAMP")
                    if 'claimed_at' not in uo_cols:
                        cur.execute("ALTER TABLE uniform_orders ADD COLUMN claimed_at TIMESTAMP")
                    if 'claimed_by_user_id' not in uo_cols:
                        cur.execute("ALTER TABLE uniform_orders ADD COLUMN claimed_by_user_id INTEGER")
                    if 'updated_at' not in uo_cols:
                        cur.execute("ALTER TABLE uniform_orders ADD COLUMN updated_at TIMESTAMP DEFAULT NOW()")
                    conn.commit()

                # Migration for missing columns in inventory_items
                cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'inventory_items'")
                ii_cols = [r[0] for r in cur.fetchall()]
                if ii_cols:
                    if 'size_price_step' not in ii_cols:
                        cur.execute("ALTER TABLE inventory_items ADD COLUMN size_price_step NUMERIC(10,2) DEFAULT 20.00")
                    if 'parent_item_id' not in ii_cols:
                        cur.execute("ALTER TABLE inventory_items ADD COLUMN parent_item_id INTEGER")
                    if 'is_set_piece' not in ii_cols:
                        cur.execute("ALTER TABLE inventory_items ADD COLUMN is_set_piece BOOLEAN DEFAULT FALSE")
                    conn.commit()
            except Exception as e:
                logger.warning(f"Could not create or migrate uniform_orders tables: {e}")
                conn.rollback()

            # ── SHS Elective Enrollment System tables ──

            try:
                # 1. shs_selection_periods – registrar controlled open/close
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS shs_selection_periods (
                        period_id    SERIAL PRIMARY KEY,
                        branch_id    INTEGER NOT NULL REFERENCES branches(branch_id) ON DELETE CASCADE,
                        year_id      INTEGER NOT NULL REFERENCES school_years(year_id) ON DELETE CASCADE,
                        term_name    VARCHAR(50) NOT NULL,
                        status       VARCHAR(20) DEFAULT 'CLOSED',
                        opened_at    TIMESTAMP,
                        closed_at    TIMESTAMP,
                        CONSTRAINT uq_branch_term_selection UNIQUE (branch_id, year_id, term_name)
                    )
                """)
                conn.commit()
            except Exception as e:
                logger.warning(f"Could not create shs_selection_periods table: {e}")
                conn.rollback()

            try:
                # 2. shs_elective_offerings – branch admin managed electives linked to section_teachers
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS shs_elective_offerings (
                        offering_id        SERIAL PRIMARY KEY,
                        branch_id          INTEGER NOT NULL REFERENCES branches(branch_id) ON DELETE CASCADE,
                        year_id            INTEGER NOT NULL REFERENCES school_years(year_id) ON DELETE CASCADE,
                        term_name          VARCHAR(50) NOT NULL,
                        section_teacher_id INTEGER NOT NULL REFERENCES section_teachers(id) ON DELETE CASCADE,
                        group_code         VARCHAR(50) NOT NULL,
                        shs_track          VARCHAR(50) NOT NULL DEFAULT 'Academic',
                        capacity           INTEGER NOT NULL DEFAULT 30,
                        status             VARCHAR(20) DEFAULT 'ACTIVE',
                        created_at         TIMESTAMP DEFAULT NOW(),
                        CONSTRAINT uq_section_teacher_term UNIQUE (section_teacher_id, term_name)
                    )
                """)
                conn.commit()
            except Exception as e:
                logger.warning(f"Could not create shs_elective_offerings table: {e}")
                conn.rollback()

            try:
                # 3. shs_student_elective_requests – student selection submissions
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS shs_student_elective_requests (
                        request_id       SERIAL PRIMARY KEY,
                        enrollment_id    INTEGER NOT NULL REFERENCES enrollments(enrollment_id) ON DELETE CASCADE,
                        student_user_id  INTEGER REFERENCES users(user_id),
                        branch_id        INTEGER NOT NULL,
                        year_id          INTEGER NOT NULL,
                        term_name        VARCHAR(50) NOT NULL,
                        status           VARCHAR(30) DEFAULT 'PENDING',
                        revision_reason  TEXT,
                        submitted_at     TIMESTAMP DEFAULT NOW(),
                        reviewed_by      INTEGER REFERENCES users(user_id),
                        reviewed_at      TIMESTAMP
                    )
                """)
                conn.commit()
            except Exception as e:
                logger.warning(f"Could not create shs_student_elective_requests table: {e}")
                conn.rollback()

            try:
                # 4. shs_student_elective_items – line items per request
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS shs_student_elective_items (
                        item_id      SERIAL PRIMARY KEY,
                        request_id   INTEGER NOT NULL REFERENCES shs_student_elective_requests(request_id) ON DELETE CASCADE,
                        offering_id  INTEGER NOT NULL REFERENCES shs_elective_offerings(offering_id) ON DELETE CASCADE
                    )
                """)
                conn.commit()
            except Exception as e:
                logger.warning(f"Could not create shs_student_elective_items table: {e}")
                conn.rollback()

            try:
                # 5. shs_student_elective_memberships – active class enrollment
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS shs_student_elective_memberships (
                        membership_id    SERIAL PRIMARY KEY,
                        enrollment_id    INTEGER NOT NULL REFERENCES enrollments(enrollment_id) ON DELETE CASCADE,
                        student_user_id  INTEGER REFERENCES users(user_id),
                        offering_id      INTEGER NOT NULL REFERENCES shs_elective_offerings(offering_id) ON DELETE CASCADE,
                        term_name        VARCHAR(50) NOT NULL,
                        year_id          INTEGER NOT NULL REFERENCES school_years(year_id) ON DELETE CASCADE,
                        status           VARCHAR(20) DEFAULT 'ACTIVE',
                        enrolled_at      TIMESTAMP DEFAULT NOW(),
                        dropped_at       TIMESTAMP
                    )
                """)
                conn.commit()
            except Exception as e:
                logger.warning(f"Could not create shs_student_elective_memberships table: {e}")
                conn.rollback()

            # ── Safe ALTER TABLEs for SHS curriculum support ──
            try:
                cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'enrollments'")
                enr_shs = [r[0] for r in cur.fetchall()]
                if 'curriculum_type' not in enr_shs:
                    cur.execute("ALTER TABLE enrollments ADD COLUMN curriculum_type VARCHAR(50) DEFAULT 'basic_ed'")
                if 'shs_track' not in enr_shs:
                    cur.execute("ALTER TABLE enrollments ADD COLUMN shs_track VARCHAR(50)")
                conn.commit()
            except Exception as e:
                logger.warning(f"Could not add SHS columns to enrollments: {e}")
                conn.rollback()

            try:
                cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'subjects'")
                subj_cols = [r[0] for r in cur.fetchall()]
                if subj_cols:
                    if 'subject_type' not in subj_cols:
                        cur.execute("ALTER TABLE subjects ADD COLUMN subject_type VARCHAR(50) DEFAULT 'CORE'")
                    if 'track' not in subj_cols:
                        cur.execute("ALTER TABLE subjects ADD COLUMN track VARCHAR(50)")
                    if 'pathway' not in subj_cols:
                        cur.execute("ALTER TABLE subjects ADD COLUMN pathway VARCHAR(100)")
                    if 'prerequisite_subject_id' not in subj_cols:
                        cur.execute("ALTER TABLE subjects ADD COLUMN prerequisite_subject_id INTEGER REFERENCES public.subjects(subject_id) ON DELETE SET NULL")
                    conn.commit()
            except Exception as e:
                logger.warning(f"Could not add SHS columns to subjects: {e}")
                conn.rollback()

            # ── Migration for shs_pathways table ──
            try:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS public.shs_pathways (
                        pathway_id    SERIAL PRIMARY KEY,
                        branch_id     INTEGER NOT NULL REFERENCES public.branches(branch_id) ON DELETE CASCADE,
                        track_name    VARCHAR(100) NOT NULL,
                        pathway_name  VARCHAR(200) NOT NULL,
                        description   TEXT,
                        is_active     BOOLEAN DEFAULT TRUE,
                        display_order INTEGER DEFAULT 0,
                        created_at    TIMESTAMP DEFAULT NOW(),
                        CONSTRAINT uq_branch_track_pathway UNIQUE (branch_id, track_name, pathway_name)
                    )
                """)
                cur.execute("CREATE INDEX IF NOT EXISTS idx_shs_pathways_branch ON public.shs_pathways (branch_id)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_shs_pathways_active ON public.shs_pathways (branch_id, is_active)")
                conn.commit()
            except Exception as e:
                logger.warning(f"Could not create shs_pathways table: {e}")
                conn.rollback()

            try:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS public.audit_logs (
                        log_id      SERIAL PRIMARY KEY,
                        user_id     INTEGER,
                        user_name   VARCHAR(150),
                        role        VARCHAR(50),
                        branch_id   INTEGER,
                        action      VARCHAR(100) NOT NULL,
                        details     TEXT,
                        ip_address  VARCHAR(50),
                        created_at  TIMESTAMP DEFAULT NOW()
                    )
                """)
                cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON public.audit_logs (action)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_created ON public.audit_logs (created_at DESC)")
                conn.commit()
            except Exception as e:
                logger.warning(f"Could not create audit_logs table: {e}")
                conn.rollback()

            try:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS public.system_settings (
                        setting_key   VARCHAR(100) PRIMARY KEY,
                        setting_value TEXT,
                        updated_at    TIMESTAMP DEFAULT NOW()
                    )
                """)
                cur.execute("""
                    INSERT INTO public.system_settings (setting_key, setting_value)
                    VALUES ('maintenance_mode', 'off')
                    ON CONFLICT (setting_key) DO NOTHING
                """)
                conn.commit()
            except Exception as e:
                logger.warning(f"Could not create system_settings table: {e}")
                conn.rollback()

            try:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS public.failed_logins (
                        id         SERIAL PRIMARY KEY,
                        ip_address VARCHAR(50),
                        username   VARCHAR(150),
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                """)
                cur.execute("CREATE INDEX IF NOT EXISTS idx_failed_logins_ip ON public.failed_logins (ip_address, created_at DESC)")
                conn.commit()
            except Exception as e:
                logger.warning(f"Could not create failed_logins table: {e}")
                conn.rollback()

            try:
                cur.execute("UPDATE users SET full_name = 'Super Admin' WHERE role = 'super_admin' AND (full_name IS NULL OR full_name = '')")
                conn.commit()
            except Exception as e:
                logger.warning(f"Could not update super admin full_name: {e}")
                conn.rollback()

            # ── SWAFO: is_swafo flag on users ──
            try:
                cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'users'")
                usr_cols = [r[0] for r in cur.fetchall()]
                if 'is_swafo' not in usr_cols:
                    cur.execute("ALTER TABLE users ADD COLUMN is_swafo BOOLEAN DEFAULT FALSE")
                if 'is_dc' not in usr_cols:
                    cur.execute("ALTER TABLE users ADD COLUMN is_dc BOOLEAN DEFAULT FALSE")
                conn.commit()
            except Exception as e:
                logger.warning(f"Could not add is_swafo to users: {e}")
                conn.rollback()

            # ── SWAFO: swafo_records table (student cumulative records) ──
            try:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS swafo_records (
                        record_id           SERIAL PRIMARY KEY,
                        enrollment_id       INTEGER NOT NULL REFERENCES enrollments(enrollment_id) ON DELETE CASCADE,
                        branch_id           INTEGER NOT NULL,
                        -- I. Family Background
                        family_members      JSONB DEFAULT '[]',
                        kamag_anak          TEXT,
                        may_sariling_silid  VARCHAR(10),
                        kasama_sa_silid     TEXT,
                        uri_ng_kabuhayan    VARCHAR(50),
                        natutulog_sa_bahay  VARCHAR(10),
                        naranasan_maglayas  VARCHAR(10),
                        dahilan_maglayas    TEXT,
                        -- II. Kalusugan
                        piskal_na_kapansanan TEXT,
                        malinaw_mata        VARCHAR(10),
                        maayos_pandinig     VARCHAR(10),
                        naiban_sakit        VARCHAR(10),
                        karamdaman          TEXT,
                        -- III. Edukasyon
                        education_history   JSONB DEFAULT '[]',
                        kalagayan_pag_aaral VARCHAR(50),
                        kung_napatigil      TEXT,
                        umakyat_antas       VARCHAR(10),
                        kung_opo_antas       TEXT,
                        -- IV. Relihiyon
                        may_binyag          VARCHAR(10),
                        parokya_binyag      TEXT,
                        may_kumpil          VARCHAR(10),
                        parokya_kumpil      TEXT,
                        relihiyon           TEXT,
                        kasali_samahan      VARCHAR(10),
                        uri_samahan         TEXT,
                        nakapag_kumpisal    VARCHAR(10),
                        nakatanggap_komunyon VARCHAR(10),
                        -- V. Summer Subjects
                        summer_subjects     JSONB DEFAULT '[]',
                        pinakagusto_subject TEXT,
                        inaayawan_subject   TEXT,
                        -- VI. Bokasyon/Kurso
                        bokasyon_kurso      TEXT,
                        kaninong_kagustuhan TEXT,
                        sarili_description  TEXT,
                        -- Meta
                        status              VARCHAR(20) DEFAULT 'draft',
                        teacher_notes       TEXT,
                        reviewed_by         INTEGER REFERENCES users(user_id),
                        reviewed_at         TIMESTAMP,
                        submitted_at        TIMESTAMP,
                        created_at          TIMESTAMP DEFAULT NOW(),
                        updated_at          TIMESTAMP DEFAULT NOW(),
                        UNIQUE (enrollment_id)
                    )
                """)
                cur.execute("CREATE INDEX IF NOT EXISTS idx_swafo_records_branch ON swafo_records (branch_id)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_swafo_records_status ON swafo_records (status)")
                conn.commit()
            except Exception as e:
                logger.warning(f"Could not create swafo_records table: {e}")
                conn.rollback()

            # ── SWAFO: swafo_discipline_log table ──
            try:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS swafo_discipline_log (
                        log_id          SERIAL PRIMARY KEY,
                        enrollment_id   INTEGER NOT NULL REFERENCES enrollments(enrollment_id) ON DELETE CASCADE,
                        branch_id       INTEGER NOT NULL,
                        logged_by       INTEGER NOT NULL REFERENCES users(user_id),
                        incident_date   DATE NOT NULL,
                        incident_type   VARCHAR(100),
                        description     TEXT NOT NULL,
                        action_taken    TEXT,
                        severity        VARCHAR(20) DEFAULT 'minor',
                        created_at      TIMESTAMP DEFAULT NOW()
                    )
                """)
                cur.execute("CREATE INDEX IF NOT EXISTS idx_swafo_discipline_enrollment ON swafo_discipline_log (enrollment_id)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_swafo_discipline_branch ON swafo_discipline_log (branch_id)")
                conn.commit()
            except Exception as e:
                logger.warning(f"Could not create swafo_discipline_log table: {e}")
                conn.rollback()

            # Commit successful things
            conn.commit()
            cur.close()
            _MIGRATIONS_RUN = True

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


def get_break_times_config(branch_id=None):
    """
    Retrieves customized break and prayer times config from system_settings table.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        key = f"break_times_config_{branch_id}" if branch_id else "liceo_break_times_config"
        cur.execute("SELECT setting_value FROM system_settings WHERE setting_key = %s", (key,))
        row = cur.fetchone()
        if not row and branch_id:
            cur.execute("SELECT setting_value FROM system_settings WHERE setting_key = 'liceo_break_times_config'")
            row = cur.fetchone()
        if row and row[0]:
            return json.loads(row[0])
    except Exception as e:
        logger.warning(f"Could not load break_times_config: {e}")
    finally:
        try:
            cur.close()
        except Exception:
            pass
        conn.close()
    return None


def save_break_times_config(config_dict, branch_id=None):
    """
    Saves customized break and prayer times config into system_settings table.
    """
    if not isinstance(config_dict, dict):
        return False
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        key = f"break_times_config_{branch_id}" if branch_id else "liceo_break_times_config"
        val_str = json.dumps(config_dict)
        cur.execute("""
            INSERT INTO system_settings (setting_key, setting_value, updated_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (setting_key) DO UPDATE
            SET setting_value = EXCLUDED.setting_value,
                updated_at = NOW()
        """, (key, val_str))
        
        if branch_id:
            cur.execute("""
                INSERT INTO system_settings (setting_key, setting_value, updated_at)
                VALUES ('liceo_break_times_config', %s, NOW())
                ON CONFLICT (setting_key) DO UPDATE
                SET setting_value = EXCLUDED.setting_value,
                    updated_at = NOW()
            """, (val_str,))
            
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        logger.error(f"Error saving break_times_config: {e}")
        return False
    finally:
        try:
            cur.close()
        except Exception:
            pass
        conn.close()


def merge_user_accounts(primary_id, secondary_id):
    """
    Merges a secondary user account into a primary user account.
    Transfers linked parent students, notifications, teacher assignments, and merges user_roles.
    Deletes the secondary user account after re-linking child records.
    Returns (success, message).
    """
    if primary_id == secondary_id:
        return False, "Primary and secondary accounts must be different."

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("SELECT * FROM users WHERE user_id = %s", (primary_id,))
        p_user = cur.fetchone()
        cur.execute("SELECT * FROM users WHERE user_id = %s", (secondary_id,))
        s_user = cur.fetchone()

        if not p_user or not s_user:
            return False, "One or both user accounts do not exist."

        # Parse primary roles
        try:
            p_roles = json.loads(p_user["user_roles"]) if p_user.get("user_roles") else ([p_user["role"]] if p_user.get("role") else [])
        except Exception:
            p_roles = [p_user["role"]] if p_user.get("role") else []

        # Parse secondary roles
        try:
            s_roles = json.loads(s_user["user_roles"]) if s_user.get("user_roles") else ([s_user["role"]] if s_user.get("role") else [])
        except Exception:
            s_roles = [s_user["role"]] if s_user.get("role") else []

        # Merge unique roles
        merged_roles = list(dict.fromkeys(p_roles + s_roles))

        # Re-link parent_student
        cur.execute("""
            UPDATE parent_student 
            SET parent_id = %s 
            WHERE parent_id = %s 
              AND student_id NOT IN (SELECT student_id FROM parent_student WHERE parent_id = %s)
        """, (primary_id, secondary_id, primary_id))
        cur.execute("DELETE FROM parent_student WHERE parent_id = %s", (secondary_id,))

        # Re-link parent_notifications if table exists
        try:
            cur.execute("UPDATE parent_notifications SET parent_id = %s WHERE parent_id = %s", (primary_id, secondary_id))
        except Exception:
            conn.rollback()
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Re-link teacher tables if applicable
        teacher_tables = [("section_teachers", "teacher_id"), ("teacher_sections", "teacher_id"), ("subject_loads", "teacher_id"), ("attendance_scores", "teacher_id")]
        for tbl, col in teacher_tables:
            try:
                cur.execute(f"UPDATE {tbl} SET {col} = %s WHERE {col} = %s", (primary_id, secondary_id))
            except Exception:
                conn.rollback()
                cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Sync missing email or names if primary user is missing them
        email_to_set = p_user.get("email") or s_user.get("email")
        fname_to_set = p_user.get("first_name") or s_user.get("first_name")
        mname_to_set = p_user.get("middle_name") or s_user.get("middle_name")
        lname_to_set = p_user.get("last_name") or s_user.get("last_name")
        fullname_to_set = p_user.get("full_name") or s_user.get("full_name")

        cur.execute("""
            UPDATE users
            SET user_roles = %s,
                email = %s,
                first_name = %s,
                middle_name = %s,
                last_name = %s,
                full_name = %s
            WHERE user_id = %s
        """, (json.dumps(merged_roles), email_to_set, fname_to_set, mname_to_set, lname_to_set, fullname_to_set, primary_id))

        # Delete secondary user account
        cur.execute("DELETE FROM users WHERE user_id = %s", (secondary_id,))

        conn.commit()
        return True, f"Successfully merged account '{s_user.get('username')}' into '{p_user.get('username')}'."
    except Exception as e:
        conn.rollback()
        return False, f"Failed to merge user accounts: {str(e)}"
    finally:
        cur.close()
        conn.close()