-- ============================================================
-- SHS Elective Enrollment System Migration (Simplified)
-- SAFE: All statements are idempotent (IF NOT EXISTS / IF NOT)
-- ============================================================

-- 1. SHS Selection Periods (Registrar Controlled, calendar-term mapped)
CREATE TABLE IF NOT EXISTS public.shs_selection_periods (
    period_id    SERIAL PRIMARY KEY,
    branch_id    INTEGER NOT NULL REFERENCES public.branches(branch_id) ON DELETE CASCADE,
    year_id      INTEGER NOT NULL REFERENCES public.school_years(year_id) ON DELETE CASCADE,
    term_name    VARCHAR(50) NOT NULL,
    status       VARCHAR(20) DEFAULT 'CLOSED',
    opened_at    TIMESTAMP,
    closed_at    TIMESTAMP,
    CONSTRAINT uq_branch_year_term_name UNIQUE (branch_id, year_id, term_name)
);

-- 2. SHS Elective Offerings (Branch Admin Managed, maps section-teacher assignments)
CREATE TABLE IF NOT EXISTS public.shs_elective_offerings (
    offering_id        SERIAL PRIMARY KEY,
    branch_id          INTEGER NOT NULL REFERENCES public.branches(branch_id) ON DELETE CASCADE,
    year_id            INTEGER NOT NULL REFERENCES public.school_years(year_id) ON DELETE CASCADE,
    term_name          VARCHAR(50) NOT NULL,
    section_teacher_id INTEGER NOT NULL REFERENCES public.section_teachers(id) ON DELETE CASCADE,
    group_code         VARCHAR(50) NOT NULL,
    shs_track          VARCHAR(50) NOT NULL DEFAULT 'Academic',
    capacity           INTEGER NOT NULL DEFAULT 30,
    status             VARCHAR(20) DEFAULT 'ACTIVE',
    created_at         TIMESTAMP DEFAULT NOW(),
    CONSTRAINT uq_section_teacher_term UNIQUE (section_teacher_id, term_name)
);

-- 3. SHS Student Elective Requests
CREATE TABLE IF NOT EXISTS public.shs_student_elective_requests (
    request_id       SERIAL PRIMARY KEY,
    enrollment_id    INTEGER NOT NULL REFERENCES public.enrollments(enrollment_id) ON DELETE CASCADE,
    student_user_id  INTEGER REFERENCES public.users(user_id) ON DELETE SET NULL,
    branch_id        INTEGER NOT NULL REFERENCES public.branches(branch_id) ON DELETE CASCADE,
    year_id          INTEGER NOT NULL REFERENCES public.school_years(year_id) ON DELETE CASCADE,
    term_name        VARCHAR(50) NOT NULL,
    status           VARCHAR(30) DEFAULT 'PENDING',
    revision_reason  TEXT,
    submitted_at     TIMESTAMP DEFAULT NOW(),
    reviewed_by      INTEGER REFERENCES public.users(user_id) ON DELETE SET NULL,
    reviewed_at      TIMESTAMP
);

-- 4. SHS Student Elective Items (Line items per request)
CREATE TABLE IF NOT EXISTS public.shs_student_elective_items (
    item_id      SERIAL PRIMARY KEY,
    request_id   INTEGER NOT NULL REFERENCES public.shs_student_elective_requests(request_id) ON DELETE CASCADE,
    offering_id  INTEGER NOT NULL REFERENCES public.shs_elective_offerings(offering_id) ON DELETE CASCADE
);

-- 5. SHS Student Elective Memberships (Active class enrollment)
CREATE TABLE IF NOT EXISTS public.shs_student_elective_memberships (
    membership_id    SERIAL PRIMARY KEY,
    enrollment_id    INTEGER NOT NULL REFERENCES public.enrollments(enrollment_id) ON DELETE CASCADE,
    student_user_id  INTEGER REFERENCES public.users(user_id) ON DELETE SET NULL,
    offering_id      INTEGER NOT NULL REFERENCES public.shs_elective_offerings(offering_id) ON DELETE CASCADE,
    term_name        VARCHAR(50) NOT NULL,
    year_id          INTEGER NOT NULL REFERENCES public.school_years(year_id) ON DELETE CASCADE,
    status           VARCHAR(20) DEFAULT 'ACTIVE',
    enrolled_at      TIMESTAMP DEFAULT NOW(),
    dropped_at       TIMESTAMP
);

-- ── Safe Column Additions ──
ALTER TABLE public.enrollments ADD COLUMN IF NOT EXISTS curriculum_type VARCHAR(50) DEFAULT 'basic_ed';
ALTER TABLE public.enrollments ADD COLUMN IF NOT EXISTS shs_track VARCHAR(50);
ALTER TABLE public.subjects ADD COLUMN IF NOT EXISTS subject_type VARCHAR(50) DEFAULT 'CORE';
ALTER TABLE public.subjects ADD COLUMN IF NOT EXISTS track VARCHAR(50);
ALTER TABLE public.subjects ADD COLUMN IF NOT EXISTS pathway VARCHAR(100);

-- ── Indexes for Performance ──
CREATE INDEX IF NOT EXISTS idx_shs_offerings_branch ON public.shs_elective_offerings (branch_id);
CREATE INDEX IF NOT EXISTS idx_shs_memberships_enrollment ON public.shs_student_elective_memberships (enrollment_id);
CREATE INDEX IF NOT EXISTS idx_shs_memberships_offering ON public.shs_student_elective_memberships (offering_id);
CREATE INDEX IF NOT EXISTS idx_shs_requests_enrollment ON public.shs_student_elective_requests (enrollment_id);

DO $$
BEGIN
    RAISE NOTICE 'SHS Elective Enrollment System simplified tables, columns, and indexes created successfully.';
END $$;
