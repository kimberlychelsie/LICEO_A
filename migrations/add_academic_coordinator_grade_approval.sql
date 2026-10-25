-- Additive Academic Coordinator support for teacher accounts and grade approvals.
-- Safe to rerun. Existing approval records and grade values are not rewritten.

BEGIN;

ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS is_academic_coordinator BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE public.grade_submission_requests
    ADD COLUMN IF NOT EXISTS academic_coordinator_approved_by INTEGER,
    ADD COLUMN IF NOT EXISTS academic_coordinator_approved_at TIMESTAMP;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'grade_submission_requests_academic_coordinator_approved_by_fkey'
    ) THEN
        ALTER TABLE public.grade_submission_requests
            ADD CONSTRAINT grade_submission_requests_academic_coordinator_approved_by_fkey
            FOREIGN KEY (academic_coordinator_approved_by)
            REFERENCES public.users(user_id)
            ON DELETE SET NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_grade_sub_pending_academic_coordinator
    ON public.grade_submission_requests (branch_id, year_id, status)
    WHERE status = 'pending_academic_coordinator';

COMMIT;
