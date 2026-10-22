import unittest

from routes.teacher import _get_deped_transmuted_grade, _get_transmutation_band


class Base70GradingTests(unittest.TestCase):
    def test_base70_boundaries(self):
        self.assertEqual(_get_deped_transmuted_grade(0), 70)
        self.assertEqual(_get_deped_transmuted_grade(50), 85)
        self.assertEqual(_get_deped_transmuted_grade(100), 100)

    def test_base70_clamps_out_of_range_values(self):
        self.assertEqual(_get_deped_transmuted_grade(-1), 70)
        self.assertEqual(_get_deped_transmuted_grade(101), 100)

    def test_invalid_or_missing_grade_remains_missing(self):
        self.assertIsNone(_get_deped_transmuted_grade(None))
        self.assertIsNone(_get_deped_transmuted_grade(""))

    def test_base70_rounding_matches_browser_preview(self):
        self.assertEqual(_get_deped_transmuted_grade(10), 73)
        self.assertEqual(_get_deped_transmuted_grade(16.66), 75)
        self.assertEqual(_get_deped_transmuted_grade(99), 100)

    def test_debug_label_describes_base70_formula(self):
        self.assertEqual(_get_transmutation_band(50), "70 + (50.00 x 0.30) => 85")


if __name__ == "__main__":
    unittest.main()
