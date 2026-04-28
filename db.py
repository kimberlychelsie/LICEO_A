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

            # ── Inventory Items image_url migration ──
            try:
                cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'inventory_items'")
                inv_cols = [r[0] for r in cur.fetchall()]
                if 'image_url' not in inv_cols:
                    cur.execute("ALTER TABLE inventory_items ADD COLUMN image_url TEXT")
                
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
                
                # ── SEEDING: If a branch has NO inventory, seed the default uniforms ──
                cur.execute("SELECT branch_id FROM branches")
                branches = [r[0] for r in cur.fetchall()]
                
                for b_id in branches:
                    cur.execute("SELECT COUNT(*) FROM inventory_items WHERE branch_id = %s", (b_id,))
                    if cur.fetchone()[0] == 0:
                        logger.info(f"Seeding default inventory for branch {b_id}")
                        for item_name, img_path in uniform_images.items():
                            cur.execute("""
                                INSERT INTO inventory_items (branch_id, category, item_name, price, stock_total, reserved_qty, image_url, is_active)
                                VALUES (%s, 'UNIFORM', %s, 550.00, 600, 0, %s, TRUE)
                                RETURNING item_id
                            """, (b_id, item_name, img_path))
                            new_item_id = cur.fetchone()[0]
                            
                            # Add default sizes for the seeded item (100 stock per size)
                            for sz in ["XS", "S", "M", "L", "XL", "XXL"]:
                                cur.execute("""
                                    INSERT INTO inventory_item_sizes (item_id, size_label, stock_total, reserved_qty)
                                    VALUES (%s, %s, 100, 0)
                                """, (new_item_id, sz))

                    # ── SEEDING: Books (If branch has no books) ──
                    cur.execute("SELECT COUNT(*) FROM inventory_items WHERE branch_id = %s AND category = 'BOOK'", (b_id,))
                    if cur.fetchone()[0] == 0:
                        logger.info(f"Seeding textbook inventory for branch {b_id}")
                        BOOKS_DATA = """Nursery,FNB,Religion,323.00
Nursery,JO-ES,Filipino- Binhi:Pinagyamang Edisyon,535.00
Nursery,NEO-ASIA,English-Phonics,460.00
Nursery,JO-ES,Math- Math Builders,650.00
Nursery,NEO-ASIA,AP- Getting Ready Series "Sibika at Kultura" K1,460.00
Nursery,JO-ES,Science- Exploring Science Kinder,619.00
Nursery,SIBS,ESP- Mabuting Bata Magandang Pag-uugali,335.00
Kindergarten,N/A,Religion,580.00
Kindergarten,ABIVA,MAKABANSA(AP)-Serye ng Hakbang sa Pag-unlad,435.00
Kindergarten,The Library,LANGUAGE/READING/WRITING-Smart Language K1,430.00
Kindergarten,N/A,Learn Ahead in Reading K1,435.00
Kindergarten,N/A,Basic Writing for Early Learners(K),450.00
Kindergarten,ABIVA,SCIENCE-Ladders to Learning Series K,435.00
Kindergarten,The Library,MATHEMATICS-Global Mathematics K,445.00
Kindergarten,ABIVA,GMRC-Hakbang sa Kabutihang Asal K1,380.00
Grade 1,PHOENIX,Religion-MAPSA BSTSC: I Believe in Jesus 1,620.00
Grade 1,PHOENIX,Language- Integrated English for Effective Com.-3rd Ed,440.00
Grade 1,PHOENIX,Reading and Literacy-Integrated Eng.for Effective Com.3rdEd,460.00
Grade 1,PHOENIX,Mathematics-Realistic Math,890.00
Grade 1,REX,MAKABANSA- Lahing Pilipino(Unang Edisyon),779.00
Grade 1,JO-ES,GMRC- Tanglaw sa kagandahang Asal at Wastong Pag-uugali,560.00
Grade 1,Book Choice,ICT-CYBERWORLD I.T. ESSENTIALS Getting to Know My Computer,540.00
Grade 1,ABIVA,SRA,390.00
Grade 2,PHOENIX,Religion-MAPSA BSTSC: I Grow in Jesus 2,620.00
Grade 2,DIWA,Filipino-Wikang Filipino sa Mabisang Kom.,785.00
Grade 2,PHOENIX,English- Integrated English for Effective Com.,670.00
Grade 2,PHOENIX,Math- Realistic MathBasic Beyond Breakthrough,905.00
Grade 2,REX,Makabansa- Lahing Pilipino Kaagapay sa Ika-21 Siglo,779.00
Grade 2,JO-ES,GMRC- Tanglaw sa Kagandahang Asal at Wastong Pag-uugali,560.00
Grade 2,Book Choice,ICT- Global Tech Computer Series-Intro.to Comp.,540.00
Grade 3,PHOENIX,Religion-MAPSA BSTSC: I Celebrate Jesus 3,620.00
Grade 3,DIWA,Filipino-Wikang Filipino sa Mabisang Kom.,785.00
Grade 3,PHOENIX,English- Integrated English for Effective Com.,670.00
Grade 3,PHOENIX,Math-Realistic MathBasic Beyond Breakthrough,910.00
Grade 3,REX,Makabansa-Lahing Pilipino Kaagapay sa Ika-21 Siglo,779.00
Grade 3,JO-ES,GMRC- Tanglaw sa Kagandahang Asal at Wastong Pag-uugali,610.00
Grade 3,REX,Science- Science Links,779.00
Grade 3,Book Choice,ICT- Global Tech Computer Series 3/ Computer 101,540.00
Grade 4,PHOENIX,Religion-MAPSA BSTSC: Jesus Sends Me...4,640.00
Grade 4,DIWA,Filipino-Wikang Filipino sa Mabisang Kom.,785.00
Grade 4,PHOENIX,English-Integrated English for Effective Communication,670.00
Grade 4,PHOENIX,Realistic Math,875.00
Grade 4,REX,AP-Lahing Pilipino Kaagapay sa Ika-21 Siglo,779.00
Grade 4,REX,MAPEH- Expeditions in MAPEH,679.00
Grade 4,JO-ES,GMRC-Tanglaw sa kagandahang Asal at Wastong Pag-uugali,560.00
Grade 4,Book Choice,ICT-Global Tech Computer Series MS Office Application,540.00
Grade 4,REX,Science Links (Balatbat),779.00
Grade 4,FnB,EPP-Tagumpay,573.00
Grade 5,PHOENIX,Religion-MAPSA BSTSC:Jesus Sends Me...5,640.00
Grade 5,DIWA,Filipino-Wikang Filipino sa Mabisang Kom.,785.00
Grade 5,PHOENIX,English-Integrated English for Effective Communication,670.00
Grade 5,PHOENIX,Realistic Math,875.00
Grade 5,REX,AP-Lahing Pilipino Kaagapay sa Ika-21 Siglo,779.00
Grade 5,REX,MAPEH- Expeditions in MAPEH,679.00
Grade 5,JO-ES,GMRC-Tanglaw sa kagandahang Asal at Wastong Pag-uugali,560.00
Grade 5,Book Choice,ICT-Global Tech Computer Series 5 Computer Application,540.00
Grade 5,REX,Science Links (Balatbat),779.00
Grade 5,FnB,EPP-Tagumpay,573.00
Grade 6,FNB,Religion-Christian Life Education Series 4th Ed.,600.00
Grade 6,SIBS,Filipino- Pintig ng Lahing Pilipino Ikalawang Edisyon,755.00
Grade 6,REX,English-Essential English for Active Learners 2020,629.00
Grade 6,PHOENIX-SIBS,Math Buddies,570.00
Grade 6,ABIVA,AP- Kamalayang Panlipunan,635.00
Grade 6,EPHESIANS,MAPEH- The Joy of MAPEH,670.00
Grade 6,JO-ES,ESP- Dakilang Pag-asa,380.00
Grade 6,Book Choice,ICT-CYBERWORLD I.T. ESSENTIALS Computer Knowledge,540.00
Grade 6,TECHFACTOR,Science-Science Tek Inquiry-based Approach,750.00
Grade 6,FNB,EPP- Tagumpay,605.00
Grade 7,PHOENIX,Religion-MAPSA CLE-BTSC: Jesus Announces God...7,620.00
Grade 7,DIWA,Filipino- Filipino sa Modernong Panahon,885.00
Grade 7,PHOENIX,English-English Communication Arts & Skills,505.00
Grade 7,PHOENIX,Mathematics- Realistic Math,580.00
Grade 7,REX,AP-Kayamanan - Pilipinas sa Timog Silangang Asya,749.00
Grade 7,REX,MAPEH- Expeditions in MAPEH,699.00
Grade 7,EPHESIANS,Values Education-Marangal,600.00
Grade 7,SPDCSS,ICT- Module,0.00
Grade 7,REX,Science Links,799.00
Grade 7,PISARA,TLE,680.00
Grade 8,PHOENIX,Religion-MAPSA CLE-BTSC: Jesus Conveys God...8,640.00
Grade 8,DIWA,Filipino- Filipino sa Modernong Panahon,885.00
Grade 8,PHOENIX,English-English Communication Arts & Skills (ECAS),530.00
Grade 8,PHOENIX,Mathematics- Realistic Math,725.00
Grade 8,REX,AP-Kayamanan - Ang Asya at Daigdig,749.00
Grade 8,REX,MAPEH- Expeditions in MAPEH,699.00
Grade 8,EPHESIANS,Values Education-Marangal-Edukasyon sa Pagpapakatao,600.00
Grade 8,REX,ICT- D-Whiz in ICT Skills Dev't.,599.00
Grade 8,REX,Science-Science Links,799.00
Grade 8,PISARA,TLE-TLE 8 Building Foundations,870.00
Grade 9,Vicarish,Religion-Christian Living: Sent Forth,630.00
Grade 9,REX,Filipino- Punla: Mga Akdang Panitikan,709.00
Grade 9,ABIVA,English-English in Perspective,705.00
Grade 9,DIWA,Math-Mathematics for Innovative Minds,885.00
Grade 9,Brilliant,AP- Ugnayan at Kaunlaran 9:Ekonomiks,610.00
Grade 9,Vibal,MAPEH- Living with Music Art Physical and Health,750.00
Grade 9,EPHESIANS,ESP- Marangal,555.00
Grade 9,REX,ICT- D-Whiz /PROSKILLS,657.00
Grade 9,REX,Science- Science Links,729.00
Grade 9,Inteligente,TLE- SPICE Book 1,510.00
Grade 10,Vicarish,Religion-Christian Living: Evangelizers,595.00
Grade 10,REX,Filipino- Punla: Mga Akdang Panitikan,709.00
Grade 10,ABIVA,English-English in Perspective,705.00
Grade 10,DIWA,Math-Mathematics for Innovative Minds,885.00
Grade 10,Brilliant,AP- Ugnayan at Kaunlaran 10:Isyu ng Lipunan,610.00
Grade 10,Vibal,MAPEH- Living with Music Art Physical and Health,750.00
Grade 10,EPHESIANS,ESP- Marangal,555.00
Grade 10,REX,ICT- D-Whiz/ PROSKILLS,599.00
Grade 10,REX,Science- Science Links,729.00
Grade 10,Inteligente,TLE- SPICE Book 2,540.00"""
                        
                        for line in BOOKS_DATA.split('\n'):
                            if not line.strip(): continue
                            parts = line.split(',')
                            if len(parts) < 4: continue
                            level = parts[0].strip()
                            if level == "Kindergarten": level = "Kinder"
                            pub = parts[1].strip()
                            title = parts[2].strip()
                            price = float(parts[3].strip())
                            full_name = f"[{pub}] {title}"
                            
                            cur.execute("""
                                INSERT INTO inventory_items (branch_id, category, item_name, grade_level, price, stock_total, reserved_qty, is_active, is_common)
                                VALUES (%s, 'BOOK', %s, %s, %s, 100, 0, TRUE, FALSE)
                            """, (b_id, full_name, level, price))
                    else:
                        # ── UPDATE: Force existing books to 100 stock and cleanup sizes ──
                        cur.execute("""
                            UPDATE inventory_items 
                            SET stock_total = 100 
                            WHERE branch_id = %s AND category = 'BOOK'
                        """, (b_id,))
                        
                        # Books should NOT have entries in inventory_item_sizes
                        cur.execute("""
                            DELETE FROM inventory_item_sizes 
                            WHERE item_id IN (SELECT item_id FROM inventory_items WHERE branch_id = %s AND category = 'BOOK')
                        """, (b_id,))
                
                conn.commit()
            except Exception as e:
                logger.warning(f"Could not migrate inventory_items image_url: {e}")
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
                conn.commit()
            except Exception as e:
                logger.warning(f"Could not migrate financial tables: {e}")
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