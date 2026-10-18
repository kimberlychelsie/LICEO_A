import unittest
from decimal import Decimal
from pathlib import Path

from routes.librarian import _parse_positive_price


ROOT = Path(__file__).resolve().parents[1]
ROUTE = (ROOT / "routes" / "librarian.py").read_text(encoding="utf-8")
TEMPLATE = (ROOT / "templates" / "librarian_books_inventory.html").read_text(
    encoding="utf-8"
)


class LibrarianInventoryUxTest(unittest.TestCase):
    def test_academic_levels_cover_the_complete_grade_sequence(self):
        self.assertIn('"pre-elementary": ("Nursery", "Kinder")', ROUTE)
        self.assertIn('tuple(f"Grade {grade}" for grade in range(1, 7))', ROUTE)
        self.assertIn('tuple(f"Grade {grade}" for grade in range(7, 11))', ROUTE)
        self.assertIn('"shs": ("Grade 11", "Grade 12")', ROUTE)
        self.assertIn("WHEN grade_level = 'Grade 12' THEN 13", ROUTE)

    def test_filters_are_validated_and_parameterized(self):
        self.assertIn('if level_filter not in valid_levels:', ROUTE)
        self.assertIn('if status_filter not in {"", "low", "out", "well"}:', ROUTE)
        self.assertIn('where.append("grade_level = ANY(%s)")', ROUTE)
        self.assertIn('params.append(list(INVENTORY_ACADEMIC_LEVELS[level_filter]))', ROUTE)
        self.assertIn("(grade_level IS NULL OR BTRIM(grade_level) = '')", ROUTE)

    def test_route_builds_deterministically_ordered_grade_groups(self):
        self.assertIn('grade_rank = {grade: index for index, grade in enumerate(GRADES)}', ROUTE)
        self.assertIn('grade = (item.get("grade_level") or "").strip() or "Unassigned"', ROUTE)
        self.assertIn('grade_groups=grade_groups', ROUTE)
        self.assertNotIn("items | groupby('grade_level')", TEMPLATE)

    def test_template_has_level_grade_and_status_filters(self):
        self.assertIn('name="level" id="invLevel"', TEMPLATE)
        self.assertIn('name="grade" id="invGrade"', TEMPLATE)
        self.assertIn('name="status" id="invStatus"', TEMPLATE)
        self.assertIn('[levelSel, gradeSel, statusSel].forEach', TEMPLATE)

    def test_all_grade_view_uses_accessible_collapsible_sections(self):
        self.assertIn('<details class="grade-section"', TEMPLATE)
        self.assertIn('<summary class="grade-header">', TEMPLATE)
        self.assertIn('class="grade-chevron"', TEMPLATE)
        self.assertIn('.grade-section[open] .grade-chevron', TEMPLATE)

    def test_price_parser_accepts_only_positive_currency_values(self):
        for invalid in (None, "", "0", "0.00", "-1", "NaN", "Infinity", "1.001", "1e999"):
            with self.subTest(invalid=invalid):
                self.assertIsNone(_parse_positive_price(invalid))
        self.assertEqual(Decimal("0.01"), _parse_positive_price("0.01"))
        self.assertEqual(Decimal("500.00"), _parse_positive_price("500"))

    def test_add_and_edit_forms_enforce_positive_prices(self):
        form = (ROOT / "templates" / "librarian_book_form.html").read_text(encoding="utf-8")
        self.assertIn('type="number" name="price"', form)
        self.assertIn('min="0.01" step="0.01"', form)
        self.assertIn("priceField.setCustomValidity", form)
        self.assertNotIn('id="bookForm" novalidate', form)
        self.assertGreaterEqual(ROUTE.count("_parse_positive_price(price_raw)"), 2)

    def test_manage_menu_groups_inventory_actions(self):
        self.assertIn('class="inventory-manage-trigger"', TEMPLATE)
        self.assertIn('id="bookManageMenu"', TEMPLATE)
        self.assertIn('id="manageEditBook"', TEMPLATE)
        self.assertIn('id="manageRestockBook"', TEMPLATE)
        self.assertIn('id="manageDeleteBookForm"', TEMPLATE)
        self.assertIn('name="csrf_token"', TEMPLATE)
        self.assertIn("window.confirm(", TEMPLATE)
        self.assertIn("closeBookManageMenu({ restoreFocus: true })", TEMPLATE)

    def test_delete_is_branch_scoped_and_preserves_history(self):
        delete_route = ROUTE[ROUTE.index("def book_delete(item_id):"):]
        self.assertIn("FOR UPDATE", delete_route)
        self.assertIn("r.status IN ('RESERVED', 'PAID')", delete_route)
        self.assertIn('int(book["reserved_qty"] or 0) > 0', delete_route)
        self.assertIn("SET is_active = FALSE", delete_route)
        self.assertIn("item_id = %s AND branch_id = %s", delete_route)
        self.assertNotIn("DELETE FROM inventory_items", delete_route)


if __name__ == "__main__":
    unittest.main()
