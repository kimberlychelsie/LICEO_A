import unittest
from pathlib import Path

from utils.inventory_pricing import (
    is_valid_inventory_price,
    require_valid_inventory_price,
)


ROOT = Path(__file__).resolve().parents[1]


class InventoryPriceValidationTest(unittest.TestCase):
    def test_null_zero_negative_and_nonfinite_prices_are_invalid(self):
        for value in (None, 0, "0.00", -1, "NaN", "Infinity", "-Infinity", "bad"):
            with self.subTest(value=value):
                self.assertFalse(is_valid_inventory_price(value))

    def test_positive_price_is_valid(self):
        self.assertTrue(is_valid_inventory_price("0.01"))
        self.assertTrue(is_valid_inventory_price("499.00"))

    def test_invalid_price_raises(self):
        with self.assertRaisesRegex(ValueError, "valid configured price"):
            require_valid_inventory_price(0, "Book")


class ReservationCatalogPricePolicyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.student = (ROOT / "routes" / "student.py").read_text(encoding="utf-8")
        cls.parent = (ROOT / "routes" / "parent.py").read_text(encoding="utf-8")
        cls.cashier = (ROOT / "routes" / "cashier.py").read_text(encoding="utf-8")
        cls.template = (
            ROOT / "templates" / "cashier_reservation_view.html"
        ).read_text(encoding="utf-8")

    def test_student_and_parent_share_price_filtered_catalog(self):
        self.assertIn('role not in ("student", "parent")', self.student)
        self.assertIn("AND price IS NOT NULL AND price > 0", self.student)
        self.assertIn("price::text NOT IN ('NaN', 'Infinity', '-Infinity')", self.student)
        self.assertIn('"student.student_reservation"', self.parent)

    def test_out_of_stock_positive_items_are_not_filtered_from_catalog(self):
        catalog_start = self.student.index('query = """', self.student.index("def student_reservation"))
        catalog_end = self.student.index('cursor.execute(query', catalog_start)
        catalog_query = self.student[catalog_start:catalog_end]
        self.assertIn("price > 0", catalog_query)
        self.assertNotIn("stock_total > reserved_qty", catalog_query)
        self.assertNotIn("stock_total > 0", catalog_query)

    def test_checkout_revalidates_database_price_under_lock(self):
        self.assertIn("FOR UPDATE", self.student)
        self.assertIn("AND price IS NOT NULL AND price > 0", self.student)
        self.assertIn("require_valid_inventory_price(", self.student)
        self.assertNotIn("request.form.get('price", self.student)
        self.assertNotIn('request.form.get("price', self.student)

    def test_mixed_cart_invalid_item_is_rejected_before_transaction(self):
        selected = self.student.index("submitted_quantities = {}")
        transaction = self.student.index("db_tx = get_db_connection()", selected)
        guard = self.student.index("set(submitted_quantities) - visible_item_ids", selected)
        self.assertLess(guard, transaction)
        self.assertIn("One or more selected items are unavailable", self.student)

    def test_historical_records_are_not_repriced_or_modified(self):
        policy_start = self.student.index("submitted_quantities = {}")
        self.assertNotIn("UPDATE reservation_items", self.student[policy_start:])
        self.assertIn("unit_price, line_total", self.student)

    def test_no_free_confirmation_bypass(self):
        self.assertNotIn("Confirm Free Reservation", self.template)
        start = self.cashier.index("def cashier_mark_paid")
        end = self.cashier.index("def cashier_mark_claimed", start)
        self.assertNotIn("UPDATE reservations", self.cashier[start:end])
        self.assertIn("Status-only payment confirmation is disabled", self.cashier[start:end])


if __name__ == "__main__":
    unittest.main()
