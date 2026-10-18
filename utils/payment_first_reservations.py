"""Payment-first reservation helpers.

The feature is additive and disabled by default. Helpers that use the additive
schema verify it first, so a pre-migration installation stays in legacy mode.
"""

from __future__ import annotations

import os
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


PAYMENT_FIRST_POLICY = "PAYMENT_FIRST"
MONEY = Decimal("0.01")
_IDEMPOTENCY_RE = re.compile(r"^[A-Za-z0-9_-]{16,128}$")


class PaymentFirstError(ValueError):
    pass


class PaymentFirstSchemaError(PaymentFirstError):
    pass


class PaymentFirstInventoryUnavailable(PaymentFirstError):
    def __init__(self, message, reservation_ids=None):
        super().__init__(message)
        self.reservation_ids = list(reservation_ids or [])


def payment_first_enabled():
    return os.getenv("RESERVATION_PAYMENT_FIRST_ENABLED", "").strip().lower() in {
        "1", "true", "yes", "on"
    }


def _row_value(row, key, index=0):
    if row is None:
        return None
    return row.get(key) if isinstance(row, dict) else row[index]


def _money(value):
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise PaymentFirstError("Invalid monetary amount.")
    if not amount.is_finite():
        raise PaymentFirstError("Invalid monetary amount.")
    return amount.quantize(MONEY, rounding=ROUND_HALF_UP)


def payment_first_schema_ready(cursor):
    """Return True only when every runtime object required by the feature exists."""
    cursor.execute(
        """
        SELECT
            EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'reservations'
                  AND column_name = 'inventory_policy'
            )
            AND EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'payments'
                  AND column_name = 'transaction_id'
            )
            AND to_regclass('public.reservation_inventory_allocations') IS NOT NULL
            AND to_regclass('public.reservation_availability_events') IS NOT NULL
            AND to_regclass('public.reservation_availability_deliveries') IS NOT NULL
            AND to_regclass('public.payment_transactions') IS NOT NULL AS ready
        """
    )
    return bool(_row_value(cursor.fetchone(), "ready"))


def require_payment_first_schema(cursor):
    if not payment_first_schema_ready(cursor):
        raise PaymentFirstSchemaError(
            "Payment-first reservations are not ready in this database. "
            "Apply the approved additive migrations before enabling the feature."
        )


def get_reservation_policy(cursor, reservation_id, branch_id):
    if not payment_first_schema_ready(cursor):
        return None
    cursor.execute(
        """SELECT inventory_policy FROM reservations
           WHERE reservation_id = %s AND branch_id = %s""",
        (reservation_id, branch_id),
    )
    return _row_value(cursor.fetchone(), "inventory_policy")


def create_payment_first_reservations(
    cursor, *, book_lines, student_user_id, branch_id, student_grade,
    reserved_by_user_id, enrollment_id
):
    """Create one unpaid reservation per book without changing stock counters."""
    require_payment_first_schema(cursor)
    reservation_ids = []
    for line in sorted(book_lines, key=lambda entry: int(entry["item_id"])):
        qty = int(line["qty"])
        unit_price = _money(line["unit_price"])
        line_total = _money(line["line_total"])
        if (
            qty <= 0
            or qty > 3
            or unit_price <= 0
            or line_total != _money(unit_price * qty)
        ):
            raise PaymentFirstError("The selected book quantity or price is invalid.")
        cursor.execute(
            """
            INSERT INTO reservations (
                student_user_id, branch_id, student_grade_level, status,
                reserved_by_user_id, enrollment_id, inventory_policy
            ) VALUES (%s, %s, %s, 'RESERVED', %s, %s, %s)
            RETURNING reservation_id
            """,
            (student_user_id, branch_id, student_grade, reserved_by_user_id,
             enrollment_id, PAYMENT_FIRST_POLICY),
        )
        reservation_id = int(_row_value(cursor.fetchone(), "reservation_id"))
        cursor.execute(
            """
            INSERT INTO reservation_items (
                reservation_id, item_id, qty, size_label, unit_price, line_total
            ) VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (reservation_id, line["item_id"], qty, line.get("size_label"),
             unit_price, line_total),
        )
        reservation_ids.append(reservation_id)
    return reservation_ids
