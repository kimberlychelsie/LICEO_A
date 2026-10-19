import unittest
from pathlib import Path

from flask import Flask, session

from utils.parent_sync import sync_user_parent_links


ROOT = Path(__file__).resolve().parents[1]


class StudentCursor:
    def __init__(self):
        self.statements = []

    def execute(self, sql, params=None):
        self.statements.append((sql, params))

    def fetchone(self):
        return {
            "user_id": 64,
            "email": "shared@example.test",
            "branch_id": 11,
            "role": "student",
            "user_roles": '["student", "parent"]',
        }


class ParentLinkSecurityTests(unittest.TestCase):
    def test_student_shadow_user_is_never_auto_linked_as_parent(self):
        app = Flask(__name__)
        app.secret_key = "test"
        cursor = StudentCursor()

        with app.test_request_context("/"):
            session["user_id"] = 64
            session["role"] = "student"
            session["roles"] = ["student", "parent"]

            result = sync_user_parent_links(None, cursor, 64)

            self.assertFalse(result["has_parent_role"])
            self.assertEqual(result["user_roles"], ["student"])
            self.assertEqual(session["roles"], ["student"])
            self.assertEqual(session["role"], "student")

        executed_sql = "\n".join(sql for sql, _ in cursor.statements)
        self.assertNotIn("INSERT INTO parent_student", executed_sql)
        self.assertNotIn("DELETE FROM parent_student", executed_sql)

    def test_legacy_startup_linking_excludes_students_and_cross_branch_matches(self):
        source = (ROOT / "db.py").read_text(encoding="utf-8")

        self.assertIn("AND u.branch_id = e.branch_id", source)
        self.assertIn("AND u.role <> 'student'", source)
        self.assertIn("WHERE u.role <> 'student'", source)

    def test_registrar_only_recognizes_eligible_same_branch_parents(self):
        source = (ROOT / "routes" / "registrar.py").read_text(encoding="utf-8")
        listing = source[source.index("def registrar_enrollments"):source.index(
            "def _parse_deped_name")]

        self.assertIn("pu.branch_id = e.branch_id", listing)
        self.assertIn("pu.role = 'parent'", listing)
        self.assertIn("pu.role <> 'student'", listing)
        self.assertIn("u2.branch_id = e.branch_id", listing)
        self.assertIn("LOWER(TRIM(e2.guardian_email))", listing)

    def test_manual_link_requires_registrar_verified_parent_identity(self):
        source = (ROOT / "routes" / "parent.py").read_text(encoding="utf-8")
        route = source[source.index("def link_child"):source.index(
            "@parent_bp.route(\"/parent/child/<int:enrollment_id>\""
        )]

        self.assertIn('parent_user.get("role") != "parent"', route)
        self.assertIn('parent_user.get("branch_id") is None', route)
        self.assertIn('parent_user.get("branch_id") != branch_id_int', route)
        self.assertIn("guardian_email != parent_email", route)
        self.assertIn('parent_user.get("enrollment_id") == enrollment_id', route)
        self.assertIn("FOR UPDATE", route)

    def test_parent_registration_persists_identity_fields(self):
        source = (ROOT / "routes" / "parent.py").read_text(encoding="utf-8")
        register = source[source.index("def register"):source.index(
            "@parent_bp.route(\"/parent/dashboard\""
        )]

        self.assertIn("email, full_name, contact_number", register)
