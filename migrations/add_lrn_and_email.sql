-- ============================================================
-- MIGRATION: Add lrn, email, guardian_email to enrollments
-- Run this in Railway: Postgres → Database → Query tab
-- if lrn column does NOT already exist on your Railway DB
-- ============================================================

ALTER TABLE public.enrollments
    ADD COLUMN IF NOT EXISTS lrn character varying(12);

ALTER TABLE public.enrollments
    ADD COLUMN IF NOT EXISTS email character varying(255);

ALTER TABLE public.enrollments
    ADD COLUMN IF NOT EXISTS guardian_email character varying(255);

-- ============================================================
-- MIGRATION: Ensure enrollments.status can hold new values
-- (open_for_enrollment, enrolled) - no change needed since
-- status is VARCHAR(20) which is already wide enough.
-- ============================================================

-- ============================================================
-- MIGRATION: Add branch_code to branches (if missing)
-- ============================================================
ALTER TABLE public.branches
    ADD COLUMN IF NOT EXISTS branch_code character varying(20);
