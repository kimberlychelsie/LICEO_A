import unittest

from flask import Flask, session
from werkzeug.exceptions import Forbidden, NotFound, Unauthorized

from routes.student import _authorized_legacy_enrollment


class EnrollmentCursor:
    def __init__(self, enrollment=None):
        self.enrollment = enrollment
        self.executions = []

    def execute(self, sql, params):
        self.executions.append((" ".join(sql.split()), params))

    def fetchone(self):
        return self.enrollment


class LegacyEnrollmentAccessTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.secret_key = "legacy-access-test"

    def test_unauthenticated_access_is_rejected(self):
        with self.app.test_request_context("/"):
            with self.assertRaises(Unauthorized):
                _authorized_legacy_enrollment(EnrollmentCursor(), 1, 10)

    def test_cross_branch_access_does_not_disclose_enrollment(self):
        with self.app.test_request_context("/"):
            session.update(user_id=7, role="registrar", branch_id=2)
            with self.assertRaises(NotFound):
                _authorized_legacy_enrollment(EnrollmentCursor(), 1, 10)

    def test_student_cannot_tamper_with_another_enrollment_id(self):
        cursor = EnrollmentCursor({"enrollment_id": 10, "branch_id": 1})
        with self.app.test_request_context("/"):
            session.update(
                user_id=7, role="student", branch_id=1, enrollment_id=11
            )
            with self.assertRaises(Forbidden):
                _authorized_legacy_enrollment(cursor, 1, 10)

    def test_owner_and_same_branch_staff_are_authorized(self):
        enrollment = {"enrollment_id": 10, "branch_id": 1}
        for role, enrollment_id in (("student", 10), ("registrar", None), ("branch_admin", None)):
            with self.subTest(role=role), self.app.test_request_context("/"):
                session.update(user_id=7, role=role, branch_id=1)
                if enrollment_id:
                    session["enrollment_id"] = enrollment_id
                result = _authorized_legacy_enrollment(
                    EnrollmentCursor(enrollment), 1, 10, for_update=True
                )
                self.assertEqual(result["enrollment_id"], 10)

    def test_unrelated_authenticated_role_is_forbidden(self):
        with self.app.test_request_context("/"):
            session.update(user_id=7, role="teacher", branch_id=1)
            with self.assertRaises(Forbidden):
                _authorized_legacy_enrollment(EnrollmentCursor(), 1, 10)


if __name__ == "__main__":
    unittest.main()
