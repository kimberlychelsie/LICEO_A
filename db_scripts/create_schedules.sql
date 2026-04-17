-- Run this script to manually create the 'schedules' table
-- This table is required for the new Schedules and LMS features.

CREATE TABLE IF NOT EXISTS public.schedules (
    schedule_id     SERIAL PRIMARY KEY,
    subject_id      integer NOT NULL REFERENCES public.subjects(subject_id) ON DELETE CASCADE,
    section_id      integer NOT NULL REFERENCES public.sections(section_id) ON DELETE CASCADE,
    teacher_id      integer NOT NULL REFERENCES public.users(user_id) ON DELETE CASCADE,
    day_of_week     character varying(20) NOT NULL,
    start_time      time without time zone NOT NULL,
    end_time        time without time zone NOT NULL,
    room            character varying(50),
    year_id         integer NOT NULL REFERENCES public.school_years(year_id) ON DELETE CASCADE,
    branch_id       integer NOT NULL REFERENCES public.branches(branch_id) ON DELETE CASCADE,
    created_at      timestamp NOT NULL DEFAULT now()
);

-- Optimization: Add indexes for faster schedule lookups
CREATE INDEX IF NOT EXISTS idx_schedules_teacher ON public.schedules (teacher_id);
CREATE INDEX IF NOT EXISTS idx_schedules_section ON public.schedules (section_id);
CREATE INDEX IF NOT EXISTS idx_schedules_branch  ON public.schedules (branch_id);
CREATE INDEX IF NOT EXISTS idx_schedules_year    ON public.schedules (year_id);

-- Verify after creation
ALTER TABLE public.schedules OWNER TO liceo_db1;
ALTER SEQUENCE public.schedules_id_seq OWNER TO liceo_db1;

DO $$ 
BEGIN 
    RAISE NOTICE 'Schedules table and indexes created and ownership transferred to liceo_db1.'; 
END $$;
