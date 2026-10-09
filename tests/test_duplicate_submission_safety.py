import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STUDENT = (ROOT / "routes" / "student.py").read_text()
ENROLL_TEMPLATE = (ROOT / "templates" / "student_enroll.html").read_text()


class DuplicateSubmissionSafetyTest(unittest.TestCase):
    def test_identity_input_changes_invalidate_pending_duplicate_responses(self):
        schedule_start = ENROLL_TEMPLATE.index("function scheduleCheck()")
        schedule_block = ENROLL_TEMPLATE[schedule_start:ENROLL_TEMPLATE.index("if (lrnEl)", schedule_start)]
        self.assertIn("duplicateSeq++;", schedule_block)
        self.assertIn("clearTimeout(duplicateTimer);", schedule_block)
        self.assertIn("var seq = duplicateSeq;", ENROLL_TEMPLATE)
        self.assertNotIn("var seq = ++duplicateSeq;", ENROLL_TEMPLATE)

    def test_public_post_acquires_transaction_advisory_locks_before_identity_query(self):
        self.assertIn("def acquire_student_identity_locks", STUDENT)
        self.assertIn("pg_advisory_xact_lock", STUDENT)
        self.assertIn("student_identity:lrn:", STUDENT)
        self.assertIn("student_identity:name_dob:", STUDENT)
        self.assertIn("student_identity:name_dob_email:", STUDENT)
        lock_pos = STUDENT.index("acquire_student_identity_locks(cursor, student_name, dob, lrn, email)")
        validate_pos = STUDENT.index("identity_result = validate_student_identity(cursor, student_name, dob, lrn, email)")
        insert_pos = STUDENT.index("INSERT INTO enrollments")
        self.assertLess(lock_pos, validate_pos)
        self.assertLess(validate_pos, insert_pos)

    def test_advisory_locks_use_stable_hash_and_deadlock_safe_order(self):
        self.assertIn("hashlib.sha256", STUDENT)
        self.assertNotIn("hash(", STUDENT)
        self.assertIn("for lock_id in sorted({_student_identity_lock_id(key) for key in keys}):", STUDENT)

    def test_branch_enrollment_number_lock_uses_branch_scope(self):
        self.assertIn("def acquire_branch_enrollment_no_lock", STUDENT)
        self.assertIn('f"branch_enrollment_no:branch:{int(branch_id)}"', STUDENT)
        self.assertIn("SELECT pg_advisory_xact_lock(%s)", STUDENT)

    def test_public_enrollment_number_lock_is_before_max_and_insert(self):
        lock_pos = STUDENT.index("acquire_branch_enrollment_no_lock(cursor, branch_id)")
        max_pos = STUDENT.index("SELECT COALESCE(MAX(branch_enrollment_no), 0) + 1 AS next_no")
        insert_pos = STUDENT.index("INSERT INTO enrollments", max_pos)
        commit_pos = STUDENT.index("db.commit()", insert_pos)
        self.assertLess(lock_pos, max_pos)
        self.assertLess(max_pos, insert_pos)
        self.assertLess(insert_pos, commit_pos)

    def test_review_failure_rolls_back_before_public_enrollment_commit(self):
        review_pos = STUDENT.index("record_identity_review(cursor, enrollment_id, branch_id, identity_result)")
        rollback_pos = STUDENT.index("db.rollback()", review_pos)
        commit_pos = STUDENT.index("db.commit()", review_pos)
        self.assertLess(rollback_pos, commit_pos)


if __name__ == "__main__":
    unittest.main()
