import unittest
from pathlib import Path

from utils.reservation_security import (
    ReservationSecurityError,
    lock_reservation_for_cancellation,
    release_reserved_inventory,
)


ROOT = Path(__file__).resolve().parents[1]


class CancellationCursor:
    def __init__(self, status="RESERVED", has_payment=False):
        self.status = status
        self.has_payment = has_payment
        self.result = None
        self.rowcount = -1
        self.queries = []

    def execute(self, query, params=()):
        normalized = " ".join(query.split())
        self.queries.append(normalized)
        self.rowcount = -1
        if "FROM reservations r" in normalized and "FOR UPDATE OF r" not in normalized:
            self.result = {"reservation_id": 7, "resolved_enrollment_id": 21}
        elif normalized.startswith("SELECT bill_id FROM billing"):
            self.result = [{"bill_id": 5}]
        elif "FOR UPDATE OF r" in normalized:
            self.result = {
                "reservation_id": 7,
                "branch_id": 4,
                "status": self.status,
                "enrollment_id": 21,
                "student_user_id": 12,
                "resolved_enrollment_id": 21,
            }
        elif "AS has_payment_evidence" in normalized:
            self.result = {"has_payment_evidence": self.has_payment}
        else:
            raise AssertionError(f"Unexpected SQL: {normalized}")

    def fetchone(self):
        return self.result

    def fetchall(self):
        return self.result


class ReleaseCursor:
    def __init__(self):
        self.result = None
        self.rowcount = -1
        self.inventory_params = None
        self.size_params = None

    def execute(self, query, params=()):
        normalized = " ".join(query.split())
        self.rowcount = -1
        if normalized.startswith("SELECT item_id, NULLIF"):
            self.result = [{"item_id": 8, "size_label": "M", "qty": 2}]
        elif normalized.startswith("UPDATE inventory_items"):
            self.inventory_params = params
            self.rowcount = 1
        elif normalized.startswith("SELECT size_id"):
            self.result = {"size_id": 44}
        elif normalized.startswith("UPDATE inventory_item_sizes"):
            self.size_params = params
            self.rowcount = 1
        else:
            raise AssertionError(f"Unexpected SQL: {normalized}")

    def fetchone(self):
        return self.result

    def fetchall(self):
        return self.result


class ReservationCancellationSecurityTest(unittest.TestCase):
    def test_cancellation_locks_billing_before_reservation(self):
        cursor = CancellationCursor()
        result = lock_reservation_for_cancellation(cursor, 7, 4)
        self.assertEqual(result["reservation_id"], 7)
        bill_lock = next(i for i, q in enumerate(cursor.queries) if q.startswith("SELECT bill_id FROM billing"))
        reservation_lock = next(i for i, q in enumerate(cursor.queries) if "FOR UPDATE OF r" in q)
        self.assertLess(bill_lock, reservation_lock)
        self.assertIn("ORDER BY bill_id FOR UPDATE", cursor.queries[bill_lock])

    def test_direct_or_general_payment_evidence_fails_closed(self):
        with self.assertRaisesRegex(ReservationSecurityError, "payment activity"):
            lock_reservation_for_cancellation(
                CancellationCursor(has_payment=True), 7, 4
            )

    def test_non_reserved_and_duplicate_cancellation_are_rejected(self):
        for status in ("PAID", "CLAIMED", "CANCELLED"):
            with self.subTest(status=status):
                with self.assertRaisesRegex(ReservationSecurityError, "Only RESERVED"):
                    lock_reservation_for_cancellation(
                        CancellationCursor(status=status), 7, 4
                    )

    def test_multi_item_release_updates_holds_not_physical_stock(self):
        cursor = ReleaseCursor()
        release_reserved_inventory(cursor, 7, 4)
        self.assertEqual(cursor.inventory_params, (2, 8, 4, 2))
        self.assertEqual(cursor.size_params, (2, 44, 2))


class ReservationPhase3SourceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.student = (ROOT / "routes" / "student.py").read_text(encoding="utf-8")
        cls.cashier = (ROOT / "routes" / "cashier.py").read_text(encoding="utf-8")
        cls.security = (ROOT / "utils" / "reservation_security.py").read_text(encoding="utf-8")
        cls.catalog = (ROOT / "templates" / "student_reservation.html").read_text(encoding="utf-8")
        cls.student_history = (ROOT / "templates" / "student_reservations_list.html").read_text(encoding="utf-8")
        cls.parent_history = (ROOT / "templates" / "parent_reservations_list.html").read_text(encoding="utf-8")

    def test_stock_visibility_and_limits_are_present(self):
        self.assertIn("{% set initial_available = it.available if it.available > 0 else 0 %}", self.catalog)
        self.assertIn("{{ initial_available }} available", self.catalog)
        self.assertIn("Out of Stock", self.catalog)
        self.assertIn('max="{{ max_qty }}"', self.catalog)
        self.assertGreaterEqual(self.catalog.count("disabled{% endif %}"), 3)
        self.assertIn("quantity < 0 or quantity > 3", self.student)
        self.assertIn("if qty > available", self.student)

    def test_student_and_parent_cancel_forms_are_post_csrf_confirmed(self):
        for template in (self.student_history, self.parent_history):
            self.assertIn('method="post"', template)
            self.assertIn("csrf_token()", template)
            self.assertIn("return confirm(", template)
            self.assertIn("student.cancel_reservation", template)

    def test_authorization_and_atomic_status_guard_remain_explicit(self):
        route_start = self.student.index("def cancel_reservation")
        route = self.student[route_start:route_start + 5000]
        self.assertIn('role not in ("student", "parent")', route)
        self.assertIn("JOIN parent_student", route)
        self.assertIn("reservation.get(\"student_user_id\") != user_id", route)
        self.assertIn("release_reserved_inventory", route)
        self.assertIn("AND status = 'RESERVED'", route)
        self.assertIn("conn.rollback()", route)

    def test_cashier_uses_same_payment_safe_cancellation_helper(self):
        start = self.cashier.index("def cashier_cancel_reservation")
        route = self.cashier[start:start + 5000]
        self.assertIn("lock_reservation_for_cancellation", route)
        self.assertIn("release_reserved_inventory", route)
        self.assertIn("AND status = 'RESERVED'", route)
        self.assertIn("is_branch_active", route)

    def test_no_automatic_expiration_or_background_release_added(self):
        changed_sources = self.student + self.cashier + self.security
        self.assertNotIn("cancel_expired_reservations", changed_sources)
        self.assertNotIn("reservation_expiration", changed_sources)


if __name__ == "__main__":
    unittest.main()
