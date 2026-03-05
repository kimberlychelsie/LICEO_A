-- Add missing columns to users table
ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS full_name character varying(150),
    ADD COLUMN IF NOT EXISTS gender character varying(20),
    ADD COLUMN IF NOT EXISTS grade_level character varying(50),
    ADD COLUMN IF NOT EXISTS email character varying(255);
