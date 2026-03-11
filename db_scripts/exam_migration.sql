-- ══════════════════════════════════════════
-- EXAM SYSTEM MIGRATION
-- ══════════════════════════════════════════

-- 1. Exams table
CREATE TABLE IF NOT EXISTS exams (
    exam_id        SERIAL PRIMARY KEY,
    branch_id      INTEGER NOT NULL REFERENCES branches(branch_id),
    section_id     INTEGER NOT NULL REFERENCES sections(section_id),
    subject_id     INTEGER NOT NULL REFERENCES subjects(subject_id),
    teacher_id     INTEGER NOT NULL REFERENCES users(user_id),
    title          VARCHAR(255) NOT NULL,
    exam_type      VARCHAR(50) DEFAULT 'quiz',   -- quiz / periodical / activity
    duration_mins  INTEGER NOT NULL DEFAULT 30,   -- 30, 60, 120
    scheduled_date DATE,
    status         VARCHAR(20) DEFAULT 'draft',   -- draft / published / closed
    created_at     TIMESTAMP DEFAULT NOW()
);

-- 2. Exam questions
CREATE TABLE IF NOT EXISTS exam_questions (
    question_id    SERIAL PRIMARY KEY,
    exam_id        INTEGER NOT NULL REFERENCES exams(exam_id) ON DELETE CASCADE,
    question_text  TEXT NOT NULL,
    question_type  VARCHAR(20) NOT NULL,           -- mcq / truefalse
    choices        JSONB,                          -- ["A","B","C","D"] for MCQ, NULL for T/F
    correct_answer TEXT NOT NULL,                  -- "A","B","C","D" or "True","False"
    points         INTEGER DEFAULT 1,
    order_num      INTEGER DEFAULT 0
);

-- 3. Exam results (one per student per exam)
CREATE TABLE IF NOT EXISTS exam_results (
    result_id      SERIAL PRIMARY KEY,
    exam_id        INTEGER NOT NULL REFERENCES exams(exam_id) ON DELETE CASCADE,
    enrollment_id  INTEGER NOT NULL REFERENCES enrollments(enrollment_id),
    score          NUMERIC(5,2) DEFAULT 0,
    total_points   INTEGER DEFAULT 0,
    submitted_at   TIMESTAMP,
    started_at     TIMESTAMP DEFAULT NOW(),
    status         VARCHAR(20) DEFAULT 'in_progress', -- in_progress / submitted / auto_submitted
    tab_switches   INTEGER DEFAULT 0               -- track tab switches
);

-- 4. Exam answers (one per question per student)
CREATE TABLE IF NOT EXISTS exam_answers (
    answer_id      SERIAL PRIMARY KEY,
    result_id      INTEGER NOT NULL REFERENCES exam_results(result_id) ON DELETE CASCADE,
    question_id    INTEGER NOT NULL REFERENCES exam_questions(question_id),
    student_answer TEXT,
    is_correct     BOOLEAN DEFAULT FALSE
);

-- 5. Tab switch log (detailed per switch event)
CREATE TABLE IF NOT EXISTS exam_tab_switches (
    id             SERIAL PRIMARY KEY,
    result_id      INTEGER NOT NULL REFERENCES exam_results(result_id) ON DELETE CASCADE,
    switched_at    TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_exams_branch     ON exams(branch_id);
CREATE INDEX IF NOT EXISTS idx_exams_teacher    ON exams(teacher_id);
CREATE INDEX IF NOT EXISTS idx_exams_section    ON exams(section_id);
CREATE INDEX IF NOT EXISTS idx_exam_results_exam ON exam_results(exam_id);
CREATE INDEX IF NOT EXISTS idx_exam_results_enr  ON exam_results(enrollment_id);
CREATE INDEX IF NOT EXISTS idx_exam_answers_res  ON exam_answers(result_id);


-- 1. Randomize question order (no DB change needed)

-- 2. Question limit (pick random N questions)
ALTER TABLE exams ADD COLUMN IF NOT EXISTS question_limit INT DEFAULT NULL;

-- 3. Auto-open / auto-close (scheduled_date already exists, add end time)
ALTER TABLE exams ADD COLUMN IF NOT EXISTS scheduled_start TIMESTAMP DEFAULT NULL;
ALTER TABLE exams ADD COLUMN IF NOT EXISTS scheduled_end   TIMESTAMP DEFAULT NULL;

-- 4. Max attempts
ALTER TABLE exams ADD COLUMN IF NOT EXISTS max_attempts INT DEFAULT 1;

-- 5. Passing score
ALTER TABLE exams ADD COLUMN IF NOT EXISTS passing_score INT DEFAULT 75;

-- 7. Exam instructions
ALTER TABLE exams ADD COLUMN IF NOT EXISTS instructions TEXT DEFAULT NULL;

-- 8. Randomize questions
ALTER TABLE exams ADD COLUMN IF NOT EXISTS randomize BOOLEAN DEFAULT FALSE;