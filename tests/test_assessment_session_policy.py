import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
AUTH = (ROOT / "utils" / "auth_sessions.py").read_text(encoding="utf-8")
PORTAL = (ROOT / "routes" / "student_portal.py").read_text(encoding="utf-8")
BASE = (ROOT / "templates" / "base.html").read_text(encoding="utf-8")
SESSION_TIMEOUT = (ROOT / "templates" / "_session_timeout.html").read_text(encoding="utf-8")
TAKE = (ROOT / "templates" / "student_exam_take.html").read_text(encoding="utf-8")


class AssessmentSessionPolicyTests(unittest.TestCase):
    def test_default_idle_timeout_is_five_minutes(self):
        self.assertIn('AUTH_SESSION_IDLE_TIMEOUT_SECONDS", "300"', APP)
        self.assertIn("auth_idle_timeout_seconds", SESSION_TIMEOUT)

    def test_only_live_owned_assessment_bypasses_idle_cutoff(self):
        self.assertIn("def _student_has_live_assessment_attempt", APP)
        self.assertIn("r.enrollment_id = %s", APP)
        self.assertIn("r.status = 'in_progress'", APP)
        self.assertIn("r.started_at + (e.duration_mins * INTERVAL '1 minute')", APP)
        self.assertIn("allow_idle_expired", AUTH)

    def test_exam_page_uses_verified_heartbeat(self):
        self.assertIn('route("/student/exams/heartbeat"', PORTAL)
        self.assertIn("window.LICEO_ACTIVE_ASSESSMENT = true", TAKE)
        self.assertIn("setInterval(assessmentHeartbeat, 120000)", TAKE)
        self.assertGreaterEqual(
            TAKE.count("localStorage.removeItem('liceoAssessmentHeartbeatAt')"), 3
        )

    def test_normal_activity_keepalive_is_throttled(self):
        self.assertIn('@app.post("/auth/session/keepalive")', APP)
        self.assertIn("now - lastKeepaliveAt < 120000", SESSION_TIMEOUT)

    def test_timeout_performs_csrf_protected_server_logout(self):
        self.assertIn("method: 'POST'", SESSION_TIMEOUT)
        self.assertIn("'X-CSRFToken': csrfToken()", SESSION_TIMEOUT)
        self.assertIn("url_for('auth.logout')", SESSION_TIMEOUT)
        self.assertIn("window.location.replace", SESSION_TIMEOUT)

    def test_automatic_polling_endpoints_are_passive(self):
        for endpoint in (
            "cashier.cashier_sidebar_badges",
            "registrar.registrar_sidebar_badges",
            "registrar.registrar_inventory_stats_api",
            "teacher.teacher_exam_results_status",
            "student_portal.check_exam_status",
            "student_portal.student_exam_heartbeat",
        ):
            self.assertIn(endpoint, APP)
        self.assertIn("refresh_idle=bool", APP)

    def test_answer_save_requires_active_matching_attempt(self):
        save = PORTAL[PORTAL.index("def save_answer"):PORTAL.index("def student_exam_tab_switch")]
        self.assertIn("q.exam_id = r.exam_id", save)
        self.assertIn("r.enrollment_id = %s", save)
        self.assertIn("r.status = 'in_progress'", save)
        self.assertIn("FOR UPDATE OF r", save)
        self.assertIn("_assessment_remaining_seconds", save)

    def test_finalization_is_idempotent_and_uses_the_same_attempt_lock(self):
        finalize = PORTAL[PORTAL.index("def _finalize_expired_attempt"):PORTAL.index("@student_portal_bp")]
        take = PORTAL[PORTAL.index("def student_exam_take"):PORTAL.index("def auto_finalize_expired_exams")]
        self.assertIn("FOR UPDATE", finalize)
        self.assertIn("AND status = 'in_progress'", finalize)
        self.assertIn("FOR UPDATE OF r", take)
        self.assertIn("AND status='in_progress'", take)

    def test_attempt_and_scheduled_deadlines_are_both_enforced(self):
        self.assertIn("min(attempt_remaining, schedule_remaining)", PORTAL)
        self.assertIn("COALESCE(ext.new_due_date, e.scheduled_start)", APP)
        self.assertIn("COALESCE(ext.new_due_date, e.scheduled_start)", PORTAL)

    def test_resume_restores_server_answers_and_stable_order(self):
        self.assertIn("saved_answers=saved_answers", PORTAL)
        self.assertIn("random.Random(result_id)", PORTAL)
        self.assertIn("serverSavedAnswers", TAKE)


if __name__ == "__main__":
    unittest.main()
