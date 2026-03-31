-- Adds grading year_id support so teacher posting/upsert works with ON CONFLICT including year_id,
-- and recomputation filters using sections.year_id.
--
-- Safe to run multiple times (best-effort checks + backfills).

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_name='posted_grades' AND column_name='year_id'
  ) THEN
    ALTER TABLE posted_grades ADD COLUMN year_id INTEGER;
  END IF;
END $$;

-- Backfill sections.year_id from enrollments.year_id (best-effort).
UPDATE sections s
SET year_id = sub.year_id
FROM (
  SELECT section_id, MAX(year_id) AS year_id
  FROM enrollments
  WHERE year_id IS NOT NULL AND year_id <> 0
  GROUP BY section_id
) sub
WHERE s.section_id = sub.section_id
  AND (s.year_id IS NULL OR s.year_id = 0);

-- Backfill posted_grades.year_id (best-effort, prefer enrollments.year_id).
UPDATE posted_grades pg
SET year_id = e.year_id
FROM enrollments e
WHERE pg.enrollment_id = e.enrollment_id
  AND (pg.year_id IS NULL OR pg.year_id = 0)
  AND e.year_id IS NOT NULL AND e.year_id <> 0;

-- Fallback: use sections.year_id if still null.
UPDATE posted_grades pg
SET year_id = s.year_id
FROM sections s
WHERE pg.section_id = s.section_id
  AND (pg.year_id IS NULL OR pg.year_id = 0)
  AND s.year_id IS NOT NULL AND s.year_id <> 0;

-- Drop the old uniqueness (without year_id) so different school years can co-exist.
ALTER TABLE posted_grades
DROP CONSTRAINT IF EXISTS posted_grades_enrollment_id_subject_id_grading_period_key;

-- Create a unique index matching routes/teacher.py ON CONFLICT target.
CREATE UNIQUE INDEX IF NOT EXISTS posted_grades_uniq_enrollment_subject_period_year
ON posted_grades (enrollment_id, subject_id, grading_period, year_id);

