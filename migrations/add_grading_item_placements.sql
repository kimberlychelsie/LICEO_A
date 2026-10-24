-- Explicit class-record placement for portal and manual assessment items.
-- Additive, idempotent, and safe to rerun. Apply before deploying the code.
-- Existing quizzes remain WW and existing activities remain PT. Existing
-- non-quiz exams stay legacy until a teacher configures the new ST&E slots.

BEGIN;

ALTER TABLE public.exams
    ADD COLUMN IF NOT EXISTS grading_slot VARCHAR(32),
    ADD COLUMN IF NOT EXISTS class_record_max_score NUMERIC(10,2);

ALTER TABLE public.activities
    ADD COLUMN IF NOT EXISTS grading_component VARCHAR(12),
    ADD COLUMN IF NOT EXISTS grading_subtype VARCHAR(32);

UPDATE public.exams
SET grading_slot = 'ww_quiz'
WHERE grading_slot IS NULL
  AND exam_type IN ('quiz', 'monthly_exam');

UPDATE public.exams e
SET class_record_max_score = totals.total_points
FROM (
    SELECT exam_id, MAX(total_points) AS total_points
    FROM public.exam_results
    WHERE total_points > 0
    GROUP BY exam_id
) totals
WHERE e.exam_id = totals.exam_id
  AND e.class_record_max_score IS NULL;

UPDATE public.activities
SET grading_component = 'pt'
WHERE grading_component IS NULL;

UPDATE public.activities
SET grading_subtype = CASE LOWER(COALESCE(category, ''))
    WHEN 'assignment' THEN 'assignment'
    WHEN 'project' THEN 'project'
    WHEN 'performance task' THEN 'activity'
    ELSE 'activity'
END
WHERE grading_subtype IS NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'exams_grading_slot_check'
          AND conrelid = 'public.exams'::regclass
    ) THEN
        ALTER TABLE public.exams
            ADD CONSTRAINT exams_grading_slot_check CHECK (
                grading_slot IS NULL OR grading_slot IN (
                    'ww_quiz', 'ww_activity', 'ww_assignment',
                    'ste_st1', 'ste_st2', 'ste_term_exam', 'excluded'
                )
            );
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'exams_class_record_max_score_check'
          AND conrelid = 'public.exams'::regclass
    ) THEN
        ALTER TABLE public.exams
            ADD CONSTRAINT exams_class_record_max_score_check CHECK (
                class_record_max_score IS NULL OR class_record_max_score > 0
            );
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'activities_grading_component_check'
          AND conrelid = 'public.activities'::regclass
    ) THEN
        ALTER TABLE public.activities
            ADD CONSTRAINT activities_grading_component_check CHECK (
                grading_component IN ('ww', 'pt', 'excluded')
            );
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'activities_grading_subtype_check'
          AND conrelid = 'public.activities'::regclass
    ) THEN
        ALTER TABLE public.activities
            ADD CONSTRAINT activities_grading_subtype_check CHECK (
                grading_subtype IS NULL OR grading_subtype IN (
                    'activity', 'assignment', 'participation',
                    'recitation', 'project', 'other'
                )
            );
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_exams_grading_slot
    ON public.exams
       (branch_id, year_id, teacher_id, section_id, subject_id, grading_period, grading_slot);

CREATE INDEX IF NOT EXISTS idx_activities_grading_component
    ON public.activities
       (branch_id, year_id, teacher_id, section_id, subject_id, grading_period, grading_component);

CREATE UNIQUE INDEX IF NOT EXISTS uq_exams_official_ste_slot
    ON public.exams (teacher_id, section_id, subject_id, grading_period, year_id, grading_slot)
    WHERE grading_slot IN ('ste_st1', 'ste_st2', 'ste_term_exam')
      AND COALESCE(is_archived, FALSE) = FALSE;

COMMIT;
