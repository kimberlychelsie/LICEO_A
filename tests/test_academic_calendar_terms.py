import ast
import unittest
from datetime import datetime
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
BRANCH_ADMIN_PATH = ROOT / "routes" / "branch_admin.py"


def _load_calendar_helpers():
    source = BRANCH_ADMIN_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    wanted = {"_ordinal_term_name", "_term_number", "_validate_academic_terms"}
    module = ast.Module(
        body=[node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in wanted],
        type_ignores=[],
    )
    namespace = {"datetime": datetime, "re": re}
    exec(compile(module, str(BRANCH_ADMIN_PATH), "exec"), namespace)
    return namespace


HELPERS = _load_calendar_helpers()
validate = HELPERS["_validate_academic_terms"]


def term(name, start, end, row_id=""):
    return {"id": row_id, "period_name": name, "start_date": start, "end_date": end}


class AcademicCalendarTermValidationTest(unittest.TestCase):
    def test_fourth_term_is_valid_when_non_overlapping(self):
        terms = [
            term("1st", "2026-06-01", "2026-07-31", "11"),
            term("2nd", "2026-08-01", "2026-09-30", "12"),
            term("3rd", "2026-10-01", "2026-11-30", "13"),
            term("4th", "2026-12-01", "2027-02-01"),
        ]
        self.assertEqual(validate(terms), {})

    def test_overlap_and_shared_boundary_are_rejected(self):
        self.assertTrue(validate([term("1st", "2026-06-01", "2026-08-01"), term("2nd", "2026-07-31", "2026-09-30")]))
        self.assertTrue(validate([term("1st", "2026-06-01", "2026-08-01"), term("2nd", "2026-08-01", "2026-09-30")]))

    def test_next_day_is_allowed(self):
        self.assertEqual(validate([term("1st", "2026-06-01", "2026-08-01"), term("2nd", "2026-08-02", "2026-09-30")]), {})

    def test_invalid_range_and_duplicate_number_are_rejected(self):
        self.assertTrue(validate([term("1st", "2026-08-02", "2026-08-01")]))
        errors = validate([term("1st", "2026-06-01", "2026-07-01"), term("1st", "2026-08-01", "2026-09-01")])
        self.assertEqual(set(errors), {0, 1})

    def test_scope_and_concurrency_guards_are_present(self):
        source = BRANCH_ADMIN_PATH.read_text(encoding="utf-8")
        self.assertIn("pg_advisory_xact_lock", source)
        self.assertIn("WHERE id = %s AND branch_id = %s AND year_id = %s", source)
        self.assertIn("submitted_ids != set(existing.keys())", source)

    def test_delete_is_scoped_and_blocks_referenced_terms(self):
        source = BRANCH_ADMIN_PATH.read_text(encoding="utf-8")
        template = (ROOT / "templates" / "branch_admin_academic_calendar.html").read_text(encoding="utf-8")
        self.assertIn("DELETE FROM grading_period_ranges", source)
        self.assertIn("WHERE id = %s AND branch_id = %s AND year_id = %s", source)
        self.assertIn("cannot be deleted because it is already referenced", source)
        self.assertIn("grading_weights gw JOIN sections gw_sec", source)
        self.assertNotIn("grading_weights WHERE branch_id = %s AND year_id = %s", source)
        self.assertIn('name="delete_term_id" value="{{ term.id }}"', template)
        self.assertIn("WARNING: Delete", template)

    def test_calendar_dates_can_be_set_in_the_future(self):
        template = (ROOT / "templates" / "branch_admin_academic_calendar.html").read_text(encoding="utf-8")
        base = (ROOT / "templates" / "base.html").read_text(encoding="utf-8")
        self.assertIn("data-allow-future", template)
        self.assertIn("!input.hasAttribute('data-allow-future')", base)

    def test_additional_terms_stay_out_of_grading_activation(self):
        for relative in ("routes/teacher.py", "routes/student_portal.py", "routes/registrar.py", "app.py"):
            source = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("period_name IN ('1st', '2nd', '3rd')", source, relative)


if __name__ == "__main__":
    unittest.main()
