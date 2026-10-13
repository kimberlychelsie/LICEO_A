import unittest
from pathlib import Path

from utils.enrollment_text_validation import (
    enrollment_field_spam_error,
    enrollment_remarks_error,
    SPAM_SPECIALS_MESSAGE,
    REMARKS_SPECIALS_MESSAGE,
)

ROOT = Path(__file__).resolve().parents[1]
STUDENT = (ROOT / "routes" / "student.py").read_text(encoding="utf-8")
ENROLL_TEMPLATE = (ROOT / "templates" / "student_enroll.html").read_text(encoding="utf-8")
EDIT_TEMPLATE = (ROOT / "templates" / "student_enroll_edit.html").read_text(encoding="utf-8")


class EnrollmentTextValidationTest(unittest.TestCase):
    def test_blocks_repeating_dot_comma_spam(self):
        self.assertEqual(enrollment_field_spam_error(".,.,.,.,.,.,"), SPAM_SPECIALS_MESSAGE)

    def test_blocks_repeating_hyphen_comma_spam(self):
        self.assertEqual(enrollment_field_spam_error("-,-,-,-,-,"), SPAM_SPECIALS_MESSAGE)

    def test_blocks_hyphenated_keyboard_spam(self):
        self.assertEqual(enrollment_field_spam_error("sadas-fsasd-asdas"), SPAM_SPECIALS_MESSAGE)

    def test_allows_real_names_and_addresses(self):
        self.assertIsNone(enrollment_field_spam_error("Juan Miguel"))
        self.assertIsNone(enrollment_field_spam_error("Anne-Marie"))
        self.assertIsNone(enrollment_field_spam_error("Brgy. San Jose, Cebu City"))
        self.assertIsNone(enrollment_field_spam_error("House No., Street, Barangay"))
        self.assertIsNone(enrollment_field_spam_error("Teacher"))
        self.assertIsNone(enrollment_field_spam_error(""))

    def test_remarks_blocks_special_character_spam(self):
        self.assertEqual(
            enrollment_remarks_error("===ppHHHHJ&^^%$#!#$%^&*()_)(*&^"),
            SPAM_SPECIALS_MESSAGE,
        )
        self.assertEqual(enrollment_remarks_error("hello & goodbye"), REMARKS_SPECIALS_MESSAGE)
        self.assertIsNone(enrollment_remarks_error("Scholarship applicant, late enrollee"))

    def test_public_and_correction_forms_use_spam_checks(self):
        self.assertIn("enrollment_field_spam_error", STUDENT)
        self.assertIn("function hasSpamSpecials", ENROLL_TEMPLATE)
        self.assertIn("function hasSpamSpecials", EDIT_TEMPLATE)
        self.assertIn("Special-character spam is not allowed", ENROLL_TEMPLATE)
        self.assertIn("Special-character spam is not allowed", EDIT_TEMPLATE)
        self.assertIn('name="remarks"', ENROLL_TEMPLATE)
        self.assertIn("/[^A-Za-z0-9ñÑ\\s.,-]/g", ENROLL_TEMPLATE)
        self.assertIn("enrollment_remarks_error", STUDENT)


if __name__ == "__main__":
    unittest.main()
