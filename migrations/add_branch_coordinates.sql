-- Migration to add latitude and longitude to branches table
ALTER TABLE branches ADD COLUMN IF NOT EXISTS latitude NUMERIC(10, 7);
ALTER TABLE branches ADD COLUMN IF NOT EXISTS longitude NUMERIC(10, 7);
