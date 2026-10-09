import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STUDENT = (ROOT / "routes" / "student.py").read_text()
PARENT = (ROOT / "routes" / "parent.py").read_text()
LIBRARIAN = (ROOT / "routes" / "librarian.py").read_text()
WORKFLOW_MIGRATION = (ROOT / "migrations" / "ensure_enrollment_workflow_columns.sql").read_text()
PREFLIGHT = (ROOT / "migrations" / "preflight_enrollment_railway_readonly.sql").read_text()


class EnrollmentNumberScopeTest(unittest.TestCase):
    def test_migration_uses_branch_year_enrollment_number_uniqueness(self):
        self.assertIn("uq_enrollments_branch_year_no", WORKFLOW_MIGRATION)
        self.assertIn("UNIQUE (branch_id, year_id, branch_enrollment_no)", WORKFLOW_MIGRATION)
        self.assertIn("GROUP BY branch_id, year_id, branch_enrollment_no", WORKFLOW_MIGRATION)
        self.assertNotIn("UNIQUE (branch_id, branch_enrollment_no)", WORKFLOW_MIGRATION)

    def test_preflight_checks_branch_year_enrollment_number_duplicates(self):
        self.assertIn("duplicate_branch_year_enrollment_no", PREFLIGHT)
        self.assertIn("GROUP BY branch_id, year_id, branch_enrollment_no", PREFLIGHT)
        self.assertIn("uq_enrollments_branch_year_no", PREFLIGHT)

    def test_new_student_allocation_remains_branch_wide(self):
        self.assertIn("SELECT COALESCE(MAX(branch_enrollment_no), 0) + 1 AS next_no FROM enrollments WHERE branch_id = %s", STUDENT)
        self.assertIn('f"branch_enrollment_no:branch:{int(branch_id)}"', STUDENT)

    def test_continuing_students_reuse_existing_branch_number(self):
        self.assertIn('next_no = enrollment.get("branch_enrollment_no")', STUDENT)

    def test_public_tracking_prefers_active_year_when_number_repeats(self):
        lookup_pos = STUDENT.index("WHERE e.branch_enrollment_no = %s AND e.branch_id = %s")
        order_pos = STUDENT.index("ORDER BY COALESCE(sy.is_active, FALSE) DESC, e.year_id DESC NULLS LAST, e.created_at DESC", lookup_pos)
        self.assertLess(lookup_pos, order_pos)

    def test_parent_link_prefers_active_year_when_number_repeats(self):
        lookup_pos = PARENT.index("WHERE e.branch_enrollment_no=%s AND e.branch_id=%s")
        order_pos = PARENT.index("ORDER BY COALESCE(sy.is_active, FALSE) DESC, e.year_id DESC NULLS LAST, e.created_at DESC", lookup_pos)
        self.assertLess(lookup_pos, order_pos)

    def test_librarian_branch_number_lookups_prefer_active_year(self):
        self.assertGreaterEqual(
            LIBRARIAN.count("ORDER BY COALESCE(sy.is_active, FALSE) DESC, e.year_id DESC NULLS LAST, e.created_at DESC"),
            2
        )


if __name__ == "__main__":
    unittest.main()
