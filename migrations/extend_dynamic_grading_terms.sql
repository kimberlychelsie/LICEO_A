-- Allow policy-defined 4th, 5th, and later ordinal grading periods in legacy
-- teacher-weight and transfer tables. No application data rows are changed.

BEGIN;

DO $$
DECLARE
    existing_type "char";
    existing_definition TEXT;
BEGIN
    IF to_regclass('public.teacher_grading_weights') IS NOT NULL THEN
        SELECT c.contype, pg_get_constraintdef(c.oid)
          INTO existing_type, existing_definition
        FROM pg_constraint c
        WHERE c.conrelid = 'public.teacher_grading_weights'::regclass
          AND c.conname = 'teacher_grading_weights_period_check';

        IF existing_type IS NOT NULL AND existing_type <> 'c' THEN
            RAISE EXCEPTION
                'teacher_grading_weights_period_check is not a CHECK constraint; manual review required';
        END IF;

        IF existing_definition IS NULL
           OR existing_definition NOT LIKE '%[1-9][0-9]*%' THEN
            IF existing_definition IS NOT NULL THEN
                ALTER TABLE public.teacher_grading_weights
                    DROP CONSTRAINT teacher_grading_weights_period_check;
            END IF;
            ALTER TABLE public.teacher_grading_weights
                ADD CONSTRAINT teacher_grading_weights_period_check
                CHECK (grading_period ~ '^[1-9][0-9]*(st|nd|rd|th)$') NOT VALID;
        END IF;

        ALTER TABLE public.teacher_grading_weights
            VALIDATE CONSTRAINT teacher_grading_weights_period_check;
    END IF;
END $$;

DO $$
DECLARE
    existing_type "char";
    existing_definition TEXT;
BEGIN
    IF to_regclass('public.student_transfer_requests') IS NOT NULL THEN
        SELECT c.contype, pg_get_constraintdef(c.oid)
          INTO existing_type, existing_definition
        FROM pg_constraint c
        WHERE c.conrelid = 'public.student_transfer_requests'::regclass
          AND c.conname = 'chk_transfer_term';

        IF existing_type IS NOT NULL AND existing_type <> 'c' THEN
            RAISE EXCEPTION
                'chk_transfer_term is not a CHECK constraint; manual review required';
        END IF;

        IF existing_definition IS NULL
           OR existing_definition NOT LIKE '%[1-9][0-9]*%' THEN
            IF existing_definition IS NOT NULL THEN
                ALTER TABLE public.student_transfer_requests
                    DROP CONSTRAINT chk_transfer_term;
            END IF;
            ALTER TABLE public.student_transfer_requests
                ADD CONSTRAINT chk_transfer_term
                CHECK (effective_term ~ '^[1-9][0-9]*(st|nd|rd|th)$') NOT VALID;
        END IF;

        ALTER TABLE public.student_transfer_requests
            VALIDATE CONSTRAINT chk_transfer_term;
    END IF;
END $$;

COMMIT;
