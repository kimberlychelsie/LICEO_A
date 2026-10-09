-- Enrollment workflow cleanup: introduce correction_requested status.
-- Source schema uses enrollments.status as VARCHAR(20), so no column change is
-- required unless a deployed database has an out-of-band CHECK constraint.
-- Preserve historical rejected rows; do not backfill automatically.

BEGIN;

DO $$
DECLARE
    constraint_def text;
BEGIN
    SELECT pg_get_constraintdef(c.oid)
      INTO constraint_def
    FROM pg_constraint c
    JOIN pg_class t ON t.oid = c.conrelid
    JOIN pg_namespace n ON n.oid = t.relnamespace
    WHERE n.nspname = 'public'
      AND t.relname = 'enrollments'
      AND c.contype = 'c'
      AND pg_get_constraintdef(c.oid) ILIKE '%status%'
    LIMIT 1;

    IF constraint_def IS NOT NULL AND constraint_def NOT ILIKE '%correction_requested%' THEN
        RAISE EXCEPTION 'Manual review required: enrollments.status CHECK constraint must be updated to allow correction_requested. Constraint: %', constraint_def;
    END IF;
END $$;

COMMIT;
