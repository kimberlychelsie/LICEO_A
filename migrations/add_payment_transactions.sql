-- Phase 1 preparation: one official receipt across itemized payment rows.
--
-- Review only. This migration adds a nullable link to existing payments and
-- does not alter historical receipts or payment attribution.

-- OR-* remains valid for historical payment rows. Only the new OR-BATCH-
-- namespace is reserved for payment_transactions. Abort instead of silently
-- taking over a receipt number if a historical collision is found.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM public.payments
        WHERE receipt_number LIKE 'OR-BATCH-%'
    ) THEN
        RAISE EXCEPTION
            'Existing payments use the reserved OR-BATCH receipt namespace';
    END IF;
END
$$;

CREATE UNIQUE INDEX IF NOT EXISTS uq_billing_scope
    ON public.billing (bill_id, enrollment_id, branch_id);

CREATE TABLE IF NOT EXISTS public.payment_transactions (
    transaction_id BIGSERIAL PRIMARY KEY,
    idempotency_key VARCHAR(128) NOT NULL,
    receipt_number  VARCHAR(50) NOT NULL,
    bill_id         INTEGER NOT NULL,
    enrollment_id   INTEGER NOT NULL,
    branch_id       INTEGER NOT NULL,
    year_id         INTEGER,
    total_amount    NUMERIC(12,2) NOT NULL,
    payment_method  VARCHAR(20) NOT NULL,
    notes           TEXT,
    received_by     INTEGER NOT NULL,
    created_at      TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),

    CONSTRAINT payment_transactions_idempotency_key_key
        UNIQUE (idempotency_key),
    CONSTRAINT payment_transactions_receipt_number_key
        UNIQUE (receipt_number),
    CONSTRAINT payment_transactions_receipt_format_check
        CHECK (
            receipt_number
                ~ '^OR-BATCH-[0-9]{8}-[0-9A-Fa-f]{32}$'
        ),
    CONSTRAINT payment_transactions_total_check
        CHECK (total_amount > 0),
    CONSTRAINT payment_transactions_billing_scope_fkey
        FOREIGN KEY (bill_id, enrollment_id, branch_id)
        REFERENCES public.billing (bill_id, enrollment_id, branch_id)
        ON DELETE RESTRICT,
    CONSTRAINT payment_transactions_branch_year_fkey
        FOREIGN KEY (branch_id, year_id)
        REFERENCES public.school_years (branch_id, year_id)
        ON DELETE RESTRICT,
    CONSTRAINT payment_transactions_received_by_fkey
        FOREIGN KEY (received_by)
        REFERENCES public.users (user_id)
        ON DELETE RESTRICT
);

-- This key allows each linked payment row to prove that it belongs to the
-- same bill, enrollment, and branch as its transaction header.
CREATE UNIQUE INDEX IF NOT EXISTS uq_payment_transactions_scope
    ON public.payment_transactions
       (transaction_id, bill_id, enrollment_id, branch_id);

CREATE INDEX IF NOT EXISTS idx_payment_transactions_bill_created
    ON public.payment_transactions (bill_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_payment_transactions_branch_created
    ON public.payment_transactions (branch_id, created_at DESC);

-- CREATE INDEX IF NOT EXISTS only compares names. Verify the ownership keys
-- that later foreign keys depend on before changing payments.
DO $$
DECLARE
    actual_definition TEXT;
BEGIN
    SELECT pg_get_indexdef('public.uq_billing_scope'::regclass)
      INTO actual_definition;
    IF actual_definition !~* '\(bill_id, enrollment_id, branch_id\)$' THEN
        RAISE EXCEPTION
            'uq_billing_scope has an unexpected definition: %',
            actual_definition;
    END IF;

    SELECT pg_get_indexdef(
        'public.uq_payment_transactions_scope'::regclass
    ) INTO actual_definition;
    IF actual_definition !~* '\(transaction_id, bill_id, enrollment_id, branch_id\)$' THEN
        RAISE EXCEPTION
            'uq_payment_transactions_scope has an unexpected definition: %',
            actual_definition;
    END IF;
END
$$;

ALTER TABLE public.payments
    ADD COLUMN IF NOT EXISTS transaction_id BIGINT;

DO $$
DECLARE
    actual_definition TEXT;
BEGIN
    SELECT pg_get_constraintdef(oid)
      INTO actual_definition
      FROM pg_constraint
     WHERE conrelid = 'public.payments'::regclass
       AND conname = 'payments_batch_target_type_check';

    IF actual_definition IS NULL THEN
        ALTER TABLE public.payments
            ADD CONSTRAINT payments_batch_target_type_check
            CHECK (transaction_id IS NULL OR target_type IS NOT NULL);
    ELSIF actual_definition !~* 'transaction_id IS NULL.*target_type IS NOT NULL' THEN
        RAISE EXCEPTION
            'payments_batch_target_type_check has an unexpected definition: %',
            actual_definition;
    END IF;
END
$$;

DO $$
DECLARE
    actual_definition TEXT;
BEGIN
    SELECT pg_get_constraintdef(oid)
      INTO actual_definition
      FROM pg_constraint
     WHERE conrelid = 'public.payments'::regclass
       AND conname = 'payments_transaction_scope_fkey';

    IF actual_definition IS NULL THEN
        ALTER TABLE public.payments
            ADD CONSTRAINT payments_transaction_scope_fkey
            FOREIGN KEY (transaction_id, bill_id, enrollment_id, branch_id)
            REFERENCES public.payment_transactions
                (transaction_id, bill_id, enrollment_id, branch_id)
            ON DELETE RESTRICT
            NOT VALID;
    ELSIF actual_definition !~* (
        '^FOREIGN KEY \(transaction_id, bill_id, enrollment_id, branch_id\) '
        || 'REFERENCES (public\.)?payment_transactions'
        || '\(transaction_id, bill_id, enrollment_id, branch_id\) '
        || 'ON DELETE RESTRICT'
    ) THEN
        RAISE EXCEPTION
            'payments_transaction_scope_fkey has an unexpected definition: %',
            actual_definition;
    END IF;
END
$$;

DO $$
DECLARE
    actual_definition TEXT;
BEGIN
    SELECT pg_get_constraintdef(oid)
      INTO actual_definition
      FROM pg_constraint
     WHERE conrelid = 'public.payments'::regclass
       AND conname = 'payments_batch_child_receipt_check';

    IF actual_definition IS NULL THEN
        ALTER TABLE public.payments
            ADD CONSTRAINT payments_batch_child_receipt_check
            CHECK (transaction_id IS NULL OR receipt_number IS NULL);
    ELSIF actual_definition !~* 'transaction_id IS NULL.*receipt_number IS NULL' THEN
        RAISE EXCEPTION
            'payments_batch_child_receipt_check has an unexpected definition: %',
            actual_definition;
    END IF;
END
$$;

DO $$
DECLARE
    actual_definition TEXT;
BEGIN
    SELECT pg_get_constraintdef(oid)
      INTO actual_definition
      FROM pg_constraint
     WHERE conrelid = 'public.payments'::regclass
       AND conname = 'payments_batch_reservation_target_check';

    IF actual_definition IS NULL THEN
        ALTER TABLE public.payments
            ADD CONSTRAINT payments_batch_reservation_target_check
            CHECK (
                transaction_id IS NULL
                OR target_type <> 'reservation'
                OR target_id IS NOT NULL
            );
    ELSIF actual_definition !~* (
        'transaction_id IS NULL.*target_type.*reservation.*target_id IS NOT NULL'
    ) THEN
        RAISE EXCEPTION
            'payments_batch_reservation_target_check has an unexpected definition: %',
            actual_definition;
    END IF;
END
$$;

DO $$
DECLARE
    actual_definition TEXT;
BEGIN
    SELECT pg_get_constraintdef(oid)
      INTO actual_definition
      FROM pg_constraint
     WHERE conrelid = 'public.payments'::regclass
       AND conname = 'payments_batch_receipt_namespace_check';

    IF actual_definition IS NULL THEN
        ALTER TABLE public.payments
            ADD CONSTRAINT payments_batch_receipt_namespace_check
            CHECK (
                receipt_number IS NULL
                OR receipt_number NOT LIKE 'OR-BATCH-%'
            );
    ELSIF actual_definition !~* 'receipt_number.*OR-BATCH-' THEN
        RAISE EXCEPTION
            'payments_batch_receipt_namespace_check has an unexpected definition: %',
            actual_definition;
    END IF;
END
$$;

-- Verify the critical table constraints as definitions, not merely by name.
DO $$
DECLARE
    expected RECORD;
    actual_definition TEXT;
BEGIN
    FOR expected IN
        SELECT *
        FROM (VALUES
            (
                'payment_transactions_idempotency_key_key',
                'UNIQUE \(idempotency_key\)'
            ),
            (
                'payment_transactions_receipt_number_key',
                'UNIQUE \(receipt_number\)'
            ),
            (
                'payment_transactions_receipt_format_check',
                'OR-BATCH-'
            ),
            (
                'payment_transactions_billing_scope_fkey',
                'FOREIGN KEY \(bill_id, enrollment_id, branch_id\)'
            ),
            (
                'payment_transactions_branch_year_fkey',
                'FOREIGN KEY \(branch_id, year_id\)'
            )
        ) AS required_constraint(constraint_name, definition_pattern)
    LOOP
        SELECT pg_get_constraintdef(oid)
          INTO actual_definition
          FROM pg_constraint
         WHERE conrelid = 'public.payment_transactions'::regclass
           AND conname = expected.constraint_name;

        IF actual_definition IS NULL
           OR actual_definition !~* expected.definition_pattern THEN
            RAISE EXCEPTION
                'Constraint % is missing or unexpected: %',
                expected.constraint_name,
                actual_definition;
        END IF;
    END LOOP;
END
$$;

CREATE INDEX IF NOT EXISTS idx_payments_transaction_id
    ON public.payments (transaction_id)
    WHERE transaction_id IS NOT NULL;

-- A reservation may be attributed only once inside a single receipt batch.
CREATE UNIQUE INDEX IF NOT EXISTS uq_payments_transaction_reservation
    ON public.payments (transaction_id, target_id)
    WHERE transaction_id IS NOT NULL
      AND target_type = 'reservation';

DO $$
DECLARE
    actual_definition TEXT;
BEGIN
    SELECT pg_get_indexdef(
        'public.uq_payments_transaction_reservation'::regclass
    ) INTO actual_definition;
    IF actual_definition !~* (
        '\(transaction_id, target_id\).*WHERE.*transaction_id IS NOT NULL'
        || '.*target_type.*reservation'
    ) THEN
        RAISE EXCEPTION
            'uq_payments_transaction_reservation has an unexpected definition: %',
            actual_definition;
    END IF;
END
$$;

COMMENT ON COLUMN public.payments.transaction_id IS
    'Nullable for historical rows; new grouped payments reference one official payment transaction.';

-- Required service invariants for Phase 2B:
-- 1. Generate exactly OR-BATCH-YYYYMMDD-<32 hex characters>.
-- 2. On idempotency conflict, return the existing result only when branch_id,
--    bill_id, enrollment_id, total_amount, and payment_method all match.
-- 3. Before commit, require every transaction-linked reservation payment to
--    target an authorized reservation and require child SUM(amount) to equal
--    payment_transactions.total_amount exactly.
--
-- Reconciliation query (must return no rows):
-- SELECT pt.transaction_id,
--        pt.total_amount,
--        COALESCE(SUM(p.amount), 0)::NUMERIC(12,2) AS child_total
-- FROM public.payment_transactions pt
-- LEFT JOIN public.payments p
--        ON p.transaction_id = pt.transaction_id
-- GROUP BY pt.transaction_id, pt.total_amount
-- HAVING COALESCE(SUM(p.amount), 0)::NUMERIC(12,2) <> pt.total_amount;

-- Validate after the Phase 2 writer and production audit confirm every new
-- transaction-linked payment has matching bill/enrollment/branch scope:
-- ALTER TABLE public.payments
--     VALIDATE CONSTRAINT payments_transaction_scope_fkey;
