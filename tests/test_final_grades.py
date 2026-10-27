import os
import unittest
from decimal import Decimal
from unittest.mock import patch

from services.final_grades import (
    AmbiguousGradingPolicyError,
    GradingPolicy,
    InvalidGradingPolicyError,
    MissingGradingPolicyError,
    PeriodGrade,
    calculate_final_grade,
    grading_policy_final_grades_enabled,
    load_active_grading_policy,
    load_effective_grading_policy,
    required_grading_periods,
    validate_academic_term_name,
    validate_required_period,
)


def policy(periods=("1st", "2nd", "3rd"), scale=0):
    return GradingPolicy(
        policy_id=7, branch_id=2, year_id=9, policy_version="test-v1",
        rounding_mode="excel_round", rounding_scale=scale,
        status="active", required_periods=tuple(periods),
    )


class FakeCursor:
    def __init__(self, policies, periods=()):
        self.policies = policies
        self.periods = periods
        self.result = None

    def execute(self, sql, params):
        self.result = self.periods if "grading_policy_periods" in sql else self.policies

    def fetchall(self):
        return self.result


class FinalGradeServiceTests(unittest.TestCase):
    def test_period_validation_supports_three_four_and_five_term_policies(self):
        self.assertEqual(validate_required_period("3rd", ("1st", "2nd", "3rd")), "3rd")
        self.assertEqual(validate_required_period("4th", ("1st", "2nd", "3rd", "4th")), "4th")
        self.assertEqual(
            validate_required_period("5th", ("1st", "2nd", "3rd", "4th", "5th")),
            "5th",
        )
        with self.assertRaises(InvalidGradingPolicyError):
            validate_required_period("4th", ("1st", "2nd", "3rd"))

    def test_academic_term_validation_accepts_policy_terms_and_full_year_only(self):
        periods = ("1st", "2nd", "3rd", "4th", "5th")
        self.assertEqual(validate_academic_term_name("5th Term", periods), "5th Term")
        self.assertEqual(validate_academic_term_name("Full Year", periods), "Full Year")
        self.assertIsNone(validate_academic_term_name("", periods))
        with self.assertRaises(InvalidGradingPolicyError):
            validate_academic_term_name("6th Term", periods)

    def test_three_term_excel_rounding_and_input_immutability(self):
        grades = [PeriodGrade("1st", 80), PeriodGrade("2nd", 81), PeriodGrade("3rd", 82)]
        snapshot = list(grades)
        result = calculate_final_grade(policy(), grades)
        self.assertTrue(result.complete)
        self.assertEqual(result.final_grade, Decimal("81"))
        self.assertEqual(grades, snapshot)

    def test_four_term_policy_has_no_global_period_count(self):
        result = calculate_final_grade(
            policy(("1st", "2nd", "3rd", "4th")),
            [PeriodGrade("4th", 88), PeriodGrade("2nd", 86),
             PeriodGrade("1st", 84), PeriodGrade("3rd", 90)],
        )
        self.assertEqual(result.required_periods, ("1st", "2nd", "3rd", "4th"))
        self.assertEqual(result.final_grade, Decimal("87"))

    def test_five_term_policy_has_no_global_period_count(self):
        result = calculate_final_grade(
            policy(("1st", "2nd", "3rd", "4th", "5th")),
            [PeriodGrade("1st", 80), PeriodGrade("2nd", 81),
             PeriodGrade("3rd", 82), PeriodGrade("4th", 83),
             PeriodGrade("5th", 84)],
        )
        self.assertTrue(result.complete)
        self.assertEqual(result.required_periods, ("1st", "2nd", "3rd", "4th", "5th"))
        self.assertEqual(result.final_grade, Decimal("82"))

    def test_historical_three_term_policy_is_not_changed_by_other_calendar_terms(self):
        result = calculate_final_grade(
            policy(("1st", "2nd", "3rd")),
            [PeriodGrade("1st", 80), PeriodGrade("2nd", 85), PeriodGrade("3rd", 90)],
        )
        self.assertTrue(result.complete)
        self.assertEqual(result.final_grade, Decimal("85"))

    def test_excel_half_up_boundary(self):
        result = calculate_final_grade(
            policy(("1st", "2nd")),
            [PeriodGrade("1st", 80), PeriodGrade("2nd", 81)],
        )
        self.assertEqual(result.final_grade, Decimal("81"))

    def test_incomplete_grade_is_not_averaged(self):
        result = calculate_final_grade(
            policy(), [PeriodGrade("1st", 90), PeriodGrade("2nd", 80, completed=False)]
        )
        self.assertFalse(result.complete)
        self.assertIsNone(result.final_grade)
        self.assertEqual(result.error_code, "invalid_or_incomplete_period_grades")
        self.assertEqual(result.missing_periods, ("3rd",))

    def test_duplicate_and_unexpected_grades_are_rejected(self):
        duplicate = calculate_final_grade(
            policy(), [PeriodGrade("1st", 80), PeriodGrade("1st", 81),
                       PeriodGrade("2nd", 82), PeriodGrade("3rd", 83)]
        )
        self.assertEqual(duplicate.duplicate_periods, ("1st",))
        self.assertIsNone(duplicate.final_grade)
        unexpected = calculate_final_grade(
            policy(), [PeriodGrade("1st", 80), PeriodGrade("2nd", 82),
                       PeriodGrade("3rd", 83), PeriodGrade("4th", 84)]
        )
        self.assertEqual(unexpected.unexpected_periods, ("4th",))
        self.assertIsNone(unexpected.final_grade)

    def test_invalid_values_and_noncanonical_names_are_rejected(self):
        result = calculate_final_grade(
            policy(), [PeriodGrade("1st", float("nan")), PeriodGrade("2nd", 82),
                       PeriodGrade("3rd", 83)]
        )
        self.assertEqual(result.invalid_periods, ("1st",))
        with self.assertRaises(InvalidGradingPolicyError):
            calculate_final_grade(policy(("First",)), [PeriodGrade("First", 90)])

    def test_policy_loader_requires_exactly_one_active_policy(self):
        with self.assertRaises(MissingGradingPolicyError):
            load_active_grading_policy(FakeCursor([]), branch_id=2, year_id=9)
        rows = [(1, 2, 9, "a", "excel_round", 0, "active")] * 2
        with self.assertRaises(AmbiguousGradingPolicyError):
            load_active_grading_policy(FakeCursor(rows), branch_id=2, year_id=9)

    def test_policy_loader_preserves_explicit_order(self):
        row = [(7, 2, 9, "test-v1", "excel_round", 0, "active")]
        loaded = load_active_grading_policy(
            FakeCursor(row, [(1, "1st"), (2, "2nd"), (3, "3rd"), (4, "4th")]),
            branch_id=2, year_id=9,
        )
        self.assertEqual(loaded.required_periods, ("1st", "2nd", "3rd", "4th"))

    def test_dynamic_policy_integration_is_enabled_by_default(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertTrue(grading_policy_final_grades_enabled())

    def test_explicit_emergency_rollback_preserves_legacy_periods_without_querying(self):
        cursor = FakeCursor([])
        with patch.dict(os.environ, {"GRADING_POLICY_FINAL_GRADES_ENABLED": "false"}):
            self.assertIsNone(
                load_effective_grading_policy(cursor, branch_id=2, year_id=9)
            )
            self.assertEqual(
                required_grading_periods(
                    cursor, branch_id=2, year_id=9,
                    legacy_periods=("1st", "2nd", "3rd"),
                ),
                ("1st", "2nd", "3rd"),
            )

    def test_enabled_integration_requires_explicit_policy(self):
        with patch.dict(os.environ, {"GRADING_POLICY_FINAL_GRADES_ENABLED": "true"}):
            with self.assertRaises(MissingGradingPolicyError):
                load_effective_grading_policy(
                    FakeCursor([]), branch_id=2, year_id=9
                )


if __name__ == "__main__":
    unittest.main()
