-- Dynamic grading categories and teacher component distributions.
-- Additive, idempotent, and safe to rerun. Apply before deploying the feature.

BEGIN;

CREATE TABLE IF NOT EXISTS public.grading_categories (
    category_id SERIAL PRIMARY KEY,
    branch_id INTEGER NOT NULL REFERENCES public.branches(branch_id) ON DELETE CASCADE,
    year_id INTEGER NOT NULL REFERENCES public.school_years(year_id) ON DELETE CASCADE,
    code VARCHAR(80) NOT NULL,
    name VARCHAR(120) NOT NULL,
    ww_pct NUMERIC(5,2) NOT NULL,
    pt_pct NUMERIC(5,2) NOT NULL,
    qa_pct NUMERIC(5,2) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT grading_categories_weights_check CHECK (
        ww_pct BETWEEN 0 AND 100
        AND pt_pct BETWEEN 0 AND 100
        AND qa_pct BETWEEN 0 AND 100
        AND ww_pct + pt_pct + qa_pct = 100
    ),
    CONSTRAINT grading_categories_scope_code_key UNIQUE (branch_id, year_id, code),
    CONSTRAINT grading_categories_scope_name_key UNIQUE (branch_id, year_id, name)
);

ALTER TABLE public.section_teachers
    ADD COLUMN IF NOT EXISTS grading_category_id INTEGER;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'section_teachers_grading_category_id_fkey'
          AND conrelid = 'public.section_teachers'::regclass
    ) THEN
        ALTER TABLE public.section_teachers
            ADD CONSTRAINT section_teachers_grading_category_id_fkey
            FOREIGN KEY (grading_category_id)
            REFERENCES public.grading_categories(category_id)
            ON DELETE RESTRICT;
    END IF;
END $$;

INSERT INTO public.grading_categories
    (branch_id, year_id, code, name, ww_pct, pt_pct, qa_pct)
SELECT sy.branch_id, sy.year_id, defaults.code, defaults.name,
       defaults.ww_pct, defaults.pt_pct, defaults.qa_pct
FROM public.school_years sy
CROSS JOIN (VALUES
    ('language', 'Language / Values', 30.00, 50.00, 20.00),
    ('science_math', 'Science / Math', 40.00, 40.00, 20.00),
    ('skills', 'Skills / Technical', 20.00, 60.00, 20.00)
) AS defaults(code, name, ww_pct, pt_pct, qa_pct)
ON CONFLICT (branch_id, year_id, code) DO NOTHING;

UPDATE public.section_teachers st
SET grading_category_id = gc.category_id
FROM public.sections sec
JOIN public.subjects sub ON TRUE
JOIN public.grading_categories gc
  ON gc.branch_id = sec.branch_id
 AND gc.year_id = sec.year_id
 AND gc.code = COALESCE(NULLIF(sub.deped_category, ''), 'language')
WHERE st.section_id = sec.section_id
  AND st.subject_id = sub.subject_id
  AND st.grading_category_id IS NULL;

CREATE INDEX IF NOT EXISTS idx_section_teachers_grading_category
    ON public.section_teachers (grading_category_id);

CREATE TABLE IF NOT EXISTS public.teacher_component_distributions (
    distribution_id SERIAL PRIMARY KEY,
    teacher_id INTEGER NOT NULL REFERENCES public.users(user_id) ON DELETE CASCADE,
    branch_id INTEGER NOT NULL REFERENCES public.branches(branch_id) ON DELETE CASCADE,
    year_id INTEGER NOT NULL REFERENCES public.school_years(year_id) ON DELETE CASCADE,
    section_id INTEGER NOT NULL REFERENCES public.sections(section_id) ON DELETE CASCADE,
    subject_id INTEGER NOT NULL REFERENCES public.subjects(subject_id) ON DELETE CASCADE,
    grading_period VARCHAR(20) NOT NULL,
    ww_quiz_pct NUMERIC(5,2) NOT NULL DEFAULT 50,
    ww_monthly_exam_pct NUMERIC(5,2) NOT NULL DEFAULT 50,
    pt_activity_pct NUMERIC(5,2) NOT NULL DEFAULT 34,
    pt_participation_pct NUMERIC(5,2) NOT NULL DEFAULT 33,
    pt_attendance_pct NUMERIC(5,2) NOT NULL DEFAULT 33,
    qa_periodical_exam_pct NUMERIC(5,2) NOT NULL DEFAULT 100,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT teacher_component_distributions_ranges_check CHECK (
        ww_quiz_pct BETWEEN 0 AND 100
        AND ww_monthly_exam_pct BETWEEN 0 AND 100
        AND pt_activity_pct BETWEEN 0 AND 100
        AND pt_participation_pct BETWEEN 0 AND 100
        AND pt_attendance_pct BETWEEN 0 AND 100
        AND qa_periodical_exam_pct BETWEEN 0 AND 100
    ),
    CONSTRAINT teacher_component_distributions_ww_check CHECK (
        ww_quiz_pct + ww_monthly_exam_pct = 100
    ),
    CONSTRAINT teacher_component_distributions_pt_check CHECK (
        pt_activity_pct + pt_participation_pct + pt_attendance_pct = 100
    ),
    CONSTRAINT teacher_component_distributions_qa_check CHECK (
        qa_periodical_exam_pct = 100
    ),
    CONSTRAINT teacher_component_distributions_scope_key UNIQUE (
        teacher_id, section_id, subject_id, grading_period, year_id
    )
);

COMMIT;
