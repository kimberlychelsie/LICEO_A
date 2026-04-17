-- Run this in pgAdmin or psql to fix the permissions issue for the local developer user
-- This ensures 'liceo_db' can create and alter tables as needed for updates.

GRANT ALL PRIVILEGES ON DATABASE liceo_db TO liceo_db;
GRANT ALL ON SCHEMA public TO liceo_db;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO liceo_db;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO liceo_db;

-- If 'liceo_db' is not the owner of the schema:
ALTER SCHEMA public OWNER TO liceo_db;

-- If tables already exist, ensure the app user owns them to allow 'CREATE INDEX' etc.
REASSIGN OWNED BY postgres TO liceo_db; -- Run this if 'postgres' created them
-- OR specifically for schedules:
ALTER TABLE IF EXISTS public.schedules OWNER TO liceo_db;
ALTER SEQUENCE IF EXISTS public.schedules_id_seq OWNER TO liceo_db;
