"""Cancellation and claim compatibility for legacy and payment-first rows."""

from utils.payment_first_reservations import (
    PAYMENT_FIRST_POLICY,
    PaymentFirstError,
    _money,
    _row_value,
    get_reservation_policy,
)


def cancel_inventory(cursor, reservation, legacy_release):
    """Unpaid payment-first rows have no hold; legacy rows release their hold."""
    policy = get_reservation_policy(
        cursor, reservation["reservation_id"], reservation["branch_id"]
    )
    if policy == PAYMENT_FIRST_POLICY:
        cursor.execute(
            "SELECT 1 FROM reservation_inventory_allocations "
            "WHERE reservation_id=%s AND allocation_state='ALLOCATED'",
            (reservation["reservation_id"],),
        )
        if cursor.fetchone():
            raise PaymentFirstError(
                "Paid reservations require authorized refund reconciliation."
            )
        return False
    legacy_release(cursor, reservation["reservation_id"], reservation["branch_id"])
    return True


def claim_inventory(
    cursor, reservation, *, legacy_settlement, legacy_deduct
):
    """Consume a paid allocation exactly once, with a legacy fallback."""
    policy = get_reservation_policy(
        cursor, reservation["reservation_id"], reservation["branch_id"]
    )
    if policy != PAYMENT_FIRST_POLICY:
        settlement = legacy_settlement(cursor, reservation)
        legacy_deduct(cursor, reservation["reservation_id"], reservation["branch_id"])
        return settlement
    cursor.execute(
        "SELECT a.*,p.amount AS payment_amount,p.transaction_id,ri.line_total,ri.qty,"
        "pt.total_amount AS transaction_total FROM reservation_inventory_allocations a "
        "JOIN reservation_items ri ON ri.reservation_item_id=a.reservation_item_id "
        "JOIN payments p ON p.payment_id=a.payment_id "
        "JOIN payment_transactions pt ON pt.transaction_id=p.transaction_id "
        "WHERE a.reservation_id=%s AND a.branch_id=%s FOR UPDATE OF a",
        (reservation["reservation_id"], reservation["branch_id"]),
    )
    allocations = cursor.fetchall() or []
    if len(allocations) != 1:
        raise PaymentFirstError("Verified inventory allocation is missing.")
    allocation = allocations[0]
    if allocation["allocation_state"] != "ALLOCATED":
        raise PaymentFirstError("This reservation was already claimed or released.")
    if (_money(allocation["payment_amount"]) != _money(allocation["line_total"])
            or int(allocation["quantity"]) != int(allocation["qty"])
            or not allocation.get("transaction_id")):
        raise PaymentFirstError("The reservation payment allocation is invalid.")
    cursor.execute(
        "SELECT COALESCE(SUM(amount),0) AS total FROM payments WHERE transaction_id=%s",
        (allocation["transaction_id"],),
    )
    if _money(_row_value(cursor.fetchone(), "total") or 0) != _money(
        allocation["transaction_total"]
    ):
        raise PaymentFirstError("The official payment transaction is inconsistent.")
    _consume_allocation(cursor, allocation)
    return {
        "enrollment_id": reservation.get("resolved_enrollment_id")
        or reservation.get("enrollment_id"),
        "total": _money(allocation["line_total"]),
        "is_settled": True,
    }


def _consume_allocation(cursor, allocation):
    qty = int(allocation["quantity"])
    cursor.execute(
        "UPDATE inventory_items SET stock_total=stock_total-%s,"
        "reserved_qty=reserved_qty-%s WHERE item_id=%s AND branch_id=%s "
        "AND stock_total >= %s AND reserved_qty >= %s",
        (qty, qty, allocation["item_id"], allocation["branch_id"], qty, qty),
    )
    if cursor.rowcount != 1:
        raise PaymentFirstError("Allocated inventory is inconsistent.")
    if allocation.get("size_id") is not None:
        cursor.execute(
            "UPDATE inventory_item_sizes SET stock_total=stock_total-%s,"
            "reserved_qty=reserved_qty-%s WHERE size_id=%s AND item_id=%s "
            "AND stock_total >= %s AND reserved_qty >= %s",
            (qty, qty, allocation["size_id"], allocation["item_id"], qty, qty),
        )
        if cursor.rowcount != 1:
            raise PaymentFirstError("Allocated size inventory is inconsistent.")
    cursor.execute(
        "UPDATE reservation_inventory_allocations SET allocation_state='CONSUMED',"
        "consumed_at=NOW() WHERE allocation_id=%s AND allocation_state='ALLOCATED'",
        (allocation["allocation_id"],),
    )
    if cursor.rowcount != 1:
        raise PaymentFirstError("This allocation was already consumed.")
