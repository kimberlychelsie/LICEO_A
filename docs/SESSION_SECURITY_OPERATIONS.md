# Session security operations

## Daily retention cleanup

Run the cleanup once per day as a separate Railway cron service or external
scheduler. Do not run it as a permanent Flask background thread.

```text
python -m scripts.cleanup_auth_sessions
```

The cron service must reference the same database variables as the web service.
Recommended schedule: `17 3 * * *` (once daily at 03:17 UTC). Staggering away
from midnight reduces the chance of competing with other daily jobs.
Set `LICEO_RUN_STARTUP_MIGRATIONS=false`; schema changes belong to the separate
migration-first deployment step, not the retention command.

Defaults:

- `AUTH_SESSION_RETENTION_DAYS=7`
- `AUTH_SESSION_CLEANUP_BATCH_SIZE=1000`
- `AUTH_SESSION_CLEANUP_MAX_BATCHES=100`

Each batch commits separately and selects eligible rows with `FOR UPDATE SKIP
LOCKED`. A row is eligible seven days after revocation, or seven days after
expiration when it was never revoked. Active, unexpired sessions never match.
Overlapping cleanup invocations can safely skip rows locked by another worker.

The command prints only deletion and batch counts. It never prints tokens or
database credentials. A nonzero exit means the scheduler should alert an
operator and retry at its next scheduled run.

## Migration-first deployment

1. Back up the database using the platform's normal backup mechanism.
2. Confirm the target service/database identity without displaying credentials.
3. Apply `migrations/add_auth_sessions.sql` before deploying application code.
4. Verify the table, foreign key, check constraint, and three indexes exist.
5. Deploy the web service with the 300-second idle timeout configuration.
6. Deploy the separate daily cleanup service using the command above.
7. Run login, logout/replayed-cookie, normal idle, and active-assessment smoke tests.
8. Monitor authentication errors, cleanup counts, database latency, and locks.

Rollback is non-destructive: roll the web service back to the previous release
and disable the cron service. Leave `auth_sessions` and its indexes in place;
they are additive and removing them would discard security audit state. Restore
from backup only for an independently confirmed database incident.

## PostgreSQL verification

`tests/test_session_security_postgres.py` is deliberately disabled unless
`SESSION_SECURITY_TEST_DB_NAME` starts with `liceo_session_test_`. Create a
disposable database with that prefix, apply
`tests/fixtures/session_security_schema.sql` followed by
`migrations/add_auth_sessions.sql`, set the variable, and run:

```text
python -X utf8 -m unittest tests.test_session_security_postgres -v
```

Drop the disposable database after the run. Never point this test at a shared,
development, staging, or production database; its setup truncates its fixture
tables between cases.
