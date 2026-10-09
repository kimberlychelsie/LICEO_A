-- Enrollment workflow compatibility columns for public enrollment,
-- duplicate detection, correction/resubmission, and Registrar decisions.
--
-- SAFE/IDEMPOTENT:
-- - Adds missing nullable columns only.
-- - Adds non-unique indexes only, plus branch enrollment number uniqueness
--   only when existing data is compatible.
-- - Deletes no records.
-- - Does not backfill or overwrite existing records.

BEGIN;

DO $$
DECLARE
    duplicate_branch_numbers text;
    incompatible_columns text;
    existing_constraint_def text;
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name = 'enrollments'
    ) THEN
        RAISE EXCEPTION 'Missing required table public.enrollments';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name = 'branches'
    ) THEN
        RAISE EXCEPTION 'Missing required table public.branches';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name = 'school_years'
    ) THEN
        RAISE EXCEPTION 'Missing required table public.school_years';
    END IF;

    WITH expected_columns(column_name, expected_data_type) AS (
        VALUES
            ('status', 'character varying'),
            ('student_first_name', 'character varying'),
            ('student_middle_name', 'character varying'),
            ('student_last_name', 'character varying'),
            ('father_first_name', 'character varying'),
            ('father_middle_name', 'character varying'),
            ('father_last_name', 'character varying'),
            ('mother_first_name', 'character varying'),
            ('mother_middle_name', 'character varying'),
            ('mother_last_name', 'character varying'),
            ('guardian_first_name', 'character varying'),
            ('guardian_middle_name', 'character varying'),
            ('guardian_last_name', 'character varying'),
            ('branch_enrollment_no', 'integer'),
            ('lrn', 'character varying'),
            ('email', 'character varying'),
            ('guardian_email', 'character varying'),
            ('enroll_type', 'character varying'),
            ('enroll_date', 'date'),
            ('birthplace', 'character varying'),
            ('remarks', 'text'),
            ('father_name', 'character varying'),
            ('father_contact', 'character varying'),
            ('father_occupation', 'character varying'),
            ('mother_name', 'character varying'),
            ('mother_contact', 'character varying'),
            ('mother_occupation', 'character varying'),
            ('school_year', 'character varying'),
            ('rejection_reason', 'text'),
            ('academic_status', 'character varying'),
            ('profile_image', 'character varying'),
            ('year_id', 'integer'),
            ('section_id', 'integer'),
            ('curriculum_type', 'character varying'),
            ('shs_track', 'character varying')
    ),
    existing_bad AS (
        SELECT ec.column_name || ' is ' || c.data_type ||
               COALESCE('(' || c.character_maximum_length || ')', '') AS item
        FROM expected_columns ec
        JOIN information_schema.columns c
          ON c.table_schema = 'public'
         AND c.table_name = 'enrollments'
         AND c.column_name = ec.column_name
        WHERE c.data_type <> ec.expected_data_type
    ),
    rejected_at_bad AS (
        SELECT 'rejected_at is ' || c.data_type AS item
        FROM information_schema.columns c
        WHERE c.table_schema = 'public'
          AND c.table_name = 'enrollments'
          AND c.column_name = 'rejected_at'
          AND c.data_type NOT IN ('timestamp without time zone', 'timestamp with time zone')
    )
    SELECT string_agg(item, ', ' ORDER BY item)
      INTO incompatible_columns
    FROM (
        SELECT item FROM existing_bad
        UNION ALL
        SELECT item FROM rejected_at_bad
    ) bad;

    IF incompatible_columns IS NOT NULL THEN
        RAISE EXCEPTION 'Incompatible existing enrollments columns: %', incompatible_columns;
    END IF;

    ALTER TABLE public.enrollments
        ADD COLUMN IF NOT EXISTS student_first_name VARCHAR(255),
        ADD COLUMN IF NOT EXISTS student_middle_name VARCHAR(255),
        ADD COLUMN IF NOT EXISTS student_last_name VARCHAR(255),
        ADD COLUMN IF NOT EXISTS father_first_name VARCHAR(255),
        ADD COLUMN IF NOT EXISTS father_middle_name VARCHAR(255),
        ADD COLUMN IF NOT EXISTS father_last_name VARCHAR(255),
        ADD COLUMN IF NOT EXISTS mother_first_name VARCHAR(255),
        ADD COLUMN IF NOT EXISTS mother_middle_name VARCHAR(255),
        ADD COLUMN IF NOT EXISTS mother_last_name VARCHAR(255),
        ADD COLUMN IF NOT EXISTS guardian_first_name VARCHAR(255),
        ADD COLUMN IF NOT EXISTS guardian_middle_name VARCHAR(255),
        ADD COLUMN IF NOT EXISTS guardian_last_name VARCHAR(255),
        ADD COLUMN IF NOT EXISTS branch_enrollment_no INTEGER,
        ADD COLUMN IF NOT EXISTS lrn VARCHAR(12),
        ADD COLUMN IF NOT EXISTS email VARCHAR(255),
        ADD COLUMN IF NOT EXISTS guardian_email VARCHAR(255),
        ADD COLUMN IF NOT EXISTS enroll_type VARCHAR(50),
        ADD COLUMN IF NOT EXISTS enroll_date DATE,
        ADD COLUMN IF NOT EXISTS birthplace VARCHAR(255),
        ADD COLUMN IF NOT EXISTS remarks TEXT,
        ADD COLUMN IF NOT EXISTS father_name VARCHAR(255),
        ADD COLUMN IF NOT EXISTS father_contact VARCHAR(255),
        ADD COLUMN IF NOT EXISTS father_occupation VARCHAR(255),
        ADD COLUMN IF NOT EXISTS mother_name VARCHAR(255),
        ADD COLUMN IF NOT EXISTS mother_contact VARCHAR(255),
        ADD COLUMN IF NOT EXISTS mother_occupation VARCHAR(255),
        ADD COLUMN IF NOT EXISTS school_year VARCHAR(255),
        ADD COLUMN IF NOT EXISTS rejection_reason TEXT,
        ADD COLUMN IF NOT EXISTS rejected_at TIMESTAMP,
        ADD COLUMN IF NOT EXISTS academic_status VARCHAR(50),
        ADD COLUMN IF NOT EXISTS profile_image VARCHAR(255),
        ADD COLUMN IF NOT EXISTS year_id INTEGER,
        ADD COLUMN IF NOT EXISTS section_id INTEGER,
        ADD COLUMN IF NOT EXISTS curriculum_type VARCHAR(50) DEFAULT 'basic_ed',
        ADD COLUMN IF NOT EXISTS shs_track VARCHAR(50);

    SELECT string_agg(branch_id::text || ':' || year_id::text || ':' || branch_enrollment_no::text || ' (' || ct::text || ')', ', ' ORDER BY branch_id, year_id, branch_enrollment_no)
      INTO duplicate_branch_numbers
    FROM (
        SELECT branch_id, year_id, branch_enrollment_no, COUNT(*) AS ct
        FROM public.enrollments
        WHERE year_id IS NOT NULL
          AND branch_enrollment_no IS NOT NULL
        GROUP BY branch_id, year_id, branch_enrollment_no
        HAVING COUNT(*) > 1
    ) dupes;

    IF duplicate_branch_numbers IS NOT NULL THEN
        RAISE EXCEPTION 'Cannot add uq_enrollments_branch_year_no; duplicate branch/year branch_enrollment_no values exist: %', duplicate_branch_numbers;
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'uq_enrollments_branch_year_no'
          AND conrelid = 'public.enrollments'::regclass
    ) THEN
        ALTER TABLE public.enrollments
            ADD CONSTRAINT uq_enrollments_branch_year_no
            UNIQUE (branch_id, year_id, branch_enrollment_no);
    ELSE
        SELECT pg_get_constraintdef(oid)
          INTO existing_constraint_def
        FROM pg_constraint
        WHERE conname = 'uq_enrollments_branch_year_no'
          AND conrelid = 'public.enrollments'::regclass;

        IF existing_constraint_def <> 'UNIQUE (branch_id, year_id, branch_enrollment_no)' THEN
            RAISE EXCEPTION 'Constraint uq_enrollments_branch_year_no has unexpected definition: %', existing_constraint_def;
        END IF;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_enrollments_identity_lrn
    ON public.enrollments (lrn)
    WHERE lrn IS NOT NULL AND TRIM(lrn) <> '';

CREATE INDEX IF NOT EXISTS idx_enrollments_identity_name_dob_email
    ON public.enrollments (
        lower(trim(coalesce(student_first_name, ''))),
        lower(trim(coalesce(student_middle_name, ''))),
        lower(trim(coalesce(student_last_name, ''))),
        dob,
        lower(trim(coalesce(email, '')))
    );

CREATE INDEX IF NOT EXISTS idx_enrollments_status_identity
    ON public.enrollments (status, enrollment_id);

CREATE INDEX IF NOT EXISTS idx_enrollments_branch_year_status
    ON public.enrollments (branch_id, year_id, status);

COMMIT;
