import unittest
from decimal import Decimal
from pathlib import Path

from utils.reservation_security import (
    ReservationSecurityError,
    deduct_reserved_inventory,
    get_verified_direct_settlement,
    lock_reservation,
)


ROOT = Path(__file__).resolve().parents[1]


class FakeCursor:
    def __init__(self, reservation=None, paid="0.00", settlement_lines=None, stock_lines=None):
        self.reservation = reservation
        self.paid = paid
        self.settlement_lines = settlement_lines
        self.stock_lines = stock_lines or []
        self.result = None
        self.rowcount = -1

    def execute(self, query, params=()):
        normalized = " ".join(query.split())
        self.rowcount = -1
        if "FROM reservations r" in normalized:
            self.result = self.reservation
        elif normalized.startswith("SELECT ri.item_id, ri.qty"):
            self.result = self.settlement_lines or []
        elif "SUM(p.amount)" in normalized:
            self.result = {"verified_paid": Decimal(self.paid)}
        elif normalized.startswith("SELECT item_id, NULLIF"):
            self.result = list(self.stock_lines)
        elif normalized.startswith("UPDATE inventory_items"):
            self.rowcount = 1
            self.result = None
        elif normalized.startswith("SELECT size_id"):
            self.result = None
        else:
            raise AssertionError(f"Unexpected SQL: {normalized}")

    def fetchone(self):
        return self.result

    def fetchall(self):
        return self.result


class ReservationSettlementTest(unittest.TestCase):
    def setUp(self):
        self.reservation = {
            "reservation_id": 7,
            "branch_id": 4,
            "status": "PAID",
            "resolved_enrollment_id": 21,
        }

    def line(self, qty=1, unit_price="100.00", line_total="100.00", **overrides):
        line = {
            "item_id": 3,
            "valid_item_id": 3,
            "item_branch_id": 4,
            "qty": qty,
            "unit_price": Decimal(unit_price),
            "line_total": Decimal(line_total),
        }
        line.update(overrides)
        return line

    def settlement(self, line=None, paid="0.00", lines=None):
        settlement_lines = lines if lines is not None else ([] if line is None else [line])
        return get_verified_direct_settlement(
            FakeCursor(paid=paid, settlement_lines=settlement_lines), self.reservation
        )

    def test_partial_direct_payment_remains_unsettled(self):
        result = self.settlement(self.line(), paid="40.00")
        self.assertFalse(result["is_settled"])
        self.assertEqual(result["remaining"], Decimal("60.00"))

    def test_multi_item_total_controls_partial_and_full_settlement(self):
        lines = [
            self.line(unit_price="100.00", line_total="100.00"),
            self.line(
                unit_price="75.00",
                line_total="150.00",
                qty=2,
                item_id=4,
                valid_item_id=4,
            ),
        ]
        partial = self.settlement(lines=lines, paid="249.99")
        self.assertEqual(partial["total"], Decimal("250.00"))
        self.assertFalse(partial["is_settled"])
        full = self.settlement(lines=lines, paid="250.00")
        self.assertTrue(full["is_settled"])

    def test_paid_reservation_without_payment_is_unsettled(self):
        result = self.settlement(self.line(), paid="0.00")
        self.assertFalse(result["is_settled"])

    def test_full_direct_payment_is_verified(self):
        result = self.settlement(self.line(), paid="100.00")
        self.assertTrue(result["is_settled"])

    def test_zero_total_historical_reservation_is_not_settled(self):
        result = self.settlement(self.line(unit_price="0.00", line_total="0.00"))
        self.assertFalse(result["is_settled"])
        self.assertEqual(result["paid"], Decimal("0.00"))

    def test_empty_reservation_is_rejected(self):
        with self.assertRaisesRegex(ReservationSecurityError, "no items"):
            self.settlement()

    def test_invalid_quantities_are_rejected(self):
        for qty in (0, -1, Decimal("1.5")):
            with self.subTest(qty=qty):
                with self.assertRaisesRegex(ReservationSecurityError, "invalid quantity"):
                    self.settlement(self.line(qty=qty))

    def test_negative_amounts_are_rejected(self):
        for line in (
            self.line(unit_price="-1.00", line_total="-1.00"),
            self.line(unit_price="1.00", line_total="-1.00"),
        ):
            with self.assertRaisesRegex(ReservationSecurityError, "negative"):
                self.settlement(line)

    def test_incorrect_line_total_is_rejected(self):
        with self.assertRaisesRegex(ReservationSecurityError, "inconsistent"):
            self.settlement(self.line(qty=2, unit_price="10.00", line_total="19.99"))

    def test_missing_or_cross_branch_item_is_rejected(self):
        for line in (
            self.line(valid_item_id=None),
            self.line(item_branch_id=99),
        ):
            with self.assertRaisesRegex(ReservationSecurityError, "invalid item"):
                self.settlement(line)

    def test_cross_branch_or_missing_reservation_is_rejected(self):
        with self.assertRaises(ReservationSecurityError):
            lock_reservation(FakeCursor(reservation=None), 7, 99)

    def test_duplicate_or_invalid_stock_deduction_fails_closed(self):
        cursor = FakeCursor(stock_lines=[{"item_id": 3, "size_label": None, "qty": 2}])

        def reject_update(query, params=()):
            normalized = " ".join(query.split())
            if normalized.startswith("SELECT item_id, NULLIF"):
                cursor.result = cursor.stock_lines
            elif normalized.startswith("UPDATE inventory_items"):
                cursor.rowcount = 0
            else:
                raise AssertionError(f"Unexpected SQL: {normalized}")

        cursor.execute = reject_update
        with self.assertRaises(ReservationSecurityError):
            deduct_reserved_inventory(cursor, 7, 4)


class ReservationRouteGuardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cashier = (ROOT / "routes" / "cashier.py").read_text(encoding="utf-8")
        cls.librarian = (ROOT / "routes" / "librarian.py").read_text(encoding="utf-8")
        cls.security = (ROOT / "utils" / "reservation_security.py").read_text(encoding="utf-8")

    def test_status_only_paid_transition_and_free_confirmation_are_disabled(self):
        start = self.cashier.index("def cashier_mark_paid")
        end = self.cashier.index("def cashier_mark_claimed", start)
        route = self.cashier[start:end]
        self.assertNotIn("UPDATE reservations", route)
        self.assertIn("Status-only payment confirmation is disabled", route)
        self.assertNotIn("is_free", route)
        self.assertIn('"is_settled": total_amount > 0 and remaining <= MONEY_EPSILON', self.security)

    def test_both_claim_routes_require_authorization_paid_and_verified_settlement(self):
        for source, function_name, auth_guard in (
            (self.cashier, "def cashier_mark_claimed", "_require_cashier"),
            (self.librarian, "def mark_reservation_claimed", "_require_librarian"),
        ):
            start = source.index(function_name)
            route = source[start:start + 5000]
            self.assertIn(auth_guard, route)
            self.assertIn('reservation["status"] != "PAID"', route)
            self.assertIn("require_verified_direct_settlement", route)
            self.assertIn("deduct_reserved_inventory", route)

    def test_payment_route_locks_bill_and_validates_target(self):
        self.assertIn("FOR UPDATE OF b", self.cashier)
        self.assertIn("_validate_specific_payment_target", self.cashier)
        self.assertIn('settlement["enrollment_id"] != bill["enrollment_id"]', self.cashier)
        self.assertIn('lock_reservation(cursor, target_id, bill["branch_id"])', self.cashier)

    def test_verified_payments_require_bill_enrollment_and_branch_match(self):
        self.assertIn("JOIN billing b ON b.bill_id = p.bill_id", self.security)
        self.assertIn("p.branch_id = %s", self.security)
        self.assertIn("p.enrollment_id = %s", self.security)
        self.assertIn("b.enrollment_id = %s", self.security)

    def test_stock_deduction_uses_guarded_arithmetic_not_clamping(self):
        self.assertNotIn("GREATEST", self.security)
        self.assertIn("stock_total >= %s AND reserved_qty >= %s", self.security)


if __name__ == "__main__":
    unittest.main()
