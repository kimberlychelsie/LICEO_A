-- Phase 1 Student Identity Protection: Registrar review queue
-- Stores ambiguous identity decisions without changing enrollment records.
--
-- SAFE/IDEMPOTENT:
-- - Creates student_identity_reviews only when missing.
-- - Adds no enrollment/student data.
-- - Deletes no records.
-- - Fails early if required base tables/columns are missing.
-- - Adds supporting non-unique indexes only.
-- - Preserves review audit rows by preventing deletion of referenced
--   enrollments/branches while reviews exist.

BEGIN;

DO $$
DECLARE
    missing_items text;
    missing_constraints text;
BEGIN
    WITH required_tables(table_name) AS (
        VALUES
            ('enrollments'),
            ('student_accounts'),
            ('branches'),
            ('users')
    ),
    missing_tables AS (
        SELECT 'table public.' || rt.table_name AS item
        FROM required_tables rt
        WHERE NOT EXISTS (
            SELECT 1
            FROM information_schema.tables t
            WHERE t.table_schema = 'public'
              AND t.table_name = rt.table_name
        )
    ),
    required_columns(table_name, column_name) AS (
        VALUES
            ('enrollments', 'enrollment_id'),
            ('enrollments', 'branch_id'),
            ('student_accounts', 'enrollment_id'),
            ('branches', 'branch_id'),
            ('users', 'user_id')
    ),
    missing_columns AS (
        SELECT 'column public.' || rc.table_name || '.' || rc.column_name AS item
        FROM required_columns rc
        WHERE NOT EXISTS (
            SELECT 1
            FROM information_schema.columns c
            WHERE c.table_schema = 'public'
              AND c.table_name = rc.table_name
              AND c.column_name = rc.column_name
        )
    )
    SELECT string_agg(item, ', ' ORDER BY item)
      INTO missing_items
    FROM (
        SELECT item FROM missing_tables
        UNION ALL
        SELECT item FROM missing_columns
    ) missing;

    IF missing_items IS NOT NULL THEN
        RAISE EXCEPTION 'Missing required schema for student_identity_reviews migration: %', missing_items;
    END IF;

    WITH required_pk(table_name, column_name) AS (
        VALUES
            ('enrollments', 'enrollment_id'),
            ('branches', 'branch_id'),
            ('users', 'user_id')
    ),
    missing_pk AS (
        SELECT 'primary/unique key public.' || rp.table_name || '(' || rp.column_name || ')' AS item
        FROM required_pk rp
        WHERE NOT EXISTS (
            SELECT 1
            FROM pg_constraint con
            JOIN pg_class rel ON rel.oid = con.conrelid
            JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
            JOIN pg_attribute att ON att.attrelid = rel.oid AND att.attnum = ANY(con.conkey)
            WHERE nsp.nspname = 'public'
              AND rel.relname = rp.table_name
              AND att.attname = rp.column_name
              AND con.contype IN ('p', 'u')
        )
    )
    SELECT string_agg(item, ', ' ORDER BY item)
      INTO missing_constraints
    FROM missing_pk;

    IF missing_constraints IS NOT NULL THEN
        RAISE EXCEPTION 'Missing referenced primary/unique constraints for student_identity_reviews migration: %', missing_constraints;
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS public.student_identity_reviews (
    review_id SERIAL PRIMARY KEY,
    enrollment_id INTEGER NOT NULL REFERENCES public.enrollments(enrollment_id),
    matched_enrollment_id INTEGER REFERENCES public.enrollments(enrollment_id) ON DELETE SET NULL,
    branch_id INTEGER NOT NULL REFERENCES public.branches(branch_id),
    status VARCHAR(30) NOT NULL DEFAULT 'pending',
    reasons TEXT,
    decision_reason TEXT,
    reviewed_by INTEGER REFERENCES public.users(user_id) ON DELETE SET NULL,
    reviewed_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_student_identity_review_enrollment UNIQUE (enrollment_id),
    CONSTRAINT chk_student_identity_review_status
        CHECK (status IN ('pending', 'distinct_student', 'existing_student'))
);

CREATE INDEX IF NOT EXISTS idx_student_identity_reviews_branch_status
    ON public.student_identity_reviews (branch_id, status);

CREATE INDEX IF NOT EXISTS idx_student_identity_reviews_matched
    ON public.student_identity_reviews (matched_enrollment_id);

CREATE INDEX IF NOT EXISTS idx_student_identity_reviews_reviewed_by
    ON public.student_identity_reviews (reviewed_by);

CREATE INDEX IF NOT EXISTS idx_student_identity_reviews_status_updated
    ON public.student_identity_reviews (status, updated_at);

CREATE INDEX IF NOT EXISTS idx_student_accounts_enrollment_identity
    ON public.student_accounts (enrollment_id)
    WHERE enrollment_id IS NOT NULL;

COMMIT;
