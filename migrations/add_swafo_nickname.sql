BEGIN;

ALTER TABLE public.swafo_records
    ADD COLUMN IF NOT EXISTS nickname VARCHAR(50);

COMMIT;
