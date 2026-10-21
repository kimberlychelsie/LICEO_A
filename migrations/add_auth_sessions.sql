-- Server-verifiable authenticated sessions.
-- Run this migration before deploying code that requires auth_sessions.
-- It is additive and safe to rerun.

BEGIN;

CREATE TABLE IF NOT EXISTS public.auth_sessions (
    session_id_hash VARCHAR(64) PRIMARY KEY,
    user_id INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ NULL,
    CONSTRAINT auth_sessions_user_id_fkey
        FOREIGN KEY (user_id)
        REFERENCES public.users(user_id)
        ON DELETE CASCADE,
    CONSTRAINT auth_sessions_expiry_check
        CHECK (expires_at > created_at)
);

CREATE INDEX IF NOT EXISTS idx_auth_sessions_active_user
    ON public.auth_sessions (user_id, expires_at)
    WHERE revoked_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_auth_sessions_expires_at
    ON public.auth_sessions (expires_at);

CREATE INDEX IF NOT EXISTS idx_auth_sessions_revoked_at
    ON public.auth_sessions (revoked_at)
    WHERE revoked_at IS NOT NULL;

COMMIT;
