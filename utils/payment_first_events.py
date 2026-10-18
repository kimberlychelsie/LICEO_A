"""Deduplicated availability events and portal notifications."""

import uuid

from utils.payment_first_reservations import (
    PAYMENT_FIRST_POLICY,
    _row_value,
    payment_first_schema_ready,
    require_payment_first_schema,
)


def _notify(cursor, event_id, row, event_type):
    unavailable = event_type == "UNAVAILABLE"
    title = (
        "Reserved Book Currently Unavailable"
        if unavailable else "Reserved Book Available Again"
    )
    item_name = row.get("item_name") or "book"
    message = (
        f"{item_name} was allocated to another completed payment first. "
        "Your unpaid reservation remains open and no payment was recorded."
        if unavailable
        else f"{item_name} is available again. Please ask the cashier to "
             "verify stock before completing payment."
    )
    student_id = row.get("student_user_id")
    enrollment_id = row.get("enrollment_id")
    if student_id:
        cursor.execute(
            "INSERT INTO reservation_availability_deliveries "
            "(availability_event_id,recipient_type,recipient_user_id) "
            "VALUES (%s,'STUDENT',%s) ON CONFLICT DO NOTHING RETURNING delivery_id",
            (event_id, student_id),
        )
        if cursor.fetchone():
            cursor.execute(
                "INSERT INTO student_notifications (student_id,title,message,link) "
                "VALUES (%s,%s,%s,'/student/reservations')",
                (student_id, title, message),
            )
    if not enrollment_id:
        return
    cursor.execute(
        "SELECT DISTINCT parent_id FROM parent_student WHERE student_id=%s ORDER BY parent_id",
        (enrollment_id,),
    )
    for parent in cursor.fetchall() or []:
        parent_id = int(_row_value(parent, "parent_id"))
        cursor.execute(
            "INSERT INTO reservation_availability_deliveries "
            "(availability_event_id,recipient_type,recipient_user_id) "
            "VALUES (%s,'PARENT',%s) ON CONFLICT DO NOTHING RETURNING delivery_id",
            (event_id, parent_id),
        )
        if cursor.fetchone():
            cursor.execute(
                "INSERT INTO parent_notifications (parent_id,student_id,title,message,link) "
                "VALUES (%s,%s,%s,%s,'/parent/reservations')",
                (parent_id, enrollment_id, title, message),
            )


def _new_shortage(cursor, row):
    cursor.execute(
        "SELECT availability_event_id FROM reservation_availability_events "
        "WHERE reservation_id=%s AND event_type='UNAVAILABLE' "
        "AND resolved_at IS NULL FOR UPDATE",
        (row["reservation_id"],),
    )
    existing = cursor.fetchone()
    if existing:
        return int(_row_value(existing, "availability_event_id"))
    cursor.execute(
        "SELECT COALESCE(MAX(episode_number),0)+1 AS episode "
        "FROM reservation_availability_events WHERE reservation_item_id=%s",
        (row["reservation_item_id"],),
    )
    episode = int(_row_value(cursor.fetchone(), "episode") or 1)
    cursor.execute(
        "INSERT INTO reservation_availability_events "
        "(event_key,reservation_id,reservation_item_id,branch_id,item_id,size_id,"
        "episode_number,event_type) VALUES (%s,%s,%s,%s,%s,%s,%s,'UNAVAILABLE') "
        "ON CONFLICT DO NOTHING RETURNING availability_event_id",
        (str(uuid.uuid4()), row["reservation_id"], row["reservation_item_id"],
         row["branch_id"], row["item_id"], row.get("size_id"), episode),
    )
    created = cursor.fetchone()
    if not created:
        cursor.execute(
            "SELECT availability_event_id FROM reservation_availability_events "
            "WHERE reservation_id=%s AND event_type='UNAVAILABLE' AND resolved_at IS NULL",
            (row["reservation_id"],),
        )
        created = cursor.fetchone()
    event_id = int(_row_value(created, "availability_event_id"))
    _notify(cursor, event_id, row, "UNAVAILABLE")
    return event_id


def record_unavailable_reservations(cursor, *, branch_id, reservation_ids):
    """Record losing reservations after the failed payment transaction rolls back."""
    require_payment_first_schema(cursor)
    ids = sorted({int(value) for value in reservation_ids})
    if not ids:
        return 0
    cursor.execute(
        "SELECT r.reservation_id,r.branch_id,r.enrollment_id,r.student_user_id,"
        "ri.reservation_item_id,ri.item_id,ri.size_label,ii.item_name,iis.size_id "
        "FROM reservations r JOIN reservation_items ri ON ri.reservation_id=r.reservation_id "
        "JOIN inventory_items ii ON ii.item_id=ri.item_id "
        "LEFT JOIN inventory_item_sizes iis ON iis.item_id=ri.item_id "
        "AND iis.size_label=ri.size_label WHERE r.branch_id=%s "
        "AND r.inventory_policy=%s AND r.status='RESERVED' "
        "AND r.reservation_id=ANY(%s) ORDER BY r.reservation_id",
        (branch_id, PAYMENT_FIRST_POLICY, ids),
    )
    count = 0
    for row in cursor.fetchall() or []:
        _new_shortage(cursor, dict(row))
        count += 1
    return count


def record_newly_unavailable(cursor, *, branch_id, paid_reservation_ids):
    """Notify other unpaid requests when a winning payment exhausts stock."""
    require_payment_first_schema(cursor)
    paid_ids = sorted({int(value) for value in paid_reservation_ids})
    cursor.execute(
        "SELECT DISTINCT ri.item_id FROM reservation_items ri "
        "WHERE ri.reservation_id=ANY(%s) ORDER BY ri.item_id",
        (paid_ids,),
    )
    item_ids = [int(_row_value(row, "item_id")) for row in cursor.fetchall() or []]
    if not item_ids:
        return 0
    cursor.execute(
        "SELECT r.reservation_id,r.branch_id,r.enrollment_id,r.student_user_id,"
        "ri.reservation_item_id,ri.item_id,ri.qty,ri.size_label,ii.item_name,"
        "ii.stock_total-ii.reserved_qty AS item_available,iis.size_id,"
        "CASE WHEN iis.size_id IS NULL THEN NULL "
        "ELSE iis.stock_total-iis.reserved_qty END AS size_available "
        "FROM reservations r JOIN reservation_items ri ON ri.reservation_id=r.reservation_id "
        "JOIN inventory_items ii ON ii.item_id=ri.item_id "
        "LEFT JOIN inventory_item_sizes iis ON iis.item_id=ri.item_id "
        "AND iis.size_label=ri.size_label WHERE r.branch_id=%s "
        "AND r.inventory_policy=%s AND r.status='RESERVED' "
        "AND ri.item_id=ANY(%s) AND NOT (r.reservation_id=ANY(%s)) "
        "ORDER BY r.reservation_id",
        (branch_id, PAYMENT_FIRST_POLICY, item_ids, paid_ids),
    )
    count = 0
    for row in cursor.fetchall() or []:
        qty = int(row.get("qty") or 0)
        item_available = int(row.get("item_available") or 0)
        size_available = row.get("size_available")
        if item_available >= qty and (
            size_available is None or int(size_available) >= qty
        ):
            continue
        _new_shortage(cursor, dict(row))
        count += 1
    return count


def resolve_available_events(cursor, *, branch_id, item_id):
    if not payment_first_schema_ready(cursor):
        return 0
    cursor.execute(
        "SELECT ev.*,r.enrollment_id,r.student_user_id,ri.qty AS requested_qty,ii.item_name,"
        "ii.stock_total AS item_stock,ii.reserved_qty AS item_reserved,"
        "iis.stock_total AS size_stock,iis.reserved_qty AS size_reserved "
        "FROM reservation_availability_events ev "
        "JOIN reservations r ON r.reservation_id=ev.reservation_id "
        "JOIN reservation_items ri ON ri.reservation_item_id=ev.reservation_item_id "
        "JOIN inventory_items ii ON ii.item_id=ev.item_id "
        "LEFT JOIN inventory_item_sizes iis ON iis.size_id=ev.size_id "
        "WHERE ev.branch_id=%s AND ev.item_id=%s AND ev.event_type='UNAVAILABLE' "
        "AND ev.resolved_at IS NULL AND r.status='RESERVED' "
        "AND r.inventory_policy=%s ORDER BY ev.availability_event_id FOR UPDATE OF ev",
        (branch_id, item_id, PAYMENT_FIRST_POLICY),
    )
    resolved = 0
    for row in cursor.fetchall() or []:
        item_available = int(row["item_stock"] or 0) - int(row["item_reserved"] or 0)
        requested_qty = int(row.get("requested_qty") or 0)
        size_available = None
        if row.get("size_id") is not None:
            size_available = int(row.get("size_stock") or 0) - int(row.get("size_reserved") or 0)
        if (
            item_available < requested_qty
            or (size_available is not None and size_available < requested_qty)
        ):
            continue
        cursor.execute(
            "UPDATE reservation_availability_events SET resolved_at=NOW() "
            "WHERE availability_event_id=%s AND resolved_at IS NULL",
            (row["availability_event_id"],),
        )
        if cursor.rowcount != 1:
            continue
        cursor.execute(
            "INSERT INTO reservation_availability_events "
            "(event_key,reservation_id,reservation_item_id,branch_id,item_id,size_id,"
            "episode_number,event_type,related_event_id) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,'AVAILABLE_AGAIN',%s) "
            "RETURNING availability_event_id",
            (str(uuid.uuid4()), row["reservation_id"], row["reservation_item_id"],
             row["branch_id"], row["item_id"], row.get("size_id"),
             row["episode_number"], row["availability_event_id"]),
        )
        event_id = int(_row_value(cursor.fetchone(), "availability_event_id"))
        _notify(cursor, event_id, dict(row), "AVAILABLE_AGAIN")
        resolved += 1
    return resolved
