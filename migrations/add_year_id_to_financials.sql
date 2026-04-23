-- Migration: Add year_id to billing and payments tables
-- Created: 2026-04-23

-- 1. Add year_id to billing
ALTER TABLE public.billing ADD COLUMN IF NOT EXISTS year_id INTEGER;

-- 2. Add year_id to payments
ALTER TABLE public.payments ADD COLUMN IF NOT EXISTS year_id INTEGER;

-- 3. Backfill billing year_id from enrollments
UPDATE public.billing b
SET year_id = e.year_id
FROM public.enrollments e
WHERE b.enrollment_id = e.enrollment_id
  AND b.year_id IS NULL;

-- 4. Backfill payments year_id from billing (which was just backfilled)
UPDATE public.payments p
SET year_id = b.year_id
FROM public.billing b
WHERE p.bill_id = b.bill_id
  AND p.year_id IS NULL;

-- 5. Add Foreign Key constraints (optional but recommended)
-- ALTER TABLE public.billing ADD CONSTRAINT fk_billing_year FOREIGN KEY (year_id) REFERENCES school_years(year_id);
-- ALTER TABLE public.payments ADD CONSTRAINT fk_payments_year FOREIGN KEY (year_id) REFERENCES school_years(year_id);
