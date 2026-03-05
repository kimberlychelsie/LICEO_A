-- Add branch_code column to branches table
ALTER TABLE public.branches
    ADD COLUMN IF NOT EXISTS branch_code character varying(20);

-- Add unique constraint on branch_code (allow NULL for existing rows)
CREATE UNIQUE INDEX IF NOT EXISTS branches_branch_code_key
    ON public.branches (branch_code)
    WHERE branch_code IS NOT NULL;
