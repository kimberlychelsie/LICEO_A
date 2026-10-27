import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = (ROOT / "migrations" / "add_internal_student_transfers.sql").read_text(encoding="utf-8")
DYNAMIC_TERMS_MIGRATION = (ROOT / "migrations" / "extend_dynamic_grading_terms.sql").read_text(encoding="utf-8")
ROUTES = (ROOT / "routes" / "registrar.py").read_text(encoding="utf-8")
TEMPLATE = (ROOT / "templates" / "registrar_student_transfers.html").read_text(encoding="utf-8")
BASE = (ROOT / "templates" / "base.html").read_text(encoding="utf-8")
STUDENT_PORTAL = (ROOT / "routes" / "student_portal.py").read_text(encoding="utf-8")
STUDENT_GRADES = (ROOT / "templates" / "student_grades.html").read_text(encoding="utf-8")
TEACHER = (ROOT / "routes" / "teacher.py").read_text(encoding="utf-8")


class InternalStudentTransferTests(unittest.TestCase):
    def test_migration_is_additive_audited_and_idempotent(self):
        self.assertIn("CREATE TABLE IF NOT EXISTS public.student_transfer_requests", MIGRATION)
        self.assertIn("CREATE TABLE IF NOT EXISTS public.student_transfer_history", MIGRATION)
        self.assertIn("WHERE status = 'pending_destination'", MIGRATION)
        self.assertIn("source_branch_id <> destination_branch_id", MIGRATION)
        self.assertIn("must allow transferred_out", MIGRATION)
        self.assertNotIn("TRUNCATE", MIGRATION.upper())

    def test_transfer_constraint_supports_policy_defined_later_terms(self):
        self.assertIn("effective_term ~ '^[1-9][0-9]*(st|nd|rd|th)$'", MIGRATION)
        self.assertIn("DROP CONSTRAINT chk_transfer_term", DYNAMIC_TERMS_MIGRATION)
        self.assertIn("VALIDATE CONSTRAINT chk_transfer_term", DYNAMIC_TERMS_MIGRATION)

    def test_routes_are_registrar_and_branch_scoped(self):
        block = ROUTES[ROUTES.index("def registrar_student_transfers"):ROUTES.index("def toggle_new_student_enrollment")]
        self.assertIn('session.get("role") != "registrar"', block)
        self.assertIn("tr.destination_branch_id=%s", block)
        self.assertIn("tr.source_branch_id=%s", block)
        self.assertIn("destination_branch_id=%s", block)

    def test_request_requires_open_destination_and_documents(self):
        block = ROUTES[ROUTES.index("def registrar_request_student_transfer"):ROUTES.index("def registrar_decide_student_transfer")]
        self.assertIn("ns.is_open=TRUE", block)
        self.assertIn("form 137", block.lower())
        self.assertIn("form 138", block.lower())
        self.assertIn("student_transfer_history", block)
        self.assertIn("required_grading_periods(", block)
        self.assertIn("required_terms = configured_terms[:configured_terms.index(effective_term)]", block)
        self.assertIn("COUNT(DISTINCT pg.subject_id) AS posted_subjects", block)
        self.assertIn("posted_subjects < assigned_subjects", block)

    def test_approval_locks_and_preserves_source_history(self):
        block = ROUTES[ROUTES.index("def registrar_decide_student_transfer"):ROUTES.index("def toggle_new_student_enrollment")]
        self.assertIn("FOR UPDATE OF tr, e", block)
        self.assertIn("FOR UPDATE OF ns", block)
        self.assertIn("FOR UPDATE OF s", block)
        self.assertIn("status='transferred_out'", block)
        self.assertIn("INSERT INTO enrollments", block)
        self.assertIn("UPDATE student_accounts SET enrollment_id=%s, branch_id=%s", block)
        self.assertNotIn("DELETE FROM posted_grades", block)
        self.assertNotIn("DELETE FROM enrollments", block)

    def test_ui_has_request_incoming_outgoing_and_decisions(self):
        for text in ("Request Transfer", "Incoming", "Outgoing", "Permanent Record (SF10 / Form 137)", "Report Card (SF9 / Form 138)", "rejectTransfer"):
            self.assertIn(text, TEMPLATE)
        self.assertIn("/registrar/student-transfers", BASE)

    def test_transfer_student_picker_has_grade_and_search_filters(self):
        for marker in ("transferGradeFilter", "transferStudentSearch", "filterTransferStudents"):
            self.assertIn(marker, TEMPLATE)
        self.assertIn('data-name="{{ s.student_name|e }}"', TEMPLATE)
        self.assertIn("academicGradeOrder", TEMPLATE)
        self.assertIn('data-sf10="{{ 1 if s.has_sf10 else 0 }}"', TEMPLATE)
        self.assertIn("Manage Documents", TEMPLATE)

    def test_student_grades_has_transfer_aware_consolidated_view(self):
        self.assertIn("consolidated_transfer_id", STUDENT_PORTAL)
        self.assertIn("period_index < effective_index", STUDENT_PORTAL)
        self.assertIn("period_index >= effective_index", STUDENT_PORTAL)
        self.assertIn("Consolidated Record", STUDENT_GRADES)
        self.assertIn("grade_sources", STUDENT_GRADES)

    def test_destination_teacher_cannot_grade_pre_transfer_terms(self):
        self.assertIn("def _assert_student_gradeable_for_period", TEACHER)
        self.assertIn("Destination teachers cannot edit these historical grades", TEACHER)
        self.assertIn("tr.destination_enrollment_id=e.enrollment_id", TEACHER)
        participation_block = TEACHER[TEACHER.index("def participation_input"):TEACHER.index("def attendance_input")]
        attendance_block = TEACHER[TEACHER.index("def attendance_input"):]
        self.assertIn("_assert_student_gradeable_for_period", participation_block)
        self.assertIn("_assert_student_gradeable_for_period", attendance_block)


if __name__ == "__main__":
    unittest.main()
