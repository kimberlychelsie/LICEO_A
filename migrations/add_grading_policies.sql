-- Explicit, versioned grading-policy foundation.
-- This migration creates no policies and changes no historical grade records.

BEGIN;

DO $$
BEGIN
    IF to_regclass('public.grading_period_ranges') IS NULL THEN
        RAISE EXCEPTION 'Run add_grading_period_ranges_foundation.sql first';
    END IF;
END $$;

-- The scoped calendar-term foreign key below requires this exact candidate key.
-- Establish it here as well as in the foundation migration so this migration is
-- safe after an older or partially applied version of the foundation script.
DO $$
DECLARE
    missing_columns TEXT;
BEGIN
    SELECT string_agg(expected.column_name, ', ' ORDER BY expected.column_name)
      INTO missing_columns
    FROM (VALUES ('id'), ('branch_id'), ('year_id')) AS expected(column_name)
    LEFT JOIN information_schema.columns actual
      ON actual.table_schema='public'
     AND actual.table_name='grading_period_ranges'
     AND actual.column_name=expected.column_name
    WHERE actual.column_name IS NULL;

    IF missing_columns IS NOT NULL THEN
        RAISE EXCEPTION
            'grading_period_ranges is missing required scoped-key columns: %',
            missing_columns;
    END IF;

    IF EXISTS (
        SELECT 1 FROM pg_constraint c
        WHERE c.conrelid='public.grading_period_ranges'::regclass
          AND c.conname='grading_period_ranges_scoped_id_unique'
          AND NOT (
              c.contype='u'
              AND (
                  SELECT array_agg(a.attname::TEXT ORDER BY key.ordinality)
                  FROM unnest(c.conkey) WITH ORDINALITY AS key(attnum, ordinality)
                  JOIN pg_attribute a
                    ON a.attrelid=c.conrelid AND a.attnum=key.attnum
              )=ARRAY['id','branch_id','year_id']::TEXT[]
          )
    ) THEN
        RAISE EXCEPTION
            'Constraint grading_period_ranges_scoped_id_unique has an incompatible definition; manual review required';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint c
        WHERE c.conrelid='public.grading_period_ranges'::regclass
          AND c.contype IN ('p','u')
          AND (
              SELECT array_agg(a.attname::TEXT ORDER BY key.ordinality)
              FROM unnest(c.conkey) WITH ORDINALITY AS key(attnum, ordinality)
              JOIN pg_attribute a
                ON a.attrelid=c.conrelid AND a.attnum=key.attnum
          )=ARRAY['id','branch_id','year_id']::TEXT[]
    ) THEN
        ALTER TABLE public.grading_period_ranges
            ADD CONSTRAINT grading_period_ranges_scoped_id_unique
            UNIQUE (id, branch_id, year_id);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint c
        WHERE c.conrelid='public.grading_period_ranges'::regclass
          AND c.contype IN ('p','u')
          AND (
              SELECT array_agg(a.attname::TEXT ORDER BY key.ordinality)
              FROM unnest(c.conkey) WITH ORDINALITY AS key(attnum, ordinality)
              JOIN pg_attribute a
                ON a.attrelid=c.conrelid AND a.attnum=key.attnum
          )=ARRAY['id','branch_id','year_id']::TEXT[]
    ) THEN
        RAISE EXCEPTION
            'grading_period_ranges requires UNIQUE (id, branch_id, year_id)';
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS public.grading_policies (
    policy_id          BIGSERIAL PRIMARY KEY,
    branch_id          INTEGER NOT NULL,
    year_id            INTEGER NOT NULL,
    policy_version     VARCHAR(50) NOT NULL,
    rounding_mode      VARCHAR(30) NOT NULL,
    rounding_scale     SMALLINT NOT NULL,
    status             VARCHAR(30) NOT NULL DEFAULT 'draft',
    verification_notes TEXT,
    created_by         INTEGER REFERENCES public.users(user_id) ON DELETE SET NULL,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    verified_by        INTEGER REFERENCES public.users(user_id) ON DELETE SET NULL,
    verified_at        TIMESTAMPTZ,
    activated_by       INTEGER REFERENCES public.users(user_id) ON DELETE SET NULL,
    activated_at       TIMESTAMPTZ,
    retired_at         TIMESTAMPTZ,
    CONSTRAINT grading_policies_scope_version_unique
        UNIQUE (branch_id, year_id, policy_version),
    CONSTRAINT grading_policies_scoped_id_unique
        UNIQUE (policy_id, branch_id, year_id),
    CONSTRAINT grading_policies_branch_year_fkey
        FOREIGN KEY (branch_id, year_id)
        REFERENCES public.school_years(branch_id, year_id) ON DELETE RESTRICT,
    CONSTRAINT grading_policies_rounding_check
        CHECK (rounding_mode='excel_round' AND rounding_scale BETWEEN 0 AND 4),
    CONSTRAINT grading_policies_status_check
        CHECK (status IN ('draft','pending_verification','verified','active','retired')),
    CONSTRAINT grading_policies_verification_check
        CHECK (
            status IN ('draft','pending_verification')
            OR (verified_by IS NOT NULL AND verified_at IS NOT NULL
                AND NULLIF(BTRIM(verification_notes),'') IS NOT NULL)
        )
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_grading_policies_active_scope
    ON public.grading_policies (branch_id, year_id)
    WHERE status='active';

CREATE TABLE IF NOT EXISTS public.grading_policy_periods (
    policy_id        BIGINT NOT NULL,
    branch_id        INTEGER NOT NULL,
    year_id          INTEGER NOT NULL,
    sequence_no      SMALLINT NOT NULL,
    calendar_term_id INTEGER NOT NULL,
    PRIMARY KEY (policy_id, sequence_no),
    CONSTRAINT grading_policy_period_term_unique
        UNIQUE (policy_id, calendar_term_id),
    CONSTRAINT grading_policy_period_sequence_check CHECK (sequence_no >= 1),
    CONSTRAINT grading_policy_period_policy_fkey
        FOREIGN KEY (policy_id, branch_id, year_id)
        REFERENCES public.grading_policies(policy_id, branch_id, year_id)
        ON DELETE RESTRICT,
    CONSTRAINT grading_policy_period_calendar_fkey
        FOREIGN KEY (calendar_term_id, branch_id, year_id)
        REFERENCES public.grading_period_ranges(id, branch_id, year_id)
        ON DELETE RESTRICT
);

-- Existing objects with these names must match the additive foundation.
DO $$
DECLARE
    mismatch TEXT;
BEGIN
    SELECT string_agg(expected.column_name, ', ' ORDER BY expected.column_name)
      INTO mismatch
    FROM (VALUES
        ('policy_id','bigint','NO'), ('branch_id','integer','NO'),
        ('year_id','integer','NO'), ('policy_version','character varying','NO'),
        ('rounding_mode','character varying','NO'), ('rounding_scale','smallint','NO'),
        ('status','character varying','NO')
    ) AS expected(column_name,data_type,is_nullable)
    LEFT JOIN information_schema.columns actual
      ON actual.table_schema='public' AND actual.table_name='grading_policies'
     AND actual.column_name=expected.column_name
    WHERE actual.column_name IS NULL OR actual.data_type<>expected.data_type
       OR actual.is_nullable<>expected.is_nullable;
    IF mismatch IS NOT NULL THEN
        RAISE EXCEPTION 'Incompatible grading_policies columns require manual review: %', mismatch;
    END IF;

    SELECT string_agg(expected.column_name, ', ' ORDER BY expected.column_name)
      INTO mismatch
    FROM (VALUES
        ('policy_id','bigint','NO'), ('branch_id','integer','NO'),
        ('year_id','integer','NO'), ('sequence_no','smallint','NO'),
        ('calendar_term_id','integer','NO')
    ) AS expected(column_name,data_type,is_nullable)
    LEFT JOIN information_schema.columns actual
      ON actual.table_schema='public' AND actual.table_name='grading_policy_periods'
     AND actual.column_name=expected.column_name
    WHERE actual.column_name IS NULL OR actual.data_type<>expected.data_type
       OR actual.is_nullable<>expected.is_nullable;
    IF mismatch IS NOT NULL THEN
        RAISE EXCEPTION 'Incompatible grading_policy_periods columns require manual review: %', mismatch;
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint c
        WHERE c.conrelid='public.grading_policies'::regclass AND c.contype='p'
          AND pg_get_constraintdef(c.oid)='PRIMARY KEY (policy_id)'
    ) THEN
        ALTER TABLE public.grading_policies
            ADD CONSTRAINT grading_policies_pkey PRIMARY KEY (policy_id);
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint c
        WHERE c.conrelid='public.grading_policies'::regclass AND c.contype='u'
          AND pg_get_constraintdef(c.oid)='UNIQUE (branch_id, year_id, policy_version)'
    ) THEN
        ALTER TABLE public.grading_policies
            ADD CONSTRAINT grading_policies_scope_version_unique
            UNIQUE (branch_id, year_id, policy_version);
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint c
        WHERE c.conrelid='public.grading_policies'::regclass AND c.contype='u'
          AND pg_get_constraintdef(c.oid)='UNIQUE (policy_id, branch_id, year_id)'
    ) THEN
        ALTER TABLE public.grading_policies
            ADD CONSTRAINT grading_policies_scoped_id_unique
            UNIQUE (policy_id, branch_id, year_id);
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint c
        WHERE c.conrelid='public.grading_policy_periods'::regclass AND c.contype='p'
          AND pg_get_constraintdef(c.oid)='PRIMARY KEY (policy_id, sequence_no)'
    ) THEN
        ALTER TABLE public.grading_policy_periods
            ADD CONSTRAINT grading_policy_periods_pkey PRIMARY KEY (policy_id, sequence_no);
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint c
        WHERE c.conrelid='public.grading_policy_periods'::regclass AND c.contype='u'
          AND pg_get_constraintdef(c.oid)='UNIQUE (policy_id, calendar_term_id)'
    ) THEN
        ALTER TABLE public.grading_policy_periods
            ADD CONSTRAINT grading_policy_period_term_unique UNIQUE (policy_id, calendar_term_id);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_grading_policy_periods_scope
    ON public.grading_policy_periods (branch_id, year_id, policy_id, sequence_no);

CREATE OR REPLACE FUNCTION public.grading_policy_has_grade_references(target_policy_id BIGINT)
RETURNS BOOLEAN
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    found_reference BOOLEAN := FALSE;
BEGIN
    IF to_regclass('public.grade_submission_requests') IS NOT NULL THEN
        EXECUTE $sql$
            SELECT EXISTS (
                SELECT 1
                FROM public.grading_policies gp
                JOIN public.grading_policy_periods gpp ON gpp.policy_id=gp.policy_id
                JOIN public.grading_period_ranges gpr ON gpr.id=gpp.calendar_term_id
                JOIN public.grade_submission_requests gsr
                  ON gsr.branch_id=gp.branch_id AND gsr.year_id=gp.year_id
                 AND gsr.grading_period=gpr.period_name
                WHERE gp.policy_id=$1
                  AND gsr.status IN (
                    'pending_academic_coordinator','pending_admin',
                    'approved_for_posting','posted','rejected'
                  )
            )
        $sql$ INTO found_reference USING target_policy_id;
        IF found_reference THEN RETURN TRUE; END IF;
    END IF;

    IF to_regclass('public.posted_grades') IS NOT NULL
       AND to_regclass('public.sections') IS NOT NULL THEN
        EXECUTE $sql$
            SELECT EXISTS (
                SELECT 1
                FROM public.grading_policies gp
                JOIN public.grading_policy_periods gpp ON gpp.policy_id=gp.policy_id
                JOIN public.grading_period_ranges gpr ON gpr.id=gpp.calendar_term_id
                JOIN public.posted_grades pg
                  ON pg.year_id=gp.year_id AND pg.grading_period=gpr.period_name
                JOIN public.sections s
                  ON s.section_id=pg.section_id AND s.branch_id=gp.branch_id
                WHERE gp.policy_id=$1
            )
        $sql$ INTO found_reference USING target_policy_id;
        IF found_reference THEN RETURN TRUE; END IF;
    END IF;

    IF to_regclass('public.finalized_grades') IS NOT NULL
       AND to_regclass('public.enrollments') IS NOT NULL THEN
        EXECUTE $sql$
            SELECT EXISTS (
                SELECT 1
                FROM public.grading_policies gp
                JOIN public.grading_policy_periods gpp ON gpp.policy_id=gp.policy_id
                JOIN public.grading_period_ranges gpr ON gpr.id=gpp.calendar_term_id
                JOIN public.finalized_grades fg
                  ON fg.year_id=gp.year_id AND fg.grading_period=gpr.period_name
                JOIN public.enrollments e
                  ON e.enrollment_id=fg.enrollment_id AND e.branch_id=gp.branch_id
                WHERE gp.policy_id=$1
            )
        $sql$ INTO found_reference USING target_policy_id;
    END IF;
    RETURN found_reference;
END $$;

CREATE OR REPLACE FUNCTION public.validate_grading_policy_periods(target_policy_id BIGINT)
RETURNS VOID
LANGUAGE plpgsql
AS $$
DECLARE
    period_count INTEGER;
    min_sequence INTEGER;
    max_sequence INTEGER;
BEGIN
    SELECT COUNT(*), MIN(sequence_no), MAX(sequence_no)
      INTO period_count, min_sequence, max_sequence
    FROM public.grading_policy_periods
    WHERE policy_id=target_policy_id;

    IF period_count=0 OR min_sequence<>1 OR max_sequence<>period_count THEN
        RAISE EXCEPTION
            'Grading policy % must have contiguous periods numbered from 1',
            target_policy_id;
    END IF;
END $$;

CREATE OR REPLACE FUNCTION public.guard_grading_policy_update()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP='INSERT' THEN
        IF NEW.status<>'draft' THEN
            RAISE EXCEPTION 'New grading policies must start in draft status';
        END IF;
        RETURN NEW;
    END IF;

    -- Draft and pending policies are candidates, not historical references.
    -- They must remain editable even when legacy grades share their term names.
    IF TG_OP='DELETE' THEN
        IF OLD.status IN ('verified','active','retired') THEN
            RAISE EXCEPTION 'Locked grading policies require an audited migration';
        END IF;
        RETURN OLD;
    END IF;

    IF OLD.policy_id<>NEW.policy_id OR OLD.branch_id<>NEW.branch_id
       OR OLD.year_id<>NEW.year_id OR OLD.policy_version<>NEW.policy_version THEN
        RAISE EXCEPTION 'Grading policy identity and scope are immutable';
    END IF;

    IF OLD.status IN ('verified','active','retired')
       AND (OLD.rounding_mode, OLD.rounding_scale, OLD.verification_notes)
           IS DISTINCT FROM
           (NEW.rounding_mode, NEW.rounding_scale, NEW.verification_notes) THEN
        RAISE EXCEPTION 'Verified, active, and retired grading policies are immutable';
    END IF;

    IF OLD.status<>NEW.status THEN
        IF NOT (
            (OLD.status='draft' AND NEW.status='pending_verification') OR
            (OLD.status='pending_verification' AND NEW.status IN ('draft','verified')) OR
            (OLD.status='verified' AND NEW.status='active') OR
            (OLD.status='active' AND NEW.status='retired')
        ) THEN
            RAISE EXCEPTION 'Invalid grading policy status transition: % -> %', OLD.status, NEW.status;
        END IF;
        IF NEW.status IN ('verified','active') THEN
            PERFORM public.validate_grading_policy_periods(NEW.policy_id);
        END IF;
    END IF;

    IF OLD.status IN ('verified','active','retired')
       AND public.grading_policy_has_grade_references(OLD.policy_id)
       AND (OLD.rounding_mode, OLD.rounding_scale)
           IS DISTINCT FROM (NEW.rounding_mode, NEW.rounding_scale) THEN
        RAISE EXCEPTION 'Historically referenced grading policies require an audited migration';
    END IF;
    RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION public.guard_grading_policy_period_change()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    target_policy BIGINT;
    target_status TEXT;
BEGIN
    target_policy := CASE WHEN TG_OP='DELETE' THEN OLD.policy_id ELSE NEW.policy_id END;
    SELECT status INTO target_status
    FROM public.grading_policies WHERE policy_id=target_policy FOR UPDATE;
    IF target_status IS NULL THEN
        RAISE EXCEPTION 'Grading policy % does not exist', target_policy;
    END IF;
    -- Only verified lifecycle states are locked.  The indirect reference
    -- detector matches by branch/year/term and must not lock a new draft.
    IF target_status IN ('verified','active','retired') THEN
        RAISE EXCEPTION 'Locked grading policy periods require an audited migration';
    END IF;
    RETURN COALESCE(NEW, OLD);
END $$;

DROP TRIGGER IF EXISTS trg_guard_grading_policy_update ON public.grading_policies;
CREATE TRIGGER trg_guard_grading_policy_update
BEFORE INSERT OR UPDATE OR DELETE ON public.grading_policies
FOR EACH ROW EXECUTE FUNCTION public.guard_grading_policy_update();

DROP TRIGGER IF EXISTS trg_guard_grading_policy_period_change ON public.grading_policy_periods;
CREATE TRIGGER trg_guard_grading_policy_period_change
BEFORE INSERT OR UPDATE OR DELETE ON public.grading_policy_periods
FOR EACH ROW EXECUTE FUNCTION public.guard_grading_policy_period_change();

COMMIT;
