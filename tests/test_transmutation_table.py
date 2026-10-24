import unittest
from pathlib import Path

from routes.teacher import (
    TRANSMUTATION_RANGES,
    _get_deped_transmuted_grade,
    _get_transmutation_band,
)


ROOT = Path(__file__).resolve().parents[1]
TEACHER_ROUTE = (ROOT / "routes" / "teacher.py").read_text(encoding="utf-8")
CLASS_RECORD = (ROOT / "templates" / "teacher_class_record.html").read_text(encoding="utf-8")


class TransmutationTableTests(unittest.TestCase):
    def test_confirmed_boundaries(self):
        cases = {
            0: 60,
            4.67: 60,
            4.68: 61,
            4.675: 61,
            46.66: 69,
            46.67: 70,
            69.99: 74,
            70.00: 75,
            88.97: 91,
            99.49: 99,
            99.50: 100,
            100: 100,
        }
        for initial, expected in cases.items():
            with self.subTest(initial=initial):
                self.assertEqual(_get_deped_transmuted_grade(initial), expected)

    def test_every_range_endpoint_maps_to_its_grade(self):
        self.assertEqual(len(TRANSMUTATION_RANGES), 41)
        for lower, upper, expected in TRANSMUTATION_RANGES:
            with self.subTest(lower=lower, upper=upper, expected=expected):
                self.assertEqual(_get_deped_transmuted_grade(lower), expected)
                self.assertEqual(_get_deped_transmuted_grade(upper), expected)

    def test_out_of_range_values_are_clamped(self):
        self.assertEqual(_get_deped_transmuted_grade(-1), 60)
        self.assertEqual(_get_deped_transmuted_grade(101), 100)

    def test_invalid_or_nonfinite_grade_remains_missing(self):
        self.assertIsNone(_get_deped_transmuted_grade(None))
        self.assertIsNone(_get_deped_transmuted_grade(""))
        self.assertIsNone(_get_deped_transmuted_grade(float("nan")))
        self.assertIsNone(_get_deped_transmuted_grade(float("inf")))

    def test_debug_label_describes_matched_table_band(self):
        self.assertEqual(_get_transmutation_band(50), "46.67 to 51.33 => 70")

    def test_browser_preview_uses_the_same_server_table(self):
        self.assertIn("transmutation_ranges=TRANSMUTATION_RANGES", TEACHER_ROUTE)
        self.assertIn(
            "const TRANSMUTATION_RANGES = {{ transmutation_ranges | tojson }};",
            CLASS_RECORD,
        )
        self.assertNotIn("Math.round(70 +", CLASS_RECORD)
        self.assertNotIn("base-70", CLASS_RECORD.lower())


if __name__ == "__main__":
    unittest.main()
