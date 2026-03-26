ALTER TABLE teacher_announcements ADD COLUMN year_id INTEGER NOT NULL;

ALTER TABLE grading_weights ADD COLUMN year_id integer;

ALTER TABLE grading_weights
ADD CONSTRAINT grading_weights_full_unique
UNIQUE (teacher_id, section_id, subject_id, grading_period, year_id);

ALTER TABLE attendance_scores ADD COLUMN year_id integer;

ALTER TABLE attendance_scores
ADD CONSTRAINT attendance_scores_unique
UNIQUE (enrollment_id, subject_id, grading_period, year_id);

ALTER TABLE attendance_scores
ADD COLUMN updated_at timestamp with time zone;

ALTER TABLE participation_scores ADD COLUMN year_id integer;

ALTER TABLE participation_scores
ADD CONSTRAINT participation_scores_unique
UNIQUE (enrollment_id, subject_id, grading_period, year_id);

ALTER TABLE participation_scores
ADD COLUMN updated_at timestamp with time zone;

ALTER TABLE posted_grades ADD COLUMN section_id integer;

ALTER TABLE posted_grades ADD COLUMN year_id integer;
ALTER TABLE posted_grades ADD COLUMN posted_by integer;

ALTER TABLE posted_grades
ADD CONSTRAINT posted_grades_section_id_fkey
FOREIGN KEY (section_id) REFERENCES sections(section_id) ON DELETE CASCADE;

ALTER TABLE posted_grades
ADD CONSTRAINT posted_grades_unique
UNIQUE (enrollment_id, subject_id, grading_period, year_id);

GRANT USAGE, SELECT ON SEQUENCE posted_grades_grade_id_seq TO liceo_db;
