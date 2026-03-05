-- Migration to add section_id to enrollments table
BEGIN;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name   = 'enrollments'
          AND column_name  = 'section_id'
    ) THEN
        ALTER TABLE public.enrollments
            ADD COLUMN section_id INTEGER REFERENCES public.sections(section_id) ON DELETE SET NULL;
    END IF;
END
$$;

COMMIT;
