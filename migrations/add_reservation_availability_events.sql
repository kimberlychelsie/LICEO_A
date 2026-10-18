-- Phase 1 preparation: durable shortage/restock episodes and recipient dedup.
--
-- Review only. Run after add_reservation_inventory_allocations.sql because
-- this migration uses the composite ownership indexes prepared there.

CREATE TABLE IF NOT EXISTS public.reservation_availability_events (
    availability_event_id BIGSERIAL PRIMARY KEY,
    event_key              UUID NOT NULL,
    reservation_id         INTEGER NOT NULL,
    reservation_item_id    INTEGER NOT NULL,
    branch_id              INTEGER NOT NULL,
    item_id                 INTEGER NOT NULL,
    size_id                 INTEGER,
    episode_number          INTEGER NOT NULL,
    event_type              VARCHAR(24) NOT NULL,
    related_event_id        BIGINT,
    created_at              TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    resolved_at             TIMESTAMP WITHOUT TIME ZONE,

    CONSTRAINT reservation_availability_events_event_key_key
        UNIQUE (event_key),
    CONSTRAINT reservation_availability_events_related_episode_key
        UNIQUE (
            availability_event_id,
            reservation_id,
            reservation_item_id,
            episode_number
        ),
    CONSTRAINT reservation_availability_events_episode_key
        UNIQUE (reservation_item_id, episode_number, event_type),
    CONSTRAINT reservation_availability_events_episode_check
        CHECK (episode_number > 0),
    CONSTRAINT reservation_availability_events_type_check
        CHECK (event_type IN ('UNAVAILABLE', 'AVAILABLE_AGAIN')),
    CONSTRAINT reservation_availability_events_relation_check
        CHECK (
            (event_type = 'UNAVAILABLE' AND related_event_id IS NULL)
            OR (event_type = 'AVAILABLE_AGAIN' AND related_event_id IS NOT NULL)
        ),
    CONSTRAINT reservation_availability_events_resolved_check
        CHECK (resolved_at IS NULL OR resolved_at >= created_at),
    CONSTRAINT reservation_availability_events_reservation_branch_fkey
        FOREIGN KEY (reservation_id, branch_id)
        REFERENCES public.reservations (reservation_id, branch_id)
        ON DELETE RESTRICT,
    CONSTRAINT reservation_availability_events_reservation_item_fkey
        FOREIGN KEY (reservation_item_id, reservation_id, item_id)
        REFERENCES public.reservation_items (
            reservation_item_id,
            reservation_id,
            item_id
        )
        ON DELETE RESTRICT,
    CONSTRAINT reservation_availability_events_item_branch_fkey
        FOREIGN KEY (item_id, branch_id)
        REFERENCES public.inventory_items (item_id, branch_id)
        ON DELETE RESTRICT,
    CONSTRAINT reservation_availability_events_size_item_fkey
        FOREIGN KEY (size_id, item_id)
        REFERENCES public.inventory_item_sizes (size_id, item_id)
        ON DELETE RESTRICT,
    CONSTRAINT reservation_availability_events_related_episode_fkey
        FOREIGN KEY (
            related_event_id,
            reservation_id,
            reservation_item_id,
            episode_number
        )
        REFERENCES public.reservation_availability_events (
            availability_event_id,
            reservation_id,
            reservation_item_id,
            episode_number
        )
        ON DELETE RESTRICT,
    CONSTRAINT reservation_availability_events_related_not_self_check
        CHECK (
            related_event_id IS NULL
            OR related_event_id <> availability_event_id
        )
);

-- At most one unresolved shortage can exist for a reservation line. A later
-- shortage becomes a new numbered episode only after the prior one resolves.
CREATE UNIQUE INDEX IF NOT EXISTS uq_reservation_unresolved_shortage
    ON public.reservation_availability_events (reservation_id)
    WHERE event_type = 'UNAVAILABLE' AND resolved_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_reservation_availability_inventory
    ON public.reservation_availability_events
       (branch_id, item_id, size_id, event_type, resolved_at);

CREATE INDEX IF NOT EXISTS idx_reservation_availability_reservation
    ON public.reservation_availability_events
       (reservation_id, episode_number, created_at);

CREATE TABLE IF NOT EXISTS public.reservation_availability_deliveries (
    delivery_id          BIGSERIAL PRIMARY KEY,
    availability_event_id BIGINT NOT NULL,
    recipient_type       VARCHAR(16) NOT NULL,
    recipient_user_id    INTEGER NOT NULL,
    delivered_at         TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),

    CONSTRAINT reservation_availability_deliveries_recipient_key
        UNIQUE (availability_event_id, recipient_type, recipient_user_id),
    CONSTRAINT reservation_availability_deliveries_type_check
        CHECK (recipient_type IN ('STUDENT', 'PARENT')),
    CONSTRAINT reservation_availability_deliveries_event_fkey
        FOREIGN KEY (availability_event_id)
        REFERENCES public.reservation_availability_events (availability_event_id)
        ON DELETE CASCADE,
    CONSTRAINT reservation_availability_deliveries_user_fkey
        FOREIGN KEY (recipient_user_id)
        REFERENCES public.users (user_id)
        ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_reservation_availability_delivery_user
    ON public.reservation_availability_deliveries
       (recipient_user_id, delivered_at DESC);

-- Detect incompatible same-named constraints and partial index definitions.
DO $$
DECLARE
    expected RECORD;
    actual_definition TEXT;
BEGIN
    FOR expected IN
        SELECT *
        FROM (VALUES
            (
                'reservation_availability_events_reservation_item_fkey',
                'FOREIGN KEY \(reservation_item_id, reservation_id, item_id\)'
            ),
            (
                'reservation_availability_events_related_episode_fkey',
                'FOREIGN KEY \(related_event_id, reservation_id, reservation_item_id, episode_number\)'
            ),
            (
                'reservation_availability_deliveries_recipient_key',
                'UNIQUE \(availability_event_id, recipient_type, recipient_user_id\)'
            )
        ) AS required_constraint(constraint_name, definition_pattern)
    LOOP
        SELECT pg_get_constraintdef(oid)
          INTO actual_definition
          FROM pg_constraint
         WHERE conrelid = CASE
                 WHEN expected.constraint_name LIKE
                          'reservation_availability_deliveries_%'
                     THEN 'public.reservation_availability_deliveries'::regclass
                 ELSE 'public.reservation_availability_events'::regclass
             END
           AND conname = expected.constraint_name;

        IF actual_definition IS NULL
           OR actual_definition !~* expected.definition_pattern THEN
            RAISE EXCEPTION
                'Constraint % is missing or unexpected: %',
                expected.constraint_name,
                actual_definition;
        END IF;
    END LOOP;

    SELECT pg_get_indexdef(
        'public.uq_reservation_unresolved_shortage'::regclass
    ) INTO actual_definition;
    IF actual_definition !~* '\(reservation_id\).*WHERE.*event_type.*UNAVAILABLE.*resolved_at IS NULL' THEN
        RAISE EXCEPTION
            'uq_reservation_unresolved_shortage has an unexpected definition: %',
            actual_definition;
    END IF;
END
$$;

-- The application must insert the existing notification row and this delivery
-- row in one transaction. The unique recipient key makes retries idempotent
-- without coupling this table to two differently shaped notification tables.
-- Before creating AVAILABLE_AGAIN, the service must lock related_event_id and
-- verify that it is an unresolved UNAVAILABLE event. PostgreSQL CHECK/FK
-- constraints cannot compare event_type across two rows without a trigger.
