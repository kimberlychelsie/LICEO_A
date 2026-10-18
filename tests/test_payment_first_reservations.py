import os
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from utils.payment_first_lifecycle import cancel_inventory
from utils.payment_first_payments import (
    _lock_inventory,
    get_payment_first_availability,
    process_payment_first_batch,
)
from utils.payment_first_reservations import (
    PAYMENT_FIRST_POLICY,
    PaymentFirstError,
    PaymentFirstInventoryUnavailable,
    create_payment_first_reservations,
    payment_first_enabled,
)


ROOT = Path(__file__).resolve().parents[1]


class CheckoutCursor:
    def __init__(self, schema_ready=True):
        self.schema_ready = schema_ready
        self.result = None
        self.rowcount = -1
        self.next_id = 100
        self.queries = []
        self.reservation_params = []
        self.item_params = []

    def execute(self, query, params=()):
        normalized = " ".join(query.split())
        self.queries.append(normalized)
        if "information_schema.columns" in normalized:
            self.result = {"ready": self.schema_ready}
        elif normalized.startswith("INSERT INTO reservations"):
            self.next_id += 1
            self.result = {"reservation_id": self.next_id}
            self.reservation_params.append(params)
        elif normalized.startswith("INSERT INTO reservation_items"):
            self.result = None
            self.item_params.append(params)
        elif normalized.startswith("SELECT inventory_policy"):
            self.result = {"inventory_policy": PAYMENT_FIRST_POLICY}
        elif normalized.startswith("SELECT 1 FROM reservation_inventory_allocations"):
            self.result = None
        else:
            raise AssertionError(f"Unexpected SQL: {normalized}")

    def fetchone(self):
        return self.result


class PaymentFirstCheckoutTest(unittest.TestCase):
    def test_feature_flag_is_disabled_when_unset(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(payment_first_enabled())

    def test_each_book_gets_its_own_header_and_one_item(self):
        cursor = CheckoutCursor()
        ids = create_payment_first_reservations(
            cursor,
            book_lines=[
                {"item_id": 8, "qty": 1, "size_label": None,
                 "unit_price": Decimal("100.00"), "line_total": Decimal("100.00")},
                {"item_id": 9, "qty": 2, "size_label": None,
                 "unit_price": Decimal("75.00"), "line_total": Decimal("150.00")},
            ],
            student_user_id=12,
            branch_id=4,
            student_grade="Grade 7",
            reserved_by_user_id=12,
            enrollment_id=21,
        )
        self.assertEqual(ids, [101, 102])
        self.assertEqual(len(cursor.reservation_params), 2)
        self.assertEqual(len(cursor.item_params), 2)
        self.assertTrue(all(params[-1] == PAYMENT_FIRST_POLICY
                            for params in cursor.reservation_params))
        self.assertFalse(any(query.startswith("UPDATE inventory")
                             for query in cursor.queries))

    def test_invalid_or_zero_price_line_is_rejected_atomically(self):
        cursor = CheckoutCursor()
        with self.assertRaises(PaymentFirstError):
            create_payment_first_reservations(
                cursor,
                book_lines=[
                    {"item_id": 8, "qty": 1, "size_label": None,
                     "unit_price": Decimal("100.00"), "line_total": Decimal("100.00")},
                    {"item_id": 9, "qty": 1, "size_label": None,
                     "unit_price": Decimal("0.00"), "line_total": Decimal("0.00")},
                ],
                student_user_id=12,
                branch_id=4,
                student_grade="Grade 7",
                reserved_by_user_id=12,
                enrollment_id=21,
            )
        self.assertEqual(len(cursor.reservation_params), 1)
        # The route owns the transaction and rolls this first insert back.

    def test_unpaid_payment_first_cancellation_releases_no_inventory(self):
        cursor = CheckoutCursor()
        released = []
        reservation = {"reservation_id": 7, "branch_id": 4}
        result = cancel_inventory(
            cursor, reservation,
            lambda *args: released.append(args),
        )
        self.assertFalse(result)
        self.assertEqual(released, [])


class PaymentCursor:
    def __init__(self, transaction_total=Decimal("175.00")):
        self.result = None
        self.rows = []
        self.rowcount = -1
        self.transaction_total = transaction_total
        self.queries = []

    def execute(self, query, params=()):
        normalized = " ".join(query.split())
        self.queries.append(normalized)
        if "information_schema.columns" in normalized:
            self.result = {"ready": True}
        elif normalized.startswith("SELECT pg_advisory_xact_lock"):
            self.result = None
        elif normalized.startswith("SELECT * FROM payment_transactions"):
            self.result = None
        elif normalized.startswith("INSERT INTO payment_transactions"):
            self.result = {"transaction_id": 55}
        elif normalized.startswith("SELECT COALESCE(SUM(amount),0) AS total"):
            self.result = {"total": self.transaction_total}
        else:
            raise AssertionError(f"Unexpected SQL: {normalized}")

    def fetchone(self):
        return self.result


class InventoryCursor:
    def __init__(self):
        self.rows = []

    def execute(self, query, params=()):
        normalized = " ".join(query.split())
        if normalized.startswith("SELECT item_id,branch_id,item_name"):
            self.rows = [{
                "item_id": 8,
                "branch_id": 4,
                "item_name": "Book",
                "stock_total": 1,
                "reserved_qty": 0,
                "is_active": True,
                "price": Decimal("100.00"),
            }]
        else:
            raise AssertionError(f"Unexpected SQL: {normalized}")

    def fetchall(self):
        return self.rows


class AvailabilityCursor:
    def __init__(self, rows):
        self.rows = rows
        self.params = None

    def execute(self, query, params=()):
        self.params = params
        if "FROM reservations r" not in " ".join(query.split()):
            raise AssertionError(f"Unexpected SQL: {query}")

    def fetchall(self):
        return self.rows


class PaymentFirstAvailabilityTest(unittest.TestCase):
    def test_unavailable_book_is_not_currently_payable(self):
        cursor = AvailabilityCursor([{
            "reservation_id": 38,
            "qty": 1,
            "size_label": None,
            "category": "BOOK",
            "price": Decimal("500.00"),
            "is_active": True,
            "item_stock_total": 1,
            "item_reserved_qty": 1,
            "size_stock_total": None,
            "size_reserved_qty": None,
        }])
        result = get_payment_first_availability(cursor, [38], 4)
        self.assertEqual(result[38]["available_qty"], 0)
        self.assertFalse(result[38]["is_currently_payable"])
        self.assertEqual(cursor.params, (4, [38]))

    def test_available_book_is_currently_payable(self):
        cursor = AvailabilityCursor([{
            "reservation_id": 39,
            "qty": 2,
            "size_label": None,
            "category": "BOOK",
            "price": Decimal("500.00"),
            "is_active": True,
            "item_stock_total": 5,
            "item_reserved_qty": 2,
            "size_stock_total": None,
            "size_reserved_qty": None,
        }])
        result = get_payment_first_availability(cursor, [39], 4)
        self.assertEqual(result[39]["available_qty"], 3)
        self.assertTrue(result[39]["is_currently_payable"])

    def test_size_stock_can_make_item_unavailable(self):
        cursor = AvailabilityCursor([{
            "reservation_id": 40,
            "qty": 1,
            "size_label": "S",
            "category": "BOOK",
            "price": Decimal("500.00"),
            "is_active": True,
            "item_stock_total": 5,
            "item_reserved_qty": 0,
            "size_stock_total": 1,
            "size_reserved_qty": 1,
        }])
        result = get_payment_first_availability(cursor, [40], 4)
        self.assertEqual(result[40]["available_qty"], 0)
        self.assertFalse(result[40]["is_currently_payable"])


class PaymentFirstPaymentTest(unittest.TestCase):
    def setUp(self):
        self.bill = {
            "bill_id": 9,
            "enrollment_id": 21,
            "branch_id": 4,
            "year_id": 3,
            "balance": Decimal("500.00"),
        }
        self.rows = [
            {"reservation_id": 101, "amount": Decimal("100.00")},
            {"reservation_id": 102, "amount": Decimal("75.00")},
        ]

    @patch("utils.payment_first_payments._transaction_result")
    @patch("utils.payment_first_payments._write_children")
    @patch("utils.payment_first_payments._lock_inventory")
    @patch("utils.payment_first_payments._locked_reservations")
    def test_exact_full_batch_creates_one_transaction(
        self, locked, lock_inventory, write_children, transaction_result
    ):
        cursor = PaymentCursor()
        locked.return_value = self.rows
        transaction_result.return_value = {"transaction_id": 55}
        result = process_payment_first_batch(
            cursor,
            bill=self.bill,
            reservation_ids=[101, 102],
            amount=Decimal("175.00"),
            payment_method="cash",
            notes="",
            received_by=7,
            idempotency_key="payment_request_123456",
        )
        self.assertEqual(result["transaction_id"], 55)
        lock_inventory.assert_called_once()
        write_children.assert_called_once()
        self.assertEqual(
            sum(q.startswith("INSERT INTO payment_transactions") for q in cursor.queries),
            1,
        )

    @patch("utils.payment_first_payments._write_children")
    @patch("utils.payment_first_payments._lock_inventory")
    @patch("utils.payment_first_payments._locked_reservations")
    def test_partial_batch_is_rejected_before_inventory_or_payment(
        self, locked, lock_inventory, write_children
    ):
        cursor = PaymentCursor()
        locked.return_value = self.rows
        with self.assertRaisesRegex(PaymentFirstError, "Full payment"):
            process_payment_first_batch(
                cursor,
                bill=self.bill,
                reservation_ids=[101, 102],
                amount=Decimal("100.00"),
                payment_method="cash",
                notes="",
                received_by=7,
                idempotency_key="payment_request_123456",
            )
        lock_inventory.assert_not_called()
        write_children.assert_not_called()
        self.assertFalse(any(
            q.startswith("INSERT INTO payment_transactions") for q in cursor.queries
        ))

    def test_combined_quantity_is_checked_against_one_stock_pool(self):
        rows = [
            {"reservation_id": 101, "item_id": 8, "qty": 1, "size_label": None},
            {"reservation_id": 102, "item_id": 8, "qty": 1, "size_label": None},
        ]
        with self.assertRaises(PaymentFirstInventoryUnavailable) as raised:
            _lock_inventory(InventoryCursor(), rows, 4)
        self.assertEqual(raised.exception.reservation_ids, [101, 102])


class PaymentFirstSourceInvariantTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.student = (ROOT / "routes" / "student.py").read_text(encoding="utf-8")
        cls.cashier = (ROOT / "routes" / "cashier.py").read_text(encoding="utf-8")
        cls.librarian = (ROOT / "routes" / "librarian.py").read_text(encoding="utf-8")
        cls.payment = (ROOT / "utils" / "payment_first_payments.py").read_text(encoding="utf-8")
        cls.events = (ROOT / "utils" / "payment_first_events.py").read_text(encoding="utf-8")
        cls.lifecycle = (ROOT / "utils" / "payment_first_lifecycle.py").read_text(encoding="utf-8")
        cls.cashier_template = (ROOT / "templates" / "cashier_view_bill.html").read_text(encoding="utf-8")

    def test_new_checkout_is_feature_gated_and_does_not_hold_stock(self):
        self.assertIn("if book_lines and payment_first_enabled()", self.student)
        self.assertIn("create_payment_first_reservations(", self.student)
        self.assertIn("success_ids", self.student)

    def test_full_batch_payment_and_stock_allocation_are_one_service_call(self):
        self.assertIn("Full payment of PHP", self.payment)
        self.assertIn("INSERT INTO payment_transactions", self.payment)
        self.assertIn("INSERT INTO payments", self.payment)
        self.assertIn("INSERT INTO reservation_inventory_allocations", self.payment)
        self.assertIn("stock_total-reserved_qty >= %s", self.payment)
        self.assertIn("SELECT pg_advisory_xact_lock", self.payment)
        self.assertIn("SUM(amount)", self.payment)

    def test_cashier_supports_explicit_batch_not_silent_general_allocation(self):
        self.assertIn('"reservation_batch"', self.cashier)
        self.assertIn("Use the book payment controls", self.cashier)
        self.assertIn("idempotency_key", self.cashier_template)
        self.assertIn("payment-first-book", self.cashier_template)
        self.assertIn("Pay Selected", self.cashier_template)

    def test_claim_consumes_physical_and_reserved_stock_once(self):
        self.assertIn("allocation_state='CONSUMED'", self.lifecycle)
        self.assertIn("stock_total=stock_total-%s", self.lifecycle)
        self.assertIn("reserved_qty=reserved_qty-%s", self.lifecycle)
        self.assertIn("allocation_state='ALLOCATED'", self.lifecycle)
        self.assertIn("claim_inventory(", self.cashier)
        self.assertIn("claim_inventory(", self.librarian)

    def test_notifications_are_deduplicated_for_students_and_parents(self):
        self.assertGreaterEqual(self.events.count("ON CONFLICT DO NOTHING"), 3)
        self.assertIn("student_notifications", self.events)
        self.assertIn("parent_notifications", self.events)
        self.assertIn("AVAILABLE_AGAIN", self.events)
        self.assertIn("record_newly_unavailable", self.cashier)


if __name__ == "__main__":
    unittest.main()
