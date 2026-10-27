import ast
import unittest
from datetime import datetime
from pathlib import Path
import re
import uuid


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


def _load_policy_sync_helper(calendar_terms):
    source = BRANCH_ADMIN_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    helper_names = {
        "_changed_periods_have_grade_references",
        "_policy_has_completed_grade_set",
        "_synchronize_calendar_grading_policy",
    }
    nodes = [
        item for item in tree.body
        if isinstance(item, ast.FunctionDef) and item.name in helper_names
    ]
    replaced = []
    namespace = {
        "datetime": datetime,
        "uuid": uuid,
        "_ordered_calendar_terms": lambda *_: calendar_terms,
        "_replace_policy_periods": lambda *args: replaced.append(args),
    }
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(BRANCH_ADMIN_PATH), "exec"), namespace)
    return namespace["_synchronize_calendar_grading_policy"], replaced


class PolicySyncCursor:
    def __init__(self, active=(), active_periods=(), draft=None, references=(), finalized=False,
                 appended_references=False, completed_grade_set=False):
        self.active = list(active)
        self.active_periods = list(active_periods)
        self.draft = draft
        self.references = list(references)
        self.finalized = finalized
        self.appended_references = appended_references
        self.completed_grade_set = completed_grade_set
        self.result = None
        self.statements = []

    def execute(self, sql, params=()):
        normalized = " ".join(sql.split())
        self.statements.append((normalized, params))
        if normalized.startswith("SELECT policy_id, rounding_mode, rounding_scale"):
            self.result = self.active
        elif normalized.startswith("SELECT gpp.calendar_term_id"):
            self.result = self.active_periods
        elif normalized.startswith("SELECT policy_id FROM grading_policies"):
            self.result = self.draft
        elif "RETURNING policy_id" in normalized:
            self.result = {"policy_id": 99}
        elif "grading_policy_has_grade_references" in normalized:
            self.result = {"referenced": self.references.pop(0)}
        elif "AS has_finalized" in normalized:
            self.result = {"has_finalized": self.finalized}
        elif "AS has_changed_period_references" in normalized:
            self.result = {"has_changed_period_references": self.appended_references}
        elif "AS has_completed_grade_set" in normalized:
            self.result = {"has_completed_grade_set": self.completed_grade_set}
        else:
            self.result = None

    def fetchall(self):
        return self.result or []

    def fetchone(self):
        return self.result


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
        self.assertIn("UPDATE grading_period_ranges SET is_active = FALSE", source)
        self.assertIn("WHERE id = %s AND branch_id = %s AND year_id = %s", source)
        self.assertIn("cannot be deleted because it is already referenced", source)
        self.assertIn("grading_weights gw JOIN sections gw_sec", source)
        self.assertIn("attendance_scores ats", source)
        self.assertIn("JOIN sections ats_sec ON ats_sec.section_id = ats.section_id", source)
        self.assertIn("participation_scores ps", source)
        self.assertIn("JOIN sections ps_sec ON ps_sec.section_id = ps.section_id", source)
        self.assertNotIn("attendance_scores WHERE year_id", source)
        self.assertNotIn("participation_scores WHERE year_id", source)
        self.assertNotIn("grading_weights WHERE branch_id = %s AND year_id = %s", source)
        self.assertIn('type="button" class="delete-term-btn" data-delete-saved="true"', template)
        self.assertIn('data-term-id="{{ term.id }}"', template)
        self.assertIn("deleteInput.name = 'delete_term_id'", template)
        self.assertNotIn('type="submit" class="delete-term-btn"', template)
        self.assertIn("WARNING: Delete", template)

    def test_enter_key_cannot_implicitly_submit_a_delete_button(self):
        template = (ROOT / "templates" / "branch_admin_academic_calendar.html").read_text(encoding="utf-8")
        self.assertNotIn('type="submit" class="delete-term-btn"', template)
        self.assertIn('type="submit" id="save-terms-btn"', template)
        self.assertIn("HTMLFormElement.prototype.submit.call(form)", template)
        self.assertNotIn("const periods = ['1st', '2nd', '3rd']", template)

    def test_calendar_dates_can_be_set_in_the_future(self):
        template = (ROOT / "templates" / "branch_admin_academic_calendar.html").read_text(encoding="utf-8")
        base = (ROOT / "templates" / "base.html").read_text(encoding="utf-8")
        self.assertIn("data-allow-future", template)
        self.assertIn("!input.hasAttribute('data-allow-future')", base)

    def test_dynamic_policy_integration_is_enabled_by_default(self):
        env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
        service = (ROOT / "services" / "final_grades.py").read_text(encoding="utf-8")
        self.assertIn("GRADING_POLICY_FINAL_GRADES_ENABLED=true", env_example)
        self.assertIn('os.getenv("GRADING_POLICY_FINAL_GRADES_ENABLED", "true")', service)
        self.assertIn("load_active_grading_policy", service)

    def test_branch_dashboard_and_schedules_render_later_terms_dynamically(self):
        dashboard = (ROOT / "templates" / "branch_admin_dashboard.html").read_text(encoding="utf-8")
        schedules = (ROOT / "templates" / "schedules_allinone.html").read_text(encoding="utf-8")
        self.assertIn("{% for term in metrics.terms %}", dashboard)
        self.assertNotIn("[('1st', '1st Term'), ('2nd', '2nd Term'), ('3rd', '3rd Term')]", dashboard)
        self.assertNotIn("const preferredOrder = ['1st Term', '2nd Term', '3rd Term'", schedules)
        self.assertIn("parseInt(a, 10)", schedules)

    def test_calendar_save_automatically_activates_internal_policy(self):
        source = BRANCH_ADMIN_PATH.read_text(encoding="utf-8")
        self.assertIn("def _synchronize_calendar_grading_policy", source)
        self.assertIn("status = 'draft'", source)
        self.assertIn("SET status = 'pending_verification'", source)
        self.assertIn("status = 'verified'", source)
        self.assertIn("status = 'active'", source)
        self.assertIn("_synchronize_calendar_grading_policy(", source)
        self.assertIn("rounding_scale = 0", source)
        self.assertIn("has_dynamic_weight_terms", source)
        self.assertIn("has_dynamic_transfer_terms", source)

    def test_policy_ui_is_removed_and_locked_history_is_protected(self):
        source = BRANCH_ADMIN_PATH.read_text(encoding="utf-8")
        template = (ROOT / "templates" / "branch_admin_academic_calendar.html").read_text(encoding="utf-8")
        for action in ("sync_policy_draft", "submit_policy", "return_policy_draft", "verify_policy", "activate_policy"):
            self.assertNotIn(f'value="{action}"', template)
        self.assertNotIn("Grading Policy", template)
        self.assertNotIn("Review notes", template)
        self.assertIn("grading_policy_has_grade_references", source)
        self.assertIn("Existing grades were not changed", source)
        self.assertIn("is_active = TRUE", source)

    def test_calendar_and_policy_updates_share_one_transaction(self):
        source = BRANCH_ADMIN_PATH.read_text(encoding="utf-8")
        save_block = source[source.index('if action == "save_ranges"'):source.index("# Fetch ranges")]
        self.assertLess(
            save_block.index("_synchronize_calendar_grading_policy("),
            save_block.index("db.commit()"),
        )
        self.assertIn("db.rollback()", save_block)
        self.assertIn("Required grading periods were updated automatically", source)
        template = (ROOT / "templates" / "branch_admin_academic_calendar.html").read_text(encoding="utf-8")
        self.assertIn("calendar_requires_sync", source)
        self.assertIn("if not calendar_requires_sync", template)

    def test_safe_calendar_terms_are_automatically_activated(self):
        calendar_terms = [
            {"id": 11, "period_name": "1st"}, {"id": 12, "period_name": "2nd"},
            {"id": 13, "period_name": "3rd"}, {"id": 14, "period_name": "4th"},
            {"id": 15, "period_name": "5th"},
        ]
        sync, replaced = _load_policy_sync_helper(calendar_terms)
        cursor = PolicySyncCursor(references=[False])
        policy_id, outcome = sync(cursor, 4, 8, 22)
        self.assertEqual((policy_id, outcome), (99, "created"))
        self.assertEqual(replaced[0][1:4], (99, 4, 8))
        sql = "\n".join(statement for statement, _ in cursor.statements)
        self.assertLess(sql.index("SET status = 'pending_verification'"), sql.index("SET status = 'verified'"))
        self.assertLess(sql.index("SET status = 'verified'"), sql.index("SET status = 'active'"))

    def test_active_policy_is_not_rewritten_when_terms_match(self):
        terms = [{"id": 11}, {"id": 12}, {"id": 13}, {"id": 14}]
        sync, replaced = _load_policy_sync_helper(terms)
        cursor = PolicySyncCursor(
            active=[{"policy_id": 7, "rounding_mode": "excel_round", "rounding_scale": 0}],
            active_periods=[{"calendar_term_id": row["id"]} for row in terms],
        )
        self.assertEqual(sync(cursor, 4, 8, 22), (7, "unchanged"))
        self.assertEqual(replaced, [])
        self.assertFalse(any(statement.startswith("UPDATE grading_policies") for statement, _ in cursor.statements))

    def test_structural_change_is_blocked_when_active_policy_has_grade_dependencies(self):
        terms = [{"id": 11}, {"id": 12}, {"id": 14}]
        sync, replaced = _load_policy_sync_helper(terms)
        cursor = PolicySyncCursor(
            active=[{"policy_id": 7, "rounding_mode": "excel_round", "rounding_scale": 0}],
            active_periods=[{"calendar_term_id": 11}, {"calendar_term_id": 12}, {"calendar_term_id": 13}],
            references=[True],
        )
        with self.assertRaisesRegex(ValueError, "Existing grades were not changed"):
            sync(cursor, 4, 8, 22)
        self.assertEqual(replaced, [])
        self.assertFalse(any("INSERT INTO grading_policies" in statement for statement, _ in cursor.statements))

    def test_referenced_policy_allows_clean_append_before_old_final_is_complete(self):
        terms = [
            {"id": 11, "period_name": "1st"},
            {"id": 12, "period_name": "2nd"},
            {"id": 13, "period_name": "3rd"},
            {"id": 14, "period_name": "4th"},
        ]
        sync, replaced = _load_policy_sync_helper(terms)
        cursor = PolicySyncCursor(
            active=[{"policy_id": 7, "rounding_mode": "excel_round", "rounding_scale": 0}],
            active_periods=[
                {"calendar_term_id": 11, "period_name": "1st"},
                {"calendar_term_id": 12, "period_name": "2nd"},
                {"calendar_term_id": 13, "period_name": "3rd"},
            ],
            references=[True, True],
        )
        self.assertEqual(sync(cursor, 4, 8, 22), (99, "created"))
        self.assertEqual(replaced[0][1:4], (99, 4, 8))
        sql = "\n".join(statement for statement, _ in cursor.statements)
        self.assertIn("AS has_changed_period_references", sql)
        self.assertIn("AS has_completed_grade_set", sql)
        self.assertIn("status = 'retired'", sql)

    def test_append_is_blocked_after_an_old_policy_final_set_is_complete(self):
        terms = [
            {"id": 11, "period_name": "1st"},
            {"id": 12, "period_name": "2nd"},
            {"id": 13, "period_name": "3rd"},
            {"id": 14, "period_name": "4th"},
        ]
        sync, replaced = _load_policy_sync_helper(terms)
        cursor = PolicySyncCursor(
            active=[{"policy_id": 7, "rounding_mode": "excel_round", "rounding_scale": 0}],
            active_periods=[
                {"calendar_term_id": 11, "period_name": "1st"},
                {"calendar_term_id": 12, "period_name": "2nd"},
                {"calendar_term_id": 13, "period_name": "3rd"},
            ],
            references=[True], completed_grade_set=True,
        )
        with self.assertRaisesRegex(ValueError, "final-grade set was already completed"):
            sync(cursor, 4, 8, 22)
        self.assertEqual(replaced, [])

    def test_append_is_blocked_when_new_term_already_has_grade_records(self):
        terms = [
            {"id": 11, "period_name": "1st"},
            {"id": 12, "period_name": "2nd"},
            {"id": 13, "period_name": "3rd"},
            {"id": 14, "period_name": "4th"},
        ]
        sync, replaced = _load_policy_sync_helper(terms)
        cursor = PolicySyncCursor(
            active=[{"policy_id": 7, "rounding_mode": "excel_round", "rounding_scale": 0}],
            active_periods=[
                {"calendar_term_id": 11, "period_name": "1st"},
                {"calendar_term_id": 12, "period_name": "2nd"},
                {"calendar_term_id": 13, "period_name": "3rd"},
            ],
            references=[True], appended_references=True,
        )
        with self.assertRaisesRegex(ValueError, "added or removed academic term already has grading records"):
            sync(cursor, 4, 8, 22)
        self.assertEqual(replaced, [])

    def test_unused_tail_term_can_be_archived_without_rewriting_locked_policy(self):
        terms = [
            {"id": 11, "period_name": "1st"},
            {"id": 12, "period_name": "2nd"},
            {"id": 13, "period_name": "3rd"},
        ]
        sync, replaced = _load_policy_sync_helper(terms)
        cursor = PolicySyncCursor(
            active=[{"policy_id": 7, "rounding_mode": "excel_round", "rounding_scale": 0}],
            active_periods=[
                {"calendar_term_id": 11, "period_name": "1st"},
                {"calendar_term_id": 12, "period_name": "2nd"},
                {"calendar_term_id": 13, "period_name": "3rd"},
                {"calendar_term_id": 14, "period_name": "4th"},
            ],
            references=[True, True],
        )
        self.assertEqual(sync(cursor, 4, 8, 22), (99, "created"))
        self.assertEqual(replaced[0][1:4], (99, 4, 8))
        sql = "\n".join(statement for statement, _ in cursor.statements)
        self.assertIn("AS has_changed_period_references", sql)
        self.assertIn("status = 'retired'", sql)

    def test_deleting_unreferenced_fourth_term_can_restore_legacy_three_term_policy(self):
        terms = [
            {"id": 11, "period_name": "1st"},
            {"id": 12, "period_name": "2nd"},
            {"id": 13, "period_name": "3rd"},
        ]
        sync, _ = _load_policy_sync_helper(terms)
        cursor = PolicySyncCursor(
            draft={"policy_id": 7}, references=[True], finalized=False
        )
        self.assertEqual(
            sync(cursor, 4, 8, 22, allow_legacy_three_term_backfill=True),
            (7, "updated"),
        )
        sql = "\n".join(statement for statement, _ in cursor.statements)
        self.assertIn("AS has_finalized", sql)
        self.assertIn("SET status = 'active'", sql)

    def test_legacy_backfill_is_blocked_when_finalized_grades_exist(self):
        terms = [
            {"id": 11, "period_name": "1st"},
            {"id": 12, "period_name": "2nd"},
            {"id": 13, "period_name": "3rd"},
        ]
        sync, _ = _load_policy_sync_helper(terms)
        cursor = PolicySyncCursor(
            draft={"policy_id": 7}, references=[True], finalized=True
        )
        with self.assertRaisesRegex(ValueError, "historical policy verification"):
            sync(cursor, 4, 8, 22, allow_legacy_three_term_backfill=True)


if __name__ == "__main__":
    unittest.main()
