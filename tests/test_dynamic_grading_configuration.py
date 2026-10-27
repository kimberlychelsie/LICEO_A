import unittest
from pathlib import Path

from utils.grading_configuration import get_assignment_grading_weights


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = (ROOT / "migrations" / "add_dynamic_grading_configuration.sql").read_text(encoding="utf-8")
ADMIN = (ROOT / "routes" / "branch_admin.py").read_text(encoding="utf-8")
REGISTRAR = (ROOT / "routes" / "registrar.py").read_text(encoding="utf-8")
TEACHER = (ROOT / "routes" / "teacher.py").read_text(encoding="utf-8")
ADMIN_SUBJECTS = (ROOT / "templates" / "branch_admin_subjects.html").read_text(encoding="utf-8")
REGISTRAR_SUBJECTS = (ROOT / "templates" / "registrar_subjects.html").read_text(encoding="utf-8")
CLASS_RECORD = (ROOT / "templates" / "teacher_class_record.html").read_text(encoding="utf-8")
WEIGHT_OVERVIEW = (ROOT / "templates" / "teacher_grading_weights.html").read_text(encoding="utf-8")
CONFIG = (ROOT / "utils" / "grading_configuration.py").read_text(encoding="utf-8")


class StubCursor:
    def __init__(self, rows):
        self.rows = iter(rows)
        self.calls = []

    def execute(self, statement, params=None):
        self.calls.append((statement, params))

    def fetchone(self):
        return next(self.rows)


class DynamicGradingConfigurationTests(unittest.TestCase):
    def test_recognized_legacy_category_is_only_a_suggestion(self):
        cursor = StubCursor([
            {"available": True},
            None,
            {"deped_category": "science_math"},
        ])
        weights = get_assignment_grading_weights(cursor, 7, 2, 9, 11, 13, "4th")
        self.assertFalse(weights["configured"])
        self.assertTrue(weights["suggested_available"])
        self.assertEqual((weights["ww"], weights["pt"], weights["qa"]), (0.40, 0.40, 0.20))
        self.assertEqual(cursor.calls[1][1], (7, 2, 9, 11, 13, "4th"))

    def test_unknown_category_keeps_computation_fallback_but_not_suggestion(self):
        cursor = StubCursor([
            {"available": True},
            None,
            {"deped_category": "unknown"},
        ])
        weights = get_assignment_grading_weights(cursor, 7, 2, 9, 11, 13, "1st")
        self.assertFalse(weights["configured"])
        self.assertFalse(weights["suggested_available"])
        self.assertEqual(weights["name"], "No recognized suggested distribution")
        # Phase 1 intentionally leaves the numerical resolver unchanged.
        self.assertEqual((weights["ww"], weights["pt"], weights["qa"]), (0.30, 0.50, 0.20))

    def test_saved_teacher_configuration_is_authoritative(self):
        cursor = StubCursor([
            {"available": True},
            {"weight_id": 5, "ww_pct": 0, "pt_pct": 70, "qa_pct": 30},
        ])
        weights = get_assignment_grading_weights(cursor, 7, 2, 9, 11, 13, "5th")
        self.assertTrue(weights["configured"])
        self.assertFalse(weights["suggested_available"])
        self.assertEqual((weights["ww"], weights["pt"], weights["qa"]), (0.0, 0.70, 0.30))

    def test_migration_is_teacher_owned_scoped_and_validated(self):
        self.assertIn("CREATE TABLE IF NOT EXISTS public.teacher_grading_weights", MIGRATION)
        self.assertIn("ww_pct + pt_pct + qa_pct = 100", MIGRATION)
        self.assertIn("grading_period ~ '^[1-9][0-9]*(st|nd|rd|th)$'", MIGRATION)
        self.assertIn(
            "teacher_id, section_id, subject_id, grading_period, year_id",
            MIGRATION,
        )
        self.assertNotIn("CREATE TABLE IF NOT EXISTS public.teacher_component_distributions", MIGRATION)
        self.assertNotIn("CREATE TABLE IF NOT EXISTS public.grading_categories", MIGRATION)

    def test_branch_admin_no_longer_manages_grading_weights(self):
        self.assertNotIn('route("/branch-admin/grading-categories"', ADMIN)
        self.assertNotIn("Manage Categories", ADMIN_SUBJECTS)
        self.assertNotIn('name="categories"', ADMIN_SUBJECTS)
        self.assertNotIn("grading_categories", ADMIN_SUBJECTS)
        self.assertNotIn('name="categories"', REGISTRAR_SUBJECTS)
        self.assertNotIn('name="deped_category"', REGISTRAR_SUBJECTS)
        self.assertNotIn('request.form.get("deped_category"', REGISTRAR)

    def test_teacher_weight_save_is_owned_scoped_and_locked(self):
        route = TEACHER[
            TEACHER.index("def grading_component_distribution"):
            TEACHER.index("def _assert_student_gradeable_for_period")
        ]
        self.assertIn("st.teacher_id=%s", route)
        self.assertIn("sec.branch_id=%s", route)
        self.assertIn("pending_registrar", route)
        self.assertIn("INSERT INTO teacher_grading_weights", route)
        self.assertIn("WW, PT, and QA must total exactly 100%", route)
        self.assertIn(
            "ON CONFLICT (teacher_id,section_id,subject_id,grading_period,year_id)",
            route,
        )

        submission = TEACHER[
            TEACHER.index("def teacher_submit_grades"):
            TEACHER.index("def teacher_unsubmit_grades")
        ]
        self.assertIn("s.branch_id=%s", submission)

    def test_class_record_modal_edits_only_major_weights(self):
        self.assertIn('name="ww_pct"', CLASS_RECORD)
        self.assertIn('name="pt_pct"', CLASS_RECORD)
        self.assertIn('name="qa_pct"', CLASS_RECORD)
        self.assertNotIn('name="ww_quiz_pct"', CLASS_RECORD)
        self.assertNotIn('name="pt_activity_pct"', CLASS_RECORD)
        self.assertIn("Suggested Defaults — Not Yet Saved", CLASS_RECORD)
        self.assertIn("Save and Confirm Weights", CLASS_RECORD)
        self.assertIn("totalValid&&(!componentConfigured||changed)", CLASS_RECORD)
        self.assertIn("input.value.trim()!==''", CLASS_RECORD)
        self.assertIn("Total is exactly 100%.", CLASS_RECORD)

    def test_unknown_legacy_category_is_not_presented_as_a_suggestion(self):
        self.assertIn("suggested_available = source_code in LEGACY_WEIGHTS", CONFIG)
        self.assertIn('"No recognized suggested distribution"', CONFIG)
        self.assertIn("No recognized suggested distribution is available", CLASS_RECORD)
        self.assertIn("if show_weight_values else ''", CLASS_RECORD)

    def test_backend_rejects_blank_and_avoids_unchanged_saved_update(self):
        route = TEACHER[
            TEACHER.index("def grading_component_distribution"):
            TEACHER.index("def _assert_student_gradeable_for_period")
        ]
        self.assertIn("len(values) != len(fields)", route)
        self.assertIn("not math.isfinite(value)", route)
        self.assertIn("value < 0 or value > 100", route)
        self.assertIn('weights.get("configured") and all(', route)
        self.assertIn("already saved with these values", route)
        self.assertIn("pending_academic_coordinator", route)

    def test_internal_scores_are_pooled_not_distributed(self):
        compute = TEACHER[TEACHER.index("def _compute_period_grades"):]
        self.assertIn("activity_earned, activity_possible = activity_scores.get", compute)
        self.assertIn("pt_score = act_score if has_activity else 0.0", compute)
        self.assertIn("No Participation/Attendance", compute)
        self.assertNotIn("get_teacher_component_distribution", TEACHER)
        self.assertNotIn("teacher_component_distributions", CONFIG)

    def test_zero_weight_major_components_do_not_block_submission(self):
        submission = TEACHER[
            TEACHER.index("def teacher_submit_grades"):
            TEACHER.index("def teacher_unsubmit_grades")
        ]
        self.assertIn("requires_ww = float(weights.get('quiz_pct') or 0) > 0", submission)
        self.assertIn("requires_pt = float(weights.get('activity_pct') or 0) > 0", submission)
        self.assertIn("requires_ste = float(weights.get('exam_pct') or 0) > 0", submission)
        self.assertIn('if not weights.get("configured")', submission)

    def test_teacher_can_safely_reopen_locked_records(self):
        reopen = TEACHER[
            TEACHER.index("def teacher_unsubmit_grades"):
            TEACHER.index("def teacher_post_grades")
        ]
        self.assertIn("approved_for_posting", reopen)
        self.assertIn("previous_status == 'posted'", reopen)
        self.assertNotIn("DELETE FROM posted_grades", reopen)
        self.assertIn("last published grades remain visible until reposted", reopen)
        self.assertIn("s.branch_id=%s", reopen)
        self.assertIn("FOR UPDATE OF st", reopen)
        self.assertIn("Locked later terms must be reopened in reverse order", reopen)
        self.assertIn("registrar_approved_by = NULL", reopen)
        self.assertIn("admin_approved_by = NULL", reopen)
        self.assertIn("Reopen for Editing", CLASS_RECORD)
        self.assertIn("currently published grades will remain visible", CLASS_RECORD)

        post = TEACHER[TEACHER.index("def teacher_post_grades"):]
        self.assertIn("s.branch_id=%s", post)
        self.assertIn("FOR UPDATE OF st", post)
        self.assertIn("SELECT id, status FROM grade_submission_requests", post)
        self.assertIn("FOR UPDATE", post)

    def test_academic_coordinator_filters_do_not_depend_on_pending_rows(self):
        review = TEACHER[
            TEACHER.index("def academic_coordinator_grade_review"):
            TEACHER.index("def academic_coordinator_approve_grade_request")
        ]
        grade_filter_query = review[
            review.index("# Filters describe the active branch/year"):
            review.index("grade_levels = cur.fetchall()")
        ]
        self.assertIn("FROM sections s", grade_filter_query)
        self.assertIn("s.branch_id = %s AND s.year_id = %s", grade_filter_query)
        self.assertNotIn("grade_submission_requests", grade_filter_query)
        self.assertIn("WHEN 'nursery' THEN 0", grade_filter_query)
        self.assertIn("WHEN 'kinder' THEN 1", grade_filter_query)
        self.assertIn("WHEN 'grade 1' THEN 2", grade_filter_query)
        self.assertIn("WHEN 'grade 12' THEN 13", grade_filter_query)
        self.assertIn("grade_key", review)
        self.assertIn("pending_academic_coordinator", review)

    def test_weight_overview_does_not_duplicate_assignment_list(self):
        self.assertEqual(WEIGHT_OVERVIEW.count("{% for a in assignments %}"), 1)
        self.assertIn('id="gwSearch"', WEIGHT_OVERVIEW)
        self.assertIn('id="gwStatusFilter"', WEIGHT_OVERVIEW)
        self.assertIn('data-status="{{ \'saved\' if a.configured else \'unsaved\' }}"', WEIGHT_OVERVIEW)
        self.assertIn("assignment details are intentionally not duplicated", WEIGHT_OVERVIEW)
        overview = TEACHER[
            TEACHER.index("def grading_weights"):
            TEACHER.index("def grading_weights_set")
        ]
        self.assertIn("'configured': w['configured']", overview)


if __name__ == "__main__":
    unittest.main()
