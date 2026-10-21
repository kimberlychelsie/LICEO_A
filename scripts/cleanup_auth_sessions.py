"""Bounded auth-session retention command for cron/scheduler execution."""

import argparse
import os

from utils.auth_sessions import cleanup_auth_sessions


def _env_int(name, default):
    value = os.getenv(name)
    return int(value) if value not in (None, "") else default


def main():
    parser = argparse.ArgumentParser(description="Delete old expired/revoked sessions.")
    parser.add_argument(
        "--retention-days",
        type=int,
        default=_env_int("AUTH_SESSION_RETENTION_DAYS", 7),
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=_env_int("AUTH_SESSION_CLEANUP_BATCH_SIZE", 1000),
    )
    parser.add_argument(
        "--max-batches",
        type=int,
        default=_env_int("AUTH_SESSION_CLEANUP_MAX_BATCHES", 100),
    )
    args = parser.parse_args()
    result = cleanup_auth_sessions(
        retention_days=args.retention_days,
        batch_size=args.batch_size,
        max_batches=args.max_batches,
    )
    print(
        "Auth-session cleanup complete: "
        f"deleted={result['deleted']} batches={result['batches']}"
    )


if __name__ == "__main__":
    main()
