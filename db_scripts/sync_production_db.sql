-- ============================================================
-- LICEO_A Production Sync Script (Railway)
-- Run this in Railway: Postgres → Database → Query tab
-- This script fixes missing columns and tables without deleting data.
-- ============================================================

-- 1. Fix 'sections' table
DO $$ 
BEGIN 
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='sections' AND column_name='id') THEN
        ALTER TABLE sections RENAME COLUMN id TO section_id;
    END IF;
END $$;

ALTER TABLE sections ADD COLUMN IF NOT EXISTS grade_level_id INTEGER;
ALTER TABLE sections ADD COLUMN IF NOT EXISTS capacity INTEGER DEFAULT 50;
ALTER TABLE sections ADD COLUMN IF NOT EXISTS year_id INTEGER;
ALTER TABLE sections ADD COLUMN IF NOT EXISTS teacher_id INTEGER;

-- 2. Fix 'grade_levels' table
ALTER TABLE grade_levels ADD COLUMN IF NOT EXISTS branch_id INTEGER;

-- 3. Fix 'users' table
ALTER TABLE users ADD COLUMN IF NOT EXISTS full_name VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS gender VARCHAR(20);
ALTER TABLE users ADD COLUMN IF NOT EXISTS email VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS contact_number VARCHAR(20);
ALTER TABLE users ADD COLUMN IF NOT EXISTS dob DATE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS profile_image VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS enrollment_id INTEGER;
ALTER TABLE users ADD COLUMN IF NOT EXISTS grade_level_id INTEGER;
ALTER TABLE users ADD COLUMN IF NOT EXISTS grade_level VARCHAR(50);

-- 4. Create missing tables (Academic Management)
CREATE TABLE IF NOT EXISTS public.subjects (
    subject_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    branch_id INTEGER,
    deped_category VARCHAR(100),
    UNIQUE(name)
);

CREATE TABLE IF NOT EXISTS public.section_teachers (
    id SERIAL PRIMARY KEY,
    section_id INTEGER NOT NULL REFERENCES sections(section_id) ON DELETE CASCADE,
    teacher_id INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
    subject_id INTEGER NOT NULL REFERENCES subjects(subject_id) ON DELETE CASCADE,
    year_id INTEGER,
    is_archived BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS public.exams (
    exam_id SERIAL PRIMARY KEY,
    branch_id INTEGER,
    section_id INTEGER,
    subject_id INTEGER,
    teacher_id INTEGER,
    title VARCHAR(255),
    exam_type VARCHAR(50),
    duration_mins INTEGER,
    scheduled_date DATE,
    status VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    question_limit INTEGER,
    scheduled_start TIMESTAMP,
    scheduled_end TIMESTAMP,
    max_attempts INTEGER DEFAULT 1,
    passing_score INTEGER,
    instructions TEXT,
    randomize BOOLEAN DEFAULT FALSE,
    grading_period VARCHAR(50),
    is_visible BOOLEAN DEFAULT FALSE,
    batch_id VARCHAR(20),
    year_id INTEGER,
    is_archived BOOLEAN DEFAULT FALSE,
    class_mode VARCHAR(20) DEFAULT 'Virtual'
);

CREATE TABLE IF NOT EXISTS public.exam_results (
    result_id SERIAL PRIMARY KEY,
    exam_id INTEGER REFERENCES exams(exam_id) ON DELETE CASCADE,
    enrollment_id INTEGER,
    score INTEGER,
    total_points INTEGER,
    submitted_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    status VARCHAR(50),
    tab_switches INTEGER DEFAULT 0,
    year_id INTEGER
);

CREATE TABLE IF NOT EXISTS public.activities (
    activity_id SERIAL PRIMARY KEY,
    branch_id INTEGER,
    section_id INTEGER,
    subject_id INTEGER,
    teacher_id INTEGER,
    title VARCHAR(255),
    category VARCHAR(50),
    instructions TEXT,
    max_score INTEGER,
    due_date TIMESTAMP,
    allow_resubmission BOOLEAN DEFAULT FALSE,
    allowed_file_types TEXT,
    attachment_path TEXT,
    status VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP,
    grading_period VARCHAR(50),
    batch_id VARCHAR(20),
    year_id INTEGER,
    is_archived BOOLEAN DEFAULT FALSE,
    youtube_link TEXT
);

CREATE TABLE IF NOT EXISTS public.activity_submissions (
    submission_id SERIAL PRIMARY KEY,
    activity_id INTEGER REFERENCES activities(activity_id) ON DELETE CASCADE,
    student_id INTEGER,
    enrollment_id INTEGER,
    file_path TEXT,
    original_filename VARCHAR(255),
    submitted_at TIMESTAMP DEFAULT NOW(),
    is_late BOOLEAN DEFAULT FALSE,
    attempt_no INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    status VARCHAR(50),
    feedback TEXT,
    graded_at TIMESTAMP,
    graded_by INTEGER,
    allow_resubmit BOOLEAN DEFAULT FALSE,
    year_id INTEGER,
    viewed_at TIMESTAMP,
    attachments JSONB,
    is_viewed BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS public.attendance_scores (
    id SERIAL PRIMARY KEY,
    teacher_id INTEGER,
    enrollment_id INTEGER,
    section_id INTEGER,
    subject_id INTEGER,
    grading_period VARCHAR(50),
    score INTEGER,
    year_id INTEGER,
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT uq_attendance UNIQUE (enrollment_id, section_id, subject_id, grading_period)
);

CREATE TABLE IF NOT EXISTS public.posted_grades (
    id SERIAL PRIMARY KEY,
    enrollment_id INTEGER,
    section_id INTEGER,
    subject_id INTEGER,
    grading_period VARCHAR(50),
    score NUMERIC(5,2),
    is_finalized BOOLEAN DEFAULT FALSE,
    year_id INTEGER,
    UNIQUE (enrollment_id, subject_id, grading_period, year_id)
);

-- 5. Fix 'enrollments' table (Missing columns from analysis)
ALTER TABLE enrollments ADD COLUMN IF NOT EXISTS year_id INTEGER;
ALTER TABLE enrollments ADD COLUMN IF NOT EXISTS lrn VARCHAR(12);
ALTER TABLE enrollments ADD COLUMN IF NOT EXISTS father_name VARCHAR(255);
ALTER TABLE enrollments ADD COLUMN IF NOT EXISTS mother_name VARCHAR(255);
ALTER TABLE enrollments ADD COLUMN IF NOT EXISTS enroll_type VARCHAR(255);
ALTER TABLE enrollments ADD COLUMN IF NOT EXISTS enroll_date DATE;
ALTER TABLE enrollments ADD COLUMN IF NOT EXISTS birthplace VARCHAR(255);
ALTER TABLE enrollments ADD COLUMN IF NOT EXISTS remarks TEXT;
ALTER TABLE enrollments ADD COLUMN IF NOT EXISTS father_contact VARCHAR(255);
ALTER TABLE enrollments ADD COLUMN IF NOT EXISTS mother_contact VARCHAR(255);
ALTER TABLE enrollments ADD COLUMN IF NOT EXISTS father_occupation VARCHAR(255);
ALTER TABLE enrollments ADD COLUMN IF NOT EXISTS mother_occupation VARCHAR(255);
ALTER TABLE enrollments ADD COLUMN IF NOT EXISTS rejection_reason TEXT;
ALTER TABLE enrollments ADD COLUMN IF NOT EXISTS rejected_at TIMESTAMP;
ALTER TABLE enrollments ADD COLUMN IF NOT EXISTS academic_status VARCHAR(50);
ALTER TABLE enrollments ADD COLUMN IF NOT EXISTS profile_image VARCHAR(255);

-- 6. Ensure sequences are correct (if any were manually created without SERIAL)
-- This is just a safety measure.
