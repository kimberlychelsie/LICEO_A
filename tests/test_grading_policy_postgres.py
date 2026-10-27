import os
import pathlib
import threading
import unittest

import psycopg2
import psycopg2.extras

from services.final_grades import PeriodGrade, calculate_final_grade, load_active_grading_policy


ROOT = pathlib.Path(__file__).resolve().parents[1]
MIGRATIONS = (
    ROOT / "migrations" / "add_grading_period_ranges_foundation.sql",
    ROOT / "migrations" / "add_grading_policies.sql",
)
DYNAMIC_TERMS_MIGRATION = ROOT / "migrations" / "extend_dynamic_grading_terms.sql"


def _database_name():
    return os.getenv("GRADING_POLICY_TEST_DB_NAME", "")


def _connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=_database_name(),
        user=os.getenv("DB_USER", "liceo_db"),
        password=os.getenv("DB_PASSWORD", "1234"),
        connect_timeout=5,
    )


class GradingPolicyPostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        name = _database_name()
        if not name.startswith("liceo_grading_policy_test_"):
            raise unittest.SkipTest("Disposable grading-policy PostgreSQL DB is not configured.")
        with _connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT current_database()")
            if cur.fetchone()[0] != name:
                raise RuntimeError("Refusing to run outside the disposable grading-policy database")
            cur.execute("CREATE TABLE IF NOT EXISTS branches (branch_id SERIAL PRIMARY KEY, branch_name TEXT NOT NULL)")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS school_years (
                    year_id SERIAL PRIMARY KEY, label VARCHAR(9) NOT NULL,
                    branch_id INTEGER, is_active BOOLEAN NOT NULL DEFAULT FALSE
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id SERIAL PRIMARY KEY, username VARCHAR(50),
                    password VARCHAR(255), role VARCHAR(20)
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS grade_submission_requests (
                    id SERIAL PRIMARY KEY, section_id INTEGER NOT NULL,
                    subject_id INTEGER NOT NULL, grading_period VARCHAR(20) NOT NULL,
                    year_id INTEGER NOT NULL, branch_id INTEGER NOT NULL,
                    status VARCHAR(30) NOT NULL DEFAULT 'draft'
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS teacher_grading_weights (
                    weight_id SERIAL PRIMARY KEY,
                    grading_period VARCHAR(20) NOT NULL,
                    CONSTRAINT teacher_grading_weights_period_check
                        CHECK (grading_period IN ('1st','2nd','3rd'))
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS student_transfer_requests (
                    transfer_id SERIAL PRIMARY KEY,
                    effective_term VARCHAR(20) NOT NULL,
                    CONSTRAINT chk_transfer_term
                        CHECK (effective_term IN ('1st','2nd','3rd'))
                )
            """)
            for migration in MIGRATIONS:
                cur.execute(migration.read_text(encoding="utf-8"))
            cur.execute(DYNAMIC_TERMS_MIGRATION.read_text(encoding="utf-8"))
            # Idempotency is exercised against the exact resulting schema.
            for migration in MIGRATIONS:
                cur.execute(migration.read_text(encoding="utf-8"))
            cur.execute(DYNAMIC_TERMS_MIGRATION.read_text(encoding="utf-8"))

    def setUp(self):
        with _connection() as conn, conn.cursor() as cur:
            cur.execute(
                "TRUNCATE grading_policy_periods,grading_policies,"
                "grading_period_ranges,grade_submission_requests,school_years,"
                "teacher_grading_weights,student_transfer_requests,"
                "users,branches RESTART IDENTITY CASCADE"
            )
            cur.execute("INSERT INTO branches(branch_name) VALUES ('A'),('B') RETURNING branch_id")
            branches = [row[0] for row in cur.fetchall()]
            cur.execute(
                "INSERT INTO school_years(label,branch_id,is_active) "
                "VALUES ('2099-2100',%s,TRUE),('2099-2100',%s,TRUE) RETURNING year_id",
                branches,
            )
            years = [row[0] for row in cur.fetchall()]
            cur.execute(
                "INSERT INTO users(username,password,role) VALUES ('verifier','x','branch_admin') RETURNING user_id"
            )
            verifier = cur.fetchone()[0]
            self.ids = {"branch": branches[0], "other_branch": branches[1],
                        "year": years[0], "other_year": years[1], "verifier": verifier}
            self.ids["terms"] = []
            for number, name in enumerate(("1st", "2nd", "3rd", "4th"), start=1):
                cur.execute(
                    "INSERT INTO grading_period_ranges(branch_id,year_id,period_name,start_date,end_date) "
                    "VALUES (%s,%s,%s,DATE '2099-01-01' + %s,DATE '2099-01-01' + %s) RETURNING id",
                    (branches[0], years[0], name, number * 10, number * 10 + 5),
                )
                self.ids["terms"].append(cur.fetchone()[0])
            cur.execute(
                "INSERT INTO grading_period_ranges(branch_id,year_id,period_name,start_date,end_date) "
                "VALUES (%s,%s,'1st','2099-01-01','2099-01-05') RETURNING id",
                (branches[1], years[1]),
            )
            self.ids["other_term"] = cur.fetchone()[0]

    def _create_policy(self, period_count, version="test-v1", status="draft"):
        ids = self.ids
        with _connection() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO grading_policies(branch_id,year_id,policy_version,rounding_mode,rounding_scale,status) "
                "VALUES (%s,%s,%s,'excel_round',0,'draft') RETURNING policy_id",
                (ids["branch"], ids["year"], version),
            )
            policy_id = cur.fetchone()[0]
            for position, term_id in enumerate(ids["terms"][:period_count], start=1):
                cur.execute(
                    "INSERT INTO grading_policy_periods(policy_id,branch_id,year_id,sequence_no,calendar_term_id) "
                    "VALUES (%s,%s,%s,%s,%s)",
                    (policy_id, ids["branch"], ids["year"], position, term_id),
                )
            if status in ("verified", "active"):
                cur.execute("UPDATE grading_policies SET status='pending_verification' WHERE policy_id=%s", (policy_id,))
                cur.execute(
                    "UPDATE grading_policies SET status='verified',verified_by=%s,verified_at=NOW(),"
                    "verification_notes='Disposable test verification' WHERE policy_id=%s",
                    (ids["verifier"], policy_id),
                )
            if status == "active":
                cur.execute(
                    "UPDATE grading_policies SET status='active',activated_by=%s,activated_at=NOW() WHERE policy_id=%s",
                    (ids["verifier"], policy_id),
                )
            return policy_id

    def test_three_and_four_term_policies_load_and_calculate(self):
        three = self._create_policy(3, "three-v1", "active")
        with _connection() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            loaded = load_active_grading_policy(cur, branch_id=self.ids["branch"], year_id=self.ids["year"])
            self.assertEqual(loaded.policy_id, three)
            result = calculate_final_grade(loaded, [PeriodGrade("1st", 80), PeriodGrade("2nd", 81), PeriodGrade("3rd", 82)])
            self.assertEqual(str(result.final_grade), "81")
        with _connection() as conn, conn.cursor() as cur:
            cur.execute("UPDATE grading_policies SET status='retired',retired_at=NOW() WHERE policy_id=%s", (three,))
        self._create_policy(4, "four-v1", "active")
        with _connection() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            loaded = load_active_grading_policy(cur, branch_id=self.ids["branch"], year_id=self.ids["year"])
            self.assertEqual(loaded.required_periods, ("1st", "2nd", "3rd", "4th"))

    def test_dynamic_term_upgrade_accepts_fourth_and_later_terms(self):
        with _connection() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO teacher_grading_weights(grading_period) VALUES ('4th'),('5th')"
            )
            cur.execute(
                "INSERT INTO student_transfer_requests(effective_term) VALUES ('4th'),('5th')"
            )
        with self.assertRaises(psycopg2.IntegrityError), _connection() as conn, conn.cursor() as cur:
            cur.execute("INSERT INTO teacher_grading_weights(grading_period) VALUES ('final')")

    def test_cross_branch_calendar_term_is_rejected(self):
        policy_id = self._create_policy(1)
        with self.assertRaises(psycopg2.IntegrityError), _connection() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO grading_policy_periods(policy_id,branch_id,year_id,sequence_no,calendar_term_id) "
                "VALUES (%s,%s,%s,2,%s)",
                (policy_id, self.ids["branch"], self.ids["year"], self.ids["other_term"]),
            )

    def test_verified_policy_periods_are_locked(self):
        policy_id = self._create_policy(3, status="verified")
        with self.assertRaises(psycopg2.DatabaseError), _connection() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM grading_policy_periods WHERE policy_id=%s AND sequence_no=3", (policy_id,))

    def test_historically_referenced_draft_periods_are_locked(self):
        policy_id = self._create_policy(3)
        with _connection() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO grade_submission_requests(section_id,subject_id,grading_period,year_id,branch_id,status) "
                "VALUES (1,1,'1st',%s,%s,'pending_admin')",
                (self.ids["year"], self.ids["branch"]),
            )
        with self.assertRaises(psycopg2.DatabaseError), _connection() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM grading_policy_periods WHERE policy_id=%s AND sequence_no=1", (policy_id,))

    def test_noncontiguous_policy_cannot_be_verified(self):
        policy_id = self._create_policy(2)
        with _connection() as conn, conn.cursor() as cur:
            cur.execute("UPDATE grading_policy_periods SET sequence_no=3 WHERE policy_id=%s AND sequence_no=2", (policy_id,))
        with self.assertRaises(psycopg2.DatabaseError), _connection() as conn, conn.cursor() as cur:
            cur.execute("UPDATE grading_policies SET status='pending_verification' WHERE policy_id=%s", (policy_id,))
            cur.execute(
                "UPDATE grading_policies SET status='verified',verified_by=%s,verified_at=NOW(),"
                "verification_notes='test' WHERE policy_id=%s",
                (self.ids["verifier"], policy_id),
            )

    def test_concurrent_activation_allows_only_one_active_policy(self):
        first = self._create_policy(3, "concurrent-a", "verified")
        second = self._create_policy(3, "concurrent-b", "verified")
        barrier = threading.Barrier(2)
        outcomes = []

        def activate(policy_id):
            try:
                with _connection() as conn, conn.cursor() as cur:
                    barrier.wait(timeout=3)
                    cur.execute(
                        "UPDATE grading_policies SET status='active',activated_by=%s,activated_at=NOW() WHERE policy_id=%s",
                        (self.ids["verifier"], policy_id),
                    )
                outcomes.append("active")
            except psycopg2.IntegrityError:
                outcomes.append("conflict")

        threads = [threading.Thread(target=activate, args=(value,)) for value in (first, second)]
        for thread in threads: thread.start()
        for thread in threads: thread.join(5)
        self.assertEqual(sorted(outcomes), ["active", "conflict"])


if __name__ == "__main__":
    unittest.main()
