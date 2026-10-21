import unittest

from utils.auth_sessions import cleanup_auth_sessions


class FakeConnection:
    def __init__(self, batch_results):
        self.batch_results = list(batch_results)
        self.executions = []
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed = True


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection
        self.current = []
        self.closed = False

    def execute(self, sql, params):
        self.connection.executions.append((" ".join(sql.split()), params))
        self.current = self.connection.batch_results.pop(0)

    def fetchall(self):
        return self.current

    def close(self):
        self.closed = True


class AuthSessionCleanupTests(unittest.TestCase):
    def test_cleanup_is_bounded_and_commits_each_batch(self):
        connection = FakeConnection([
            [("old-a",), ("old-b",)],
            [("old-c",)],
        ])
        result = cleanup_auth_sessions(
            db_factory=lambda: connection,
            retention_days=7,
            batch_size=2,
            max_batches=5,
        )
        self.assertEqual(result, {"deleted": 3, "batches": 2})
        self.assertEqual(connection.commits, 2)
        self.assertTrue(connection.closed)

    def test_predicate_never_selects_active_sessions(self):
        connection = FakeConnection([[]])
        cleanup_auth_sessions(db_factory=lambda: connection)
        sql, params = connection.executions[0]
        self.assertIn("revoked_at IS NOT NULL", sql)
        self.assertIn("revoked_at IS NULL AND expires_at <", sql)
        self.assertNotIn("last_seen_at", sql)
        self.assertEqual(params, (7, 7, 1000))

    def test_overlapping_workers_use_skip_locked(self):
        connection = FakeConnection([[]])
        cleanup_auth_sessions(db_factory=lambda: connection)
        sql, _ = connection.executions[0]
        self.assertIn("FOR UPDATE SKIP LOCKED", sql)
        self.assertIn("LIMIT %s", sql)

    def test_invalid_limits_fail_before_connecting(self):
        def unexpected_connection():
            self.fail("invalid configuration must not connect")

        for kwargs in (
            {"retention_days": -1},
            {"batch_size": 0},
            {"batch_size": 10001},
            {"max_batches": 0},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                cleanup_auth_sessions(db_factory=unexpected_connection, **kwargs)


if __name__ == "__main__":
    unittest.main()
