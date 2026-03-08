-- NOTE: Wala pang branch_id ang grade_levels table sa current schema ninyo kaya magkaka-error kung direct ninyong i-apply ang constraint na may branch_id. Kailangan nating i-add muna ang branch_id column.

-- 1. I-add muna ang branch_id column (Optional: if the table doesn't have it yet)
ALTER TABLE public.grade_levels ADD COLUMN IF NOT EXISTS branch_id integer;

-- 2. I-drop ang lumang single-column unique constraint sa name
ALTER TABLE public.grade_levels DROP CONSTRAINT IF EXISTS grade_levels_name_key;

-- 3. I-add ang bagong composite unique constraint:
ALTER TABLE public.grade_levels ADD CONSTRAINT grade_levels_name_branch_key UNIQUE (name, branch_id);
