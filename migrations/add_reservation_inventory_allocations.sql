-- Phase 1 preparation: explicit inventory allocation ownership.
--
-- Review only. Do not execute until the payment-first application release and
-- production preflight have been approved. This migration is additive and
-- intentionally does not backfill or alter historical inventory counters.

ALTER TABLE public.reservations
    ADD COLUMN IF NOT EXISTS inventory_policy VARCHAR(32);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conrelid = 'public.reservations'::regclass
          AND conname = 'reservations_inventory_policy_check'
    ) THEN
        ALTER TABLE public.reservations
            ADD CONSTRAINT reservations_inventory_policy_check
            CHECK (
                inventory_policy IS NULL
                OR inventory_policy IN ('CHECKOUT_HOLD', 'PAYMENT_FIRST')
            ) NOT VALID;
    END IF;
END
$$;

COMMENT ON COLUMN public.reservations.inventory_policy IS
    'NULL denotes an unclassified historical reservation; new payment-first rows must explicitly use PAYMENT_FIRST.';

-- These redundant composite keys let foreign keys prove branch and ownership
-- relationships instead of relying on application joins alone.
CREATE UNIQUE INDEX IF NOT EXISTS uq_reservations_id_branch
    ON public.reservations (reservation_id, branch_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_reservation_items_allocation_owner
    ON public.reservation_items
       (reservation_item_id, reservation_id, item_id, qty);

CREATE UNIQUE INDEX IF NOT EXISTS uq_reservation_items_event_owner
    ON public.reservation_items
       (reservation_item_id, reservation_id, item_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_inventory_items_id_branch
    ON public.inventory_items (item_id, branch_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_inventory_sizes_id_item
    ON public.inventory_item_sizes (size_id, item_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_payments_allocation_target
    ON public.payments
       (payment_id, branch_id, target_type, target_id);

-- CREATE INDEX IF NOT EXISTS only compares object names. Fail before creating
-- dependent foreign keys if a same-named index has a different definition.
DO $$
DECLARE
    actual_definition TEXT;
BEGIN
    SELECT pg_get_indexdef('public.uq_reservations_id_branch'::regclass)
      INTO actual_definition;
    IF actual_definition !~* '\(reservation_id, branch_id\)$' THEN
        RAISE EXCEPTION
            'uq_reservations_id_branch has an unexpected definition: %',
            actual_definition;
    END IF;

    SELECT pg_get_indexdef(
        'public.uq_reservation_items_allocation_owner'::regclass
    ) INTO actual_definition;
    IF actual_definition !~* '\(reservation_item_id, reservation_id, item_id, qty\)$' THEN
        RAISE EXCEPTION
            'uq_reservation_items_allocation_owner has an unexpected definition: %',
            actual_definition;
    END IF;

    SELECT pg_get_indexdef(
        'public.uq_reservation_items_event_owner'::regclass
    ) INTO actual_definition;
    IF actual_definition !~* '\(reservation_item_id, reservation_id, item_id\)$' THEN
        RAISE EXCEPTION
            'uq_reservation_items_event_owner has an unexpected definition: %',
            actual_definition;
    END IF;

    SELECT pg_get_indexdef('public.uq_inventory_items_id_branch'::regclass)
      INTO actual_definition;
    IF actual_definition !~* '\(item_id, branch_id\)$' THEN
        RAISE EXCEPTION
            'uq_inventory_items_id_branch has an unexpected definition: %',
            actual_definition;
    END IF;

    SELECT pg_get_indexdef('public.uq_inventory_sizes_id_item'::regclass)
      INTO actual_definition;
    IF actual_definition !~* '\(size_id, item_id\)$' THEN
        RAISE EXCEPTION
            'uq_inventory_sizes_id_item has an unexpected definition: %',
            actual_definition;
    END IF;

    SELECT pg_get_indexdef('public.uq_payments_allocation_target'::regclass)
      INTO actual_definition;
    IF actual_definition !~* '\(payment_id, branch_id, target_type, target_id\)$' THEN
        RAISE EXCEPTION
            'uq_payments_allocation_target has an unexpected definition: %',
            actual_definition;
    END IF;
END
$$;

CREATE TABLE IF NOT EXISTS public.reservation_inventory_allocations (
    allocation_id       BIGSERIAL PRIMARY KEY,
    reservation_id      INTEGER NOT NULL,
    reservation_item_id INTEGER NOT NULL,
    branch_id           INTEGER NOT NULL,
    item_id              INTEGER NOT NULL,
    size_id              INTEGER,
    payment_id           INTEGER NOT NULL,
    payment_target_type  VARCHAR(50) NOT NULL DEFAULT 'reservation',
    payment_target_id    INTEGER NOT NULL,
    quantity             INTEGER NOT NULL,
    allocation_state     VARCHAR(16) NOT NULL DEFAULT 'ALLOCATED',
    allocated_by_user_id INTEGER NOT NULL,
    allocated_at         TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    consumed_at          TIMESTAMP WITHOUT TIME ZONE,
    released_at          TIMESTAMP WITHOUT TIME ZONE,

    CONSTRAINT reservation_inventory_allocations_reservation_item_key
        UNIQUE (reservation_item_id),
    CONSTRAINT reservation_inventory_allocations_quantity_check
        CHECK (quantity > 0),
    CONSTRAINT reservation_inventory_allocations_payment_target_check
        CHECK (
            payment_target_type = 'reservation'
            AND payment_target_id = reservation_id
        ),
    CONSTRAINT reservation_inventory_allocations_state_check
        CHECK (allocation_state IN ('ALLOCATED', 'CONSUMED', 'RELEASED')),
    CONSTRAINT reservation_inventory_allocations_lifecycle_check
        CHECK (
            (allocation_state = 'ALLOCATED' AND consumed_at IS NULL AND released_at IS NULL)
            OR (allocation_state = 'CONSUMED' AND consumed_at IS NOT NULL AND released_at IS NULL)
            OR (allocation_state = 'RELEASED' AND released_at IS NOT NULL AND consumed_at IS NULL)
        ),
    CONSTRAINT reservation_inventory_allocations_reservation_branch_fkey
        FOREIGN KEY (reservation_id, branch_id)
        REFERENCES public.reservations (reservation_id, branch_id)
        ON DELETE RESTRICT,
    CONSTRAINT reservation_inventory_allocations_reservation_item_fkey
        FOREIGN KEY (
            reservation_item_id,
            reservation_id,
            item_id,
            quantity
        )
        REFERENCES public.reservation_items (
            reservation_item_id,
            reservation_id,
            item_id,
            qty
        )
        ON DELETE RESTRICT,
    CONSTRAINT reservation_inventory_allocations_item_branch_fkey
        FOREIGN KEY (item_id, branch_id)
        REFERENCES public.inventory_items (item_id, branch_id)
        ON DELETE RESTRICT,
    CONSTRAINT reservation_inventory_allocations_size_item_fkey
        FOREIGN KEY (size_id, item_id)
        REFERENCES public.inventory_item_sizes (size_id, item_id)
        ON DELETE RESTRICT,
    CONSTRAINT reservation_inventory_allocations_payment_branch_fkey
        FOREIGN KEY (
            payment_id,
            branch_id,
            payment_target_type,
            payment_target_id
        )
        REFERENCES public.payments (
            payment_id,
            branch_id,
            target_type,
            target_id
        )
        ON DELETE RESTRICT,
    CONSTRAINT reservation_inventory_allocations_user_fkey
        FOREIGN KEY (allocated_by_user_id)
        REFERENCES public.users (user_id)
        ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_reservation_allocations_reservation
    ON public.reservation_inventory_allocations
       (reservation_id, allocation_state);

CREATE INDEX IF NOT EXISTS idx_reservation_allocations_inventory
    ON public.reservation_inventory_allocations
       (branch_id, item_id, size_id, allocation_state);

CREATE INDEX IF NOT EXISTS idx_reservation_allocations_payment
    ON public.reservation_inventory_allocations (payment_id);

-- Detect partially hand-created or same-named incompatible constraints.
DO $$
DECLARE
    expected RECORD;
    actual_definition TEXT;
BEGIN
    FOR expected IN
        SELECT *
        FROM (VALUES
            (
                'reservation_inventory_allocations_reservation_item_key',
                'UNIQUE \(reservation_item_id\)'
            ),
            (
                'reservation_inventory_allocations_reservation_item_fkey',
                'FOREIGN KEY \(reservation_item_id, reservation_id, item_id, quantity\)'
            ),
            (
                'reservation_inventory_allocations_payment_branch_fkey',
                'FOREIGN KEY \(payment_id, branch_id, payment_target_type, payment_target_id\)'
            ),
            (
                'reservation_inventory_allocations_payment_target_check',
                'payment_target_id.*reservation_id'
            )
        ) AS required_constraint(constraint_name, definition_pattern)
    LOOP
        SELECT pg_get_constraintdef(oid)
          INTO actual_definition
          FROM pg_constraint
         WHERE conrelid =
                   'public.reservation_inventory_allocations'::regclass
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

-- Required service invariant: before inserting an allocation, lock the
-- reservation and its payment, verify the payment is transaction-linked and
-- equals the reservation's complete stored balance, then insert both records
-- in the same transaction. The foreign keys above prove ownership, quantity,
-- branch, and reservation targeting without introducing a circular FK.

-- Validation is intentionally separate from creation. Run only after the
-- production preflight confirms every non-NULL policy value is recognized.
-- ALTER TABLE public.reservations
--     VALIDATE CONSTRAINT reservations_inventory_policy_check;
