BEGIN;

DO $$
DECLARE
    constraint_def TEXT;
BEGIN
    SELECT pg_get_constraintdef(c.oid)
      INTO constraint_def
    FROM pg_constraint c
    JOIN pg_class t ON t.oid=c.conrelid
    JOIN pg_namespace n ON n.oid=t.relnamespace
    WHERE n.nspname='public' AND t.relname='enrollments' AND c.contype='c'
      AND pg_get_constraintdef(c.oid) ILIKE '%status%'
    LIMIT 1;

    IF constraint_def IS NOT NULL AND constraint_def NOT ILIKE '%transferred_out%' THEN
        RAISE EXCEPTION 'Manual review required: enrollments.status CHECK constraint must allow transferred_out. Constraint: %', constraint_def;
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS public.student_transfer_requests (
    transfer_id SERIAL PRIMARY KEY,
    source_enrollment_id INTEGER NOT NULL REFERENCES public.enrollments(enrollment_id),
    destination_enrollment_id INTEGER REFERENCES public.enrollments(enrollment_id),
    source_branch_id INTEGER NOT NULL REFERENCES public.branches(branch_id),
    destination_branch_id INTEGER NOT NULL REFERENCES public.branches(branch_id),
    source_year_id INTEGER NOT NULL REFERENCES public.school_years(year_id),
    destination_year_id INTEGER NOT NULL REFERENCES public.school_years(year_id),
    requested_grade_level VARCHAR(100) NOT NULL,
    destination_section_id INTEGER REFERENCES public.sections(section_id),
    effective_term VARCHAR(20) NOT NULL,
    reason TEXT NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'pending_destination',
    decision_reason TEXT,
    requested_by INTEGER REFERENCES public.users(user_id) ON DELETE SET NULL,
    processed_by INTEGER REFERENCES public.users(user_id) ON DELETE SET NULL,
    requested_at TIMESTAMP NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_transfer_different_branches CHECK (source_branch_id <> destination_branch_id),
    CONSTRAINT chk_transfer_term CHECK (
        effective_term ~ '^[1-9][0-9]*(st|nd|rd|th)$'
    ),
    CONSTRAINT chk_transfer_status CHECK (
        status IN ('pending_destination', 'approved', 'rejected', 'cancelled')
    )
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_student_transfer_open_source
    ON public.student_transfer_requests (source_enrollment_id)
    WHERE status = 'pending_destination';

CREATE INDEX IF NOT EXISTS idx_student_transfers_destination_status
    ON public.student_transfer_requests (destination_branch_id, status, requested_at DESC);

CREATE INDEX IF NOT EXISTS idx_student_transfers_source_status
    ON public.student_transfer_requests (source_branch_id, status, requested_at DESC);

CREATE TABLE IF NOT EXISTS public.student_transfer_history (
    history_id SERIAL PRIMARY KEY,
    transfer_id INTEGER NOT NULL REFERENCES public.student_transfer_requests(transfer_id) ON DELETE CASCADE,
    action VARCHAR(40) NOT NULL,
    old_status VARCHAR(30),
    new_status VARCHAR(30) NOT NULL,
    notes TEXT,
    acted_by INTEGER REFERENCES public.users(user_id) ON DELETE SET NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_student_transfer_history_transfer
    ON public.student_transfer_history (transfer_id, created_at);

COMMIT;
