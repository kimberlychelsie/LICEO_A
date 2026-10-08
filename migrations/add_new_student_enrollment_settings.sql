-- ============================================================
-- New Student Enrollment Settings
-- SAFE: Idempotent schema foundation only. No enrollment window
-- is opened by this migration; missing rows must be treated as
-- CLOSED by application code once enforcement is enabled.
-- ============================================================

-- Required so PostgreSQL can enforce that a settings row points
-- to a school year owned by the same branch.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.table_constraints
        WHERE constraint_schema = 'public'
          AND table_name = 'school_years'
          AND constraint_name = 'school_years_branch_year_unique'
    ) THEN
        ALTER TABLE public.school_years
        ADD CONSTRAINT school_years_branch_year_unique UNIQUE (branch_id, year_id);
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS public.new_student_enrollment_settings (
    setting_id SERIAL PRIMARY KEY,
    branch_id  INTEGER NOT NULL REFERENCES public.branches(branch_id) ON DELETE CASCADE,
    year_id    INTEGER NOT NULL,
    is_open    BOOLEAN NOT NULL DEFAULT FALSE,
    opened_at  TIMESTAMP,
    closed_at  TIMESTAMP,
    opened_by  INTEGER REFERENCES public.users(user_id) ON DELETE SET NULL,
    closed_by  INTEGER REFERENCES public.users(user_id) ON DELETE SET NULL,
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT uq_new_student_enrollment_branch_year UNIQUE (branch_id, year_id),
    CONSTRAINT fk_new_student_enrollment_school_year_branch
        FOREIGN KEY (branch_id, year_id)
        REFERENCES public.school_years(branch_id, year_id)
        ON DELETE CASCADE
);
