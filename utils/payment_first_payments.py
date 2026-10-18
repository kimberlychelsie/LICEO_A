"""Atomic payment and inventory allocation for payment-first books."""

import hashlib
import re
import secrets
from datetime import datetime, timezone
from decimal import Decimal

from utils.payment_first_reservations import (
    MONEY,
    PAYMENT_FIRST_POLICY,
    PaymentFirstError,
    PaymentFirstInventoryUnavailable,
    _money,
    _row_value,
    require_payment_first_schema,
)


def get_payment_first_availability(cursor, reservation_ids, branch_id):
    """Return a read-only, fail-closed stock snapshot for payment controls."""
    ids = sorted({int(value) for value in reservation_ids})
    if not ids:
        return {}

    cursor.execute(
        "SELECT r.reservation_id,ri.qty,ri.size_label,ii.category,ii.price,"
        "ii.is_active,ii.stock_total AS item_stock_total,"
        "ii.reserved_qty AS item_reserved_qty,"
        "iis.stock_total AS size_stock_total,"
        "iis.reserved_qty AS size_reserved_qty "
        "FROM reservations r "
        "JOIN reservation_items ri ON ri.reservation_id=r.reservation_id "
        "JOIN inventory_items ii ON ii.item_id=ri.item_id "
        "LEFT JOIN inventory_item_sizes iis ON iis.item_id=ri.item_id "
        "AND iis.size_label=ri.size_label "
        "WHERE r.branch_id=%s AND r.reservation_id=ANY(%s) "
        "ORDER BY r.reservation_id,ri.reservation_item_id",
        (branch_id, ids),
    )
    grouped = {reservation_id: [] for reservation_id in ids}
    for row in cursor.fetchall() or []:
        grouped.setdefault(int(row["reservation_id"]), []).append(row)

    result = {}
    for reservation_id in ids:
        rows = grouped.get(reservation_id) or []
        available = 0
        payable = False
        if len(rows) == 1:
            row = rows[0]
            qty = row.get("qty")
            try:
                valid_price = _money(row.get("price")) > 0
            except PaymentFirstError:
                valid_price = False
            valid_item = (
                not isinstance(qty, bool)
                and isinstance(qty, int)
                and qty > 0
                and bool(row.get("is_active"))
                and str(row.get("category") or "").upper() == "BOOK"
                and valid_price
            )
            if valid_item:
                available = max(
                    0,
                    int(row.get("item_stock_total") or 0)
                    - int(row.get("item_reserved_qty") or 0),
                )
                if row.get("size_stock_total") is not None:
                    size_available = max(
                        0,
                        int(row.get("size_stock_total") or 0)
                        - int(row.get("size_reserved_qty") or 0),
                    )
                    available = min(available, size_available)
                payable = available >= qty
        result[reservation_id] = {
            "available_qty": available,
            "is_currently_payable": payable,
        }
    return result


def _lock_id(value):
    raw = int(hashlib.sha256(value.encode("utf-8")).hexdigest()[:16], 16)
    return raw - (1 << 64) if raw >= (1 << 63) else raw


def _locked_reservations(cursor, reservation_ids, bill):
    ids = sorted({int(value) for value in reservation_ids})
    if not ids or len(ids) != len(reservation_ids):
        raise PaymentFirstError("Select one or more unique book reservations.")
    cursor.execute(
        "SELECT reservation_id,branch_id,enrollment_id,student_user_id,status,"
        "inventory_policy FROM reservations WHERE reservation_id=ANY(%s) "
        "ORDER BY reservation_id FOR UPDATE",
        (ids,),
    )
    reservations = cursor.fetchall() or []
    if len(reservations) != len(ids):
        raise PaymentFirstError("One or more reservations were not found.")
    rows = []
    for reservation in reservations:
        rid = int(reservation["reservation_id"])
        if int(reservation["branch_id"]) != int(bill["branch_id"]):
            raise PaymentFirstError("A reservation belongs to another branch.")
        if int(reservation.get("enrollment_id") or 0) != int(bill["enrollment_id"]):
            raise PaymentFirstError("A reservation does not belong to this bill.")
        if reservation.get("inventory_policy") != PAYMENT_FIRST_POLICY:
            raise PaymentFirstError("Legacy reservations cannot use a payment-first batch.")
        if str(reservation.get("status") or "").upper() != "RESERVED":
            raise PaymentFirstError(f"Reservation #{rid} is no longer payable.")
        rows.append(_locked_item(cursor, reservation, bill))
    return rows


def _locked_item(cursor, reservation, bill):
    rid = int(reservation["reservation_id"])
    cursor.execute(
        "SELECT ri.reservation_item_id,ri.reservation_id,ri.item_id,ri.qty,"
        "ri.size_label,ri.unit_price,ri.line_total,ii.item_name,ii.category "
        "FROM reservation_items ri JOIN inventory_items ii ON ii.item_id=ri.item_id "
        "WHERE ri.reservation_id=%s ORDER BY ri.reservation_item_id FOR UPDATE OF ri",
        (rid,),
    )
    items = cursor.fetchall() or []
    if len(items) != 1:
        raise PaymentFirstError(f"Reservation #{rid} must contain exactly one book.")
    item = items[0]
    qty = item.get("qty")
    unit_price = _money(item.get("unit_price"))
    line_total = _money(item.get("line_total"))
    invalid = (
        isinstance(qty, bool)
        or not isinstance(qty, int)
        or qty <= 0
        or qty > 3
        or unit_price <= 0
        or line_total != _money(unit_price * qty)
    )
    if invalid:
        raise PaymentFirstError(f"Reservation #{rid} has invalid stored values.")
    if str(item.get("category") or "").upper() != "BOOK":
        raise PaymentFirstError(f"Reservation #{rid} is not a book reservation.")
    cursor.execute(
        "SELECT COALESCE(SUM(amount),0) AS paid FROM payments "
        "WHERE branch_id=%s AND enrollment_id=%s "
        "AND target_type='reservation' AND target_id=%s",
        (bill["branch_id"], bill["enrollment_id"], rid),
    )
    if _money(_row_value(cursor.fetchone(), "paid") or 0) != Decimal("0.00"):
        raise PaymentFirstError(f"Reservation #{rid} already has payment activity.")
    return {**dict(reservation), **dict(item), "amount": line_total}


def _lock_inventory(cursor, rows, branch_id):
    ids = sorted({int(row["item_id"]) for row in rows})
    cursor.execute(
        "SELECT item_id,branch_id,item_name,stock_total,reserved_qty,is_active,price "
        "FROM inventory_items WHERE item_id=ANY(%s) ORDER BY item_id FOR UPDATE",
        (ids,),
    )
    items = {int(row["item_id"]): row for row in (cursor.fetchall() or [])}
    if len(items) != len(ids):
        raise PaymentFirstError("One or more inventory items no longer exist.")
    rows_by_item = {}
    size_keys = []
    for row in rows:
        item = items[int(row["item_id"])]
        if (int(item["branch_id"]) != int(branch_id) or not item.get("is_active")
                or _money(item.get("price")) <= 0):
            raise PaymentFirstError("A selected book is no longer available for sale.")
        rows_by_item.setdefault(int(row["item_id"]), []).append(row)
        if row.get("size_label"):
            size_keys.append((int(row["item_id"]), str(row["size_label"])))
    for item_id, item_rows in rows_by_item.items():
        item = items[item_id]
        available = int(item.get("stock_total") or 0) - int(item.get("reserved_qty") or 0)
        required = sum(int(row["qty"]) for row in item_rows)
        if available < required:
            raise PaymentFirstInventoryUnavailable(
                f"{item.get('item_name') or 'A selected book'} is no longer in stock.",
                [entry["reservation_id"] for entry in item_rows],
            )
    sizes = {}
    if size_keys:
        keys = sorted(set(size_keys))
        cursor.execute(
            "SELECT size_id,item_id,size_label,stock_total,reserved_qty "
            "FROM inventory_item_sizes WHERE (item_id,size_label) IN "
            "(SELECT * FROM unnest(%s::integer[],%s::text[])) "
            "ORDER BY item_id,size_id FOR UPDATE",
            ([key[0] for key in keys], [key[1] for key in keys]),
        )
        sizes = {(int(row["item_id"]), str(row["size_label"])): row
                 for row in (cursor.fetchall() or [])}
    rows_by_size = {}
    for row in rows:
        size = sizes.get((int(row["item_id"]), str(row.get("size_label") or "")))
        row["size_id"] = size.get("size_id") if size else None
        if size:
            rows_by_size.setdefault(int(size["size_id"]), []).append(row)
    for size_id, size_rows in rows_by_size.items():
        size = sizes[(
            int(size_rows[0]["item_id"]),
            str(size_rows[0].get("size_label") or ""),
        )]
        available = int(size.get("stock_total") or 0) - int(size.get("reserved_qty") or 0)
        required = sum(int(row["qty"]) for row in size_rows)
        if available < required:
            raise PaymentFirstInventoryUnavailable(
                f"{size_rows[0].get('item_name') or 'A selected book'} is no longer in stock.",
                [entry["reservation_id"] for entry in size_rows],
            )


def _transaction_result(cursor, transaction_id):
    cursor.execute(
        "SELECT pt.*,b.total_amount AS bill_total,b.amount_paid AS bill_paid,"
        "b.balance AS bill_balance,br.branch_name,br.location,"
        "e.student_first_name,e.student_middle_name,e.student_last_name,"
        "e.guardian_first_name,e.guardian_middle_name,e.guardian_last_name,"
        "e.grade_level,e.branch_enrollment_no,"
        "COALESCE(NULLIF(TRIM(u.full_name),''),u.username) AS received_by_name "
        "FROM payment_transactions pt JOIN billing b ON b.bill_id=pt.bill_id "
        "JOIN enrollments e ON e.enrollment_id=pt.enrollment_id "
        "JOIN branches br ON br.branch_id=pt.branch_id "
        "JOIN users u ON u.user_id=pt.received_by WHERE pt.transaction_id=%s",
        (transaction_id,),
    )
    transaction = dict(cursor.fetchone())
    cursor.execute(
        "SELECT p.payment_id,p.target_id AS reservation_id,p.amount,ii.item_name,"
        "ri.qty,ri.unit_price,ri.line_total FROM payments p "
        "JOIN reservation_items ri ON ri.reservation_id=p.target_id "
        "JOIN inventory_items ii ON ii.item_id=ri.item_id "
        "WHERE p.transaction_id=%s AND p.target_type='reservation' ORDER BY p.target_id",
        (transaction_id,),
    )
    transaction["items"] = [dict(row) for row in (cursor.fetchall() or [])]
    return transaction


def _retry_result(cursor, transaction, bill, amount, method, reservation_ids):
    mismatch = (
        int(transaction["branch_id"]) != int(bill["branch_id"])
        or int(transaction["bill_id"]) != int(bill["bill_id"])
        or int(transaction["enrollment_id"]) != int(bill["enrollment_id"])
        or _money(transaction["total_amount"]) != amount
        or str(transaction["payment_method"]).lower() != method
    )
    if mismatch:
        raise PaymentFirstError("Payment request key was reused for different details.")
    cursor.execute(
        "SELECT target_id FROM payments WHERE transaction_id=%s "
        "AND target_type='reservation' ORDER BY target_id",
        (transaction["transaction_id"],),
    )
    existing = [int(_row_value(row, "target_id")) for row in cursor.fetchall() or []]
    if existing != sorted(int(value) for value in reservation_ids):
        raise PaymentFirstError("Payment request key was reused for different books.")
    return _transaction_result(cursor, transaction["transaction_id"])


def process_payment_first_batch(
    cursor, *, bill, reservation_ids, amount, payment_method, notes,
    received_by, idempotency_key
):
    """Fully pay and allocate one or more books in one database transaction."""
    require_payment_first_schema(cursor)
    amount = _money(amount)
    method = str(payment_method or "").strip().lower()
    key = str(idempotency_key or "").strip()
    if (
        amount <= 0
        or not method
        or re.fullmatch(r"[A-Za-z0-9_-]{16,128}", key) is None
    ):
        raise PaymentFirstError("Invalid payment request. Reload and try again.")
    cursor.execute("SELECT pg_advisory_xact_lock(%s)", (_lock_id(f"book-payment:{key}"),))
    cursor.execute("SELECT * FROM payment_transactions WHERE idempotency_key=%s FOR UPDATE", (key,))
    existing = cursor.fetchone()
    if existing:
        return _retry_result(cursor, existing, bill, amount, method, reservation_ids)
    rows = _locked_reservations(cursor, reservation_ids, bill)
    expected = _money(sum((row["amount"] for row in rows), Decimal("0.00")))
    if amount != expected:
        raise PaymentFirstError(f"Full payment of PHP {expected:,.2f} is required.")
    if amount > _money(bill.get("balance") or 0):
        raise PaymentFirstError("Payment exceeds the current billing balance.")
    _lock_inventory(cursor, rows, bill["branch_id"])
    receipt = (
        f"OR-BATCH-{datetime.now(timezone.utc):%Y%m%d}-"
        f"{secrets.token_hex(16).upper()}"
    )
    cursor.execute(
        "INSERT INTO payment_transactions (idempotency_key,receipt_number,bill_id,"
        "enrollment_id,branch_id,year_id,total_amount,payment_method,notes,received_by) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING transaction_id",
        (key, receipt, bill["bill_id"], bill["enrollment_id"], bill["branch_id"],
         bill.get("year_id"), amount, method, notes, received_by),
    )
    transaction_id = int(_row_value(cursor.fetchone(), "transaction_id"))
    _write_children(cursor, rows, bill, transaction_id, method, notes, received_by)
    cursor.execute("SELECT COALESCE(SUM(amount),0) AS total FROM payments WHERE transaction_id=%s", (transaction_id,))
    if _money(_row_value(cursor.fetchone(), "total") or 0) != amount:
        raise PaymentFirstError("The itemized payment total is inconsistent.")
    return _transaction_result(cursor, transaction_id)


def _write_children(cursor, rows, bill, transaction_id, method, notes, received_by):
    for row in rows:
        cursor.execute(
            "INSERT INTO payments (bill_id,enrollment_id,branch_id,year_id,amount,"
            "payment_method,receipt_number,notes,received_by,target_type,target_id,transaction_id) "
            "VALUES (%s,%s,%s,%s,%s,%s,NULL,%s,%s,'reservation',%s,%s) RETURNING payment_id",
            (bill["bill_id"], bill["enrollment_id"], bill["branch_id"], bill.get("year_id"),
             row["amount"], method, notes, received_by, row["reservation_id"], transaction_id),
        )
        payment_id = int(_row_value(cursor.fetchone(), "payment_id"))
        cursor.execute(
            "UPDATE inventory_items SET reserved_qty=reserved_qty+%s "
            "WHERE item_id=%s AND branch_id=%s AND stock_total-reserved_qty >= %s",
            (row["qty"], row["item_id"], bill["branch_id"], row["qty"]),
        )
        if cursor.rowcount != 1:
            raise PaymentFirstInventoryUnavailable(
                "A selected book is no longer in stock.",
                [r["reservation_id"] for r in rows if r["item_id"] == row["item_id"]],
            )
        if row.get("size_id") is not None:
            cursor.execute(
                "UPDATE inventory_item_sizes SET reserved_qty=reserved_qty+%s "
                "WHERE size_id=%s AND item_id=%s AND stock_total-reserved_qty >= %s",
                (row["qty"], row["size_id"], row["item_id"], row["qty"]),
            )
            if cursor.rowcount != 1:
                raise PaymentFirstInventoryUnavailable(
                    "A selected book size is no longer in stock.",
                    [
                        r["reservation_id"] for r in rows
                        if r.get("size_id") == row.get("size_id")
                    ],
                )
        cursor.execute(
            "INSERT INTO reservation_inventory_allocations (reservation_id,"
            "reservation_item_id,branch_id,item_id,size_id,payment_id,payment_target_type,"
            "payment_target_id,quantity,allocation_state,allocated_by_user_id) "
            "VALUES (%s,%s,%s,%s,%s,%s,'reservation',%s,%s,'ALLOCATED',%s)",
            (row["reservation_id"], row["reservation_item_id"], bill["branch_id"],
             row["item_id"], row.get("size_id"), payment_id, row["reservation_id"],
             row["qty"], received_by),
        )
        cursor.execute(
            "UPDATE reservations SET status='PAID',paid_at=NOW() WHERE reservation_id=%s "
            "AND branch_id=%s AND status='RESERVED' AND inventory_policy=%s",
            (row["reservation_id"], bill["branch_id"], PAYMENT_FIRST_POLICY),
        )
        if cursor.rowcount != 1:
            raise PaymentFirstError("A reservation changed during payment.")
