CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    username TEXT NOT NULL
);

CREATE TABLE enrollments (
    enrollment_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id)
);

CREATE TABLE exams (
    exam_id SERIAL PRIMARY KEY,
    duration_mins INTEGER NOT NULL,
    scheduled_start TIMESTAMPTZ
);

CREATE TABLE exam_results (
    result_id SERIAL PRIMARY KEY,
    exam_id INTEGER NOT NULL REFERENCES exams(exam_id),
    enrollment_id INTEGER NOT NULL REFERENCES enrollments(enrollment_id),
    score INTEGER,
    total_points INTEGER,
    submitted_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status TEXT NOT NULL DEFAULT 'in_progress'
);

CREATE TABLE exam_questions (
    question_id SERIAL PRIMARY KEY,
    exam_id INTEGER NOT NULL REFERENCES exams(exam_id),
    points INTEGER NOT NULL
);

CREATE TABLE exam_answers (
    result_id INTEGER NOT NULL REFERENCES exam_results(result_id),
    question_id INTEGER NOT NULL REFERENCES exam_questions(question_id),
    student_answer TEXT,
    is_correct BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (result_id, question_id)
);

CREATE TABLE individual_extensions (
    extension_id SERIAL PRIMARY KEY,
    item_id INTEGER NOT NULL,
    enrollment_id INTEGER NOT NULL,
    item_type TEXT NOT NULL,
    new_due_date TIMESTAMPTZ
);
