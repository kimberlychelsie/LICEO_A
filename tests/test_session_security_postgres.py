import os
import pathlib
import statistics
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor

import psycopg2
from dotenv import load_dotenv

from utils.auth_sessions import cleanup_auth_sessions, revoke_auth_session, touch_auth_session


load_dotenv()


def _database_name():
    return os.getenv("SESSION_SECURITY_TEST_DB_NAME", "")


def _connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=_database_name(),
        user=os.getenv("DB_USER", "liceo_db"),
        password=os.getenv("DB_PASSWORD", "1234"),
        connect_timeout=5,
    )


def _save_answer(result_id, question_id, answer, ready=None, delay=0):
    with _connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT status FROM exam_results WHERE result_id=%s FOR UPDATE",
            (result_id,),
        )
        status = cur.fetchone()[0]
        if ready:
            ready.set()
        if delay:
            time.sleep(delay)
        if status != "in_progress":
            return False
        cur.execute(
            """
            INSERT INTO exam_answers(result_id,question_id,student_answer,is_correct)
            VALUES (%s,%s,%s,%s)
            ON CONFLICT(result_id,question_id) DO UPDATE
            SET student_answer=EXCLUDED.student_answer,
                is_correct=EXCLUDED.is_correct
            """,
            (result_id, question_id, answer, answer == "A"),
        )
        return True


def _finalize(result_id, status, ready=None, delay=0):
    with _connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT status FROM exam_results WHERE result_id=%s FOR UPDATE",
            (result_id,),
        )
        if cur.fetchone()[0] != "in_progress":
            return False
        if ready:
            ready.set()
        if delay:
            time.sleep(delay)
        cur.execute(
            """
            SELECT COALESCE(SUM(CASE WHEN a.is_correct THEN q.points ELSE 0 END),0),
                   COALESCE(SUM(q.points),0)
            FROM exam_questions q
            LEFT JOIN exam_answers a
              ON a.question_id=q.question_id AND a.result_id=%s
            WHERE q.exam_id=(SELECT exam_id FROM exam_results WHERE result_id=%s)
            """,
            (result_id, result_id),
        )
        score, total = cur.fetchone()
        cur.execute(
            """
            UPDATE exam_results
            SET status=%s,score=%s,total_points=%s,submitted_at=NOW()
            WHERE result_id=%s AND status='in_progress'
            """,
            (status, score, total, result_id),
        )
        return cur.rowcount == 1


class SessionSecurityPostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        name = _database_name()
        if not name.startswith("liceo_session_test_"):
            raise unittest.SkipTest("Disposable session-security PostgreSQL DB is not configured.")
        with _connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT current_database()")
            if cur.fetchone()[0] != name:
                raise RuntimeError("Refusing to run outside the disposable database")

    def setUp(self):
        with _connection() as conn, conn.cursor() as cur:
            cur.execute(
                "TRUNCATE exam_answers,exam_questions,exam_results,exams,"
                "individual_extensions,auth_sessions,enrollments,users RESTART IDENTITY CASCADE"
            )
            cur.execute(
                "INSERT INTO users(username) VALUES ('student') RETURNING user_id"
            )
            self.user_id = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO enrollments(user_id) VALUES (%s) RETURNING enrollment_id",
                (self.user_id,),
            )
            self.enrollment_id = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO exams(duration_mins,scheduled_start) VALUES (30,NOW()) RETURNING exam_id"
            )
            self.exam_id = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO exam_results(exam_id,enrollment_id) VALUES (%s,%s) RETURNING result_id",
                (self.exam_id, self.enrollment_id),
            )
            self.result_id = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO exam_questions(exam_id,points) VALUES (%s,10) RETURNING question_id",
                (self.exam_id,),
            )
            self.question_id = cur.fetchone()[0]

    def _status_and_answers(self):
        with _connection() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT status,score,total_points FROM exam_results WHERE result_id=%s",
                (self.result_id,),
            )
            result = cur.fetchone()
            cur.execute(
                "SELECT COUNT(*) FROM exam_answers WHERE result_id=%s",
                (self.result_id,),
            )
            return result, cur.fetchone()[0]

    def test_answer_save_racing_manual_submission_cannot_modify_finalized_attempt(self):
        locked = threading.Event()
        save = threading.Thread(
            target=_save_answer,
            args=(self.result_id, self.question_id, "A", locked, 0.15),
        )
        submit = threading.Thread(target=_finalize, args=(self.result_id, "submitted"))
        save.start()
        self.assertTrue(locked.wait(2))
        submit.start()
        save.join(3)
        submit.join(3)
        result, answers = self._status_and_answers()
        self.assertEqual(result, ("submitted", 10, 10))
        self.assertEqual(answers, 1)
        self.assertFalse(_save_answer(self.result_id, self.question_id, "B"))
        self.assertEqual(self._status_and_answers()[1], 1)

    def test_answer_save_racing_expiration_is_serialized(self):
        locked = threading.Event()
        expire = threading.Thread(
            target=_finalize,
            args=(self.result_id, "auto_submitted", locked, 0.15),
        )
        save = threading.Thread(
            target=_save_answer,
            args=(self.result_id, self.question_id, "A"),
        )
        expire.start()
        self.assertTrue(locked.wait(2))
        save.start()
        expire.join(3)
        save.join(3)
        result, answers = self._status_and_answers()
        self.assertEqual(result, ("auto_submitted", 0, 10))
        self.assertEqual(answers, 0)

    def test_manual_and_automatic_finalization_are_idempotent(self):
        barrier = threading.Barrier(3)
        outcomes = []

        def run(status):
            barrier.wait()
            outcomes.append(_finalize(self.result_id, status))

        threads = [
            threading.Thread(target=run, args=("submitted",)),
            threading.Thread(target=run, args=("auto_submitted",)),
        ]
        for thread in threads:
            thread.start()
        barrier.wait()
        for thread in threads:
            thread.join(3)
        self.assertEqual(sorted(outcomes), [False, True])
        self.assertIn(self._status_and_answers()[0][0], ("submitted", "auto_submitted"))

    def test_heartbeat_racing_logout_finishes_revoked(self):
        raw_id = "integration-heartbeat-token"
        from utils.auth_sessions import _hash_session_id

        with _connection() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO auth_sessions(session_id_hash,user_id,expires_at) "
                "VALUES (%s,%s,NOW()+INTERVAL '1 hour')",
                (_hash_session_id(raw_id), self.user_id),
            )
        barrier = threading.Barrier(3)

        def heartbeat():
            with _connection() as conn, conn.cursor() as cur:
                barrier.wait()
                touch_auth_session(cur, raw_id, self.user_id, 300, True)

        def logout():
            with _connection() as conn, conn.cursor() as cur:
                barrier.wait()
                revoke_auth_session(cur, raw_id, self.user_id)

        threads = [threading.Thread(target=heartbeat), threading.Thread(target=logout)]
        for thread in threads:
            thread.start()
        barrier.wait()
        for thread in threads:
            thread.join(3)
        with _connection() as conn, conn.cursor() as cur:
            self.assertFalse(touch_auth_session(cur, raw_id, self.user_id, 300, True))

    def test_concurrent_cleanup_preserves_active_and_removes_terminal_rows(self):
        with _connection() as conn, conn.cursor() as cur:
            rows = []
            for index in range(20):
                rows.append((f"expired-{index}", self.user_id))
            cur.executemany(
                "INSERT INTO auth_sessions(session_id_hash,user_id,created_at,last_seen_at,expires_at) "
                "VALUES (%s,%s,NOW()-INTERVAL '20 days',NOW()-INTERVAL '20 days',NOW()-INTERVAL '10 days')",
                rows,
            )
            cur.executemany(
                "INSERT INTO auth_sessions(session_id_hash,user_id,expires_at,revoked_at) "
                "VALUES (%s,%s,NOW()+INTERVAL '1 day',NOW()-INTERVAL '10 days')",
                [(f"revoked-{index}", self.user_id) for index in range(20)],
            )
            cur.execute(
                "INSERT INTO auth_sessions(session_id_hash,user_id,expires_at) "
                "VALUES ('active',%s,NOW()+INTERVAL '1 day')",
                (self.user_id,),
            )
        barrier = threading.Barrier(3)
        results = []

        def worker():
            barrier.wait()
            results.append(cleanup_auth_sessions(_connection, 7, 5, 20)["deleted"])

        threads = [threading.Thread(target=worker), threading.Thread(target=worker)]
        for thread in threads:
            thread.start()
        barrier.wait()
        for thread in threads:
            thread.join(5)
        self.assertEqual(sum(results), 40)
        with _connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT session_id_hash FROM auth_sessions")
            self.assertEqual(cur.fetchall(), [("active",)])

    def test_auth_session_migration_is_idempotent(self):
        migration = pathlib.Path("migrations/add_auth_sessions.sql").read_text(
            encoding="utf-8"
        )
        with _connection() as conn, conn.cursor() as cur:
            cur.execute(migration)
            conn.commit()
            cur.execute(migration)
            conn.commit()
            cur.execute(
                "SELECT COUNT(*) FROM pg_indexes "
                "WHERE schemaname='public' AND tablename='auth_sessions'"
            )
            self.assertEqual(cur.fetchone()[0], 4)

    def test_representative_registry_touch_load(self):
        from utils.auth_sessions import _hash_session_id

        count = 100
        tokens = [f"load-token-{index}" for index in range(count)]
        with _connection() as conn, conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO auth_sessions(session_id_hash,user_id,expires_at) "
                "VALUES (%s,%s,NOW()+INTERVAL '1 hour')",
                [(_hash_session_id(token), self.user_id) for token in tokens],
            )
        groups = [tokens[index::10] for index in range(10)]

        def touch_group(group):
            measurements = []
            with _connection() as conn, conn.cursor() as cur:
                for token in group:
                    started = time.perf_counter()
                    if not touch_auth_session(cur, token, self.user_id, 300):
                        raise AssertionError("active session touch unexpectedly failed")
                    conn.commit()
                    measurements.append((time.perf_counter() - started) * 1000)
            return measurements

        started = time.perf_counter()
        with ThreadPoolExecutor(max_workers=10) as pool:
            grouped_latencies = list(pool.map(touch_group, groups))
        latencies = [value for group in grouped_latencies for value in group]
        wall_ms = (time.perf_counter() - started) * 1000
        self.assertEqual(len(latencies), count)
        p95 = statistics.quantiles(latencies, n=20)[18]
        print(
            f"SESSION_LOAD touches={count} wall_ms={wall_ms:.2f} "
            f"mean_ms={statistics.mean(latencies):.2f} p95_ms={p95:.2f}"
        )
        self.assertLess(p95, 2000)


if __name__ == "__main__":
    unittest.main()
