-- Phase 3: add school-year support to teacher class announcements.
--
-- This migration is additive. It intentionally leaves year_id nullable and
-- does not update existing announcement records.
--
-- The regular CREATE INDEX below is transaction-safe and suitable for local
-- preparation. On a busy production database, operators may instead create
-- the same index with CREATE INDEX CONCURRENTLY. CONCURRENTLY must be executed
-- outside a transaction and must not be placed inside a transactional
-- migration runner.

ALTER TABLE public.teacher_announcements
    ADD COLUMN IF NOT EXISTS year_id INTEGER;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint c
        WHERE c.conrelid = 'public.teacher_announcements'::regclass
          AND c.contype = 'f'
          AND pg_get_constraintdef(c.oid) LIKE
              'FOREIGN KEY (branch_id, year_id) REFERENCES school_years(branch_id, year_id)%'
    ) THEN
        IF NOT EXISTS (
            SELECT 1
            FROM pg_constraint c
            WHERE c.conrelid = 'public.school_years'::regclass
              AND c.contype IN ('p', 'u')
              AND pg_get_constraintdef(c.oid) = 'UNIQUE (branch_id, year_id)'
        ) THEN
            RAISE EXCEPTION
                'Required UNIQUE (branch_id, year_id) constraint is missing on school_years';
        END IF;

        IF EXISTS (
            SELECT 1
            FROM pg_constraint c
            WHERE c.conrelid = 'public.teacher_announcements'::regclass
              AND c.conname = 'teacher_announcements_branch_year_fkey'
        ) THEN
            RAISE EXCEPTION
                'Constraint teacher_announcements_branch_year_fkey exists with an unexpected definition';
        END IF;

        ALTER TABLE public.teacher_announcements
            ADD CONSTRAINT teacher_announcements_branch_year_fkey
            FOREIGN KEY (branch_id, year_id)
            REFERENCES public.school_years (branch_id, year_id)
            ON DELETE RESTRICT
            NOT VALID;
    END IF;
END
$$;

CREATE INDEX IF NOT EXISTS idx_teacher_ann_branch_year_created
    ON public.teacher_announcements
       (branch_id, year_id, created_at DESC, announcement_id DESC);

-- Validate only after the separate, audited backfill has completed:
-- ALTER TABLE public.teacher_announcements
--     VALIDATE CONSTRAINT teacher_announcements_branch_year_fkey;
--
-- Production alternative for the index (run outside a transaction):
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_teacher_ann_branch_year_created
--     ON public.teacher_announcements
--        (branch_id, year_id, created_at DESC, announcement_id DESC);
