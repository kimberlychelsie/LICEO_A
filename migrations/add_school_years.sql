-- Migration: Add school_years table and link sections to it

-- 1. Create the school_years table
CREATE TABLE IF NOT EXISTS school_years (
    year_id SERIAL PRIMARY KEY,
    label VARCHAR(9) NOT NULL
);

-- 2. Add branch_id column to school_years
ALTER TABLE school_years
ADD COLUMN IF NOT EXISTS branch_id INT;

-- 3. Add foreign key from school_years to branches
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_school_year_branch'
    ) THEN
        ALTER TABLE school_years
        ADD CONSTRAINT fk_school_year_branch
        FOREIGN KEY (branch_id) REFERENCES branches(branch_id);
    END IF;
END $$;

-- 4. Drop old unique constraint on label alone (if exists)
ALTER TABLE school_years
DROP CONSTRAINT IF EXISTS school_years_label_key;

-- 5. Create unique constraint on (branch_id, label)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'school_years_branch_label_unique'
    ) THEN
        ALTER TABLE school_years
        ADD CONSTRAINT school_years_branch_label_unique UNIQUE(branch_id, label);
    END IF;
END $$;

-- 6. Create unique index on (branch_id, label)
CREATE UNIQUE INDEX IF NOT EXISTS unique_year_per_branch
ON school_years(branch_id, label);

-- 7. Add year_id column to sections
ALTER TABLE sections
ADD COLUMN IF NOT EXISTS year_id INTEGER;

-- 8. Add foreign key from sections to school_years
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_sections_year'
    ) THEN
        ALTER TABLE sections
        ADD CONSTRAINT fk_sections_year
        FOREIGN KEY (year_id) REFERENCES school_years(year_id);
    END IF;
END $$;
