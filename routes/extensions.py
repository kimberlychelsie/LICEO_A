"""Shared Flask extensions to avoid circular imports."""
import os

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect


def _limiter_storage_uri() -> str:
    """Rate-limit storage: Redis in production, memory locally."""
    uri = (os.getenv("RATELIMIT_STORAGE_URI") or os.getenv("REDIS_URL") or "").strip()
    if uri:
        return uri
    return "memory://"


limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day"],
    storage_uri=_limiter_storage_uri(),
)

# Shared CSRF instance
csrf = CSRFProtect()