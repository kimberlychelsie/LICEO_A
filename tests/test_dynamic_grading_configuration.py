import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = (ROOT / "migrations" / "add_dynamic_grading_configuration.sql").read_text(encoding="utf-8")
ADMIN = (ROOT / "routes" / "branch_admin.py").read_text(encoding="utf-8")
TEACHER = (ROOT / "routes" / "teacher.py").read_text(encoding="utf-8")
ADMIN_TEMPLATE = (ROOT / "templates" / "branch_admin_grading_categories.html").read_text(encoding="utf-8")
TEACHER_TEMPLATE = (ROOT / "templates" / "teacher_grading_components.html").read_text(encoding="utf-8")
WEIGHTS_TEMPLATE = (ROOT / "templates" / "teacher_grading_weights.html").read_text(encoding="utf-8")
CLASS_RECORD_TEMPLATE = (ROOT / "templates" / "teacher_class_record.html").read_text(encoding="utf-8")


class DynamicGradingConfigurationTests(unittest.TestCase):
    def test_migration_is_additive_scoped_and_validated(self):
        self.assertIn("CREATE TABLE IF NOT EXISTS public.grading_categories", MIGRATION)
        self.assertIn("ADD COLUMN IF NOT EXISTS grading_category_id", MIGRATION)
        self.assertIn("CREATE TABLE IF NOT EXISTS public.teacher_component_distributions", MIGRATION)
        self.assertIn("ww_pct + pt_pct + qa_pct = 100", MIGRATION)
        self.assertIn("ww_quiz_pct + ww_monthly_exam_pct = 100", MIGRATION)
        self.assertIn("pt_activity_pct + pt_participation_pct + pt_attendance_pct = 100", MIGRATION)
        self.assertIn("UNIQUE (\n        teacher_id, section_id, subject_id, grading_period, year_id", MIGRATION)

    def test_admin_can_manage_categories_without_hardcoded_options(self):
        self.assertIn('route("/branch-admin/grading-categories"', ADMIN)
        self.assertIn('session.get("role") != "branch_admin"', ADMIN)
        self.assertIn("WW, PT, and QA must total exactly 100%", ADMIN)
        self.assertIn('status not in ("all", "active", "inactive")', ADMIN)
        self.assertIn("LIMIT %s OFFSET %s", ADMIN)
        self.assertIn("per_page = 4", ADMIN)
        self.assertIn("math.isfinite", ADMIN)
        self.assertIn("form_errors", ADMIN)
        self.assertIn("{% for category in grading_categories %}", (ROOT / "templates" / "branch_admin_subjects.html").read_text(encoding="utf-8"))
        self.assertIn("Add Category", ADMIN_TEMPLATE)
        self.assertIn(">Apply</button>", ADMIN_TEMPLATE)
        self.assertIn("updateFormState", ADMIN_TEMPLATE)
        self.assertIn('id="categoryModal"', ADMIN_TEMPLATE)
        self.assertIn("openAddModal", ADMIN_TEMPLATE)
        self.assertIn("openCategoryModal", ADMIN_TEMPLATE)
        self.assertIn("submitButton.disabled=!(valid&&changed())", ADMIN_TEMPLATE)
        self.assertIn("gc-segment ww", ADMIN_TEMPLATE)
        self.assertIn("Subject Assignments", ADMIN_TEMPLATE)
        self.assertIn("COUNT(DISTINCT gc.category_id)", ADMIN)
        self.assertIn("SET is_active=NOT gc.is_active", ADMIN)
        self.assertIn("gc-manage-trigger", ADMIN_TEMPLATE)
        self.assertIn("aria-haspopup", ADMIN_TEMPLATE)

    def test_teacher_distribution_is_owned_scoped_and_locked(self):
        route = TEACHER[TEACHER.index("def grading_component_distribution"):TEACHER.index("def _compute_period_grades")]
        self.assertIn("st.teacher_id=%s", route)
        self.assertIn("sec.branch_id=%s", route)
        self.assertIn("pending_registrar", route)
        self.assertNotIn("WHERE teacher_id=%s AND section_id=%s", route)
        self.assertIn("WHERE section_id=%s AND subject_id=%s", route)
        self.assertIn("ON CONFLICT (teacher_id,section_id,subject_id,grading_period,year_id)", route)
        self.assertIn("must total 100%", TEACHER_TEMPLATE)

    def test_computation_preserves_legacy_until_teacher_saves(self):
        compute = TEACHER[TEACHER.index("def _compute_period_grades"):]
        self.assertIn("if distribution:", compute)
        self.assertIn("else:\n            ww_score = _cap_0_100(quiz_scores.get(eid, 0))", compute)
        self.assertIn("pt_activity_pct", compute)
        self.assertIn("get_assignment_grading_weights", compute)

    def test_zero_weight_components_do_not_block_submission(self):
        submission = TEACHER[TEACHER.index("def teacher_submit_grades"):TEACHER.index("def teacher_unsubmit_grades")]
        self.assertIn("requires_qa = float(weights.get('exam_pct') or 0) > 0", submission)
        self.assertIn("requires_qa and not r.get('has_qa_score')", submission)
        self.assertIn("and requires_qa", submission)
        self.assertIn(">Add Category</button>", ADMIN_TEMPLATE)

    def test_component_configuration_is_inside_each_term_record(self):
        self.assertNotIn("config_period in ['1st', '2nd', '3rd']", WEIGHTS_TEMPLATE)
        self.assertIn('id="componentModal"', CLASS_RECORD_TEMPLATE)
        self.assertIn("openComponentModal", CLASS_RECORD_TEMPLATE)
        self.assertIn('name="return_to" value="class_record"', CLASS_RECORD_TEMPLATE)
        self.assertIn("period=period", CLASS_RECORD_TEMPLATE)
        self.assertIn("{% if period != 'final' %}", CLASS_RECORD_TEMPLATE)
        route = TEACHER[TEACHER.index("def grading_component_distribution"):TEACHER.index("def _compute_period_grades")]
        self.assertIn('request.form.get("return_to") == "class_record"', route)


if __name__ == "__main__":
    unittest.main()
