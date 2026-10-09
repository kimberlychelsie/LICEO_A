import unittest

from utils.student_identity import evaluate_student_identity_match


def row(**overrides):
    data = {
        "student_first_name": "Melbourne",
        "student_middle_name": "",
        "student_last_name": "Santos",
        "student_name": "Melbourne Santos",
        "dob": "2012-05-10",
        "lrn": "123456789001",
        "email": "parent@gmail.com",
        "guardian_email": "parent@gmail.com",
        "status": "enrolled",
    }
    data.update(overrides)
    return data


class StudentIdentityValidationTest(unittest.TestCase):
    def test_matching_lrn_blocks_existing_student(self):
        result = evaluate_student_identity_match(
            "Melbourne Santos",
            "2012-05-10",
            "123456789001",
            row()
        )
        self.assertEqual(result["action"], "block")

    def test_pending_cross_branch_application_blocks_by_lrn(self):
        result = evaluate_student_identity_match(
            "Melbourne Santos",
            "2012-05-10",
            "123456789001",
            row(status="pending", branch_id=1)
        )
        self.assertEqual(result["action"], "block")

    def test_previous_year_existing_student_blocks_by_lrn(self):
        result = evaluate_student_identity_match(
            "Melbourne Santos",
            "2012-05-10",
            "123456789001",
            row(status="completed", year_id=5)
        )
        self.assertEqual(result["action"], "block")

    def test_same_student_email_does_not_block_sibling(self):
        result = evaluate_student_identity_match(
            "Mel Santos",
            "2013-06-11",
            "",
            row(email="parent@gmail.com", guardian_email="parent@gmail.com")
        )
        self.assertEqual(result["action"], "ok")

    def test_distinct_twins_with_same_birthday_are_not_hard_blocked(self):
        result = evaluate_student_identity_match(
            "Mel Santos",
            "2012-05-10",
            "123456789002",
            row()
        )
        self.assertNotEqual(result["action"], "block")

    def test_blank_lrn_same_name_dob_email_blocks(self):
        result = evaluate_student_identity_match(
            "Melbourne Santos",
            "2012-05-10",
            "",
            row(lrn="", email="parent@gmail.com"),
            new_email="parent@gmail.com"
        )
        self.assertEqual(result["action"], "block")

    def test_exact_name_and_birthday_requires_review_without_lrn(self):
        result = evaluate_student_identity_match(
            "Melbourne Santos",
            "2012-05-10",
            "",
            row(lrn="", email="other@gmail.com"),
            new_email="parent@gmail.com"
        )
        self.assertEqual(result["action"], "review")

    def test_lrn_conflict_blocks_regardless_name_or_birthday(self):
        result = evaluate_student_identity_match(
            "Different Learner",
            "2014-01-01",
            "123456789001",
            row()
        )
        self.assertEqual(result["action"], "block")

    def test_rejected_application_does_not_block_reapplication(self):
        result = evaluate_student_identity_match(
            "Melbourne Santos",
            "2012-05-10",
            "123456789001",
            row(status="rejected")
        )
        self.assertEqual(result["action"], "ok")

    def test_rejected_application_with_student_account_still_blocks_by_lrn(self):
        result = evaluate_student_identity_match(
            "Melbourne Santos",
            "2012-05-10",
            "123456789001",
            row(status="rejected", has_student_account=True)
        )
        self.assertEqual(result["action"], "block")


if __name__ == "__main__":
    unittest.main()
