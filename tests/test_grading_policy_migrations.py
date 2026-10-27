import pathlib
import re
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
CALENDAR = (ROOT / "migrations" / "add_grading_period_ranges_foundation.sql").read_text(encoding="utf-8")
POLICY = (ROOT / "migrations" / "add_grading_policies.sql").read_text(encoding="utf-8")
DISCOVERY = (ROOT / "scripts" / "discover_grading_policies.py").read_text(encoding="utf-8")
DYNAMIC_TERMS = (ROOT / "migrations" / "extend_dynamic_grading_terms.sql").read_text(encoding="utf-8")


class GradingPolicyMigrationContractTests(unittest.TestCase):
    def test_calendar_foundation_is_additive_and_legacy_safe(self):
        self.assertIn("CREATE TABLE IF NOT EXISTS public.grading_period_ranges", CALENDAR)
        self.assertIn("ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE", CALENDAR)
        self.assertIn("WHERE is_active", CALENDAR)
        self.assertIn("NOT VALID", CALENDAR)
        self.assertIn("Incompatible grading_period_ranges", CALENDAR)
        self.assertNotIn("DELETE FROM", CALENDAR.upper())
        self.assertNotIn("UPDATE ", CALENDAR.upper())

    def test_policy_schema_is_explicit_scoped_and_ordered(self):
        self.assertIn("CREATE TABLE IF NOT EXISTS public.grading_policies", POLICY)
        self.assertIn("CREATE TABLE IF NOT EXISTS public.grading_policy_periods", POLICY)
        self.assertIn("UNIQUE (policy_id, calendar_term_id)", POLICY)
        self.assertIn("WHERE status='active'", POLICY)
        self.assertIn("sequence_no", POLICY)
        self.assertIn("calendar_term_id", POLICY)

    def test_scoped_calendar_candidate_key_precedes_referencing_table(self):
        constraint_sql = "ADD CONSTRAINT grading_period_ranges_scoped_id_unique"
        policy_periods_sql = "CREATE TABLE IF NOT EXISTS public.grading_policy_periods"
        self.assertIn("UNIQUE (id, branch_id, year_id)", CALENDAR)
        self.assertIn(constraint_sql, POLICY)
        self.assertLess(POLICY.index(constraint_sql), POLICY.index(policy_periods_sql))
        self.assertIn("c.contype IN ('p','u')", POLICY)
        self.assertIn("ARRAY['id','branch_id','year_id']::TEXT[]", POLICY)

    def test_migrations_do_not_mutate_rows_or_drop_constraints(self):
        for migration in (CALENDAR, POLICY):
            normalized = migration.upper()
            self.assertIsNone(re.search(r"(?m)^\s*DELETE\s+FROM\s+", normalized))
            self.assertIsNone(re.search(r"(?m)^\s*UPDATE\s+[^;]+\s+SET\s+", normalized))
            self.assertNotIn("DROP CONSTRAINT", normalized)

    def test_locked_policies_have_database_guards(self):
        self.assertIn("guard_grading_policy_update", POLICY)
        self.assertIn("guard_grading_policy_period_change", POLICY)
        self.assertIn("grading_policy_has_grade_references", POLICY)
        self.assertIn("require an audited migration", POLICY)

    def test_drafts_remain_editable_while_verified_policies_are_locked(self):
        self.assertIn("IF target_status IN ('verified','active','retired') THEN", POLICY)
        self.assertNotIn(
            "IF target_status IN ('verified','active','retired')\n       OR public.grading_policy_has_grade_references",
            POLICY,
        )
        self.assertIn("IF OLD.status IN ('verified','active','retired')", POLICY)

    def test_discovery_tool_is_read_only_and_opt_in(self):
        self.assertIn("readonly=True", DISCOVERY)
        self.assertIn("ALLOW_GRADING_POLICY_DISCOVERY", DISCOVERY)
        for mutation in ("INSERT INTO", "UPDATE ", "DELETE FROM", "ALTER TABLE", "CREATE TABLE"):
            self.assertNotIn(mutation, DISCOVERY.upper())

    def test_dynamic_term_upgrade_replaces_only_named_check_constraints(self):
        self.assertIn("teacher_grading_weights_period_check", DYNAMIC_TERMS)
        self.assertIn("chk_transfer_term", DYNAMIC_TERMS)
        self.assertIn("existing_type <> 'c'", DYNAMIC_TERMS)
        self.assertIn("NOT VALID", DYNAMIC_TERMS)
        self.assertIn("VALIDATE CONSTRAINT", DYNAMIC_TERMS)
        self.assertNotIn("UPDATE ", DYNAMIC_TERMS.upper())
        self.assertNotIn("DELETE FROM", DYNAMIC_TERMS.upper())


if __name__ == "__main__":
    unittest.main()
