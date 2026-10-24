-- Teacher-owned WW/PT/QA weights per class-record term.
-- Additive, idempotent, and safe to rerun. Apply before deploying the feature.
-- This migration intentionally does not create or require Branch Admin categories.

BEGIN;

CREATE TABLE IF NOT EXISTS public.teacher_grading_weights (
    weight_id SERIAL PRIMARY KEY,
    teacher_id INTEGER NOT NULL REFERENCES public.users(user_id) ON DELETE CASCADE,
    branch_id INTEGER NOT NULL REFERENCES public.branches(branch_id) ON DELETE CASCADE,
    year_id INTEGER NOT NULL REFERENCES public.school_years(year_id) ON DELETE CASCADE,
    section_id INTEGER NOT NULL REFERENCES public.sections(section_id) ON DELETE CASCADE,
    subject_id INTEGER NOT NULL REFERENCES public.subjects(subject_id) ON DELETE CASCADE,
    grading_period VARCHAR(20) NOT NULL,
    ww_pct NUMERIC(5,2) NOT NULL,
    pt_pct NUMERIC(5,2) NOT NULL,
    qa_pct NUMERIC(5,2) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT teacher_grading_weights_period_check CHECK (
        grading_period IN ('1st', '2nd', '3rd')
    ),
    CONSTRAINT teacher_grading_weights_ranges_check CHECK (
        ww_pct BETWEEN 0 AND 100
        AND pt_pct BETWEEN 0 AND 100
        AND qa_pct BETWEEN 0 AND 100
    ),
    CONSTRAINT teacher_grading_weights_total_check CHECK (
        ww_pct + pt_pct + qa_pct = 100
    ),
    CONSTRAINT teacher_grading_weights_scope_key UNIQUE (
        teacher_id, section_id, subject_id, grading_period, year_id
    )
);

CREATE INDEX IF NOT EXISTS idx_teacher_grading_weights_scope
    ON public.teacher_grading_weights
       (branch_id, year_id, teacher_id, section_id, subject_id, grading_period);

-- Preserve top-level weights when this replaces an already-installed version of
-- the former admin-category feature. Fresh installations simply skip this block.
DO $$
BEGIN
    IF to_regclass('public.grading_categories') IS NOT NULL
       AND EXISTS (
           SELECT 1 FROM information_schema.columns
           WHERE table_schema='public' AND table_name='section_teachers'
             AND column_name='grading_category_id'
       ) THEN
        EXECUTE $copy$
            INSERT INTO public.teacher_grading_weights (
                teacher_id, branch_id, year_id, section_id, subject_id,
                grading_period, ww_pct, pt_pct, qa_pct
            )
            SELECT st.teacher_id, sec.branch_id, st.year_id, st.section_id, st.subject_id,
                   periods.period_name, gc.ww_pct, gc.pt_pct, gc.qa_pct
            FROM public.section_teachers st
            JOIN public.sections sec ON sec.section_id=st.section_id
            JOIN public.grading_categories gc ON gc.category_id=st.grading_category_id
            CROSS JOIN (VALUES ('1st'), ('2nd'), ('3rd')) AS periods(period_name)
            WHERE st.teacher_id IS NOT NULL
            ON CONFLICT (teacher_id, section_id, subject_id, grading_period, year_id)
            DO NOTHING
        $copy$;
    END IF;
END $$;

COMMIT;
