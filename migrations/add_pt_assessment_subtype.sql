-- Allow 'assessment' (PAR: A = Assessment / Achievement) as an activity grading subtype.
ALTER TABLE public.activities DROP CONSTRAINT IF EXISTS activities_grading_subtype_check;
ALTER TABLE public.activities
    ADD CONSTRAINT activities_grading_subtype_check CHECK (
        grading_subtype IS NULL OR grading_subtype IN (
            'activity', 'assignment', 'participation',
            'recitation', 'project', 'assessment', 'other'
        )
    );
