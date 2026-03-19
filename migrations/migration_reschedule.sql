-- Create individual_extensions table to handle student-specific deadlines
CREATE TABLE IF NOT EXISTS individual_extensions (
    extension_id SERIAL PRIMARY KEY,
    enrollment_id INTEGER NOT NULL REFERENCES enrollments(enrollment_id) ON DELETE CASCADE,
    item_type    VARCHAR(20) NOT NULL, -- 'activity', 'exam', 'quiz'
    item_id      INTEGER NOT NULL,      -- activity_id or exam_id
    new_due_date TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    created_at   TIMESTAMP DEFAULT NOW()
);

-- Add unique constraint to prevent duplicate extensions for the same item/student
ALTER TABLE individual_extensions ADD CONSTRAINT uq_extension UNIQUE (enrollment_id, item_type, item_id);
