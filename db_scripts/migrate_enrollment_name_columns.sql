-- Migration: Split combined name columns into first/middle/last name parts
-- Run this on Railway PostgreSQL before deploying
-- Date: 2026-07-22

-- Step 1: Add new split-name columns
ALTER TABLE enrollments
ADD COLUMN IF NOT EXISTS student_first_name  VARCHAR(100),
ADD COLUMN IF NOT EXISTS student_middle_name VARCHAR(100),
ADD COLUMN IF NOT EXISTS student_last_name   VARCHAR(100),

ADD COLUMN IF NOT EXISTS father_first_name   VARCHAR(100),
ADD COLUMN IF NOT EXISTS father_middle_name  VARCHAR(100),
ADD COLUMN IF NOT EXISTS father_last_name    VARCHAR(100),

ADD COLUMN IF NOT EXISTS mother_first_name   VARCHAR(100),
ADD COLUMN IF NOT EXISTS mother_middle_name  VARCHAR(100),
ADD COLUMN IF NOT EXISTS mother_last_name    VARCHAR(100),

ADD COLUMN IF NOT EXISTS guardian_first_name  VARCHAR(100),
ADD COLUMN IF NOT EXISTS guardian_middle_name VARCHAR(100),
ADD COLUMN IF NOT EXISTS guardian_last_name   VARCHAR(100);

-- Step 2: Drop old combined name columns
ALTER TABLE enrollments
DROP COLUMN IF EXISTS student_name,
DROP COLUMN IF EXISTS father_name,
DROP COLUMN IF EXISTS mother_name,
DROP COLUMN IF EXISTS guardian_name;
