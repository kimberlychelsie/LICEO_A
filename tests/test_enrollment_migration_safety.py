import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / "migrations" / "ensure_enrollment_workflow_columns.sql").read_text()
REVIEWS = (ROOT / "migrations" / "add_student_identity_reviews.sql").read_text()
CORRECTION = (ROOT / "migrations" / "add_correction_requested_status.sql").read_text()


class EnrollmentMigrationSafetyTest(unittest.TestCase):
    def test_workflow_migration_checks_existing_column_types(self):
        self.assertIn("expected_columns(column_name, expected_data_type)", WORKFLOW)
        self.assertIn("Incompatible existing enrollments columns", WORKFLOW)
        self.assertIn("('status', 'character varying')", WORKFLOW)
        self.assertIn("('branch_enrollment_no', 'integer')", WORKFLOW)
        self.assertIn("('year_id', 'integer')", WORKFLOW)
        self.assertIn("c.data_type NOT IN ('timestamp without time zone', 'timestamp with time zone')", WORKFLOW)

    def test_workflow_migration_verifies_unique_constraint_definition(self):
        self.assertIn("uq_enrollments_branch_year_no", WORKFLOW)
        self.assertIn("UNIQUE (branch_id, year_id, branch_enrollment_no)", WORKFLOW)
        self.assertIn("has unexpected definition", WORKFLOW)
        self.assertNotIn("UNIQUE (branch_id, branch_enrollment_no)", WORKFLOW)

    def test_identity_review_migration_verifies_referenced_keys(self):
        self.assertIn("required_pk(table_name, column_name)", REVIEWS)
        self.assertIn("primary/unique key public.", REVIEWS)
        self.assertIn("con.contype IN ('p', 'u')", REVIEWS)

    def test_identity_review_migration_preserves_audit_rows(self):
        self.assertIn("enrollment_id INTEGER NOT NULL REFERENCES public.enrollments(enrollment_id),", REVIEWS)
        self.assertIn("branch_id INTEGER NOT NULL REFERENCES public.branches(branch_id),", REVIEWS)
        self.assertIn("matched_enrollment_id INTEGER REFERENCES public.enrollments(enrollment_id) ON DELETE SET NULL", REVIEWS)
        self.assertIn("reviewed_by INTEGER REFERENCES public.users(user_id) ON DELETE SET NULL", REVIEWS)
        self.assertNotIn("enrollment_id INTEGER NOT NULL REFERENCES public.enrollments(enrollment_id) ON DELETE CASCADE", REVIEWS)
        self.assertNotIn("branch_id INTEGER NOT NULL REFERENCES public.branches(branch_id) ON DELETE CASCADE", REVIEWS)

    def test_review_statuses_match_registrar_policy(self):
        self.assertIn("CHECK (status IN ('pending', 'distinct_student', 'existing_student'))", REVIEWS)

    def test_migrations_do_not_modify_existing_student_records(self):
        combined = "\n".join([WORKFLOW, REVIEWS, CORRECTION]).upper()
        self.assertNotIn("DELETE FROM", combined)
        self.assertNotIn("TRUNCATE", combined)
        self.assertNotIn("DROP TABLE", combined)
        self.assertNotIn("UPDATE PUBLIC.ENROLLMENTS", combined)
        self.assertNotIn("UPDATE ENROLLMENTS", combined)
        self.assertNotIn("ALTER SEQUENCE", combined)


if __name__ == "__main__":
    unittest.main()
