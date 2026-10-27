import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


def source(relative):
    return (ROOT / relative).read_text(encoding="utf-8")


class GradingPolicyRoleIntegrationTests(unittest.TestCase):
    def test_teacher_summary_and_export_use_shared_service(self):
        teacher = source("routes/teacher.py")
        template = source("templates/teacher_class_record.html")
        self.assertGreaterEqual(teacher.count("calculate_final_grade("), 2)
        self.assertIn("final_grade_policy.required_periods", teacher)
        self.assertIn("'period_grades': grades", teacher)
        self.assertIn("for required_period in grading_periods", template)
        self.assertIn("{{ r.final_grade | int }}", template)
        self.assertNotIn("r.grade_3rd", template)

    def test_teacher_class_record_supports_fifth_and_later_policy_terms(self):
        teacher = source("routes/teacher.py")
        class_record = source("templates/teacher_class_record.html")
        weights = source("templates/teacher_grading_weights.html")
        submit_block = teacher[
            teacher.index("def teacher_submit_grades"):
            teacher.index("def teacher_unsubmit_grades")
        ]
        self.assertIn("configured_periods.index(period)", submit_block)
        self.assertIn("previous_period = configured_periods[period_index - 1]", submit_block)
        self.assertNotIn("if period == '2nd'", submit_block)
        self.assertNotIn("elif period == '3rd'", submit_block)
        self.assertIn("p ~ ' Term'", class_record)
        self.assertIn("for grading_period in grading_periods", weights)
        self.assertNotIn("period='3rd'", weights)

    def test_teacher_dashboard_reports_missing_policy_without_legacy_fallback(self):
        teacher = source("routes/teacher.py")
        dashboard_block = teacher[
            teacher.index("def teacher_dashboard"):
            teacher.index("def teacher_profile")
        ]
        self.assertIn("except GradingPolicyError as exc", dashboard_block)
        self.assertIn("configured_periods = []", dashboard_block)
        self.assertIn("Grading policy configuration error", dashboard_block)

    def test_student_parent_and_transfer_use_shared_service(self):
        student = source("routes/student_portal.py")
        parent = source("routes/parent.py")
        registrar = source("routes/registrar.py")
        transfer_template = source("templates/registrar_student_transfers.html")
        self.assertIn("calculate_final_grade(policy", student)
        self.assertIn("calculate_final_grade(final_grade_policy", parent)
        self.assertIn("configured_terms[:configured_terms.index(effective_term)]", registrar)
        self.assertIn("for term in transfer_terms", transfer_template)

    def test_student_grade_enrollments_include_policy_ownership(self):
        student = source("routes/student_portal.py")
        grades = student[
            student.index("def student_grades"):
            student.index("def student_my_schedule")
        ]
        self.assertGreaterEqual(grades.count("e.branch_id, e.year_id"), 2)
        self.assertGreaterEqual(
            grades.count("e.year_id = sy.year_id AND e.branch_id = sy.branch_id"), 2
        )
        self.assertIn('branch_id=enr["branch_id"], year_id=enr["year_id"]', grades)
        self.assertNotIn("e.student_first_name = %s", grades)

    def test_student_missing_policy_is_rendered_without_keyerror_or_fallback(self):
        student = source("routes/student_portal.py")
        template = source("templates/student_grades.html")
        grades = student[
            student.index("def student_grades"):
            student.index("def student_my_schedule")
        ]
        self.assertIn("policy_error = str(exc)", grades)
        self.assertIn("if policy_error or not section_id", grades)
        self.assertIn("grading_periods = []", grades)
        self.assertIn("grading_policy_error=policy_error", grades)
        self.assertIn("{% if grading_policy_error %}", template)
        self.assertNotIn("{{ grading_policy_error }}", template)

    def test_parent_policy_uses_each_selected_child_enrollment(self):
        parent = source("routes/parent.py")
        template = source("templates/parent_child_detail.html")
        detail = parent[
            parent.index("def child_detail"):
            parent.index("def parent_bills")
        ]
        self.assertIn("WHERE ps.parent_id=%s AND ps.student_id=%s", detail)
        self.assertIn('branch_id=child["branch_id"], year_id=child["year_id"]', detail)
        self.assertNotIn('branch_id=session.get("branch_id")', detail)
        self.assertIn("e.year_id = sy.year_id AND e.branch_id = sy.branch_id", detail)
        self.assertIn("grading_policy_error = str(exc)", detail)
        self.assertIn("grading_periods = []", detail)
        self.assertIn("grading_policy_error=grading_policy_error", detail)
        self.assertIn("{% for period in grading_periods %}", template)
        self.assertNotIn('<th style="text-align:center;">1st Term</th>', template)
        self.assertNotIn("{{ grading_policy_error }}", template)

    def test_calendar_detection_has_no_fixed_three_term_sql_gate(self):
        for relative in (
            "app.py", "routes/teacher.py", "routes/student_portal.py",
            "routes/registrar.py",
        ):
            self.assertNotIn(
                "period_name IN ('1st', '2nd', '3rd')", source(relative), relative
            )

    def test_transfer_period_order_is_not_capped_at_third_term(self):
        teacher = source("routes/teacher.py")
        self.assertNotIn("CASE tr.effective_term WHEN '1st'", teacher)
        self.assertIn("regexp_replace(tr.effective_term", teacher)

    def test_remaining_role_filters_render_the_applicable_policy_periods(self):
        for relative in (
            "templates/registrar_grade_review.html",
            "templates/branch_admin_grade_approval.html",
            "templates/teacher_activities.html",
            "templates/teacher_quizzes.html",
            "templates/teacher_exams.html",
            "templates/teacher_schedules.html",
            "templates/schedules_allinone.html",
        ):
            markup = source(relative)
            self.assertIn("for period in grading_periods", markup, relative)
            self.assertNotIn('value="1st"', markup, relative)
            self.assertNotIn('value="2nd"', markup, relative)
            self.assertNotIn('value="3rd"', markup, relative)

    def test_teacher_subject_detail_shows_but_locks_future_policy_terms(self):
        detail = source("templates/teacher_subject_detail.html")
        self.assertGreaterEqual(detail.count("for period in grading_periods"), 3)
        self.assertGreaterEqual(detail.count("period not in unlocked_periods"), 3)
        self.assertIn("(Future)", detail)

    def test_subject_and_schedule_mutations_validate_policy_terms(self):
        for relative in ("routes/registrar.py", "routes/branch_admin.py"):
            route_source = source(relative)
            self.assertIn("validate_academic_term_name(term_name, configured_periods)", route_source)
            self.assertIn("validate_academic_term_name(term_name, grading_periods)", route_source)
        for relative in (
            "templates/registrar_subjects.html", "templates/branch_admin_subjects.html"
        ):
            markup = source(relative)
            self.assertIn("configuredPeriodOptions", markup)
            self.assertIn("grading_periods|tojson", markup)

    def test_student_all_terms_grouping_is_policy_driven(self):
        student = source("routes/student_portal.py")
        template = source("templates/student_grades.html")
        grades = student[
            student.index("def student_grades"):
            student.index("def student_my_schedule")
        ]
        self.assertIn("grade_term_groups", grades)
        self.assertIn("for period in grading_periods", grades)
        self.assertIn("future_terms", grades)
        self.assertIn("for group in grade_term_groups", template)
        self.assertNotIn("ns_terms.t3", template)
        self.assertNotIn("subj.grades.get('3rd')", template)

    def test_academic_calendar_heading_uses_selected_branch_year(self):
        route_source = source("routes/branch_admin.py")
        template = source("templates/branch_admin_academic_calendar.html")
        calendar = route_source[
            route_source.index("def branch_admin_academic_calendar"):
            route_source.index("# --- MOVED FROM REGISTRAR ---")
        ]
        self.assertIn("WHERE year_id = %s AND branch_id = %s", calendar)
        self.assertIn("school_year_label=school_year_label", calendar)
        self.assertIn("{{ school_year_label }}", template)
        self.assertNotIn("session.get('active_sy_label'", template)


if __name__ == "__main__":
    unittest.main()
