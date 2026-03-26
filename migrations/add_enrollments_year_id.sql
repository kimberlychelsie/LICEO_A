-- Migration: Add year_id to enrollments and link to school_years

ALTER TABLE enrollments ADD COLUMN IF NOT EXISTS year_id INTEGER;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_enrollments_year'
    ) THEN
        ALTER TABLE enrollments
        ADD CONSTRAINT fk_enrollments_year
        FOREIGN KEY (year_id) REFERENCES school_years(year_id);
    END IF;
END $$;
