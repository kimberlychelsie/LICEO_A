import unittest
from pathlib import Path

from utils.assessment_resume import find_resumable_assessment_exam_id


ROOT = Path(__file__).resolve().parents[1]
AUTH = (ROOT / "routes" / "auth.py").read_text(encoding="utf-8")
PORTAL = (ROOT / "routes" / "student_portal.py").read_text(encoding="utf-8")


class FakeCursor:
    def __init__(self, row):
        self.row = row
        self.sql = ""
        self.params = None

    def execute(self, sql, params):
        self.sql = " ".join(sql.split())
        self.params = params

    def fetchone(self):
        return self.row


class AssessmentResumeRedirectTests(unittest.TestCase):
    def test_lookup_is_owned_active_published_and_deadline_bounded(self):
        cursor = FakeCursor({"exam_id": 44})
        self.assertEqual(find_resumable_assessment_exam_id(cursor, 91), 44)
        self.assertEqual(cursor.params, (91,))
        self.assertIn("r.enrollment_id = %s", cursor.sql)
        self.assertIn("r.status = 'in_progress'", cursor.sql)
        self.assertIn("LOWER(COALESCE(e.status, '')) = 'published'", cursor.sql)
        self.assertIn("r.started_at + (e.duration_mins * INTERVAL '1 minute')", cursor.sql)
        self.assertIn("COALESCE(ext.new_due_date, e.scheduled_start)", cursor.sql)

    def test_missing_enrollment_or_attempt_does_not_redirect(self):
        cursor = FakeCursor(None)
        self.assertIsNone(find_resumable_assessment_exam_id(cursor, None))
        self.assertEqual(cursor.sql, "")
        self.assertIsNone(find_resumable_assessment_exam_id(cursor, 91))

    def test_login_and_dashboard_use_shared_resume_lookup(self):
        self.assertGreaterEqual(AUTH.count("find_resumable_assessment_exam_id("), 2)
        dashboard = PORTAL[PORTAL.index("def dashboard():"):]
        self.assertIn("find_resumable_assessment_exam_id(", dashboard)
        self.assertIn('"student_portal.student_exam_take"', dashboard)


if __name__ == "__main__":
    unittest.main()
