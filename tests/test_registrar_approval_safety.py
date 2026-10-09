import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRAR = (ROOT / "routes" / "registrar.py").read_text()
STUDENT = (ROOT / "routes" / "student.py").read_text()
DASHBOARD = (ROOT / "templates" / "registrar_dashboard.html").read_text()
EDIT_TEMPLATE = (ROOT / "templates" / "student_enroll_edit.html").read_text()
TRACK_TEMPLATE = (ROOT / "templates" / "track_enrollment.html").read_text()


class RegistrarApprovalSafetyTest(unittest.TestCase):
    def test_approval_locks_pending_active_year_enrollment(self):
        self.assertIn("FOR UPDATE", REGISTRAR)
        self.assertIn("AND status = 'pending'", REGISTRAR)
        self.assertIn("Only pending applications in the active school year can be approved.", REGISTRAR)

    def test_approval_reruns_identity_validation(self):
        self.assertIn("from routes.student import validate_student_identity", REGISTRAR)
        self.assertIn("exclude_enrollment_id=enrollment_id", REGISTRAR)
        self.assertIn('identity_result["action"] == "block"', REGISTRAR)

    def test_approval_records_distinct_student_decision(self):
        self.assertIn("def _save_identity_review_decision", REGISTRAR)
        self.assertNotIn("Verified as distinct student through standard Registrar approval.", REGISTRAR)
        self.assertIn("identity_distinct_confirm", REGISTRAR)
        self.assertIn("Please confirm this is a distinct student", REGISTRAR)
        self.assertIn('"distinct_student"', REGISTRAR)

    def test_reject_updates_only_pending_application(self):
        self.assertIn("SET status=%s, rejection_reason=%s, rejected_at=NOW()", REGISTRAR)
        self.assertIn("WHERE enrollment_id=%s AND branch_id=%s AND year_id=%s AND status='pending'", REGISTRAR)

    def test_account_creation_keeps_independent_identity_check(self):
        self.assertIn("def create_student_account", REGISTRAR)
        self.assertIn("Identity review must be confirmed as Distinct Student before creating this account.", REGISTRAR)
        self.assertIn("SELECT 1 FROM student_accounts WHERE enrollment_id=%s", REGISTRAR)

    def test_public_enrollment_keeps_lrn_optional_and_email_contextual(self):
        self.assertIn("if lrn and (not lrn.isdigit() or len(lrn) != 12):", STUDENT)
        self.assertIn("identity_result = validate_student_identity(cursor, student_name, dob, lrn, email)", STUDENT)
        self.assertIn("new_email=new_email", STUDENT)

    def test_registrar_import_locks_before_branch_enrollment_number_allocation(self):
        self.assertIn("from routes.student import acquire_branch_enrollment_no_lock", REGISTRAR)
        lock_pos = REGISTRAR.index("acquire_branch_enrollment_no_lock(cursor, branch_id)")
        max_pos = REGISTRAR.index("SELECT COALESCE(MAX(branch_enrollment_no), 0) + 1 AS next_no")
        insert_pos = REGISTRAR.index("INSERT INTO enrollments (", max_pos)
        commit_pos = REGISTRAR.index("db.commit()", insert_pos)
        self.assertLess(lock_pos, max_pos)
        self.assertLess(max_pos, insert_pos)
        self.assertLess(insert_pos, commit_pos)

    def test_large_identity_review_panel_is_not_visible_on_registrar_dashboard(self):
        self.assertNotIn("Identity Review", DASHBOARD)
        self.assertNotIn("Confirm Existing Student", DASHBOARD)
        self.assertIn("I verified this is a different student", DASHBOARD)
        self.assertIn("Reason for confirmation", DASHBOARD)
        self.assertIn("identity_review_required", DASHBOARD)
        self.assertNotIn("Review complete", DASHBOARD)
        self.assertIn("Documents reviewed", DASHBOARD)

    def test_dashboard_uses_effective_identity_review_requirement(self):
        self.assertIn('e["identity_review_required"] = False', REGISTRAR)
        self.assertIn('e["identity_review_required"] = True', REGISTRAR)
        self.assertIn('from routes.student import validate_student_identity', REGISTRAR)
        self.assertIn('exclude_enrollment_id=e.get("enrollment_id")', REGISTRAR)
        self.assertIn('identity_result["action"] == "review"', REGISTRAR)

    def test_existing_student_review_locks_pending_branch_enrollment(self):
        route_pos = REGISTRAR.index("def decide_identity_review")
        select_pos = REGISTRAR.index("SELECT enrollment_id, status FROM enrollments", route_pos)
        update_review_pos = REGISTRAR.index("UPDATE student_identity_reviews", select_pos)
        self.assertIn("WHERE enrollment_id = %s AND branch_id = %s AND status = 'pending'", REGISTRAR[select_pos:update_review_pos])
        self.assertIn("FOR UPDATE", REGISTRAR[select_pos:update_review_pos])
        self.assertLess(select_pos, update_review_pos)

    def test_existing_student_review_rejects_enrollment_in_same_transaction(self):
        route_pos = REGISTRAR.index("def decide_identity_review")
        review_update_pos = REGISTRAR.index("UPDATE student_identity_reviews", route_pos)
        reject_update_pos = REGISTRAR.index("SET status = 'rejected'", review_update_pos)
        commit_pos = REGISTRAR.index("db.commit()", reject_update_pos)
        self.assertLess(review_update_pos, reject_update_pos)
        self.assertLess(reject_update_pos, commit_pos)
        self.assertIn("rejection_reason = %s", REGISTRAR[reject_update_pos:commit_pos])
        self.assertIn("rejected_at = NOW()", REGISTRAR[reject_update_pos:commit_pos])

    def test_existing_student_review_rolls_back_on_missing_review_or_non_pending(self):
        route_pos = REGISTRAR.index("def decide_identity_review")
        next_route = REGISTRAR.index("@registrar_bp.route", route_pos + 1)
        route_block = REGISTRAR[route_pos:next_route]
        self.assertIn("db.rollback()", route_block)
        self.assertIn("Identity review record not found.", route_block)
        self.assertIn("Only pending applications in your branch", route_block)

    def test_identity_review_route_does_not_create_student_accounts(self):
        route_pos = REGISTRAR.index("def decide_identity_review")
        next_route = REGISTRAR.index("@registrar_bp.route", route_pos + 1)
        route_block = REGISTRAR[route_pos:next_route]
        self.assertNotIn("INSERT INTO student_accounts", route_block)

    def test_pending_queue_excludes_rejected_correction_rows(self):
        self.assertIn("new_where = \"e.branch_id=%s AND e.year_id=%s AND e.status = 'pending'\"", REGISTRAR)
        self.assertNotIn("new_where = \"e.branch_id=%s AND e.year_id=%s AND e.status IN ('pending', 'rejected')\"", REGISTRAR)

    def test_request_correction_and_final_reject_are_separate_actions(self):
        self.assertIn('action not in ("approved", "rejected", "correction_requested")', REGISTRAR)
        self.assertIn('SET status=%s, rejection_reason=%s, rejected_at=NOW()', REGISTRAR)
        self.assertIn('correction_requested', DASHBOARD)
        self.assertIn('Final reject this enrollment?', DASHBOARD)
        self.assertIn('return redirect(url_for("registrar.registrar_enrollments", year_id=selected_year_id))', REGISTRAR)

    def test_correction_and_final_reject_email_copy_are_separate(self):
        self.assertIn('if action in ("correction_requested", "rejected"):', REGISTRAR)
        self.assertIn("fix and re-submit your application", REGISTRAR)
        self.assertIn("Application Not Approved", REGISTRAR)
        self.assertIn("If you have questions, please contact the Registrar's Office.", REGISTRAR)
        self.assertIn('PUBLIC_BASE_URL', REGISTRAR)
        self.assertIn('cta = f"""', REGISTRAR)
        self.assertIn('use_background=False', REGISTRAR)
        self.assertIn('email_status == "missing"', REGISTRAR)
        self.assertIn("email notification could not be sent", REGISTRAR)
        rejected_pos = REGISTRAR.index('subject = f"Enrollment Application Result - {branch_name}"')
        rejected_block = REGISTRAR[rejected_pos:REGISTRAR.index('html_body = f"""', rejected_pos)]
        self.assertNotIn("fix and re-submit", rejected_block)
        self.assertNotIn("tracking page", rejected_block)

    def test_track_edit_only_for_correction_requested_not_final_rejected(self):
        self.assertIn("enrollment.status == 'correction_requested'", TRACK_TEMPLATE)
        rejected_pos = TRACK_TEMPLATE.index("{% elif enrollment.status == 'rejected' %}", TRACK_TEMPLATE.index("Conditional Alerts"))
        rejected_block = TRACK_TEMPLATE[rejected_pos:TRACK_TEMPLATE.index("{% elif enrollment.status == 'approved' %}", rejected_pos)]
        self.assertNotIn("Fix & Re-submit Application", rejected_block)

    def test_correction_route_updates_same_correction_row_and_excludes_self_from_identity_check(self):
        route_pos = STUDENT.index("def enroll_edit")
        next_route = STUDENT.index("@student_bp.route", route_pos + 1)
        route_block = STUDENT[route_pos:next_route]
        self.assertIn('if enrollment.get("status") != "correction_requested":', STUDENT)
        self.assertIn("exclude_enrollment_id=enrollment_id", STUDENT)
        self.assertIn("UPDATE enrollments SET", route_block)
        self.assertNotIn("INSERT INTO enrollments", route_block)
        self.assertIn("validate_shs_pathway_for_year", route_block)
        self.assertIn('update_values.append("pending")', route_block)
        self.assertIn('return redirect(url_for("student.track_enrollment"))', route_block)

    def test_correction_form_uses_split_names_and_transferee_semester(self):
        self.assertIn('name="student_first_name"', EDIT_TEMPLATE)
        self.assertIn('name="student_middle_name"', EDIT_TEMPLATE)
        self.assertIn('name="student_last_name"', EDIT_TEMPLATE)
        self.assertNotIn('name="student_name"', EDIT_TEMPLATE)
        self.assertIn('name="enroll_semester"', EDIT_TEMPLATE)
        self.assertIn('name="shs_track"', EDIT_TEMPLATE)
        self.assertNotIn('name="year_id"', EDIT_TEMPLATE)
        self.assertIn("saved_type.startswith('Transferee')", EDIT_TEMPLATE)
        self.assertIn("function updateSemVisibility()", EDIT_TEMPLATE)

    def test_correction_form_matches_public_layout_sections(self):
        self.assertIn("Father's Information", EDIT_TEMPLATE)
        self.assertIn("Mother's Information", EDIT_TEMPLATE)
        self.assertIn("Guardian's Information", EDIT_TEMPLATE)
        self.assertIn('id="section-father"', EDIT_TEMPLATE)
        self.assertIn('id="section-mother"', EDIT_TEMPLATE)
        self.assertIn('id="section-guardian"', EDIT_TEMPLATE)
        self.assertIn('class="c8"', EDIT_TEMPLATE)
        self.assertIn('<label>School Year</label>', EDIT_TEMPLATE)
        self.assertNotIn('class="c10"', EDIT_TEMPLATE)
        self.assertNotIn('<label>SY</label>', EDIT_TEMPLATE)

    def test_correction_documents_use_public_upload_layout(self):
        self.assertIn('class="section requirements-section"', EDIT_TEMPLATE)
        self.assertIn("<h3>Requirement/s Submitted</h3>", EDIT_TEMPLATE)
        self.assertIn("PDF, JPG, JPEG, PNG accepted (Max 10MB per file)", EDIT_TEMPLATE)
        self.assertIn("'psa_birth_cert'", EDIT_TEMPLATE)
        self.assertIn("'baptismal_cert'", EDIT_TEMPLATE)
        self.assertIn("'form_138'", EDIT_TEMPLATE)
        self.assertIn("'good_moral'", EDIT_TEMPLATE)
        self.assertIn("'form_137'", EDIT_TEMPLATE)
        self.assertIn('name="{{ field_id }}"', EDIT_TEMPLATE)
        self.assertIn("Already uploaded. Uploading a new file will replace the previous one.", EDIT_TEMPLATE)
        self.assertIn("'Card / Form 138', 'Form 138'", EDIT_TEMPLATE)
        self.assertNotIn('class="doc-item"', EDIT_TEMPLATE)
        self.assertNotIn('class="file-input-wrapper"', EDIT_TEMPLATE)

    def test_correction_form_matches_public_birthday_and_validation_ui(self):
        self.assertIn('id="field_dob"', EDIT_TEMPLATE)
        self.assertIn('max="{{ max_dob_date }}"', EDIT_TEMPLATE)
        self.assertIn("Minimum age is 3 years old", EDIT_TEMPLATE)
        self.assertIn("Birthday cannot be a future date.", EDIT_TEMPLATE)
        self.assertIn("Student must be at least 3 years old to enroll.", EDIT_TEMPLATE)
        self.assertIn('id="field_lrn"', EDIT_TEMPLATE)
        self.assertIn('pattern="\\d{12}"', EDIT_TEMPLATE)
        self.assertIn("LRN must be exactly 12 digits (numbers only).", EDIT_TEMPLATE)
        self.assertIn("function isValidPHMobile", EDIT_TEMPLATE)
        self.assertIn("Student contact must be an 11-digit PH mobile", EDIT_TEMPLATE)
        self.assertIn("Consecutive dots (..) are not allowed in home address.", EDIT_TEMPLATE)
        self.assertIn("is too large. Maximum size is 10MB.", EDIT_TEMPLATE)
        self.assertIn("has an invalid type. Only PDF, JPG, JPEG, and PNG are allowed.", EDIT_TEMPLATE)
        self.assertNotIn("Set max date for Birthday", EDIT_TEMPLATE)

    def test_correction_post_has_server_side_public_validation_rules(self):
        route_pos = STUDENT.index("def enroll_edit")
        next_route = STUDENT.index("@student_bp.route", route_pos + 1)
        route_block = STUDENT[route_pos:next_route]
        self.assertIn('valid_grade_names = {g["name"] for g in grade_levels}', route_block)
        self.assertIn('valid_enroll_types = {"Old", "New", "Transferee"}', route_block)
        self.assertIn('valid_semesters = {"First Semester", "Second Semester"}', route_block)
        self.assertIn('re.match(r"^09\\d{9}$", val)', route_block)
        self.assertIn("Birthday cannot be a future date.", route_block)
        self.assertIn("Student must be at least 3 years old to enroll.", route_block)
        self.assertIn("Home address must be at least 5 characters long.", route_block)
        self.assertIn("Previous school contains invalid characters.", route_block)
        self.assertIn('corrected["shs_track"] = None', route_block)
        self.assertIn("max_dob_date=max_dob_date", route_block)


if __name__ == "__main__":
    unittest.main()
