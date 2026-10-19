-- Additive event history for the existing grade approval workflow.
-- This migration is safe to rerun and does not rewrite legacy requests.

BEGIN;

CREATE TABLE IF NOT EXISTS public.grade_submission_history (
    event_id BIGSERIAL PRIMARY KEY,
    request_id INTEGER NOT NULL,
    event_type VARCHAR(40) NOT NULL,
    from_status VARCHAR(30),
    to_status VARCHAR(30) NOT NULL,
    actor_user_id INTEGER,
    actor_role VARCHAR(30) NOT NULL,
    remarks TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT grade_submission_history_request_fkey
        FOREIGN KEY (request_id)
        REFERENCES public.grade_submission_requests(id)
        ON DELETE CASCADE,
    CONSTRAINT grade_submission_history_actor_fkey
        FOREIGN KEY (actor_user_id)
        REFERENCES public.users(user_id)
        ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_grade_submission_history_request_created
    ON public.grade_submission_history (request_id, created_at, event_id);

COMMIT;
