-- Fix sections table: add missing columns
ALTER TABLE public.sections
    ADD COLUMN IF NOT EXISTS section_id     INTEGER,
    ADD COLUMN IF NOT EXISTS section_name   CHARACTER VARYING(100),
    ADD COLUMN IF NOT EXISTS school_year    CHARACTER VARYING(20),
    ADD COLUMN IF NOT EXISTS teacher_id     INTEGER,
    ADD COLUMN IF NOT EXISTS grade_level_id INTEGER;

-- Sync section_id from id (for backward compat)
UPDATE public.sections SET section_id = id WHERE section_id IS NULL;

-- Populate grade_level_id from grade_level text
UPDATE public.sections s
SET grade_level_id = g.id
FROM public.grade_levels g
WHERE g.name = s.grade_level AND s.grade_level_id IS NULL;

-- Create subjects table
CREATE TABLE IF NOT EXISTS public.subjects (
    subject_id  SERIAL PRIMARY KEY,
    name        CHARACTER VARYING(100) NOT NULL UNIQUE
);

-- Create section_teachers table
CREATE TABLE IF NOT EXISTS public.section_teachers (
    id          SERIAL PRIMARY KEY,
    section_id  INTEGER,
    teacher_id  INTEGER,
    subject_id  INTEGER
);

-- Create teacher_announcements table
CREATE TABLE IF NOT EXISTS public.teacher_announcements (
    announcement_id SERIAL PRIMARY KEY,
    teacher_user_id INTEGER,
    branch_id       INTEGER,
    grade_level     CHARACTER VARYING(50),
    title           CHARACTER VARYING(200) NOT NULL,
    body            TEXT,
    created_at      TIMESTAMP WITHOUT TIME ZONE DEFAULT now()
);

-- Fix users table
ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS full_name    CHARACTER VARYING(150),
    ADD COLUMN IF NOT EXISTS gender       CHARACTER VARYING(20),
    ADD COLUMN IF NOT EXISTS grade_level  CHARACTER VARYING(50),
    ADD COLUMN IF NOT EXISTS email        CHARACTER VARYING(255),
    ADD COLUMN IF NOT EXISTS require_password_change BOOLEAN DEFAULT FALSE;
