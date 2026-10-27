import unittest
from pathlib import Path

from werkzeug.datastructures import MultiDict

from routes.student_portal import (
    _completed_education_levels,
    _validate_swafo_personal_info,
    _validate_swafo_submission,
)


ROOT = Path(__file__).resolve().parents[1]


class SwafoValidationTests(unittest.TestCase):
    def test_swafo_draft_normalizes_and_accepts_valid_rows(self):
        form = MultiDict([
            ("nickname", "  KC  "),
            ("uri_ng_kabuhayan", "Katamtaman"),
            ("kalagayan_pag_aaral", "Mahusay"),
            ("fm_name[]", "Juan Dela Cruz"),
            ("fm_edad[]", "40"),
            ("fm_estatus[]", "College"),
            ("fm_pinapasukan[]", "Liceo"),
            ("fm_trabaho[]", "Teacher"),
            ("ed_antas[]", "Elementary"),
            ("ed_paaralan[]", "Liceo"),
            ("ed_taon[]", "2020"),
            ("ed_katamo[]", "With Honors"),
        ])

        cleaned, family, education, summer = _validate_swafo_submission(form)

        self.assertEqual(cleaned["nickname"], "KC")
        self.assertEqual(family, [{
            "name": "Juan Dela Cruz", "edad": "40", "estatus": "College",
            "pinapasukan": "Liceo", "trabaho": "Teacher",
        }])
        self.assertEqual(education[0]["taon"], "2020")
        self.assertEqual(summer, [])

    def test_swafo_rejects_tampered_choices(self):
        for field, value in (
            ("uri_ng_kabuhayan", "Unknown"),
            ("kalagayan_pag_aaral", "Excellent"),
        ):
            with self.subTest(field=field), self.assertRaises(ValueError):
                _validate_swafo_submission(MultiDict([(field, value)]))

    def test_swafo_rejects_invalid_family_age_and_education_year(self):
        with self.assertRaises(ValueError):
            _validate_swafo_submission(MultiDict([
                ("fm_name[]", "Juan"), ("fm_edad[]", "121"),
            ]))

        with self.assertRaises(ValueError):
            _validate_swafo_submission(MultiDict([
                ("ed_antas[]", "Elementary"), ("ed_paaralan[]", "Liceo"),
                ("ed_taon[]", "20x6"),
            ]))

    def test_swafo_submit_requires_yes_no_answers(self):
        with self.assertRaisesRegex(ValueError, "Pumili ng sagot"):
            _validate_swafo_submission(MultiDict(), require_complete=True)

    def test_swafo_template_contains_prefilled_personal_information(self):
        template = (ROOT / "templates" / "student_swafo_form.html").read_text(encoding="utf-8")
        for label in (
            "Pangalan", "Gitnang Pangalan", "Apelyido", "Palayaw", "Edad", "Kasarian",
            "Kapanganakan: Petsa", "Kapanganakan: Lugar", "Tirahan", "Cell Number",
        ):
            self.assertIn(label, template)
        self.assertIn('name="nickname"', template)
        self.assertIn("student_info.contact_number", template)

    def test_swafo_personal_info_is_validated_and_normalized(self):
        personal = _validate_swafo_personal_info(MultiDict({
            "student_first_name": " Maria ", "student_middle_name": "Santos",
            "student_last_name": "Dela Cruz", "gender": "Female", "dob": "2010-05-12",
            "birthplace": "Majayjay, Laguna", "address": "Barangay San Roque, Majayjay",
            "contact_number": "09123456789",
        }))
        self.assertEqual(personal["student_first_name"], "Maria")
        self.assertEqual(personal["contact_number"], "09123456789")

        with self.assertRaises(ValueError):
            _validate_swafo_personal_info(MultiDict({
                "student_first_name": "M", "student_last_name": "Student", "gender": "Female",
                "dob": "2030-01-01", "birthplace": "Laguna", "address": "Valid address",
            }))

    def test_completed_education_levels_follow_current_grade(self):
        cases = (
            ("Nursery", []),
            ("Kinder", []),
            ("Grade 3", ["Kinder"]),
            ("Grade 7", ["Kinder", "Elementary"]),
            ("Grade 11", ["Kinder", "Elementary", "Junior High"]),
        )
        for grade_level, expected in cases:
            with self.subTest(grade_level=grade_level):
                self.assertEqual(_completed_education_levels(grade_level), expected)


if __name__ == "__main__":
    unittest.main()
