from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


MONEY_EPSILON = Decimal("0.005")
MONEY_QUANTUM = Decimal("0.01")


class ReservationSecurityError(ValueError):
    pass


def lock_reservation(cursor, reservation_id, branch_id):
    cursor.execute(
        """
        SELECT r.reservation_id, r.branch_id, r.status, r.enrollment_id,
               r.student_user_id,
               COALESCE(r.enrollment_id, sa.enrollment_id) AS resolved_enrollment_id
        FROM reservations r
        LEFT JOIN users u ON u.user_id = r.student_user_id
        LEFT JOIN student_accounts sa ON sa.username = u.username
        WHERE r.reservation_id = %s AND r.branch_id = %s
        FOR UPDATE OF r
        """,
        (reservation_id, branch_id),
    )
    reservation = cursor.fetchone()
    if not reservation:
        raise ReservationSecurityError("Reservation not found or access denied.")
    return reservation


def lock_reservation_for_cancellation(cursor, reservation_id, branch_id):
    """Lock billing rows before the reservation and reject payment-associated cancellations."""
    cursor.execute(
        """
        SELECT r.reservation_id,
               COALESCE(r.enrollment_id, sa.enrollment_id) AS resolved_enrollment_id
        FROM reservations r
        LEFT JOIN users u ON u.user_id = r.student_user_id
        LEFT JOIN student_accounts sa ON sa.username = u.username
        WHERE r.reservation_id = %s AND r.branch_id = %s
        """,
        (reservation_id, branch_id),
    )
    candidate = cursor.fetchone()
    if not candidate or not candidate.get("resolved_enrollment_id"):
        raise ReservationSecurityError(
            "Reservation ownership cannot be verified. Manual review is required."
        )

    enrollment_id = candidate["resolved_enrollment_id"]
    cursor.execute(
        """
        SELECT bill_id
        FROM billing
        WHERE enrollment_id = %s AND branch_id = %s
        ORDER BY bill_id
        FOR UPDATE
        """,
        (enrollment_id, branch_id),
    )
    cursor.fetchall()

    reservation = lock_reservation(cursor, reservation_id, branch_id)
    if reservation.get("resolved_enrollment_id") != enrollment_id:
        raise ReservationSecurityError(
            "Reservation ownership changed. Please try again."
        )
    if reservation.get("status") != "RESERVED":
        raise ReservationSecurityError("Only RESERVED reservations can be cancelled.")

    cursor.execute(
        """
        SELECT EXISTS (
            SELECT 1
            FROM payments p
            JOIN billing b ON b.bill_id = p.bill_id
            WHERE b.enrollment_id = %s
              AND b.branch_id = %s
              AND p.branch_id = %s
              AND p.amount <> 0
              AND (
                    (p.target_type = 'reservation' AND p.target_id = %s)
                    OR p.target_type IS NULL
                    OR p.target_type = 'general'
              )
        ) AS has_payment_evidence
        """,
        (enrollment_id, branch_id, branch_id, reservation_id),
    )
    evidence = cursor.fetchone() or {}
    if evidence.get("has_payment_evidence"):
        raise ReservationSecurityError(
            "This reservation has payment activity that requires manual review before cancellation."
        )
    return reservation


def get_verified_direct_settlement(cursor, reservation):
    """Return settlement backed only by directly targeted, ownership-matched payments."""
    enrollment_id = reservation.get("resolved_enrollment_id")
    if not enrollment_id:
        raise ReservationSecurityError(
            "Reservation payment ownership cannot be verified. Manual reconciliation is required."
        )

    cursor.execute(
        """
        SELECT ri.item_id, ri.qty, ri.unit_price, ri.line_total,
               ii.item_id AS valid_item_id, ii.branch_id AS item_branch_id
        FROM reservation_items ri
        LEFT JOIN inventory_items ii ON ii.item_id = ri.item_id
        WHERE ri.reservation_id = %s
        ORDER BY ri.item_id
        """,
        (reservation["reservation_id"],),
    )
    lines = cursor.fetchall() or []
    if not lines:
        raise ReservationSecurityError("Reservation has no items.")

    total_amount = Decimal("0.00")
    for line in lines:
        if (
            line.get("valid_item_id") is None
            or line.get("item_branch_id") != reservation["branch_id"]
        ):
            raise ReservationSecurityError("Reservation contains an invalid item.")
        try:
            qty_value = Decimal(str(line.get("qty")))
            qty = int(qty_value)
            unit_price = Decimal(str(line.get("unit_price")))
            line_total = Decimal(str(line.get("line_total")))
        except (InvalidOperation, TypeError, ValueError, OverflowError):
            raise ReservationSecurityError("Reservation contains invalid item values.")
        if qty <= 0 or qty_value != Decimal(qty):
            raise ReservationSecurityError("Reservation contains an invalid quantity.")
        if not unit_price.is_finite() or not line_total.is_finite():
            raise ReservationSecurityError("Reservation contains invalid monetary values.")
        if unit_price < 0 or line_total < 0:
            raise ReservationSecurityError("Reservation contains negative monetary values.")
        try:
            expected = (unit_price * qty).quantize(
                MONEY_QUANTUM, rounding=ROUND_HALF_UP
            )
            stored = line_total.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
        except InvalidOperation:
            raise ReservationSecurityError("Reservation contains invalid monetary values.")
        if stored != expected:
            raise ReservationSecurityError("Reservation item total is inconsistent.")
        total_amount += stored

    cursor.execute(
        """
        SELECT COALESCE(SUM(p.amount), 0) AS verified_paid
        FROM payments p
        JOIN billing b ON b.bill_id = p.bill_id
        WHERE p.target_type = 'reservation'
          AND p.target_id = %s
          AND p.branch_id = %s
          AND b.branch_id = %s
          AND p.enrollment_id = %s
          AND b.enrollment_id = %s
        """,
        (
            reservation["reservation_id"],
            reservation["branch_id"],
            reservation["branch_id"],
            enrollment_id,
            enrollment_id,
        ),
    )
    verified_paid = Decimal(str(cursor.fetchone()["verified_paid"] or 0))
    remaining = max(Decimal("0"), total_amount - verified_paid)
    return {
        "total": total_amount,
        "paid": verified_paid,
        "remaining": remaining,
        "is_settled": total_amount > 0 and remaining <= MONEY_EPSILON,
        "enrollment_id": enrollment_id,
    }


def require_verified_direct_settlement(cursor, reservation):
    settlement = get_verified_direct_settlement(cursor, reservation)
    if not settlement["is_settled"]:
        raise ReservationSecurityError(
            "Verified direct payment is incomplete or unavailable. Manual reconciliation is required."
        )
    return settlement


def deduct_reserved_inventory(cursor, reservation_id, branch_id):
    """Deduct physical and reserved stock exactly once in the caller transaction."""
    cursor.execute(
        """
        SELECT item_id, NULLIF(TRIM(size_label), '') AS size_label, SUM(qty) AS qty
        FROM reservation_items
        WHERE reservation_id = %s
        GROUP BY item_id, NULLIF(TRIM(size_label), '')
        ORDER BY item_id, NULLIF(TRIM(size_label), '')
        """,
        (reservation_id,),
    )
    lines = cursor.fetchall() or []
    if not lines:
        raise ReservationSecurityError("Reservation has no items to release.")

    for line in lines:
        qty = int(line["qty"] or 0)
        if qty <= 0:
            raise ReservationSecurityError("Reservation contains an invalid quantity.")
        cursor.execute(
            """
            UPDATE inventory_items
            SET stock_total = stock_total - %s, reserved_qty = reserved_qty - %s
            WHERE item_id = %s AND branch_id = %s
              AND stock_total >= %s AND reserved_qty >= %s
            """,
            (qty, qty, line["item_id"], branch_id, qty, qty),
        )
        if cursor.rowcount != 1:
            raise ReservationSecurityError("Inventory stock does not match the reservation.")

        if line.get("size_label"):
            cursor.execute(
                """
                SELECT size_id FROM inventory_item_sizes
                WHERE item_id = %s AND size_label = %s
                FOR UPDATE
                """,
                (line["item_id"], line["size_label"]),
            )
            size_row = cursor.fetchone()
            if size_row:
                cursor.execute(
                    """
                    UPDATE inventory_item_sizes
                    SET stock_total = stock_total - %s, reserved_qty = reserved_qty - %s
                    WHERE size_id = %s
                      AND stock_total >= %s AND reserved_qty >= %s
                    """,
                    (qty, qty, size_row["size_id"], qty, qty),
                )
                if cursor.rowcount != 1:
                    raise ReservationSecurityError(
                        "Size-level inventory does not match the reservation."
                    )

def release_reserved_inventory(cursor, reservation_id, branch_id):
    """Release every reservation hold without changing physical stock."""
    cursor.execute(
        """
        SELECT item_id, NULLIF(TRIM(size_label), '') AS size_label, SUM(qty) AS qty
        FROM reservation_items
        WHERE reservation_id = %s
        GROUP BY item_id, NULLIF(TRIM(size_label), '')
        ORDER BY item_id, NULLIF(TRIM(size_label), '')
        """,
        (reservation_id,),
    )
    lines = cursor.fetchall() or []
    if not lines:
        raise ReservationSecurityError("Reservation has no items to cancel.")

    for line in lines:
        qty = int(line["qty"] or 0)
        if qty <= 0:
            raise ReservationSecurityError("Reservation contains an invalid quantity.")
        cursor.execute(
            """
            UPDATE inventory_items
            SET reserved_qty = reserved_qty - %s
            WHERE item_id = %s AND branch_id = %s AND reserved_qty >= %s
            """,
            (qty, line["item_id"], branch_id, qty),
        )
        if cursor.rowcount != 1:
            raise ReservationSecurityError("Inventory hold does not match the reservation.")

        if line.get("size_label"):
            cursor.execute(
                """
                SELECT size_id FROM inventory_item_sizes
                WHERE item_id = %s AND size_label = %s
                FOR UPDATE
                """,
                (line["item_id"], line["size_label"]),
            )
            size_row = cursor.fetchone()
            if size_row:
                cursor.execute(
                    """
                    UPDATE inventory_item_sizes
                    SET reserved_qty = reserved_qty - %s
                    WHERE size_id = %s AND reserved_qty >= %s
                    """,
                    (qty, size_row["size_id"], qty),
                )
                if cursor.rowcount != 1:
                    raise ReservationSecurityError(
                        "Size-level inventory hold does not match the reservation."
                    )
