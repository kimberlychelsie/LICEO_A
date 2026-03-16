-- Migration to add missing enrollment columns to the enrollments table
BEGIN;

DO $$
BEGIN
    -- enroll_type
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='enrollments' AND column_name='enroll_type') THEN
        ALTER TABLE public.enrollments ADD COLUMN enroll_type VARCHAR(50);
    END IF;

    -- enroll_date
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='enrollments' AND column_name='enroll_date') THEN
        ALTER TABLE public.enrollments ADD COLUMN enroll_date DATE;
    END IF;

    -- remarks
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='enrollments' AND column_name='remarks') THEN
        ALTER TABLE public.enrollments ADD COLUMN remarks TEXT;
    END IF;

    -- birthplace
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='enrollments' AND column_name='birthplace') THEN
        ALTER TABLE public.enrollments ADD COLUMN birthplace VARCHAR(255);
    END IF;

    -- father_name
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='enrollments' AND column_name='father_name') THEN
        ALTER TABLE public.enrollments ADD COLUMN father_name VARCHAR(100);
    END IF;

    -- father_contact
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='enrollments' AND column_name='father_contact') THEN
        ALTER TABLE public.enrollments ADD COLUMN father_contact VARCHAR(20);
    END IF;

    -- father_occupation
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='enrollments' AND column_name='father_occupation') THEN
        ALTER TABLE public.enrollments ADD COLUMN father_occupation VARCHAR(100);
    END IF;

    -- mother_name
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='enrollments' AND column_name='mother_name') THEN
        ALTER TABLE public.enrollments ADD COLUMN mother_name VARCHAR(100);
    END IF;

    -- mother_contact
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='enrollments' AND column_name='mother_contact') THEN
        ALTER TABLE public.enrollments ADD COLUMN mother_contact VARCHAR(20);
    END IF;

    -- mother_occupation
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='enrollments' AND column_name='mother_occupation') THEN
        ALTER TABLE public.enrollments ADD COLUMN mother_occupation VARCHAR(100);
    END IF;

    -- school_year
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='enrollments' AND column_name='school_year') THEN
        ALTER TABLE public.enrollments ADD COLUMN school_year VARCHAR(20);
    END IF;
END
$$;

COMMIT;
