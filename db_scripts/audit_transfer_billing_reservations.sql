-- Read-only audit: cross-branch reservations encountered while reconciling bills.
-- This does not update, lock, or delete any record.
WITH resolved_reservations AS (
    SELECT
        r.reservation_id,
        r.branch_id AS reservation_branch_id,
        r.enrollment_id AS reservation_enrollment_id,
        COALESCE(r.enrollment_id, sa.enrollment_id) AS resolved_enrollment_id,
        r.student_user_id
    FROM reservations r
    LEFT JOIN users u ON u.user_id = r.student_user_id
    LEFT JOIN student_accounts sa ON sa.username = u.username
),
transfer_links AS (
    SELECT transfer_id, source_enrollment_id, destination_enrollment_id,
           source_branch_id, destination_branch_id, status
    FROM student_transfer_requests
    WHERE status = 'approved'
)
SELECT DISTINCT
    b.bill_id,
    b.enrollment_id AS bill_enrollment_id,
    b.branch_id AS bill_branch_id,
    b.year_id AS bill_year_id,
    rr.reservation_id,
    rr.resolved_enrollment_id AS reservation_enrollment_id,
    rr.reservation_branch_id,
    tl.transfer_id,
    tl.status AS transfer_status,
    CASE
        WHEN tl.transfer_id IS NOT NULL THEN 'VERIFIED_TRANSFER'
        ELSE 'MANUAL_REVIEW_REQUIRED'
    END AS reconciliation_status
FROM billing b
JOIN resolved_reservations rr
  ON rr.resolved_enrollment_id = b.enrollment_id
LEFT JOIN transfer_links tl
  ON tl.source_enrollment_id = rr.resolved_enrollment_id
 AND tl.destination_enrollment_id = b.enrollment_id
 AND tl.source_branch_id = rr.reservation_branch_id
 AND tl.destination_branch_id = b.branch_id
WHERE rr.reservation_branch_id IS DISTINCT FROM b.branch_id
ORDER BY b.bill_id, rr.reservation_id;
