import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = (ROOT / "migrations" / "add_grading_item_placements.sql").read_text(encoding="utf-8")
TEACHER = (ROOT / "routes" / "teacher.py").read_text(encoding="utf-8")
CLASS_RECORD = (ROOT / "templates" / "teacher_class_record.html").read_text(encoding="utf-8")
CREATE_ACTIVITY = (ROOT / "templates" / "teacher_create_activity.html").read_text(encoding="utf-8")
CREATE_EXAM = (ROOT / "templates" / "teacher_exam_create.html").read_text(encoding="utf-8")


class GradingItemPlacementTests(unittest.TestCase):
    def test_migration_is_additive_idempotent_and_preserves_legacy_data(self):
        self.assertIn("ADD COLUMN IF NOT EXISTS grading_slot", MIGRATION)
        self.assertIn("ADD COLUMN IF NOT EXISTS class_record_max_score", MIGRATION)
        self.assertIn("ADD COLUMN IF NOT EXISTS grading_component", MIGRATION)
        self.assertIn("SET grading_slot = 'ww_quiz'", MIGRATION)
        self.assertIn("SET grading_component = 'pt'", MIGRATION)
        self.assertNotIn("DROP TABLE", MIGRATION.upper())
        self.assertNotIn("TRUNCATE", MIGRATION.upper())

    def test_manual_assessment_hps_is_persisted_without_student_results(self):
        self.assertIn("class_record_max_score", TEACHER)
        self.assertIn("grading_slot,\n                    class_record_max_score", TEACHER)
        self.assertIn("e.class_record_max_score", TEACHER)
        self.assertIn("UPDATE exams SET class_record_max_score=%s", TEACHER)

    def test_official_ste_slots_are_unique_per_class_record_term(self):
        self.assertIn("CREATE UNIQUE INDEX IF NOT EXISTS uq_exams_official_ste_slot", MIGRATION)
        self.assertIn("'ste_st1', 'ste_st2', 'ste_term_exam'", MIGRATION)
        self.assertIn("grading_period, year_id, grading_slot", MIGRATION)

    def test_spreadsheet_formula_uses_fixed_internal_ste_weights(self):
        self.assertIn('"ste_st1": 0.30', TEACHER)
        self.assertIn('"ste_st2": 0.30', TEACHER)
        self.assertIn('"ste_term_exam": 0.40', TEACHER)
        self.assertIn("qa_score += slot_score * internal_weight", TEACHER)

        ww = 178 / 199 * 20
        pt = 377 / 388 * 50
        ste = ((51 / 70 * 30) + (38 / 50 * 30) + (45.5 / 60 * 40)) * 0.30
        self.assertAlmostEqual(ww + pt + ste, 88.97, places=2)

    def test_ww_and_pt_are_pooled_by_earned_score_and_hps(self):
        self.assertIn("earned, possible = exam_earned + act_earned, exam_possible + act_possible", TEACHER)
        self.assertIn("activity_earned, activity_possible = activity_scores.get", TEACHER)
        self.assertIn("pt_score = act_score if has_activity else 0.0", TEACHER)
        compute = TEACHER[TEACHER.index("def _compute_period_grades"):TEACHER.index("def class_record")]
        self.assertNotIn("FROM attendance_scores", compute)
        self.assertNotIn("FROM participation_scores", compute)

    def test_portal_items_require_explicit_placement(self):
        self.assertIn('name="grading_component"', CREATE_ACTIVITY)
        self.assertIn('value="ww"', CREATE_ACTIVITY)
        self.assertNotIn('<option value="pt"', CREATE_ACTIVITY)
        self.assertIn('name="grading_slot"', CREATE_EXAM)
        self.assertIn('value="ste_st1"', CREATE_EXAM)
        self.assertIn('value="ste_st2"', CREATE_EXAM)
        self.assertIn('value="ste_term_exam"', CREATE_EXAM)

    def test_class_record_exposes_manual_items_without_editing_internal_percentages(self):
        for mode in (
            "quiz", "ww_activity", "ww_assignment",
            "recitation", "project", "assessment",
            "summative_test_1", "summative_test_2", "term_exam",
        ):
            self.assertIn(f"switchBatchMode('{mode}')", CLASS_RECORD)
        self.assertNotIn("switchBatchMode('new_activity')", CLASS_RECORD)
        self.assertIn("ST1 30% + ST2 30% + Exam 40%", CLASS_RECORD)
        self.assertNotIn('name="max_attendance"', CLASS_RECORD)
        self.assertNotIn('name="score_att_', CLASS_RECORD)
        self.assertIn("pooled Recitation (plus Project/Assessment)", CLASS_RECORD)

    def test_submission_ignores_excluded_items_and_respects_major_zero_weights(self):
        submission = TEACHER[
            TEACHER.index("def teacher_submit_grades"):
            TEACHER.index("def teacher_unsubmit_grades")
        ]
        self.assertIn("act['grading_component'] == 'ww' and requires_ww", submission)
        self.assertIn("act['grading_component'] == 'pt'", submission)
        self.assertIn("act['grading_subtype'] in ('recitation', 'project', 'assessment')", submission)
        self.assertIn("and requires_pt", submission)
        self.assertIn("exam_slot(ex) in STE_SLOT_WEIGHTS and requires_ste", submission)
        self.assertIn("not r.get('has_qa_score')", submission)

    def test_locked_records_reject_new_portal_items(self):
        self.assertGreaterEqual(TEACHER.count("_is_class_record_locked("), 5)
        self.assertIn("Cannot create an exam because", TEACHER)
        self.assertIn("Cannot create a quiz because", TEACHER)
        self.assertIn("Cannot add an activity because", TEACHER)


if __name__ == "__main__":
    unittest.main()
