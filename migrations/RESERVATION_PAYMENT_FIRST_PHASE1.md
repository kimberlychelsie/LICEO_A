# Reservation Payment-First Phase 1

This document records the read-only audit and the rollout contract for the
approved payment-first book reservation policy. The SQL files beside this
document are preparation artifacts only. They have not been executed.

## Prepared migrations

Run in this order only after a production preflight and explicit approval:

1. `add_reservation_inventory_allocations.sql`
2. `add_reservation_availability_events.sql`
3. `add_payment_transactions.sql`

All three migrations are additive. They do not backfill rows, change existing
receipts, reset inventory, or delete data. `CREATE TABLE IF NOT EXISTS`,
`ADD COLUMN IF NOT EXISTS`, named-constraint checks, and `CREATE INDEX IF NOT
EXISTS` make them rerunnable for the expected complete-or-absent deployment.
A partially hand-created table still requires inspection before rerunning.

## Existing behavior traced

- `routes/student.py:student_reservation` creates one reservation header for a
  submitted book cart, creates several reservation item rows, and immediately
  increments item and size `reserved_qty` under row locks.
- The same Student route is used by an authorized linked Parent after checking
  `parent_student`; Parent history is rendered by
  `routes/parent.py:parent_reservations_list`.
- `routes/cashier.py:process_payment` locks billing rows and accepts direct or
  general payments. Current direct reservation validation permits a payment up
  to the remaining balance, so partial book payments remain possible in the
  legacy runtime.
- General payment processing writes several targeted `payments` rows and calls
  `generate_receipt_number` per row. The first row is used as the representative
  receipt; there is no durable batch identity for one official combined receipt.
- `utils/reservation_security.py:get_verified_direct_settlement` recognizes
  only ownership-matched, directly targeted reservation payments. General
  payment attribution is intentionally not inferred for release.
- Cashier and Librarian claim routes require `PAID`, verified direct settlement,
  and guarded inventory deduction. `deduct_reserved_inventory` decreases both
  physical stock and the legacy hold. The locked status update prevents a
  second successful claim.
- Student/Parent/Cashier cancellation uses billing-before-reservation locking,
  rejects ambiguous payment evidence, and calls `release_reserved_inventory`
  without increasing physical stock.
- Librarian restock changes physical stock. No durable shortage episode or
  recipient-level notification deduplication currently exists.

## Read-only local database audit

The inspected connection was explicitly limited to local loopback and used a
PostgreSQL read-only transaction. It identified PostgreSQL 18.1, database
`liceo_db`. This is local development data and must not be treated as Railway
production evidence.

Aggregate results:

| Check | Result |
| --- | ---: |
| Reservations | 5 |
| RESERVED / CLAIMED / CANCELLED | 3 / 1 / 1 |
| Historical multi-item reservations | 3 |
| Maximum lines in one reservation | 4 |
| Direct reservation payment rows | 1 |
| Partial or overpaid direct book cases | 0 / 0 |
| General payment rows | 1 |
| Missing or duplicate receipt rows | 0 / 0 |
| Item physical stock / stored reserved | 15,598 / 8 |
| Item expected legacy holds / mismatches | 8 / 0 |
| Size physical stock / stored reserved | 4,800 / 0 |
| Size expected legacy holds / mismatches | 0 / 0 |

There were no local orphan enrollments, item-branch mismatches, inconsistent
line totals, bill/payment scope mismatches, missing direct reservation targets,
or direct reservation payment scope mismatches. Production must be audited
independently before migration.

## Schema findings

- `reservations` has a branch FK and status check, but `enrollment_id` has no FK.
- `reservation_items` references reservations and inventory items and enforces
  positive quantity. Branch consistency is currently application-enforced.
- `payments.target_type` plus `target_id` is polymorphic and cannot provide a
  reservation FK. `receipt_number` is unique per existing payment row.
- `inventory_items` and `inventory_item_sizes` store aggregate physical and
  reserved quantities. They cannot identify which reservation owns a hold.
- `school_years` has the required `UNIQUE (branch_id, year_id)` key.
- Student and Parent notification tables have different primary-key names and
  recipient shapes. The prepared delivery table therefore owns deduplication
  without a fragile polymorphic notification-row FK.

## Compatibility contract

`reservations.inventory_policy` is nullable. Existing NULL rows remain legacy
and must continue through the current checkout-held paths. Phase 2 must write
`PAYMENT_FIRST` explicitly for each new one-book reservation. It must never
guess a historical row's mode from status, date, payment, or `reserved_qty`.

Existing RESERVED, PAID, CLAIMED, and CANCELLED rows remain readable. No
allocation row is fabricated for them. Historical direct and general payments
and receipt numbers remain unchanged. Claims and cancellations of NULL-policy
rows continue using the legacy helpers until separately reconciled.

For a new payment-first reservation, one allocation row owns the exact
reservation line, inventory item, optional size, quantity, branch, and direct
payment row. The unique reservation-item key prevents duplicate allocation.
Its composite foreign keys prove that the reservation item, item ID, quantity,
branch, and reservation-targeted payment all describe the same allocation.
`reserved_qty` remains the aggregate fast counter: Phase 2 increments it only
when allocation and full payment commit, and decrements it once when the
allocation becomes CONSUMED or RELEASED.

The database does not determine that a payment amount fully settles a
reservation. Phase 2B must lock the billing, reservation, payment, and
inventory rows in the documented order; compare the trusted stored line total
with the reservation-targeted payment; and insert the payment plus allocation
in one transaction. The payment is inserted first and the allocation FK then
references it, avoiding a circular dependency.

## Payment transaction invariants

One `payment_transactions` row owns the official receipt and idempotency key.
Its child `payments` rows retain itemized `target_type` and `target_id`, and new
rows link through nullable `transaction_id`. Historical rows stay NULL.

The Phase 2 transaction must:

1. Reject partial payment for every new PAYMENT_FIRST book reservation.
2. Reject the full submitted general payment if any amount cannot be allocated.
3. Insert exactly one transaction header and one targeted payment row per paid
   reservation, then verify `SUM(payments.amount) = total_amount` before commit.
4. Store the official receipt only on `payment_transactions`; transaction-linked
   child rows must not invent several official receipts. Receipt rendering must
   query by transaction ID and itemize all targets.
5. Generate official numbers as
   `OR-BATCH-YYYYMMDD-<32 hexadecimal characters>`. Existing `OR-*` payment
   receipts stay unchanged; new child payment rows cannot use the reserved
   `OR-BATCH-` namespace.
6. Reuse a caller-supplied idempotency key on retry. A uniqueness conflict may
   return the existing committed result only when branch, bill, enrollment,
   amount, and payment method all match exactly. Any mismatch is a conflict,
   not a retry.

PostgreSQL cannot enforce the cross-row amount sum with a normal CHECK. The
application must verify it in the same transaction, and tests must cover an
injected failure before commit.

## Deterministic lock order

Every Phase 2 payment, cancellation, claim, and reconciliation path must use:

1. Billing rows by ascending `bill_id`.
2. Reservation rows by ascending `reservation_id`.
3. Inventory item rows by ascending `item_id`.
4. Inventory size rows by ascending `size_id`.
5. Insert the payment transaction, targeted payments, allocations, events, and
   notifications only after validation while those locks remain held.

The final-copy race is resolved by the inventory row lock. The winner rechecks
`stock_total - reserved_qty`, records full payment and allocation, increments
the aggregate hold, and commits atomically. The loser sees insufficient stock;
the complete payment attempt rolls back and no payment or receipt is stored.

Restock code may lock inventory directly but must not subsequently lock billing
or reservation rows in reverse order. It can resolve already identified event
rows and enqueue notifications in the restock transaction without locking the
reservation header.

## Availability notification contract

An UNAVAILABLE event represents one shortage episode for one book
reservation. Only one unresolved event is allowed per reservation. Restock
resolution locks the unresolved event, sets its `resolved_at`, and creates one
AVAILABLE_AGAIN event tied by foreign key to the same reservation, reservation
item, and episode. The service must also verify that the related row is an
UNAVAILABLE event. AVAILABLE_AGAIN does not allocate or promise stock;
payment-time stock validation remains authoritative.

For each Student and currently authorized linked Parent, insert the existing
notification row and one `reservation_availability_deliveries` row in the same
transaction. The unique event/type/user key makes retries recipient-idempotent.
Parent recipients must be resolved from `parent_student` at delivery time.
The delivery table prevents duplicate Student/Parent delivery per event, while
the service remains responsible for proving the Student owns the reservation
and each Parent is currently linked and authorized.

## Production identity verification

Do not paste or print `DATABASE_URL`. In Railway, open the active web service,
confirm which PostgreSQL service its `DATABASE_URL` reference points to, then
run the following only in that linked database's query console. These are
read-only and intentionally avoid personal data:

```sql
BEGIN READ ONLY;
SET LOCAL statement_timeout = '10s';

SELECT current_database() AS database_name,
       current_user AS database_user,
       current_setting('server_version') AS postgres_version,
       current_setting('transaction_read_only') AS transaction_read_only;

SELECT (SELECT COUNT(*) FROM public.reservations) AS reservations,
       (SELECT COUNT(*) FROM public.reservation_items) AS reservation_items,
       (SELECT COUNT(*) FROM public.payments) AS payments,
       (SELECT COUNT(*) FROM public.inventory_items) AS inventory_items;

SELECT status, COUNT(*) AS records
FROM public.reservations
GROUP BY status
ORDER BY status;

WITH expected AS (
    SELECT ri.item_id, SUM(ri.qty)::BIGINT AS expected_reserved
    FROM public.reservations r
    JOIN public.reservation_items ri
      ON ri.reservation_id = r.reservation_id
    WHERE r.status IN ('RESERVED', 'PAID')
    GROUP BY ri.item_id
)
SELECT COUNT(*) FILTER (
           WHERE ii.reserved_qty <> COALESCE(e.expected_reserved, 0)
       ) AS mismatched_items,
       COALESCE(SUM(ii.reserved_qty), 0) AS stored_reserved,
       COALESCE(SUM(e.expected_reserved), 0) AS expected_reserved
FROM public.inventory_items ii
LEFT JOIN expected e ON e.item_id = ii.item_id;

WITH expected AS (
    SELECT ri.item_id,
           ri.size_label,
           SUM(ri.qty)::BIGINT AS expected_reserved
    FROM public.reservations r
    JOIN public.reservation_items ri
      ON ri.reservation_id = r.reservation_id
    WHERE r.status IN ('RESERVED', 'PAID')
      AND ri.size_label IS NOT NULL
    GROUP BY ri.item_id, ri.size_label
)
SELECT COUNT(*) FILTER (
           WHERE s.reserved_qty <> COALESCE(e.expected_reserved, 0)
       ) AS mismatched_sizes,
       COALESCE(SUM(s.reserved_qty), 0) AS stored_reserved,
       COALESCE(SUM(e.expected_reserved), 0) AS expected_reserved
FROM public.inventory_item_sizes s
LEFT JOIN expected e
       ON e.item_id = s.item_id
      AND e.size_label = s.size_label;

COMMIT;
```

The verified active database must report the previously observed 64
reservations before production reconciliation is considered complete. A
different count means the service/database link or query context must be
resolved first; it is not permission to change either database.

## Rollout and rollback

1. Back up production and run the read-only reconciliation queries first.
2. Put migration execution under a maintenance window; these regular indexes
   may lock their tables briefly. For large production tables, prepare separate
   `CREATE INDEX CONCURRENTLY` commands outside a transaction.
3. Apply the three schema migrations in order. Do not backfill policy,
   allocations, transaction IDs, events, or delivery rows.
4. Deploy a bridge release that reads both NULL legacy and PAYMENT_FIRST rows,
   while new payment-first checkout remains feature-disabled.
5. Enable payment-first checkout only after payment, receipt, claim,
   cancellation, notification, and concurrency tests pass against a restored
   production snapshot.

Rollback must disable new payment-first checkout before reverting application
code. The additive tables and columns should remain in place. Older code does
not understand PAYMENT_FIRST rows and must not process them as legacy holds;
use the bridge release for operational rollback. Dropping schema objects or
rewriting policy values is not an approved rollback.

## Approval gates before Phase 2

- Run the same aggregate audit against verified production in read-only mode.
- Confirm the production notification primary keys and school-year composite
  unique constraint match the inspected schema.
- Approve `inventory_policy = NULL` as the permanent legacy marker.
- Approve child `payments.receipt_number = NULL` for new transaction-linked
  rows, with the official number stored on `payment_transactions`.
- Approve the idempotency-key retention and retry response behavior.
- Approve the exact shortage/restock notification text and links.
- Approve maintenance-window indexes or a separate concurrent-index runbook.
- Reconcile any production inventory mismatch before enabling payment-first.
