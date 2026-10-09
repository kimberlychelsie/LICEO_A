-- READ-ONLY Railway preflight for latest enrollment workflow migrations.
-- Safe to run before migrations. This script performs metadata SELECTs only.
-- It does not create, alter, update, delete, or lock application data.

-- 1. Required base tables.
SELECT 'required_table' AS check_type,
       required.table_name,
       CASE WHEN t.table_name IS NULL THEN 'MISSING' ELSE 'OK' END AS status
FROM (VALUES
    ('enrollments'),
    ('student_accounts'),
    ('branches'),
    ('school_years'),
    ('new_student_enrollment_settings'),
    ('student_identity_reviews')
) AS required(table_name)
LEFT JOIN information_schema.tables t
  ON t.table_schema = 'public'
 AND t.table_name = required.table_name
ORDER BY required.table_name;

-- 2. Required enrollment columns for public submission, duplicate detection,
-- correction/resubmission, and Registrar decisions.
SELECT 'enrollment_column' AS check_type,
       required.column_name,
       COALESCE(c.data_type, 'MISSING') AS data_type,
       c.character_maximum_length,
       CASE WHEN c.column_name IS NULL THEN 'MISSING' ELSE 'OK' END AS status
FROM (VALUES
    ('enrollment_id'),
    ('branch_id'),
    ('status'),
    ('student_first_name'),
    ('student_middle_name'),
    ('student_last_name'),
    ('dob'),
    ('branch_enrollment_no'),
    ('lrn'),
    ('email'),
    ('guardian_email'),
    ('guardian_first_name'),
    ('guardian_middle_name'),
    ('guardian_last_name'),
    ('guardian_contact'),
    ('previous_school'),
    ('enroll_type'),
    ('enroll_date'),
    ('birthplace'),
    ('father_first_name'),
    ('father_middle_name'),
    ('father_last_name'),
    ('father_contact'),
    ('father_occupation'),
    ('mother_first_name'),
    ('mother_middle_name'),
    ('mother_last_name'),
    ('mother_contact'),
    ('mother_occupation'),
    ('remarks'),
    ('rejection_reason'),
    ('rejected_at'),
    ('year_id'),
    ('section_id'),
    ('shs_track')
) AS required(column_name)
LEFT JOIN information_schema.columns c
  ON c.table_schema = 'public'
 AND c.table_name = 'enrollments'
 AND c.column_name = required.column_name
ORDER BY required.column_name;

-- 3. Status column capacity and CHECK constraints.
SELECT 'enrollment_status_type' AS check_type,
       data_type,
       character_maximum_length,
       CASE
           WHEN character_maximum_length IS NULL OR character_maximum_length >= 20 THEN 'OK'
           ELSE 'TOO_SHORT'
       END AS status
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'enrollments'
  AND column_name = 'status';

SELECT 'enrollment_status_check' AS check_type,
       conname,
       pg_get_constraintdef(oid) AS constraint_def,
       CASE
           WHEN pg_get_constraintdef(oid) ILIKE '%correction_requested%' THEN 'OK'
           ELSE 'VERIFY_OR_UPDATE_BEFORE_MIGRATION'
       END AS status
FROM pg_constraint
WHERE conrelid = 'public.enrollments'::regclass
  AND contype = 'c'
  AND pg_get_constraintdef(oid) ILIKE '%status%';

-- 4. Duplicate branch/year enrollment numbers that would block uniqueness.
SELECT 'duplicate_branch_year_enrollment_no' AS check_type,
       branch_id,
       year_id,
       branch_enrollment_no,
       COUNT(*) AS duplicate_count
FROM public.enrollments
WHERE year_id IS NOT NULL
  AND branch_enrollment_no IS NOT NULL
GROUP BY branch_id, year_id, branch_enrollment_no
HAVING COUNT(*) > 1
ORDER BY branch_id, year_id, branch_enrollment_no;

-- 5. Existing identity-review table shape, if present.
SELECT 'student_identity_review_column' AS check_type,
       c.column_name,
       c.data_type,
       c.character_maximum_length,
       c.is_nullable
FROM information_schema.columns c
WHERE c.table_schema = 'public'
  AND c.table_name = 'student_identity_reviews'
ORDER BY c.ordinal_position;

SELECT 'student_identity_review_constraint' AS check_type,
       tc.constraint_name,
       tc.constraint_type
FROM information_schema.table_constraints tc
WHERE tc.table_schema = 'public'
  AND tc.table_name = 'student_identity_reviews'
ORDER BY tc.constraint_name;

-- 6. Current constraints/indexes relevant to latest enrollment workflow.
SELECT 'enrollment_constraint' AS check_type,
       conname,
       pg_get_constraintdef(oid) AS constraint_def
FROM pg_constraint
WHERE conrelid = 'public.enrollments'::regclass
  AND conname IN ('uq_enrollments_branch_no', 'uq_enrollments_branch_year_no', 'fk_enrollments_year')
ORDER BY conname;

SELECT 'relevant_index' AS check_type,
       schemaname,
       tablename,
       indexname,
       indexdef
FROM pg_indexes
WHERE schemaname = 'public'
  AND (
      tablename IN ('enrollments', 'student_accounts', 'student_identity_reviews')
      AND (
          indexname ILIKE '%identity%'
          OR indexname ILIKE '%branch_year_status%'
          OR indexname ILIKE '%branch_no%'
          OR indexname ILIKE '%enrollment%'
      )
  )
ORDER BY tablename, indexname;
