import hashlib
import logging
import secrets

from flask import current_app, flash, redirect, request, session, url_for

from db import get_db_connection


logger = logging.getLogger(__name__)

AUTH_SESSION_KEY = "_auth_session_id"
DEFAULT_ABSOLUTE_LIFETIME_SECONDS = 24 * 60 * 60
DEFAULT_IDLE_TIMEOUT_SECONDS = 60 * 60


def _hash_session_id(session_id):
    return hashlib.sha256(session_id.encode("utf-8")).hexdigest()


def issue_auth_session(cursor, user_id, absolute_lifetime_seconds=None):
    """Create a server-verifiable login session and place its opaque ID in Flask's cookie."""
    lifetime = int(
        absolute_lifetime_seconds
        or current_app.config.get(
            "AUTH_SESSION_ABSOLUTE_LIFETIME_SECONDS",
            DEFAULT_ABSOLUTE_LIFETIME_SECONDS,
        )
    )
    raw_session_id = secrets.token_urlsafe(32)
    cursor.execute(
        """
        INSERT INTO auth_sessions (
            session_id_hash, user_id, created_at, last_seen_at, expires_at
        )
        VALUES (%s, %s, NOW(), NOW(), NOW() + (%s * INTERVAL '1 second'))
        """,
        (_hash_session_id(raw_session_id), user_id, lifetime),
    )
    session[AUTH_SESSION_KEY] = raw_session_id
    return raw_session_id


def touch_auth_session(cursor, raw_session_id, user_id, idle_timeout_seconds):
    """Validate and refresh one active session without extending its absolute expiry."""
    if not raw_session_id or not user_id:
        return False

    cursor.execute(
        """
        UPDATE auth_sessions
        SET last_seen_at = NOW()
        WHERE session_id_hash = %s
          AND user_id = %s
          AND revoked_at IS NULL
          AND expires_at > NOW()
          AND last_seen_at >= NOW() - (%s * INTERVAL '1 second')
        RETURNING session_id_hash
        """,
        (
            _hash_session_id(raw_session_id),
            user_id,
            int(idle_timeout_seconds),
        ),
    )
    return cursor.fetchone() is not None


def revoke_auth_session(cursor, raw_session_id, user_id):
    """Revoke one login session. The operation is idempotent."""
    if not raw_session_id or not user_id:
        return True

    cursor.execute(
        """
        UPDATE auth_sessions
        SET revoked_at = COALESCE(revoked_at, NOW())
        WHERE session_id_hash = %s
          AND user_id = %s
        """,
        (_hash_session_id(raw_session_id), user_id),
    )
    return True


def revoke_current_auth_session(db_factory=None):
    """Revoke the current browser session using the shared PostgreSQL registry."""
    raw_session_id = session.get(AUTH_SESSION_KEY)
    user_id = session.get("user_id")
    if not raw_session_id or not user_id:
        return True

    factory = db_factory or get_db_connection
    db = None
    cursor = None
    try:
        db = factory()
        cursor = db.cursor()
        revoke_auth_session(cursor, raw_session_id, user_id)
        db.commit()
        return True
    except Exception:
        if db:
            db.rollback()
        logger.exception("Unable to revoke the current authenticated session")
        return False
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


def enforce_active_auth_session(
    db_factory=None,
    idle_timeout_seconds=DEFAULT_IDLE_TIMEOUT_SECONDS,
    login_endpoint="auth.login",
):
    """Fail closed unless the authenticated cookie maps to an active server session."""
    user_id = session.get("user_id")
    if not user_id:
        if session.get("role"):
            return _reject_session(login_endpoint)
        return None

    raw_session_id = session.get(AUTH_SESSION_KEY)
    if not raw_session_id:
        return _reject_session(login_endpoint)

    factory = db_factory or get_db_connection
    db = None
    cursor = None
    try:
        db = factory()
        cursor = db.cursor()
        is_active = touch_auth_session(
            cursor,
            raw_session_id,
            user_id,
            idle_timeout_seconds,
        )
        db.commit()
    except Exception:
        if db:
            db.rollback()
        logger.exception("Authenticated session validation is unavailable")
        return "Authentication service temporarily unavailable.", 503
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()

    if not is_active:
        return _reject_session(login_endpoint)
    return None


def _reject_session(login_endpoint):
    session.clear()
    flash("Your session is no longer valid. Please sign in again.", "warning")
    if request.endpoint == login_endpoint:
        return None
    return redirect(url_for(login_endpoint))
