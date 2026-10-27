import unittest
from pathlib import Path

from utils.grade_approval_history import (
    fetch_grade_history,
    record_grade_history,
)


class FakeCursor:
    def __init__(self, available=True, history=None):
        self.available = available
        self.history = history or []
        self.executed = []
        self._result = None

    def execute(self, sql, params=None):
        self.executed.append((sql, params))
        normalized = " ".join(sql.split()).lower()
        if "to_regclass" in normalized:
            self._result = {"available": self.available}
        elif normalized.startswith("insert into grade_submission_history"):
            self._result = None
        elif "from grade_submission_history h" in normalized:
            self._result = self.history
        else:
            raise AssertionError(f"Unexpected SQL: {normalized}")

    def fetchone(self):
        return self._result

    def fetchall(self):
        return self._result


class GradeApprovalHistoryTests(unittest.TestCase):
    def test_pre_migration_mode_does_not_reference_missing_table(self):
        cursor = FakeCursor(available=False)
        created = record_grade_history(
            cursor, 7, "submitted", "draft", "pending_registrar", 3, "teacher"
        )
        self.assertFalse(created)
        self.assertEqual(len(cursor.executed), 1)
        self.assertIn("to_regclass", cursor.executed[0][0])

    def test_event_insert_uses_actual_transition_values(self):
        cursor = FakeCursor(available=True)
        created = record_grade_history(
            cursor, 7, "returned", "pending_admin", "rejected",
            9, "branch_admin", "Correct the final grade."
        )
        self.assertTrue(created)
        self.assertEqual(len(cursor.executed), 2)
        self.assertEqual(
            cursor.executed[1][1],
            (7, "returned", "pending_admin", "rejected", 9, "branch_admin", "Correct the final grade."),
        )

    def test_history_is_scoped_to_one_request(self):
        expected = [{"event_id": 1, "event_type": "submitted"}]
        cursor = FakeCursor(available=True, history=expected)
        history, enabled = fetch_grade_history(cursor, 42)
        self.assertTrue(enabled)
        self.assertEqual(history, expected)
        self.assertEqual(cursor.executed[-1][1], (42,))

    def test_template_supports_every_real_workflow_status(self):
        source = Path("templates/_grade_approval_tracker.html").read_text(encoding="utf-8")
        for status in (
            "draft", "pending_registrar", "pending_admin", "rejected",
            "approved_for_posting", "posted",
        ):
            self.assertIn(status, source)

    def test_progress_segments_reach_each_workflow_node(self):
        css = Path("static/css/grade_approval_tracker.css").read_text(encoding="utf-8")
        self.assertIn("status-pending_registrar:before{background:linear-gradient(to right,#2563eb 0 33.33%", css)
        self.assertIn("#16a34a 0 33.33%,#2563eb 33.33% 66.67%", css)
        self.assertIn("#16a34a 0 66.67%,#2563eb 66.67% 100%", css)
        self.assertNotIn("#2563eb 0 16.67%", css)


if __name__ == "__main__":
    unittest.main()
