import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def function_source(source, function_name):
    start = source.index(f"def {function_name}")
    next_route = source.find("\n@", start)
    return source[start:] if next_route == -1 else source[start:next_route]


class AccountArchivalSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.branch_admin = (ROOT / "routes" / "branch_admin.py").read_text(encoding="utf-8")
        cls.auth = (ROOT / "routes" / "auth.py").read_text(encoding="utf-8")
        cls.app = (ROOT / "app.py").read_text(encoding="utf-8")
        cls.template = (ROOT / "templates" / "branch_admin_manage_accounts.html").read_text(
            encoding="utf-8"
        )

    def test_student_archive_synchronizes_both_login_identities(self):
        route = function_source(self.branch_admin, "branch_admin_archive_student_account")
        self.assertIn("UPDATE student_accounts SET is_active = FALSE", route)
        self.assertIn("SET status = 'inactive', is_archived = TRUE", route)
        self.assertIn("enrollment_id = %s OR username = %s", route)
        self.assertIn("FOR UPDATE", route)

    def test_student_restore_synchronizes_both_login_identities(self):
        route = function_source(self.branch_admin, "branch_admin_unarchive_student_account")
        self.assertIn("UPDATE student_accounts SET is_active = TRUE", route)
        self.assertIn("SET status = 'active', is_archived = FALSE", route)
        self.assertIn("enrollment_id = %s OR username = %s", route)

    def test_archived_students_have_a_filtered_restore_view(self):
        listing = function_source(self.branch_admin, "branch_admin_manage_accounts")
        self.assertIn("COALESCE(sa.is_active, TRUE) = %s", listing)
        self.assertIn("params = [branch_id, not show_archived]", listing)
        self.assertIn("Archived Students", self.template)
        self.assertIn("Active Students", self.template)

    def test_login_and_existing_sessions_reject_archived_accounts(self):
        self.assertIn('bool(user.get("is_archived", False))', self.auth)
        self.assertIn("bool(user.get('is_archived', False))", self.app)
        self.assertIn("FROM student_accounts", self.app)
        self.assertIn('student_account.get("is_active", True)', self.app)

    def test_permanent_delete_requires_archive_first(self):
        staff_delete = function_source(self.branch_admin, "branch_admin_delete_account")
        student_delete = function_source(self.branch_admin, "branch_admin_delete_student_account")
        self.assertIn("COALESCE(is_archived, FALSE) = TRUE", staff_delete)
        self.assertIn("Only archived accounts can be permanently deleted", staff_delete)
        self.assertIn("COALESCE(is_active, TRUE) = FALSE", student_delete)
        self.assertIn("Only archived student accounts can be permanently deleted", student_delete)
        self.assertNotIn("<!-- Delete Account -->", self.template)
        self.assertIn("Delete Permanently", self.template)


if __name__ == "__main__":
    unittest.main()
