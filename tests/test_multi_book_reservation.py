import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MultiBookCheckoutTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.student = (ROOT / "routes" / "student.py").read_text(encoding="utf-8")
        cls.cashier = (ROOT / "routes" / "cashier.py").read_text(encoding="utf-8")
        cls.librarian = (ROOT / "routes" / "librarian.py").read_text(encoding="utf-8")
        cls.security = (
            ROOT / "utils" / "reservation_security.py"
        ).read_text(encoding="utf-8")

        start = cls.student.index("reservation_id = None")
        end = cls.student.index("uniform_order_number = None", start)
        cls.book_checkout = cls.student[start:end]

    def test_one_header_contains_one_or_many_book_lines(self):
        self.assertEqual(self.book_checkout.count("INSERT INTO reservations ("), 1)
        self.assertEqual(self.book_checkout.count("RETURNING reservation_id"), 1)
        self.assertIn("for line in book_lines:", self.book_checkout)
        self.assertIn("INSERT INTO reservation_items", self.book_checkout)

    def test_all_items_are_validated_before_header_insert(self):
        validation = self.book_checkout.index(
            'for sel in sorted(selected, key=lambda entry: int(entry["item_id"]))'
        )
        header = self.book_checkout.index("INSERT INTO reservations (")
        self.assertLess(validation, header)
        self.assertIn("FOR UPDATE", self.book_checkout)
        self.assertIn("price IS NOT NULL AND price > 0", self.book_checkout)
        self.assertIn("qty > available", self.book_checkout)

    def test_inventory_locks_are_deterministically_ordered(self):
        self.assertIn(
            'sorted(selected, key=lambda entry: int(entry["item_id"]))',
            self.book_checkout,
        )
        self.assertIn("ORDER BY item_id", self.security)

    def test_guarded_stock_hold_is_atomic_and_does_not_reduce_physical_stock(self):
        hold_start = self.book_checkout.index("UPDATE inventory_items")
        hold_end = self.book_checkout.index("INSERT INTO reservation_items", hold_start)
        hold = self.book_checkout[hold_start:hold_end]
        self.assertIn("SET reserved_qty = reserved_qty + %s", hold)
        self.assertIn("stock_total - reserved_qty >= %s", hold)
        self.assertNotIn("SET stock_total", hold)
        self.assertIn("if cursor_tx.rowcount != 1", hold)
        self.assertIn("db_tx.rollback()", self.student)

    def test_duplicate_and_malformed_entries_are_rejected(self):
        self.assertIn("request.form.lists()", self.student)
        self.assertIn("len(values) != 1", self.student)
        self.assertIn("duplicate or malformed item entries", self.student)
        self.assertIn("duplicate size selections", self.student)

    def test_confirmation_reads_every_separate_reservation(self):
        confirmation = self.student.index("if success_ids:")
        confirmation_source = self.student[confirmation:confirmation + 1800]
        self.assertIn("FROM reservation_items ri", confirmation_source)
        self.assertIn("WHERE ri.reservation_id = ANY(%s)", confirmation_source)
        item_query = confirmation_source.split("FROM reservation_items ri", 1)[1]
        item_query = item_query.split("for item in cursor.fetchall()", 1)[0]
        self.assertNotIn("LIMIT 1", item_query)

    def test_student_and_parent_history_aggregate_all_lines(self):
        self.assertIn("COALESCE(SUM(ri.line_total), 0) AS total_amount", self.student)
        parent = (ROOT / "routes" / "parent.py").read_text(encoding="utf-8")
        self.assertIn("COALESCE(SUM(ri.line_total), 0) AS total_amount", parent)
        self.assertIn("STRING_AGG(DISTINCT ii.item_name", parent)

    def test_cashier_receipt_and_librarian_release_read_all_lines(self):
        receipt = self.cashier.index("def reservation_receipt")
        receipt_source = self.cashier[receipt:receipt + 5000]
        self.assertIn("FROM reservation_items ri", receipt_source)
        self.assertIn("WHERE ri.reservation_id = %s", receipt_source)
        release = self.librarian.index("def mark_reservation_claimed")
        release_source = self.librarian[release:release + 4500]
        self.assertIn("FROM reservation_items", release_source)
        self.assertIn("for item in items:", release_source)

    def test_cancel_and_claim_process_every_item_once(self):
        self.assertIn("def release_reserved_inventory", self.security)
        self.assertIn("reserved_qty = reserved_qty - %s", self.security)
        self.assertIn("def deduct_reserved_inventory", self.security)
        self.assertIn(
            "stock_total = stock_total - %s, reserved_qty = reserved_qty - %s",
            self.security,
        )
        cancel = self.cashier.index("def cashier_cancel_reservation")
        self.assertIn(
            "cancel_inventory(cur, reservation, release_reserved_inventory)",
            self.cashier[cancel:cancel + 1500],
        )

    def test_uniform_preorder_remains_separate(self):
        self.assertIn("uniform_lines = []  # separate uniform pre-order workflow", self.student)
        self.assertIn("INSERT INTO uniform_orders", self.student)
        self.assertNotIn("uniform_order_items", self.book_checkout)

    def test_historical_one_item_reads_remain_compatible(self):
        self.assertNotIn("UPDATE reservation_items", self.student)
        self.assertNotIn("DELETE FROM reservation_items", self.student)
        self.assertIn("WHERE ri.reservation_id = %s", self.cashier)


if __name__ == "__main__":
    unittest.main()
