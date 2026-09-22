-- ================================================================
-- Performance Indexes Migration
-- Safe to run multiple times (IF NOT EXISTS)
-- Covers all high-traffic tables used by the LMS
-- ================================================================

-- enrollments (most queried table in the system)
CREATE INDEX IF NOT EXISTS idx_enroll_branch_id        ON public.enrollments (branch_id);
CREATE INDEX IF NOT EXISTS idx_enroll_year_id          ON public.enrollments (year_id);
CREATE INDEX IF NOT EXISTS idx_enroll_branch_year      ON public.enrollments (branch_id, year_id);
CREATE INDEX IF NOT EXISTS idx_enroll_status           ON public.enrollments (status);
CREATE INDEX IF NOT EXISTS idx_enroll_branch_year_stat ON public.enrollments (branch_id, year_id, status);
CREATE INDEX IF NOT EXISTS idx_enroll_section_id       ON public.enrollments (section_id);
CREATE INDEX IF NOT EXISTS idx_enroll_lrn              ON public.enrollments (lrn);
CREATE INDEX IF NOT EXISTS idx_enroll_email            ON public.enrollments (lower(email));
CREATE INDEX IF NOT EXISTS idx_enroll_guardian_email   ON public.enrollments (lower(guardian_email));
CREATE INDEX IF NOT EXISTS idx_enroll_branch_enroll_no ON public.enrollments (branch_id, branch_enrollment_no);

-- users
CREATE INDEX IF NOT EXISTS idx_users_username    ON public.users (lower(username));
CREATE INDEX IF NOT EXISTS idx_users_email       ON public.users (lower(email));
CREATE INDEX IF NOT EXISTS idx_users_role        ON public.users (role);
CREATE INDEX IF NOT EXISTS idx_users_branch_id   ON public.users (branch_id);
CREATE INDEX IF NOT EXISTS idx_users_role_branch ON public.users (role, branch_id);
CREATE INDEX IF NOT EXISTS idx_users_status      ON public.users (status);

-- student_accounts
CREATE INDEX IF NOT EXISTS idx_stud_acct_enrollment ON public.student_accounts (enrollment_id);
CREATE INDEX IF NOT EXISTS idx_stud_acct_username   ON public.student_accounts (lower(username));

-- posted_grades
CREATE INDEX IF NOT EXISTS idx_grades_enrollment_id ON public.posted_grades (enrollment_id);
CREATE INDEX IF NOT EXISTS idx_grades_section_subj  ON public.posted_grades (section_id, subject_id);
CREATE INDEX IF NOT EXISTS idx_grades_period        ON public.posted_grades (grading_period);
CREATE INDEX IF NOT EXISTS idx_grades_enroll_subj_p ON public.posted_grades (enrollment_id, subject_id, grading_period);

-- activities
CREATE INDEX IF NOT EXISTS idx_activities_section    ON public.activities (section_id);
CREATE INDEX IF NOT EXISTS idx_activities_subject    ON public.activities (subject_id);
CREATE INDEX IF NOT EXISTS idx_activities_period     ON public.activities (grading_period);
CREATE INDEX IF NOT EXISTS idx_activities_sec_subj_p ON public.activities (section_id, subject_id, grading_period);

-- activity_grades
CREATE INDEX IF NOT EXISTS idx_act_grades_activity   ON public.activity_grades (activity_id);
CREATE INDEX IF NOT EXISTS idx_act_grades_submission ON public.activity_grades (submission_id);
CREATE INDEX IF NOT EXISTS idx_act_grades_student    ON public.activity_grades (student_id);

-- exams
CREATE INDEX IF NOT EXISTS idx_exams_section_subj ON public.exams (section_id, subject_id);
CREATE INDEX IF NOT EXISTS idx_exams_period        ON public.exams (grading_period);

-- exam_results
CREATE INDEX IF NOT EXISTS idx_exam_results_exam   ON public.exam_results (exam_id);
CREATE INDEX IF NOT EXISTS idx_exam_results_enroll ON public.exam_results (enrollment_id);

-- sections
CREATE INDEX IF NOT EXISTS idx_sections_branch_year ON public.sections (branch_id, year_id);

-- section_teachers
CREATE INDEX IF NOT EXISTS idx_sec_teachers_teacher ON public.section_teachers (teacher_id);
CREATE INDEX IF NOT EXISTS idx_sec_teachers_section ON public.section_teachers (section_id);

-- attendance_scores
CREATE INDEX IF NOT EXISTS idx_attend_scores_enroll  ON public.attendance_scores (enrollment_id);
CREATE INDEX IF NOT EXISTS idx_attend_scores_section ON public.attendance_scores (section_id);
CREATE INDEX IF NOT EXISTS idx_attend_scores_period  ON public.attendance_scores (grading_period);

-- student_notifications
CREATE INDEX IF NOT EXISTS idx_stud_notif_student_id ON public.student_notifications (student_id);
CREATE INDEX IF NOT EXISTS idx_stud_notif_is_read    ON public.student_notifications (student_id, is_read);

-- parent_notifications
CREATE INDEX IF NOT EXISTS idx_parent_notif_parent_id  ON public.parent_notifications (parent_id);
CREATE INDEX IF NOT EXISTS idx_parent_notif_student_id ON public.parent_notifications (student_id);

-- enrollment_documents
CREATE INDEX IF NOT EXISTS idx_enroll_docs_enroll_id ON public.enrollment_documents (enrollment_id);

-- grade_submission_requests
CREATE INDEX IF NOT EXISTS idx_grade_sub_section ON public.grade_submission_requests (section_id, subject_id);
CREATE INDEX IF NOT EXISTS idx_grade_sub_status  ON public.grade_submission_requests (status);

-- school_years
CREATE INDEX IF NOT EXISTS idx_school_years_branch ON public.school_years (branch_id);
CREATE INDEX IF NOT EXISTS idx_school_years_active ON public.school_years (branch_id, is_active);
