-- ============================================================
-- section_teachers: Add term_name and is_archived columns
-- SAFE: idempotent (IF NOT EXISTS)
-- Run this in Railway: Postgres → Database → Query tab
-- ============================================================

ALTER TABLE public.section_teachers
    ADD COLUMN IF NOT EXISTS term_name   VARCHAR(50),
    ADD COLUMN IF NOT EXISTS is_archived BOOLEAN DEFAULT FALSE;

DO $$
BEGIN
    RAISE NOTICE 'section_teachers: term_name and is_archived columns ensured.';
END $$;
