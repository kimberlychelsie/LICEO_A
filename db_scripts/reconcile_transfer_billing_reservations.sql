-- Safe transfer/billing reconciliation workflow.
-- Run only after reviewing the returned rows. It never deletes reservations,
-- payments, bills, or historical transfer rows.
BEGIN;

-- Repair only missing bill scope metadata from its owning enrollment.
-- Non-null mismatches are deliberately NOT overwritten; they require review.
UPDATE billing b
SET branch_id = e.branch_id,
    year_id = COALESCE(b.year_id, e.year_id),
    updated_at = NOW()
FROM enrollments e
WHERE e.enrollment_id = b.enrollment_id
  AND (b.branch_id IS NULL OR b.year_id IS NULL)
RETURNING b.bill_id, b.enrollment_id, b.branch_id, b.year_id;

-- Produce the remaining cross-branch candidates for manual reconciliation.
-- A VERIFIED_TRANSFER row is safely handled by the application reconciliation
-- path. MANUAL_REVIEW_REQUIRED rows must not be reassigned automatically.
WITH transfer_links AS (
    SELECT transfer_id, source_enrollment_id, destination_enrollment_id,
           source_branch_id, destination_branch_id, status
    FROM student_transfer_requests
    WHERE status = 'approved'
)
SELECT DISTINCT
    b.bill_id,
    b.enrollment_id AS destination_enrollment_id,
    b.branch_id AS destination_branch_id,
    r.reservation_id,
    r.branch_id AS source_branch_id,
    COALESCE(r.enrollment_id, sa.enrollment_id) AS source_enrollment_id,
    tl.transfer_id,
    CASE WHEN tl.transfer_id IS NULL
         THEN 'MANUAL_REVIEW_REQUIRED'
         ELSE 'VERIFIED_TRANSFER'
    END AS reconciliation_status
FROM billing b
JOIN reservations r
  ON r.branch_id IS DISTINCT FROM b.branch_id
LEFT JOIN users u ON u.user_id = r.student_user_id
LEFT JOIN student_accounts sa ON sa.username = u.username
LEFT JOIN transfer_links tl
  ON tl.source_enrollment_id = COALESCE(r.enrollment_id, sa.enrollment_id)
 AND tl.destination_enrollment_id = b.enrollment_id
 AND tl.source_branch_id = r.branch_id
 AND tl.destination_branch_id = b.branch_id
WHERE COALESCE(r.enrollment_id, sa.enrollment_id) = b.enrollment_id
ORDER BY b.bill_id, r.reservation_id;

-- The only persisted repair above fills NULL scope metadata from the owning
-- enrollment. Cross-branch non-NULL mismatches remain untouched for manual
-- review, while verified transfers are reconciled by the application path.
COMMIT;
