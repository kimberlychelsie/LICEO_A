-- Canonical academic-calendar term storage required by grading policies.
-- Additive and idempotent: existing rows are never updated or deleted.

BEGIN;

DO $$
BEGIN
    IF to_regclass('public.branches') IS NULL
       OR to_regclass('public.school_years') IS NULL THEN
        RAISE EXCEPTION 'branches and school_years must exist before grading period ranges';
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS public.grading_period_ranges (
    id          SERIAL PRIMARY KEY,
    branch_id   INTEGER NOT NULL,
    year_id     INTEGER NOT NULL,
    period_name VARCHAR(10) NOT NULL,
    start_date  DATE NOT NULL,
    end_date    DATE NOT NULL,
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Calendar terms referenced by locked policy history must be archived instead
-- of physically deleted. Existing rows remain active on first installation.
ALTER TABLE public.grading_period_ranges
    ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;

-- Refuse incompatible legacy shapes instead of coercing or rewriting them.
DO $$
DECLARE
    mismatch TEXT;
BEGIN
    SELECT string_agg(expected.column_name, ', ' ORDER BY expected.column_name)
      INTO mismatch
    FROM (VALUES
        ('id',          'integer',              'NO'),
        ('branch_id',   'integer',              'NO'),
        ('year_id',     'integer',              'NO'),
        ('period_name', 'character varying',    'NO'),
        ('start_date',  'date',                 'NO'),
        ('end_date',    'date',                 'NO'),
        ('is_active',   'boolean',              'NO')
    ) AS expected(column_name, data_type, is_nullable)
    LEFT JOIN information_schema.columns actual
      ON actual.table_schema='public'
     AND actual.table_name='grading_period_ranges'
     AND actual.column_name=expected.column_name
    WHERE actual.column_name IS NULL
       OR actual.data_type <> expected.data_type
       OR actual.is_nullable <> expected.is_nullable;

    IF mismatch IS NOT NULL THEN
        RAISE EXCEPTION
            'Incompatible grading_period_ranges columns require manual review: %', mismatch;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema='public' AND table_name='grading_period_ranges'
          AND column_name='id' AND column_default IS NOT NULL
    ) THEN
        RAISE EXCEPTION 'grading_period_ranges.id requires a sequence-backed default; manual review required';
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint c
        WHERE c.conrelid='public.school_years'::regclass
          AND c.contype IN ('p','u')
          AND pg_get_constraintdef(c.oid)='UNIQUE (branch_id, year_id)'
    ) THEN
        ALTER TABLE public.school_years
            ADD CONSTRAINT school_years_branch_year_unique
            UNIQUE (branch_id, year_id);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint c
        WHERE c.conrelid='public.grading_period_ranges'::regclass
          AND c.contype='p'
    ) THEN
        ALTER TABLE public.grading_period_ranges
            ADD CONSTRAINT grading_period_ranges_pkey PRIMARY KEY (id);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint c
        WHERE c.conrelid='public.grading_period_ranges'::regclass
          AND c.contype='u'
          AND pg_get_constraintdef(c.oid)='UNIQUE (branch_id, year_id, period_name)'
    ) THEN
        ALTER TABLE public.grading_period_ranges
            ADD CONSTRAINT grading_period_ranges_branch_year_name_unique
            UNIQUE (branch_id, year_id, period_name);
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
          AND c.contype='c'
          AND pg_get_constraintdef(c.oid) LIKE 'CHECK ((start_date <= end_date))%'
    ) THEN
        ALTER TABLE public.grading_period_ranges
            ADD CONSTRAINT grading_period_ranges_date_order_check
            CHECK (start_date <= end_date) NOT VALID;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint c
        WHERE c.conrelid='public.grading_period_ranges'::regclass
          AND c.contype='f'
          AND pg_get_constraintdef(c.oid) LIKE
              'FOREIGN KEY (branch_id, year_id) REFERENCES school_years(branch_id, year_id)%'
    ) THEN
        ALTER TABLE public.grading_period_ranges
            ADD CONSTRAINT grading_period_ranges_branch_year_fkey
            FOREIGN KEY (branch_id, year_id)
            REFERENCES public.school_years (branch_id, year_id)
            ON DELETE RESTRICT
            NOT VALID;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_grading_period_ranges_active_date
    ON public.grading_period_ranges (branch_id, year_id, start_date, end_date);

CREATE INDEX IF NOT EXISTS idx_grading_period_ranges_current_date
    ON public.grading_period_ranges (branch_id, year_id, start_date, end_date)
    WHERE is_active;

COMMIT;

-- Validate only after the read-only discovery report shows no legacy conflicts:
-- ALTER TABLE public.grading_period_ranges VALIDATE CONSTRAINT grading_period_ranges_date_order_check;
-- ALTER TABLE public.grading_period_ranges VALIDATE CONSTRAINT grading_period_ranges_branch_year_fkey;
