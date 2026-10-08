--
-- PostgreSQL database dump
--

\restrict jkAStvQ7WoGuVFIipKGRuFlOll2KIwwVNaXJCUggmgI1LUAdDdy2TgMZf2P4U2m

-- Dumped from database version 17.11 (Debian 17.11-1.pgdg13+2)
-- Dumped by pg_dump version 18.1

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: activities; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.activities (
    activity_id integer NOT NULL,
    branch_id integer,
    section_id integer,
    subject_id integer,
    teacher_id integer,
    title character varying(255) NOT NULL,
    category character varying(100),
    instructions text,
    max_score integer DEFAULT 100,
    due_date timestamp without time zone,
    allow_resubmission boolean DEFAULT true,
    allowed_file_types character varying(255),
    attachment_path character varying(500),
    status character varying(50) DEFAULT 'Draft'::character varying,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now(),
    grading_period character varying(50),
    batch_id character varying(20),
    year_id integer,
    is_archived boolean DEFAULT false
);


--
-- Name: activities_activity_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.activities_activity_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: activities_activity_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.activities_activity_id_seq OWNED BY public.activities.activity_id;


--
-- Name: activity_grades; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.activity_grades (
    grade_id integer NOT NULL,
    submission_id integer,
    activity_id integer,
    student_id integer,
    raw_score numeric(5,2),
    max_score integer,
    percentage numeric(5,2),
    remarks text,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


--
-- Name: activity_grades_grade_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.activity_grades_grade_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: activity_grades_grade_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.activity_grades_grade_id_seq OWNED BY public.activity_grades.grade_id;


--
-- Name: activity_submissions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.activity_submissions (
    submission_id integer NOT NULL,
    activity_id integer,
    student_id integer,
    enrollment_id integer,
    file_path character varying(500),
    original_filename character varying(255),
    submitted_at timestamp without time zone DEFAULT now(),
    is_late boolean DEFAULT false,
    attempt_no integer DEFAULT 1,
    is_active boolean DEFAULT true,
    allow_resubmit boolean DEFAULT false,
    status character varying(50) DEFAULT 'Submitted'::character varying,
    feedback text,
    graded_at timestamp without time zone,
    graded_by integer,
    year_id integer,
    attachments jsonb,
    is_viewed boolean DEFAULT false
);


--
-- Name: activity_submissions_submission_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.activity_submissions_submission_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: activity_submissions_submission_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.activity_submissions_submission_id_seq OWNED BY public.activity_submissions.submission_id;


--
-- Name: announcements_announcement_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.announcements_announcement_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: announcements; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.announcements (
    announcement_id integer DEFAULT nextval('public.announcements_announcement_id_seq'::regclass) NOT NULL,
    title character varying(255) NOT NULL,
    message text NOT NULL,
    is_active boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    image_url text,
    branch_id integer,
    audience text DEFAULT 'all'::text NOT NULL
);


--
-- Name: attendance_scores; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.attendance_scores (
    id integer NOT NULL,
    enrollment_id integer NOT NULL,
    section_id integer NOT NULL,
    subject_id integer NOT NULL,
    grading_period character varying(10) NOT NULL,
    score numeric(5,2) DEFAULT 0 NOT NULL,
    updated_at timestamp without time zone DEFAULT now(),
    teacher_id integer NOT NULL,
    year_id integer,
    total_days integer DEFAULT 10
);


--
-- Name: attendance_scores_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.attendance_scores_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: attendance_scores_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.attendance_scores_id_seq OWNED BY public.attendance_scores.id;


--
-- Name: audit_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_logs (
    log_id integer NOT NULL,
    user_id integer,
    user_name character varying(150),
    role character varying(50),
    branch_id integer,
    action character varying(100) NOT NULL,
    details text,
    ip_address character varying(50),
    created_at timestamp without time zone DEFAULT now()
);


--
-- Name: audit_logs_log_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.audit_logs_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: audit_logs_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.audit_logs_log_id_seq OWNED BY public.audit_logs.log_id;


--
-- Name: billing_bill_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.billing_bill_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: billing; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.billing (
    bill_id integer DEFAULT nextval('public.billing_bill_id_seq'::regclass) NOT NULL,
    enrollment_id integer NOT NULL,
    branch_id integer NOT NULL,
    tuition_fee numeric(10,2) DEFAULT 0.00,
    books_fee numeric(10,2) DEFAULT 0.00,
    uniform_fee numeric(10,2) DEFAULT 0.00,
    other_fees numeric(10,2) DEFAULT 0.00,
    total_amount numeric(10,2) NOT NULL,
    amount_paid numeric(10,2) DEFAULT 0.00,
    balance numeric(10,2) NOT NULL,
    status character varying(10) DEFAULT 'pending'::character varying,
    created_by integer NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    year_id integer
);


--
-- Name: book_release_items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.book_release_items (
    release_item_id integer NOT NULL,
    release_id integer NOT NULL,
    item_id integer NOT NULL,
    qty integer NOT NULL,
    unit_price numeric DEFAULT 0 NOT NULL
);


--
-- Name: book_release_items_release_item_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.book_release_items_release_item_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: book_release_items_release_item_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.book_release_items_release_item_id_seq OWNED BY public.book_release_items.release_item_id;


--
-- Name: book_releases; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.book_releases (
    release_id integer NOT NULL,
    branch_id integer NOT NULL,
    enrollment_id integer NOT NULL,
    released_by_user_id integer NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    student_name text
);


--
-- Name: book_releases_release_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.book_releases_release_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: book_releases_release_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.book_releases_release_id_seq OWNED BY public.book_releases.release_id;


--
-- Name: branches_branch_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.branches_branch_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: branches; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.branches (
    branch_id integer DEFAULT nextval('public.branches_branch_id_seq'::regclass) NOT NULL,
    branch_name character varying(100) NOT NULL,
    location character varying(100),
    status character varying(10) DEFAULT 'active'::character varying,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    branch_code character varying(20),
    latitude numeric(10,7),
    longitude numeric(10,7)
);


--
-- Name: chatbot_faqs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.chatbot_faqs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: chatbot_faqs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.chatbot_faqs (
    id integer DEFAULT nextval('public.chatbot_faqs_id_seq'::regclass) NOT NULL,
    branch_id integer,
    question text NOT NULL,
    answer text NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: daily_attendance; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.daily_attendance (
    id integer NOT NULL,
    enrollment_id integer NOT NULL,
    subject_id integer NOT NULL,
    branch_id integer NOT NULL,
    year_id integer NOT NULL,
    attendance_date date NOT NULL,
    status character varying(2) NOT NULL,
    points numeric(3,2) NOT NULL,
    recorded_by integer,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: daily_attendance_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.daily_attendance_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: daily_attendance_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.daily_attendance_id_seq OWNED BY public.daily_attendance.id;


--
-- Name: daily_participation; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.daily_participation (
    id integer NOT NULL,
    enrollment_id integer NOT NULL,
    subject_id integer NOT NULL,
    branch_id integer NOT NULL,
    year_id integer NOT NULL,
    participation_date date NOT NULL,
    points integer NOT NULL,
    recorded_by integer,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: daily_participation_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.daily_participation_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: daily_participation_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.daily_participation_id_seq OWNED BY public.daily_participation.id;


--
-- Name: enrollment_books_book_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.enrollment_books_book_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: enrollment_books; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.enrollment_books (
    book_id integer DEFAULT nextval('public.enrollment_books_book_id_seq'::regclass) NOT NULL,
    enrollment_id integer NOT NULL,
    book_name character varying(100) NOT NULL,
    quantity integer DEFAULT 1,
    created_at timestamp without time zone DEFAULT now() NOT NULL
);


--
-- Name: enrollment_documents_doc_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.enrollment_documents_doc_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: enrollment_documents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.enrollment_documents (
    doc_id integer DEFAULT nextval('public.enrollment_documents_doc_id_seq'::regclass) NOT NULL,
    enrollment_id integer NOT NULL,
    file_name character varying(255) NOT NULL,
    file_path character varying(500) NOT NULL,
    uploaded_at timestamp without time zone DEFAULT now() NOT NULL,
    doc_type character varying(255)
);


--
-- Name: enrollment_history; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.enrollment_history (
    id integer NOT NULL,
    enrollment_id integer,
    school_year character varying(20),
    grade_level character varying(10),
    section_name character varying(20),
    status character varying(20)
);


--
-- Name: enrollment_history_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.enrollment_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: enrollment_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.enrollment_history_id_seq OWNED BY public.enrollment_history.id;


--
-- Name: enrollment_uniforms_uniform_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.enrollment_uniforms_uniform_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: enrollment_uniforms; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.enrollment_uniforms (
    uniform_id integer DEFAULT nextval('public.enrollment_uniforms_uniform_id_seq'::regclass) NOT NULL,
    enrollment_id integer NOT NULL,
    uniform_type character varying(50) NOT NULL,
    size character varying(10) NOT NULL,
    quantity integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL
);


--
-- Name: enrollments_enrollment_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.enrollments_enrollment_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: enrollments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.enrollments (
    enrollment_id integer DEFAULT nextval('public.enrollments_enrollment_id_seq'::regclass) NOT NULL,
    grade_level character varying(50),
    branch_id integer NOT NULL,
    status character varying(20),
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    user_id integer,
    gender character varying(20),
    dob date,
    address text,
    contact_number character varying(20),
    guardian_contact character varying(20),
    previous_school character varying(150),
    branch_enrollment_no integer,
    section_id integer,
    lrn character varying(12),
    email character varying(255),
    guardian_email character varying(255),
    enroll_type character varying(50),
    enroll_date date,
    remarks text,
    birthplace character varying(255),
    father_contact character varying(20),
    father_occupation character varying(100),
    mother_contact character varying(20),
    mother_occupation character varying(100),
    school_year character varying(20),
    profile_image character varying(255),
    year_id integer,
    rejection_reason text,
    rejected_at timestamp without time zone,
    academic_status character varying(50),
    student_first_name character varying(100),
    student_middle_name character varying(100),
    student_last_name character varying(100),
    father_first_name character varying(100),
    father_middle_name character varying(100),
    father_last_name character varying(100),
    mother_first_name character varying(100),
    mother_middle_name character varying(100),
    mother_last_name character varying(100),
    guardian_first_name character varying(100),
    guardian_middle_name character varying(100),
    guardian_last_name character varying(100),
    father_name character varying(255),
    mother_name character varying(255),
    curriculum_type character varying(50) DEFAULT 'basic_ed'::character varying,
    shs_track character varying(50)
);


--
-- Name: exam_answers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.exam_answers (
    answer_id integer NOT NULL,
    result_id integer NOT NULL,
    question_id integer NOT NULL,
    student_answer text,
    is_correct boolean DEFAULT false
);


--
-- Name: exam_answers_answer_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.exam_answers_answer_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: exam_answers_answer_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.exam_answers_answer_id_seq OWNED BY public.exam_answers.answer_id;


--
-- Name: exam_questions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.exam_questions (
    question_id integer NOT NULL,
    exam_id integer NOT NULL,
    question_text text NOT NULL,
    question_type character varying(20) NOT NULL,
    choices text,
    correct_answer text NOT NULL,
    points integer DEFAULT 1,
    order_num integer DEFAULT 0
);


--
-- Name: exam_questions_question_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.exam_questions_question_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: exam_questions_question_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.exam_questions_question_id_seq OWNED BY public.exam_questions.question_id;


--
-- Name: exam_results; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.exam_results (
    result_id integer NOT NULL,
    exam_id integer NOT NULL,
    enrollment_id integer NOT NULL,
    score numeric(5,2) DEFAULT 0,
    total_points integer DEFAULT 0,
    submitted_at timestamp without time zone,
    started_at timestamp without time zone DEFAULT now(),
    status character varying(20) DEFAULT 'in_progress'::character varying,
    tab_switches integer DEFAULT 0,
    year_id integer
);


--
-- Name: exam_results_result_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.exam_results_result_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: exam_results_result_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.exam_results_result_id_seq OWNED BY public.exam_results.result_id;


--
-- Name: exam_student_permissions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.exam_student_permissions (
    permission_id integer NOT NULL,
    exam_id integer NOT NULL,
    enrollment_id integer NOT NULL,
    is_allowed boolean DEFAULT true
);


--
-- Name: exam_student_permissions_permission_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.exam_student_permissions_permission_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: exam_student_permissions_permission_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.exam_student_permissions_permission_id_seq OWNED BY public.exam_student_permissions.permission_id;


--
-- Name: exam_tab_switches; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.exam_tab_switches (
    id integer NOT NULL,
    result_id integer NOT NULL,
    switched_at timestamp without time zone DEFAULT now(),
    reason character varying(50)
);


--
-- Name: exam_tab_switches_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.exam_tab_switches_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: exam_tab_switches_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.exam_tab_switches_id_seq OWNED BY public.exam_tab_switches.id;


--
-- Name: exams; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.exams (
    exam_id integer NOT NULL,
    branch_id integer NOT NULL,
    section_id integer NOT NULL,
    subject_id integer NOT NULL,
    teacher_id integer NOT NULL,
    title character varying(255) NOT NULL,
    exam_type character varying(50) DEFAULT 'quiz'::character varying,
    duration_mins integer DEFAULT 30 NOT NULL,
    scheduled_date date,
    status character varying(20) DEFAULT 'draft'::character varying,
    created_at timestamp without time zone DEFAULT now(),
    question_limit integer,
    scheduled_start timestamp without time zone,
    scheduled_end timestamp without time zone,
    max_attempts integer DEFAULT 1,
    passing_score integer DEFAULT 75,
    instructions text,
    randomize boolean DEFAULT false,
    grading_period character varying(20) DEFAULT '1st'::character varying,
    is_visible boolean DEFAULT false NOT NULL,
    batch_id character varying(20),
    year_id integer,
    is_archived boolean DEFAULT false,
    class_mode character varying(20) DEFAULT 'Virtual'::character varying
);


--
-- Name: exams_exam_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.exams_exam_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: exams_exam_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.exams_exam_id_seq OWNED BY public.exams.exam_id;


--
-- Name: failed_logins; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.failed_logins (
    id integer NOT NULL,
    ip_address character varying(50),
    username character varying(150),
    created_at timestamp without time zone DEFAULT now()
);


--
-- Name: failed_logins_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.failed_logins_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: failed_logins_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.failed_logins_id_seq OWNED BY public.failed_logins.id;


--
-- Name: finalized_grades; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.finalized_grades (
    id integer NOT NULL,
    enrollment_id integer NOT NULL,
    subject_id integer NOT NULL,
    grading_period character varying(10) NOT NULL,
    year_id integer NOT NULL,
    final_attendance_pct numeric(5,2),
    final_participation_avg numeric(5,2),
    finalized_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: finalized_grades_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.finalized_grades_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: finalized_grades_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.finalized_grades_id_seq OWNED BY public.finalized_grades.id;


--
-- Name: grade_levels_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.grade_levels_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: grade_levels; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.grade_levels (
    id integer DEFAULT nextval('public.grade_levels_id_seq'::regclass) NOT NULL,
    name character varying(50) NOT NULL,
    display_order integer DEFAULT 0,
    description text,
    branch_id integer
);


--
-- Name: grade_overrides; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.grade_overrides (
    id integer NOT NULL,
    enrollment_id integer NOT NULL,
    section_id integer NOT NULL,
    subject_id integer NOT NULL,
    grading_period character varying(20) NOT NULL,
    year_id integer NOT NULL,
    override_ww numeric(6,2),
    override_pt numeric(6,2),
    override_qa numeric(6,2),
    override_note text,
    overridden_by integer,
    overridden_at timestamp without time zone DEFAULT now()
);


--
-- Name: grade_overrides_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.grade_overrides_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: grade_overrides_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.grade_overrides_id_seq OWNED BY public.grade_overrides.id;


--
-- Name: grade_submission_requests; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.grade_submission_requests (
    id integer NOT NULL,
    section_id integer NOT NULL,
    subject_id integer NOT NULL,
    grading_period character varying(20) NOT NULL,
    year_id integer NOT NULL,
    branch_id integer NOT NULL,
    status character varying(30) DEFAULT 'draft'::character varying,
    submitted_by integer,
    submitted_at timestamp without time zone,
    registrar_approved_by integer,
    registrar_approved_at timestamp without time zone,
    admin_approved_by integer,
    admin_approved_at timestamp without time zone,
    rejection_remarks text,
    rejected_by integer,
    rejected_at timestamp without time zone
);


--
-- Name: grade_submission_requests_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.grade_submission_requests_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: grade_submission_requests_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.grade_submission_requests_id_seq OWNED BY public.grade_submission_requests.id;


--
-- Name: grading_period_ranges; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.grading_period_ranges (
    id integer NOT NULL,
    branch_id integer NOT NULL,
    year_id integer NOT NULL,
    period_name character varying(10) NOT NULL,
    start_date date NOT NULL,
    end_date date NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: grading_period_ranges_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.grading_period_ranges_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: grading_period_ranges_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.grading_period_ranges_id_seq OWNED BY public.grading_period_ranges.id;


--
-- Name: grading_weights; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.grading_weights (
    id integer NOT NULL,
    teacher_id integer NOT NULL,
    section_id integer NOT NULL,
    subject_id integer NOT NULL,
    grading_period character varying(10) NOT NULL,
    quiz_pct numeric(5,2) DEFAULT 30 NOT NULL,
    exam_pct numeric(5,2) DEFAULT 40 NOT NULL,
    activity_pct numeric(5,2) DEFAULT 30 NOT NULL,
    participation_pct numeric(5,2) DEFAULT 0 NOT NULL,
    attendance_pct numeric(5,2) DEFAULT 0 NOT NULL,
    created_at timestamp without time zone DEFAULT now(),
    weight_id integer,
    branch_id integer,
    updated_at timestamp without time zone,
    year_id integer
);


--
-- Name: grading_weights_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.grading_weights_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: grading_weights_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.grading_weights_id_seq OWNED BY public.grading_weights.id;


--
-- Name: holidays; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.holidays (
    id integer NOT NULL,
    branch_id integer,
    year_id integer NOT NULL,
    holiday_date date NOT NULL,
    holiday_name character varying(100) NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    status character varying(20) DEFAULT 'active'::character varying
);


--
-- Name: holidays_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.holidays_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: holidays_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.holidays_id_seq OWNED BY public.holidays.id;


--
-- Name: individual_extensions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.individual_extensions (
    extension_id integer NOT NULL,
    enrollment_id integer NOT NULL,
    item_type character varying(20) NOT NULL,
    item_id integer NOT NULL,
    new_due_date timestamp without time zone NOT NULL,
    created_at timestamp without time zone DEFAULT now(),
    student_id integer,
    year_id integer
);


--
-- Name: individual_extensions_extension_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.individual_extensions_extension_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: individual_extensions_extension_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.individual_extensions_extension_id_seq OWNED BY public.individual_extensions.extension_id;


--
-- Name: inventory_item_sizes_size_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.inventory_item_sizes_size_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: inventory_item_sizes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.inventory_item_sizes (
    size_id integer DEFAULT nextval('public.inventory_item_sizes_size_id_seq'::regclass) NOT NULL,
    item_id integer NOT NULL,
    size_label character varying(10) NOT NULL,
    stock_total integer DEFAULT 0 NOT NULL,
    reserved_qty integer DEFAULT 0 NOT NULL
);


--
-- Name: inventory_items_item_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.inventory_items_item_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: inventory_items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.inventory_items (
    item_id integer DEFAULT nextval('public.inventory_items_item_id_seq'::regclass) NOT NULL,
    branch_id integer NOT NULL,
    category text NOT NULL,
    item_name text NOT NULL,
    grade_level text,
    is_common boolean DEFAULT false NOT NULL,
    size_label text,
    price numeric(12,2) DEFAULT 0 NOT NULL,
    stock_total integer DEFAULT 0 NOT NULL,
    reserved_qty integer DEFAULT 0 NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    image_url text,
    publisher character varying(100),
    parent_item_id integer,
    is_set_piece boolean DEFAULT false,
    size_price_step numeric(12,2) DEFAULT 20,
    CONSTRAINT inventory_items_category_check CHECK ((category = ANY (ARRAY['BOOK'::text, 'UNIFORM'::text])))
);


--
-- Name: inventory_sizes_size_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.inventory_sizes_size_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: inventory_sizes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.inventory_sizes (
    size_id integer DEFAULT nextval('public.inventory_sizes_size_id_seq'::regclass) NOT NULL,
    item_id integer,
    size_label character varying(10),
    stock_qty integer DEFAULT 0,
    reserved_qty integer DEFAULT 0
);


--
-- Name: login_2fa_tokens; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.login_2fa_tokens (
    token_id integer NOT NULL,
    token_hash character varying(64) NOT NULL,
    user_id integer NOT NULL,
    user_role character varying(50),
    ip_address character varying(45),
    status character varying(20) DEFAULT 'PENDING'::character varying,
    created_at timestamp without time zone DEFAULT (now() AT TIME ZONE 'UTC'::text),
    expires_at timestamp without time zone NOT NULL
);


--
-- Name: login_2fa_tokens_token_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.login_2fa_tokens_token_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: login_2fa_tokens_token_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.login_2fa_tokens_token_id_seq OWNED BY public.login_2fa_tokens.token_id;


--
-- Name: parent_notifications; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.parent_notifications (
    notif_id integer NOT NULL,
    parent_id integer NOT NULL,
    student_id integer,
    title character varying(255) NOT NULL,
    message text NOT NULL,
    link character varying(255),
    is_read boolean DEFAULT false,
    created_at timestamp without time zone DEFAULT now()
);


--
-- Name: parent_notifications_notif_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.parent_notifications_notif_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: parent_notifications_notif_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.parent_notifications_notif_id_seq OWNED BY public.parent_notifications.notif_id;


--
-- Name: parent_student_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.parent_student_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: parent_student; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.parent_student (
    id integer DEFAULT nextval('public.parent_student_id_seq'::regclass) NOT NULL,
    parent_id integer NOT NULL,
    student_id integer NOT NULL,
    relationship character varying(20) DEFAULT 'guardian'::character varying,
    created_at timestamp without time zone DEFAULT now() NOT NULL
);


--
-- Name: participation_scores; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.participation_scores (
    id integer NOT NULL,
    enrollment_id integer NOT NULL,
    section_id integer NOT NULL,
    subject_id integer NOT NULL,
    grading_period character varying(10) NOT NULL,
    score numeric(5,2) DEFAULT 0 NOT NULL,
    updated_at timestamp without time zone DEFAULT now(),
    teacher_id integer NOT NULL,
    year_id integer,
    max_score numeric DEFAULT 10 NOT NULL
);


--
-- Name: participation_scores_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.participation_scores_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: participation_scores_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.participation_scores_id_seq OWNED BY public.participation_scores.id;


--
-- Name: password_reset_tokens; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.password_reset_tokens (
    id integer NOT NULL,
    token_hash text NOT NULL,
    user_id integer,
    student_account_id integer,
    email text NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    expires_at timestamp without time zone NOT NULL,
    used_at timestamp without time zone
);


--
-- Name: password_reset_tokens_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.password_reset_tokens_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: password_reset_tokens_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.password_reset_tokens_id_seq OWNED BY public.password_reset_tokens.id;


--
-- Name: payments_payment_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.payments_payment_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: payments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.payments (
    payment_id integer DEFAULT nextval('public.payments_payment_id_seq'::regclass) NOT NULL,
    bill_id integer NOT NULL,
    enrollment_id integer NOT NULL,
    branch_id integer NOT NULL,
    amount numeric(10,2) NOT NULL,
    payment_method character varying(20) DEFAULT 'cash'::character varying,
    payment_date timestamp without time zone DEFAULT now() NOT NULL,
    receipt_number character varying(50),
    notes text,
    received_by integer NOT NULL,
    year_id integer,
    target_type character varying(50) DEFAULT 'general'::character varying,
    target_id integer
);


--
-- Name: posted_grades; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.posted_grades (
    id integer NOT NULL,
    enrollment_id integer NOT NULL,
    subject_id integer NOT NULL,
    grading_period character varying(10) NOT NULL,
    grade numeric(5,2) NOT NULL,
    posted_by integer,
    posted_at timestamp without time zone DEFAULT now(),
    section_id integer NOT NULL,
    year_id integer
);


--
-- Name: posted_grades_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.posted_grades_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: posted_grades_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.posted_grades_id_seq OWNED BY public.posted_grades.id;


--
-- Name: reservation_items_reservation_item_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.reservation_items_reservation_item_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: reservation_items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.reservation_items (
    reservation_item_id integer DEFAULT nextval('public.reservation_items_reservation_item_id_seq'::regclass) NOT NULL,
    reservation_id integer NOT NULL,
    item_id integer NOT NULL,
    qty integer NOT NULL,
    size_label text,
    unit_price numeric(12,2) DEFAULT 0 NOT NULL,
    line_total numeric(12,2) DEFAULT 0 NOT NULL,
    publisher character varying(255),
    CONSTRAINT reservation_items_qty_check CHECK ((qty > 0))
);


--
-- Name: reservations_reservation_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.reservations_reservation_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: reservations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.reservations (
    reservation_id integer DEFAULT nextval('public.reservations_reservation_id_seq'::regclass) NOT NULL,
    student_user_id integer,
    branch_id integer NOT NULL,
    student_grade_level text,
    status text DEFAULT 'RESERVED'::text NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    paid_at timestamp without time zone,
    claimed_at timestamp without time zone,
    cancelled_at timestamp without time zone,
    reserved_by_user_id integer,
    enrollment_id integer,
    CONSTRAINT reservations_status_check CHECK ((status = ANY (ARRAY['RESERVED'::text, 'PAID'::text, 'CLAIMED'::text, 'CANCELLED'::text])))
);


--
-- Name: schedules; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.schedules (
    schedule_id integer NOT NULL,
    subject_id integer,
    section_id integer,
    teacher_id integer,
    day_of_week character varying(16) NOT NULL,
    start_time time without time zone NOT NULL,
    end_time time without time zone NOT NULL,
    room character varying(32),
    year_id integer,
    branch_id integer,
    is_archived boolean DEFAULT false,
    term_name character varying(50)
);


--
-- Name: schedules_schedule_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.schedules_schedule_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: schedules_schedule_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.schedules_schedule_id_seq OWNED BY public.schedules.schedule_id;


--
-- Name: school_years; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.school_years (
    year_id integer NOT NULL,
    label character varying(9) NOT NULL,
    branch_id integer,
    is_active boolean DEFAULT false NOT NULL
);


--
-- Name: school_years_year_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.school_years_year_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: school_years_year_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.school_years_year_id_seq OWNED BY public.school_years.year_id;


--
-- Name: section_teachers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.section_teachers (
    id integer NOT NULL,
    section_id integer NOT NULL,
    teacher_id integer,
    subject_id integer NOT NULL,
    year_id integer,
    is_archived boolean DEFAULT false,
    term_name character varying(50)
);


--
-- Name: section_teachers_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.section_teachers_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: section_teachers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.section_teachers_id_seq OWNED BY public.section_teachers.id;


--
-- Name: sections_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.sections_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: sections; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sections (
    section_id integer DEFAULT nextval('public.sections_id_seq'::regclass) NOT NULL,
    branch_id integer NOT NULL,
    grade_level character varying(50),
    section_name character varying(100) NOT NULL,
    school_year character varying(20),
    created_at timestamp without time zone DEFAULT now(),
    teacher_id integer,
    grade_level_id integer,
    capacity integer DEFAULT 50 NOT NULL,
    year_id integer
);


--
-- Name: shs_elective_offerings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.shs_elective_offerings (
    offering_id integer NOT NULL,
    branch_id integer NOT NULL,
    year_id integer NOT NULL,
    term_name character varying(50) NOT NULL,
    section_teacher_id integer NOT NULL,
    group_code character varying(50) NOT NULL,
    shs_track character varying(50) DEFAULT 'Academic'::character varying NOT NULL,
    capacity integer DEFAULT 30 NOT NULL,
    status character varying(20) DEFAULT 'ACTIVE'::character varying,
    created_at timestamp without time zone DEFAULT now()
);


--
-- Name: shs_elective_offerings_offering_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.shs_elective_offerings_offering_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: shs_elective_offerings_offering_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.shs_elective_offerings_offering_id_seq OWNED BY public.shs_elective_offerings.offering_id;


--
-- Name: shs_pathways; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.shs_pathways (
    pathway_id integer NOT NULL,
    branch_id integer NOT NULL,
    track_name character varying(100) NOT NULL,
    pathway_name character varying(200) NOT NULL,
    description text,
    is_active boolean DEFAULT true,
    display_order integer DEFAULT 0,
    created_at timestamp without time zone DEFAULT now()
);


--
-- Name: shs_pathways_pathway_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.shs_pathways_pathway_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: shs_pathways_pathway_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.shs_pathways_pathway_id_seq OWNED BY public.shs_pathways.pathway_id;


--
-- Name: shs_selection_periods; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.shs_selection_periods (
    period_id integer NOT NULL,
    branch_id integer NOT NULL,
    year_id integer NOT NULL,
    term_name character varying(50) NOT NULL,
    status character varying(20) DEFAULT 'CLOSED'::character varying,
    opened_at timestamp without time zone,
    closed_at timestamp without time zone
);


--
-- Name: shs_selection_periods_period_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.shs_selection_periods_period_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: shs_selection_periods_period_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.shs_selection_periods_period_id_seq OWNED BY public.shs_selection_periods.period_id;


--
-- Name: shs_student_elective_items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.shs_student_elective_items (
    item_id integer NOT NULL,
    request_id integer NOT NULL,
    offering_id integer NOT NULL
);


--
-- Name: shs_student_elective_items_item_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.shs_student_elective_items_item_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: shs_student_elective_items_item_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.shs_student_elective_items_item_id_seq OWNED BY public.shs_student_elective_items.item_id;


--
-- Name: shs_student_elective_memberships; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.shs_student_elective_memberships (
    membership_id integer NOT NULL,
    enrollment_id integer NOT NULL,
    student_user_id integer,
    offering_id integer NOT NULL,
    term_name character varying(50) NOT NULL,
    year_id integer NOT NULL,
    status character varying(20) DEFAULT 'ACTIVE'::character varying,
    enrolled_at timestamp without time zone DEFAULT now(),
    dropped_at timestamp without time zone
);


--
-- Name: shs_student_elective_memberships_membership_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.shs_student_elective_memberships_membership_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: shs_student_elective_memberships_membership_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.shs_student_elective_memberships_membership_id_seq OWNED BY public.shs_student_elective_memberships.membership_id;


--
-- Name: shs_student_elective_requests; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.shs_student_elective_requests (
    request_id integer NOT NULL,
    enrollment_id integer NOT NULL,
    student_user_id integer,
    branch_id integer NOT NULL,
    year_id integer NOT NULL,
    term_name character varying(50) NOT NULL,
    status character varying(30) DEFAULT 'PENDING'::character varying,
    revision_reason text,
    submitted_at timestamp without time zone DEFAULT now(),
    reviewed_by integer,
    reviewed_at timestamp without time zone
);


--
-- Name: shs_student_elective_requests_request_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.shs_student_elective_requests_request_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: shs_student_elective_requests_request_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.shs_student_elective_requests_request_id_seq OWNED BY public.shs_student_elective_requests.request_id;


--
-- Name: student_accounts_account_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.student_accounts_account_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: student_accounts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.student_accounts (
    account_id integer DEFAULT nextval('public.student_accounts_account_id_seq'::regclass) NOT NULL,
    enrollment_id integer NOT NULL,
    branch_id integer NOT NULL,
    username character varying(100) NOT NULL,
    password character varying(255) NOT NULL,
    email character varying(255),
    is_active boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    require_password_change boolean DEFAULT false,
    last_password_change timestamp without time zone,
    full_name character varying(120),
    gender character varying(16),
    contact_number character varying(32),
    dob date,
    profile_image character varying(255)
);


--
-- Name: student_notifications; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.student_notifications (
    id integer NOT NULL,
    student_id integer NOT NULL,
    title character varying(150) NOT NULL,
    message text NOT NULL,
    link text,
    is_read boolean DEFAULT false,
    created_at timestamp without time zone DEFAULT now(),
    notification_id integer
);


--
-- Name: student_notifications_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.student_notifications_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: student_notifications_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.student_notifications_id_seq OWNED BY public.student_notifications.id;


--
-- Name: subjects; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.subjects (
    subject_id integer NOT NULL,
    name character varying(100) NOT NULL,
    units integer DEFAULT 3,
    deped_category character varying(20) DEFAULT 'language'::character varying,
    subject_type character varying(50) DEFAULT 'CORE'::character varying,
    track character varying(50),
    pathway character varying(100),
    prerequisite_subject_id integer
);


--
-- Name: subjects_subject_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.subjects_subject_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: subjects_subject_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.subjects_subject_id_seq OWNED BY public.subjects.subject_id;


--
-- Name: swafo_discipline_log; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.swafo_discipline_log (
    log_id integer NOT NULL,
    enrollment_id integer,
    student_id integer,
    branch_id integer,
    logged_by integer,
    reported_by integer,
    incident_date date NOT NULL,
    incident_type character varying(100),
    offense_level character varying(50),
    severity character varying(50),
    description text,
    action_taken text,
    status character varying(50) DEFAULT 'Pending'::character varying,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    referred_to_swafo boolean DEFAULT false,
    referral_reason text
);


--
-- Name: swafo_discipline_log_log_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.swafo_discipline_log_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: swafo_discipline_log_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.swafo_discipline_log_log_id_seq OWNED BY public.swafo_discipline_log.log_id;


--
-- Name: swafo_parent_conferences; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.swafo_parent_conferences (
    conference_id integer NOT NULL,
    branch_id integer,
    enrollment_id integer,
    discipline_log_id integer,
    scheduled_by integer,
    title character varying(255) NOT NULL,
    conference_date date NOT NULL,
    conference_time character varying(50),
    meeting_type character varying(50) DEFAULT 'in_person'::character varying,
    meeting_location character varying(255),
    agenda text,
    status character varying(50) DEFAULT 'scheduled'::character varying,
    parent_notes text,
    minutes_of_meeting text,
    agreements text,
    parent_acknowledged_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: swafo_parent_conferences_conference_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.swafo_parent_conferences_conference_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: swafo_parent_conferences_conference_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.swafo_parent_conferences_conference_id_seq OWNED BY public.swafo_parent_conferences.conference_id;


--
-- Name: swafo_records; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.swafo_records (
    record_id integer NOT NULL,
    enrollment_id integer,
    student_id integer,
    family_members jsonb DEFAULT '[]'::jsonb,
    health_info jsonb DEFAULT '{}'::jsonb,
    education_history jsonb DEFAULT '[]'::jsonb,
    summer_subjects jsonb DEFAULT '[]'::jsonb,
    religion_info jsonb DEFAULT '{}'::jsonb,
    vocation_info jsonb DEFAULT '{}'::jsonb,
    general_info jsonb DEFAULT '{}'::jsonb,
    status character varying(50) DEFAULT 'Draft'::character varying,
    teacher_notes text,
    reviewed_by integer,
    reviewed_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    submitted_at timestamp without time zone
);


--
-- Name: swafo_records_record_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.swafo_records_record_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: swafo_records_record_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.swafo_records_record_id_seq OWNED BY public.swafo_records.record_id;


--
-- Name: system_settings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.system_settings (
    setting_key character varying(100) NOT NULL,
    setting_value text,
    updated_at timestamp without time zone DEFAULT now()
);


--
-- Name: teacher_announcements; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.teacher_announcements (
    announcement_id integer NOT NULL,
    teacher_user_id integer NOT NULL,
    branch_id integer NOT NULL,
    grade_level character varying(50) NOT NULL,
    title character varying(200) NOT NULL,
    body text,
    created_at timestamp without time zone DEFAULT now(),
    year_id integer NOT NULL
);


--
-- Name: teacher_announcements_announcement_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.teacher_announcements_announcement_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: teacher_announcements_announcement_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.teacher_announcements_announcement_id_seq OWNED BY public.teacher_announcements.announcement_id;


--
-- Name: teacher_grade_levels; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.teacher_grade_levels (
    id integer NOT NULL,
    teacher_id integer NOT NULL,
    grade_level_id integer NOT NULL
);


--
-- Name: teacher_grade_levels_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.teacher_grade_levels_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: teacher_grade_levels_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.teacher_grade_levels_id_seq OWNED BY public.teacher_grade_levels.id;


--
-- Name: teacher_section_assignments_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.teacher_section_assignments_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: uniform_order_items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.uniform_order_items (
    item_id integer NOT NULL,
    order_id integer NOT NULL,
    inventory_item_id integer,
    item_name character varying(255) NOT NULL,
    size_label character varying(50),
    unit_price numeric(10,2) DEFAULT 0.00 NOT NULL,
    quantity integer DEFAULT 1 NOT NULL,
    line_total numeric(10,2) DEFAULT 0.00 NOT NULL,
    created_at timestamp without time zone DEFAULT now()
);


--
-- Name: uniform_order_items_item_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.uniform_order_items_item_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: uniform_order_items_item_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.uniform_order_items_item_id_seq OWNED BY public.uniform_order_items.item_id;


--
-- Name: uniform_orders; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.uniform_orders (
    order_id integer NOT NULL,
    order_number character varying(50) NOT NULL,
    enrollment_id integer NOT NULL,
    student_user_id integer,
    branch_id integer NOT NULL,
    year_id integer,
    total_amount numeric(10,2) DEFAULT 0.00 NOT NULL,
    payment_status character varying(20) DEFAULT 'Unpaid'::character varying,
    order_status character varying(30) DEFAULT 'For Ordering'::character varying,
    created_by_user_id integer,
    bill_id integer,
    created_at timestamp without time zone DEFAULT now(),
    onsite_arrived_at timestamp without time zone,
    claimed_at timestamp without time zone,
    claimed_by_user_id integer,
    updated_at timestamp without time zone DEFAULT now()
);


--
-- Name: uniform_orders_order_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.uniform_orders_order_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: uniform_orders_order_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.uniform_orders_order_id_seq OWNED BY public.uniform_orders.order_id;


--
-- Name: users_user_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.users_user_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    user_id integer DEFAULT nextval('public.users_user_id_seq'::regclass) NOT NULL,
    branch_id integer,
    username character varying(50) NOT NULL,
    password character varying(255) NOT NULL,
    role character varying(20),
    status character varying(10) DEFAULT 'active'::character varying,
    require_password_change boolean DEFAULT false,
    last_password_change timestamp without time zone,
    full_name character varying(150),
    gender character varying(20),
    grade_level character varying(50),
    email character varying(255),
    grade_level_id integer,
    enrollment_id integer,
    contact_number character varying(32),
    dob date,
    profile_image character varying(255),
    last_login timestamp without time zone,
    teacher_type character varying(20) DEFAULT 'advisory'::character varying,
    specialization_subject character varying(100),
    department character varying(50),
    is_archived boolean DEFAULT false,
    first_name character varying(255),
    middle_name character varying(255),
    last_name character varying(255),
    is_swafo boolean DEFAULT false,
    user_roles text,
    is_dc boolean DEFAULT false
);


--
-- Name: activities activity_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.activities ALTER COLUMN activity_id SET DEFAULT nextval('public.activities_activity_id_seq'::regclass);


--
-- Name: activity_grades grade_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.activity_grades ALTER COLUMN grade_id SET DEFAULT nextval('public.activity_grades_grade_id_seq'::regclass);


--
-- Name: activity_submissions submission_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.activity_submissions ALTER COLUMN submission_id SET DEFAULT nextval('public.activity_submissions_submission_id_seq'::regclass);


--
-- Name: attendance_scores id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.attendance_scores ALTER COLUMN id SET DEFAULT nextval('public.attendance_scores_id_seq'::regclass);


--
-- Name: audit_logs log_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs ALTER COLUMN log_id SET DEFAULT nextval('public.audit_logs_log_id_seq'::regclass);


--
-- Name: book_release_items release_item_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.book_release_items ALTER COLUMN release_item_id SET DEFAULT nextval('public.book_release_items_release_item_id_seq'::regclass);


--
-- Name: book_releases release_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.book_releases ALTER COLUMN release_id SET DEFAULT nextval('public.book_releases_release_id_seq'::regclass);


--
-- Name: daily_attendance id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.daily_attendance ALTER COLUMN id SET DEFAULT nextval('public.daily_attendance_id_seq'::regclass);


--
-- Name: daily_participation id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.daily_participation ALTER COLUMN id SET DEFAULT nextval('public.daily_participation_id_seq'::regclass);


--
-- Name: enrollment_history id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.enrollment_history ALTER COLUMN id SET DEFAULT nextval('public.enrollment_history_id_seq'::regclass);


--
-- Name: exam_answers answer_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.exam_answers ALTER COLUMN answer_id SET DEFAULT nextval('public.exam_answers_answer_id_seq'::regclass);


--
-- Name: exam_questions question_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.exam_questions ALTER COLUMN question_id SET DEFAULT nextval('public.exam_questions_question_id_seq'::regclass);


--
-- Name: exam_results result_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.exam_results ALTER COLUMN result_id SET DEFAULT nextval('public.exam_results_result_id_seq'::regclass);


--
-- Name: exam_student_permissions permission_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.exam_student_permissions ALTER COLUMN permission_id SET DEFAULT nextval('public.exam_student_permissions_permission_id_seq'::regclass);


--
-- Name: exam_tab_switches id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.exam_tab_switches ALTER COLUMN id SET DEFAULT nextval('public.exam_tab_switches_id_seq'::regclass);


--
-- Name: exams exam_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.exams ALTER COLUMN exam_id SET DEFAULT nextval('public.exams_exam_id_seq'::regclass);


--
-- Name: failed_logins id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.failed_logins ALTER COLUMN id SET DEFAULT nextval('public.failed_logins_id_seq'::regclass);


--
-- Name: finalized_grades id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.finalized_grades ALTER COLUMN id SET DEFAULT nextval('public.finalized_grades_id_seq'::regclass);


--
-- Name: grade_overrides id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.grade_overrides ALTER COLUMN id SET DEFAULT nextval('public.grade_overrides_id_seq'::regclass);


--
-- Name: grade_submission_requests id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.grade_submission_requests ALTER COLUMN id SET DEFAULT nextval('public.grade_submission_requests_id_seq'::regclass);


--
-- Name: grading_period_ranges id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.grading_period_ranges ALTER COLUMN id SET DEFAULT nextval('public.grading_period_ranges_id_seq'::regclass);


--
-- Name: grading_weights id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.grading_weights ALTER COLUMN id SET DEFAULT nextval('public.grading_weights_id_seq'::regclass);


--
-- Name: holidays id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.holidays ALTER COLUMN id SET DEFAULT nextval('public.holidays_id_seq'::regclass);


--
-- Name: individual_extensions extension_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.individual_extensions ALTER COLUMN extension_id SET DEFAULT nextval('public.individual_extensions_extension_id_seq'::regclass);


--
-- Name: login_2fa_tokens token_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.login_2fa_tokens ALTER COLUMN token_id SET DEFAULT nextval('public.login_2fa_tokens_token_id_seq'::regclass);


--
-- Name: parent_notifications notif_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parent_notifications ALTER COLUMN notif_id SET DEFAULT nextval('public.parent_notifications_notif_id_seq'::regclass);


--
-- Name: participation_scores id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.participation_scores ALTER COLUMN id SET DEFAULT nextval('public.participation_scores_id_seq'::regclass);


--
-- Name: password_reset_tokens id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.password_reset_tokens ALTER COLUMN id SET DEFAULT nextval('public.password_reset_tokens_id_seq'::regclass);


--
-- Name: posted_grades id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.posted_grades ALTER COLUMN id SET DEFAULT nextval('public.posted_grades_id_seq'::regclass);


--
-- Name: schedules schedule_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schedules ALTER COLUMN schedule_id SET DEFAULT nextval('public.schedules_schedule_id_seq'::regclass);


--
-- Name: school_years year_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.school_years ALTER COLUMN year_id SET DEFAULT nextval('public.school_years_year_id_seq'::regclass);


--
-- Name: section_teachers id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.section_teachers ALTER COLUMN id SET DEFAULT nextval('public.section_teachers_id_seq'::regclass);


--
-- Name: shs_elective_offerings offering_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shs_elective_offerings ALTER COLUMN offering_id SET DEFAULT nextval('public.shs_elective_offerings_offering_id_seq'::regclass);


--
-- Name: shs_pathways pathway_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shs_pathways ALTER COLUMN pathway_id SET DEFAULT nextval('public.shs_pathways_pathway_id_seq'::regclass);


--
-- Name: shs_selection_periods period_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shs_selection_periods ALTER COLUMN period_id SET DEFAULT nextval('public.shs_selection_periods_period_id_seq'::regclass);


--
-- Name: shs_student_elective_items item_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shs_student_elective_items ALTER COLUMN item_id SET DEFAULT nextval('public.shs_student_elective_items_item_id_seq'::regclass);


--
-- Name: shs_student_elective_memberships membership_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shs_student_elective_memberships ALTER COLUMN membership_id SET DEFAULT nextval('public.shs_student_elective_memberships_membership_id_seq'::regclass);


--
-- Name: shs_student_elective_requests request_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shs_student_elective_requests ALTER COLUMN request_id SET DEFAULT nextval('public.shs_student_elective_requests_request_id_seq'::regclass);


--
-- Name: student_notifications id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_notifications ALTER COLUMN id SET DEFAULT nextval('public.student_notifications_id_seq'::regclass);


--
-- Name: subjects subject_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subjects ALTER COLUMN subject_id SET DEFAULT nextval('public.subjects_subject_id_seq'::regclass);


--
-- Name: swafo_discipline_log log_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.swafo_discipline_log ALTER COLUMN log_id SET DEFAULT nextval('public.swafo_discipline_log_log_id_seq'::regclass);


--
-- Name: swafo_parent_conferences conference_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.swafo_parent_conferences ALTER COLUMN conference_id SET DEFAULT nextval('public.swafo_parent_conferences_conference_id_seq'::regclass);


--
-- Name: swafo_records record_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.swafo_records ALTER COLUMN record_id SET DEFAULT nextval('public.swafo_records_record_id_seq'::regclass);


--
-- Name: teacher_announcements announcement_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teacher_announcements ALTER COLUMN announcement_id SET DEFAULT nextval('public.teacher_announcements_announcement_id_seq'::regclass);


--
-- Name: teacher_grade_levels id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teacher_grade_levels ALTER COLUMN id SET DEFAULT nextval('public.teacher_grade_levels_id_seq'::regclass);


--
-- Name: uniform_order_items item_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.uniform_order_items ALTER COLUMN item_id SET DEFAULT nextval('public.uniform_order_items_item_id_seq'::regclass);


--
-- Name: uniform_orders order_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.uniform_orders ALTER COLUMN order_id SET DEFAULT nextval('public.uniform_orders_order_id_seq'::regclass);


--
-- Data for Name: activities; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.activities (activity_id, branch_id, section_id, subject_id, teacher_id, title, category, instructions, max_score, due_date, allow_resubmission, allowed_file_types, attachment_path, status, created_at, updated_at, grading_period, batch_id, year_id, is_archived) FROM stdin;
26	10	138	156	114	Activity 5	\N	\N	100	\N	t	\N	\N	Draft	2026-09-29 11:31:53.789707	2026-09-29 11:31:53.789707	2nd	\N	30	f
27	10	138	156	114	Activity 1	\N	\N	100	\N	t	\N	\N	Draft	2026-10-01 02:37:57.194345	2026-10-01 02:37:57.194345	1st	\N	30	f
21	4	84	22	86	Activity 1	Assignment	send ka file	100	2026-08-20 19:37:00	t		\N	Published	2026-08-19 11:38:12.331651	2026-08-19 11:38:12.331651	1st	a61db5f0	10	f
20	4	84	22	86	Exhibit	Assignment	Pass only	100	2026-08-27 00:00:00	t		\N	Published	2026-08-19 07:29:48.096671	2026-08-27 04:09:05.279721	1st	ce0c8899	10	f
22	10	138	156	114	Act 1	Assignment	Submit	100	2026-09-23 15:23:00	t		\N	Published	2026-09-22 07:23:51.855172	2026-09-22 07:23:51.855172	2nd	3eb9dd6e	30	f
23	10	138	156	114	Act 2	Assignment	Act 3	100	2026-09-23 15:57:00	t		\N	Published	2026-09-22 07:57:17.77706	2026-09-22 07:57:17.77706	2nd	41f379ac	30	f
24	10	138	156	114	Activity 3	\N	\N	100	\N	t	\N	\N	Draft	2026-09-22 07:58:52.484408	2026-09-22 07:58:52.484408	2nd	\N	30	f
25	10	138	156	114	Act 3	Assignment		100	2026-09-29 19:28:00	t		\N	Published	2026-09-29 11:28:38.502826	2026-09-29 11:28:38.502826	2nd	61218c91	30	f
\.


--
-- Data for Name: activity_grades; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.activity_grades (grade_id, submission_id, activity_id, student_id, raw_score, max_score, percentage, remarks, created_at, updated_at) FROM stdin;
9	11	21	127	100.00	100	100.00		2026-08-19 11:43:18.785111	2026-08-19 11:43:18.785111
10	12	21	107	100.00	100	100.00		2026-08-27 04:47:11.433416	2026-08-27 04:47:11.433416
13	15	26	\N	100.00	100	100.00	\N	2026-09-29 11:32:11.778891	2026-09-29 11:32:11.778891
11	13	22	149	100.00	100	100.00		2026-09-22 07:57:51.799666	2026-09-29 11:32:11.778891
14	16	26	\N	99.00	100	99.00	\N	2026-09-29 11:32:11.778891	2026-09-29 11:32:11.778891
15	17	27	\N	70.00	100	70.00	\N	2026-10-01 02:38:12.430615	2026-10-01 02:38:12.430615
16	18	27	\N	90.00	100	90.00	\N	2026-10-01 02:38:12.430615	2026-10-01 02:38:12.430615
17	19	27	\N	99.00	100	99.00	\N	2026-10-01 02:38:12.430615	2026-10-01 02:38:12.430615
\.


--
-- Data for Name: activity_submissions; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.activity_submissions (submission_id, activity_id, student_id, enrollment_id, file_path, original_filename, submitted_at, is_late, attempt_no, is_active, allow_resubmit, status, feedback, graded_at, graded_by, year_id, attachments, is_viewed) FROM stdin;
11	21	127	140	https://res.cloudinary.com/diwiuseil/image/upload/v1787139774/liceo_submissions/Bible-Verse-Wallpaper_ead1e0.jpg	Bible-Verse-Wallpaper.jpg	2026-08-19 19:42:55.213532	f	1	t	f	Graded	\N	2026-08-19 11:43:18.785111	86	\N	[{"name": "Bible-Verse-Wallpaper.jpg", "path": "https://res.cloudinary.com/diwiuseil/image/upload/v1787139774/liceo_submissions/Bible-Verse-Wallpaper_ead1e0.jpg", "type": "jpg"}]	f
12	21	107	134	https://res.cloudinary.com/diwiuseil/image/upload/v1787805998/liceo_submissions/IMG_0052_584586.png	IMG_0052.png	2026-08-27 12:46:38.966845	f	1	t	f	Graded	\N	2026-08-27 04:47:11.433416	86	\N	[{"name": "IMG_0052.png", "path": "https://res.cloudinary.com/diwiuseil/image/upload/v1787805998/liceo_submissions/IMG_0052_584586.png", "type": "png"}]	f
13	22	149	489	https://res.cloudinary.com/diwiuseil/image/upload/v1790061862/liceo_submissions/survey_lms_09957f.jpg	survey_lms.jpg	2026-09-22 15:24:23.343311	f	1	t	f	Graded	\N	2026-09-22 07:57:51.799666	114	\N	[{"name": "survey_lms.jpg", "path": "https://res.cloudinary.com/diwiuseil/image/upload/v1790061862/liceo_submissions/survey_lms_09957f.jpg", "type": "jpg"}]	f
14	24	149	489	\N	\N	2026-09-22 07:59:03.363244	f	1	t	t	Submitted	\N	\N	\N	\N	\N	f
15	26	\N	491	\N	\N	2026-09-29 11:32:11.778891	f	1	t	f	submitted	\N	\N	\N	\N	\N	f
16	26	149	489	\N	\N	2026-09-29 11:32:11.778891	f	1	t	f	submitted	\N	\N	\N	\N	\N	f
17	27	\N	491	\N	\N	2026-10-01 02:38:12.430615	f	1	t	f	submitted	\N	\N	\N	\N	\N	f
18	27	148	490	\N	\N	2026-10-01 02:38:12.430615	f	1	t	f	submitted	\N	\N	\N	\N	\N	f
19	27	149	489	\N	\N	2026-10-01 02:38:12.430615	f	1	t	f	submitted	\N	\N	\N	\N	\N	f
\.


--
-- Data for Name: announcements; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.announcements (announcement_id, title, message, is_active, created_at, image_url, branch_id, audience) FROM stdin;
\.


--
-- Data for Name: attendance_scores; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.attendance_scores (id, enrollment_id, section_id, subject_id, grading_period, score, updated_at, teacher_id, year_id, total_days) FROM stdin;
7	491	138	156	1st	9.00	2026-10-01 02:38:12.430615	114	\N	10
8	490	138	156	1st	9.00	2026-10-01 02:38:12.430615	114	\N	10
9	489	138	156	1st	8.00	2026-10-01 02:38:12.430615	114	\N	10
\.


--
-- Data for Name: audit_logs; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.audit_logs (log_id, user_id, user_name, role, branch_id, action, details, ip_address, created_at) FROM stdin;
2	65	System Administrator	super_admin	\N	USER_LOGIN	Successful login from IP 100.64.0.13	100.64.0.13	2026-09-07 02:01:26.791089
3	65	System Administrator	super_admin	\N	USER_LOGIN	Successful login from IP 100.64.0.8	100.64.0.8	2026-09-07 02:08:41.776338
4	65	System Administrator	super_admin	\N	DATABASE_BACKUP	Exported database SQL backup (124959 bytes)	100.64.0.5	2026-09-07 02:10:58.070069
7	\N	LDMAJ_Admin_2	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_Admin_2' from IP 100.64.0.6	100.64.0.6	2026-09-07 02:22:37.591845
8	\N	LDMAJ_Admin	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_Admin' from IP 100.64.0.7	100.64.0.7	2026-09-07 02:22:46.382888
10	\N	LDMAJ_Admin_2	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_Admin_2' from IP 100.64.0.6	100.64.0.6	2026-09-07 02:29:01.508402
11	\N	LDMAJ_Admin_2	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_Admin_2' from IP 100.64.0.6	100.64.0.6	2026-09-07 02:29:05.749404
12	\N	LDMAJ_Admin_2	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_Admin_2' from IP 100.64.0.6	100.64.0.6	2026-09-07 02:29:07.586287
13	\N	LDMAJ_Librarian	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_Librarian' from IP 100.64.0.6	100.64.0.6	2026-09-07 02:30:02.471485
14	\N	LDMAJ_Librarian	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_Librarian' from IP 100.64.0.11	100.64.0.11	2026-09-07 02:30:09.571705
15	65	System Administrator	super_admin	\N	USER_LOGIN	Successful login from IP 100.64.0.10	100.64.0.10	2026-09-07 02:30:18.782124
16	65	System Administrator	super_admin	\N	MAINTENANCE_TOGGLE	Maintenance mode changed to 'ON' by Super Admin	100.64.0.9	2026-09-07 02:30:52.619342
17	65	System Administrator	super_admin	\N	MAINTENANCE_TOGGLE	Maintenance mode changed to 'OFF' by Super Admin	100.64.0.10	2026-09-07 02:31:40.663465
18	138	Jocelyn Villaraza Ramirez	branch_admin	1	USER_LOGIN	Successful login from IP 100.64.0.11	100.64.0.11	2026-09-07 02:38:33.666755
19	\N	LDMAJ_Admin	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_Admin' from IP 100.64.0.9	100.64.0.9	2026-09-07 02:39:03.362837
20	\N	LDMAJ_Admin	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_Admin' from IP 100.64.0.6	100.64.0.6	2026-09-07 02:39:15.22601
21	\N	superadmin	guest	\N	FAILED_LOGIN	Failed login attempt for username 'superadmin' from IP 100.64.0.9	100.64.0.9	2026-09-07 02:39:17.382222
22	\N	LDMAJ_Admin	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_Admin' from IP 100.64.0.10	100.64.0.10	2026-09-07 02:39:21.944163
23	\N	LDMAJ_Admin	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_Admin' from IP 100.64.0.10	100.64.0.10	2026-09-07 02:39:58.806975
24	138	Jocelyn Villaraza Ramirez	branch_admin	1	USER_LOGIN	Successful login from IP 100.64.0.9	100.64.0.9	2026-09-07 02:42:20.970803
25	138	Jocelyn Villaraza Ramirez	branch_admin	1	USER_LOGIN	Successful login from IP 100.64.0.12	100.64.0.12	2026-09-07 02:43:10.717292
26	139	Maricis Modina	registrar	1	USER_LOGIN	Successful login from IP 100.64.0.7	100.64.0.7	2026-09-07 02:45:45.578893
27	139	Maricis Modina	registrar	1	USER_LOGIN	Successful login from IP 100.64.0.17	100.64.0.17	2026-09-07 02:46:28.95037
28	\N	superadmin	guest	\N	FAILED_LOGIN	Failed login attempt for username 'superadmin' from IP 100.64.0.9	100.64.0.9	2026-09-07 02:48:42.320246
29	\N	superadmin	guest	\N	FAILED_LOGIN	Failed login attempt for username 'superadmin' from IP 100.64.0.15	100.64.0.15	2026-09-07 02:48:57.638259
30	65	System Administrator	super_admin	\N	USER_LOGIN	Successful login from IP 100.64.0.3	100.64.0.3	2026-09-07 02:49:09.865531
31	\N	LDMAJ_Registrar	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_Registrar' from IP 100.64.0.7	100.64.0.7	2026-09-07 02:49:51.028924
32	138	Jocelyn Villaraza Ramirez	branch_admin	1	USER_LOGIN	Successful login from IP 100.64.0.11	100.64.0.11	2026-09-07 02:50:36.531813
33	139	Maricis Modina	registrar	1	USER_LOGIN	Successful login from IP 100.64.0.10	100.64.0.10	2026-09-07 03:19:36.31087
34	\N	LDMAJ_Registrar	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_Registrar' from IP 100.64.0.15	100.64.0.15	2026-09-07 03:21:30.952548
35	\N	LDMAJ_Registrar	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_Registrar' from IP 100.64.0.18	100.64.0.18	2026-09-07 03:21:49.033109
36	139	Maricis Modina	registrar	1	USER_LOGIN	Successful login from IP 100.64.0.16	100.64.0.16	2026-09-07 03:21:55.716415
37	138	Jocelyn Villaraza Ramirez	branch_admin	1	USER_LOGIN	Successful login from IP 100.64.0.8	100.64.0.8	2026-09-07 04:04:03.750596
38	97	Chelsie Cada	branch_admin	4	USER_LOGIN	Successful login from IP 100.64.0.15	100.64.0.15	2026-09-07 06:11:42.622775
39	86	Joy Cruz	teacher	4	USER_LOGIN	Successful login from IP 100.64.0.10	100.64.0.10	2026-09-07 06:11:59.031057
40	107	LDPSJ_0001	student	4	USER_LOGIN	Successful login from IP 100.64.0.10	100.64.0.10	2026-09-07 06:12:10.505339
41	83	Mateo De Leon	registrar	4	USER_LOGIN	Successful login from IP 100.64.0.5	100.64.0.5	2026-09-07 06:12:25.919792
42	84	Severin Maria Clarke	cashier	4	USER_LOGIN	Successful login from IP 100.64.0.19	100.64.0.19	2026-09-07 06:12:58.999874
43	106	LDPSJ_Parent1	parent	4	USER_LOGIN	Successful login from IP 100.64.0.4	100.64.0.4	2026-09-07 06:13:47.495905
44	85	Maria Lee	librarian	4	USER_LOGIN	Successful login from IP 100.64.0.5	100.64.0.5	2026-09-07 06:14:16.329071
45	139	Maricis Modina	registrar	1	USER_LOGIN	Successful login from IP 100.64.0.19	100.64.0.19	2026-09-07 06:21:55.191803
46	65	System Administrator	super_admin	\N	USER_LOGIN	Successful login from IP 100.64.0.8	100.64.0.8	2026-09-07 06:37:14.162846
47	\N	LDPSJ_Amin_2	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDPSJ_Amin_2' from IP 100.64.0.16	100.64.0.16	2026-09-07 06:45:56.575284
48	\N	LDPSJ_Amin_2	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDPSJ_Amin_2' from IP 100.64.0.17	100.64.0.17	2026-09-07 06:46:22.452983
49	138	Jocelyn Villaraza Ramirez	branch_admin	1	USER_LOGIN	Successful login from IP 100.64.0.2	100.64.0.2	2026-09-07 06:46:39.458673
50	83	Mateo De Leon	registrar	4	USER_LOGIN	Successful login from IP 100.64.0.13	100.64.0.13	2026-09-07 13:29:40.839349
51	86	Joy Cruz	teacher	4	USER_LOGIN	Successful login from IP 100.64.0.20	100.64.0.20	2026-09-07 13:41:40.646566
52	107	LDPSJ_0001	student	4	USER_LOGIN	Successful login from IP 100.64.0.13	100.64.0.13	2026-09-07 13:47:41.098408
53	106	LDPSJ_Parent1	parent	4	USER_LOGIN	Successful login from IP 100.64.0.10	100.64.0.10	2026-09-07 13:53:17.300046
54	84	Severin Maria Clarke	cashier	4	USER_LOGIN	Successful login from IP 100.64.0.22	100.64.0.22	2026-09-07 13:58:29.210889
55	85	Maria Lee	librarian	4	USER_LOGIN	Successful login from IP 100.64.0.11	100.64.0.11	2026-09-07 14:06:48.452881
56	138	Jocelyn Villaraza Ramirez	branch_admin	1	USER_LOGIN	Successful login from IP 100.64.0.12	100.64.0.12	2026-09-08 03:40:20.48391
57	139	Maricis Modina	registrar	1	USER_LOGIN	Successful login from IP 100.64.0.16	100.64.0.16	2026-09-08 04:02:38.691995
58	138	Jocelyn Villaraza Ramirez	branch_admin	1	USER_LOGIN	Successful login from IP 100.64.0.20	100.64.0.20	2026-09-08 06:08:39.074821
59	139	Maricis Modina	registrar	1	USER_LOGIN	Successful login from IP 100.64.0.21	100.64.0.21	2026-09-08 07:16:18.507428
60	139	Maricis Modina	registrar	1	USER_LOGIN	Successful login from IP 100.64.0.5	100.64.0.5	2026-09-08 08:33:14.176436
61	\N	superadmin	guest	\N	FAILED_LOGIN	Failed login attempt for username 'superadmin' from IP 100.64.0.17	100.64.0.17	2026-09-08 15:05:52.907161
62	\N	superadmin	guest	\N	FAILED_LOGIN	Failed login attempt for username 'superadmin' from IP 100.64.0.21	100.64.0.21	2026-09-08 15:32:45.824802
63	\N	superadmin	guest	\N	FAILED_LOGIN	Failed login attempt for username 'superadmin' from IP 100.64.0.12	100.64.0.12	2026-09-08 15:32:53.385849
64	\N	superadmin	guest	\N	FAILED_LOGIN	Failed login attempt for username 'superadmin' from IP 100.64.0.21	100.64.0.21	2026-09-08 15:33:48.587593
65	\N	superadmin	guest	\N	FAILED_LOGIN	Failed login attempt for username 'superadmin' from IP 100.64.0.12	100.64.0.12	2026-09-08 15:34:02.369848
66	139	Maricis Modina	registrar	1	USER_LOGIN	Successful login from IP 100.64.0.4	100.64.0.4	2026-09-09 14:08:12.185128
67	139	Maricis Modina	registrar	1	USER_LOGIN	Successful login from IP 100.64.0.17	100.64.0.17	2026-09-10 02:42:37.819163
68	\N	LDMAJ_Registrar	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_Registrar' from IP 100.64.0.20	100.64.0.20	2026-09-10 03:50:50.914144
69	139	Maricis Modina	registrar	1	USER_LOGIN	Successful login from IP 100.64.0.14	100.64.0.14	2026-09-10 03:51:05.030856
70	\N	superadmin	guest	\N	FAILED_LOGIN	Failed login attempt for username 'superadmin' from IP 100.64.0.10	100.64.0.10	2026-09-10 04:04:21.203002
71	\N	superadmin	guest	\N	FAILED_LOGIN	Failed login attempt for username 'superadmin' from IP 100.64.0.5	100.64.0.5	2026-09-10 04:04:28.179291
72	\N	superadmin	guest	\N	FAILED_LOGIN	Failed login attempt for username 'superadmin' from IP 100.64.0.20	100.64.0.20	2026-09-10 04:04:37.437183
73	\N	superadmin	guest	\N	FAILED_LOGIN	Failed login attempt for username 'superadmin' from IP 100.64.0.10	100.64.0.10	2026-09-10 04:04:43.302495
74	\N	superadmin	guest	\N	FAILED_LOGIN	Failed login attempt for username 'superadmin' from IP 100.64.0.8	100.64.0.8	2026-09-10 04:04:53.462217
75	\N	superadmin	guest	\N	FAILED_LOGIN	Failed login attempt for username 'superadmin' from IP 100.64.0.21	100.64.0.21	2026-09-10 04:12:52.265597
76	\N	superadmin	guest	\N	FAILED_LOGIN	Failed login attempt for username 'superadmin' from IP 100.64.0.16	100.64.0.16	2026-09-10 04:13:04.051894
77	\N	superadmin	guest	\N	FAILED_LOGIN	Failed login attempt for username 'superadmin' from IP 100.64.0.19	100.64.0.19	2026-09-10 04:15:07.493918
78	\N	superadmin	guest	\N	FAILED_LOGIN	Failed login attempt for username 'superadmin' from IP 100.64.0.20	100.64.0.20	2026-09-10 04:15:21.292192
79	65	System Administrator	super_admin	\N	USER_LOGIN	Successful login from IP 100.64.0.16	100.64.0.16	2026-09-10 04:16:16.253276
80	65	System Administrator	super_admin	\N	DATABASE_BACKUP	Exported database SQL backup (511050 bytes)	100.64.0.13	2026-09-10 04:16:40.585421
81	\N	superadmin	guest	\N	FAILED_LOGIN	Failed login attempt for username 'superadmin' from IP 100.64.0.20	100.64.0.20	2026-09-10 04:19:13.189408
82	65	System Administrator	super_admin	\N	USER_LOGIN	Successful login from IP 100.64.0.10	100.64.0.10	2026-09-10 04:19:22.158386
83	139	Maricis Modina	registrar	1	USER_LOGIN	Successful login from IP 100.64.0.8	100.64.0.8	2026-09-10 09:04:56.789293
84	\N	LDMAJ_Admin	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_Admin' from IP 100.64.0.9	100.64.0.9	2026-09-10 10:21:41.575943
85	138	Jocelyn Villaraza Ramirez	branch_admin	1	USER_LOGIN	Successful login from IP 100.64.0.21	100.64.0.21	2026-09-10 10:21:54.867204
86	\N	LDMAJ_Registrar	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_Registrar' from IP 100.64.0.12	100.64.0.12	2026-09-12 01:26:44.54129
87	\N	LDMAJ_Registrar	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_Registrar' from IP 100.64.0.10	100.64.0.10	2026-09-12 01:27:00.073227
88	139	Maricis Modina	registrar	1	USER_LOGIN	Successful login from IP 100.64.0.4	100.64.0.4	2026-09-12 01:27:27.893181
89	139	Maricis Modina	registrar	1	USER_LOGIN	Successful login from IP 100.64.0.17	100.64.0.17	2026-09-12 01:31:22.256279
90	139	Maricis Modina	registrar	1	USER_LOGIN	Successful login from IP 100.64.0.6	100.64.0.6	2026-09-12 01:43:02.146245
91	138	Jocelyn Villaraza Ramirez	branch_admin	1	USER_LOGIN	Successful login from IP 100.64.0.4	100.64.0.4	2026-09-12 09:55:54.487849
92	139	Maricis Modina	registrar	1	USER_LOGIN	Successful login from IP 100.64.0.16	100.64.0.16	2026-09-12 10:51:17.187708
93	\N	LDMAJ_Admin	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_Admin' from IP 100.64.0.11	100.64.0.11	2026-09-12 11:01:26.488538
94	138	Jocelyn Villaraza Ramirez	branch_admin	1	USER_LOGIN	Successful login from IP 100.64.0.7	100.64.0.7	2026-09-12 11:01:37.087642
95	139	Maricis Modina	registrar	1	USER_LOGIN	Successful login from IP 100.64.0.16	100.64.0.16	2026-09-12 12:23:45.193663
96	\N	LDMAJ_Admin_	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_Admin_' from IP 100.64.0.14	100.64.0.14	2026-09-12 12:34:06.269724
97	138	Jocelyn Villaraza Ramirez	branch_admin	1	USER_LOGIN	Successful login from IP 100.64.0.4	100.64.0.4	2026-09-12 12:34:08.761302
98	138	Jocelyn Villaraza Ramirez	branch_admin	1	USER_LOGIN	Successful login from IP 100.64.0.18	100.64.0.18	2026-09-12 13:56:27.503349
99	138	Jocelyn Villaraza Ramirez	branch_admin	1	USER_LOGIN	Successful login from IP 100.64.0.20	100.64.0.20	2026-09-12 22:18:26.209539
100	\N	LDMAJ_Admin	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_Admin' from IP 100.64.0.8	100.64.0.8	2026-09-13 13:44:29.638084
101	\N	LDMAJ_Admin	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_Admin' from IP 100.64.0.10	100.64.0.10	2026-09-13 13:44:44.118763
102	138	Jocelyn Villaraza Ramirez	branch_admin	1	USER_LOGIN	Successful login from IP 100.64.0.13	100.64.0.13	2026-09-13 13:44:53.982353
103	\N	LDBB_Teacher_6	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDBB_Teacher_6' from IP 100.64.0.14	100.64.0.14	2026-09-13 15:05:10.485176
104	\N	LDBB_Teacher	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDBB_Teacher' from IP 100.64.0.20	100.64.0.20	2026-09-13 15:05:18.411097
105	114	Zoe Anne Lim	teacher	10	USER_LOGIN	Successful login from IP 100.64.0.6	100.64.0.6	2026-09-13 15:05:27.214164
106	109	Joseph Lim Cruz	branch_admin	10	USER_LOGIN	Successful login from IP 100.64.0.6	100.64.0.6	2026-09-13 15:05:41.05816
107	139	Maricis Modina	registrar	1	USER_LOGIN	Successful login from IP 100.64.0.21	100.64.0.21	2026-09-14 01:08:25.138809
108	139	Maricis Modina	registrar	1	USER_LOGIN	Successful login from IP 100.64.0.8	100.64.0.8	2026-09-14 14:09:32.707695
109	86	Joy Cruz	teacher	4	USER_LOGIN	Successful login from IP 100.64.0.4	100.64.0.4	2026-09-15 04:30:14.110846
110	\N	bello.cypress	guest	\N	FAILED_LOGIN	Failed login attempt for username 'bello.cypress' from IP 100.64.0.14	100.64.0.14	2026-09-15 12:37:43.910484
111	\N	Bello.Cypress	guest	\N	FAILED_LOGIN	Failed login attempt for username 'Bello.Cypress' from IP 100.64.0.19	100.64.0.19	2026-09-15 13:10:17.608018
112	\N	cypress.bello	guest	\N	FAILED_LOGIN	Failed login attempt for username 'cypress.bello' from IP 100.64.0.15	100.64.0.15	2026-09-15 13:10:46.066994
113	\N	bello.cypress	guest	\N	FAILED_LOGIN	Failed login attempt for username 'bello.cypress' from IP 100.64.0.15	100.64.0.15	2026-09-15 13:12:40.169689
114	139	Maricis Modina	registrar	1	USER_LOGIN	Successful login from IP 100.64.0.11	100.64.0.11	2026-09-15 14:25:42.946174
115	\N	mabayamban angela	guest	\N	FAILED_LOGIN	Failed login attempt for username 'mabayamban angela' from IP 100.64.0.10	100.64.0.10	2026-09-16 13:48:48.761636
116	\N	angela	guest	\N	FAILED_LOGIN	Failed login attempt for username 'angela' from IP 100.64.0.8	100.64.0.8	2026-09-17 01:35:08.255368
117	86	Joy Cruz	teacher	4	USER_LOGIN	Successful login from IP 100.64.0.9	100.64.0.9	2026-09-17 23:00:38.417148
118	\N	LDPSJ_Teacher_2	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDPSJ_Teacher_2' from IP 100.64.0.9	100.64.0.9	2026-09-17 23:01:28.086944
119	\N	LDPSJ_Teacher_2	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDPSJ_Teacher_2' from IP 100.64.0.11	100.64.0.11	2026-09-17 23:02:14.983773
120	\N	LDPSJ_Teacher_2	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDPSJ_Teacher_2' from IP 100.64.0.11	100.64.0.11	2026-09-17 23:02:19.883489
121	\N	LDPSJ_Teacher_2	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDPSJ_Teacher_2' from IP 100.64.0.20	100.64.0.20	2026-09-17 23:02:24.65555
122	\N	LDPSJ_Teacher_2	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDPSJ_Teacher_2' from IP 100.64.0.9	100.64.0.9	2026-09-17 23:02:31.200919
123	114	Zoe Anne Lim	teacher	10	USER_LOGIN	Successful login from IP 100.64.0.5	100.64.0.5	2026-09-17 23:03:00.433943
124	97	Chelsie Cada	branch_admin	4	USER_LOGIN	Successful login from IP 100.64.0.20	100.64.0.20	2026-09-17 23:04:12.899883
125	\N	LDPSJ_Teacher_2	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDPSJ_Teacher_2' from IP 100.64.0.9	100.64.0.9	2026-09-17 23:05:19.654935
126	\N	LDPSJ_Teacher_2	guest	\N	ACCOUNT_LOCKOUT	Account 'LDPSJ_Teacher_2' locked out for 5 mins after 5 failed login attempts	100.64.0.20	2026-09-17 23:05:33.283711
127	83	Mateo De Leon	registrar	4	USER_LOGIN	Successful login from IP 100.64.0.20	100.64.0.20	2026-09-17 23:06:18.423365
128	\N	LDBB_Teacher	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDBB_Teacher' from IP 100.64.0.21	100.64.0.21	2026-09-17 23:08:03.879095
129	\N	LDBB_Teacher	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDBB_Teacher' from IP 100.64.0.8	100.64.0.8	2026-09-17 23:08:27.396488
130	\N	LDBB_Admin	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDBB_Admin' from IP 100.64.0.21	100.64.0.21	2026-09-17 23:09:10.497031
131	\N	LDPAE_Registrar	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDPAE_Registrar' from IP 100.64.0.7	100.64.0.7	2026-09-17 23:28:08.318812
132	\N	LDBB_Registrar	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDBB_Registrar' from IP 100.64.0.16	100.64.0.16	2026-09-18 02:56:03.741428
133	111	Mary Grace Reyes	registrar	10	USER_LOGIN	Successful login from IP 100.64.0.22	100.64.0.22	2026-09-18 02:56:15.698132
134	\N	LDBB_0014	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDBB_0014' from IP 100.64.0.22	100.64.0.22	2026-09-18 03:00:18.820848
135	140	LDBB_0014	student	10	USER_LOGIN	Successful login from IP 100.64.0.17	100.64.0.17	2026-09-18 03:00:30.678554
136	\N	LDMAJ_Admin	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_Admin' from IP 100.64.0.2	100.64.0.2	2026-09-18 05:16:06.675221
137	138	Jocelyn Villaraza Ramirez	branch_admin	1	USER_LOGIN	Successful login from IP 100.64.0.18	100.64.0.18	2026-09-18 05:16:16.676673
138	\N	LDMAJ_Teacher	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_Teacher' from IP 100.64.0.17	100.64.0.17	2026-09-18 05:18:57.005994
139	\N	LDMAJ_Teacher	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_Teacher' from IP 100.64.0.19	100.64.0.19	2026-09-18 05:19:33.449457
140	141	Rowena Rosel Del Rosario	teacher	1	USER_LOGIN	Successful login from IP 100.64.0.13	100.64.0.13	2026-09-18 05:20:06.542731
141	141	Rowena Rosel Del Rosario	teacher	1	USER_LOGIN	Successful login from IP 100.64.0.21	100.64.0.21	2026-09-18 05:22:09.06196
142	143	Johanne Estela Mari Cobrado	teacher	1	USER_LOGIN	Successful login from IP 100.64.0.10	100.64.0.10	2026-09-18 05:22:27.386005
143	\N	LDMAJ_Teacher_2	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_Teacher_2' from IP 100.64.0.18	100.64.0.18	2026-09-18 05:23:07.699086
144	\N	LDMAJ_Teacher_2	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_Teacher_2' from IP 100.64.0.20	100.64.0.20	2026-09-18 05:23:42.988784
145	143	Johanne Estela Mari Cobrado	teacher	1	USER_LOGIN	Successful login from IP 100.64.0.17	100.64.0.17	2026-09-18 05:23:57.33085
146	\N	LDMAJ_Teacher_2	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_Teacher_2' from IP 100.64.0.18	100.64.0.18	2026-09-18 05:24:02.223013
147	143	Johanne Estela Mari Cobrado	teacher	1	USER_LOGIN	Successful login from IP 100.64.0.16	100.64.0.16	2026-09-18 05:24:59.20211
148	142	Anna Marie Montemor Breganza	teacher	1	USER_LOGIN	Successful login from IP 100.64.0.3	100.64.0.3	2026-09-18 05:25:06.112719
149	142	Anna Marie Montemor Breganza	teacher	1	USER_LOGIN	Successful login from IP 100.64.0.19	100.64.0.19	2026-09-18 05:27:09.295308
150	138	Jocelyn Villaraza Ramirez	branch_admin	1	USER_LOGIN	Successful login from IP 100.64.0.11	100.64.0.11	2026-09-18 16:01:50.159591
151	83	Mateo De Leon	registrar	4	USER_LOGIN	Successful login from IP 100.64.0.2	100.64.0.2	2026-09-20 11:11:23.953232
152	138	Jocelyn Villaraza Ramirez	branch_admin	1	USER_LOGIN	Successful login from IP 100.64.0.9	100.64.0.9	2026-09-20 14:20:13.079754
153	109	Joseph Lim Cruz	branch_admin	10	USER_LOGIN	Successful login from IP 100.64.0.19	100.64.0.19	2026-09-20 14:51:12.432221
154	\N	LDMAJ_Admin	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_Admin' from IP 100.64.0.17	100.64.0.17	2026-09-20 14:57:04.943986
155	138	Jocelyn Villaraza Ramirez	branch_admin	1	USER_LOGIN	Successful login from IP 100.64.0.22	100.64.0.22	2026-09-20 14:57:14.653904
156	139	Maricis Modina	registrar	1	USER_LOGIN	Successful login from IP 100.64.0.9	100.64.0.9	2026-09-20 16:35:26.067522
157	\N	LDMAJ_Admin	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_Admin' from IP 100.64.0.3	100.64.0.3	2026-09-20 16:35:45.165965
158	\N	LDMAJ_Admin	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_Admin' from IP 100.64.0.3	100.64.0.3	2026-09-20 16:35:57.80549
159	146	Nicelyn C. Arsolacia	teacher	1	USER_LOGIN	Successful login from IP 100.64.0.7	100.64.0.7	2026-09-21 07:37:04.015237
160	146	Nicelyn C. Arsolacia	teacher	1	USER_LOGIN	Successful login from IP 100.64.0.9	100.64.0.9	2026-09-21 07:38:17.410179
161	138	Jocelyn Villaraza Ramirez	branch_admin	1	USER_LOGIN	Successful login from IP 100.64.0.7	100.64.0.7	2026-09-21 09:33:16.620222
162	138	Jocelyn Villaraza Ramirez	branch_admin	1	USER_LOGIN	Successful login from IP 100.64.0.9	100.64.0.9	2026-09-21 13:37:44.44678
163	\N	LDMAJ_Teacher	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_Teacher' from IP 100.64.0.4	100.64.0.4	2026-09-21 14:29:57.201711
164	86	Joy Cruz	teacher	4	USER_LOGIN	Successful login from IP 100.64.0.9	100.64.0.9	2026-09-21 14:32:58.702108
165	86	Joy Cruz	teacher	4	USER_LOGIN	Successful login from IP 100.64.0.9	100.64.0.9	2026-09-21 14:33:47.975491
166	\N	LDMAJ_Teacher	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_Teacher' from IP 100.64.0.15	100.64.0.15	2026-09-21 14:36:37.710774
167	86	Joy Cruz	teacher	4	USER_LOGIN	Successful login from IP 100.64.0.9	100.64.0.9	2026-09-21 14:36:40.017562
168	138	Jocelyn Villaraza Ramirez	branch_admin	1	USER_LOGIN	Successful login from IP 100.64.0.2	100.64.0.2	2026-09-22 03:21:23.381315
169	109	Joseph Lim Cruz	branch_admin	10	USER_LOGIN	Successful login from IP 100.64.0.13	100.64.0.13	2026-09-22 03:22:24.741115
170	109	Joseph Lim Cruz	branch_admin	10	USER_LOGIN	Successful login from IP 100.64.0.17	100.64.0.17	2026-09-22 05:02:12.391058
171	\N	LDMAJ_Admin	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_Admin' from IP 100.64.0.4	100.64.0.4	2026-09-22 06:50:16.492098
172	\N	LDMAJ_Admin	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_Admin' from IP 100.64.0.4	100.64.0.4	2026-09-22 06:50:26.69781
173	109	Joseph Lim Cruz	branch_admin	10	USER_LOGIN	Successful login from IP 100.64.0.6	100.64.0.6	2026-09-22 06:50:41.794507
174	\N	LDBB_Registrar	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDBB_Registrar' from IP 100.64.0.2	100.64.0.2	2026-09-22 06:55:28.180467
175	111	Mary Grace Reyes	registrar	10	USER_LOGIN	Successful login from IP 100.64.0.13	100.64.0.13	2026-09-22 06:55:38.219124
176	\N	LiceoLMS	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LiceoLMS' from IP 100.64.0.19	100.64.0.19	2026-09-22 06:56:42.907967
177	65	System Administrator	super_admin	\N	USER_LOGIN	Successful login from IP 100.64.0.17	100.64.0.17	2026-09-22 06:56:54.183086
178	114	Zoe Anne Lim	teacher	10	USER_LOGIN	Successful login from IP 100.64.0.8	100.64.0.8	2026-09-22 07:01:21.833056
179	\N	LDMAJ_0015	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_0015' from IP 100.64.0.19	100.64.0.19	2026-09-22 07:18:24.227181
180	\N	LDMAJ_0015	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_0015' from IP 100.64.0.5	100.64.0.5	2026-09-22 07:18:38.015433
181	\N	LDMAJ_0015	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_0015' from IP 100.64.0.20	100.64.0.20	2026-09-22 07:18:51.958078
182	86	Joy Cruz	teacher	4	USER_LOGIN	Successful login from IP 100.64.0.13	100.64.0.13	2026-09-22 07:47:04.071772
183	65	System Administrator	super_admin	\N	MAINTENANCE_TOGGLE	Maintenance mode changed to 'ON' by Super Admin	100.64.0.21	2026-09-22 07:47:56.163507
184	65	System Administrator	super_admin	\N	MAINTENANCE_TOGGLE	Maintenance mode changed to 'OFF' by Super Admin	100.64.0.17	2026-09-22 07:48:22.680871
185	114	Zoe Anne Lim	teacher	10	USER_LOGIN	Successful login from IP 100.64.0.12	100.64.0.12	2026-09-22 07:55:09.59764
186	131	Mary Santos	cashier	10	USER_LOGIN	Successful login from IP 100.64.0.1	100.64.0.1	2026-09-22 08:05:01.447241
187	113	Jose Luis Mercedes	librarian	10	USER_LOGIN	Successful login from IP 100.64.0.21	100.64.0.21	2026-09-22 08:10:40.990285
188	\N	LDBB_Parent	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDBB_Parent' from IP 100.64.0.11	100.64.0.11	2026-09-22 08:14:00.744713
189	\N	LDBB_Parent	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDBB_Parent' from IP 100.64.0.8	100.64.0.8	2026-09-22 08:14:11.685186
190	106	Brenda Robel Biticon	parent	4	USER_LOGIN	Successful login from IP 100.64.0.20	100.64.0.20	2026-09-22 08:14:56.406347
191	\N	LDBB_Teacher	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDBB_Teacher' from IP 100.64.0.18	100.64.0.18	2026-09-22 08:17:50.772731
192	\N	LDBB_Teacher	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDBB_Teacher' from IP 100.64.0.15	100.64.0.15	2026-09-22 08:17:56.278995
193	114	Zoe Anne Lim	teacher	10	USER_LOGIN	Successful login from IP 100.64.0.1	100.64.0.1	2026-09-22 08:18:02.012754
194	138	Jocelyn Villaraza Ramirez	branch_admin	1	USER_LOGIN	Successful login from IP 100.64.0.20	100.64.0.20	2026-09-22 08:19:24.870675
195	138	Jocelyn Villaraza Ramirez	parent	1	ROLE_SWITCH	User switched active portal role to parent	100.64.0.11	2026-09-22 08:19:46.674124
196	\N	LDMAJ_Admin	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_Admin' from IP 100.64.0.20	100.64.0.20	2026-09-22 08:22:37.546119
197	138	Jocelyn Villaraza Ramirez	branch_admin	1	USER_LOGIN	Successful login from IP 100.64.0.1	100.64.0.1	2026-09-22 08:22:46.249985
198	109	Joseph Lim Cruz	branch_admin	10	USER_LOGIN	Successful login from IP 100.64.0.11	100.64.0.11	2026-09-22 08:23:05.501588
199	\N	LDMAJ_Registrar	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_Registrar' from IP 100.64.0.15	100.64.0.15	2026-09-22 08:28:56.145254
200	139	Maricis Modina	registrar	1	USER_LOGIN	Successful login from IP 100.64.0.10	100.64.0.10	2026-09-22 08:29:04.267843
201	111	Mary Grace Reyes	registrar	10	USER_LOGIN	Successful login from IP 100.64.0.5	100.64.0.5	2026-09-22 08:29:22.189923
202	150	LDMAJ_0337	student	1	USER_LOGIN	Successful login from IP 100.64.0.10	100.64.0.10	2026-09-22 08:32:05.634249
203	151	LDBB_0018	student	10	USER_LOGIN	Successful login from IP 100.64.0.5	100.64.0.5	2026-09-22 08:34:06.876611
204	131	Mary Santos	cashier	10	USER_LOGIN	Successful login from IP 100.64.0.17	100.64.0.17	2026-09-22 08:36:27.182712
205	\N	LDBB_Parent	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDBB_Parent' from IP 100.64.0.7	100.64.0.7	2026-09-22 08:40:30.466637
206	106	Brenda Robel Biticon	parent	4	USER_LOGIN	Successful login from IP 100.64.0.7	100.64.0.7	2026-09-22 08:40:41.475349
207	109	Joseph Lim Cruz	branch_admin	10	USER_LOGIN	Successful login from IP 100.64.0.10	100.64.0.10	2026-09-22 08:44:39.563061
208	114	Zoe Anne Lim	teacher	10	USER_LOGIN	Successful login from IP 100.64.0.18	100.64.0.18	2026-09-22 08:46:40.004194
209	131	Mary Santos	cashier	10	USER_LOGIN	Successful login from IP 100.64.0.10	100.64.0.10	2026-09-22 08:48:05.424087
210	\N	LDBB_0337	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDBB_0337' from IP 100.64.0.11	100.64.0.11	2026-09-22 10:54:45.78026
211	\N	LDBB_0337	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDBB_0337' from IP 100.64.0.3	100.64.0.3	2026-09-22 10:54:59.165567
212	139	Maricis Modina	registrar	1	USER_LOGIN	Successful login from IP 100.64.0.11	100.64.0.11	2026-09-22 10:57:57.466335
213	139	Maricis Modina	parent	1	ROLE_SWITCH	User switched active portal role to parent	100.64.0.4	2026-09-22 10:58:01.62812
214	139	Brenda Robel Biticon	registrar	1	ROLE_SWITCH	User switched active portal role to registrar	100.64.0.14	2026-09-22 10:58:13.379998
215	65	System Administrator	super_admin	\N	USER_LOGIN	Successful login from IP 100.64.0.12	100.64.0.12	2026-09-22 11:00:45.692938
216	139	Brenda Robel Biticon	parent	1	ROLE_SWITCH	User switched active portal role to parent	100.64.0.19	2026-09-22 11:09:40.331945
217	139	Brenda Robel Biticon	registrar	1	ROLE_SWITCH	User switched active portal role to registrar	100.64.0.14	2026-09-22 11:09:44.827995
218	139	Brenda Robel Biticon	parent	1	ROLE_SWITCH	User switched active portal role to parent	100.64.0.19	2026-09-22 11:10:26.97317
219	139	Brenda Robel Biticon	registrar	1	ROLE_SWITCH	User switched active portal role to registrar	100.64.0.7	2026-09-22 11:10:34.411855
220	138	Jocelyn Villaraza Ramirez	branch_admin	1	USER_LOGIN	Successful login from IP 100.64.0.15	100.64.0.15	2026-09-22 11:11:01.860932
221	138	Jocelyn Villaraza Ramirez	parent	1	ROLE_SWITCH	User switched active portal role to parent	100.64.0.12	2026-09-22 11:11:10.731853
222	138	Vivian Maria Mamaril	branch_admin	1	ROLE_SWITCH	User switched active portal role to branch_admin	100.64.0.7	2026-09-22 11:11:15.693703
223	138	Jocelyn Villaraza Ramirez	branch_admin	1	USER_LOGIN	Successful login from IP 100.64.0.16	100.64.0.16	2026-09-22 11:12:41.924049
224	138	Jocelyn Villaraza Ramirez	parent	1	ROLE_SWITCH	User switched active portal role to parent	100.64.0.14	2026-09-22 11:12:47.307814
225	138	Vivian Maria Mamaril	branch_admin	1	ROLE_SWITCH	User switched active portal role to branch_admin	100.64.0.7	2026-09-22 11:12:53.13694
226	138	Jocelyn Villaraza Ramirez	branch_admin	1	USER_LOGIN	Successful login from IP 100.64.0.12	100.64.0.12	2026-09-22 11:12:59.38757
227	\N	LDMAJ_0015	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_0015' from IP 100.64.0.8	100.64.0.8	2026-09-22 11:14:16.993204
228	\N	LDMAJ_0015	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_0015' from IP 100.64.0.8	100.64.0.8	2026-09-22 11:14:26.488839
229	\N	LDMAJ_0015	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_0015' from IP 100.64.0.13	100.64.0.13	2026-09-22 11:14:34.895491
230	\N	LDBB_0019	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDBB_0019' from IP 100.64.0.1	100.64.0.1	2026-09-22 11:14:54.536368
231	\N	LDBB_0015	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDBB_0015' from IP 100.64.0.17	100.64.0.17	2026-09-22 11:15:04.041221
232	149	LDBB_0015	student	10	USER_LOGIN	Successful login from IP 100.64.0.5	100.64.0.5	2026-09-22 11:15:15.019168
233	149	LDBB_0015	parent	10	ROLE_SWITCH	User switched active portal role to parent	100.64.0.20	2026-09-22 11:15:21.102219
234	149	Junterial Maria Sierra	student	10	ROLE_SWITCH	User switched active portal role to student	100.64.0.5	2026-09-22 11:15:27.375912
235	130	LDBB_0001	student	10	USER_LOGIN	Successful login from IP 100.64.0.4	100.64.0.4	2026-09-22 12:35:53.794626
236	\N	LDBB_Parent	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDBB_Parent' from IP 100.64.0.2	100.64.0.2	2026-09-22 12:36:37.800432
237	111	Mary Grace Reyes	registrar	10	USER_LOGIN	Successful login from IP 100.64.0.1	100.64.0.1	2026-09-22 12:36:56.120039
238	111	Mary Grace Reyes	registrar	10	USER_LOGIN	Successful login from IP 100.64.0.2	100.64.0.2	2026-09-22 12:41:16.642327
239	111	Mary Grace Reyes	parent	10	ROLE_SWITCH	User switched active portal role to parent	100.64.0.9	2026-09-22 12:56:04.518289
240	111	John Lee Smith	registrar	10	ROLE_SWITCH	User switched active portal role to registrar	100.64.0.16	2026-09-22 12:56:10.858557
241	114	Zoe Anne Lim	teacher	10	USER_LOGIN	Successful login from IP 100.64.0.16	100.64.0.16	2026-09-22 12:58:02.731813
242	114	Zoe Anne Lim	teacher	10	USER_LOGIN	Successful login from IP 100.64.0.16	100.64.0.16	2026-09-22 13:19:36.709704
243	106	Brenda Robel Biticon	parent	4	USER_LOGIN	Successful login from IP 100.64.0.9	100.64.0.9	2026-09-22 13:59:41.26322
244	109	Joseph Lim Cruz	branch_admin	10	USER_LOGIN	Successful login from IP 100.64.0.8	100.64.0.8	2026-09-22 14:11:31.539827
245	\N	LDMAJ_Admin	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_Admin' from IP 100.64.0.9	100.64.0.9	2026-09-22 21:43:48.052055
246	138	Jocelyn Villaraza Ramirez	branch_admin	1	USER_LOGIN	Successful login from IP 100.64.0.11	100.64.0.11	2026-09-22 21:43:58.231222
247	138	Jocelyn Villaraza Ramirez	parent	1	ROLE_SWITCH	User switched active portal role to parent	100.64.0.9	2026-09-22 21:44:10.172409
248	138	Vivian Maria Mamaril	branch_admin	1	ROLE_SWITCH	User switched active portal role to branch_admin	100.64.0.14	2026-09-22 21:44:14.893084
249	138	Jocelyn Villaraza Ramirez	branch_admin	1	USER_LOGIN	Successful login from IP 100.64.0.14	100.64.0.14	2026-09-22 21:44:44.467615
250	138	Jocelyn Villaraza Ramirez	branch_admin	1	USER_LOGIN	Successful login from IP 100.64.0.3	100.64.0.3	2026-09-22 22:23:27.227237
251	\N	LDMAJ_Registrar	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_Registrar' from IP 100.64.0.4	100.64.0.4	2026-09-22 22:25:43.951513
252	139	Maricis Modina	registrar	1	USER_LOGIN	Successful login from IP 100.64.0.3	100.64.0.3	2026-09-22 22:26:03.021994
253	138	Jocelyn Villaraza Ramirez	branch_admin	1	USER_LOGIN	Successful login from IP 100.64.0.3	100.64.0.3	2026-09-22 22:26:53.653234
254	111	Mary Grace Reyes	registrar	10	USER_LOGIN	Successful login from IP 100.64.0.4	100.64.0.4	2026-09-22 22:28:51.028178
255	109	Joseph Lim Cruz	branch_admin	10	USER_LOGIN	Successful login from IP 100.64.0.1	100.64.0.1	2026-09-22 22:29:31.153913
256	111	Mary Grace Reyes	registrar	10	USER_LOGIN	Successful login from IP 100.64.0.3	100.64.0.3	2026-09-22 22:30:44.302726
257	109	Joseph Lim Cruz	branch_admin	10	USER_LOGIN	Successful login from IP 100.64.0.8	100.64.0.8	2026-09-22 22:37:09.29366
258	\N	LDBB_Teacher	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDBB_Teacher' from IP 100.64.0.5	100.64.0.5	2026-09-23 01:59:54.84647
259	114	Zoe Anne Lim	teacher	10	USER_LOGIN	Successful login from IP 100.64.0.7	100.64.0.7	2026-09-23 02:00:02.786447
260	\N	LDBB_Admin	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDBB_Admin' from IP 100.64.0.8	100.64.0.8	2026-09-23 02:00:50.528868
261	109	Joseph Lim Cruz	branch_admin	10	USER_LOGIN	Successful login from IP 100.64.0.1	100.64.0.1	2026-09-23 02:00:57.936196
262	114	Zoe Anne Lim	teacher	10	USER_LOGIN	Successful login from IP 100.64.0.6	100.64.0.6	2026-09-23 02:02:31.910246
263	\N	LDBB_0004	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDBB_0004' from IP 100.64.0.13	100.64.0.13	2026-09-23 11:19:45.531203
264	\N	LDBB_0004	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDBB_0004' from IP 100.64.0.3	100.64.0.3	2026-09-23 11:19:53.675448
265	130	LDBB_0001	student	10	USER_LOGIN	Successful login from IP 100.64.0.21	100.64.0.21	2026-09-23 11:20:03.470676
266	109	Joseph Lim Cruz	branch_admin	10	USER_LOGIN	Successful login from IP 100.64.0.15	100.64.0.15	2026-09-23 11:20:55.948365
267	\N	LDMAJ_Teacher12	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_Teacher12' from IP 100.64.0.12	100.64.0.12	2026-09-23 11:23:44.104392
268	\N	LDMAJ_Teacher12	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_Teacher12' from IP 100.64.0.11	100.64.0.11	2026-09-23 11:23:57.571702
269	\N	LDMAJ_Teacher12	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_Teacher12' from IP 100.64.0.18	100.64.0.18	2026-09-23 11:24:02.763943
270	114	Zoe Anne Lim	teacher	10	USER_LOGIN	Successful login from IP 100.64.0.3	100.64.0.3	2026-09-23 11:35:05.802052
271	\N	LDBB_0020	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDBB_0020' from IP 100.64.0.8	100.64.0.8	2026-09-23 11:38:01.907973
272	149	LDBB_0015	student	10	USER_LOGIN	Successful login from IP 100.64.0.12	100.64.0.12	2026-09-23 11:38:38.873671
273	114	Zoe Anne Lim	teacher	10	USER_LOGIN	Successful login from IP 100.64.0.17	100.64.0.17	2026-09-23 11:38:57.113204
274	149	LDBB_0015	student	10	USER_LOGIN	Successful login from IP 100.64.0.14	100.64.0.14	2026-09-23 11:39:32.631513
275	\N	LDBB_0001	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDBB_0001' from IP 100.64.0.6	100.64.0.6	2026-09-23 12:07:21.264706
276	\N	LDBB_0004	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDBB_0004' from IP 100.64.0.5	100.64.0.5	2026-09-23 12:08:07.990908
277	\N	LDBB_0001	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDBB_0001' from IP 100.64.0.16	100.64.0.16	2026-09-23 12:08:26.860542
278	130	LDBB_0001	student	10	USER_LOGIN	Successful login from IP 100.64.0.13	100.64.0.13	2026-09-23 12:08:50.585712
279	149	LDBB_0015	student	10	USER_LOGIN	Successful login from IP 100.64.0.21	100.64.0.21	2026-09-23 12:09:36.884412
280	149	LDBB_0015	student	10	USER_LOGIN	Successful login from IP 100.64.0.8	100.64.0.8	2026-09-23 12:14:57.186975
281	149	LDBB_0015	student	10	USER_LOGIN	Successful login from IP 100.64.0.4	100.64.0.4	2026-09-23 12:51:42.763234
282	\N	LDPSJ_Teacher_2	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDPSJ_Teacher_2' from IP 100.64.0.1	100.64.0.1	2026-09-24 05:51:18.594676
283	\N	LDPSJ_Teacher_2	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDPSJ_Teacher_2' from IP 100.64.0.7	100.64.0.7	2026-09-24 05:51:39.154166
284	\N	LDPAE_Teacher	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDPAE_Teacher' from IP 100.64.0.3	100.64.0.3	2026-09-24 05:52:00.108754
285	86	Joy Cruz	teacher	4	USER_LOGIN	Successful login from IP 100.64.0.19	100.64.0.19	2026-09-24 05:52:32.48561
286	86	Joy Cruz	teacher	4	USER_LOGIN	Successful login from IP 100.64.0.21	100.64.0.21	2026-09-24 05:52:45.692586
287	\N	LDBAY_Teacher	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDBAY_Teacher' from IP 100.64.0.6	100.64.0.6	2026-09-24 05:53:28.456941
288	86	Joy Cruz	teacher	4	USER_LOGIN	Successful login from IP 100.64.0.9	100.64.0.9	2026-09-24 05:53:52.139662
289	106	Brenda Robel Biticon	parent	4	USER_LOGIN	Successful login from IP 100.64.0.11	100.64.0.11	2026-09-24 05:54:57.701264
290	\N	LDMAJ_Registrar	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_Registrar' from IP 100.64.0.9	100.64.0.9	2026-09-24 06:16:55.759692
291	\N	LDMAJ_Registrar	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_Registrar' from IP 100.64.0.10	100.64.0.10	2026-09-24 06:17:39.081385
292	139	Maricis Modina	registrar	1	USER_LOGIN	Successful login from IP 100.64.0.13	100.64.0.13	2026-09-24 06:17:49.991591
293	\N	LDMAJ_Registrar	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_Registrar' from IP 100.64.0.20	100.64.0.20	2026-09-24 06:37:00.288483
294	139	Maricis Modina	registrar	1	USER_LOGIN	Successful login from IP 100.64.0.18	100.64.0.18	2026-09-24 06:48:48.460418
295	\N	LDMAJ_Registrar	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_Registrar' from IP 100.64.0.7	100.64.0.7	2026-09-24 08:23:24.813855
296	139	Maricis Modina	registrar	1	USER_LOGIN	Successful login from IP 100.64.0.14	100.64.0.14	2026-09-24 08:23:42.287676
297	139	Maricis Modina	registrar	1	USER_LOGIN	Successful login from IP 100.64.0.7	100.64.0.7	2026-09-24 08:26:28.254321
298	138	Jocelyn Villaraza Ramirez	branch_admin	1	USER_LOGIN	Successful login from IP 100.64.0.4	100.64.0.4	2026-09-24 09:50:27.361865
299	138	Jocelyn Villaraza Ramirez	branch_admin	1	USER_LOGIN	Successful login from IP 100.64.0.9	100.64.0.9	2026-09-24 10:42:27.329251
300	139	Maricis Modina	registrar	1	USER_LOGIN	Successful login from IP 100.64.0.21	100.64.0.21	2026-09-24 12:24:08.264632
301	\N	LDMAJ_0173	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_0173' from IP 100.64.0.14	100.64.0.14	2026-09-24 12:25:55.050194
302	153	LDMAJ_0173	student	1	USER_LOGIN	Successful login from IP 100.64.0.11	100.64.0.11	2026-09-24 12:27:35.447099
303	153	LDMAJ_0173	student	1	USER_LOGIN	Successful login from IP 100.64.0.3	100.64.0.3	2026-09-24 12:30:47.212845
304	\N	LDMAJ_Registrar	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_Registrar' from IP 100.64.0.3	100.64.0.3	2026-09-24 12:51:36.524793
305	139	Maricis Modina	registrar	1	USER_LOGIN	Successful login from IP 100.64.0.13	100.64.0.13	2026-09-24 12:51:48.23222
306	139	Maricis Modina	registrar	1	USER_LOGIN	Successful login from IP 100.64.0.2	100.64.0.2	2026-09-24 12:52:04.876686
307	138	Jocelyn Villaraza Ramirez	branch_admin	1	USER_LOGIN	Successful login from IP 100.64.0.17	100.64.0.17	2026-09-24 12:53:21.496053
308	\N	Niña Conejares	guest	\N	FAILED_LOGIN	Failed login attempt for username 'Niña Conejares' from IP 100.64.0.10	100.64.0.10	2026-09-24 12:57:41.19098
309	\N	ninaconejares_	guest	\N	FAILED_LOGIN	Failed login attempt for username 'ninaconejares_' from IP 100.64.0.6	100.64.0.6	2026-09-24 12:57:55.178997
310	\N	LDMAJ_0011	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_0011' from IP 100.64.0.6	100.64.0.6	2026-09-24 12:58:13.524265
311	154	LDMAJ_0011	student	1	USER_LOGIN	Successful login from IP 100.64.0.21	100.64.0.21	2026-09-24 12:58:31.097294
312	\N	LDMAJ_0068	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_0068' from IP 100.64.0.15	100.64.0.15	2026-09-24 13:21:34.358653
313	155	LDMAJ_0068	student	1	USER_LOGIN	Successful login from IP 100.64.0.3	100.64.0.3	2026-09-24 13:21:43.20364
314	156	LDMAJ_0057	student	1	USER_LOGIN	Successful login from IP 100.64.0.15	100.64.0.15	2026-09-24 13:22:35.873789
315	138	Jocelyn Villaraza Ramirez	branch_admin	1	USER_LOGIN	Successful login from IP 100.64.0.11	100.64.0.11	2026-09-24 14:00:59.700008
316	\N	coderajamila@gmail.com	guest	\N	FAILED_LOGIN	Failed login attempt for username 'coderajamila@gmail.com' from IP 100.64.0.18	100.64.0.18	2026-09-24 14:01:52.509033
317	\N	coderajamila@gmail.com	guest	\N	FAILED_LOGIN	Failed login attempt for username 'coderajamila@gmail.com' from IP 100.64.0.15	100.64.0.15	2026-09-24 14:02:03.228088
318	\N	LDMAJ_0065	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_0065' from IP 100.64.0.8	100.64.0.8	2026-09-24 14:03:47.739445
319	\N	LDMAJ	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ' from IP 100.64.0.10	100.64.0.10	2026-09-24 14:05:42.323608
320	157	LDMAJ_0065	student	1	USER_LOGIN	Successful login from IP 100.64.0.18	100.64.0.18	2026-09-24 14:06:00.814266
321	139	Maricis Modina	registrar	1	USER_LOGIN	Successful login from IP 100.64.0.10	100.64.0.10	2026-09-24 15:13:41.462738
322	138	Jocelyn Villaraza Ramirez	branch_admin	1	USER_LOGIN	Successful login from IP 100.64.0.9	100.64.0.9	2026-09-24 15:15:53.615082
323	\N	LDMAJ_0288	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_0288' from IP 100.64.0.15	100.64.0.15	2026-09-24 19:36:00.264556
324	86	Joy Cruz	teacher	4	USER_LOGIN	Successful login from IP 100.64.0.3	100.64.0.3	2026-09-25 02:40:58.446181
325	138	Jocelyn Villaraza Ramirez	branch_admin	1	USER_LOGIN	Successful login from IP 100.64.0.13	100.64.0.13	2026-09-25 02:49:05.087793
326	139	Maricis Modina	registrar	1	USER_LOGIN	Successful login from IP 100.64.0.15	100.64.0.15	2026-09-25 02:49:23.39138
327	138	Jocelyn Villaraza Ramirez	branch_admin	1	USER_LOGIN	Successful login from IP 100.64.0.11	100.64.0.11	2026-09-25 05:09:34.825102
328	139	Precy Angela C. Roceo	registrar	1	USER_LOGIN	Successful login from IP 100.64.0.4	100.64.0.4	2026-09-25 08:08:17.741549
329	138	Jocelyn Villaraza Ramirez	branch_admin	1	USER_LOGIN	Successful login from IP 100.64.0.19	100.64.0.19	2026-09-25 14:54:23.272018
330	65	System Administrator	super_admin	\N	USER_LOGIN	Successful login from IP 100.64.0.19	100.64.0.19	2026-09-26 03:35:00.070384
331	138	Jocelyn Villaraza Ramirez	branch_admin	1	USER_LOGIN	Successful login from IP 100.64.0.13	100.64.0.13	2026-09-26 06:20:07.453402
332	\N	LDMAJ_0001	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_0001' from IP 100.64.0.17	100.64.0.17	2026-09-26 07:54:39.440891
333	\N	LDBB_0001	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDBB_0001' from IP 100.64.0.16	100.64.0.16	2026-09-26 09:39:35.692581
334	\N	LDBB_0004	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDBB_0004' from IP 100.64.0.1	100.64.0.1	2026-09-26 09:39:47.033876
335	\N	LDBB_0004	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDBB_0004' from IP 100.64.0.1	100.64.0.1	2026-09-26 09:39:56.993608
336	\N	LDBB_0004	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDBB_0004' from IP 100.64.0.19	100.64.0.19	2026-09-26 09:40:23.56179
337	\N	LDBB_0012	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDBB_0012' from IP 100.64.0.20	100.64.0.20	2026-09-26 09:40:31.724826
338	\N	LDBB_Registrar	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDBB_Registrar' from IP 100.64.0.19	100.64.0.19	2026-09-26 09:40:42.669355
339	111	Mary Grace Reyes	registrar	10	USER_LOGIN	Successful login from IP 100.64.0.18	100.64.0.18	2026-09-26 09:40:52.643491
340	\N	LDBB_0019	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDBB_0019' from IP 100.64.0.16	100.64.0.16	2026-09-26 09:41:20.555544
341	\N	LDBB_0019	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDBB_0019' from IP 100.64.0.10	100.64.0.10	2026-09-26 09:41:35.597967
342	\N	LDBB_0019	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDBB_0019' from IP 100.64.0.12	100.64.0.12	2026-09-26 09:41:40.887166
343	\N	LDBB_0019	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDBB_0019' from IP 100.64.0.12	100.64.0.12	2026-09-26 09:41:47.334086
344	\N	LDBB_0015	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDBB_0015' from IP 100.64.0.2	100.64.0.2	2026-09-26 09:41:58.889768
345	149	LDBB_0015	student	10	USER_LOGIN	Successful login from IP 100.64.0.4	100.64.0.4	2026-09-26 09:42:07.819415
346	166	LDMAJ_0055	student	1	USER_LOGIN	Successful login from IP 100.64.0.20	100.64.0.20	2026-09-26 16:18:26.848438
347	167	LDMAJ_0100	student	1	USER_LOGIN	Successful login from IP 100.64.0.19	100.64.0.19	2026-09-27 02:33:45.347141
348	138	Jocelyn Villaraza Ramirez	branch_admin	1	USER_LOGIN	Successful login from IP 100.64.0.12	100.64.0.12	2026-09-28 03:53:00.243554
349	\N	LDMAJ_Registrar	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_Registrar' from IP 100.64.0.15	100.64.0.15	2026-09-28 03:57:36.65612
350	139	Precy Angela C. Roceo	registrar	1	USER_LOGIN	Successful login from IP 100.64.0.13	100.64.0.13	2026-09-28 03:57:48.250768
351	\N	queenb026880@gmail.com	guest	\N	FAILED_LOGIN	Failed login attempt for username 'queenb026880@gmail.com' from IP 100.64.0.18	100.64.0.18	2026-09-28 05:08:36.814475
352	\N	queenb026880@gmail.com	guest	\N	FAILED_LOGIN	Failed login attempt for username 'queenb026880@gmail.com' from IP 100.64.0.16	100.64.0.16	2026-09-28 05:10:43.633703
353	\N	queenb026880@gmail.com	guest	\N	FAILED_LOGIN	Failed login attempt for username 'queenb026880@gmail.com' from IP 100.64.0.5	100.64.0.5	2026-09-28 05:12:03.336503
354	\N	queenb026880@gmail.com	guest	\N	FAILED_LOGIN	Failed login attempt for username 'queenb026880@gmail.com' from IP 100.64.0.5	100.64.0.5	2026-09-28 05:13:25.773925
355	138	Jocelyn Villaraza Ramirez	branch_admin	1	USER_LOGIN	Successful login from IP 100.64.0.12	100.64.0.12	2026-09-28 05:15:15.245027
356	\N	LDMAJ_0288	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_0288' from IP 100.64.0.14	100.64.0.14	2026-09-28 05:15:26.491712
357	\N	queenb026880@gmail.com	guest	\N	FAILED_LOGIN	Failed login attempt for username 'queenb026880@gmail.com' from IP 100.64.0.14	100.64.0.14	2026-09-28 05:15:50.36048
358	\N	Baby Queen D.  Buera	guest	\N	FAILED_LOGIN	Failed login attempt for username 'Baby Queen D.  Buera' from IP 100.64.0.17	100.64.0.17	2026-09-28 05:16:42.793809
359	\N	LDMAJ_0288	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_0288' from IP 100.64.0.21	100.64.0.21	2026-09-28 05:17:34.199936
360	\N	LDMAJ_0288	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_0288' from IP 100.64.0.16	100.64.0.16	2026-09-28 05:17:52.666608
361	168	LDMAJ_0076	student	1	USER_LOGIN	Successful login from IP 100.64.0.18	100.64.0.18	2026-09-28 07:35:07.313136
362	169	LDMAJ_0039	student	1	USER_LOGIN	Successful login from IP 100.64.0.11	100.64.0.11	2026-09-29 06:37:02.505233
363	\N	LDBB_0020	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDBB_0020' from IP 100.64.0.15	100.64.0.15	2026-09-29 10:57:06.758025
364	\N	LDBB_0020	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDBB_0020' from IP 100.64.0.8	100.64.0.8	2026-09-29 10:57:16.810534
365	\N	LDBB_0019	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDBB_0019' from IP 100.64.0.3	100.64.0.3	2026-09-29 10:57:36.398404
366	\N	LDBB_0019	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDBB_0019' from IP 100.64.0.15	100.64.0.15	2026-09-29 10:57:47.1893
367	\N	LDBB_0021	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDBB_0021' from IP 100.64.0.3	100.64.0.3	2026-09-29 10:58:12.885989
368	\N	LDBB_Registrar	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDBB_Registrar' from IP 100.64.0.20	100.64.0.20	2026-09-29 10:58:54.409347
369	111	Mary Grace Reyes	registrar	10	USER_LOGIN	Successful login from IP 100.64.0.7	100.64.0.7	2026-09-29 10:59:05.563415
370	\N	LDBB_0014	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDBB_0014' from IP 100.64.0.8	100.64.0.8	2026-09-29 11:01:21.22455
371	140	LDBB_0014	student	10	USER_LOGIN	Successful login from IP 100.64.0.20	100.64.0.20	2026-09-29 11:01:30.543585
372	111	Mary Grace Reyes	registrar	10	USER_LOGIN	Successful login from IP 100.64.0.8	100.64.0.8	2026-09-29 11:05:36.969844
373	65	System Administrator	super_admin	\N	USER_LOGIN	Successful login from IP 100.64.0.2	100.64.0.2	2026-09-29 11:07:39.730552
374	109	Joseph Lim Cruz	branch_admin	10	USER_LOGIN	Successful login from IP 100.64.0.9	100.64.0.9	2026-09-29 11:09:48.574582
375	111	Mary Grace Reyes	registrar	10	USER_LOGIN	Successful login from IP 100.64.0.4	100.64.0.4	2026-09-29 11:14:53.637715
376	111	Mary Grace Reyes	parent	10	ROLE_SWITCH	User switched active portal role to parent	100.64.0.12	2026-09-29 11:18:51.61419
377	131	Mary Santos	cashier	10	USER_LOGIN	Successful login from IP 100.64.0.6	100.64.0.6	2026-09-29 11:22:01.56993
378	113	Jose Luis Mercedes	librarian	10	USER_LOGIN	Successful login from IP 100.64.0.13	100.64.0.13	2026-09-29 11:24:56.037581
379	114	Zoe Anne Lim	teacher	10	USER_LOGIN	Successful login from IP 100.64.0.21	100.64.0.21	2026-09-29 11:27:02.989061
380	149	LDBB_0015	student	10	USER_LOGIN	Successful login from IP 100.64.0.4	100.64.0.4	2026-09-29 11:35:54.579166
381	114	Zoe Anne Lim	teacher	10	USER_LOGIN	Successful login from IP 100.64.0.17	100.64.0.17	2026-09-29 11:37:13.73001
382	\N	LDMAJ_Teacher	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_Teacher' from IP 100.64.0.20	100.64.0.20	2026-10-01 02:30:56.316641
383	86	Joy Cruz	teacher	4	USER_LOGIN	Successful login from IP 100.64.0.19	100.64.0.19	2026-10-01 02:31:01.79916
384	114	Zoe Anne Lim	teacher	10	USER_LOGIN	Successful login from IP 100.64.0.6	100.64.0.6	2026-10-01 02:32:35.827532
385	109	Joseph Lim Cruz	branch_admin	10	USER_LOGIN	Successful login from IP 100.64.0.3	100.64.0.3	2026-10-01 02:33:21.893357
386	114	Zoe Anne Lim	teacher	10	USER_LOGIN	Successful login from IP 100.64.0.20	100.64.0.20	2026-10-01 02:35:17.030001
387	114	Zoe Anne Lim	teacher	10	USER_LOGIN	Successful login from IP 100.64.0.10	100.64.0.10	2026-10-01 02:35:44.252267
388	109	Joseph Lim Cruz	branch_admin	10	USER_LOGIN	Successful login from IP 100.64.0.3	100.64.0.3	2026-10-01 02:40:41.264733
389	114	Zoe Anne Lim	teacher	10	USER_LOGIN	Successful login from IP 100.64.0.5	100.64.0.5	2026-10-01 02:42:06.5181
390	114	Zoe Anne Lim	teacher	10	USER_LOGIN	Successful login from IP 100.64.0.16	100.64.0.16	2026-10-01 02:47:56.435667
391	\N	LDBB_Student	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDBB_Student' from IP 100.64.0.7	100.64.0.7	2026-10-01 03:17:07.862349
392	\N	LDMAJ_0001	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_0001' from IP 100.64.0.21	100.64.0.21	2026-10-01 03:36:13.596998
393	107	LDPSJ_0001	student	4	USER_LOGIN	Successful login from IP 100.64.0.12	100.64.0.12	2026-10-01 03:36:43.979099
394	\N	LDMAJ_0001	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_0001' from IP 100.64.0.14	100.64.0.14	2026-10-01 04:42:23.632561
395	83	Mateo De Leon	registrar	4	USER_LOGIN	Successful login from IP 100.64.0.15	100.64.0.15	2026-10-01 05:55:41.234676
396	83	Mateo De Leon	registrar	4	USER_LOGIN	Successful login from IP 100.64.0.2	100.64.0.2	2026-10-01 05:55:41.432971
397	139	Precy Angela C. Roceo	registrar	1	USER_LOGIN	Successful login from IP 100.64.0.12	100.64.0.12	2026-10-01 05:57:08.1746
398	\N	LDMAJ_Teacher	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_Teacher' from IP 100.64.0.4	100.64.0.4	2026-10-01 06:00:02.70304
399	\N	LDMAJ_Teacher	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_Teacher' from IP 100.64.0.14	100.64.0.14	2026-10-01 06:00:09.238465
400	139	Precy Angela C. Roceo	registrar	1	USER_LOGIN	Successful login from IP 100.64.0.6	100.64.0.6	2026-10-01 06:00:30.284473
401	139	Precy Angela C. Roceo	registrar	1	USER_LOGIN	Successful login from IP 100.64.0.7	100.64.0.7	2026-10-01 06:32:11.91296
402	170	LDMAJ_0052	student	1	USER_LOGIN	Successful login from IP 100.64.0.14	100.64.0.14	2026-10-01 06:43:08.653357
403	\N	LDMAJ_Cashier	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_Cashier' from IP 100.64.0.18	100.64.0.18	2026-10-01 07:39:30.527467
404	84	Severin Maria Clarke	cashier	4	USER_LOGIN	Successful login from IP 100.64.0.4	100.64.0.4	2026-10-01 07:40:51.647714
405	85	Maria Lee	librarian	4	USER_LOGIN	Successful login from IP 100.64.0.16	100.64.0.16	2026-10-01 07:54:36.374664
406	106	Brenda Robel Biticon	parent	4	USER_LOGIN	Successful login from IP 100.64.0.13	100.64.0.13	2026-10-01 08:26:56.251466
407	171	LDMAJ_0027	student	1	USER_LOGIN	Successful login from IP 100.64.0.13	100.64.0.13	2026-10-01 09:23:47.677221
408	106	Brenda Robel Biticon	parent	4	USER_LOGIN	Successful login from IP 100.64.0.12	100.64.0.12	2026-10-01 12:44:10.714128
409	107	LDPSJ_0001	student	4	USER_LOGIN	Successful login from IP 100.64.0.16	100.64.0.16	2026-10-01 12:49:41.197045
410	109	Joseph Lim Cruz	branch_admin	10	USER_LOGIN	Successful login from IP 100.64.0.5	100.64.0.5	2026-10-01 12:56:16.900591
411	113	Jose Luis Mercedes	librarian	10	USER_LOGIN	Successful login from IP 100.64.0.12	100.64.0.12	2026-10-01 12:56:54.242912
412	113	Jose Luis Mercedes	parent	10	ROLE_SWITCH	User switched active portal role to parent	100.64.0.16	2026-10-01 12:57:11.058449
413	114	Zoe Anne Lim	teacher	10	USER_LOGIN	Successful login from IP 100.64.0.18	100.64.0.18	2026-10-01 12:57:49.541433
414	\N	LDBB_0001	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDBB_0001' from IP 100.64.0.13	100.64.0.13	2026-10-01 12:58:10.921458
415	\N	LDBB_0001	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDBB_0001' from IP 100.64.0.17	100.64.0.17	2026-10-01 12:58:29.020032
416	114	Zoe Anne Lim	teacher	10	USER_LOGIN	Successful login from IP 100.64.0.19	100.64.0.19	2026-10-01 12:58:31.374591
417	\N	LDBB_0001	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDBB_0001' from IP 100.64.0.19	100.64.0.19	2026-10-01 13:01:26.114004
418	83	Mateo De Leon	registrar	4	USER_LOGIN	Successful login from IP 100.64.0.9	100.64.0.9	2026-10-01 13:02:00.054091
419	114	Zoe Anne Lim	teacher	10	USER_LOGIN	Successful login from IP 100.64.0.12	100.64.0.12	2026-10-01 13:03:12.643075
420	149	LDBB_0015	student	10	USER_LOGIN	Successful login from IP 100.64.0.7	100.64.0.7	2026-10-01 13:06:22.893384
421	149	LDBB_0015	student	10	USER_LOGIN	Successful login from IP 100.64.0.2	100.64.0.2	2026-10-01 14:22:50.523282
422	138	Jocelyn Villaraza Ramirez	branch_admin	1	USER_LOGIN	Successful login from IP 100.64.0.16	100.64.0.16	2026-10-01 23:05:48.284354
423	138	Jocelyn Villaraza Ramirez	branch_admin	1	USER_LOGIN	Successful login from IP 100.64.0.8	100.64.0.8	2026-10-02 23:42:04.240582
424	138	Jocelyn Villaraza Ramirez	branch_admin	1	USER_LOGIN	Successful login from IP 100.64.0.2	100.64.0.2	2026-10-03 02:32:40.041236
425	138	Jocelyn Villaraza Ramirez	branch_admin	1	USER_LOGIN	Successful login from IP 100.64.0.1	100.64.0.1	2026-10-03 04:04:12.31766
426	169	LDMAJ_0039	student	1	USER_LOGIN	Successful login from IP 100.64.0.12	100.64.0.12	2026-10-03 08:38:42.440517
427	138	Jocelyn Villaraza Ramirez	branch_admin	1	USER_LOGIN	Successful login from IP 100.64.0.20	100.64.0.20	2026-10-03 10:32:07.074226
428	169	LDMAJ_0039	student	1	USER_LOGIN	Successful login from IP 100.64.0.5	100.64.0.5	2026-10-03 12:11:51.096891
429	138	Jocelyn Villaraza Ramirez	branch_admin	1	USER_LOGIN	Successful login from IP 100.64.0.4	100.64.0.4	2026-10-03 13:10:42.537594
430	114	Zoe Anne Lim	teacher	10	USER_LOGIN	Successful login from IP 100.64.0.14	100.64.0.14	2026-10-04 16:19:14.777513
431	\N	LDBB_Student	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDBB_Student' from IP 100.64.0.2	100.64.0.2	2026-10-04 17:03:20.743335
432	149	LDBB_0015	student	10	USER_LOGIN	Successful login from IP 100.64.0.15	100.64.0.15	2026-10-04 17:04:05.061121
433	169	LDMAJ_0039	student	1	USER_LOGIN	Successful login from IP 100.64.0.15	100.64.0.15	2026-10-05 01:23:55.531858
434	149	LDBB_0015	student	10	USER_LOGIN	Successful login from IP 100.64.0.4	100.64.0.4	2026-10-05 08:43:00.320597
435	114	Zoe Anne Lim	teacher	10	USER_LOGIN	Successful login from IP 100.64.0.11	100.64.0.11	2026-10-05 08:47:42.618382
436	114	Zoe Anne Lim	teacher	10	USER_LOGIN	Successful login from IP 100.64.0.21	100.64.0.21	2026-10-05 14:26:03.533053
437	109	Joseph Lim Cruz	branch_admin	10	USER_LOGIN	Successful login from IP 100.64.0.19	100.64.0.19	2026-10-05 14:26:18.36099
438	111	Mary Grace Reyes	registrar	10	USER_LOGIN	Successful login from IP 100.64.0.2	100.64.0.2	2026-10-05 14:26:34.13383
439	111	Mary Grace Reyes	parent	10	ROLE_SWITCH	User switched active portal role to parent	100.64.0.3	2026-10-05 14:26:38.535901
440	114	Zoe Anne Lim	teacher	10	USER_LOGIN	Successful login from IP 100.64.0.15	100.64.0.15	2026-10-05 18:22:00.143296
441	131	Mary Santos	cashier	10	USER_LOGIN	Successful login from IP 100.64.0.16	100.64.0.16	2026-10-05 18:36:25.944356
442	114	Zoe Anne Lim	teacher	10	USER_LOGIN	Successful login from IP 100.64.0.14	100.64.0.14	2026-10-05 18:41:36.014741
443	\N	LDBB_ADMIN	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDBB_ADMIN' from IP 100.64.0.17	100.64.0.17	2026-10-05 18:50:31.84618
444	138	Jocelyn Villaraza Ramirez	branch_admin	1	USER_LOGIN	Successful login from IP 100.64.0.3	100.64.0.3	2026-10-05 18:50:37.499727
445	149	LDBB_0015	student	10	USER_LOGIN	Successful login from IP 100.64.0.1	100.64.0.1	2026-10-05 18:56:15.029023
446	139	Precy Angela C. Roceo	registrar	1	USER_LOGIN	Successful login from IP 100.64.0.2	100.64.0.2	2026-10-06 01:09:38.764063
447	114	Zoe Anne Lim	teacher	10	USER_LOGIN	Successful login from IP 100.64.0.5	100.64.0.5	2026-10-06 01:36:02.258567
448	\N	LDMAJ_Teacher	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_Teacher' from IP 100.64.0.3	100.64.0.3	2026-10-06 01:36:14.656172
449	114	Zoe Anne Lim	teacher	10	USER_LOGIN	Successful login from IP 100.64.0.21	100.64.0.21	2026-10-06 01:36:23.280576
450	138	Jocelyn Villaraza Ramirez	branch_admin	1	USER_LOGIN	Successful login from IP 100.64.0.8	100.64.0.8	2026-10-06 01:37:32.116448
451	\N	LDBB_0004	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDBB_0004' from IP 100.64.0.11	100.64.0.11	2026-10-06 01:37:45.129978
452	\N	LDBB_0022	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDBB_0022' from IP 100.64.0.19	100.64.0.19	2026-10-06 01:37:58.484048
453	149	LDBB_0015	student	10	USER_LOGIN	Successful login from IP 100.64.0.19	100.64.0.19	2026-10-06 01:38:32.248042
454	139	Precy Angela C. Roceo	registrar	1	USER_LOGIN	Successful login from IP 100.64.0.19	100.64.0.19	2026-10-06 01:38:57.956065
455	111	Mary Grace Reyes	registrar	10	USER_LOGIN	Successful login from IP 100.64.0.13	100.64.0.13	2026-10-06 01:40:57.582661
456	\N	LDMAJ_Librarian	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_Librarian' from IP 100.64.0.18	100.64.0.18	2026-10-06 01:51:04.925496
457	\N	LDMAJ_Librarian	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDMAJ_Librarian' from IP 100.64.0.8	100.64.0.8	2026-10-06 01:51:32.312278
458	85	Maria Lee	librarian	4	USER_LOGIN	Successful login from IP 100.64.0.6	100.64.0.6	2026-10-06 01:53:08.566179
459	86	Joy Cruz	teacher	4	USER_LOGIN	Successful login from IP 100.64.0.15	100.64.0.15	2026-10-06 02:03:52.228242
460	114	Zoe Anne Lim	teacher	10	USER_LOGIN	Successful login from IP 100.64.0.19	100.64.0.19	2026-10-06 02:04:46.330313
461	131	Mary Santos	cashier	10	USER_LOGIN	Successful login from IP 100.64.0.17	100.64.0.17	2026-10-06 02:12:09.711288
462	109	Joseph Lim Cruz	branch_admin	10	USER_LOGIN	Successful login from IP 100.64.0.2	100.64.0.2	2026-10-07 12:39:27.537049
463	111	Mary Grace Reyes	registrar	10	USER_LOGIN	Successful login from IP 100.64.0.18	100.64.0.18	2026-10-07 12:45:53.938581
464	149	LDBB_0015	student	10	USER_LOGIN	Successful login from IP 100.64.0.21	100.64.0.21	2026-10-07 12:48:13.128288
465	111	Mary Grace Reyes	registrar	10	USER_LOGIN	Successful login from IP 100.64.0.6	100.64.0.6	2026-10-07 12:49:33.717995
466	109	Joseph Lim Cruz	branch_admin	10	USER_LOGIN	Successful login from IP 100.64.0.18	100.64.0.18	2026-10-07 12:53:30.517764
467	131	Mary Santos	cashier	10	USER_LOGIN	Successful login from IP 100.64.0.8	100.64.0.8	2026-10-07 13:09:26.074187
468	109	Joseph Lim Cruz	branch_admin	10	USER_LOGIN	Successful login from IP 100.64.0.19	100.64.0.19	2026-10-07 13:11:01.395965
469	114	Zoe Anne Lim	teacher	10	USER_LOGIN	Successful login from IP 100.64.0.13	100.64.0.13	2026-10-07 13:12:30.021716
470	111	Mary Grace Reyes	registrar	10	USER_LOGIN	Successful login from IP 100.64.0.19	100.64.0.19	2026-10-07 13:13:00.130678
471	111	Mary Grace Reyes	parent	10	ROLE_SWITCH	User switched active portal role to parent	100.64.0.17	2026-10-07 13:16:53.759477
472	131	Mary Santos	cashier	10	USER_LOGIN	Successful login from IP 100.64.0.8	100.64.0.8	2026-10-07 13:18:37.915676
473	111	Mary Grace Reyes	registrar	10	USER_LOGIN	Successful login from IP 100.64.0.10	100.64.0.10	2026-10-08 01:09:37.172357
474	109	Joseph Lim Cruz	branch_admin	10	USER_LOGIN	Successful login from IP 100.64.0.16	100.64.0.16	2026-10-08 01:09:58.261587
475	109	Joseph Lim Cruz	branch_admin	10	USER_LOGIN	Successful login from IP 100.64.0.2	100.64.0.2	2026-10-08 01:29:04.137593
476	109	Joseph Lim Cruz	branch_admin	10	USER_LOGIN	Successful login from IP 100.64.0.21	100.64.0.21	2026-10-08 01:29:57.890508
477	\N	LDBB_Parent1	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDBB_Parent1' from IP 100.64.0.12	100.64.0.12	2026-10-08 03:17:22.540513
478	\N	LDBB_Parent	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDBB_Parent' from IP 100.64.0.8	100.64.0.8	2026-10-08 03:17:29.68677
479	139	Precy Angela C. Roceo	registrar	1	USER_LOGIN	Successful login from IP 100.64.0.8	100.64.0.8	2026-10-08 03:18:42.779661
480	109	Joseph Lim Cruz	branch_admin	10	USER_LOGIN	Successful login from IP 100.64.0.9	100.64.0.9	2026-10-08 07:06:45.634459
481	\N	LDBB_Teacher	guest	\N	FAILED_LOGIN	Failed login attempt for username 'LDBB_Teacher' from IP 100.64.0.14	100.64.0.14	2026-10-08 07:21:58.555707
482	139	Precy Angela C. Roceo	registrar	1	USER_LOGIN	Successful login from IP 100.64.0.4	100.64.0.4	2026-10-08 09:29:57.057551
483	139	Precy Angela C. Roceo	registrar	1	USER_LOGIN	Successful login from IP 100.64.0.3	100.64.0.3	2026-10-08 10:16:23.508456
\.


--
-- Data for Name: billing; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.billing (bill_id, enrollment_id, branch_id, tuition_fee, books_fee, uniform_fee, other_fees, total_amount, amount_paid, balance, status, created_by, created_at, updated_at, year_id) FROM stdin;
16	489	10	14000.00	0.00	0.00	0.00	14000.00	14000.00	0.00	paid	131	2026-09-22 08:05:30.384611	2026-10-07 13:19:00.15273	30
17	496	10	14000.00	0.00	0.00	0.00	14000.00	1000.00	13000.00	partial	131	2026-09-29 11:22:29.419228	2026-10-07 13:19:00.15273	30
13	135	4	14000.00	800.00	4590.00	0.00	19390.00	17570.00	1820.00	partial	84	2026-08-19 08:02:39.294153	2026-08-22 05:58:18.524976	10
14	136	10	14000.00	0.00	0.00	0.00	14000.00	16323.00	0.00	paid	131	2026-08-31 08:56:27.758063	2026-09-01 03:06:51.943115	26
12	134	4	14000.00	800.00	2781.00	0.00	17581.00	18350.00	0.00	paid	84	2026-08-18 03:44:16.221278	2026-08-22 05:58:18.524976	10
15	141	10	15000.00	920.00	6120.00	0.00	22040.00	0.00	22040.00	pending	131	2026-09-01 03:05:56.73168	2026-09-29 11:23:19.992806	26
\.


--
-- Data for Name: book_release_items; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.book_release_items (release_item_id, release_id, item_id, qty, unit_price) FROM stdin;
1	1	110	1	323.00
2	2	1233	1	323.00
3	3	1233	1	323.00
\.


--
-- Data for Name: book_releases; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.book_releases (release_id, branch_id, enrollment_id, released_by_user_id, created_at, student_name) FROM stdin;
2	10	136	113	2026-08-31 09:07:08.09219	Melbourne Robel Biticon
3	10	136	113	2026-09-22 08:12:24.924385	Melbourne Robel Biticon
\.


--
-- Data for Name: branches; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.branches (branch_id, branch_name, location, status, created_at, is_active, branch_code, latitude, longitude) FROM stdin;
4	Liceo de Pagsanjan	Pagsanjan, Laguna	active	2026-04-29 02:59:43.823167	t	LDPSJ	14.2724245	121.4564643
5	Liceo de Luisiana	Luisiana, Laguna	active	2026-04-29 03:27:03.811945	t	LDLUI	14.1848216	121.5089953
7	Liceo de Calauan	Calauan, Laguna	active	2026-04-29 03:53:21.217222	t	LDCAL	14.1454104	121.3157451
8	ICCS - Sta. Cruz	Sta. Cruz, Laguna	active	2026-04-29 06:50:05.487684	t	LDMAJ1	14.1462922	121.4715953
6	Liceo de Paete	Paete, Laguna	active	2026-04-29 03:29:44.812804	t	LDPAE	14.3647219	121.4816680
10	Liceo de Bubukal	Bubukal	active	2026-08-19 03:16:56.964881	t	LDBB	\N	\N
1	Liceo de Majayjay	Majayjay, Laguna	active	2026-04-28 08:06:21.574976	t	LDMAJ	14.1462923	121.4715953
\.


--
-- Data for Name: chatbot_faqs; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.chatbot_faqs (id, branch_id, question, answer, created_at) FROM stdin;
3	\N	Can I enroll online?	Yes. You can fill out the enrollment form, upload requirements. However, an onsite assessment/interview may still be required.	2026-04-29 01:13:44.709612
5	\N	How much is the tuition fee?	Tuition fees vary by grade level. You can view the full breakdown on the portal after selecting a grade level. Installment plans are available.	2026-04-29 01:14:35.244413
6	\N	Is there an entrance exam?	No, there isn't. But There is an assessment for incoming Kinder and Grade 1 students. For transferees from Grade 2-12, requirements depend on school policy.	2026-04-29 01:16:11.134926
7	\N	How will I know if my enrollment is approved?	You will receive an email notification. You can also check the status on “Track Enrollment” in the portal. Your student number will appear once approved.	2026-04-29 01:17:40.081153
8	\N	Is there a school uniform?	Yes. Students are required to wear the prescribed regular uniform, PE uniform, and Type A uniform.	2026-04-29 01:18:51.542514
9	\N	How can I monitor my child’s grades?	Parents can log in to the parent portal to view grades, attendance, class schedule, and announcements. Records are updated every grading period.	2026-04-29 01:19:37.244891
4	1	How to enroll in Liceo de Majayjay	*Fill Out the Online Enrollment Form\r\nComplete all required details in the official online enrollment form.\r\n*Prepare and Upload the Required Documents\r\nMake sure to submit the following:\r\nReport Card / Form 138 (Original)\r\nPSA Birth Certificate (Photocopy)\r\nCertificate of Good Moral Character\r\n2x2 ID Photo (2 copies)\r\nJHS Diploma or equivalent (for Senior High School applicants only)\r\n*Wait for Registrar’s Validation\r\nYour submitted documents will be reviewed by the Registrar.	2026-04-29 01:14:22.471866
10	\N	Is there a canteen and clinic in school?	Yes. The school has a fully operational canteen and clinic with a licensed nurse on duty during school hours.	2026-04-29 01:22:46.343286
11	\N	What are the requirements for enrollment?	PSA Birth Certificate\r\nReport Card\r\nForm 137\r\nCertificate of Good Moral Character\r\nBaptismal Certificate (for Catholic schools)	2026-04-29 01:23:57.742696
\.


--
-- Data for Name: daily_attendance; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.daily_attendance (id, enrollment_id, subject_id, branch_id, year_id, attendance_date, status, points, recorded_by, created_at) FROM stdin;
\.


--
-- Data for Name: daily_participation; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.daily_participation (id, enrollment_id, subject_id, branch_id, year_id, participation_date, points, recorded_by, created_at) FROM stdin;
\.


--
-- Data for Name: enrollment_books; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.enrollment_books (book_id, enrollment_id, book_name, quantity, created_at) FROM stdin;
\.


--
-- Data for Name: enrollment_documents; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.enrollment_documents (doc_id, enrollment_id, file_name, file_path, uploaded_at, doc_type) FROM stdin;
575	134	Screen_Shot_2026-07-27_at_9.04.45_AM.png	https://res.cloudinary.com/diwiuseil/image/upload/v1787022832/liceo_uploads/enrollment_docs/Screen_Shot_2026-07-27_at_9.04.45_AM_cc2efd.png	2026-08-18 03:13:52.284852	PSA Birth Certificate
576	134	Screen_Shot_2026-07-27_at_9.04.45_AM.png	https://res.cloudinary.com/diwiuseil/image/upload/v1787022833/liceo_uploads/enrollment_docs/Screen_Shot_2026-07-27_at_9.04.45_AM_6cdf9e.png	2026-08-18 03:13:52.284852	Baptismal Certificate
577	134	Screen_Shot_2026-07-27_at_9.04.45_AM.png	https://res.cloudinary.com/diwiuseil/image/upload/v1787022834/liceo_uploads/enrollment_docs/Screen_Shot_2026-07-27_at_9.04.45_AM_3db60f.png	2026-08-18 03:13:52.284852	Form 138
578	134	Screen_Shot_2026-07-27_at_9.04.45_AM.png	https://res.cloudinary.com/diwiuseil/image/upload/v1787022835/liceo_uploads/enrollment_docs/Screen_Shot_2026-07-27_at_9.04.45_AM_392dd5.png	2026-08-18 03:13:52.284852	Good Moral Certificate
579	134	Screen_Shot_2026-07-27_at_9.04.45_AM.png	https://res.cloudinary.com/diwiuseil/image/upload/v1787022836/liceo_uploads/enrollment_docs/Screen_Shot_2026-07-27_at_9.04.45_AM_314837.png	2026-08-18 03:13:52.284852	Form 137
580	135	Screen_Shot_2026-08-18_at_7.26.26_PM.png	https://res.cloudinary.com/diwiuseil/image/upload/v1787104160/liceo_uploads/enrollment_docs/Screen_Shot_2026-08-18_at_7.26.26_PM_8320e9.png	2026-08-19 01:49:19.273147	PSA Birth Certificate
581	136	Module_-_System_Administration_and_Maintenance_-_PRELIM_1.pdf	https://res.cloudinary.com/diwiuseil/image/upload/v1787110431/liceo_uploads/enrollment_docs/Module_-_System_Administration_and_Maintenance_-_PRELIM_1_563d65.pdf	2026-08-19 03:33:50.83709	PSA Birth Certificate
582	496	Parent_Consent_Gmail_2.pdf	https://res.cloudinary.com/diwiuseil/image/upload/v1790680544/liceo_uploads/enrollment_docs/Parent_Consent_Gmail_2_211589.pdf	2026-09-29 11:15:44.208929	PSA Birth Certificate
\.


--
-- Data for Name: enrollment_history; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.enrollment_history (id, enrollment_id, school_year, grade_level, section_name, status) FROM stdin;
\.


--
-- Data for Name: enrollment_uniforms; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.enrollment_uniforms (uniform_id, enrollment_id, uniform_type, size, quantity, created_at) FROM stdin;
\.


--
-- Data for Name: enrollments; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.enrollments (enrollment_id, grade_level, branch_id, status, created_at, user_id, gender, dob, address, contact_number, guardian_contact, previous_school, branch_enrollment_no, section_id, lrn, email, guardian_email, enroll_type, enroll_date, remarks, birthplace, father_contact, father_occupation, mother_contact, mother_occupation, school_year, profile_image, year_id, rejection_reason, rejected_at, academic_status, student_first_name, student_middle_name, student_last_name, father_first_name, father_middle_name, father_last_name, mother_first_name, mother_middle_name, mother_last_name, guardian_first_name, guardian_middle_name, guardian_last_name, father_name, mother_name, curriculum_type, shs_track) FROM stdin;
187	Grade 10	1	pending	2026-09-07 05:25:02.070107	\N	Male	2010-07-18	Brgy Taytay Majayjay Laguna	09564779023	09175814799	Liceo De Majayjay	37	\N	108348715006	\N	\N	Old	2026-09-07	\N	Majayjay, Laguna	09175814799	Farmer	\N	Vendor	\N	\N	18	\N	\N	\N	Joshua Miguel	Esquillo	Hernandez	Anastacio	Urizza	Hernandez	Bernadette	Esquillo	Hernandez	Anastacio	Urizza	Hernandez	\N	\N	basic_ed	\N
134	Nursery	4	completed	2026-08-18 03:13:52.284852	\N	Male	2026-08-18	Majayjay, Laguna	09344811111	09342323232	LDM	1	84	234567890311	melbournebiticon@gmail.com	melbournebiticon@gmail.com	Old	2026-08-18	\N	Majayjay, Laguna	09747482929	Farmer	09858588585	Teacher	\N	https://res.cloudinary.com/diwiuseil/image/upload/v1787102652/liceo_uploads/profiles/arthur_15476d.jpg	10	\N	\N	Excelling	Melbourne	Robel	Biticon	Mel	Argete	Biticon	Brenda	Mia	Robel	Brenda	Robel	Biticon	\N	\N	basic_ed	\N
145	Nursery	10	enrolled	2026-09-01 01:55:19.898529	\N	Male	2006-08-08	Brgy Dulong Silangan Dayap Calauan Laguna	09817400849	09274919137	Acts Computer College	8	85	108256110051	markjohnpascua08@gmail.com	markjohnpascua08@gmail.com	Old	2026-09-01	\N	Dayap Calauan Laguna	\N	\N	\N	\N	\N	\N	26	\N	\N	\N	John Mark	Suliguin	Pascua	\N	\N	\N	\N	\N	\N	Jenifer	Mendoza	Pascua	\N	\N	basic_ed	\N
492	Nursery	1	approved	2026-09-22 08:28:31.959138	\N		\N				\N	337	\N	102465465468	bakagokuto@gmail.com	bakagokuto@gmail.com	Old	2026-09-22	\N	\N	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Melbourne	Robel	Biticon	\N	\N	\N	\N	\N	\N				\N	\N	basic_ed	\N
139	Nursery	4	enrolled	2026-08-19 08:14:18.323359	\N	Male	2026-09-18	Majayjay, Laguna	09344811111	09342323232	LDM	3	84	123042340466	biticonmr1@gmail.com	bakagokuto@gmail.com	Old	2026-08-19	\N	Majayjay, Laguna	\N	\N	\N	\N	\N	\N	10	\N	\N	\N	Meryll	Robel	Biticon	\N	\N	\N	\N	\N	\N	Brenda		Biticon	\N	\N	basic_ed	\N
140	Nursery	4	enrolled	2026-08-19 11:32:30.903372	\N	Female	2009-05-04	Brgy Piit, Majayjay Laguna	09993449118	09206772884	Liceo de Majayjay	4	84	108348140042	biticonmeryll@gmail.com	biticonmeryll@gmail.com	Old	2026-08-19	\N	Sta Cruz	09206772818	Farmer	09206772884	Teacher	\N	\N	10	\N	\N	\N	Meryll Brendalyn	Robel	Biticon	Mel	Argete	Biticon	Brenda	Mia	Robel	Brenda	Mia	Robel	\N	\N	basic_ed	\N
138	Grade 1	10	enrolled	2026-08-19 04:47:50.453418	\N	Male	2021-01-15	144, Kalye Pogi	09215161256	09643845163	Pila Elementary School	3	87	104653187154	bakagoku3@gmail.com	bakagoku3@gmail.com	New	2026-08-19	\N	Pila, Laguna	\N	\N	\N	\N	\N	\N	26	\N	\N	\N	Jake	Co	Flores	\N	\N	\N	\N	\N	\N	Luke	David	Flores	\N	\N	basic_ed	\N
141	Nursery	10	enrolled	2026-08-31 08:14:03.123949	\N	Female	2020-04-30	Malinao	09764887944	09465616464	Liceo De Majaujay	4	85	108465619466	mariasierrajunterial@gmail.com	junterialmaris@gmail.com	Old	2026-08-31	\N	Majayjay	\N	\N	\N	\N	\N	\N	26	\N	\N	\N	Sierra	Cla	Rito	\N	\N	\N	\N	\N	\N	Tess	Cla	Rito	\N	\N	basic_ed	\N
142	Nursery	10	enrolled	2026-08-31 08:14:56.529374	\N	Female	2023-08-31	223 Sa Tabi Lang po	09240120660	09463087376	Calamba School	5	85	105434805276	chelzycada@gmail.com	chelzycada@gmail.com	New	2026-08-31	\N	Calamba City	\N	\N	\N	\N	\N	\N	26	\N	\N	\N	Cooper	Co	Lapsini	\N	\N	\N	\N	\N	\N	Cephi	Co	Lepsir	\N	\N	basic_ed	\N
136	Nursery	10	enrolled	2026-08-19 03:33:50.83709	\N	Male	2026-08-19	Piit	09661234567	09123456789	Liceo	1	85	108348100065	biticonmr@gmail.com	biticonmr@gmail.com	Old	2026-08-19	\N	Majayjay	09123456789	Farmer	09123456789	Teacher	\N	\N	26	\N	\N	\N	Melbourne	Robel	Biticon	Melbourne	Robel	Biticon	Melbourne	Mia	Biticon	Melbourne	Robel	Biticon	\N	\N	basic_ed	\N
143	Nursery	10	enrolled	2026-09-01 01:47:40.11005	\N	Female	2007-09-07	152, Brgy Santa Clara Sur, Pila, Laguna	09346627559	09397654694	L. Bernardo	6	85	234566758558	venice.caparros@gmail.com	lindsaygallardo4@gmail.com	New	2026-09-01	\N	Pila, Laguna	\N	\N	\N	\N	\N	\N	26	\N	\N	\N	Cyrin	Quirabo	Baldemor	\N	\N	\N	\N	\N	\N	Lindsay	Velarde	Gallardo	\N	\N	basic_ed	\N
181	Grade 10	1	enrolled	2026-09-07 04:11:09.111357	\N	Male	2010-09-05	156 MH Del Pilar St Brgy San Miguel Majayjay Laguna	09473815762	09473815762	Liceo De Majayjay	31	125	402556150003	sanjoseestuitamichaelbenedict@gmail.com	\N	Old	2026-05-07	\N	Majayjay, Laguna	09473815762	\N	09473815762	\N	\N	\N	18	\N	\N	\N	Michael Benedict	San Jose	Estuita	Michel Manuel	Portes	Estuita Jr	Maricel	Estanda	San Jose	Maricel	San Jose	Estuita	\N	\N	basic_ed	\N
144	Nursery	10	enrolled	2026-09-01 01:50:59.787354	\N	Male	2006-04-25	Labuin Sta Cruz Laguna	09626288208	09626288208	Bubukal Elementary School	7	85	108437120003	oninnapiza4@gmail.com	oninnapiza5@gmail.com	New	2026-09-01	\N	Sta cruz Laguna	\N	\N	\N	\N	\N	\N	26	\N	\N	\N	Mark Alwayne Niño	Ramirez	Napiza	\N	\N	\N	\N	\N	\N	Eloisa		Napiza	\N	\N	basic_ed	\N
146	Nursery	10	enrolled	2026-09-01 02:02:39.784829	\N	Male	2005-09-21	Malaking Ambling, Magdalena, Laguna	09765256382	09999999999	Laguna laguna	9	85	108341110064	bladimierdiego9@gmail.com	bladimierdiego9@gmail.com	New	2026-09-01	\N	Magdalena, Laguna	09989252534	Construction	09989252534	Seller	\N	\N	26	\N	\N	\N	Bladimier	Hernandez	Diego	BLADIMIER	H.	DIEGO	BLADIMIER	H.	DIEGO	BLADIMIER	H.	DIEGO	\N	\N	basic_ed	\N
147	Nursery	10	approved	2026-09-01 02:03:33.710041	\N	Female	2008-09-01	168	09083686751	09083686751	SCES	10	\N	108444130121	timoteojocazphoebe@gmail.com	timoteoalcela@gmail.com	New	2026-09-01	\N	Tanay Rizal	\N	\N	\N	\N	\N	\N	26	\N	\N	\N	Jocaz Phoebe		Timoteo	\N	\N	\N	\N	\N	\N	Alcela		Timoteo	\N	\N	basic_ed	\N
148	Nursery	10	enrolled	2026-09-01 02:21:34.355311	\N	Male	2023-08-22	33r3	09888888888	09222222222	sssssssss	11	85	222222222222	angeloponce209@gmail.com	angeloponce209@gmail.com	Old	2026-09-01	\N	wewewee	\N	\N	\N	\N	\N	\N	26	\N	\N	\N	msdiw		dwdwdw	\N	\N	\N	\N	\N	\N	sssssssssssssss		eeeeeeeeeeee	\N	\N	basic_ed	\N
149	Nursery	10	enrolled	2026-09-01 03:09:40.409673	\N	Female	2023-01-10	cigaras	09995751481	09036454543	ces	12	85	198987565657	rcyciaronresurreccion841@gmail.com	mercyresurreccion@gmail.com	New	2026-09-01	\N	magdalena,laguna	\N	\N	\N	\N	\N	\N	26	\N	\N	\N	rcy	dizon	resurreccion	\N	\N	\N	\N	\N	\N	mercy		resurreccion	\N	\N	basic_ed	\N
185	Grade 10	1	enrolled	2026-09-07 05:19:12.115922	\N	Male	2011-06-25	P Zamora St Brgy San Miguel Majayjay Laguna	09357054438	09357054438	Liceo De Majayjay	35	125	402556150004	vashneefraginal@gmail.com	\N	Old	2026-09-07	\N	Majayjay, Laguna	\N	\N	09357054438	ATI Agent	\N	\N	18	\N	\N	\N	Kaleigh Vashnee	\N	Fraginal	\N	\N	\N	Karesia	Rosales	Fraginal	Karesia	Rosales	Fraginal	\N	\N	basic_ed	\N
137	Kinder	10	enrolled	2026-08-19 04:32:25.937688	\N	Female	2022-09-01	123, Sa kalye cutie	09874215156	09452456256	Calamba Elementary School	2	86	109316425464	bakagokuto3@gmail.com	milknutdairy@gmail.com	New	2026-08-19	\N	Calamba, Laguna	\N	\N	\N	\N	\N	\N	26	\N	\N	Good Standing	Kc	C	Delicano	\N	\N	\N	\N	\N	\N	John	Lee	Smith	\N	\N	basic_ed	\N
485	Grade 10	1	enrolled	2026-09-15 15:01:18.430693	\N	Male	2010-11-09	Brgy Bukal Majayjay Laguna	\N	\N	Liceo De Majayjay	335	125	402556150006	howardleemodina@gmail.com	\N	Old	2026-05-15	\N	\N	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Howard Lee	Sol	Modina	Arnold	Argañosa	Modina	Maricris	Estella	Sol	Maricris	Estella	Sol	\N	\N	basic_ed	\N
180	Grade 8	1	pending	2026-09-07 04:10:39.472483	\N	Male	2013-08-22	Brgy San Miguel Majayjay, Laguna	09920771310	\N	Liceo De Majayjay	30	\N	484038180009	\N	\N	Old	2026-04-30	\N	Kuwait	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Luigi	Salihon	Espedido	Wenceslao Mateo	\N	Espedido Jr	Laina	Lumarac	Salihon	Laina	Salihon	Espedido	\N	\N	basic_ed	\N
178	Grade 8	1	pending	2026-09-07 04:02:01.295192	\N	Male	2013-02-26	Brgy San Francisco Majayjay Laguna	\N	\N	Liceo De Majayjay	28	\N	402556180012	\N	\N	Old	2026-05-06	\N	\N	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Skyael Peter	Raga	Ramirez	Pedro	Calim	Palentinos Jr	Suzane	Ronabio	Raga	Pedro	Calim	Palentinos Jr	\N	\N	basic_ed	\N
182	Grade 8	1	pending	2026-09-07 05:09:53.221465	\N	Male	2013-03-20	Brgy Ibabang Banga Majayjay, Laguna	09888160207	\N	Liceo De Majayjay	32	\N	108349180097	\N	\N	Old	2026-04-16	\N	\N	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Ethan Mathhew	Sunga	Urquiola	Mark Darwin	Fernandez	Urquiola	Martha Angelie	Yumol	Sunga	Martha Angelie	Sunga	Urquiola	\N	\N	basic_ed	\N
179	Grade 8	1	pending	2026-09-07 04:03:41.272347	\N	Female	2013-05-28	Brgy Origuel Majayjay Laguna	\N	\N	Liceo De Majayjay	29	\N	402556180008	\N	\N	Old	2026-04-20	\N	\N	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Serenity Chloe	Resubal	Ardez	Roger	Puatu	Ardez	Joan Kate	Ardeza	Resubal	Joan Kate	Ardeza	Resubal	\N	\N	basic_ed	\N
135	Nursery	4	enrolled	2026-08-19 01:49:19.273147	\N	Male	2024-07-18	Majayjay, Laguna	09344811111	09342323232	LDM	2	84	123042340404	bakagokuto1@gmail.com	bakagokuto@gmail.com	Old	2026-08-19	\N	Majayjay, Laguna	09747482929	Farmer	09858588585	Teacher	\N	\N	10	\N	\N	\N	Mel Gibson	Robel	Biticon	Mel	Argete	Biticon	Brenda	Mia	Robel	Brenda	Robel	Biticon	\N	\N	basic_ed	\N
171	Grade 10	1	pending	2026-09-07 03:49:32.431729	\N	Male	2011-09-06	105 C Arellano St Brgy San Miguel Majayjay Laguna	\N	09507941144	Liceo De Majayjay	21	\N	402556170014	\N	\N	Old	2026-05-12	\N	Santa Cruz Laguna	09507941144	\N	\N	OFW	\N	\N	18	\N	\N	\N	Aiden Marcus	Brucal	Gregana	Adrian	Coquillo	Gregana	Clariel	Sumage	Brucal	Adrian	Coquillo	Gregana	\N	\N	basic_ed	\N
451	Grade 11	1	enrolled	2026-09-08 08:21:19.866135	\N	Female	2009-12-02	Brgy Bakia Majayjay Laguna	09993910223	\N	Sta Catalina Integrated National High School	301	139	108344150024	joyanngranada@gmail.com	\N	New	2026-09-08	\N	Sta Cruz	\N	Tricycle Driver	\N	OFW	\N	\N	18	\N	\N	\N	Crystal Joy Ann	A	Granada	Jaybee	J	Granada	Cyrille Anne	R	Argete	Cyrille Anne	R	Argete	\N	\N	basic_ed	\N
157	Grade 10	1	pending	2026-09-07 03:28:58.687776	\N	Male	2011-06-11	38 A PUROK 3 YAKAL BRGY MALINAO MAJAYJAY LAGUNA	\N	09694909290	Liceo De Majayjay	7	\N	402647160007	\N	\N	Old	2026-05-19	\N	Manila	\N	\N	09694909290	\N	\N	\N	18	\N	\N	\N	Matteuz Czian	\N	Villanera	\N	\N	\N	Maureen Eve	Salmorin	Villanera	Maureen Eve	\N	Villanera	\N	\N	basic_ed	\N
279	Grade 12-HUMSS	1	enrolled	2026-09-07 08:04:57.912272	\N	Female	2009-08-06	\N	09393549372	09196978622	LICEO DE MAJAYJAY	129	127	108349140187	esquillolieideen@gmail.com	\N	Old	2026-06-04	\N	Sta Cruz, Laguna	09185820893	Farmer	09196978622	Housewife	\N	\N	18	\N	\N	\N	Li Eideen	M	Esquillo	Edwin	R.	Esquillo	Emelita	M.	Esquillo	Emelita	M.	Esquillo	\N	\N	basic_ed	\N
183	Grade 10	1	pending	2026-09-07 05:11:52.207931	\N	Female	2011-04-29	MH Del Pilar St Brgy San Miguel Majayjay Laguna	09294997868	\N	Liceo De Majayjay	33	\N	109437170130	\N	\N	Old	2026-05-07	\N	Santa Cruz Laguna	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Natasha Mei	Fadriquilan	Cube	Nathaniel	Urizza	Cube	Mary Ann	Dela Cruz	Fadriquilan	Mary Ann	Fadriquilan	Cube	\N	\N	basic_ed	\N
496	Nursery	10	enrolled	2026-09-29 11:05:06.769777	\N	Male	2023-09-28	\N	09668855222	\N	\N	21	116	546548667123	biticonmr2@gmail.com	biticonmr2@gmail.com	Old	2026-09-29	\N	Majayjay	\N	\N	\N	\N	\N	https://res.cloudinary.com/diwiuseil/image/upload/v1790680639/liceo_uploads/profiles/791102521_1707806513662980_5003035737954446297_n_1b3ef6.jpg	30	\N	\N	\N	Mark	\N	Biticon	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	basic_ed	\N
155	Grade 9	1	enrolled	2026-09-07 03:24:31.635451	\N	Female	2012-08-28	Brgy Malinao, Majayjay, Laguna	\N	09274350013	Liceo De Majayjay	5	122	108348170155	sioballiah0@gmail.com	\N	Old	2026-05-19	\N	Sta Cruz, Laguna	\N	\N	09274350013	\N	\N	\N	18	\N	\N	\N	Liah	Urizza	Siobal	Ailer	Villanueva	Siobal	Marlene	Coronado	Urizza	Marlene	Urizza	Siobal	\N	\N	basic_ed	\N
163	Grade 10	1	pending	2026-09-07 03:37:00.255165	\N	Female	2011-10-30	Brgy San Miguel Majayjay Laguna	\N	\N	Liceo De Majayjay	13	\N	402556160012	\N	\N	Old	2026-05-18	\N	\N	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Sophia Elaine	Gruezo	Fraginal	Eammond Bryan	Artiaga	Fraginal	Laarni	Lagradante	Gruezo	Laarni	Gruezo	Fraginal	\N	\N	basic_ed	\N
177	Grade 9	1	enrolled	2026-09-07 03:59:44.908025	\N	Female	2012-04-24	166 MH Del Pillar St, San Miguel, Majayjay, Laguna	09512388078	09477991380	Liceo De Majayjay	27	122	108348170052	villaneraailamarie2@gmail.com	\N	Old	2026-05-11	\N	Sta Cruz, Laguna	09477991380	None	\N	\N	\N	\N	18	\N	\N	\N	Aila Marie	Rebenque	Villanera	Mario	Villanueva	Villanera	Ana Luz	Plotilla	Rebenque	Mario	Villanueva	Villanera	\N	\N	basic_ed	\N
291	Grade 12-STEM	1	enrolled	2026-09-07 08:22:32.38782	\N	Female	2009-03-13	A Luna St Majayjay Laguna	09674682395	09956721281	Liceo De Majayjay	141	126	108349140135	marylilyrubian74@gmail.com	\N	Old	2026-09-07	\N	Majayjay, Laguna	09458193506	Carpenter	09956721281	Teacher	\N	\N	18	\N	\N	\N	Mary Lily	S	Rubian	Wenceslan	A	Rubian	Anamarie	A	Rubian	Anamarie	A	Rubian	\N	\N	basic_ed	\N
154	Grade 8	1	pending	2026-09-07 03:23:53.438823	\N	Male	2013-09-06	Purok 1 Brgy Talortor Majayjay, Laguna	09162595353	09162595353	Liceo De Majayjay	4	\N	409288180003	\N	\N	Old	2026-05-18	\N	Sta Cruz, Laguna	09162595353	Engineer	09162595353	Housewife	\N	\N	18	\N	\N	\N	Jaden Ryan	Opinion	Gallardo	Rodolfo	Antolin	Gallardo Jr	Myla	Ceria	Opinion	Myla	Opinion	Gallardo	\N	\N	basic_ed	\N
159	Grade 8	1	pending	2026-09-07 03:32:58.612506	\N	Male	2013-07-07	Brgy Suba Majayjay, Laguna	09338589816	09338589810	Liceo De Majayjay	9	\N	108350018001	\N	\N	Old	2026-05-06	\N	Sta Cruz, Laguna	09399551282	OFW	09338589810	Teacher	\N	\N	18	\N	\N	\N	Rojan Ezekiel	Rubina	Palentinos	Ronnie Bryan	Leobrera	Palentinos	Marah Jane	Espinase	Rubina	Marah Jane	Rubina	Palentinos	\N	\N	basic_ed	\N
170	Grade 8	1	pending	2026-09-07 03:48:46.566849	\N	Male	2012-08-21	Regidor St Brgy Sta Catalina Majayjay, Laguna	09305069242	09454176308	Liceo De Majayjay	20	\N	108349180092	\N	\N	Old	2026-05-12	\N	Majayjay, Laguna	\N	\N	09454176308	\N	\N	\N	18	\N	\N	\N	Vince Edison	\N	Guevarra	\N	\N	\N	Jenalyn	Borines	Guevarra	Jenalyn	Borines	Guevarra	\N	\N	basic_ed	\N
162	Grade 8	1	pending	2026-09-07 03:36:49.592907	\N	Female	2012-12-26	Purok 2F Brgy Bukal Majayjay, Laguna	09970977106	09970977106	Liceo De Majayjay	12	\N	108345180024	\N	\N	Old	2026-05-06	\N	Liliw, Laguna	09970977106	Farmer	09357337409	OFW	\N	\N	18	\N	\N	\N	Althea Lyka	Cortez	Banay	Lucio	Coroza	Banay	Mutya	Balala	Cortez	Lucio	Cortez	Banay	\N	\N	basic_ed	\N
156	Grade 8	1	pending	2026-09-07 03:28:06.654685	\N	Female	2013-07-21	Brgy San Isidro Majayjay, Laguna	09667942890	09667942890	Liceo De Majayjay	6	\N	402518180017	\N	\N	Old	2026-05-18	\N	Majayjay, Laguna	09667942890	OFW	09667942890	Housewife	\N	\N	18	\N	\N	\N	Martina Brielle	Coria	Carillo	Mart Alvin	Lavega	Carillo	Allea Joy	Tabuñar	Coria	Allea Joy	Coria	Carillo	\N	\N	basic_ed	\N
176	Grade 8	1	pending	2026-09-07 03:59:17.692666	\N	Female	2013-08-10	Brgy San Miguel Majayjay, Laguna	09366157338	09366157338	Liceo De Majayjay	26	\N	108348180084	\N	\N	Old	2026-05-07	\N	Sta Cruz, Laguna	09366157338	\N	\N	OFW	\N	\N	18	\N	\N	\N	Aena Paula	Arcenal	Peralta	Joven	Fabicon	Peralta	Judy	Villanera	Peralta	Joven	Fabicon	Peralta	\N	\N	basic_ed	\N
173	Grade 8	1	pending	2026-09-07 03:55:38.246129	\N	Female	2013-05-11	Brgy San Miguel Majayjay, Laguna	\N	09062441579	Liceo De Majayjay	23	\N	402556180016	\N	\N	Old	2026-05-08	\N	\N	\N	Seafarer	09062441579	Teacher	\N	\N	18	\N	\N	\N	Khaela Macayleigh	Arcenal	Trovela	Ruel	Trovela	Trovela	Kharla Rapunzylle	Bernardo	Arcenal	Kharla Rapunzylle	Arcenal	Trovela	\N	\N	basic_ed	\N
174	Grade 9	1	pending	2026-09-07 03:56:05.72575	\N	Male	2012-05-12	Brgy Oobi, Majayjay, Laguna	09624284789	09569445124	Liceo De Majayjay	24	\N	108348170075	\N	\N	Old	2026-04-13	\N	Sta Cruz, Laguna	09624284789	Seaman	09569445124	Housewife	\N	\N	18	\N	\N	\N	Renzo	Gripo	Baeta	Lawrence	Olaso	Baeta	Karen	Formaran	Gripo	Karen	Gripo	Baeta	\N	\N	basic_ed	\N
158	Grade 9	1	pending	2026-09-07 03:29:14.951644	\N	Male	2012-03-23	212 Lopez Jaena St Majayjay, Laguna	09772879775	09772879775	Liceo De Majayjay	8	\N	108349170095	\N	\N	Old	2026-05-14	\N	Sta Rosa, Laguna	\N	\N	09772879775	Freelance	\N	\N	18	\N	\N	\N	Eerin Jade	\N	Dorado	\N	\N	\N	Thelma	Ordoñez	Dorado	Thelma	\N	Dorado	\N	\N	basic_ed	\N
151	Grade 9	1	pending	2026-09-07 03:18:21.009813	\N	Male	2012-04-06	Brgy Suba Majayjay, Laguna	09454339536	09772738792	Liceo De Majayjay	1	\N	136743170351	\N	\N	Old	2026-09-07	\N	Majayjay, Laguna	09568634039	Sales Assistant	09772738792	Supervisor	\N	\N	18	\N	\N	\N	John Louiegi	Palentinos	Rosales	Edlouie	Samson	Rosales	Ruby Ann	Leobrera	Palentinos	Ruby Ann	Palentinos	Rosales	\N	\N	basic_ed	\N
168	Grade 9	1	pending	2026-09-07 03:44:54.810466	\N	Female	2012-06-17	Brgy Pangil Majayjay Laguna	\N	\N	Liceo De Majayjay	18	\N	402556170015	\N	\N	Old	2026-04-27	\N	\N	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Shareefa	Sobreviñas	Hassan	Bin Nijar	Sahidjuan	Hassan	Maria Fe	Ceribo	Sobreviñas	Maria Fe	Sobreviñas	Hassan	\N	\N	basic_ed	\N
160	Grade 10	1	pending	2026-09-07 03:34:07.631405	\N	Female	2010-11-15	A Luna St Ibaba San Francisco Majayjay Laguna	09559428875	09559428875	Liceo De Majayjay	10	\N	108349160066	\N	\N	Old	2026-05-18	\N	Santa Cruz Laguna	09559428875	OFW	09559428875	Housewife	\N	\N	18	\N	\N	\N	Karla Devin	Ceria	Nantes	Wilmar	Pidlaon	Nantes	Generose	Murtado	Ceria	Gewe Rose	Ceria	Nantes	\N	\N	basic_ed	\N
200	Grade 10	1	pending	2026-09-07 06:03:39.948901	\N	Male	2011-02-20	Brgy San Francisco Majayjay Laguna	09668077607	09668077607	Liceo De Majayjay	50	\N	108349160008	\N	\N	Old	2026-09-07	\N	Tiaong Quezon	09668077607	\N	09668077607	Housewife	\N	\N	18	\N	\N	\N	Timothy Daxen	Cruzada	De Lara	Amado	Ceria	De Lana Jr	Catherine	Pangilinan	Cruzada	Catherine	Cruzada	De Lana	\N	\N	basic_ed	\N
432	Grade 11	1	approved	2026-09-08 07:48:32.523595	\N	Female	2010-05-27	Brgy Taytay Majayjay Laguna	09647242492	09095505731	Santa Catalina National High School	282	\N	108347150015	esquillojovelynmay@gmail.com	\N	New	2026-04-13	\N	Majayjay, Laguna	09095505731	Farmer	09095505731	Farmer	\N	\N	18	\N	\N	\N	Jovelyn May	Hernandez	Esquillo	Joel	Francia	Esquillo	Evangeline	Hernandez	Esquillo	Evangeline	Hernandez	Esquillo	\N	\N	basic_ed	\N
166	Grade 10	1	pending	2026-09-07 03:42:59.346066	\N	Female	2011-04-26	Brgy San Francisco Majayjay Laguna	09306934057	09165783572	Liceo De Majayjay	16	\N	402556170013	\N	\N	Old	2026-05-13	\N	Santa Cruz Laguna	09486044260	\N	09165783572	\N	\N	\N	18	\N	\N	\N	Luz Kaylene	Gruezo	Esquillo	Walter	Espedido	Esquillo	Jovanie Ann	Gruezo	Esquillo	Jovanie Ann	Gruezo	Esquillo	\N	\N	basic_ed	\N
460	Grade 11	1	enrolled	2026-09-12 13:46:24.408536	\N	Female	2010-03-12	Brgy San Francisco Majayjay Laguna	09553104730	09553104730	Santa Catalina National High School	310	139	108348150057	maliticmaricel10@gmail.com	\N	New	2026-04-17	\N	Majayjay, Laguna	09168954480	Farmer	09553104730	Call Center	\N	\N	18	\N	\N	\N	Rucelle	Labartini	Malitic	Rudy	Esquivel	Malitic	Maricel	Labartini	Malitic	Maricel	Labartini	Malitic	\N	\N	basic_ed	\N
493	Nursery	10	enrolled	2026-09-22 08:28:36.255136	\N		\N				\N	18	116	102465465468	bakagokuto@gmail.com	bakagokuto@gmail.com	Old	2026-09-22	\N	\N	\N	\N	\N	\N	\N	\N	30	\N	\N	\N	Melbourne	Robel	Biticon	\N	\N	\N	\N	\N	\N				\N	\N	basic_ed	\N
210	Grade 10	1	enrolled	2026-09-07 06:23:44.105807	\N	Male	2011-07-20	Brgy San Miguel Majayjay Laguna	\N	09070396658	Liceo De Majayjay	60	125	108348160179	jacobespedido6@gmail.com	\N	Old	2026-09-07	\N	Majayjay, Laguna	\N	\N	09070396658	Housewife	\N	\N	18	\N	\N	\N	Jacob	Fabie	Espedido	Garylon	Togado	Espedido	Aireen	Eclavea	Fabie	Aireen	Fabie	Espedido	\N	\N	basic_ed	\N
198	Grade 10	1	enrolled	2026-09-07 05:58:42.001425	\N	Female	2011-02-14	MH Del Pilar St Brgy San Miguel Majayjay Laguna	\N	09455624996	Liceo De Majayjay	48	125	108348160027	valerieestebal1@gmail.com	\N	Old	2026-05-04	\N	Majayjay, Laguna	09455624996	Carpenter	\N	Housewife	\N	\N	18	\N	\N	\N	Valerie	Villanueva	Estebal	Rodelio	Espedido	Estebal	Joy	Homeras	Villanueva	Rodelio	Espedido	Estebal	\N	\N	basic_ed	\N
172	Grade 9	1	enrolled	2026-09-07 03:49:54.51613	\N	Male	2011-11-15	A Luna St, Majayjay, Laguna	\N	09285599318	Liceo De Majayjay	22	122	402556170010	rodleeisle10@gmail.com	\N	Old	2026-04-13	\N	Sta Cruz, Laguna	\N	Employee	09285599318	Employee	\N	\N	18	\N	\N	\N	Rodlee Carlisle	Villaraza	Conejares	Roderick	Buensuceso	Conejares	Lyra	Sunga	Villaraza	Lyra	Villaraza	Conejares	\N	\N	basic_ed	\N
209	Grade 8	1	pending	2026-09-07 06:23:06.760601	\N	Male	2013-05-16	Lopez Jaena St Brgy Sta Catalina Majayjay, Laguna	09283911975	09283911975	Liceo De Majayjay	59	\N	108348180151	\N	\N	Old	2026-06-03	\N	Sta Cruz, Laguna	\N	\N	09283911975	Teacher	\N	\N	18	\N	\N	\N	Ken Iñaki	Adornado	Estebal	Jason	Villarosa	Estebal	Imelda	Astoveza	Adornado	Imelda	Adornado	Estebal	\N	\N	basic_ed	\N
206	Grade 8	1	pending	2026-09-07 06:15:47.529658	\N	Male	2013-05-18	Purok 7, Malaliban Brgy Malinao Majayjay,Laguna	09452344934	09954017831	Liceo De Majayjay	56	\N	108348180062	\N	\N	Old	2026-06-04	\N	San Pablo, City	\N	\N	09954017831	Insurance Agent	\N	\N	18	\N	\N	\N	David Jonathan	Barba	Noriel	Jonathan	Arevalo	Noriel	Gina	Coronado	Barba	Gina	Barba	Noriel	\N	\N	basic_ed	\N
197	Grade 8	1	pending	2026-09-07 05:58:19.35791	\N	Male	2013-07-13	Brgy Origuel Majayjay Laguna	\N	\N	Liceo De Majayjay	47	\N	402556180005	\N	\N	Old	2026-06-11	\N	\N	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Jeffenzon John	Llanera	Romulo	Jeffrey	Ramos	Romulo	Lady Ann	Ronabio	Llanera	Lady Ann	Llanera	Romulo	\N	\N	basic_ed	\N
201	Grade 8	1	pending	2026-09-07 06:04:41.517975	\N	Male	2012-08-11	Brgy Munting Kawayan Majayjay Laguna	09159883985	09159883985	Liceo De Majayjay	51	\N	136756170715	\N	\N	Old	2026-06-07	\N	Parañaque, City	09159888985	\N	09159883985	\N	\N	\N	18	\N	\N	\N	Nhiel Kevin	Caberte	So	Kenil	Mendoza	So	Reyna Jean	Delfin	Caberte	Reyna Jean	Caberte	So	\N	\N	basic_ed	\N
204	Grade 8	1	pending	2026-09-07 06:09:09.088529	\N	Female	2013-02-22	Brgy Bukal Majayjay, Laguna	\N	09284315977	Liceo De Majayjay	54	\N	108348180073	\N	\N	Old	2026-06-02	\N	Aklan	\N	Seaman	09284315977	Housewife	\N	\N	18	\N	\N	\N	Fiona Praise	Alvarez	Aguilar	Christian	Mentilla	Aguilar	Rossana	Guanco	Alvarez	Rossana	Alvarez	Aguilar	\N	\N	basic_ed	\N
212	Grade 8	1	pending	2026-09-07 06:26:01.944779	\N	Female	2013-01-26	Purok Tulip Brgy Rizal Majayjay, Laguna	\N	09633366318	Liceo De Majayjay	62	\N	108864180001	\N	\N	Old	2026-06-05	\N	Lucban, Quezon	\N	\N	09633366318	Brgy Treasurer	\N	\N	18	\N	\N	\N	Janine Corine	De Castro	Intal	Johnny	Opeña	Intal	Carina	Zaide	De Castro	Carina	De Castro	Intal	\N	\N	basic_ed	\N
214	Grade 8	1	pending	2026-09-07 06:29:42.529633	\N	Female	2013-06-05	214 F Bluementritt st Brgy Origuel Majayjay Laguna	\N	\N	Liceo De Majayjay	64	\N	402556180015	\N	\N	Old	2026-05-22	\N	\N	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Tiffany Ronice Star	Dollosa	Lanuza	Romnick	Nilooban	Lanuza	Maria Christine Joyce	Gaspar	Dollosa	Maria Christine Joyce	Gaspar	Dollosa	\N	\N	basic_ed	\N
243	Grade 9	1	pending	2026-09-07 07:17:15.977859	\N	Female	2012-02-10	A Luna St Majayjay, Laguna	\N	\N	Liceo De Majayjay	93	\N	402556170008	\N	\N	Old	2026-05-25	\N	Sta Cruz, Laguna	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Maria Stephanie	Arcenal	Gruezo	Mathew Ian	Zornosa	Gruezo	Marife	Aragon	Arcenal	Marife	Gruezo	Gruezo	\N	\N	basic_ed	\N
222	Grade 10	1	pending	2026-09-07 06:41:25.098473	\N	Male	2010-12-29	Brgy Sta Catalina Majayjay Laguna	\N	09750117331	Liceo De Majayjay	72	\N	402556150002	\N	\N	Old	2026-04-28	\N	Santa Cruz Laguna	\N	OFW	09750117331	OFW	\N	\N	18	\N	\N	\N	Dwayne Rafael	Argañosa	Carpio	Bienvenido	Neri	Carpio	Maria Dulce	Miraber	Argañosa	Maria Dulce	Argañosa	Carpio	\N	\N	basic_ed	\N
232	Grade 10	1	pending	2026-09-07 06:56:33.900723	\N	Male	2010-11-27	Brgy San Francisco Majayjay Laguna	09563628750	09563628750	Liceo De Majayjay	82	\N	109811160026	\N	\N	Old	2026-04-24	\N	Majayjay, Laguna	09563628750	Teacher	09563628750	Teacher	\N	\N	18	\N	\N	\N	Lucas Abiel	Guevarra	Dimayuga	Froilan	Rogado	Dimayuga	Mary Grace	Taño	Guevarra	Mary Grace	Guevarra	Dimayuga	\N	\N	basic_ed	\N
225	Grade 10	1	enrolled	2026-09-07 06:47:15.595209	\N	Female	2010-12-24	Brgy San Francisco Majayjay Laguna	\N	\N	Liceo De Majayjay	75	125	108348160022	abiadagianna@gmail.con	\N	Old	2026-09-07	\N	\N	\N	Tricycle Driver	\N	OFW	\N	\N	18	\N	\N	\N	Giana Carla	Evasco	Abiada	Nelvin	Ortega	Abiada	Marillet	Rivera	Evasco	Marillet	Evasco	Abiada	\N	\N	basic_ed	\N
219	Grade 10	1	pending	2026-09-07 06:35:46.456662	\N	Male	2010-09-07	Brgy Malinao Majayjay Laguna	09511038464	\N	Liceo De Majayjay	69	\N	108348160162	\N	\N	Old	2026-04-30	\N	Majayjay, Laguna	\N	MWS	\N	\N	\N	\N	18	\N	\N	\N	Mico	Panado	Ronabio	Jayson	Briteller	Ronabio	Marlyne	Leonim	Panado	Marlyne	Leonim	Panado	\N	\N	basic_ed	\N
234	Grade 10	1	enrolled	2026-09-07 07:03:49.421966	\N	Female	2011-02-22	Brgy San Francisco Majayjay Laguna	09218056114	09218056114	Liceo De Majayjay	84	125	108347160012	kiziaarnuco@gmail.com	\N	Old	2026-04-20	\N	\N	09071024953	Farmer	09218056114	Housewife	\N	\N	18	\N	\N	\N	Kizia Eleija	Hapin	Arnuco	Reynaldo	Guera	Arnuco Jr	Maricris	Lagata	Hapin	Maricris	Hapin	Arnuco	\N	\N	basic_ed	\N
242	Grade 10	1	enrolled	2026-09-07 07:16:10.33432	\N	Male	2011-08-10	Brgy Suba Majayjay Laguna	09667363774	09667363774	Liceo De Majayjay	92	125	402556160011	reniellebernardo11@gmail.com	\N	Old	2026-09-07	\N	San Pablo City	\N	\N	09667363774	Government Employee	\N	\N	18	\N	\N	\N	Renielle	Mondejar	Bernardo	Raphael Jay	Agustin	Bernardo	Leni	Danila	Mondejar	Leni	Mondejar	Bernardo	\N	\N	basic_ed	\N
216	Grade 10	1	enrolled	2026-09-07 06:31:32.127891	\N	Male	2011-05-14	Brgy Villa Nogales Majayjay Laguna	09694005665	09473372630	Liceo De Majayjay	66	125	402556160007	rhonjacobadelsol@gmail.com	\N	Old	2026-04-30	\N	Majayjay, Laguna	09081562900	Sales Representatives	09473372630	Senior Network Supervisor	\N	\N	18	\N	\N	\N	Rhon Jacob	Alvareda	Del Sol	Norciolito	Peñaflor	Del Sol	Jennifer	San Diego	Alvareda	Jennifer	Alvareda	Del Sol	\N	\N	basic_ed	\N
228	Grade 10	1	enrolled	2026-09-07 06:51:18.968629	\N	Male	2011-10-10	Brgy Malinao Majayjay, Laguna	09760055249	09761379255	Liceo De Majayjay	78	125	402556160008	theonlykurtyzy@gmail.com	theonlykurtyzy@gmail.com	New	2026-04-27	\N	Majayjay, Laguna	09771945348	Seaferer	09761379255	Teacher	\N	\N	18	\N	\N	\N	Kurt Jericho Raniel	Cerez	Fortuna	Jerryco	Llorente	Fortuna	Rozinni	Eñar	Cerez	Rozinni	Cerez	Fortuna	\N	\N	basic_ed	\N
153	Grade 10	1	enrolled	2026-09-07 03:19:55.342251	\N	Female	2011-05-03	Brgy Pangil Majayjay Laguna	\N	09278058300	Liceo De Majayjay	3	125	108348170160	sereenakhloe@gmail.com	\N	Old	2026-05-18	\N	Majayjay, Laguna	\N	\N	09278058300	Teacher	\N	\N	18	\N	\N	\N	Sereena Khloe	Zornosa	Hernandez	Ser Ludwig	Rafael	Hernandez	Katherine	Visca	Zornosa	Katherine	Zornosa	Hernandez	\N	\N	basic_ed	\N
223	Grade 8	1	pending	2026-09-07 06:42:26.415009	\N	Male	2011-08-25	Brgy Coralao Majayjay, Laguna	09216710557	09959534690	Liceo De Majayjay	73	\N	402556180010	\N	\N	Old	2026-06-05	\N	Dasmariñas, City	09319822982	Brgy Kagawad	09959534690	Tech Support	\N	\N	18	\N	\N	\N	Joseph Arkin	Caldo	Codera	Joel	Palaña	Codera	Arlene	Gatbat	Caldo	Arlene	Caldo	Codera	\N	\N	basic_ed	\N
227	Grade 8	1	pending	2026-09-07 06:50:55.151117	\N	Male	2012-12-07	A Luna St Majayjay, Laguna	09273490692	09273490692	Liceo De Majayjay	77	\N	108349180008	\N	\N	Old	2026-06-08	\N	Sta Cruz, Laguna	09196637450	OFW	09273490692	OFW	\N	\N	18	\N	\N	\N	Gabrielle Gift	Montemor	Dorado	Archie Mor Bryan	Urcia	Dorado	Jennifer	Guera	Montemor	Jennifer	Montemor	Dorado	\N	\N	basic_ed	\N
220	Grade 8	1	pending	2026-09-07 06:36:04.707252	\N	Female	2013-06-25	Brgy Coralao Majayjay, Laguna	\N	09503476590	Liceo De Majayjay	70	\N	108348180075	\N	\N	Old	2026-05-27	\N	\N	09503476590	\N	\N	\N	\N	\N	18	\N	\N	\N	Khaye Cathlyn	Bagan	Arada	Melberth	Adan	Arada	Maria Teresa	Dacilo	Bagan	Melberth	Adan	Arada	\N	\N	basic_ed	\N
217	Grade 8	1	pending	2026-09-07 06:31:56.532347	\N	Female	2013-11-12	Brgy San Miguel Majayjay Laguna	\N	\N	Liceo De Majayjay	67	\N	108348180038	\N	\N	Old	2026-06-01	\N	\N	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Aizelle Anne	Clado	Lorida	Alexander	Arcenal	Lorida	Celedonia	Rabino	Clado	\N	\N	\N	\N	\N	basic_ed	\N
231	Grade 8	1	pending	2026-09-07 06:56:19.262107	\N	Female	2013-06-14	062 Brgy Pangil Majayjay, Laguna	09216754544	09056397940	Liceo De Majayjay	81	\N	401407180016	\N	\N	Old	2026-06-05	\N	STDM, Bulacan	09216754544	Seaman	09056397940	Rad Tech	\N	\N	18	\N	\N	\N	Alexandria	Collado	Sobreviñas	Mark Joseph	Ciriibo	Sobreviñas	Margareth	\N	Collado	Mark Joseph	\N	Sobreviñas	\N	\N	basic_ed	\N
240	Grade 9	1	pending	2026-09-07 07:13:50.589063	\N	Female	2012-01-01	Jacinto St Sta Catalina Majayjay, Laguna	09945314961	09311262334	Liceo De Majayjay	90	\N	108349170085	\N	\N	Old	2026-06-01	\N	Sta Cruz, Laguna	09282291081	Farmer	09311262334	Brgy Kagawad	\N	\N	18	\N	\N	\N	Maria Arissa Eugene	Yupacina	Argañosa	Rhomnick	Arcenal	Argañosa	Gracia	Pasko	Yupacina	Gracia	Yupacina	Argañosa	\N	\N	basic_ed	\N
238	Grade 10	1	enrolled	2026-09-07 07:10:12.399222	\N	Male	2011-06-20	P Zamora St Brgy San Miguel Majayjay Laguna	09567980066	09567980066	Liceo De Majayjay	88	125	402555160052	thirdymalait2006@gmail.com	\N	Old	2026-09-07	\N	Santa Cruz Laguna	\N	Technician	09567980066	Housewife	\N	\N	18	\N	\N	\N	Ruben	Trovela	Malait III	Ruben	Daluz	Malait Jr	Mary Ann	Gruezo	Trovela	Mary Ann	Trovela	Malait	\N	\N	basic_ed	\N
494	Nursery	10	enrolled	2026-09-22 12:40:29.720255	\N		2023-09-21	Majayjay, Laguna		09473372630	\N	19	116	402556180088	imbonpogi@gmail.com	imbonpogi@gmail.com	Old	2026-09-22	\N	Zapote Las Piñas City	\N	\N	\N	\N	\N	\N	30	\N	\N	\N	Loyd		Sarapat	\N	\N	\N	Junterial	Maria	Sierra				\N	\N	basic_ed	\N
239	Grade 10	1	enrolled	2026-09-07 07:13:27.144867	\N	Female	2011-09-30	Brgy Oobi Majayjay Laguna	09157738283	\N	Liceo De Majayjay	89	125	402556160015	medinabarlleygrace@gmail.com	\N	Old	2026-09-07	\N	Santa Cruz Laguna	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Barlley Grace	Padua	Medina	Rafael	Obiniana	Medina II	Cleotilde	Quinto	Padua	Cleotilde	Padua	Medina	\N	\N	basic_ed	\N
431	Grade 11	1	enrolled	2026-09-08 07:47:45.215384	\N	Female	2010-06-19	\N	09633488371	09056454681	Sta Catalina Integrated National High School	281	139	108349150095	comendadorelaiza8@gmail.com	\N	New	2026-09-08	\N	Majayjay, Laguna	09364644544	Driver	09056454681	Teacher	\N	\N	18	\N	\N	\N	Elaiza Rain	G	Comendador	Richard	P	Comendador	Ela	G	Comendador	Ela	G	Comendador	\N	\N	basic_ed	\N
167	Grade 9	1	enrolled	2026-09-07 03:43:09.15999	\N	Male	2011-12-09	J Cailles St, Majayjay, Laguna	\N	\N	Liceo De Majayjay	17	122	108348170067	adorarosales124@gmail.com	\N	Old	2026-05-11	\N	Sta Cruz, Laguna	\N	Business Owner	\N	OFW	\N	\N	18	\N	\N	\N	Sebastian Sky	Sarip	Rosales	Ralph Gregor	Arive	Rosales	Jonnaira	Angara	Sarip	Adora	Sarip	Rosales	\N	\N	basic_ed	\N
237	Grade 9	1	enrolled	2026-09-07 07:09:19.353576	\N	Male	2012-01-17	Purok 4 Antipolo Malinao Majayjay, Laguna	\N	09122127206	Liceo De Majayjay	87	122	108348170080	janwellpontiveros@gmail.com	\N	Old	2026-06-04	\N	Majayjay, Laguna	\N	Technician	09122127206	Housewife	\N	\N	18	\N	\N	\N	Janwell	Dorado	Pontiveros	Noel	Mendoza	Potiveros	Guillerma	Dela Cruz	Dorado	Guillerma	Dorado	Pontiveros	\N	\N	basic_ed	\N
268	Grade 10	1	pending	2026-09-07 07:51:59.979315	\N	Male	2011-04-17	Brgy San Miguel Majayjay Laguna	09923707279	09923707279	Liceo De Majayjay	118	\N	485615150044	\N	\N	Old	2026-06-05	\N	Majayjay, Laguna	09923707176	\N	09923707279	\N	\N	\N	18	\N	\N	\N	Kieth Dave	Eñar	Dagami	Rodolfo	\N	Dagami Jr	Eden	\N	Eñar	Eden	\N	Eñar	\N	\N	basic_ed	\N
259	Grade 10	1	pending	2026-09-07 07:42:03.462968	\N	Male	2011-06-28	Brgy Oobi Majayjay Laguna	09366544906	09366544906	Liceo De Majayjay	109	\N	108349160010	\N	\N	Old	2026-09-07	\N	Tanay Rizal	09366544906	\N	09366544906	\N	\N	\N	18	\N	\N	\N	Enz	Lumansang	Novelo	Kenny	Montino	Novelo	Hanzel	Mariano	Lumansang	Hanzel	Lumansang	Novelo	\N	\N	basic_ed	\N
251	Grade 10	1	pending	2026-09-07 07:28:57.131786	\N	Male	2010-11-21	Brgy Oobi Majayjay Laguna	09657033359	09953309505	Liceo De Majayjay	101	\N	108348160038	\N	\N	Old	2026-09-07	\N	Santa Cruz Laguna	09953309505	Farmer	\N	Housewife	\N	\N	18	\N	\N	\N	John Kristoff	Oriña	Prialde	Ghene Christian	Biticon	Prialde	Ladylyn	Brosas	Oriña	Ghene Christian	Biticon	Prialde	\N	\N	basic_ed	\N
256	Grade 10	1	pending	2026-09-07 07:36:14.56414	\N	Male	2010-12-02	Brgy Piit Majayjay Laguna	\N	\N	Liceo De Majayjay	106	\N	402556150007	\N	\N	Old	2026-09-07	\N	Cardona Rizal	\N	Technician	\N	Housewife	\N	\N	18	\N	\N	\N	Lyle Kendrick	Dorneo	Sto Domingo	Arnel	Montilola	Sto Domingo	Analyn	Arce	Dorneo	Analyn	Dorneo	Sto Domingo	\N	\N	basic_ed	\N
253	Grade 10	1	pending	2026-09-07 07:31:46.982154	\N	Male	2010-12-12	Brgy Oobi Majayjay Laguna	09855411381	\N	Liceo De Majayjay	103	\N	\N	\N	\N	Old	2026-05-25	\N	Santa Cruz Laguna	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Sean Deniel	Eria	Togado	Enrico	Oriña	Togado	Jonelyn	Gripo	Eriga	Jonelyn	Eriga	Togado	\N	\N	basic_ed	\N
265	Grade 10	1	pending	2026-09-07 07:47:03.93901	\N	Female	2011-06-22	Brgy Santa Catalina Majayjay Laguna	09354044273	09354044273	Liceo De Majayjay	115	\N	108349160064	\N	\N	Old	2026-06-08	\N	\N	\N	\N	09354044273	\N	\N	\N	18	\N	\N	\N	Cathlyn Hennesy	\N	Cordon	\N	\N	\N	Catherine	Villarosa	Cordon	Catherine	Villarosa	Cordon	\N	\N	basic_ed	\N
247	Grade 10	1	pending	2026-09-07 07:24:06.742939	\N	Female	2010-10-12	Brgy Ibabang Banga Majayjay Laguna	09363932624	09363932624	Liceo De Majayjay	97	\N	108349160041	\N	\N	Old	2026-06-03	\N	Santa Cruz Laguna	\N	\N	09363932624	Housewife	\N	\N	18	\N	\N	\N	Shyanna Rose	Madriaga	Gruezo	Noel	Nombrado	Gruezo	April Angelica	Dacanay	Madriaga	April Angelica	Madriaga	Gruezo	\N	\N	basic_ed	\N
486	Grade 10	1	pending	2026-09-15 15:34:37.038144	\N	Female	2011-09-06	Brgy San Miguel Majayjay Laguna			Liceo De Majayjay	336	\N	402556160014	\N	\N	Old	2026-05-15	\N	\N	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Princess Caylie	Clado	Jovilla	Ceazar	Arasa	Jovilla	Precious Anne	Esquillo	Clado	Precious Anne	Clado	Jovilla	\N	\N	basic_ed	\N
175	Grade 10	1	enrolled	2026-09-07 03:56:20.125103	\N	Female	2011-02-24	105 C Arellano St Brgy San Miguel Majayjay Laguna	09163491207	09163491207	Liceo De Majayjay	25	125	485563150196	shilohreesejavellana224@gmail.com	\N	Old	2026-05-12	\N	Majayjay, Laguna	\N	\N	09163491207	Fraud Risk Analyst	\N	\N	18	\N	\N	\N	Shiloh Reese	Gregana	Javellana	Ralphy	Morial	Javellana	Shella	Coquillo	Gregana	Shella	Gregana	Javellana	\N	\N	basic_ed	\N
249	Grade 9	1	pending	2026-09-07 07:27:10.316406	\N	Male	2011-09-04	Burgos St Brgy Gagalot Majayjay, Laguna	09564282618	09564282618	Liceo De Majayjay	99	\N	136665170007	\N	\N	Old	2026-06-07	\N	Pasig, City	\N	\N	09564282618	Freelancer	\N	\N	18	\N	\N	\N	Kazriel	Miranda	De Guzman	Dwight Kenneth	Licerio	De Guzman	Melisa	Melendrez	Miranda	Melisa	Miranda	De Guzman	\N	\N	basic_ed	\N
271	Grade 9	1	pending	2026-09-07 07:56:46.341479	\N	Male	2012-01-21	Purok 2, Talortor Majayjay, Laguna	09614175092	09064624182	Liceo De Majayjay	121	\N	402556170011	\N	\N	Old	2026-06-03	\N	Sta Cruz, Laguna	09064624182	Farmet	09489094815	\N	\N	\N	18	\N	\N	\N	Rafael Shane	Bukid	Hierras	Michele	Orillaza	Hierras	Krystel	Perez	Bukid	Michele	Bukid	Hierras	\N	\N	basic_ed	\N
246	Grade 9	1	pending	2026-09-07 07:22:40.62151	\N	Male	2011-12-10	41 P Zamora St Majayjay, Laguna	09777498432	09777498432	Liceo De Majayjay	96	\N	402556170004	\N	\N	Old	2026-05-21	\N	Sta Cruz, Laguna	09664634433	Call center	09777498432	Online Seller	\N	\N	18	\N	\N	\N	Van Kian	\N	Katigbak	Eriberto Arvin	\N	Soriano	Emevenciana	Villarante	Katigbak	Emevenciana	\N	Katigbak	\N	\N	basic_ed	\N
257	Grade 9	1	pending	2026-09-07 07:39:18.593835	\N	Male	2011-10-01	Brgy Panglan Majayjay, Laguna	\N	09338515190	Liceo De Majayjay	107	\N	108348170028	\N	\N	Old	2026-06-03	\N	Sta Cruz, Laguna	\N	Seaman	09338515190	\N	\N	\N	18	\N	\N	\N	Aaron Stephan	Arejola	Palentinos	Ronnie Rex	Leobrera	Palentinos	Annielou	Espedido	Arejola	Annielou	Arejola	Palentinos	\N	\N	basic_ed	\N
263	Grade 10	1	enrolled	2026-09-07 07:44:52.105658	\N	Female	2011-05-30	Brgy Gagalot Majayjay Laguna	09929570414	\N	Liceo De Majayjay	113	125	402683160023	briannajocellemiranda@gmail.com	\N	Old	2026-09-07	\N	Mandaluyong	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Brianna Jocelle	Rafael	Miranda	Joseph	\N	Miranda	Eliza May	\N	Miranda	\N	\N	\N	\N	\N	basic_ed	\N
266	Grade 9	1	pending	2026-09-07 07:47:32.615594	\N	Male	2011-09-24	Antonio Luna St Majayjay, Laguna	09760489321	09760489321	Liceo De Majayjay	116	\N	402556170012	\N	\N	Old	2026-06-01	\N	Muntinlupa, City	\N	\N	09760489321	Team Lead	\N	\N	18	\N	\N	\N	Juan Joseph	Cobrado	Santos	Steve	Melo	Santos	Mari Rose	De Torres	Cobrado	Mari Rose	Cobrado	Santos	\N	\N	basic_ed	\N
495	Grade 11	10	approved	2026-09-22 22:30:28.615157	\N		\N				\N	20	\N	546432135486	\N	\N	Old	2026-09-22	\N	\N	\N	\N	\N	\N	\N	\N	30	\N	\N	\N	gibson		biticon	\N	\N	\N	\N	\N	\N				\N	\N	basic_ed	Math
252	Grade 9	1	pending	2026-09-07 07:31:44.658639	\N	Male	2012-04-18	Brgy San Miguel Majayjay Laguna	09514226207	09514226207	Liceo De Majayjay	102	\N	108348170159	\N	\N	Old	2026-05-29	\N	Sta Cruz, Laguna	\N	\N	09514226207	Farmer	\N	\N	18	\N	\N	\N	Joel	Zorilla	Villanera	Jonathan	Merania	Villanera	Hazel	Tracina	Zorilla	Hazel	Zorilla	Zorilla	\N	\N	basic_ed	\N
398	Grade 11	1	enrolled	2026-09-08 06:43:31.761796	\N	Male	2010-01-03	A Luna St Brgy Ibabang San Francisco Majayjay, Laguna	09555294031	09555294031	SCINHS	248	139	\N	johndonsales167@gmail.com	\N	New	2026-04-14	\N	Majayjay, Laguna	09353335090	Tricycle Driver	09555294031	Housewife	\N	\N	18	\N	\N	\N	Rafael John	G	Doñasales	Ruben	R.	Doñasales	Trisha Jozarah	G.	Doñasales	Trisha Jozarah	G.	Doñasales	\N	\N	basic_ed	\N
260	Grade 9	1	pending	2026-09-07 07:42:40.342531	\N	Female	2011-11-16	Brgy Suba Majayjay Laguna	09658326517	\N	Liceo De Majayjay	110	\N	108341170072	\N	\N	Old	2026-05-26	\N	Magdalena, Laguna	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Kaithlyn Joy	Gan	Mendoza	Jade Francis	Padolina	Mendoza	Maricris	Jovellano	Gan	Maricris	Gan	Mendoza	\N	\N	basic_ed	\N
270	Grade 9	1	enrolled	2026-09-07 07:52:44.706381	\N	Female	2012-04-25	Purok 2 Brgy Piit	09321031605	09321031605	\N	120	122	\N	dollyrubian2@gmail.com	\N	Old	2026-06-03	\N	\N	\N	\N	09321031605	\N	\N	\N	18	\N	\N	\N	Alexis Julia	Rubian	Sarmiento	\N	\N	\N	Dolores	\N	Rubian	Dolores	\N	Rubian	\N	\N	basic_ed	\N
255	Grade 9	1	enrolled	2026-09-07 07:36:08.453992	\N	Female	2012-10-10	181 P Zamora St Majayjay, Laguna	09959022527	09959022527	Liceo De Majayjay	105	122	402556170006	angeliqueysha10@gmail.com	\N	Old	2026-05-29	\N	Majayjay, Laguna	\N	\N	09959022527	Store Crew	\N	\N	18	\N	\N	\N	Ysha Angelique	\N	Trovela	\N	\N	\N	Kristle	\N	Trovela	Kristle	\N	Trovela	\N	\N	basic_ed	\N
262	Grade 9	1	enrolled	2026-09-07 07:43:28.578342	\N	Female	2012-02-12	Brgy Villa Nogales Majayjay Laguna	\N	\N	Liceo De Majayjay	112	122	108348170139	grencioalthea@gmail.com	\N	Old	2026-06-03	\N	\N	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Althea	Villanueva	Grencio	Jhigor	Resubal	Grencio	Kim	Cerez	Villanueva	Kim	Villanueva	Grencio	\N	\N	basic_ed	\N
224	Grade 12-STEM	1	enrolled	2026-09-07 06:43:56.538393	\N	Female	2009-10-03	119 Lopez Jaena St Brgy Sta Catalina, Majayjay, Laguna	09858489486	09635535866	LICEO DE MAJAYJAY	74	126	108349140190	millenaalexandra2@gmail.com	\N	Old	2026-04-30	\N	Majayjay, Laguna	09121273190	\N	09635535866	\N	\N	\N	18	\N	\N	\N	Aifa Alexa	F	Millena	Alexander	\N	Millena	Estela	\N	Millena	Estella	\N	Millena	\N	\N	basic_ed	\N
190	Grade 12-STEM	1	enrolled	2026-09-07 05:36:40.299971	\N	Female	2009-06-11	411 Bonifacio St Brgy San Miguel	09297634078	\N	LICEO DE MAJAYJAY	40	126	\N	aguilarayeshamae02@gmail.com	\N	Old	2026-05-18	\N	Majayjay, Laguna	\N	Seaman	\N	Housewife	\N	\N	18	\N	\N	\N	Ayesha	\N	Aguilar	Bryan	Mentilla	Aguilar	Christine	Mercado	Aguilar	Christine	Mercado	Aguilar	\N	\N	basic_ed	\N
287	Grade 10	1	pending	2026-09-07 08:11:47.568665	\N	Male	2011-08-17	Brgy Bukal Majayjay Laguna	\N	\N	Liceo De Majayjay	137	\N	108345160003	\N	\N	Old	2026-09-07	\N	\N	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Justine	Tinaco	Brosas	Cristobal	Perolina	Brosas	Mary Jane	Libres	Tinaco	Mary Jane	Tinaco	Brosas	\N	\N	basic_ed	\N
288	Grade 10	1	pending	2026-09-07 08:12:33.221943	\N	Male	2010-11-22	Barcelonita Cabusao Camarines Sur	\N	\N	Liceo De Majayjay	138	\N	108345160005	\N	\N	Old	2026-09-07	\N	\N	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Manuel	Zuela	Cortez Jr	Manuel	Balala	Cortez	Francia	Peña	Zuela	Francia	Zuela	Cortez	\N	\N	basic_ed	\N
281	Grade 10	1	pending	2026-09-07 08:06:49.748215	\N	Male	2011-05-20	Blumentritt St Bragy Origuel Majayjay Laguna	\N	09189598974	Liceo De Majayjay	131	\N	402555160053	\N	\N	Old	2026-05-22	\N	\N	\N	\N	09189598974	\N	\N	\N	18	\N	\N	\N	Timothy Royce	Dollosa	Lanuza	Romnick	Nilooban	Lanuza	Maria Christine Joyce	Gaspar	Dollosa	Christine Joyce	Dollosa	Lanuza	\N	\N	basic_ed	\N
286	Grade 10	1	pending	2026-09-07 08:10:53.958321	\N	Male	2011-06-13	Brgy Bitaoy Majayjay Laguna	\N	\N	Liceo De Majayjay	136	\N	402769160024	\N	\N	Old	2026-06-03	\N	\N	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	MC Yohann	Noriel	Vito	Eddie	Arquiza	Vito	Michelle	Bojeador	Noriel	Michelle	Noriel	Vito	\N	\N	basic_ed	\N
276	Grade 10	1	pending	2026-09-07 08:02:31.411144	\N	Female	2011-01-25	A Luna St Majayjay Laguna	09106910751	09106910751	Liceo De Majayjay	126	\N	108348160029	\N	\N	Old	2026-05-04	\N	Santa Cruz Laguna	\N	Carpenter	09106910751	\N	\N	\N	18	\N	\N	\N	Ezra Shiekina	Dacles	Joven	Roger	Sebuc	Joven	Michaela	Argañosa	Dacles	Michaela	Dacles	Joven	\N	\N	basic_ed	\N
283	Grade 10	1	pending	2026-09-07 08:08:16.62671	\N	Female	2011-07-31	Brgy Suba Majayjay Laguna	09754066893	\N	Liceo De Majayjay	133	\N	108350160023	\N	\N	Old	2026-09-07	\N	\N	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Vheezell	Mendoza	Patron	Jayvee	Calapis	Patron	Jeizelle	Padolina	Mendoza	Jeizelle	Mendoza	Patron	\N	\N	basic_ed	\N
428	Grade 11	1	enrolled	2026-09-08 07:39:37.722428	\N	Female	2010-05-20	P Origuel Street , Majayjay, Laguna	\N	09176737148	LICEO DE MAJAYJAY	278	139	\N	besoloren0520@gmail.com	besoloren0520@gmail.com	New	2026-05-11	\N	Majayjay, Laguna	\N	\N	09176737148	\N	\N	\N	18	\N	\N	\N	Loren Mae	E	Beso	Danilo	\N	Beso	Jocelyn	\N	Esquillo	Jocelyn	\N	Esquillo	\N	\N	basic_ed	\N
487	Nursery	10	enrolled	2026-09-18 02:55:39.049819	\N		2023-09-17				\N	13	116	326549494848	bakagokuto@gmail.comgmail.com	\N	Old	2026-09-18	\N	\N	\N	\N	\N	\N	\N	\N	30	\N	\N	\N	Melbourne		Biticonnn	\N	\N	\N	\N	\N	\N				\N	\N	basic_ed	\N
274	Grade 10	1	enrolled	2026-09-07 07:59:43.223859	\N	Male	2011-08-07	Brgy Gagalot Majayjay Laguna	09382268049	\N	Liceo De Majayjay	124	125	108346160024	markmjbojabe@gmail.com	\N	Old	2026-05-25	\N	Majayjay, Laguna	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Mark Jhian	Clado	Bojabe	Evangel	Ceribo	Bojabe	Jennifer	Bojeador	Clado	Jennifer	Clado	Bojabe	\N	\N	basic_ed	\N
278	Grade 10	1	enrolled	2026-09-07 08:04:26.881709	\N	Female	2010-10-26	A Luna St Majayjay Laguna	09106910751	\N	Liceo De Majayjay	128	125	425812160008	princessannetaguiam@gmail.com	\N	Old	2026-05-21	\N	\N	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Princess Anne	Dacles	Taguim	Roberto	Pabia	Taguim	Miro Ann	\N	Dacles	Miro Ann	Dacles	Taguim	\N	\N	basic_ed	\N
285	Grade 9	1	pending	2026-09-07 08:10:07.81294	\N	Male	2011-12-09	Brgy San Francisco Majayjay, Laguna	09678071600	09176852407	Liceo De Majayjay	135	\N	402518170002	\N	\N	Old	2026-05-20	\N	Majayjay, Laguna	09992200482	Collection	09176852407	Teacher	\N	\N	18	\N	\N	\N	Adam Gabriel	Cornista	Arceta	Jerome	Eñar	Arceta	Maria Ann Criselda	Brioso	Cornista	Maria Ann Criselda	Cornista	Arceta	\N	\N	basic_ed	\N
280	Grade 9	1	pending	2026-09-07 08:06:27.74379	\N	Male	2011-09-27	Brgy Bakia Majayjay, Laguna	\N	09662232883	Liceo De Majayjay	130	\N	108344170004	\N	\N	Old	2026-06-07	\N	Majayjay, Laguna	09105211097	Farmer	09662232883	Housewife	\N	\N	18	\N	\N	\N	Mark Edward	Mercurio	Guiang	Edward	Dumlao	Guiang	Minerva	Rosende	Mercurio	Minerva	Mercurio	Guiang	\N	\N	basic_ed	\N
446	Grade 11	1	enrolled	2026-09-08 08:10:54.362155	\N	Female	2010-04-21	Brgy Ba	09858538974	09308934105	Sta Catalina National High School Extension	296	139	108344150032	jullianajuanillo@gmail.com	\N	New	2026-04-15	\N	Luisiana, Laguna	09308743946	Utility Staff	09308934105	Staff	\N	\N	18	\N	\N	\N	Julliana	S	Juanillo	Enrique	C.	Juanillo	Maria Nanette	S.	Juanillo	Maria Nanette	S.	Juanillo	\N	\N	basic_ed	\N
284	Grade 10	1	pending	2026-09-07 08:09:08.374739	\N	Male	2011-04-29	Brgy Bukal Majayjay Laguna	\N	\N	Liceo De Majayjay	134	\N	108345160001	\N	\N	Old	2026-06-05	\N	\N	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Marvin	Brosas	Aniciete	Limuel	Gagarin	Anciete	Venus	Perolina	Brosas	Venus	Brosas	Anciete	\N	\N	basic_ed	\N
277	Grade 9	1	enrolled	2026-09-07 08:03:40.103136	\N	Female	2012-01-13	Brgy Burol Majayjay Laguna	09627679296	09196978662	Liceo De Majayjay	127	122	108349170084	esquillojadeen@gmail.com	\N	Old	2026-06-04	\N	Sta Cruz, Laguna	09185820893	Farmer	09196978662	Housewife	\N	\N	18	\N	\N	\N	Jadeen Elisse	Meraber	Esquillo	Edwin	Rias	Esquillo	Emelita	Rubiales	Merabera	Emilita	Merabera	Esquillo	\N	\N	basic_ed	\N
213	Grade 12-STEM	1	enrolled	2026-09-07 06:28:19.813586	\N	Male	2009-04-03	Brgy Sta Catalina, Majayjay, Laguna	09264890432	09855413704	LICEO DE MAJAYJAY	63	126	108348914124	johndhenver34@gmail.com	\N	Old	2026-05-05	\N	Majayjay, Laguna	\N	OFW	09855413704	Cashier	\N	\N	18	\N	\N	\N	John Denver	B	Sueña	Jeffry	O.	Sueña	Jennalyn	B.	Sueña	Jennalyn	B	Sueña	\N	\N	basic_ed	\N
301	Grade 12-STEM	1	enrolled	2026-09-07 08:33:14.469495	\N	\N	2006-10-15	\N	\N	\N	LICEO DE MAJAYJAY	151	126	\N	estacajohaira@gmail.com	\N	Old	2026-06-05	\N	Atimonan, Quezon	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Johaira Shonette	E	Cajayon	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	basic_ed	\N
325	Grade 1	1	enrolled	2026-09-08 04:20:02.887812	\N	Male	2020-11-09	Brgy San Francisco Majayjay Laguna	09914213036	09914213036	\N	175	131	\N	elaine.badiola@deped.gov.ph	\N	Old	2026-05-18	\N	Tacloban City	09914213036	BPO	09914213036	Teacher	\N	\N	18	\N	\N	\N	Vince Ezekiel	A	Badiola	Miles	A	Badiola	Elaine	A	Badiola	Elaine	\N	Badiola	\N	\N	basic_ed	\N
488	Nursery	10	enrolled	2026-09-18 02:57:45.834144	\N		\N				\N	14	116	656565656565	biticonmr@gmail.com	\N	Old	2026-09-18	\N	\N	\N	\N	\N	\N	\N	\N	30	\N	\N	\N	Melbourne		Biticon	\N	\N	\N	\N	\N	\N				\N	\N	basic_ed	\N
323	Grade 1	1	enrolled	2026-09-08 04:09:56.842902	\N	Male	\N	Brgy Ilayang San Francisco Majayjay Laguna	\N	\N	\N	173	131	\N	jhoannaricamara@gmail.com	\N	Old	2026-05-08	\N	\N	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Aiden Grey Marco	\N	Manata	Mark	G	Tabucol	Editha	\N	Manata	Editha	\N	Manata	\N	\N	basic_ed	\N
326	Grade 7	1	pending	2026-09-08 04:20:05.605002	\N	Male	2014-07-08	Regidor St, Majayjay, Laguna	09395215607	09395215607	Lias Elementary School Marilao, Bulacan	176	\N	400833190004	\N	\N	New	2026-06-03	\N	Bulacan	09772116480	\N	09395215607	Dealer	\N	\N	18	\N	\N	\N	Gio Emmanuel	Obiacoro	Ciruela	Mario	Clado	Circuela	Gloria	Navasca	Obiacoro	Gloria	Obiacoro	Circuela	\N	\N	basic_ed	\N
150	Kinder	4	enrolled	2026-09-05 13:35:11.257968	\N	Male	2026-08-18	Majayjay, Laguna	09344811111	09342323232	LDM	1	121	234567890311	melbournebiticon@gmail.com	melbournebiticon@gmail.com	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	15	\N	\N	Good Standing	Melbourne	Robel	Biticon	\N	\N	\N	\N	\N	\N	Brenda	Robel	Biticon	\N	\N	basic_ed	\N
311	Grade 7	1	pending	2026-09-08 03:42:24.051003	\N	Female	\N	A Luna St Brgy San Francisco Majayjay, Laguna	09070565965		Sta Catalina Elementary School	161	\N	\N	\N	\N	New	2026-03-06	\N	Marikina City	\N	OFW Canada	\N	OFW Japan	\N	\N	18	\N	\N	\N	Hershees Lamia	Brolar	Diego	Raynem	\N	Diego	Zaidalyn	Brolar	Diego	Zaidalyn	Brolar	Diego	\N	\N	basic_ed	\N
318	Grade 1	1	enrolled	2026-09-08 03:54:58.228207	\N	Male	2020-08-20	Brgy San Francisco Majayjay Laguna	09955335448	09955335448	Liceo De Majayjay	168	131	\N	Lucaskeanmillar@gmail.com	\N	Old	2026-05-12	\N	Majayjay, Laguna	09278027109	Encoder	09955335448	Nurse	\N	\N	18	\N	\N	\N	Lucas Kean	R	Millar	Mon Keano	C	Millar	Rachelle	R	Millar	Rachelle	R	Millar	\N	\N	basic_ed	\N
315	Grade 1	1	pending	2026-09-08 03:50:27.577081	\N	Male	2019-08-21		09457192879		\N	165	\N	\N	\N	\N	Old	2026-05-08	\N	Manila	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Samantha Vanellope	A	Palada	\N	\N	\N	\N	\N	\N				\N	\N	basic_ed	\N
317	Grade 7	1	pending	2026-09-08 03:54:00.922386	\N		\N				\N	167	\N	\N	\N	\N	New	2026-03-30	\N	\N	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Gabriel	R	Ronabio	\N	\N	\N	Claire Ann	R.	Ronabio	Claire Ann	R.	Ronabio	\N	\N	basic_ed	\N
313	Grade 1	1	enrolled	2026-09-08 03:48:50.658379	\N	Male	2020-04-20	Majayjay, Laguna	\N	\N	Liceo De Majayjay	163	131	\N	reynvahomes@gmail.com	\N	Old	2026-05-08	\N	Las Pinas	09159883985	\N	09159883985	\N	\N	\N	18	\N	\N	\N	Eddrick Kenzo	\N	So	Ranil	M	So	Reyna	C	So	\N	\N	\N	\N	\N	basic_ed	\N
319	Grade 1	1	pending	2026-09-08 04:00:30.317109	\N	Male	2020-01-09	069 Brgy Ilagay Banga Majayjay Laguna	09054758483	09054758483	\N	169	\N	\N	\N	\N	Old	2026-05-11	\N	Santa Cruz Laguna	\N	OFW	09054758483	Housewife	\N	\N	18	\N	\N	\N	Nazaren	R	Cabuhat	Gregorio	P	Cabuhat	Carlota	R	Cabuhat	Carlota	R	Cabuhat	\N	\N	basic_ed	\N
324	Grade 1	1	pending	2026-09-08 04:14:37.819732	\N	Male	2020-02-06	Brgy San Miguel Majayjay Laguna	09473815762	09473815762	Liceo De Majayjay	174	\N	\N	\N	\N	Old	2026-05-08	\N	Santa Cruz Laguna	09473815762	\N	09473815762	\N	\N	\N	18	\N	\N	\N	Mark Louis	San Jose	Manalo	Luis	S	Manalo	Maricel	\N	San Jose	Maricel		San Jose	\N	\N	basic_ed	\N
321	Grade 1	1	enrolled	2026-09-08 04:04:10.855404	\N	\N	2020-06-13	Brgy Talortor Majayjay Laguna	09926484977	09926484977	\N	171	131	\N	villaraza.maricris25@gmail.com	\N	Old	2026-05-11	\N	Santa Cruz Laguna	09484286565	Cook	09926484977	\N	\N	\N	18	\N	\N	\N	Maria Rosa Patrice	E	Villaraza	Joselito	A	Villaraza	Maricris	E	Villaraza	Maricris	E	Villaraza	\N	\N	basic_ed	\N
328	Grade 2	1	pending	2026-09-08 04:24:08.81438	\N	Female	2018-11-25	083 Brgy Ibabang Banga Majayjay Laguna	09958966410	09958966410	Liceo De Majayjay	178	\N	\N	\N	\N	Old	2026-04-28	\N	Santa Cruz Laguna	09603662830	\N	09958966410	\N	\N	\N	18	\N	\N	\N	Frances Emmauelle	R	Breganza	Lloyd Jensen	F	Breganza	Charise Ann	F	Breganza	Charise Ann	F	Breganza	\N	\N	basic_ed	\N
330	Grade 2	1	pending	2026-09-08 04:28:17.301478	\N	Female	2019-01-08	Brgy Malinao Majayjay, Laguna	09174447689	09174447689	Liceo De Majayjay	180	\N	\N	\N	\N	Old	2026-06-06	\N	Majayjay, Laguna	\N	Seaferer	09174447689	\N	\N	\N	18	\N	\N	\N	Janella Catrice	C	Cerez	Joevell	M	Cerez	Christy	C	Cerez	Christy	C	Cerez	\N	\N	basic_ed	\N
320	Grade 7	1	pending	2026-09-08 04:03:49.875957	\N	Female	2016-02-25	Calumpang, Liliw, Laguna	09271742762	09271742762	Liceo De Majayjay	170	\N	409725190004	\N	\N	Old	2026-02-16	\N	Sta Cruz, Laguna	09287068511	Entrepreneur	09271742762	Entrepreneur	\N	\N	18	\N	\N	\N	Louise Ann	Avila	Pasahol	Allan	Villareal	Pasahol	Florence	Ang	Avila	Florence	Avila	Pasahol	\N	\N	basic_ed	\N
314	Grade 7	1	pending	2026-09-08 03:49:19.802078	\N	Female	2013-09-27	Brgy Ibabang Banga, Majayjay, Laguna	09519123777	09289887527	Liceo De Majayjay	164	\N	402556190010	\N	\N	Old	2026-03-02	\N	Sta Cruz, Laguna	09205348884	Vendor	09289887527	Housewife	\N	\N	18	\N	\N	\N	Eleza May	Opalda	Seño	Lucio	Aguilar	Seño	Elenita	Sahol	Opalda	Elenita	Opalda	Seño	\N	\N	basic_ed	\N
316	Grade 7	1	pending	2026-09-08 03:52:36.197829	\N	Female	2004-08-16	Lopez Jaena St Majayjay, Laguna	\N	09814676415	Sta Catalina Elementary School	166	\N	108349190076	\N	\N	New	2026-03-18	\N	Majayjay, Laguna	\N	\N	09814676415	Storekeeper	\N	\N	18	\N	\N	\N	Najela Brielle	\N	Suyo	\N	\N	\N	Camille	Ordoñez	Suyo	Camille	Ordoñez	Suyo	\N	\N	basic_ed	\N
462	Grade 11	1	enrolled	2026-09-12 13:54:45.105	\N	Female	2010-10-26	Brgy Taytay Majayjay Laguna	09507357083	\N	Santa Catalina National High School	312	139	108347150018	mercuriojewel3@gmail.com	\N	New	2026-04-14	\N	Santa Cruz Laguna	09507357083	Farmer	\N	Housewife	\N	\N	18	\N	\N	\N	Jewel Irish	\N	Mercurio	Wilfredo	G	Mercurio	Joanthen	C	Mercurio	Joanthen	C	Mercurio	\N	\N	basic_ed	\N
312	Grade 7	1	pending	2026-09-08 03:46:17.025656	\N	Male	2013-12-04	Brgy Malinao Majayjay Laguna	\N	09163236878	\N	162	\N	402556190005	\N	\N	New	2026-04-30	\N	Majayjay, Laguna	09163236878	\N	09163236878	\N	\N	\N	18	\N	\N	\N	Liam Jazz	Mirano	Barba	Louie	Coronado	Barba	Lorelyn	Arcenal	Mirano	Lorelyn	Arcenal	Mirano	\N	\N	basic_ed	\N
322	Grade 7	1	pending	2026-09-08 04:09:40.566977	\N	Male	2014-01-19	A Luna St Brgy Ibabang San Francisco Majayjay, Laguna	09667283256	09667283256	Liceo De Majayjay	172	\N	402556190002	\N	\N	Old	2026-02-13	\N	Manila	09667283256	Businessman	09667283256	Housewife	\N	\N	18	\N	\N	\N	Jacob Gabriel	Moncatar	Bautista	Jose Alberto	Lagman	Bautista	Lian Mae	Alonzo	Moncatar	Lian Mae	Alonzo	Moncatar	\N	\N	basic_ed	\N
327	Grade 7	1	pending	2026-09-08 04:22:08.818839	\N	Male	2014-08-08	Brgy San Miguel, Majayjay, Laguna	\N	\N	LICEO DE MAJAYJAY	177	\N	402556190009	\N	\N	Old	2026-06-04	\N	\N	\N	Radiologist	\N	\N	\N	\N	18	\N	\N	\N	Shanon Christopher	Coloma	Esteba	Christopher	Argayoso	Esteba	Shirley	Fagaran	Coloma	Severina	Esteba	Doctolero	\N	\N	basic_ed	\N
329	Grade 7	1	pending	2026-09-08 04:25:07.079735	\N	Male	2013-08-23	265 MH DEL PILLAR ST BRGY SAN MIGUEL	\N	\N	Great Stride Christian School	179	\N	108348180113	\N	\N	New	2026-04-16	\N	Sta Cruz, Laguna	\N	OFW	\N	Make-up Coach	\N	\N	18	\N	\N	\N	Brent Julian	Paladio	Merandela	Reynaldo	Rivera	Merandela	Vina Marie	Oconer	Paladio	Maria Teresa	C.	Oconer	\N	\N	basic_ed	\N
469	Grade 11	1	enrolled	2026-09-12 14:21:03.339235	\N	Female	2010-09-20	Brgy Piit Majayjay Laguna	09933164284	\N	Santa Catalina Integrated National High School	319	139	108346150029	vhiertuazon@gmail.com	\N	New	2026-09-12	\N	Majayjay, Laguna	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Kaye Ann	Borjal	Tuazon	Randy	Bala	Tuazon	Lanie	Borjal	Tuazon	Lanie	Borjal	Tuazon	\N	\N	basic_ed	\N
164	Grade 9	1	enrolled	2026-09-07 03:39:19.186563	\N	Male	2011-12-09	Brgy Malinao, Majayjay, Laguna	09174447689	09174447689	\N	14	122	\N	jazzcerez@gmail.com	\N	Old	2026-05-06	\N	Majayjay, Laguna	\N	Seafarer	09174447689	Government Employee	\N	\N	18	\N	\N	\N	Jazzreel Chris	C	Cerez	Joevell	M	Cerez	Christy	C	Cerez	Christy	C	Cerez	\N	\N	basic_ed	\N
332	Grade 2	1	pending	2026-09-08 04:31:33.169264	\N	Female	2019-06-20	Brgy Sta Catalina Majayjay Laguna	09198442389	09198442389	Liceo De Majayjay	182	\N	\N	\N	\N	Old	2026-06-03	\N	Santa Cruz Laguna	09567213533	Seaferer	09198442389	Teacher	\N	\N	18	\N	\N	\N	Queen Arya	Andaya	Marquez	Edward	Estupigan	Marquez	Jackelyn	Palentinos	Andaya	Jackelyn	Palentinos	Andaya	\N	\N	basic_ed	\N
333	Grade 2	1	pending	2026-09-08 04:34:18.898462	\N	Male	2019-04-30	Brgy Origuel Majayjay Laguna	09622400654	09622400654	Liceo De Majayjay	183	\N	\N	\N	\N	Old	2026-09-08	\N	Majayjay, Laguna	09563648841	Seaferer	09622400654	Business Woman	\N	\N	18	\N	\N	\N	Johann Viel	M	De Guzman	Jan Arvin	A	De Guzman	Jonalyn	M	De Guzman	Jonalyn	M	De Guzman	\N	\N	basic_ed	\N
335	Grade 2	1	pending	2026-09-08 04:37:22.4307	\N	Female	2019-07-12	Brgy Sta Catalina Majayjay Laguna	09126997258	09126997258	Liceo De Majayjay	185	\N	\N	\N	\N	Old	2026-05-28	\N	Majayjay, Laguna	09155302894	Driver	09126997258	Online Seller	\N	\N	18	\N	\N	\N	Elize Jade	Z	Marcia	Joel	A	Marcia	Eloisa	B	Zoleta	Eloisa	B	Zoleta	\N	\N	basic_ed	\N
337	Grade 2	1	pending	2026-09-08 04:42:39.561795	\N	Male	2019-07-07	Brgy Panglan Majayjay Laguna	09694918462	09694918462	Liceo De Majayjay	187	\N	\N	\N	\N	Old	2026-06-22	\N	Santa Cruz Laguna	09289575020	Seaferer	09694918462	Employee	\N	\N	18	\N	\N	\N	Jake Aldrich	R	Pajaro	Macris Bryan	D	Pajaro	Joy Delyn	R	Pajaro	Joy Delyn	R	Pajaro	\N	\N	basic_ed	\N
340	Grade 3	1	pending	2026-09-08 04:52:54.328785	\N	Male	2018-08-20	2935 Purok 3- Durian, Brgy Pangil Majayjay Laguna		09513721450	Liceo De Majayjay	190	\N	\N	\N	\N	Old	2026-06-04	\N	Pasay City	09108561837	IT Employee	09513721450	Bank Employee	\N	\N	18	\N	\N	\N	Devon Dylan	S	Cometa	Jazteen Dave	D	Cometa	Dindi	Rubio	Sapico	Dindi	Rubio	Sapico	\N	\N	basic_ed	\N
342	Grade 3	1	pending	2026-09-08 04:55:39.420202	\N	Male	2017-12-04	Majayjay, Laguna	09690434015	09613092383	Liceo De Majayjay	192	\N	\N	\N	\N	Old	2026-09-08	\N	Pampanga	\N	Chef	09613092383	Nurse	\N	\N	18	\N	\N	\N	Abrahim Kareem		David	Wenmar	\N	Aranillo	Crisel	\N	David	Crisel		David	\N	\N	basic_ed	\N
349	Grade 3	1	pending	2026-09-08 05:28:07.42053	\N	Male	2018-02-25	Brgy Suba Majayjay Laguna		09161701135	Liceo De Majayjay	199	\N	\N	\N	\N	Old	2026-04-16	\N	Majayjay, Laguna	09161701135	Driver	\N	\N	\N	\N	18	\N	\N	\N	Zion Judies	Villoria	De Sagun	Jan Ivan	C	De Sagun	Charmain Joy	\N	Villoria	Jan Ivan	C	De Sagun	\N	\N	basic_ed	\N
344	Grade 7	1	pending	2026-09-08 05:08:14.991678	\N	Male	2014-07-26	H134 Lopez Jeana St Brgy Catalina, Majayjay, Laguna	09078365369	09078365351	Sta Catalina Elementary School	194	\N	108349190017	\N	\N	New	2026-04-06	\N	Sta Cruz, Laguna	09649484351	Vendor	09078365351	\N	\N	\N	18	\N	\N	\N	Jaycel	Majometano	Villarosa	Jayson	Truvela	Villarosa	Maricel	Lumawag	Majometano	Maricel	Majometano	Villarosa	\N	\N	basic_ed	\N
354	Grade 7	1	pending	2026-09-08 05:35:18.1658	\N	Female	2014-08-23	370 A Luna St Brgy San Francisco, Majayjay, Laguna	09609542292	09265120108	Majayjay Elementary School	204	\N	108348190128	\N	\N	New	2026-04-24	\N	Sta Cruz, Laguna	09265120108	Joy Ride Driver	09609542292	OFW	\N	\N	18	\N	\N	\N	Paulyn	Villarubin	Banay	John Paulo	Soto	Banay	Manilyn	Borines	Villarubin	John Paulo	Soto	Banay	\N	\N	basic_ed	\N
341	Grade 7	1	pending	2026-09-08 04:55:22.09078	\N	Female	2014-02-11	Brgy Isabang, Majayjay, Laguna	\N	\N	Gagalot Taytay Elementary School	191	\N	108346190012	\N	\N	New	2026-05-25	\N	Majayjay, Laguna	\N	Farmer	\N	OFW	\N	\N	18	\N	\N	\N	Raniela	Mendoza	Bojabe	Erwin	Venus	Bojabe	Rachelle	Arpon	Mendoza	Rachelle	Arpon	Mendoza	\N	\N	basic_ed	\N
351	Grade 7	1	pending	2026-09-08 05:31:28.841685	\N	Female	2014-04-05	Brgy Pangil Purok Guyabank Street, Majayjay, Laguna	09387857998	\N	Gold Rich Learning School Inc.	201	\N	409288190009	\N	\N	New	2026-05-06	\N	Muntinlupa City	\N	\N	\N	Nurse	\N	\N	18	\N	\N	\N	Christiana Jade	Coloma	Cerio	Jhomer	\N	Manahan	Maria Christine	C.	Cerio	Maria Christina	C.	Cerio	\N	\N	basic_ed	\N
348	Grade 7	1	pending	2026-09-08 05:27:30.941803	\N	Female	2014-07-18	Brgy Malinao Majayjay Laguna	09688866049	09688866049	Liceo De Majayjay	198	\N	428010190029	\N	\N	Old	2026-05-28	\N	Manila	09175755292	Hotel Employee	09688866049	Teacher	\N	\N	18	\N	\N	\N	Iziebella Myrie	Cornista	Cruzat	Israel Gerald	Brul	Cruzat	Marielena	Brioso	Cornista	Marielena	Cornista	Cruzat	\N	\N	basic_ed	\N
346	Grade 7	1	pending	2026-09-08 05:24:01.152219	\N	Female	2013-09-02	Brgy San Francisco Majayjay Laguna	09196693316	09167879036	Majayjay Elementary School	196	\N	108348190027	\N	\N	New	2026-05-25	\N	Majayjay, Laguna	09167879036	Farmer	\N	OFW	\N	\N	18	\N	\N	\N	Marla Margareth	Bolar	Estebal	Mark Anthony	Reyes	Estebal	Ronalyn	Arsolacia	Bolar	Mark Anthony	Reyes	Estebal	\N	\N	basic_ed	\N
338	Grade 7	1	pending	2026-09-08 04:47:16.545384	\N	Female	2014-06-14	Brgy Bukal Majayjay Laguna	09558366338	09558366338	Bukal Elementary School	188	\N	108345190020	\N	\N	New	2026-05-20	\N	Majayjay, Laguna	\N	\N	09558366338	\N	\N	\N	18	\N	\N	\N	Princess Sofia	Trovela	Montesines	Limuel	Villanueva	Montesines	Emylene	Estupigan	Trovela	Emylene	Trovela	Montesines	\N	\N	basic_ed	\N
343	Grade 7	1	pending	2026-09-08 05:02:55.502022	\N	Female	2013-10-31	Brgy Bitaoy, Majayjay, Laguna	09281933906	09281933906	\N	193	\N	108346190018	\N	\N	New	2026-05-19	\N	Sto Domingo, Nueva Ecija	09070400136	Farmer	09281933906	Housewife	\N	\N	18	\N	\N	\N	Brianna Margaret	Alcantara	Noriel	Braian	Bojeador	Noriel	Roda	Corpuz	Alcantara	Roda	Alcantara	Noriel	\N	\N	basic_ed	\N
356	Grade 4	1	pending	2026-09-08 05:37:51.047761	\N	Male	2017-08-19	Brgy Origuel Majayjay Laguna	09292013158	09292013158	Liceo De Majayjay	206	\N	402556220011	\N	\N	Old	2026-05-26	\N	Santa Cruz Laguna	\N	\N	09292013158	Admin Staff	\N	\N	18	\N	\N	\N	Seph Sebastian Ely	\N	Ruda	\N	\N	\N	Josene Ann	Arasa	Ruda	Josene Ann	Arasa	Ruda	\N	\N	basic_ed	\N
353	Grade 5	1	pending	2026-09-08 05:33:55.296067	\N	Male	2015-04-07	Purok 2 Talortor Majayjay Laguna	09489094815	09489094815	Liceo De Majayjay	203	\N	402556210002	\N	\N	Old	2026-09-08	\N	Sta Cruz Laguna	09064624182	Farmer	09489094815	Housewife	\N	\N	18	\N	\N	\N	Nathaniel Shane	Bukid	Hierras	Michele	Orillaza	Hierras	Krystel	Perez	Bukid	Krystel	Perez	Bukid	\N	\N	basic_ed	\N
355	Grade 5	1	pending	2026-09-08 05:37:15.47119	\N	Male	2016-05-08	Brgy Sta Catalina Majayjay Laguna	09566400009	09566400009	Liceo De Majayjay	205	\N	402556210007	\N	\N	Old	2026-09-08	\N	Dubai UAE	09566400009	none	09566400009	OFW	\N	\N	18	\N	\N	\N	Bryan Lester	Mirano	Segador	Nemesio	Palarao	Segador Jr	Asuncion	Palentinos	Mirano	Asuncion	Palentinos	Mirano	\N	\N	basic_ed	\N
350	Grade 5	1	pending	2026-09-08 05:29:35.960228	\N	Female	2016-04-06	Brgy Olla Majayjay Laguna	09274991527	09274991527	Liceo De Majayjay	200	\N	402556210010	\N	\N	Old	2026-09-08	\N	\N	09274991527	Seaman	09190763096	Financial Advisor	\N	\N	18	\N	\N	\N	Tamarah Kyrie	Noriel	Rodillas	Kevin	Alcantara	Rodillas	Ivy Rose	Cedeño	Noriel	Kevin	Alcantara	Rodillas	\N	\N	basic_ed	\N
331	Grade 7	1	pending	2026-09-08 04:28:40.230317	\N	Male	2014-03-09	Brgy Bukal, Majayjay, Laguna	\N	\N	Bukal Elementary School	181	\N	108345190007	\N	\N	New	2026-05-21	\N	Sta Cruz, Laguna	09452416867	Farmer	09661901991	\N	\N	\N	18	\N	\N	\N	Yhuan Jasrel	Borines	Gregana	Israel	Pontiveros	Gregana	Jastine	Mercado	Borines	Jastine	Borines	Gregana	\N	\N	basic_ed	\N
336	Grade 7	1	pending	2026-09-08 04:38:50.046742	\N	Female	2011-06-29	Munting Kawayan, Majayjay, Laguna	09951219656	09911139439	Suba Elementary School Munting Kawayan	186	\N	107511190019	\N	\N	New	2026-05-08	\N	Zapote Las Piñas City	09911335579	Employee	09911139439	Housewife	\N	\N	18	\N	\N	\N	Paula Jane	Maranan	Gonzalvo	Pablo	Ajeto	Gonzalvo Jr.	Marite	Endoso	Maranan	Marite	Endoso	Maranan	\N	\N	basic_ed	\N
345	Grade 7	1	pending	2026-09-08 05:16:46.70339	\N	Female	2012-11-30	464 A Luna Street Majayjay Laguna	09397888826	09397888826	Bagong Tanyag Integrated School	195	\N	136880180089	\N	\N	New	2026-06-03	\N	Manila	09397888826	AC Technician	09481519097	Housewife	\N	\N	18	\N	\N	\N	Andrea Mitch	Galzote	Suyo	Manouto	Dolores	Suyo	Rosanna	Cinco	Galzote	Manouto	Galzote	Suyo	\N	\N	basic_ed	\N
381	Grade 11	1	pending	2026-09-08 06:19:35.155613	\N	Male	2010-03-01	Brgy Bakia, Majayjay, Laguna	09554865951	09665979379	Luis Bernardo Memorial High School	231	\N	108344150013	\N	\N	New	2026-06-09	\N	Sta Cruz, Laguna	\N	Retired CBK Employee	09665979379	Housewife	\N	\N	18	\N	\N	\N	Chris Andrei	R	Leobrera	Tomas	A.	Leobrera Jr.	Evelyn	R.	Leobrera	Evelyn	R.	Leobrera	\N	\N	basic_ed	\N
383	Grade 11	1	pending	2026-09-08 06:19:51.673318	\N	Male	2010-01-02	Brgy Botocan Majayjay Laguna	09670528889	09163105018	Santa Catalina National High School Extension	233	\N	108344150014	\N	\N	New	2026-01-13	\N	\N	09163105018	Computer Science Programmer	09163105018	Manufacturing Team Leader	\N	\N	18	\N	\N	\N	Ivan	Rodillas	Luna	Christopher	\N	Luna	Michelle	Pelagio	Rodillas	Michelle	Pelagio	Rodillas	\N	\N	basic_ed	\N
359	Grade 7	1	approved	2026-09-08 05:42:32.294416	\N	Male	2014-12-07	Brgy San Francisco		09853790178	MCED	209	\N	\N	\N	\N	New	2026-05-29	\N	\N	09853790178	\N	09853790178	\N	\N	\N	18	\N	\N	\N	Gene Aerrol		Argañosa	Gener Aerrol	\N	Argañosa	Rosenda	R.	Argañosa	Rosenda	R.	Argañosa	\N	\N	basic_ed	\N
367	Grade 7	1	pending	2026-09-08 05:50:46.095124	\N	Male	2014-04-25	Brgy Oobi, Majayjay, Laguna	\N	09163236792	Majayjay Elementary School	217	\N	108348190022	\N	\N	New	2026-04-30	\N	Majayjay, Laguna	09391487379	Seafarer	09163236792	\N	\N	\N	18	\N	\N	\N	John Gaberiel	Rivera	Ronabio	Robert John	Mepua	Ronabio	Claire Ann	Breganza	Rivera	Claire Ann	Breganza	Rivera	\N	\N	basic_ed	\N
365	Grade 7	1	pending	2026-09-08 05:48:14.312435	\N	Male	2014-10-24	San Juan Cainta Rizal	\N	09276184037	\N	215	\N	108346180017	\N	\N	New	2026-06-16	\N	Pasig City	09276184037	\N	09176342042	\N	\N	\N	18	\N	\N	\N	Reighn Angelo	Rivera	Rondilla	Reniel	Clenista	Rondilla	Agnes	Punzalan	Rivera	Reniel	Clenista	Rondilla	\N	\N	basic_ed	\N
361	Grade 7	1	pending	2026-09-08 05:45:39.768264	\N	Female	2013-12-17	A Luna St Brgy Ilayang San Francisco Majayjay, Laguna	09554867984	09911873648	Majayjay Elementary School	211	\N	500332190298	\N	\N	New	2026-04-13	\N	Majayjay, Laguna	\N	\N	09911873648	\N	\N	\N	18	\N	\N	\N	Keziah Elli	Zoleta	Monesit	Joshua	Lopez	Monesit	Krist Zyrille	Clado	Zoleta	Pia	Zoleta	Monesit	\N	\N	basic_ed	\N
357	Grade 7	1	pending	2026-09-08 05:38:45.414165	\N	Female	2014-06-26	Brgy Ilayang Banga Majayjay Laguna	09922380076	09922380076	\N	207	\N	424112190045	\N	\N	New	2026-05-30	\N	Imus, Cavite	09156624488	Line Leader, Machine Operator	09922380076	Housewife	\N	\N	18	\N	\N	\N	Allessandra	Basiana	Arcenal	Benedicto	R.	Arcenal	Odessa	\N	Basiana	Odessa	\N	Basiana	\N	\N	basic_ed	\N
467	Grade 11	1	pending	2026-09-12 14:15:34.108737	\N		2010-08-07		09159883985	09159883985	Liceo De Majayjay	317	\N	\N	\N	\N	Old	2026-09-12	\N	Las Pinas	09159883985	\N	09159883985	\N	\N	\N	18	\N	\N	\N	Kristine		So	Ramil	M	So	Reyna Jean	\N	So	Reyna Jean		So	\N	\N	basic_ed	\N
362	Grade 4	1	pending	2026-09-08 05:46:00.339996	\N	Male	2017-05-04	Brgy Ilayang Banga Majayjay Laguna	09054758483	09054758483	Liceo De Majayjay	212	\N	402556220004	\N	\N	Old	2026-05-11	\N	Luisiana Laguna	\N	OFW	09054758483	Housewife	\N	\N	18	\N	\N	\N	Matteo Kai	Recto	Cabuhat	Greogorio	Pinili	Cabuhat	Carlota	Arsolacia	Recto	Carlota	Recto	Cabuhat	\N	\N	basic_ed	\N
363	Grade 4	1	pending	2026-09-08 05:46:51.125284	\N	Male	2017-07-09	Brgy Olla Majayjay Laguna	\N	\N	Liceo De Majayjay	213	\N	402556220010	\N	\N	Old	2026-09-08	\N	\N	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Sid Pierre	Raga	Ramirez	Pedro	Calim	Ramirez Jr	Suzane	Ronabio	Raga	Suzane	Ronabio	Raga	\N	\N	basic_ed	\N
369	Grade 4	1	pending	2026-09-08 05:55:39.09092	\N	Female	2017-03-12	Brgy Origuel Majayjay Laguna	09652938650	09652938650	Liceo De Majayjay	219	\N	108348220038	\N	\N	Old	2026-04-27	\N	Santa Cruz Laguna	09855413698	Barber	09652938650	\N	\N	\N	18	\N	\N	\N	Skye Everly	Jimenez	Reminajes	Rick	Urganay	Reminajes	Cherry Lyn	\N	Jimenez	Cherry Lyn	\N	Jimenez	\N	\N	basic_ed	\N
368	Grade 5	1	pending	2026-09-08 05:51:33.269574	\N	Male	2015-12-01	Brgy Villa Nogales Majayjay Laguna	09473372630	09473372630	Liceo De Majayjay	218	\N	108350210009	\N	\N	Old	2026-09-08	\N	Majayjay, Laguna	09081562900	Sales Representative	09473372630	Sr. Network Supervisor	\N	\N	18	\N	\N	\N	Rhon Javid	Alvareda	Del Sol	Noraolito	Peñaflor	Del Sol	Jennifer	San Diego	Alvareda	Jennifer	San Diego	Alvareda	\N	\N	basic_ed	\N
364	Grade 5	1	pending	2026-09-08 05:47:39.026439	\N	Male	2016-05-31	Brgy Origuel St Majayjay Laguna	09524739125	09524739125	Liceo De Majayjay	214	\N	402556210005	\N	\N	Old	2026-09-08	\N	Sta Cruz Laguna	09563891463	Seafarer	09524739125	Housewife	\N	\N	18	\N	\N	\N	Dream Kaiden	Urcia	Reyes	Erickson	Sobreviñas	Reyes	Jeany	Olipano	Urcia	Jeany	Olipano	Urcia	\N	\N	basic_ed	\N
360	Grade 5	1	pending	2026-09-08 05:44:43.902486	\N	Female	2016-08-26	Brgy Oobi Majayjay Laguna	\N	09297087823	Liceo De Majayjay	210	\N	108348210068	\N	\N	Old	2026-09-08	\N	Sta Cruz Laguna	09297087823	OFW	09297087823	Housewife	\N	\N	18	\N	\N	\N	Nexie Antonitte	Romero	Conejares	Renato	Cortez	Conejares Jr	Rowena	Mantala	Romero	Rowena	Mantala	Romero	\N	\N	basic_ed	\N
358	Grade 5	1	pending	2026-09-08 05:41:23.416357	\N	Female	2016-06-21	156 M H DEL PILLAR ST BRGY SAN MIGUEL MAJAYJAY LAGUNA	09473815762	09473815762	Liceo De Majayjay	208	\N	402556210011	\N	\N	Old	2026-09-08	\N	Sta Cruz	\N	Farmer	09473815762	Supervisor	\N	\N	18	\N	\N	\N	Maddison Eve	\N	San Jose	\N	\N	\N	Maricel	Estanda	San Jose	Maricel	\N	San Jose	\N	\N	basic_ed	\N
377	Grade 6	1	pending	2026-09-08 06:06:45.183734	\N	Male	2014-12-31	Brgy Coralao Majayjay Laguna	\N	\N	Liceo De Majayjay	227	\N	108348200040	\N	\N	Old	2026-09-08	\N	\N	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Sam Angelo	Caldo	Codera	Joel	Palana	Codera	Arlene	Gatbat	Caldo	Arlene	Gatbat	Caldo	\N	\N	basic_ed	\N
380	Grade 6	1	pending	2026-09-08 06:16:45.739789	\N	Male	2015-07-19	Brgy Botocan Majayjay Laguna	09086218091	09086218091	Liceo De Majayjay	230	\N	402556200003	\N	\N	Old	2026-09-08	\N	Lucena City	09086218091	Engineer	09086218091	Engineer	\N	\N	18	\N	\N	\N	Cennon Xavier	Arce	Mendoza	Mark	Mangubat	Mendoza	Jenielyn	Francisco	Arce	Jenielyn	Francisco	Arce	\N	\N	basic_ed	\N
382	Grade 6	1	pending	2026-09-08 06:19:49.551843	\N	Male	2015-05-24	Ilayang Banga Majayjay Laguna	09120033508	09120033508	Liceo De Majayjay	232	\N	136698200062	\N	\N	Old	2026-09-08	\N	Pasig City	09072218981	Cook	09120033508	Housewife	\N	\N	18	\N	\N	\N	Ej Lawrence	Ceria	Suguitan	Eric	Jimenez	Suguitan	Danjerozs	Cabulao	Ceria	Danjeroes	C	Suguitan	\N	\N	basic_ed	\N
378	Grade 6	1	pending	2026-09-08 06:12:14.962172	\N	Female	2015-07-11	Purok 7 Mahogany St Brgy Santa Catalina Majayjay Laguna	09186338486	09186338486	Liceo De Majayjay	228	\N	108348200142	\N	\N	Old	2026-09-08	\N	Calauan Laguna	09993050946	OFW	09186338486	Housewife	\N	\N	18	\N	\N	\N	Princess Johanna	Pardilla	Aranillo	Marwen	\N	Aranillo	Marichu	Reforma	Pardilla	Marichu	Reforma	Pardilla	\N	\N	basic_ed	\N
379	Grade 6	1	pending	2026-09-08 06:13:18.56479	\N	Female	2014-09-17	Brgy San Miguel Majayjay Laguna	\N	\N	Liceo De Majayjay	229	\N	108345200018	\N	\N	Old	2026-09-08	\N	\N	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Ebryl Leigh	Gruezo	Fraginal	Eammond Bryan	Artiaga	Fraginal	Laarni	Lagradante	Gruezo	Laarni	Lagradante	Gruezo	\N	\N	basic_ed	\N
376	Grade 6	1	pending	2026-09-08 06:05:05.007959	\N	Female	2015-02-10	Brgy Olla Majayjay Laguna	\N	\N	Liceo De Majayjay	226	\N	402556200007	\N	\N	Old	2026-09-08	\N	Quezon City	\N	Engineer	\N	Engineer	\N	\N	18	\N	\N	\N	Ashley Nicole	Poblete	Macadenden	Jovenick	Caracas	Macadenden	Melanie	Allado	Poblete	Melanie	Allado	Poblete	\N	\N	basic_ed	\N
370	Grade 6	1	pending	2026-09-08 05:55:47.807944	\N	Female	2015-10-15	Purok Chico Brgy Pangil Majayjay Laguna	09532312415	09532312415	Liceo De Majayjay	220	\N	402556200009	\N	\N	Old	2026-09-08	\N	Majayjay, Laguna	09532372415	OFW	09532312415	Housewife	\N	\N	18	\N	\N	\N	Ezra Rielly	Arganza	Rosalda	Edison	Carandang	Rosalda	Rowena	Sobreviñas	Arganza	Rowena	Sobreviñas	Arganza	\N	\N	basic_ed	\N
371	Grade 7	1	pending	2026-09-08 05:58:26.0711	\N	Male	2014-07-02	Brgy Ibabang Banga, Majayjay, Laguna	09953332397	09271689391	Sta Catalina Elementary School	221	\N	108349190066	\N	\N	New	2026-02-20	\N	Majayjay, Laguna	\N	Delivery Rider	09271689391	Vendor	\N	\N	18	\N	\N	\N	Zayn	Contento	Nuñez	Romeo	Gisalan	Nuñez	Eme Rose	Oro	Contento	Emerose	Contento	Nuñez	\N	\N	basic_ed	\N
406	Grade 11	1	enrolled	2026-09-08 06:53:44.520323	\N	Male	2009-11-17	Brgy Sta Catalina, Majayjay, Laguna	09812457765	09812457765	Sta Catalina Integrated National High School	256	139	\N	noahjoshcadag3@gmail.com	\N	New	2026-03-19	\N	\N	09812457765	Farmer	09812457765	Canteen Helper	\N	\N	18	\N	\N	\N	Noah Josh	C	Cadag	Rene	E.	Cadag	Danica	C.	Cadag	Danica	C.	Cadag	\N	\N	basic_ed	\N
387	Grade 11	1	pending	2026-09-08 06:25:35.762797	\N	Male	\N	426 A Luna St Majayjay, Laguna			LICEO DE MAJAYJAY	237	\N	\N	\N	\N	Old	2026-05-25	\N	\N	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Ioannes Paolo	P	Gonzales	Sonny	\N	Gonzales	Micaela Angeline	F.	Gonzales	Micaela Angeline	F.	Gonzales	\N	\N	basic_ed	\N
388	Grade 11	1	pending	2026-09-08 06:28:37.306055	\N	Male	2010-04-24	Banahaw Village, Brgy Ibabang Banga, Majayjay, Laguna			LICEO DE MAJAYJAY	238	\N	\N	\N	\N	Old	2026-04-24	\N	\N	\N	Salesman	09662239086	OFW	\N	\N	18	\N	\N	\N	Marc Gerald	D	Fesalvo	Marc Leo	\N	Fesalvo	Geraldine	D.	Fesalvo	Gemma		Dequito	\N	\N	basic_ed	\N
389	Grade 11	1	pending	2026-09-08 06:29:17.890934	\N	Male	2010-08-13	Brgy Botocan Majayjay Laguna	09750891310		Santa Catalina National High School Extension	239	\N	\N	\N	\N	Old	2026-01-22	\N	Luisiana Laguna	09553104070	Tricycle Driver	\N	Housewife	\N	\N	18	\N	\N	\N	Deejay	Pascua	Arcenal	Andreo	Iporac	Arcenal	Verlyn	Pascua	Arcenal	Verlyn	Pascua	Arcenal	\N	\N	basic_ed	\N
390	Grade 11	1	pending	2026-09-08 06:32:17.656982	\N	Male	2010-01-17	161 P Origuel Street, Majayjay, Laguna	09684114832	09052774323	LICEO DE MAJAYJAY	240	\N	402556150014	\N	\N	Old	2026-05-18	\N	Los Baños, Laguna	\N	\N	09052774323	Casino Inspector	\N	\N	18	\N	\N	\N	Dylan Andrei		Estefa	Dean Harry	\N	Humarang	Diana	France	Estefa	Diana	France	Estefa	\N	\N	basic_ed	\N
385	Grade 11	1	enrolled	2026-09-08 06:22:08.919203	\N	Male	2010-01-29	Brgy Bakia, Majayjay, Laguna	\N	09662232883	LICEO DE MAJAYJAY	235	139	\N	edzner056@gmail.com	\N	Old	2026-06-08	\N	Majayjay, Laguna	09662232883	Farmer	09662232883	Housewife	\N	\N	18	\N	\N	\N	John Edward	M	Guiang	Edward	D.	Guiang	Minerva	M.	Guiang	Minerva	M.	Guiang	\N	\N	basic_ed	\N
392	Grade 11	1	pending	2026-09-08 06:33:04.697429	\N	Male	2010-05-12	Brgy San Francisco Majayjay Laguna	09265142731	09678049340	Liceo De Majayjay	242	\N	\N	\N	\N	Old	2026-09-08	\N	Majayjay, Laguna	09678049340	\N	09678049340	\N	\N	\N	18	\N	\N	\N	Enzo Joaquin	G	Arnuevo	Roilan	\N	Arnuevo	April	\N	Arnuevo	April		Arnuevo	\N	\N	basic_ed	\N
393	Grade 11	1	pending	2026-09-08 06:36:54.63168	\N	Male	2010-08-16	Sitio Silangan Brgy Taytay, Majayjay, Laguna	09509885650	09509876894	LICEO DE MAJAYJAY	243	\N	108346150016	\N	\N	Old	2026-05-14	\N	Lucena City	09465383014	Farmer	09509876894	Housewife	\N	\N	18	\N	\N	\N	Mark Vincent	R	Esquillo	Ariel	T.	Esquillo	Lerma	R.	Esquillo	Lerma	R.	Esquillo	\N	\N	basic_ed	\N
395	Grade 11	1	pending	2026-09-08 06:39:46.629676	\N	Male	2009-10-27	Brgy Ibabang Banga, Majayjay, Laguna	09091422871	09637623368	Santa Catalina Integrated National High School	245	\N	108349150107	\N	\N	New	2026-06-08	\N	Ibabang Banga	09637623368	\N	\N	\N	\N	\N	18	\N	\N	\N	Delmar	M	Espedido	Ramir	\N	Espedido	Maria Delia	\N	Monteagudo	Ramir		Espedido	\N	\N	basic_ed	\N
396	Grade 11	1	pending	2026-09-08 06:41:09.363858	\N	Male	2009-10-12	Brgy Origuel Majayjay Laguna	09275141392	09477061585	Liceo De Majayjay	246	\N	402556150011	\N	\N	Old	2026-04-29	\N	Majayjay, Laguna	09554161221	Driver	09477061585	Teacher	\N	\N	18	\N	\N	\N	Renver	Armenta	Conejares	Randy	Consignado	Conejares	Marilou	Armenta	Conejares	Marilou	Armenta	Conejares	\N	\N	basic_ed	\N
397	Grade 11	1	pending	2026-09-08 06:42:03.025077	\N	Male	2010-10-09	505 A Luna Street San Francisco Majayjay Laguna	09530046943	09530046943	\N	247	\N	114942150010	\N	\N	Old	2026-09-08	\N	Sta Cruz	09063992832	\N	09530046943	\N	\N	\N	18	\N	\N	\N	Shawn Markki	R	Padasas	Mark	G	Padasas	Roddette	R	Padasas	Roddette	R	Padasas	\N	\N	basic_ed	\N
405	Grade 11	1	enrolled	2026-09-08 06:53:01.595219	\N	Male	2010-05-18	Purok Kamatis Brgy Taytay Majayjay Laguna	\N	09095779685	Sta Catalina Integrated National High School	255	139	108334715001	khian@gmail.com	\N	New	2026-09-08	\N	\N	09469051705	Farmer	09095779685	\N	\N	\N	18	\N	\N	\N	Khian Laurence	B	Mirano	Gilbert	A	Mirano	Cherry Rose	B	Mirano	Cherry Rose	B	Mirano	\N	\N	basic_ed	\N
399	Grade 11	1	pending	2026-09-08 06:46:31.878314	\N	Male	2009-08-03	A Luna St Majayjay Laguna		09285599318	Liceo De Majayjay	249	\N	\N	\N	\N	Old	2026-09-08	\N	Santa Cruz Laguna	\N	Employee	09285599318	\N	\N	\N	18	\N	\N	\N	Rodwing Miguel	V	Conejares	Roderick	B	Conejos	Lyra	S	Villaraza	Lyra	S	Villaraza	\N	\N	basic_ed	\N
400	Grade 11	1	pending	2026-09-08 06:46:36.878467	\N	Male	2009-11-09	242 Plaza Rizal St Brgy Sta Catalina	09363025091	09630348365	Sta Catalina Integrated National High School	250	\N	108349150114	\N	\N	New	2026-09-08	\N	Majayjay, Laguna	09363025091	\N	09630348365	\N	\N	\N	18	\N	\N	\N	King Marion	B	Nania	Marion	Salazar	Nania	Marcilina	Sunga	Buera	Marcilina	Sunga	Buera	\N	\N	basic_ed	\N
401	Grade 11	1	pending	2026-09-08 06:47:09.897479	\N	Male	2009-12-20	Sta Catalina, Majayjay, Laguna	09355155492	09355155492	Sta Catalina National High School	251	\N	108349150005	\N	\N	New	2026-05-28	\N	Majayjay, Laguna	09354649374	Rider	09355155492	Laundry Staff	\N	\N	18	\N	\N	\N	Ace Abraham	L	Cube	Efren	\N	Cube Jr.	Mariz	\N	Lagubana	Mariz		Lagubana	\N	\N	basic_ed	\N
402	Grade 11	1	pending	2026-09-08 06:49:27.051747	\N		\N	Origuel St		09122523557	Liceo de Majayjay	252	\N	\N	\N	\N	Old	2026-09-08	\N	Pook Pila	09208852507	\N	09122523557	\N	\N	\N	18	\N	\N	\N	Aldrin	J	Modina	Edwin	B	Modina	Jenny	\N	Modina	Jenny		Modina	\N	\N	basic_ed	\N
403	Grade 11	1	pending	2026-09-08 06:49:43.367964	\N	Male	2010-01-05	Brgy Bakia, Majayjay, Laguna	09145105171	09175105171	Sta Catalina National High School	253	\N	108344150005	\N	\N	New	2026-04-04	\N	Majayjay, Laguna	09175105171	OFW	09175105171	Housewife	\N	\N	18	\N	\N	\N	Alvincent	C	Catimbang	Alvin	S.	Catimbang	Maxeth	\N	Catimbang	Maxeth		Catimbang	\N	\N	basic_ed	\N
404	Grade 11	1	pending	2026-09-08 06:50:35.362122	\N	Male	2008-10-02	Brgy San Miguel Majayjay Laguna	09273850742		Santa Catalina National High School	254	\N	108348150123	\N	\N	Old	2026-09-08	\N	Majayjay, Laguna	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Jhon Mark	Ordoñez	Aranillo	Paul	G	Aranillo	Paulina	O	Aranillo				\N	\N	basic_ed	\N
394	Grade 11	1	enrolled	2026-09-08 06:37:11.171869	\N	Male	2010-07-20	Brgy Sta Catalina, Majayjay, Laguna	\N	09483452888	\N	244	139	\N	queianperez20@gmail.com	\N	New	2026-09-08	\N	Cabuyao Laguna	09483452888	OFW	\N	\N	\N	\N	18	\N	\N	\N	Queian Andrei	B	Perez	Randy	Balong	Perez	April	P	Perez	\N	Balong	Perez	\N	\N	basic_ed	\N
407	Grade 11	1	enrolled	2026-09-08 06:54:15.732474	\N	Male	2010-06-15	Brgy Sta Catalina Majayjay Laguna	09640961614	09640961614	Santa Catalina National High School	257	139	108349150122	villanuevaeuricojoshc@gmail.com	\N	New	2026-09-08	\N	Majayjay, Laguna	\N	\N	09640961614	OFW	\N	\N	18	\N	\N	\N	Eurico Josh	Calao	Villanueva	Eric	\N	Villanueva	Christine Mey	\N	Calao	Christine Mey	\N	Calao	\N	\N	basic_ed	\N
408	Grade 11	1	pending	2026-09-08 06:56:17.408585	\N	Male	\N	Brgy San Francisco			LICEO DE MAJAYJAY	258	\N	\N	\N	\N	Old	2026-05-04	\N	\N	\N	Farmer	\N	OFW	\N	\N	18	\N	\N	\N	James Ivan		Buera	Mark Gary	\N	Buera	Apple Jemelle Ann	\N	Rivera	Mark Gary		Buera	\N	\N	basic_ed	\N
409	Grade 11	1	pending	2026-09-08 06:56:52.575691	\N	Male	2010-11-04	193 Lopez Jaena Street Majayjay Laguna	09755514203	09750891325	Sta Catalina Integrated National High School	259	\N	402555160043	\N	\N	New	2026-09-08	\N	Luisiana Laguna	\N	OFW	09750891325	OFW	\N	\N	18	\N	\N	\N	Prince Ramiel	D	Miraber	Jhonel	P	Miraber	Clarisse	R	De Guzman	Clarisse	R	De Guzman	\N	\N	basic_ed	\N
386	Grade 6	1	pending	2026-09-08 06:25:25.382249	\N	Male	2014-09-06	Brgy Sta Catalina Majayjay Laguna	09566400009	09566400009	Liceo De Majayjay	236	\N	402556200004	\N	\N	Old	2026-09-08	\N	Sta Cruz Laguna	\N	\N	09566400009	OFW	\N	\N	18	\N	\N	\N	Niel Charles	Segador	Valentin	Raymund	Clado	Valentin	Camille	Mirano	Segador	Camille	Mirano	Segador	\N	\N	basic_ed	\N
410	Grade 11	1	pending	2026-09-08 06:57:32.757399	\N	Male	2010-01-17	P Zamora St Brgy San Miguel Majayjay Laguna	09684965374	09684965374	Liceo De Majayjay	260	\N	108348150028	\N	\N	Old	2026-09-08	\N	Majayjay, Laguna	\N	\N	09684965374	\N	\N	\N	18	\N	\N	\N	Ron Justin	Banawa	Tuazon	Rommel	\N	Tuazon	Margie	Banawa	Tuazon	Margie	Banawa	Tuazon	\N	\N	basic_ed	\N
415	Grade 11	1	enrolled	2026-09-08 07:04:30.43441	\N	Male	2010-02-20	MH DEP PILLAR ST BRGY SAN MIGUEL, MAJAYJAY, LAGUNA	09051434214	09051434214	Sta Catalina Integrated National High School	265	139	\N	tommyasto6@gmail.com	\N	New	2026-03-10	\N	Majayjay, Laguna	09396254779	Restaurnt staff	09051434214	\N	\N	\N	18	\N	\N	\N	Caleb Miguel	Villareal	Asto	Uriel	S.	Asto	Sheryl	V.	Asto	Sheryl	V.	Asto	\N	\N	basic_ed	\N
412	Grade 11	1	pending	2026-09-08 07:00:31.524019	\N	Male	2010-03-02	P Griguel St Majayjay Laguna	09554161223	09267761419	Sta Catalina Integrated National High School	262	\N	108348150036	\N	\N	New	2026-09-08	\N	Majayjay, Laguna	09267761419	\N	09267761419	\N	\N	\N	18	\N	\N	\N	Charles Russele	M	Mira	Richard	E	Mira	Lirio	Modina	Miro	Lirio	Modina	Mira	\N	\N	basic_ed	\N
413	Grade 11	1	pending	2026-09-08 07:01:00.745433	\N	Male	2010-04-14	Purok 2 Brgy Bukal, Majayjay, Laguna	09970977106		LICEO DE MAJAYJAY	263	\N	\N	\N	\N	Old	2026-05-06	\N	Majayjay, Laguna	09970977106	Farmer	09353773409	OFW	\N	\N	18	\N	\N	\N	David Carl	C	Banay	Lucio	C.	Banay	Mutia	C.	Banay	Tyarisse Ann	C	Banay	\N	\N	basic_ed	\N
411	Grade 11	1	enrolled	2026-09-08 06:58:24.285563	\N	Male	2010-04-21	Brgy Malinao, Majayjay, Laguna	\N	09203251590	Sta Catalina National High School	261	139	\N	bbeongbataabon@gmail.com	\N	New	2026-06-01	\N	Majayjay, Laguna	\N	\N	09203251590	\N	\N	\N	18	\N	\N	\N	Joel	A	Bataanon Jr	Joel	A.	Bataanon	Marlyn	\N	Bataanon	Marlyn	\N	Bataanon	\N	\N	basic_ed	\N
430	Grade 11	1	enrolled	2026-09-08 07:45:19.928956	\N	Female	2009-12-07	Purok 4 Brgy Botocan, Majayjay, Laguna	09483477057	09483477057	Sta Catalina National High School Extension	280	139	108344150039	bbeongbataabon@gmail.com	\N	New	2026-04-27	\N	Majayjay, Laguna	09483477057	Farmer	09483477057	Farmer	\N	\N	18	\N	\N	\N	Shaira Faith	R	Bojabe	Feliciano	C.	Bojabe	Myra	C.	Bojabe	Myra	R.	Bojabe	\N	\N	basic_ed	\N
426	Grade 11	1	enrolled	2026-09-08 07:24:30.732764	\N	Male	\N	Brgy Talortor Majayjay Laguna	09668108449	09668108449	Liceo de Majayjay	276	139	\N	forpersonalusesonlyy@gmail.com	\N	Old	2026-09-08	\N	Sta Cruz	09668108449	\N	09668108449	\N	\N	\N	18	\N	\N	\N	Marl Gabriel	\N	Melendez	Marlon	\N	Melendez	Mayreen	\N	Melendez	Mayreen	\N	Melendez	\N	\N	basic_ed	\N
417	Grade 11	1	enrolled	2026-09-08 07:07:46.128262	\N	Male	2010-04-25	Brgy Taytay Majayjay Laguna	\N	09853790179	Sta Catalina Integrated National High School	267	139	\N	cianmercurio15@gmail.com	\N	New	2026-09-08	\N	Calamba City, Laguna	09073100876	Farmer	09853790179	\N	\N	\N	18	\N	\N	\N	Cian Dave	L	Mercurio	Celso	\N	Mercurio	Clarisa	\N	Larioza	Clarisa	\N	Larioza	\N	\N	basic_ed	\N
419	Grade 11	1	pending	2026-09-08 07:13:42.040877	\N	Male	2010-03-05	Brgy Botocan Majayjay Laguna	09777812440	09153053686	Sta Catalina Integrated National High School	269	\N	107030150007	\N	\N	New	2026-09-08	\N	Luisiana Laguna	\N	\N	09153053686	Call Center Agent	\N	\N	18	\N	\N	\N	Rykiel Drei	R	Mendoza	Merwhin	N	Mendoza	Sheryll	E	Donabio	Sheryll	E	Donabio	\N	\N	basic_ed	\N
414	Grade 11	1	enrolled	2026-09-08 07:03:24.746966	\N	Male	2010-03-30	Brgy Taytay Majayjay Laguna	\N	09107536166	\N	264	139	\N	mercuriojm200@gmail.com	\N	New	2026-09-08	\N	Majayjay, Laguna	\N	Driver	09107536166	Brgy Councilor	\N	\N	18	\N	\N	\N	John Michael	Z	Mercurio	Louie	L	Mercurio	Manuela	Z	Mercurio	Manuela	Z	Mercurio	\N	\N	basic_ed	\N
423	Grade 11	1	enrolled	2026-09-08 07:17:58.075827	\N	Male	2009-04-03	Brgy San Miguel, Majayjay, Laguna	09366157338	09366157338	Lucban Academy	273	139	\N	aeonperalta451@gmail.com	\N	New	2026-05-07	\N	Sta Cruz, Laguna	09366157338	\N	\N	OFW	\N	\N	18	\N	\N	\N	Aeon Paul	\N	Peralta	Joven	\N	Peralta	Judy	\N	Peralta	Joven	\N	Peralta	\N	\N	basic_ed	\N
422	Grade 11	1	pending	2026-09-08 07:16:52.140618	\N	Male	2010-01-13	Brgy Gagalot, Majayjay	09705152535	09705152535	\N	272	\N	108346150013	\N	\N	New	2026-09-08	\N	Majayjay, Laguna	09705152535	Farmer	09705152535	Housewife	\N	\N	18	\N	\N	\N	Dustine Kier	F	Mendoza	Noel	Vergel	Mendoza	Estrella	G	Francia	Estrella	G	Francia	\N	\N	basic_ed	\N
425	Grade 11	1	enrolled	2026-09-08 07:21:21.014485	\N	Male	2010-05-21	Purok 6 Brgy San Francisco, Majayjay, Laguna	09273876329	09273876329	SINHS	275	139	108349150118	noobhehe761@gmail.com	\N	New	2026-04-14	\N	Sta Cruz, Laguna	09173043088	Driver	09273876329	Brgy. Kagawad	\N	\N	18	\N	\N	\N	Ezekiel James Gift	M	Robel	Ferdinand	P.	Robel	Veronica	E.	Montemor	Veronica	E.	Montemor	\N	\N	basic_ed	\N
424	Grade 11	1	pending	2026-09-08 07:20:41.93398	\N		2010-10-08	Purok Chico Brgy Pangil Majayjay Laguna	09532312415	09532312415	Liceo De Majayjay	274	\N	\N	\N	\N	Old	2026-05-20	\N	Majayjay, Laguna	09532311686	OFW	09532312415	Housewife	\N	\N	18	\N	\N	\N	Enzo Rkielly	Arganza	Rosalda	Edison	Carandang	Rosalda	Rowena	Arganza	Rosalda	Rowena	Arganza	Rosalda	\N	\N	basic_ed	\N
429	Grade 11	1	approved	2026-09-08 07:40:50.928034	\N	Female	2010-03-16	1133 D Origuel Majayjay Laguna	09934892855	09774005886	\N	279	\N	109830150028	rinalynchavez0913@gmail.com	\N	New	2026-09-08	\N	\N	09936913374	\N	09774005886	\N	\N	\N	18	\N	\N	\N	Rhenz Gabrielle	C	Circulado	Gabriel	S	Circolado	Rinalyn	D	Chavez	Rinalyn	D	Chavez	\N	\N	basic_ed	\N
421	Grade 11	1	enrolled	2026-09-08 07:15:25.062258	\N	Male	2010-05-03	Brgy Oobi, Majayjay, Laguna	\N	09163236792	LICEO DE MAJAYJAY	271	139	\N	ronabiodenzel6@gmail.com	\N	Old	2026-04-30	\N	Majayjay, Laguna	09391487379	Seafarer	09163236792	\N	\N	\N	18	\N	\N	\N	Denzel	R	Ronabio	Robert John	\N	Ronabio	Claire Ann	R.	Ronabio	Claire Ann	R.	Ronabio	\N	\N	basic_ed	\N
427	Grade 11	1	pending	2026-09-08 07:25:35.469918	\N	Male	2008-05-17	Brgy Piit Majayjay Laguna	09667359562	09508509937	Suba National High School Gagalot Annex	277	\N	108346130035	\N	\N	New	2026-06-01	\N	Majayjay, Laguna	09508509937	\N	\N	\N	\N	\N	18	\N	\N	\N	Jomarie	Lopez	Rubian	Junry	Manaba	Rubian	\N	\N	\N	Junry	Manaba	Rubian	\N	\N	basic_ed	\N
418	Grade 11	1	enrolled	2026-09-08 07:12:51.935809	\N	Male	2009-07-26	Brgy Malinao, Majayjay, Laguna	09511038464	09511038464	LICEO DE MAJAYJAY	268	139	\N	kerrphilipr@gmail.com	\N	Old	2026-04-30	\N	Majayjay, Laguna	09624799479	MWS	09511038464	\N	\N	\N	18	\N	\N	\N	Kherr Philip	P	Ronabio	Jayson	B.	Ronabio	Maizlyne	L.	Panado	Maizlyne	L.	Panado	\N	\N	basic_ed	\N
420	Grade 11	1	enrolled	2026-09-08 07:14:54.317673	\N	Male	2010-05-11	Brgy Piit Majayjay Laguna	09274986859	09505183452	Suba National High School Gagalot Annex	270	139	\N	rondolajayar9@gmail.com	\N	New	2026-05-12	\N	Majayjay, Laguna	\N	Farmer	09505183452	Housekeeper	\N	\N	18	\N	\N	\N	Jay-ar	C	Rondola	Matias	\N	Rondola	Mary Ann	Cariño	Rondola	Mary Ann	Cariño	Rondola	\N	\N	basic_ed	\N
416	Grade 11	1	enrolled	2026-09-08 07:07:33.916114	\N	Male	2010-10-16	Brgy Piit Majayjay Laguna	09317213454	09355168863	Santa Catalina National High School Extension	266	139	\N	johnpaulsanvictores143@gmail.com	\N	New	2026-09-08	\N	Lucban, Quezon	\N	Farmer	09355168863	Housewife	\N	\N	18	\N	\N	\N	John Paul	Godinez	Sanvictores	Mario	Mia	Sanvictores	Catherine	Villaberde	Godinez	Catherine	Villaberde	Godinez	\N	\N	basic_ed	\N
433	Grade 11	1	pending	2026-09-08 07:49:01.925837	\N	Female	2010-10-27	Brgy Gagalot, Majayjay, Laguna	09301337855	09301337855	LICEO DE MAJAYJAY	283	\N	108346150026	\N	\N	Old	2026-04-27	\N	Majayjay, Laguna	\N	\N	09301337855	\N	\N	\N	18	\N	\N	\N	Jhasmine	M	Armenta	Michael	\N	Armenta	Jocelyn	\N	Armenta	Jocelyn		Armenta	\N	\N	basic_ed	\N
468	Grade 11	1	pending	2026-09-12 14:17:43.807781	\N		\N				Liceo De Majayjay	318	\N	\N	\N	\N	Old	2026-05-12	\N	\N	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Sangie		Sueña	Jeorge	Ringstone	Sueña	Juvy Mia	\N	Sueña	Juvy Mia		Sueña	\N	\N	basic_ed	\N
434	Grade 11	1	pending	2026-09-08 07:51:18.181731	\N	Female	2010-01-14	Barangay Isabang Majayjay Laguna	09462720751	09462720751	Liceo de Majayjay	284	\N	108346150022	\N	\N	Old	2026-09-08	\N	Sta Cruz	09462720751	Farmer	09462720751	\N	\N	\N	18	\N	\N	\N	Elren Mae	R	Comendador	Elmer	C	Comendador	Mylyn	R	Comendador	Mylyn	R	Comendador	\N	\N	basic_ed	\N
435	Grade 11	1	pending	2026-09-08 07:52:21.600913	\N	Female	2010-01-20	Brgy Oobi, Majayjay, Laguna	09292066610	09569445124	LICEO DE MAJAYJAY	285	\N	\N	\N	\N	Old	2026-04-13	\N	Irigan City, Cam Sur	09214129439	OFW	09569445124	Housewife	\N	\N	18	\N	\N	\N	Antonia		Baeta	Lawrence	\N	Baeta	Karen	\N	Baeta	Karen		Baeta	\N	\N	basic_ed	\N
436	Grade 11	1	pending	2026-09-08 07:54:50.946167	\N	Female	2009-09-15	Brgy San Miguel, Majayjay	09756821279	09741460002	\N	286	\N	108348150134	\N	\N	New	2026-09-08	\N	San Pablo City, Laguna	09976982302	\N	09741460002	\N	\N	\N	18	\N	\N	\N	Criszha Mae	B	Cube	Christian	tato	Cube	Ma Criselda	Balmaceda	Cube	Ma Criselda	Balmaceda	Cube	\N	\N	basic_ed	\N
437	Grade 11	1	pending	2026-09-08 07:55:23.868891	\N	Female	2009-12-19	Brgy Ilayang Banga Majayjay Laguna	09454176231	09275900227	Santa Catalina National High School	287	\N	108348150020	\N	\N	New	2026-09-08	\N	Majayjay, Laguna	09275900227	\N	09275900227	\N	\N	\N	18	\N	\N	\N	Princess Leian	C	Esquillo	Mario	C	Esquillo	Lynden	C	Esquillo	Lynden	C	Esquillo	\N	\N	basic_ed	\N
442	Grade 11	1	enrolled	2026-09-08 08:02:12.774407	\N	Female	2010-02-12	Ilayang San Francisco	09478027740	09559071829	Sta Catalina Integrated National High School	292	139	108348150080	daneashleyarca@gmail.com	\N	New	2026-09-08	\N	Binangonan Rizal	\N	Call Center	09559071829	Housewife	\N	\N	18	\N	\N	\N	Dane Ashley	\N	Arca	Robert	\N	Arca	Renalyn	\N	Bituin	Renalyn	\N	Bituin	\N	\N	basic_ed	\N
438	Grade 11	1	enrolled	2026-09-08 07:55:28.532172	\N	Female	2010-01-01	Purok Kagandahan Brgy Oobi, Majayjay, Laguna	09555294181	09555294181	LICEO DE MAJAYJAY	288	139	108348150086	Queenb026880@gmail.com	\N	New	2026-05-08	\N	Majayjay, Laguna	09555294181	\N	09555294181	\N	\N	\N	18	\N	\N	\N	Baby Queen	D	Buera	Elpidio	A.	Buera	Irene	C.	Buera	Irene	C.	Buera	\N	\N	basic_ed	\N
440	Grade 11	1	pending	2026-09-08 07:59:46.336321	\N	Female	2010-10-26	Brgy Oobi, Majayjay, Laguna	09126970836	09268425265	Sta Catalina Integrated National High School	290	\N	104520150023	\N	\N	New	2026-04-13	\N	San Luis, Aurora	09060444522	Driver	09268425265	Farmer	\N	\N	18	\N	\N	\N	Khiana Chloe	R	Carpio	Alexander	C.	Carpio	Mylene	R.	Carpio	Mylene	R.	Carpio	\N	\N	basic_ed	\N
441	Grade 11	1	pending	2026-09-08 08:00:29.244531	\N	Female	2009-12-30	Brgy Oobi Majayjay Laguna	09945315418	09751838152	Liceo De Majayjay	291	\N	108348150049	\N	\N	New	2026-05-18	\N	Majayjay, Laguna	09351578696	\N	09751838152	\N	\N	\N	18	\N	\N	\N	Crista Viena	G	Estebal	Benedict	V	Estebal	Pamela	G	Estebal	Pamela	G	Estebal	\N	\N	basic_ed	\N
443	Grade 11	1	enrolled	2026-09-08 08:03:14.201304	\N	Female	2009-11-18	Brgy Bakia, Majayjay, Laguna	09076606330	09636826312	Sta Catalina National High School Ext.	293	139	108344150022	kylaceria18@gmail.com	\N	New	2026-04-16	\N	Sta Cruz, Laguna	09052490348	\N	09636826312	\N	\N	\N	18	\N	\N	\N	Kyla Mae	C	Ceria	Nonito	A.	Ceria	Imelda	A.	Ceria	Imelda	A.	Ceria	\N	\N	basic_ed	\N
439	Grade 11	1	enrolled	2026-09-08 07:59:12.524152	\N	Female	2008-02-16	Brgy Batucan Majayjay Laguna	09193198580	09193198580	Sta Catalina Integrated National High School	289	139	109353130240	kyladurante5@gmail.com	\N	New	2026-09-08	\N	Burdas Quezon	\N	Construction Worker	09193198580	\N	\N	\N	18	\N	\N	\N	Kyla	C	Durante	Ruben	A	Durante	Marivic	C	Durante	Marivic	C	Durante	\N	\N	basic_ed	\N
444	Grade 11	1	pending	2026-09-08 08:06:19.463317	\N	Female	2009-12-30	Brgy San Miguel, Majayjay		09163239478	Sta Catalina Integrated National High School	294	\N	108348150047	\N	\N	New	2026-09-08	\N	Taal Batangas	09945315336	Production Operator	09163239478	Brgy Secretary	\N	\N	18	\N	\N	\N	Janna Bianca	Z	Catapang	Jeffrey	B	Catapang	Roxanne	Z	Catapang	Roxanne	Z	Catapang	\N	\N	basic_ed	\N
445	Grade 11	1	pending	2026-09-08 08:09:36.704612	\N	Female	2010-07-20	Brgy Ilayang Banga Majayjay Laguna	09654229480	09654229480	Sta Catalina Integrated National High School	295	\N	108349150023	\N	\N	New	2026-09-08	\N	Majayjay, Laguna	09654229480	Farmer	09654229480	BNS	\N	\N	18	\N	\N	\N	Trixia Andrea	M	Artiaga	Adrian	\N	Artiaga	Grace	\N	Artiaga	Grace		Artiaga	\N	\N	basic_ed	\N
450	Grade 11	1	enrolled	2026-09-08 08:20:31.439965	\N	Female	2009-12-02	Brgy Bakia, Majayjay, Laguna	09772907672	\N	Sta Catalina National High School Extension	300	139	108344150025	granadacrystaljoyceann@gmail.com	\N	New	2026-04-13	\N	Sta Cruz, Laguna	\N	Tricycle Driver	\N	OFW	\N	\N	18	\N	\N	\N	Crystal Joyce Ann	A	Granada	Jaybe	J.	Granada	Cyrille Ann	R.	Argete	Jaybe	J.	Granda	\N	\N	basic_ed	\N
447	Grade 11	1	pending	2026-09-08 08:13:01.93263	\N	Female	2010-02-06	P Origuel St Majayjay Laguna	09357334533	09357334533	Liceo de Majayjay	297	\N	108348150078	\N	\N	Old	2026-09-08	\N	Majayjay, Laguna	\N	\N	09357334533	Dressmaker	\N	\N	18	\N	\N	\N	Kieralyn	T	Aragon	Geminiano	\N	Aragon	Angeline	T	Aragon	Angeline		Aragon	\N	\N	basic_ed	\N
194	Grade 12-STEM	1	enrolled	2026-09-07 05:50:13.839581	\N	Female	2009-09-23	A Luna St, Majayjay, Laguna	09178173639	\N	LICEO DE MAJAYJAY	44	126	402555160008	naomearganosa0@gmail.com	\N	Old	2026-05-18	\N	Sta Cruz, Laguna	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Naome	\N	Argañosa	Gener	\N	Argañosa	Rosenda	\N	Argañosa	Rosenda	\N	Argañosa	\N	\N	basic_ed	\N
449	Grade 11	1	pending	2026-09-08 08:16:20.5563	\N	Female	2010-06-24		09706561030	09706561030	Sta Catalina Integrated National High School	299	\N	\N	\N	\N	New	2026-09-08	\N	Majayjay, Laguna	09706561030	\N	09706561030	\N	\N	\N	18	\N	\N	\N	Trish Shanell	B	Aranillo	Marvin	\N	Aranillo	Jenalyn	\N	Aranillo	Jenalyn		Aranillo	\N	\N	basic_ed	\N
448	Grade 11	1	enrolled	2026-09-08 08:13:57.522418	\N	Female	2010-10-11	Brgy Bakia, Majayjay, Laguna	09555825125	\N	Sta Catalina National High School Extension	298	139	108344150021	cybeeanngranada7@gmail.com	\N	New	2026-04-13	\N	Sta Cruz, Laguna	\N	Tricycle Driver	\N	OFW	\N	\N	18	\N	\N	\N	Cybee-Ann	A	Granada	Jaybe	J.	Granada	Cyrille Ann	R.	Argete	Jaybe	J.	Granada	\N	\N	basic_ed	\N
273	Grade 9	1	enrolled	2026-09-07 07:59:38.660829	\N	Male	2011-08-15	Brgy San Miguel Majayjay, Laguna	\N	\N	Liceo De Majayjay	123	122	488518170005	bert47004@gmail.com	\N	Old	2026-06-04	\N	Sta Cruz, Laguna	\N	BPO	\N	\N	\N	\N	18	\N	\N	\N	Leander Azriel	Evangelio	Contento	Rexford	Palentinos	Contento	Maricel	Olilien	Evangelio	Rexford	Evangelio	Contento	\N	\N	basic_ed	\N
191	Grade 12-STEM	1	enrolled	2026-09-07 05:41:02.168056	\N	Male	2008-01-08	Brgy Bukal, Majayjay, Laguna	09668326354	\N	\N	41	126	\N	corteznash10@gmail.com	\N	Old	2026-05-18	\N	Brgy Bukal	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Alejandro	S	Cortez	Alejandro	B	Cortez	Judelyn	S	Cortez	Judelyn	S	Cortez	\N	\N	basic_ed	\N
192	Grade 12-STEM	1	pending	2026-09-07 05:43:45.609015	\N	Male	2009-02-07	Brgy Botocan, Majayjay, Laguna	\N	\N	LICEO DE MAJAYJAY	42	\N	109864140151	\N	\N	Old	2026-05-18	\N	Calamba, Laguna	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Keeyan Kyle Angelo	\N	Rosende	Mike	R	Rosende	Grace Ne	\N	Rosende	\N	\N	\N	\N	\N	basic_ed	\N
193	Grade 12-STEM	1	pending	2026-09-07 05:47:28.676886	\N	Male	2009-05-25	A Luna Brgy Ilayang San Francisco, Majayjay, Laguna	\N	09558711173	\N	43	\N	136664140843	\N	\N	Old	2026-05-18	\N	Luisiana, Laguna	09558711173	Employee	09558711173	Employee	\N	\N	18	\N	\N	\N	Kharl Kaide	V	Loreño	Jameson	R	Loreño	Rodelyn	C	Verano	Maria Luisa	R	Loreño	\N	\N	basic_ed	\N
490	Grade 11	10	enrolled	2026-09-22 06:55:14.433602	\N		2023-09-21				\N	16	138	545612321555	mariasierrajunterial@gmail.com	mariasierrajunterial@gmail.com	Old	2026-09-22	\N	Magdalena, Laguna	\N	\N	\N	\N	\N	\N	30	\N	\N	Good Standing	Kimberly	Cada	Mamaril	\N	\N	\N	\N	\N	\N	Vivian	Maria	Mamaril	\N	\N	basic_ed	Science
208	Grade 12-GAS	1	enrolled	2026-09-07 06:20:34.595929	\N	Male	2008-10-05	644 Purok Kagandahan Brgy Oobi Majayjay, Laguna	\N	09279958895	LICEO DE MAJAYJAY	58	130	\N	roselwendell05@gmail.com	\N	Old	2026-05-04	\N	Majayjay, Laguna	\N	Farmer	09279958895	Housewife	\N	\N	18	\N	\N	\N	Wendel	L	Rosel	Jonathan	C.	Rosel	Chona	L.	Rosel	Chona	L.	Rosel	\N	\N	basic_ed	\N
221	Grade 12-STEM	1	approved	2026-09-07 06:39:11.987861	\N	Male	2009-08-03	San Miguel Pzamora St, Majayjay, Laguna	09922273691	09945315219	LICEO DE MAJAYJAY	71	\N	\N	willaneraderon@gmail.com	\N	Old	2026-04-14	\N	\N	09922243620	\N	09945315219	\N	\N	\N	18	\N	\N	\N	Prince Delon	A	Villanera	Eduardo	Crisaldo	Villanera	Norbelyn	A.	Villanera	Norbelyn	A.	Villanera	\N	\N	basic_ed	\N
202	Grade 12-STEM	1	enrolled	2026-09-07 06:05:32.43737	\N	Female	2009-10-27	Brgy Ibabang Banga, Majayjay, Laguna	09615540086	09179452911	\N	52	126	\N	altheabala31@gmail.com	\N	Old	2026-05-11	\N	Majayjay, Laguna	09085152161	\N	\N	\N	\N	\N	18	\N	\N	\N	Althea	C	Balazuela	Allan	\N	Balazuela	Adeth	\N	Balazuela	Adeth	\N	Balazuela	\N	\N	basic_ed	\N
297	Grade 12-STEM	1	enrolled	2026-09-07 08:28:43.622623	\N	Female	2009-08-02	Brgy Sta Catalina, Majayjay, Laguna	\N	\N	LICEO DE MAJAYJAY	147	126	108349140185	montemorbianca1@gmail.com	\N	Old	2026-06-05	\N	Majayja, Laguna	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Bianca Aerah	M	Breganza	Baltazar	Ruico	Breganza	Anna Marie	Montemor	Breganza	Anna Marie	Montemor	Breganza	\N	\N	basic_ed	\N
196	Grade 12-ABM	1	enrolled	2026-09-07 05:57:28.91694	\N	Female	2009-03-22	Brgy Sta Catalina Regidor St Majayjay, Laguna	09153871054	09562849354	LICEO DE MAJAYJAY	46	129	\N	vhanarubiales3@gmail.com	\N	Old	2026-05-11	\N	Sta Cruz, Laguna	09158302841	Driver	09562849354	Housewife	\N	\N	18	\N	\N	\N	Vhana Denese	A	Rubiales	Benson	\N	Rubiales	Heidi	\N	Rubiales	Heidi	\N	Rubiales	\N	\N	basic_ed	\N
203	Grade 12-GAS	1	enrolled	2026-09-07 06:08:05.68424	\N	Female	2009-01-20	Brgy Piit, Majayjay, Laguna	\N	\N	LICEO DE MAJAYJAY	53	130	108346140068	guillanaraza@gmail.com	guillanaraza@gmail.com	New	2026-05-11	\N	Pagsanjan, Laguna	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Guillan	\N	Araza	Guillermo	Ramos	Araza	Aurea	Rondola	Araza	Aurea	Rondola	Araza	\N	\N	basic_ed	\N
226	Grade 12-STEM	1	enrolled	2026-09-07 06:47:42.996707	\N	Male	2009-09-07	17 Brgy Banga, Majayjay, Laguna	\N	09391289264	LICEO DE MAJAYJAY	76	126	402555160002	resquiburnok@gmail.com	\N	Old	2026-04-30	\N	Majayjay, Laguna	\N	OFW	09391289264	Self-Employed	\N	\N	18	\N	\N	\N	Earl Norman	R	Quilonio	Norman	C.	Quilonio	Hazel Joan	R.	Quilonio	Hazel Joan	R.	Quilonio	\N	\N	basic_ed	\N
205	Grade 12-GAS	1	enrolled	2026-09-07 06:13:38.165817	\N	Male	2009-03-08	Brgy Origuel, Majayjay, Laguna	09930852439	09774005886	\N	55	130	\N	rinalynchavez0913@gmail.com	\N	Old	2026-05-08	\N	Calamba, Laguna	09774005886	\N	09774005886	\N	\N	\N	18	\N	\N	\N	Rhenz Gabriel	C	Circulado	Lester	M.	Dogatan	Rinalyn	D.	Choves	Rinalyn	\N	Chovez	\N	\N	basic_ed	\N
250	Grade 12-STEM	1	enrolled	2026-09-07 07:28:17.23301	\N	Male	2009-08-02	Brgy Piit, Majayjay, Laguna	09514246617	09321031605	LICEO DE MAJAYJAY	100	126	108348140198	tyronrubian@gmail.com	\N	Old	2026-05-18	\N	Antipolo, Rizal	\N	\N	09321031605	\N	\N	\N	18	\N	\N	\N	Tyron John	R	Rondilla	\N	\N	\N	Dolores	\N	Rubian	Dolores	\N	Rubian	\N	\N	basic_ed	\N
211	Grade 12-STEM	1	enrolled	2026-09-07 06:24:58.518316	\N	Male	2009-07-01	\N	09271689441	09271689418	LICEO DE MAJAYJAY	61	126	108347140007	ailejairus@gmail.com	\N	Old	2026-03-05	\N	Majayjay, Laguna	09993449101	Farmer	09271689418	Vendor	\N	\N	18	\N	\N	\N	Aile Jairus	E	Rondillla	Nestor	G.	Rondilla	Jennifer	E.	Rondillla	Jennifer	E.	Rondilla	\N	\N	basic_ed	\N
218	Grade 12-STEM	1	enrolled	2026-09-07 06:34:22.046988	\N	Male	2009-05-20	A Luna St Brgy San Francisco Majayjay, Laguna	09079391624	09178297807	LICEO DE MAJAYJAY	68	126	108348140108	tanesjanadrian@gmail.com	\N	Old	2026-04-27	\N	Majayjay, Laguna	\N	\N	09178297807	\N	\N	\N	18	\N	\N	\N	Jan Adrian	R	Tanes	\N	\N	\N	Jaqueline	\N	Rovera	Jaqueline	\N	Rovera	\N	\N	basic_ed	\N
207	Grade 12-STEM	1	enrolled	2026-09-07 06:16:22.891387	\N	Male	2009-04-17	Brgy San Miguel, Majayjay, Laguna	09686867751	09062441579	LICEO DE MAJAYJAY	57	126	\N	khaelmiguel.trovela@gmail.com	\N	Old	2026-05-08	\N	Sta Cruz, Laguna	\N	Seafarer	09062441579	Teacher	\N	\N	18	\N	\N	\N	Khael Miguel	A	Trovela	Ruel	\N	Trovela	Kharla Rapunzylle	\N	Trovela	Kharla Rapunzylle	\N	Trovela	\N	\N	basic_ed	\N
244	Grade 12-STEM	1	enrolled	2026-09-07 07:18:26.102752	\N	Male	\N	Purok Pag-Asa Brgy Botocan, Majayjay, Laguna	\N	09153053689	Liceo De Majayjay	94	126	\N	msherwin940@gmail.com	\N	Old	2026-04-14	\N	\N	\N	\N	09153053689	Call Center Agent WFH	\N	\N	18	\N	\N	\N	Sherwin Miguel	R	Mendoza	Merwin	V.	Mendoza	Sheryll	E.	Ronabio	Sheryll	E.	Ronabio	\N	\N	basic_ed	\N
241	Grade 12-STEM	1	enrolled	2026-09-07 07:15:10.704018	\N	Male	2008-12-15	Brgy Taytay, Majajay, Laguna	\N	09487093598	LICEO DE MAJAYJAY	91	126	\N	mercuriolanz77@gmail.com	\N	Old	2026-04-14	\N	Sta Cruz, Laguna	09487093598	Tricycle Driver	09487093598	OFW	\N	\N	18	\N	\N	\N	Lanz James	C	Mercurio	Hilario	G.	Mercurio	Julieta	C.	Mercurio	Hilario	G.	Mercurio	\N	\N	basic_ed	\N
236	Grade 12-STEM	1	enrolled	2026-09-07 07:09:15.665968	\N	Male	2009-10-19	Purok Palayan Brgy Taytay, Majayjay, Laguna	09507357083	09507357083	LICEO DE MAJAYJAY	86	126	\N	wendellmercurio1@gmail.com	\N	Old	2026-04-04	\N	Sta Cruz, Laguna	09384122496	Farmer	09507357083	Housewife	\N	\N	18	\N	\N	\N	Wendell Ivan	C	Mercurio	Wilfredo	G.	Mercurio	Joanthen	C.	Mercurio	Joanthen	C.	Mercurio	\N	\N	basic_ed	\N
248	Grade 12-STEM	1	enrolled	2026-09-07 07:24:46.896822	\N	Male	2009-02-01	4005, A Luna St Brgy San Francisco, Majayjay, Laguna	09760303577	09454176304	Liceo De Majayjay	98	126	\N	markdavidmontemor586@gmail.com	\N	Old	2026-09-07	\N	Sta Cruz, Laguna	09301254127	\N	09454176304	\N	\N	\N	18	\N	\N	\N	Mark David	G	Montemor	Cecilio	\N	Montemor	Myra	\N	Geradila	Myra	\N	Geradila	\N	\N	basic_ed	\N
230	Grade 12-STEM	1	enrolled	2026-09-07 06:55:06.99179	\N	Female	2008-05-05	Brgy Oobi, Majayjay, Laguna	09058466436	09058466436	LICEO DE MAJAYJAY	80	126	\N	noveloteya@gmail.com	\N	Old	2026-04-15	\N	Majayjay, Laguna	09556730773	Driver	09058466436	\N	\N	\N	18	\N	\N	\N	Althea	O	Novelo	Kenjay	\N	Novelo	Larnie	\N	Novelo	Larnie	\N	Novelo	\N	\N	basic_ed	\N
245	Grade 12-STEM	1	enrolled	2026-09-07 07:21:28.406679	\N	Female	2009-01-14	Brgy Suba, Majayjay, Laguna	09708013881	09268425265	LICEO DE MAJAYJAY	95	126	104520114002	kylacolignecarpio@gmail.com	\N	Old	2026-04-13	\N	San Luis, Aurora	09630444522	Driver	09268425265	Farmer	\N	\N	18	\N	\N	\N	Kyla Coligne	Ropa	Carpio	Alexander	C.	Carpio	Mylene	R.	Carpio	Mylene	R.	Carpio	\N	\N	basic_ed	\N
215	Grade 12-STEM	1	enrolled	2026-09-07 06:31:01.60421	\N	Female	2009-01-31	Brgy Panglan, Majayjay, Laguna	09204855267	\N	LICEO DE MAJAYJAY	65	126	108348140055	coderajamila@gmail.com	\N	Old	2026-05-05	\N	Majayjay, Laguna	\N	Land Agent	\N	\N	\N	\N	18	\N	\N	\N	Jamila	T	Codera	Eladio	J.	Codera	Suzette	T.	Codera	Suzzete	T.	Codera	\N	\N	basic_ed	\N
229	Grade 12-STEM	1	pending	2026-09-07 06:51:25.505143	\N	Male	2010-04-09	Ilayang San Francisco, Majayjay, Laguna	\N	\N	LICEO DE MAJAYJAY	79	\N	\N	\N	\N	Old	2026-04-28	\N	Majayjay, Laguna	\N	Driver	\N	OFW	\N	\N	18	\N	\N	\N	Gean Carlo	E	Abiada	Nelvin	\N	Abiada	Marillet	\N	Evasco	Nelvin	\N	Abiada	\N	\N	basic_ed	\N
233	Grade 12-STEM	1	pending	2026-09-07 06:59:23.087878	\N	Male	2009-07-13	Purok Palayan Brgy Taytay, Majayjay, Laguna	09850729077	09850729077	LICEO DE MAJAYJAY	83	\N	\N	\N	\N	Old	2026-04-14	\N	Tagaytay	09850729077	Driver	09850729077	Housewife	\N	\N	18	\N	\N	\N	John Lamuel	A	Rigonan	Joel	\N	Rigona	Ofelia	Adonis	Antivo	Ofelia	Adonis	Antivo	\N	\N	basic_ed	\N
235	Grade 12-ABM	1	pending	2026-09-07 07:04:15.256218	\N	Female	2009-11-24	Brgy Taytay, Majayjay, Laguna	09563164241	\N	LICEO DE MAJAYJAY	85	\N	108347140017	\N	\N	Old	2026-04-14	\N	Lucban, Quezon	09563164241	Farmer	\N	Housewife	\N	\N	18	\N	\N	\N	Princess Mae	P	Rivera	Teodoro	C.	Rivera	Clarissa	P.	Rivera	Clarissa	P.	Rivera	\N	\N	basic_ed	\N
303	Grade 12-STEM	1	enrolled	2026-09-07 08:35:35.395952	\N	\N	\N	\N	\N	\N	LICEO DE MAJAYJAY	153	126	\N	shanweinsd@gmail.com	\N	Old	2026-06-05	\N	\N	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Shan Wein	S	De Castro	Sergio	Z.	De Castro	Madonna	\N	Salvatierra	Madonna	\N	Salvatierra	\N	\N	basic_ed	\N
294	Grade 12-STEM	1	enrolled	2026-09-07 08:26:10.066213	\N	Male	2009-08-06	Bukal, Majayjay, Laguna	09979163181	09979163181	LICEO DE MAJAYJAY	144	126	108345140028	rexd6466@gmail.com	\N	Old	2026-06-05	\N	Sta Cruz, Laguna	09979163181	\N	09979163181	\N	\N	\N	18	\N	\N	\N	Ryan	\N	Dela Cruz	Rex	\N	Dela Cruz	Lhea	\N	Dela Cruz	Lhea	\N	Dela Cruz	\N	\N	basic_ed	\N
293	Grade 12-STEM	1	enrolled	2026-09-07 08:25:07.071872	\N	Female	2009-05-30	\N	09605773579	09605773579	\N	143	126	\N	joannadelrey53029@gmail.com	\N	Old	2026-05-26	\N	Tanauan Batangas	\N	OFW	09605773579	\N	\N	\N	18	\N	\N	\N	Joannah Mae	A	Delos Reyes	Ferdinand	M	Delos Reyes	Belen	A	Delos Reyes	Belen	A	Delos Reyes	\N	\N	basic_ed	\N
292	Grade 12-STEM	1	enrolled	2026-09-07 08:22:33.970383	\N	Male	2009-04-08	Brgy Botocan, Majayjay, Laguna	09301993085	09306842119	LICEO DE MAJAYJAY	142	126	108349150046	norissa14dorado@gmail.com	\N	Old	2026-07-05	\N	Sta Cruz, Laguna	\N	Driver	09306842119	House Keeper	\N	\N	18	\N	\N	\N	Eiron Kingfred	C	Dorado	Wilfred	M.	Dorado	Norassa	C.	Dorado	Norassa	C.	Dorado	\N	\N	basic_ed	\N
261	Grade 12-ABM	1	enrolled	2026-09-07 07:42:56.336538	\N	Female	2009-05-27	Brgy Talortor, Majayjay, Laguna	09484091770	09502564058	LICEO DE MAJAYJAY	111	129	\N	romerojai38@gmail.com	\N	Old	2026-06-01	\N	Talodtod, Majayjay, Laguna	09502564058	Driver	\N	Call Center	\N	\N	18	\N	\N	\N	Jahiezel Grace	G	Romero	Norman	\N	Sotalbo	Glaiza	\N	Gonzaga	Norman	\N	Sptalbo	\N	\N	basic_ed	\N
258	Grade 12-ABM	1	enrolled	2026-09-07 07:39:35.963579	\N	Female	2008-10-14	Brgy Talortor, Majayjay, Laguna	09516010470	09516010470	LICEO DE MAJAYJAY	108	129	\N	monatanajlyn14@gmail.com	\N	Old	2026-05-01	\N	Talortor	09516010470	None	09516010470	Housewife	\N	\N	18	\N	\N	\N	J-lyn	M	Vitayo	Jolam	O.	Vitayo	Jennilyn	H.	Montaña	Jennilyn	H.	Montaña	\N	\N	basic_ed	\N
267	Grade 12-GAS	1	enrolled	2026-09-07 07:49:46.717641	\N	Female	2008-09-28	Brgy Olla, Majayjay, Laguna	09095983932	09095983932	LICEO DE MAJAYJAY	117	130	108350140071	espinaseandrea1@gmail.com	\N	Old	2026-06-01	\N	Brgy Olla, Majayjay, Laguna	09095983932	PFW	09095983932	Farmer	\N	\N	18	\N	\N	\N	Andrea	\N	Montero	Arnel	P.	Montero	Racquel	E.	Montero	Racquel	E.	Montero	\N	\N	basic_ed	\N
290	Grade 12-STEM	1	enrolled	2026-09-07 08:17:46.950024	\N	Female	2008-11-13	Brgy Olla Purok Uno Masayahin	09688149950	09638149950	LICEO DE MAJAYJAY	140	126	108350140072	angelpasawa3@gmail.com	\N	Old	2026-06-05	\N	Majayjay, Laguna	09636828914	\N	09638149950	\N	\N	\N	18	\N	\N	\N	Angel Keniza	V	Pasawa	Wilfredo	O.	Pasawa	Neressa	M.	Vitayo	Neressa	M.	Vitayo	\N	\N	basic_ed	\N
299	Grade 12-STEM	1	enrolled	2026-09-07 08:30:27.667268	\N	Male	2008-12-19	Brgy Botocan Majayjay Laguna	09948012717	\N	\N	149	126	108344140017	raphaelmike494@gmail.com	\N	Old	2026-05-26	\N	Tugegarao City	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Mike Raphael	Q	Tan	Lye Hock	\N	Tan	Mildred	\N	Tan	Mildred	\N	Tan	\N	\N	basic_ed	\N
264	Grade 12-GAS	1	enrolled	2026-09-07 07:46:58.748872	\N	Male	2008-07-10	\N	09655274693	\N	LICEO DE MAJAYJAY	114	130	108346140065	ramilpontiga@gmail.com	\N	Old	2026-06-10	\N	\N	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Ramil	\N	Pontiga	Alexander	\N	Pontiga	Rowena	\N	Pontiga	Rowena	\N	Pontiga	\N	\N	basic_ed	\N
272	Grade 12-GAS	1	enrolled	2026-09-07 07:57:56.732137	\N	Male	2009-07-07	\N	09361565789	\N	LICEO DE MAJAYJAY	122	130	125157150101	arceaiman143@gmail.com	\N	Old	2026-06-09	\N	\N	\N	\N	\N	OFW	\N	\N	18	\N	\N	\N	Jebriel	E	Arce	Pablito	B.	Arce	Carina	B	Edith	Pablito	\N	Arce	\N	\N	basic_ed	\N
305	Grade 12-STEM	1	enrolled	2026-09-07 08:37:53.743036	\N	Female	2009-10-10	Brgy Taytay Majayjay, Laguna	09618965802	09161043101	Liceo De Majayjay	155	126	\N	phionajaneguera@gmail.com	\N	Old	2026-06-07	\N	Majayjay, Laguna	09052185289	\N	09161043101	Government Employee	\N	\N	18	\N	\N	\N	Phiona Jane	\N	Guera	Jeffri	\N	Guera	Prosylen	\N	Guera	Prosylen	\N	Guera	\N	\N	basic_ed	\N
300	Grade 12-STEM	1	enrolled	2026-09-07 08:31:04.284855	\N	Male	2009-09-21	Purok Tulip Brgy Rizal, Majayjay, Laguna	\N	09633366318	LICEO DE MAJAYJAY	150	126	\N	intaljames273@gmail.com	\N	Old	2026-06-05	\N	Lucena City	\N	\N	09633366318	Brgy. Treasurer	\N	\N	18	\N	\N	\N	James Cedrick	D	Intal	\N	\N	\N	Carina	D.	Intal	Carina	D.	\N	\N	\N	basic_ed	\N
282	Grade 12-HUMSS	1	enrolled	2026-09-07 08:07:40.611175	\N	Male	2009-07-03	Sta Catalina	09105032723	\N	LICEO DE MAJAYJAY	132	127	108349150052	kenmirano8@gmail.com	\N	Old	2026-09-07	\N	\N	\N	Mekaniko	\N	\N	\N	\N	18	\N	\N	\N	Ken Jerome	V	Mirano	Arnel	S.	Mirano Jr.	Nenetth	O.	Villarosa	Nenneth	O.	Villarosa	\N	\N	basic_ed	\N
296	Grade 12-STEM	1	enrolled	2026-09-07 08:28:14.166001	\N	Male	2009-06-26	Brgy Botocan Majayjay Laguna	09756741658	\N	\N	146	126	108344140006	latonerojomel@gmail.com	\N	Old	2026-05-26	\N	Caloocan City	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Jomel	Lupera	Latonero	Teodoro	\N	Latonero	Glenda	M	Lupera	Glenda	M	Lupera	\N	\N	basic_ed	\N
298	Grade 12-STEM	1	enrolled	2026-09-07 08:29:32.623886	\N	Male	2008-11-24	Purok 3 Yakal Brgy Malinao Majayjay, Laguna	09821801090	\N	Liceo De Majayjay	148	126	108348130219	shedricbc@gmail.com	\N	Old	2026-06-07	\N	Abu Dhabi, UAE	\N	\N	\N	HR	\N	\N	18	\N	\N	\N	Shedric	\N	Cabuhat	Eric Jones	\N	Cabuhat	Shiane	\N	Cabuhat	Shiane	\N	Cabuhat	\N	\N	basic_ed	\N
269	Grade 12-HUMSS	1	enrolled	2026-09-07 07:52:21.195183	\N	Male	2009-10-06	Sta Catalina	09663778838	09303749496	LICEO DE MAJAYJAY	119	127	108349150069	russelpalentinos0006@gmail.com	haha@gmail.com	Old	2026-06-01	\N	Polymedic hospital Sta Cruz Laguna	\N	\N	09303749496	\N	\N	\N	18	\N	\N	\N	Russel	O	Palentinos	Fernando	\N	Palentinos	Nenita	\N	Palentinos	Nenita	\N	Palentinos	\N	\N	basic_ed	\N
275	Grade 12-HUMSS	1	enrolled	2026-09-07 08:01:59.584914	\N	Male	2009-10-26	Brgy San Roque, Majayjay, Laguna	09357059242	09454624923	LICEO DE MAJAYJAY	125	127	108348140016	aaronvillarante40@gmail.com	\N	Old	2026-06-03	\N	Majayjay, Laguna	09563275391	Electrician	09454624923	None	\N	\N	18	\N	\N	\N	Aaron Trixer	E	Villarante	Erwin	E.	Villarante	Irizand	S.	Española	Irizand	S.	Española	\N	\N	basic_ed	\N
302	Grade 12-STEM	1	enrolled	2026-09-07 08:34:23.804114	\N	Male	2008-07-08	Sanmiguel Majayjay, Laguna	09811733861	09811255461	Liceo De Majayjay	152	126	\N	earljohnarmenta@gmail.com	\N	Old	2026-06-07	\N	Majayjay, Laguna	09318013694	Salesman	09811255461	Housewife	\N	\N	18	\N	\N	\N	Earl John	\N	Armenta	Emerson	\N	Usleno	Mary Jane	\N	Armenta	Mary Jane	\N	Armenta	\N	\N	basic_ed	\N
289	Grade 12-STEM	1	enrolled	2026-09-07 08:13:58.443848	\N	Female	2009-01-05	Brgy Ibabang Banga, Majayjay, Laguna	09464572020	\N	LICEO DE MAJAYJAY	139	126	\N	corozaandrew24@gmail.com	\N	Old	2026-06-05	\N	Sta Cruz, Laguna	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Andrea	\N	Balasbas	Isidro Andrew	D.	Caroza	Aime	L.	Balasbas	Aime	L.	Balasbas	\N	\N	basic_ed	\N
306	Grade 12-STEM	1	enrolled	2026-09-07 08:38:09.581587	\N	Female	2009-02-07	Brgy Gagalot, Majayjay, Laguna	09994710174	09100509089	LICEO DE MAJAYJAY	156	126	108347140010	eunicebarba07@gmail.com	\N	Old	2026-06-05	\N	Majayjay, Laguna	\N	\N	09100509089	\N	\N	\N	18	\N	\N	\N	Eunice	T	Barba	Eugenio	A.	Barba	Jessica	T.	Barba	Jessica	T.	Barba	\N	\N	basic_ed	\N
295	Grade 12-STEM	1	approved	2026-09-07 08:26:38.999363	\N	Male	2008-12-02	Sanroque Majayjay, Laguna	09554116346	09454624923	Liceo De Majayjay	145	\N	108348140017	quervinv@gmail.com	\N	Old	2026-06-07	\N	Majayjay, Laguna	09563275391	Tricycle Driver	09454624923	House Wife	\N	\N	18	\N	\N	\N	Isaiah Quervin	\N	Villarante	Erwin	\N	Villarante	Irizand	\N	Espoñola	Irizand	\N	Espoñola	\N	\N	basic_ed	\N
304	Grade 12-STEM	1	pending	2026-09-07 08:36:24.415927	\N	Male	2008-08-26	Brgy Gagalot Majayjay Laguna	09381646612	09629226749	\N	154	\N	\N	\N	\N	Old	2026-05-24	\N	\N	09296347011	\N	09629226749	\N	\N	\N	18	\N	\N	\N	Mark Gabriel	Barba	Bojeador	Pelmar	N	Bojeador	Grace	Barba	Bojeador	Grace	Barba	Bojeador	\N	\N	basic_ed	\N
189	Grade 12-GAS	1	enrolled	2026-09-07 05:30:43.957386	\N	Female	2009-05-04	Brgy Piit, Majayjay, Laguna	\N	09206772884	LICEO DE MAJAYJAY	39	130	108348140042	biticonmeryll@gmail.com	\N	Old	2026-05-18	\N	Sta Cruz, Laguna	09206772818	Farmer	09206772884	Teacher	\N	\N	18	\N	\N	\N	Meryll Brendalyn	Robel	Biticon	Mel	Argete	Biticon	Brenda	Mia	Robel	Brenda	Robel	Biticon	\N	\N	basic_ed	\N
307	Grade 12-STEM	1	enrolled	2026-09-07 08:40:16.706598	\N	Female	2009-04-15	Brgy Bukal Majayjay Laguna	09553546962	\N	Liceo De Majayjay	157	126	108345140014	azucenadaniella0@gmail.com	\N	Old	2026-05-24	\N	Bacoor Cavite	09357053425	Barber	\N	OFW	\N	\N	18	\N	\N	\N	Daniella Jhorge	Balala	Azucena	William	\N	Azucena	Maricel	\N	Balala	Maricel	\N	Balala	\N	\N	basic_ed	\N
391	Grade 11	1	pending	2026-09-08 06:32:37.194921	\N	Male	2010-08-22	Brgy Botocan Majayjay Laguna	09175209129	09175209129	\N	241	\N	108315160067	\N	\N	Old	2026-09-08	\N	Pagsanjan Laguna	09209318172	Brgy Treasurer	09175209129	LGU Employee	\N	\N	18	\N	\N	\N	Jimuel	G	Pestio	Mandy	R	Pestio	Katherine	G	Pestio	Katherine	G	Pestio	\N	\N	basic_ed	Science, Technology, Engineering, and Mathematics
489	Grade 11	10	enrolled	2026-09-22 06:53:22.741003	\N	Female	2023-09-21	Majayjay, Laguna	09693152461	09473372630	Liceo De Majayjay	15	138	255562002546	melbournerb@gmail.com	melbournerb@gmail.com	Old	2026-09-22	\N	Zapote Las Piñas City	09123456789	Driver	09911873648	Treasurer	\N	\N	30	\N	\N	\N	Junterial	Maria	Sierra	Junterial	Maria	Sierra	Junterial	Maria	Sierra	Junterial	Maria	Sierra	\N	\N	basic_ed	Math
456	Grade 11	1	pending	2026-09-12 01:34:15.244705	\N	Female	2010-08-04	Brgy Villa Nogales Majayjay Laguna	09070296311	09070296311	Liceo De Majayjay	306	\N	\N	\N	\N	Old	2026-09-12	\N	Zamboanga City	09213020311	\N	09070296311	\N	\N	\N	18	\N	\N	\N	Eiliyah	Sobreviñas	Hassan	Binijar	Sahidjuan	Hassan	Mariafe	Ceribo	Sobreviñas	Yafe		Sobreviñas	\N	\N	basic_ed	\N
455	Grade 11	1	pending	2026-09-12 01:23:58.543352	\N	Female	2010-09-12	Brgy San Francisco Majayjay Laguna	09357059145	09357059145	\N	305	\N	108348150161	\N	\N	New	2026-04-13	\N	Lucena City	\N	\N	09357059145	OFW	\N	\N	18	\N	\N	\N	Sabinnah Faith	Rivera	Laroza	Gilbert	\N	Laroza	Mary Grace	Rivera	Laroza	Mary Grace	Rivera	Laroza	\N	\N	basic_ed	\N
457	Grade 11	1	pending	2026-09-12 01:45:17.937678	\N	Female	2010-09-12	Brgy San Francisco Majayjay Laguna	09357058145	09357059145	Santa Catalina National High School	307	\N	108348150160	\N	\N	New	2026-04-13	\N	Lucena City	\N	\N	09357059145	OFW	\N	\N	18	\N	\N	\N	Sabannah Faith	Rivera	Laroza	Gilbert	\N	Laroza	Mary Grace	Rivera	Laroza	Mary Grace	Rivera	Laroza	\N	\N	basic_ed	\N
459	Grade 11	1	pending	2026-09-12 13:41:40.33111	\N	Female	2010-10-09	Brgy Ilayang Banga Majayjay Laguna	09945315123	09951444881	Liceo De Majayjay	309	\N	\N	\N	\N	New	2026-09-12	\N	Majayjay, Laguna	09951444881	\N	09951444881	Housewife	\N	\N	18	\N	\N	\N	Athena	Villarubin	Loja	Andrei	Manzo	Loja	Maricel	Villarubin	Loja	Maricel	Villarubin	Loja	\N	\N	basic_ed	\N
195	Grade 12-STEM	1	pending	2026-09-07 05:54:14.705315	\N	Male	2008-12-25	Purok 5 Kagandagan Brgy Oobi, Majayjay, Laguna	09751838142	09751838152	LICEO DE MAJAYJAY	45	\N	108348140049	\N	\N	Old	2026-05-18	\N	Majayjay, Laguna	09351578696	\N	09751838152	\N	\N	\N	18	\N	\N	\N	Christ Vien	G	Esteb	Benedick	\N	Estebal	Pamela	\N	Estebal	Pamela	\N	Estebal	\N	\N	basic_ed	\N
458	Grade 11	1	enrolled	2026-09-12 12:31:31.429076	\N	Female	2004-11-27	Brgy Talortor Majayjay Laguna	09668108449	\N	Philippine Womens University	308	139	\N	sphjlynamryn@gmail.com	\N	New	2026-04-30	\N	Santa Cruz Laguna	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Sophia	\N	Melendez	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	basic_ed	\N
464	Grade 11	1	enrolled	2026-09-12 14:01:18.699441	\N	Female	2010-05-27	Brgy San Miguel Majayjay Laguna	09195379450	09512416012	Santa Catalina National High School	314	139	108348150022	nedicalyssa@gmail.com	\N	New	2026-04-15	\N	Majayjay, Laguna	\N	\N	09512416012	\N	\N	\N	18	\N	\N	\N	Alyssa Jane	\N	Nedic	Alexander	B	Nedic	Jannet	A	Nedic	Jannet	A	Nedic	\N	\N	basic_ed	\N
308	Grade 12-STEM	1	pending	2026-09-07 08:41:59.31508	\N	Male	2008-08-29	Sanfrancisco Majayjay, Laguna	09672844527	09672844527	Majayjay, Laguna	158	\N	\N	\N	\N	Old	2026-05-07	\N	Majayjay, Laguna	\N	Seaman	09672844527	Businesswoman	\N	\N	18	\N	\N	\N	Lean Symon	\N	Reyes	Jefferson	\N	Reyes	Severa Eva	\N	Reyes	Severa Eva	\N	Reyes	\N	\N	basic_ed	\N
254	Grade 12-ABM	1	enrolled	2026-09-07 07:35:37.18	\N	Female	2009-09-30	Brgy Talortor, Majayjay, Laguna	09800657906	09464575463	LICEO DE MAJAYJAY	104	129	108348140064	reyeseijifaye@gmail.com	\N	Old	2026-06-01	\N	Pampanga	09097336515	Driver	09464575463	Housewife	\N	\N	18	\N	\N	\N	Eiji Faye	P	Reyes	Shernan	T.	Reyes	Khiela Catrine	P.	Reyes	Khiela Catrine	P.	Reyes	\N	\N	basic_ed	\N
309	Grade 12-STEM	1	enrolled	2026-09-07 08:42:09.642935	\N	Female	2009-02-11	Brgy Ilayang Banga, Majayjay, Laguna	09067653073	09687152013	LICEO DE MAJAYJAY	159	126	\N	charisseromero90@gmail.com	haha@gmail.com	Old	2026-05-15	\N	Brgy Ilayang Banga	09703451105	Foreman	09687152013	BHW	\N	\N	18	\N	\N	\N	Charisse	A	Romero	Teodoro	M.	Romero	Bernadette	A.	Romero	Bernadette	A.	Romero	\N	\N	basic_ed	\N
461	Grade 11	1	pending	2026-09-12 13:50:19.391346	\N	Female	2010-05-12	Brgy Origuel Majayjay Laguna		09750890282	Liceo De Majayjay	311	\N	\N	\N	\N	New	2026-04-14	\N	Quezon City	\N	\N	09750890282	Teacher	\N	\N	18	\N	\N	\N	Venice Anne	Granada	Medina	Rafael	Aguinaldo	Medina Jr	Glenda	Granada	Medina	Glenda	Granada	Medina	\N	\N	basic_ed	\N
463	Grade 11	1	pending	2026-09-12 13:58:23.195994	\N	Female	2009-11-29	Brgy Bakia Majayjay Laguna		09074071927	Santa Catalina National High School	313	\N	\N	\N	\N	New	2026-09-12	\N	Santa Cruz Laguna	\N	\N	09074071927	Agent	\N	\N	18	\N	\N	\N	Althea Zuesyne	Mendoza	Morales	Pelenio	Toreffiel	Morales Jr	Nemesia	Mendoza	Morales	Nemesia	Mendoza	Morales	\N	\N	basic_ed	\N
310	Grade 12-STEM	1	enrolled	2026-09-07 08:42:18.183445	\N	Female	2008-10-18	Brgy Origuel Majayjay Laguna	09937230278	\N	\N	160	126	\N	jasminecordial92@gmail.com	\N	Old	2026-05-25	\N	Majayjay, Laguna	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Jasmine	L	Cordial	Jeffry	\N	Cordial	Maricris	\N	Cordial	Maricris	\N	Cordial	\N	\N	basic_ed	\N
465	Grade 11	1	pending	2026-09-12 14:05:15.957968	\N	Female	2010-10-01	Brgy San Francisco Majayjay Laguna		09959567263	Santa Catalina National High School	315	\N	108348150059	\N	\N	New	2026-05-18	\N	Majayjay, Laguna	09503652971	Vegetable Retailer	09959567263	OFW	\N	\N	18	\N	\N	\N	Cheska Wendy	Torre	Noriel	Wilbert	Monteagudo	Noriel	Cindy	Torre	Noriel	Cindy	Torre	Noriel	\N	\N	basic_ed	\N
466	Grade 11	1	pending	2026-09-12 14:10:08.70457	\N	Female	2009-11-11	Brgy Oobi Majayjay Laguna	09464869349	09754358313	Santa Catalina Integrated National High School	316	\N	108348150023	\N	\N	New	2026-09-12	\N	Majayjay, Laguna	09451934021	Safety Officer	09754358313	Health Care Worker	\N	\N	18	\N	\N	\N	Princess Sophia Samantha	Merueña	Oliver	Elizalde	Toledo	Oliver	Adelfa	Merueña	Oliver	Adelfa	Merueña	Oliver	\N	\N	basic_ed	\N
453	Grade 7	1	pending	2026-09-10 09:29:37.026515	\N	Male	2013-03-08	Brgy Ilayang Banga, Majayjay, Laguna	\N	\N	\N	303	\N	108349190027	\N	\N	New	2026-09-10	\N	\N	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Jean Gabriel	Castillo	Bojeador	Avelino	Abustan	Bojeador	Jeanette	Antalan	Castillo	Jeanette	Antalan	Castillo	\N	\N	basic_ed	\N
454	Grade 7	1	pending	2026-09-10 09:33:53.172346	\N	Male	2013-11-14	Brgy Talortor, Majayjay, Laguna	\N	\N	\N	304	\N	108350190017	\N	\N	New	2026-09-10	\N	\N	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Gabriel	Cadang	Cayaban	Rolando	Gambit	Cayaban	Rosalyn	Romulo	Cadang	Rosalyn	Romulo	Cadang	\N	\N	basic_ed	\N
375	Grade 7	1	pending	2026-09-08 06:02:15.901905	\N	Male	2014-02-05	Blumintrit St Brgy Origuel, Majayjay, Laguna	09483664808	09483664808	Majayjay Elementary School	225	\N	108348190003	\N	\N	New	2026-05-15	\N	\N	09512415705	Driver	09483664808	P.B.	\N	\N	18	\N	\N	\N	Marque Shion	Ng	Macam	Marlon	Remanente	Macam	Quennie Grace	Camus	Ng	Quennie Grace	Ng	Macam	\N	\N	basic_ed	\N
373	Grade 4	1	pending	2026-09-08 06:00:09.73791	\N	Male	2016-12-12	Brgy Talortor Majayjay Laguna	09312195246	09312195246	Liceo De Majayjay	223	\N	402556220001	\N	\N	Old	2026-04-23	\N	Binan Laguna	\N	OFW	09312195246	\N	\N	\N	18	\N	\N	\N	Coen Quintin	Millan	Berroya	Mark Paolo	Reyes	Berroya	Maria Lorraine	Merestela	Millan	Maria Lorraine	Millan	Berroya	\N	\N	basic_ed	\N
352	Grade 4	1	pending	2026-09-08 05:33:29.927985	\N	Male	2017-01-09	Brgy Munting Kawayan Majayjay Laguna	09159883985	09159883985	Liceo De Majayjay	202	\N	402556220012	\N	\N	Old	2026-05-08	\N	Las Pinas	09159883985	\N	09159883985	\N	\N	\N	18	\N	\N	\N	Asher Kenjie	Caberte	So	Ranil	Mendoza	So	Reyna Jean	Delfin	Caberte	Reyna Jean	Delfin	Caberte	\N	\N	basic_ed	\N
366	Grade 4	1	pending	2026-09-08 05:50:32.364867	\N	Female	2017-07-08	Brgy Ilayang Banga Majayjay Laguna	09951444881	09951444881	Liceo De Majayjay	216	\N	402556220015	\N	\N	Old	2026-05-18	\N	Santa Cruz Laguna	09951444881	Seaferer	09951444881	Housewife	\N	\N	18	\N	\N	\N	Mikayla	Villarubin	Perez	Michael	Paragas	Perez	Maricel	Fraginal	Villarubin	Maricel	Fraginal	Villarubin	\N	\N	basic_ed	\N
470	Grade 5	1	pending	2026-09-14 01:41:07.66837	\N	Male	2016-07-04	Brgy Bagbag Quezon City NCR Second District			\N	320	\N	136521210275	\N	\N	New	2026-05-14	\N	\N	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Rylus Adam	Udtohan	Marcelo	Mark Francis	S	Marcelo	Francily Mae	\N	Udtohan	Francily Mae		Udtohan	\N	\N	basic_ed	\N
471	Grade 5	1	pending	2026-09-14 01:49:43.343308	\N	Male	2014-08-30	Brgy San Francisco Majayjay Laguna			\N	321	\N	108348210156	\N	\N	New	2026-05-14	\N	\N	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Johan Marco	Nacion	Robel	Danilo Vicente	Mia	Robel	Vilma	Claridad	Nacion	Vilma	Claridad	Nacion	\N	\N	basic_ed	\N
472	Grade 5	1	pending	2026-09-14 01:54:20.115664	\N	Male	2016-03-26	Brgy Origuel Majayjay Laguna			Liceo De Majayjay	322	\N	402556210013	\N	\N	Old	2026-09-14	\N	\N	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Geoffrey John	Llanera	Romulo	Jeffrey	Ramos	Romulo	Lady Ann	Ronabio	Llanera	Lady Ann	Ronabio	Llanera	\N	\N	basic_ed	\N
473	Grade 5	1	pending	2026-09-14 02:05:47.710457	\N	Female	2016-06-07	Brgy Origuel Majayjay Laguna			\N	323	\N	108349210053	\N	\N	New	2026-05-14	\N	\N	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Clare Yael	Oraye	Ledesma	Edgardo	Feliciano	Ledesma Jr	Caren Earl	Arela	Oraye	Caren Earl	Arela	Oraye	\N	\N	basic_ed	\N
347	Grade 5	1	pending	2026-09-08 05:25:07.905957	\N	Female	2016-05-29	Brgy Suba Majayjay Laguna	09197674395	09707947933	Liceo De Majayjay	197	\N	409288210003	\N	\N	Old	2026-09-08	\N	Sta Cruz Laguna	09197674395	OFW	09707947933	Housewife	\N	\N	18	\N	\N	\N	Lieyan	Palentinos	Losanta	Bryan	Forbes	Losanta	Wendelie	Buan	Palentinos	Wendelie	Buan	Palentinos	\N	\N	basic_ed	\N
474	Grade 5	1	pending	2026-09-14 02:11:44.998532	\N	Female	2016-03-11	Brgy Origuel Majayjay Laguna			\N	324	\N	108347210005	\N	\N	New	2026-05-14	\N	\N	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Vien Amira	Granada	Medina	Rafael	Aguinaldo	Medina Jr	Glenda	Argete	Granada	Glenda	Argete	Granada	\N	\N	basic_ed	\N
372	Grade 6	1	pending	2026-09-08 05:58:45.353475	\N	Male	2014-09-03	Brgy San Francisco Majayjay Laguna	\N	\N	Liceo De Majayjay	222	\N	108349200026	\N	\N	Old	2026-09-08	\N	\N	\N	Seafarer	\N	\N	\N	\N	18	\N	\N	\N	Raven Jacob	Mia	Solsona	Mark Kevin	Dizon	Enrico	Rechel	Tagod	Mia	Mark Kevin	Dizon	Enrico	\N	\N	basic_ed	\N
384	Grade 6	1	pending	2026-09-08 06:21:55.688266	\N	Female	2014-09-20	Brgy Pangil Majayjay Laguna	\N	09616004283	Liceo De Majayjay	234	\N	402556200005	\N	\N	Old	2026-09-08	\N	Quezon City	09616004283	\N	09616004283	\N	\N	\N	18	\N	\N	\N	Maria Luisa	Del Mundo	Castillo	Leslie	Castillo	Castillo	Evangeline	Delos Reyes	Del Mundo	Evangeline	Delos Reyes	Del Mundo	\N	\N	basic_ed	\N
374	Grade 6	1	pending	2026-09-08 06:02:02.22348	\N	Female	2015-09-09	5285 Caillest st brgy san miguel majayjay laguna	09524569534	09524569534	Liceo De Majayjay	224	\N	402518200011	\N	\N	Old	2026-09-08	\N	Sta Cruz Laguna	09524569534	OFW	09524569534	Housewife	\N	\N	18	\N	\N	\N	Sophia Railey	Cubelo	Resubal	Ray	Estefa	Resubal	Jilyn	Opamin	Cubelo	Jilyn	Opamin	Cubelo	\N	\N	basic_ed	\N
452	Grade 7	1	pending	2026-09-10 09:12:15.79961	\N	Male	2014-05-08	Brgy Panglan, Majayjay, Laguna	\N	\N	\N	302	\N	402557190001	\N	\N	New	2026-09-10	\N	\N	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Chevron Azriel	Aquino	Aponesto	Roland	Baldonado	Aponesto	Chysseir	Gozo	Aquino	Chysseir	Gozo	Aquino	\N	\N	basic_ed	\N
475	Grade 7	1	pending	2026-09-14 04:14:29.937559	\N	Male	2012-12-07	Brgy San Francisco Majayjay Laguna			Liceo De Majayjay	325	\N	409288190011	\N	\N	Old	2026-05-14	\N	\N	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Gene Aerrol	Romero	Argañosa	Gener	Miraber	Argañosa	Rosenda	Gonzaga	Romero	Rosenda	Romero	Romero	\N	\N	basic_ed	\N
339	Grade 7	1	pending	2026-09-08 04:50:30.417371	\N	Male	2014-06-23	Brgy Isabang, Majayjay, Laguna	09386728187	09386728187	\N	189	\N	108346190004	\N	\N	New	2026-05-25	\N	Majayjay, Laguna	09636826165	\N	09386728187	\N	\N	\N	18	\N	\N	\N	Brian	Mendoza	Bojabe	Bernard	Veluz	Bojabe	Rosemarie	Arpon	Mendoza	Rosemarie	Arpon	Mendoza	\N	\N	basic_ed	\N
476	Grade 7	1	pending	2026-09-14 06:02:46.164372	\N	Female	2014-02-26	Brgy San Miguel Majayjay Laguna			\N	326	\N	402556190006	\N	\N	New	2026-09-14	\N	\N	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Aniachre	Aranilla	Dimayuga	Charlie	Alvis	Dimayuga	Maria Janah	Cube	Aranilla	Maria Janah	Cube	Aranilla	\N	\N	basic_ed	\N
334	Grade 7	1	pending	2026-09-08 04:34:43.785043	\N	Female	2014-05-24	Purok Sta Catalina Brgy Ilayang Banga, Majayjay, Laguna	09852742389	09852742389	Majayjay Elementary School	184	\N	108348190124	\N	\N	New	2026-05-11	\N	Majayjay, Laguna	09307163364	Farmer	09852742389	BRGY. SEC	\N	\N	18	\N	\N	\N	Eliel Rojaneh	Garcia	Mercurio	Jerwin	Urizza	Mercurio	Rachelle	Cobrado	Garcia	Rachelle	Garcia	Mercurio	\N	\N	basic_ed	\N
186	Grade 8	1	pending	2026-09-07 05:20:12.479968	\N	Male	2013-09-12	Brgy Ilayang San francisco Majayjay Laguna	\N	\N	Majayjay Elementary School	36	\N	108348180001	\N	\N	New	2026-04-28	\N	Majayjay, Laguna	\N	Driver	\N	OFW	\N	\N	18	\N	\N	\N	Calvin James	Evasco	Abiada	Nelvin	Ortega	Abiada	Marillet	Rivera	Evasco	Nelvin	Ortega	Abiada	\N	\N	basic_ed	\N
165	Grade 8	1	pending	2026-09-07 03:41:17.140174	\N	Male	2012-12-19	Brgy San Francisco Majayjay Laguna	\N	\N	Majayjay Elementary School	15	\N	108348180004	\N	\N	New	2026-05-05	\N	\N	\N	Farmer	\N	OFW	\N	\N	18	\N	\N	\N	Mark Daniel	Rivera	Buera	Mark Gary	Monteagudo	Buera	Apple Jemelle Ann	Breganza	Rivera	Mark Gary	Monteagudo	Buera	\N	\N	basic_ed	\N
169	Grade 8	1	pending	2026-09-07 03:45:53.481595	\N	Male	2011-12-16	Purok 6 Brgy Pangil Majayjay, Laguna	09692092797	09692092797	Liceo De Majayjay	19	\N	484004160047	\N	\N	Old	2026-05-07	\N	Majayjay, Laguna	09692092797	Guest Service	09692092797	Housewife	\N	\N	18	\N	\N	\N	John Zyrus	Constan	Estera	Juluis	Villarante	Estera	Mirabel	Collaga	Costan	Mirabel	Costan	Estera	\N	\N	basic_ed	\N
477	Grade 8	1	pending	2026-09-14 06:48:05.566504	\N	Male	2013-02-19	Poblacion Brgy 1 Lipa City Batangas			Liceo De Majayjay	327	\N	402556180001	\N	\N	Old	2026-05-14	\N	\N	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Hernand	Balala	Palentinos	Homer	Norado	Palentinos	Alona	Damasco	Balala	Homer	Norado	Palentinos	\N	\N	basic_ed	\N
188	Grade 8	1	pending	2026-09-07 05:26:53.172788	\N	Male	2012-11-15	Brgy Pangil Majayjay, Laguna	09630849458	09814886008	Liceo De Majayjay	38	\N	402518180011	\N	\N	Old	2026-04-28	\N	Pasig City	\N	OFW	09814886008	Employee	\N	\N	18	\N	\N	\N	Sean Calix	Jacobe	Sanchez	Wilfredo	Baylon	Sanchez Jr	Carollyn	Mendoza	Jacobe	Carollyn	Jacobe	Sanchez	\N	\N	basic_ed	\N
478	Grade 8	1	pending	2026-09-14 07:03:23.412724	\N	Male	2013-06-10	Brgy San Francisco Majayjay Laguna			Liceo De Majayjay	328	\N	402556180011	\N	\N	Old	2026-09-14	\N	\N	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Lourd	Ceria	Seludo	Don Marcos	\N	Seludo	Chiky	Monteagudo	Ceria	Chiky	Ceria	Seludo	\N	\N	basic_ed	\N
479	Grade 8	1	pending	2026-09-14 07:58:44.574708	\N	Male	2013-10-10	Brgy San Miguel Majayjay Laguna			Liceo De Majayjay	329	\N	108348180105	\N	\N	Old	2026-09-14	\N	\N	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Dwayne Luis	Buera	Trovela	Dennis	Porcioncula	Trovela	Leonida	Condino	Buera	Leonida	Condino	Buera	\N	\N	basic_ed	\N
480	Grade 8	1	pending	2026-09-14 08:20:12.692119	\N	Female	2013-04-03	Brgy Bakia Majayjay Laguna			Liceo De Majayjay	330	\N	402556180007	\N	\N	Old	2026-09-14	\N	\N	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Aprilene	Breganza	Argete	Jay-ar	Biticon	Argete	Arlene	Villarosa	Breganza	Arlene	Villarosa	Breganza	\N	\N	basic_ed	\N
184	Grade 8	1	pending	2026-09-07 05:14:57.139708	\N	Female	2013-04-19	355 Antonio Luna Sanfrancisco Majayjay, Laguna	09218056114	09218056114	Liceo De Majayjay	34	\N	108347180008	\N	\N	Old	2026-04-20	\N	Majayjay, Laguna	09071024953	Farmer	09218056114	Housewife	\N	\N	18	\N	\N	\N	Kassandra Venisse	Hapin	Arnuco	Reynaldo	Guera	Arnuco Jr	Maricris	Lagata	Hapin	Maricris	Hapin	Arnuco	\N	\N	basic_ed	\N
481	Grade 8	1	pending	2026-09-14 08:29:14.47622	\N	Female	2012-10-08	Brgy San Miguel Majayjay Laguna			Liceo De Majayjay	331	\N	108349180070	\N	\N	Old	2026-05-14	\N	\N	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Hanes Khristel	Abiada	Bantaya	Michael	Ordoñez	Bantaya	Myra	Ortega	Abiada	Myra	Ortega	Abiada	\N	\N	basic_ed	\N
482	Grade 8	1	pending	2026-09-14 08:39:56.783135	\N	Female	2013-02-09	Caraycayon Tiagon Camarines Sur			Liceo De Majayjay	332	\N	113108180230	\N	\N	Old	2026-05-14	\N	\N	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Krisanta	Dacuno	Clamor	Rudico	Factor	Clamor	Dina	Jallores	Dacuno	Dina	Jallores	Dacuno	\N	\N	basic_ed	\N
483	Grade 8	1	pending	2026-09-14 08:52:41.215708	\N	Female	2013-02-13	Brgy Sta Catalina Majayjay Laguna			Liceo De Majayjay	333	\N	108349180025	\N	\N	Old	2026-09-14	\N	\N	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Jhanel	Coronado	Rubian	Junry	Manaba	Rubian	Nory	Villanera	Arcenal	Nory	Villanera	Arcenal	\N	\N	basic_ed	\N
152	Grade 8	1	pending	2026-09-07 03:19:18.504153	\N	Female	2013-12-08	A Luna St Sanfrancisco Majayjay, Laguna	09163252345	09163252345	Liceo De Majayjay	2	\N	402518190021	\N	\N	Old	2026-05-05	\N	Sta Cruz, Laguna	09765526646	Seafarer	09163252345	Housewife	\N	\N	18	\N	\N	\N	Rianna	Teope	Sobreviñas	Henry	Paletinos	Sobreviñas	Annacel	Condino	Teope	Annacel	Teope	Sobreviñas	\N	\N	basic_ed	\N
484	Grade 9	1	pending	2026-09-14 14:34:06.559414	\N	Male	2011-03-13	San Juan Cainta Rizal			Liceo De Majayjay	334	\N	109397170064	\N	\N	Old	2026-09-14	\N	\N	\N	\N	\N	\N	\N	\N	18	\N	\N	\N	Reniel Angelo	Rivera	Rondilla	Reniel	Clenista	Rondilla	Agnes	Punzalan	Rivera	Agnes	Rivera	Rondilla	\N	\N	basic_ed	\N
161	Grade 9	1	enrolled	2026-09-07 03:34:53.366345	\N	Female	2012-03-15	Brgy Origuel, Majayjay, Laguna	09366157339	09366157339	Liceo De Majayjay	11	122	108348170157	ninaconejares@gmail.com	\N	Old	2026-05-18	\N	Majayjay, Laguna	09552938720	Driver	09366157339	Goverment Employee	\N	\N	18	\N	\N	\N	Clara Niña	Mirabel	Conejares	Vicente Arthur	Oriña	Conejares	Cecilia	Peralta	Mirabel	Cecilia	Mirabel	Conejares	\N	\N	basic_ed	\N
199	Grade 12-STEM	1	enrolled	2026-09-07 06:02:27.532475	\N	Male	2009-06-26	A Luna St Brgy San Francisco Majayjay, Laguna	09936701346	09398196604	\N	49	126	108349150028	cjayguiruela06262009@gmail.com	\N	Old	2026-09-07	\N	Majayjay, Laguna	09692994362	\N	09398196604	\N	\N	\N	18	\N	\N	\N	Cjay	G	Guiruela	Cherie	O	Guiruela	Leonora	G.	Guiruela	Leonora	G.	Guiruela	\N	\N	basic_ed	\N
491	Grade 11	10	enrolled	2026-09-22 07:41:32.607416	\N		2023-09-21				\N	17	138	108348100006	melbournebiticon@gmail.com	melbournebiticon@gmail.com	Old	2026-09-22	\N	\N	\N	\N	\N	\N	\N	\N	30	\N	\N	Excelling	Melbourne		Biticon	\N	\N	\N	\N	\N	\N				\N	\N	basic_ed	Math
\.


--
-- Data for Name: exam_answers; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.exam_answers (answer_id, result_id, question_id, student_answer, is_correct) FROM stdin;
100	36	203	True	t
101	36	204	False	f
102	36	205	True	t
103	36	206	True	t
104	36	207	True	t
197	51	229	True	t
198	51	230	True	f
199	51	231	True	t
200	51	232	Closes an open window or app quickly	f
201	51	233	The long bar on the keyboard used to add spaces between words	f
202	51	234	Closes an open window or app quickly	f
203	51	236	Opens the print menu to print a page quickly	f
204	51	235	Opens the print menu to print a page quickly	t
114	41	208	True	t
115	41	209	True	t
116	41	210	True	t
175	50	224	B	t
176	50	226	B	t
177	50	223	A	t
178	50	222	B	t
122	43	211	True	t
123	43	212	True	t
124	43	213	True	t
125	43	214	True	t
126	43	215	True	t
179	50	225	C	t
180	50	231	True	t
181	50	229	True	t
160	49	226	B	t
161	49	223	A	t
182	50	227	True	t
183	50	230	False	t
184	50	228	True	t
326	62	254	B	t
328	62	255	C	t
94	34	197	A	t
95	34	198	True	t
96	34	199	Yes	t
97	35	200	A	t
98	35	201	True	t
99	35	202	No	t
162	49	222	B	t
185	50	236	Closes an open window or app quickly	t
186	50	233	Prints your digital documents onto physical paper	t
187	50	235	Opens the print menu to print a page quickly	t
188	50	232	Let’s you hear audio, music, or online lectures	t
189	50	234	The long bar on the keyboard used to add spaces between words	t
213	52	231	True	t
214	52	228	True	t
215	52	234	The long bar on the keyboard used to add spaces between words	t
216	52	235	Opens the print menu to print a page quickly	t
217	52	233	Prints your digital documents onto physical paper	t
218	52	232	Let’s you hear audio, music, or online lectures	t
163	49	224	B	t
164	49	225	B	f
165	49	231	True	t
166	49	227	True	t
167	49	229	True	t
168	49	230	False	t
169	49	228	True	t
170	49	232	Let’s you hear audio, music, or online lectures	t
171	49	236	Prints your digital documents onto physical paper	f
172	49	235	Prints your digital documents onto physical paper	f
173	49	234	The long bar on the keyboard used to add spaces between words	t
174	49	233	Opens the print menu to print a page quickly	f
219	52	236	Closes an open window or app quickly	t
330	62	259	True	t
190	51	226	B	t
191	51	222	A	f
192	51	225	B	f
193	51	223	A	t
194	51	224	B	t
195	51	227	True	t
196	51	228	True	t
332	62	261	True	t
334	62	260	False	t
336	62	264	The long bar on the keyboard used to add spaces between words	t
338	62	262	Let’s you hear audio, music, or online lectures	t
205	52	222	B	t
206	52	223	A	t
207	52	224	B	t
208	52	226	B	t
209	52	225	C	t
210	52	230	False	t
211	52	227	True	t
212	52	229	True	t
459	79	285	B	f
461	79	286	B	t
463	79	284	B	t
465	79	288	True	t
467	79	289	True	t
469	79	293	Opens the print menu to print a page quickly	f
471	79	292	Let’s you hear audio, music, or online lectures	t
473	79	295	Opens the print menu to print a page quickly	t
237	55	224	B	t
239	55	226	B	t
240	55	222	B	t
241	55	225	C	t
244	55	223	A	t
246	55	231	True	t
248	55	229	True	t
250	55	230	False	t
251	55	228	True	t
253	55	227	True	t
255	55	236	Closes an open window or app quickly	t
257	55	233	Prints your digital documents onto physical paper	t
258	55	235	Opens the print menu to print a page quickly	t
260	55	234	The long bar on the keyboard used to add spaces between words	t
262	55	232	Let’s you hear audio, music, or online lectures	t
458	78	267	B	t
325	62	253	A	t
327	62	252	B	t
329	62	256	B	t
331	62	258	True	t
333	62	257	True	t
335	62	265	Prints your digital documents onto physical paper	f
337	62	263	Prints your digital documents onto physical paper	t
339	62	266	Closes an open window or app quickly	t
460	79	283	A	t
462	79	282	B	t
464	79	290	True	f
466	79	287	True	t
468	79	291	True	t
470	79	294	The long bar on the keyboard used to add spaces between words	t
472	79	296	Closes an open window or app quickly	t
474	92	297	True	t
\.


--
-- Data for Name: exam_questions; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.exam_questions (question_id, exam_id, question_text, question_type, choices, correct_answer, points, order_num) FROM stdin;
237	74	Which computer part is used to type letters, numbers, and symbols into a computer?	mcq	{"A": "Monitor", "B": "Keyboard", "C": "Mouse", "D": "Speaker"}	B	1	1
238	74	What keyboard shortcut is famous for making a quick copy of selected text?	mcq	{"A": "Ctrl + C", "B": "Ctrl + Z", "C": "Ctrl + P", "D": "Ctrl + Alt + Delete"}	A	1	2
239	74	Which physical computer component acts as the "brain" of the computer?	mcq	{"A": "Hard Drive", "B": "CPU (Central Processing Unit)", "C": "Mouse", "D": "Power Cable"}	B	1	3
240	74	If you accidentally delete a paragraph in your document, which shortcut key acts like a "magic undo button"?	mcq	{"A": "Ctrl + S", "B": "Ctrl + V", "C": "Ctrl + Z", "D": "Ctrl + A"}	C	1	4
241	74	What is the computer screen that shows you picture, video, and text output called?	mcq	{"A": "Tower / Case", "B": "Monitor", "C": "Motherboard", "D": "RAM"}	B	1	5
242	74	Pressing Ctrl + V is used to paste text that you previously copied.	truefalse	\N	True	1	6
243	74	The computer mouse is used to move the pointer on your screen and click on items.	truefalse	\N	True	1	7
244	74	Pressing Ctrl + S saves your work so you don't lose it if the power goes out.	truefalse	\N	True	1	8
245	74	RAM (Memory) is the physical keyboard you type on.	truefalse	\N	False	1	9
246	74	Pressing Ctrl + A selects everything (all text or files) on your current screen.	truefalse	\N	True	1	10
247	74	Headphones / Speakers	matching	{"options": ["Closes an open window or app quickly", "Let\\u2019s you hear audio, music, or online lectures", "Opens the print menu to print a page quickly", "Prints your digital documents onto physical paper", "The long bar on the keyboard used to add spaces between words"]}	Let’s you hear audio, music, or online lectures	1	11
248	74	Printer	matching	{"options": ["Closes an open window or app quickly", "Let\\u2019s you hear audio, music, or online lectures", "Opens the print menu to print a page quickly", "Prints your digital documents onto physical paper", "The long bar on the keyboard used to add spaces between words"]}	Prints your digital documents onto physical paper	1	12
249	74	Spacebar	matching	{"options": ["Closes an open window or app quickly", "Let\\u2019s you hear audio, music, or online lectures", "Opens the print menu to print a page quickly", "Prints your digital documents onto physical paper", "The long bar on the keyboard used to add spaces between words"]}	The long bar on the keyboard used to add spaces between words	1	13
250	74	Ctrl + P	matching	{"options": ["Closes an open window or app quickly", "Let\\u2019s you hear audio, music, or online lectures", "Opens the print menu to print a page quickly", "Prints your digital documents onto physical paper", "The long bar on the keyboard used to add spaces between words"]}	Opens the print menu to print a page quickly	1	14
251	74	Alt + F4	matching	{"options": ["Closes an open window or app quickly", "Let\\u2019s you hear audio, music, or online lectures", "Opens the print menu to print a page quickly", "Prints your digital documents onto physical paper", "The long bar on the keyboard used to add spaces between words"]}	Closes an open window or app quickly	1	15
267	76	Which computer part is used to type letters, numbers, and symbols into a computer?	mcq	{"A": "Monitor", "B": "Keyboard", "C": "Mouse", "D": "Speaker"}	B	1	1
268	76	What keyboard shortcut is famous for making a quick copy of selected text?	mcq	{"A": "Ctrl + C", "B": "Ctrl + Z", "C": "Ctrl + P", "D": "Ctrl + Alt + Delete"}	A	1	2
269	76	Which physical computer component acts as the "brain" of the computer?	mcq	{"A": "Hard Drive", "B": "CPU (Central Processing Unit)", "C": "Mouse", "D": "Power Cable"}	B	1	3
270	76	If you accidentally delete a paragraph in your document, which shortcut key acts like a "magic undo button"?	mcq	{"A": "Ctrl + S", "B": "Ctrl + V", "C": "Ctrl + Z", "D": "Ctrl + A"}	C	1	4
271	76	What is the computer screen that shows you picture, video, and text output called?	mcq	{"A": "Tower / Case", "B": "Monitor", "C": "Motherboard", "D": "RAM"}	B	1	5
272	76	Pressing Ctrl + V is used to paste text that you previously copied.	truefalse	\N	True	1	6
273	76	The computer mouse is used to move the pointer on your screen and click on items.	truefalse	\N	True	1	7
274	76	Pressing Ctrl + S saves your work so you don't lose it if the power goes out.	truefalse	\N	True	1	8
275	76	RAM (Memory) is the physical keyboard you type on.	truefalse	\N	False	1	9
276	76	Pressing Ctrl + A selects everything (all text or files) on your current screen.	truefalse	\N	True	1	10
277	76	Headphones / Speakers	matching	{"options": ["Closes an open window or app quickly", "Let\\u2019s you hear audio, music, or online lectures", "Opens the print menu to print a page quickly", "Prints your digital documents onto physical paper", "The long bar on the keyboard used to add spaces between words"]}	Let’s you hear audio, music, or online lectures	1	11
282	77	Which computer part is used to type letters, numbers, and symbols into a computer?	mcq	{"A": "Monitor", "B": "Keyboard", "C": "Mouse", "D": "Speaker"}	B	1	1
283	77	What keyboard shortcut is famous for making a quick copy of selected text?	mcq	{"A": "Ctrl + C", "B": "Ctrl + Z", "C": "Ctrl + P", "D": "Ctrl + Alt + Delete"}	A	1	2
284	77	Which physical computer component acts as the "brain" of the computer?	mcq	{"A": "Hard Drive", "B": "CPU (Central Processing Unit)", "C": "Mouse", "D": "Power Cable"}	B	1	3
285	77	If you accidentally delete a paragraph in your document, which shortcut key acts like a "magic undo button"?	mcq	{"A": "Ctrl + S", "B": "Ctrl + V", "C": "Ctrl + Z", "D": "Ctrl + A"}	C	1	4
286	77	What is the computer screen that shows you picture, video, and text output called?	mcq	{"A": "Tower / Case", "B": "Monitor", "C": "Motherboard", "D": "RAM"}	B	1	5
287	77	Pressing Ctrl + V is used to paste text that you previously copied.	truefalse	\N	True	1	6
288	77	The computer mouse is used to move the pointer on your screen and click on items.	truefalse	\N	True	1	7
289	77	Pressing Ctrl + S saves your work so you don't lose it if the power goes out.	truefalse	\N	True	1	8
290	77	RAM (Memory) is the physical keyboard you type on.	truefalse	\N	False	1	9
291	77	Pressing Ctrl + A selects everything (all text or files) on your current screen.	truefalse	\N	True	1	10
297	82	bsbs	truefalse	\N	True	1	1
252	75	Which computer part is used to type letters, numbers, and symbols into a computer?	mcq	{"A": "Monitor", "B": "Keyboard", "C": "Mouse", "D": "Speaker"}	B	1	1
253	75	What keyboard shortcut is famous for making a quick copy of selected text?	mcq	{"A": "Ctrl + C", "B": "Ctrl + Z", "C": "Ctrl + P", "D": "Ctrl + Alt + Delete"}	A	1	2
254	75	Which physical computer component acts as the "brain" of the computer?	mcq	{"A": "Hard Drive", "B": "CPU (Central Processing Unit)", "C": "Mouse", "D": "Power Cable"}	B	1	3
255	75	If you accidentally delete a paragraph in your document, which shortcut key acts like a "magic undo button"?	mcq	{"A": "Ctrl + S", "B": "Ctrl + V", "C": "Ctrl + Z", "D": "Ctrl + A"}	C	1	4
256	75	What is the computer screen that shows you picture, video, and text output called?	mcq	{"A": "Tower / Case", "B": "Monitor", "C": "Motherboard", "D": "RAM"}	B	1	5
257	75	Pressing Ctrl + V is used to paste text that you previously copied.	truefalse	\N	True	1	6
258	75	The computer mouse is used to move the pointer on your screen and click on items.	truefalse	\N	True	1	7
259	75	Pressing Ctrl + S saves your work so you don't lose it if the power goes out.	truefalse	\N	True	1	8
260	75	RAM (Memory) is the physical keyboard you type on.	truefalse	\N	False	1	9
261	75	Pressing Ctrl + A selects everything (all text or files) on your current screen.	truefalse	\N	True	1	10
222	73	Which computer part is used to type letters, numbers, and symbols into a computer?	mcq	{"A": "Monitor", "B": "Keyboard", "C": "Mouse", "D": "Speaker"}	B	1	1
223	73	What keyboard shortcut is famous for making a quick copy of selected text?	mcq	{"A": "Ctrl + C", "B": "Ctrl + Z", "C": "Ctrl + P", "D": "Ctrl + Alt + Delete"}	A	1	2
224	73	Which physical computer component acts as the "brain" of the computer?	mcq	{"A": "Hard Drive", "B": "CPU (Central Processing Unit)", "C": "Mouse", "D": "Power Cable"}	B	1	3
197	67	Hi	mcq	{"A": "1", "B": "2", "C": "3", "D": "4"}	A	1	1
198	67	True	truefalse	\N	True	1	2
199	67	Exhibit	matching	{"options": ["Yes"]}	Yes	1	3
200	68	Ti	mcq	{"A": "Ta", "B": "To", "C": "Ba", "D": "Ho"}	A	1	1
201	68	Hi	truefalse	\N	True	1	2
202	68	Yes	matching	{"options": ["No"]}	No	1	3
203	69	a	truefalse	\N	True	1	1
204	69	b	truefalse	\N	True	1	2
205	69	c	truefalse	\N	True	1	3
206	69	d	truefalse	\N	True	1	4
207	69	e	truefalse	\N	True	1	5
208	70	a	truefalse	\N	True	1	1
209	70	b	truefalse	\N	True	1	2
210	70	c	truefalse	\N	True	1	3
211	71	a	truefalse	\N	True	1	1
212	71	b	truefalse	\N	True	1	2
213	71	c	truefalse	\N	True	1	3
214	71	d	truefalse	\N	True	1	4
215	71	e	truefalse	\N	True	1	5
225	73	If you accidentally delete a paragraph in your document, which shortcut key acts like a "magic undo button"?	mcq	{"A": "Ctrl + S", "B": "Ctrl + V", "C": "Ctrl + Z", "D": "Ctrl + A"}	C	1	4
226	73	What is the computer screen that shows you picture, video, and text output called?	mcq	{"A": "Tower / Case", "B": "Monitor", "C": "Motherboard", "D": "RAM"}	B	1	5
227	73	Pressing Ctrl + V is used to paste text that you previously copied.	truefalse	\N	True	1	6
228	73	The computer mouse is used to move the pointer on your screen and click on items.	truefalse	\N	True	1	7
229	73	Pressing Ctrl + S saves your work so you don't lose it if the power goes out.	truefalse	\N	True	1	8
230	73	RAM (Memory) is the physical keyboard you type on.	truefalse	\N	False	1	9
231	73	Pressing Ctrl + A selects everything (all text or files) on your current screen.	truefalse	\N	True	1	10
236	73	Alt + F4	matching	{"options": ["Closes an open window or app quickly", "Let\\u2019s you hear audio, music, or online lectures", "Opens the print menu to print a page quickly", "Prints your digital documents onto physical paper", "The long bar on the keyboard used to add spaces between words"]}	Closes an open window or app quickly	1	15
232	73	Headphones / Speakers	matching	{"options": ["Closes an open window or app quickly", "Let\\u2019s you hear audio, music, or online lectures", "Opens the print menu to print a page quickly", "Prints your digital documents onto physical paper", "The long bar on the keyboard used to add spaces between words"]}	Let’s you hear audio, music, or online lectures	1	11
233	73	Printer	matching	{"options": ["Closes an open window or app quickly", "Let\\u2019s you hear audio, music, or online lectures", "Opens the print menu to print a page quickly", "Prints your digital documents onto physical paper", "The long bar on the keyboard used to add spaces between words"]}	Prints your digital documents onto physical paper	1	12
234	73	Spacebar	matching	{"options": ["Closes an open window or app quickly", "Let\\u2019s you hear audio, music, or online lectures", "Opens the print menu to print a page quickly", "Prints your digital documents onto physical paper", "The long bar on the keyboard used to add spaces between words"]}	The long bar on the keyboard used to add spaces between words	1	13
235	73	Ctrl + P	matching	{"options": ["Closes an open window or app quickly", "Let\\u2019s you hear audio, music, or online lectures", "Opens the print menu to print a page quickly", "Prints your digital documents onto physical paper", "The long bar on the keyboard used to add spaces between words"]}	Opens the print menu to print a page quickly	1	14
262	75	Headphones / Speakers	matching	{"options": ["Closes an open window or app quickly", "Let\\u2019s you hear audio, music, or online lectures", "Opens the print menu to print a page quickly", "Prints your digital documents onto physical paper", "The long bar on the keyboard used to add spaces between words"]}	Let’s you hear audio, music, or online lectures	1	11
263	75	Printer	matching	{"options": ["Closes an open window or app quickly", "Let\\u2019s you hear audio, music, or online lectures", "Opens the print menu to print a page quickly", "Prints your digital documents onto physical paper", "The long bar on the keyboard used to add spaces between words"]}	Prints your digital documents onto physical paper	1	12
264	75	Spacebar	matching	{"options": ["Closes an open window or app quickly", "Let\\u2019s you hear audio, music, or online lectures", "Opens the print menu to print a page quickly", "Prints your digital documents onto physical paper", "The long bar on the keyboard used to add spaces between words"]}	The long bar on the keyboard used to add spaces between words	1	13
265	75	Ctrl + P	matching	{"options": ["Closes an open window or app quickly", "Let\\u2019s you hear audio, music, or online lectures", "Opens the print menu to print a page quickly", "Prints your digital documents onto physical paper", "The long bar on the keyboard used to add spaces between words"]}	Opens the print menu to print a page quickly	1	14
266	75	Alt + F4	matching	{"options": ["Closes an open window or app quickly", "Let\\u2019s you hear audio, music, or online lectures", "Opens the print menu to print a page quickly", "Prints your digital documents onto physical paper", "The long bar on the keyboard used to add spaces between words"]}	Closes an open window or app quickly	1	15
278	76	Printer	matching	{"options": ["Closes an open window or app quickly", "Let\\u2019s you hear audio, music, or online lectures", "Opens the print menu to print a page quickly", "Prints your digital documents onto physical paper", "The long bar on the keyboard used to add spaces between words"]}	Prints your digital documents onto physical paper	1	12
279	76	Spacebar	matching	{"options": ["Closes an open window or app quickly", "Let\\u2019s you hear audio, music, or online lectures", "Opens the print menu to print a page quickly", "Prints your digital documents onto physical paper", "The long bar on the keyboard used to add spaces between words"]}	The long bar on the keyboard used to add spaces between words	1	13
280	76	Ctrl + P	matching	{"options": ["Closes an open window or app quickly", "Let\\u2019s you hear audio, music, or online lectures", "Opens the print menu to print a page quickly", "Prints your digital documents onto physical paper", "The long bar on the keyboard used to add spaces between words"]}	Opens the print menu to print a page quickly	1	14
281	76	Alt + F4	matching	{"options": ["Closes an open window or app quickly", "Let\\u2019s you hear audio, music, or online lectures", "Opens the print menu to print a page quickly", "Prints your digital documents onto physical paper", "The long bar on the keyboard used to add spaces between words"]}	Closes an open window or app quickly	1	15
292	77	Headphones / Speakers	matching	{"options": ["Closes an open window or app quickly", "Let\\u2019s you hear audio, music, or online lectures", "Opens the print menu to print a page quickly", "Prints your digital documents onto physical paper", "The long bar on the keyboard used to add spaces between words"]}	Let’s you hear audio, music, or online lectures	1	11
293	77	Printer	matching	{"options": ["Closes an open window or app quickly", "Let\\u2019s you hear audio, music, or online lectures", "Opens the print menu to print a page quickly", "Prints your digital documents onto physical paper", "The long bar on the keyboard used to add spaces between words"]}	Prints your digital documents onto physical paper	1	12
294	77	Spacebar	matching	{"options": ["Closes an open window or app quickly", "Let\\u2019s you hear audio, music, or online lectures", "Opens the print menu to print a page quickly", "Prints your digital documents onto physical paper", "The long bar on the keyboard used to add spaces between words"]}	The long bar on the keyboard used to add spaces between words	1	13
295	77	Ctrl + P	matching	{"options": ["Closes an open window or app quickly", "Let\\u2019s you hear audio, music, or online lectures", "Opens the print menu to print a page quickly", "Prints your digital documents onto physical paper", "The long bar on the keyboard used to add spaces between words"]}	Opens the print menu to print a page quickly	1	14
296	77	Alt + F4	matching	{"options": ["Closes an open window or app quickly", "Let\\u2019s you hear audio, music, or online lectures", "Opens the print menu to print a page quickly", "Prints your digital documents onto physical paper", "The long bar on the keyboard used to add spaces between words"]}	Closes an open window or app quickly	1	15
\.


--
-- Data for Name: exam_results; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.exam_results (result_id, exam_id, enrollment_id, score, total_points, submitted_at, started_at, status, tab_switches, year_id) FROM stdin;
92	82	489	1.00	1	2026-10-06 02:08:44.164119	2026-10-06 01:38:36.856811	auto_submitted	18	\N
34	67	134	3.00	3	2026-08-19 07:34:08.257008	2026-08-19 07:33:49.061982	submitted	0	\N
35	68	134	3.00	3	2026-08-19 07:41:42.716732	2026-08-19 07:41:33.981652	submitted	0	\N
36	69	140	4.00	5	2026-08-19 11:40:27.299668	2026-08-19 11:39:22.310303	submitted	0	\N
49	73	143	11.00	15	2026-09-01 01:53:35.693182	2026-09-01 01:51:46.490872	submitted	0	\N
50	73	144	15.00	15	2026-09-01 01:57:51.781066	2026-09-01 01:56:12.836397	submitted	0	\N
51	73	145	8.00	15	2026-09-01 02:03:41.82471	2026-09-01 02:01:54.366849	submitted	1	\N
52	73	146	15.00	15	2026-09-01 02:13:31.382927	2026-09-01 02:11:01.566222	submitted	0	\N
55	73	148	15.00	15	2026-09-01 02:28:02.043059	2026-09-01 02:25:34.397524	submitted	0	\N
41	70	134	3.00	3	2026-08-20 08:35:06.485743	2026-08-20 08:34:17.764008	submitted	0	\N
78	76	489	1.00	15	2026-09-23 15:28:07.425633	2026-09-23 15:25:21.914633	auto_submitted	9	\N
79	77	489	12.00	15	2026-09-29 11:38:27.020608	2026-09-29 11:36:34.778184	submitted	3	\N
80	78	491	79.00	100	2026-10-01 02:38:58.118345	2026-10-01 02:38:58.118345	submitted	0	\N
43	71	134	5.00	5	2026-08-21 04:36:46.884097	2026-08-21 04:36:10.461224	submitted	3	\N
81	79	491	95.00	100	2026-10-01 02:38:58.118345	2026-10-01 02:38:58.118345	submitted	0	\N
82	78	490	90.00	100	2026-10-01 02:38:58.118345	2026-10-01 02:38:58.118345	submitted	0	\N
83	79	490	90.00	100	2026-10-01 02:38:58.118345	2026-10-01 02:38:58.118345	submitted	0	\N
60	74	491	100.00	100	2026-09-22 07:59:37.63728	2026-09-22 07:59:37.63728	submitted	0	\N
61	74	489	100.00	100	2026-09-22 07:59:37.63728	2026-09-22 07:59:37.63728	submitted	0	\N
84	78	489	95.00	100	2026-10-01 02:38:58.118345	2026-10-01 02:38:58.118345	submitted	0	\N
62	75	489	14.00	15	2026-09-22 08:03:59.482396	2026-09-22 08:02:13.690573	submitted	2	\N
85	79	489	89.00	100	2026-10-01 02:38:58.118345	2026-10-01 02:38:58.118345	submitted	0	\N
86	80	491	89.00	100	2026-10-01 02:39:51.528696	2026-10-01 02:39:51.528696	submitted	0	\N
87	81	491	90.00	100	2026-10-01 02:39:51.528696	2026-10-01 02:39:51.528696	submitted	0	\N
88	80	490	89.00	100	2026-10-01 02:39:51.528696	2026-10-01 02:39:51.528696	submitted	0	\N
89	81	490	98.00	100	2026-10-01 02:39:51.528696	2026-10-01 02:39:51.528696	submitted	0	\N
90	80	489	89.00	100	2026-10-01 02:39:51.528696	2026-10-01 02:39:51.528696	submitted	0	\N
91	81	489	90.00	100	2026-10-01 02:39:51.528696	2026-10-01 02:39:51.528696	submitted	0	\N
\.


--
-- Data for Name: exam_student_permissions; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.exam_student_permissions (permission_id, exam_id, enrollment_id, is_allowed) FROM stdin;
\.


--
-- Data for Name: exam_tab_switches; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.exam_tab_switches (id, result_id, switched_at, reason) FROM stdin;
44	43	2026-08-21 04:36:17.303439	page_hidden
45	43	2026-08-21 04:36:37.952073	page_hidden
46	43	2026-08-21 04:36:40.446605	window_blur
452	78	2026-09-23 15:25:54.809211	window_blur
453	78	2026-09-23 15:25:59.052094	window_blur
454	78	2026-09-23 15:26:02.393861	window_blur
57	51	2026-09-01 02:02:22.876043	window_blur
455	78	2026-09-23 15:26:05.799327	window_blur
456	78	2026-09-23 15:26:28.009158	fullscreen_exit
457	78	2026-09-23 15:26:57.818742	window_blur
458	78	2026-09-23 15:27:07.864067	fullscreen_exit
459	78	2026-09-23 15:27:14.570002	window_blur
460	78	2026-09-23 15:27:16.500033	fullscreen_exit
64	62	2026-09-22 08:02:24.490185	window_blur
65	62	2026-09-22 08:02:44.142926	window_blur
461	79	2026-09-29 11:36:48.468194	fullscreen_exit
462	79	2026-09-29 11:37:02.105839	fullscreen_exit
463	79	2026-09-29 11:37:04.949156	window_blur
464	92	2026-10-06 01:38:43.937672	window_blur
465	92	2026-10-06 01:40:18.748975	fullscreen_exit
466	92	2026-10-06 01:40:38.182547	window_blur
467	92	2026-10-06 01:40:41.004403	fullscreen_exit
468	92	2026-10-06 01:41:28.278064	window_blur
469	92	2026-10-06 01:41:59.163426	window_blur
470	92	2026-10-06 01:42:00.5157	fullscreen_exit
471	92	2026-10-06 01:45:18.624578	fullscreen_exit
472	92	2026-10-06 01:45:46.451577	window_blur
473	92	2026-10-06 01:46:43.635603	fullscreen_exit
474	92	2026-10-06 01:49:29.575147	window_blur
475	92	2026-10-06 01:51:21.747358	window_blur
476	92	2026-10-06 01:52:43.765466	window_blur
477	92	2026-10-06 01:53:12.991927	fullscreen_exit
478	92	2026-10-06 01:56:02.305596	window_blur
479	92	2026-10-06 01:58:59.554246	fullscreen_exit
480	92	2026-10-06 02:00:49.89806	window_blur
481	92	2026-10-06 02:01:26.282977	window_blur
\.


--
-- Data for Name: exams; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.exams (exam_id, branch_id, section_id, subject_id, teacher_id, title, exam_type, duration_mins, scheduled_date, status, created_at, question_limit, scheduled_start, scheduled_end, max_attempts, passing_score, instructions, randomize, grading_period, is_visible, batch_id, year_id, is_archived, class_mode) FROM stdin;
74	10	138	156	114	Quiz 1	quiz	30	\N	published	2026-09-22 07:27:11.38792	\N	2026-09-22 15:30:00	\N	1	75	\N	t	2nd	t	fad578ca	30	f	Virtual
75	10	138	156	114	Exam	exam	1	\N	published	2026-09-22 08:00:39.428617	\N	2026-09-22 16:00:00	\N	1	75	\N	t	2nd	t	f3352c0c	30	f	Virtual
76	10	138	156	114	Quiz 3	quiz	3	\N	published	2026-09-23 11:36:53.296089	\N	2026-09-23 19:37:00	\N	1	75	\N	f	2nd	t	352e1682	30	f	Virtual
68	4	84	22	86	Exhibit	exam	60	\N	published	2026-08-19 07:35:50.01522	\N	2026-08-19 15:35:00	\N	1	75	\N	f	1st	t	65738470	10	f	Virtual
77	10	138	156	114	Quiz 3	quiz	30	\N	published	2026-09-29 11:29:59.544968	\N	2026-09-29 19:29:00	\N	1	75	\N	t	2nd	t	0c27f4d4	30	f	Virtual
67	4	84	22	86	Exhibit Quiz	quiz	30	\N	published	2026-08-19 07:31:56.092833	\N	2026-08-19 15:31:00	\N	1	75	\N	t	1st	t	38b3ac05	10	f	Virtual
69	4	84	22	86	Quiz 2	quiz	30	\N	published	2026-08-19 11:38:32.763812	\N	2026-08-19 19:38:00	\N	1	75	\N	f	1st	t	316a5647	10	f	Virtual
78	10	138	156	114	Quiz 1	quiz	30	\N	draft	2026-10-01 02:38:32.318582	\N	\N	\N	1	75	\N	f	1st	f	\N	30	f	Virtual
79	10	138	156	114	Quiz 1	quiz	30	\N	draft	2026-10-01 02:38:33.905169	\N	\N	\N	1	75	\N	f	1st	f	\N	30	f	Virtual
70	4	84	22	86	PAQUIZZZZZZZZ	quiz	2	\N	published	2026-08-20 08:02:03.946451	\N	2026-08-20 16:03:00	\N	1	75	\N	f	1st	t	8a7372c8	10	f	Virtual
80	10	138	156	114	1st Term Periodical Exam	exam	30	\N	draft	2026-10-01 02:39:08.857546	\N	\N	\N	1	75	\N	f	1st	f	\N	30	f	Virtual
71	4	84	22	86	Quiz	quiz	30	\N	published	2026-08-21 04:29:31.033908	\N	2026-08-21 12:29:00	\N	1	75	\N	f	1st	t	d5bf3114	10	f	Virtual
81	10	138	156	114	1st Term Periodical Exam	exam	30	\N	draft	2026-10-01 02:39:24.372015	\N	\N	\N	1	75	\N	f	1st	f	\N	30	f	Virtual
82	10	138	156	114	haha	quiz	30	\N	published	2026-10-06 01:36:55.217438	\N	2026-10-06 09:36:00	\N	1	75	\N	t	2nd	t	ea209939	30	f	Virtual
73	10	85	33	114	Exhibit 2026	quiz	120	\N	published	2026-08-31 08:49:12.600307	\N	2026-09-01 10:42:00	\N	1	60	\N	t	1st	t	06170c64	26	f	Virtual
\.


--
-- Data for Name: failed_logins; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.failed_logins (id, ip_address, username, created_at) FROM stdin;
170	100.64.0.11	LDBB_0004	2026-10-06 01:37:45.129978
174	100.64.0.12	LDBB_Parent1	2026-10-08 03:17:22.540513
176	100.64.0.14	LDBB_Teacher	2026-10-08 07:21:58.555707
\.


--
-- Data for Name: finalized_grades; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.finalized_grades (id, enrollment_id, subject_id, grading_period, year_id, final_attendance_pct, final_participation_avg, finalized_at) FROM stdin;
\.


--
-- Data for Name: grade_levels; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.grade_levels (id, name, display_order, description, branch_id) FROM stdin;
37	Nursery	1	\N	1
38	Kinder	2	\N	1
39	Grade 1	3	\N	1
40	Grade 2	4	\N	1
41	Grade 3	5	\N	1
42	Grade 4	6	\N	1
43	Grade 5	7	\N	1
44	Grade 6	8	\N	1
45	Grade 7	9	\N	1
46	Grade 8	10	\N	1
47	Grade 9	11	\N	1
48	Grade 10	12	\N	1
75	Nursery	1	\N	4
76	Nursery	1	\N	10
77	Kinder	2	\N	10
78	Grade 1	3	\N	10
79	Grade 2	4	\N	10
80	Grade 3	5	\N	10
81	Grade 4	6	\N	10
82	Grade 5	7	\N	10
83	Grade 6	8	\N	10
84	Grade 7	9	\N	10
85	Grade 8	10	\N	10
86	Grade 9	11	\N	10
87	Grade 10	12	\N	10
90	Grade 11	13	\N	\N
91	Grade 12	14	\N	\N
96	Kinder	2	\N	4
100	Grade 11	13	\N	1
101	Grade 12	14	\N	1
245	Grade 12-STEM	15	\N	1
246	Grade 12-HUMSS	16	\N	1
247	Grade 12-GAS	17	\N	1
248	Grade 12-ABM	18	\N	1
172	Grade 11	13	\N	4
173	Grade 12	14	\N	4
174	Grade 11	13	\N	5
175	Grade 12	14	\N	5
176	Grade 11	13	\N	7
177	Grade 12	14	\N	7
178	Grade 11	13	\N	8
179	Grade 12	14	\N	8
180	Grade 11	13	\N	6
181	Grade 12	14	\N	6
182	Grade 11	13	\N	10
183	Grade 12	14	\N	10
\.


--
-- Data for Name: grade_overrides; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.grade_overrides (id, enrollment_id, section_id, subject_id, grading_period, year_id, override_ww, override_pt, override_qa, override_note, overridden_by, overridden_at) FROM stdin;
\.


--
-- Data for Name: grade_submission_requests; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.grade_submission_requests (id, section_id, subject_id, grading_period, year_id, branch_id, status, submitted_by, submitted_at, registrar_approved_by, registrar_approved_at, admin_approved_by, admin_approved_at, rejection_remarks, rejected_by, rejected_at) FROM stdin;
6	138	156	1st	30	10	pending_admin	114	2026-10-01 02:40:00.737351	111	2026-10-07 13:15:15.967378	\N	\N	\N	\N	\N
\.


--
-- Data for Name: grading_period_ranges; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.grading_period_ranges (id, branch_id, year_id, period_name, start_date, end_date, created_at) FROM stdin;
1	1	7	1st	2026-04-28	2026-06-15	2026-04-28 12:01:42.757101
2	1	7	2nd	2026-06-15	2026-08-18	2026-04-28 12:01:42.757101
3	1	7	3rd	2026-08-18	2026-10-20	2026-04-28 12:01:42.757101
4	1	7	4th	2026-10-20	2026-12-15	2026-04-28 12:01:42.757101
9	10	30	1st	2026-06-15	2026-09-04	2026-09-22 06:07:23.481881
10	10	30	2nd	2026-09-16	2026-12-18	2026-09-22 06:07:23.481881
11	10	30	3rd	2027-01-04	2027-04-23	2026-09-22 06:07:23.481881
12	1	18	1st	2026-06-08	2026-09-04	2026-10-03 00:45:54.09265
13	1	18	2nd	2026-09-16	2026-12-18	2026-10-03 00:45:54.09265
14	1	18	3rd	2027-01-04	2027-04-08	2026-10-03 00:45:54.09265
\.


--
-- Data for Name: grading_weights; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.grading_weights (id, teacher_id, section_id, subject_id, grading_period, quiz_pct, exam_pct, activity_pct, participation_pct, attendance_pct, created_at, weight_id, branch_id, updated_at, year_id) FROM stdin;
\.


--
-- Data for Name: holidays; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.holidays (id, branch_id, year_id, holiday_date, holiday_name, created_at, status) FROM stdin;
\.


--
-- Data for Name: individual_extensions; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.individual_extensions (extension_id, enrollment_id, item_type, item_id, new_due_date, created_at, student_id, year_id) FROM stdin;
7	140	quiz	70	2026-08-20 16:08:00	2026-08-20 08:07:46.643577	127	10
8	134	quiz	70	2026-08-20 16:34:00	2026-08-20 08:08:31.482902	107	10
9	134	activity	21	2026-08-28 12:45:00	2026-08-27 04:31:10.852201	107	10
10	489	quiz	76	2026-09-23 23:25:00	2026-09-23 12:14:34.864596	149	30
\.


--
-- Data for Name: inventory_item_sizes; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.inventory_item_sizes (size_id, item_id, size_label, stock_total, reserved_qty) FROM stdin;
49	94	XS	100	0
50	94	S	100	0
51	94	M	100	0
52	94	L	100	0
53	94	XL	100	0
54	94	XXL	100	0
55	95	XS	100	0
56	95	S	100	0
57	95	M	100	0
58	95	L	100	0
59	95	XL	100	0
60	95	XXL	100	0
61	96	XS	100	0
62	96	S	100	0
63	96	M	100	0
64	96	L	100	0
65	96	XL	100	0
66	96	XXL	100	0
67	97	XS	100	0
68	97	S	100	0
69	97	M	100	0
70	97	L	100	0
71	97	XL	100	0
72	97	XXL	100	0
73	98	XS	100	0
74	98	S	100	0
75	98	M	100	0
76	98	L	100	0
77	98	XL	100	0
78	98	XXL	100	0
79	99	XS	100	0
80	99	S	100	0
81	99	M	100	0
82	99	L	100	0
83	99	XL	100	0
84	99	XXL	100	0
85	100	XS	100	0
86	100	S	100	0
87	100	M	100	0
88	100	L	100	0
89	100	XL	100	0
90	100	XXL	100	0
91	101	XS	100	0
92	101	S	100	0
93	101	M	100	0
94	101	L	100	0
95	101	XL	100	0
96	101	XXL	100	0
481	1138	Free Size	10	0
\.


--
-- Data for Name: inventory_items; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.inventory_items (item_id, branch_id, category, item_name, grade_level, is_common, size_label, price, stock_total, reserved_qty, is_active, created_at, image_url, publisher, parent_item_id, is_set_piece, size_price_step) FROM stdin;
1138	8	UNIFORM	PE Uniform Set		t	\N	480.00	10	0	t	2026-04-29 07:10:34.626465	\N	\N	\N	f	20.00
1139	1	UNIFORM	Polo	\N	f	XS, S, M, L, XL, XXL, XXXL	450.00	0	0	t	2026-07-26 09:52:48.825424	\N	\N	96	t	20.00
1241	10	BOOK	Book	Nursery	f	FNB	455.00	10	0	t	2026-09-22 08:11:38.624665	\N	\N	\N	f	20.00
1154	1	UNIFORM	Skirt	\N	f	XS, S, M, L, XL, XXL, XXXL	430.00	0	0	t	2026-07-26 10:01:23.80708	\N	\N	100	t	20.00
112	1	BOOK	[NEO-ASIA] English-Phonics	Nursery	f	\N	460.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
114	1	BOOK	[NEO-ASIA] AP- Getting Ready Series "Sibika at Kultura" K1	Nursery	f	\N	460.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
115	1	BOOK	[JO-ES] Science- Exploring Science Kinder	Nursery	f	\N	619.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
116	1	BOOK	[SIBS] ESP- Mabuting Bata Magandang Pag-uugali	Nursery	f	\N	335.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
99	1	UNIFORM	SHS Boys Uniform Set	\N	f	\N	930.00	600	0	t	2026-04-28 12:30:21.939406	/static/img/SHS_BOYS_SET.jpg	\N	\N	f	20.00
98	1	UNIFORM	JHS Girls Uniform Set	\N	f	\N	930.00	600	0	t	2026-04-28 12:30:21.939406	/static/img/JHS_GIRLS_SET.jpg	\N	\N	f	20.00
100	1	UNIFORM	SHS Girls Uniform Set	\N	f	\N	900.00	600	0	t	2026-04-28 12:30:21.939406	/static/img/SHS_GIRLS_SET.jpg	\N	\N	f	20.00
95	1	UNIFORM	Pre-Elementary Girls Set	\N	f	\N	870.00	600	0	t	2026-04-28 12:30:21.939406	/static/img/PRE_ELEM_GIRLS_SET.jpg	\N	\N	f	20.00
101	1	UNIFORM	PE Uniform	\N	f	\N	970.00	600	0	t	2026-04-28 12:30:21.939406	/static/img/PE_SET.jpg	\N	\N	f	20.00
97	1	UNIFORM	JHS Boys Uniform Set	\N	f	\N	900.00	600	0	t	2026-04-28 12:30:21.939406	/static/img/JHS_BOYS_SET.jpg	\N	\N	f	20.00
94	1	UNIFORM	Pre-Elementary Boys Set	\N	f	\N	850.00	600	0	t	2026-04-28 12:30:21.939406	/static/img/PRE_ELEM_BOYS_SET.jpg	\N	\N	f	20.00
96	1	UNIFORM	Elementary G4-6 Boys Set	\N	f	\N	910.00	600	0	t	2026-04-28 12:30:21.939406	/static/img/ELEM_G4to6_BOYS_SET.jpg	\N	\N	f	20.00
117	1	BOOK	[N/A] Religion	Kinder	f	\N	580.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
194	1	BOOK	[EPHESIANS] Values Education-Marangal-Edukasyon sa Pagpapakatao	Grade 8	f	\N	600.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
144	1	BOOK	[REX] Makabansa-Lahing Pilipino Kaagapay sa Ika-21 Siglo	Grade 3	f	\N	779.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
145	1	BOOK	[JO-ES] GMRC- Tanglaw sa Kagandahang Asal at Wastong Pag-uugali	Grade 3	f	\N	610.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
147	1	BOOK	[Book Choice] ICT- Global Tech Computer Series 3/ Computer 101	Grade 3	f	\N	540.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
184	1	BOOK	[EPHESIANS] Values Education-Marangal	Grade 7	f	\N	600.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
141	1	BOOK	[DIWA] Filipino-Wikang Filipino sa Mabisang Kom.	Grade 3	f	\N	785.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
158	1	BOOK	[PHOENIX] Religion-MAPSA BSTSC:Jesus Sends Me...5	Grade 5	f	\N	640.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
159	1	BOOK	[DIWA] Filipino-Wikang Filipino sa Mabisang Kom.	Grade 5	f	\N	785.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
1140	1	UNIFORM	Pants	\N	f	XS, S, M, L, XL, XXL, XXXL	460.00	0	0	t	2026-07-26 09:53:55.182943	\N	\N	96	t	20.00
1156	4	UNIFORM	Polo	Nursery, Kinder, Grade 1-3	f	XS, S, M, L, XL, XXL, XXXL	450.00	0	0	t	2026-07-26 10:21:52.440868	\N	\N	1155	t	20.00
1157	4	UNIFORM	Pants	Nursery, Kinder, Grade 1-3	f	XS, S, M, L, XL, XXL, XXXL	460.00	0	0	t	2026-07-26 10:21:52.440868	\N	\N	1155	t	20.00
1159	4	UNIFORM	Blouse	Nursery, Kinder, Grade 1-6	f	XS, S, M, L, XL, XXL, XXXL	450.00	0	0	t	2026-07-26 10:21:52.440868	\N	\N	1158	t	20.00
1160	4	UNIFORM	Skirt	Nursery, Kinder, Grade 1-6	f	XS, S, M, L, XL, XXL, XXXL	460.00	0	0	t	2026-07-26 10:21:52.440868	\N	\N	1158	t	20.00
1162	4	UNIFORM	Polo	Grade 4-6	f	XS, S, M, L, XL, XXL, XXXL	450.00	0	0	t	2026-07-26 10:21:52.440868	\N	\N	1161	t	20.00
1163	4	UNIFORM	Pants	Grade 4-6	f	XS, S, M, L, XL, XXL, XXXL	460.00	0	0	t	2026-07-26 10:21:52.440868	\N	\N	1161	t	20.00
1165	4	UNIFORM	Polo	Grade 7-10	f	XS, S, M, L, XL, XXL, XXXL	500.00	0	0	t	2026-07-26 10:21:52.440868	\N	\N	1164	t	20.00
1166	4	UNIFORM	Pants	Grade 7-10	f	XS, S, M, L, XL, XXL, XXXL	520.00	0	0	t	2026-07-26 10:21:52.440868	\N	\N	1164	t	20.00
1168	4	UNIFORM	Blouse	Grade 7-10	f	XS, S, M, L, XL, XXL, XXXL	500.00	0	0	t	2026-07-26 10:21:52.440868	\N	\N	1167	t	20.00
1169	4	UNIFORM	Skirt	Grade 7-10	f	XS, S, M, L, XL, XXL, XXXL	550.00	0	0	t	2026-07-26 10:21:52.440868	\N	\N	1167	t	20.00
1171	4	UNIFORM	Polo	Grade 11-12	f	XS, S, M, L, XL, XXL, XXXL	550.00	0	0	t	2026-07-26 10:21:52.440868	\N	\N	1170	t	20.00
1172	4	UNIFORM	Pants	Grade 11-12	f	XS, S, M, L, XL, XXL, XXXL	580.00	0	0	t	2026-07-26 10:21:52.440868	\N	\N	1170	t	20.00
1174	4	UNIFORM	Blouse	Grade 11-12	f	XS, S, M, L, XL, XXL, XXXL	550.00	0	0	t	2026-07-26 10:21:52.440868	\N	\N	1173	t	20.00
1175	4	UNIFORM	Skirt	Grade 11-12	f	XS, S, M, L, XL, XXL, XXXL	600.00	0	0	t	2026-07-26 10:21:52.440868	\N	\N	1173	t	20.00
1177	4	UNIFORM	PE Shirt	All Grades	f	XS, S, M, L, XL, XXL, XXXL	400.00	0	0	t	2026-07-26 10:21:52.440868	\N	\N	1176	t	20.00
1178	4	UNIFORM	PE Pants	All Grades	f	XS, S, M, L, XL, XXL, XXXL	450.00	0	0	t	2026-07-26 10:21:52.440868	\N	\N	1176	t	20.00
1179	5	UNIFORM	Pre-Elementary Boys Set	Nursery, Kinder, Grade 1-3	f	XS, S, M, L, XL, XXL, XXXL	1000.00	0	0	t	2026-07-26 10:21:52.440868	/static/img/PRE_ELEM_BOYS_SET.jpg	\N	\N	f	20.00
1180	5	UNIFORM	Polo	Nursery, Kinder, Grade 1-3	f	XS, S, M, L, XL, XXL, XXXL	450.00	0	0	t	2026-07-26 10:21:52.440868	\N	\N	1179	t	20.00
142	1	BOOK	[PHOENIX] English- Integrated English for Effective Com.	Grade 3	f	\N	670.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
143	1	BOOK	[PHOENIX] Math-Realistic MathBasic Beyond Breakthrough	Grade 3	f	\N	910.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
180	1	BOOK	[PHOENIX] English-English Communication Arts & Skills	Grade 7	f	\N	505.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
1181	5	UNIFORM	Pants	Nursery, Kinder, Grade 1-3	f	XS, S, M, L, XL, XXL, XXXL	460.00	0	0	t	2026-07-26 10:21:52.440868	\N	\N	1179	t	20.00
1182	5	UNIFORM	Pre-Elementary Girls Set	Nursery, Kinder, Grade 1-6	f	XS, S, M, L, XL, XXL, XXXL	1000.00	0	0	t	2026-07-26 10:21:52.440868	/static/img/PRE_ELEM_GIRLS_SET.jpg	\N	\N	f	20.00
1183	5	UNIFORM	Blouse	Nursery, Kinder, Grade 1-6	f	XS, S, M, L, XL, XXL, XXXL	450.00	0	0	t	2026-07-26 10:21:52.440868	\N	\N	1182	t	20.00
170	1	BOOK	[REX] English-Essential English for Active Learners 2020	Grade 6	f	\N	629.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
156	1	BOOK	[REX] Science Links (Balatbat)	Grade 4	f	\N	779.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
111	1	BOOK	[JO-ES] Filipino- Binhi:Pinagyamang Edisyon	Nursery	f	\N	535.00	100	1	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
1184	5	UNIFORM	Skirt	Nursery, Kinder, Grade 1-6	f	XS, S, M, L, XL, XXL, XXXL	460.00	0	0	t	2026-07-26 10:21:52.440868	\N	\N	1182	t	20.00
1185	5	UNIFORM	Elementary G4-6 Boys Set	Grade 4-6	f	XS, S, M, L, XL, XXL, XXXL	1000.00	0	0	t	2026-07-26 10:21:52.440868	/static/img/ELEM_G4to6_BOYS_SET.jpg	\N	\N	f	20.00
1186	5	UNIFORM	Polo	Grade 4-6	f	XS, S, M, L, XL, XXL, XXXL	450.00	0	0	t	2026-07-26 10:21:52.440868	\N	\N	1185	t	20.00
1187	5	UNIFORM	Pants	Grade 4-6	f	XS, S, M, L, XL, XXL, XXXL	460.00	0	0	t	2026-07-26 10:21:52.440868	\N	\N	1185	t	20.00
1188	5	UNIFORM	JHS Boys Uniform Set	Grade 7-10	f	XS, S, M, L, XL, XXL, XXXL	1200.00	0	0	t	2026-07-26 10:21:52.440868	/static/img/JHS_BOYS_SET.jpg	\N	\N	f	20.00
1189	5	UNIFORM	Polo	Grade 7-10	f	XS, S, M, L, XL, XXL, XXXL	500.00	0	0	t	2026-07-26 10:21:52.440868	\N	\N	1188	t	20.00
1190	5	UNIFORM	Pants	Grade 7-10	f	XS, S, M, L, XL, XXL, XXXL	520.00	0	0	t	2026-07-26 10:21:52.440868	\N	\N	1188	t	20.00
1191	5	UNIFORM	JHS Girls Uniform Set	Grade 7-10	f	XS, S, M, L, XL, XXL, XXXL	1250.00	0	0	t	2026-07-26 10:21:52.440868	/static/img/JHS_GIRLS_SET.jpg	\N	\N	f	20.00
1192	5	UNIFORM	Blouse	Grade 7-10	f	XS, S, M, L, XL, XXL, XXXL	500.00	0	0	t	2026-07-26 10:21:52.440868	\N	\N	1191	t	20.00
1193	5	UNIFORM	Skirt	Grade 7-10	f	XS, S, M, L, XL, XXL, XXXL	550.00	0	0	t	2026-07-26 10:21:52.440868	\N	\N	1191	t	20.00
1194	5	UNIFORM	SHS Boys Uniform Set	Grade 11-12	f	XS, S, M, L, XL, XXL, XXXL	1300.00	0	0	t	2026-07-26 10:21:52.440868	/static/img/SHS_BOYS_SET.jpg	\N	\N	f	20.00
1195	5	UNIFORM	Polo	Grade 11-12	f	XS, S, M, L, XL, XXL, XXXL	550.00	0	0	t	2026-07-26 10:21:52.440868	\N	\N	1194	t	20.00
1196	5	UNIFORM	Pants	Grade 11-12	f	XS, S, M, L, XL, XXL, XXXL	580.00	0	0	t	2026-07-26 10:21:52.440868	\N	\N	1194	t	20.00
1197	5	UNIFORM	SHS Girls Uniform Set	Grade 11-12	f	XS, S, M, L, XL, XXL, XXXL	1350.00	0	0	t	2026-07-26 10:21:52.440868	/static/img/SHS_GIRLS_SET.jpg	\N	\N	f	20.00
1198	5	UNIFORM	Blouse	Grade 11-12	f	XS, S, M, L, XL, XXL, XXXL	550.00	0	0	t	2026-07-26 10:21:52.440868	\N	\N	1197	t	20.00
1199	5	UNIFORM	Skirt	Grade 11-12	f	XS, S, M, L, XL, XXL, XXXL	600.00	0	0	t	2026-07-26 10:21:52.440868	\N	\N	1197	t	20.00
1141	1	UNIFORM	Polo	\N	f	XS, S, M, L, XL, XXL, XXXL	450.00	0	0	t	2026-07-26 09:54:35.013301	\N	\N	97	t	20.00
1200	5	UNIFORM	PE Uniform	All Grades	f	XS, S, M, L, XL, XXL, XXXL	850.00	0	0	t	2026-07-26 10:21:52.440868	/static/img/PE_SET.jpg	\N	\N	f	20.00
1201	5	UNIFORM	PE Shirt	All Grades	f	XS, S, M, L, XL, XXL, XXXL	400.00	0	0	t	2026-07-26 10:21:52.440868	\N	\N	1200	t	20.00
1202	5	UNIFORM	PE Pants	All Grades	f	XS, S, M, L, XL, XXL, XXXL	450.00	0	0	t	2026-07-26 10:21:52.440868	\N	\N	1200	t	20.00
1203	7	UNIFORM	Pre-Elementary Boys Set	Nursery, Kinder, Grade 1-3	f	XS, S, M, L, XL, XXL, XXXL	1000.00	0	0	t	2026-07-26 10:21:52.440868	/static/img/PRE_ELEM_BOYS_SET.jpg	\N	\N	f	20.00
1204	7	UNIFORM	Polo	Nursery, Kinder, Grade 1-3	f	XS, S, M, L, XL, XXL, XXXL	450.00	0	0	t	2026-07-26 10:21:52.440868	\N	\N	1203	t	20.00
1205	7	UNIFORM	Pants	Nursery, Kinder, Grade 1-3	f	XS, S, M, L, XL, XXL, XXXL	460.00	0	0	t	2026-07-26 10:21:52.440868	\N	\N	1203	t	20.00
1206	7	UNIFORM	Pre-Elementary Girls Set	Nursery, Kinder, Grade 1-6	f	XS, S, M, L, XL, XXL, XXXL	1000.00	0	0	t	2026-07-26 10:21:52.440868	/static/img/PRE_ELEM_GIRLS_SET.jpg	\N	\N	f	20.00
1207	7	UNIFORM	Blouse	Nursery, Kinder, Grade 1-6	f	XS, S, M, L, XL, XXL, XXXL	450.00	0	0	t	2026-07-26 10:21:52.440868	\N	\N	1206	t	20.00
1208	7	UNIFORM	Skirt	Nursery, Kinder, Grade 1-6	f	XS, S, M, L, XL, XXL, XXXL	460.00	0	0	t	2026-07-26 10:21:52.440868	\N	\N	1206	t	20.00
1209	7	UNIFORM	Elementary G4-6 Boys Set	Grade 4-6	f	XS, S, M, L, XL, XXL, XXXL	1000.00	0	0	t	2026-07-26 10:21:52.440868	/static/img/ELEM_G4to6_BOYS_SET.jpg	\N	\N	f	20.00
1210	7	UNIFORM	Polo	Grade 4-6	f	XS, S, M, L, XL, XXL, XXXL	450.00	0	0	t	2026-07-26 10:21:52.440868	\N	\N	1209	t	20.00
1211	7	UNIFORM	Pants	Grade 4-6	f	XS, S, M, L, XL, XXL, XXXL	460.00	0	0	t	2026-07-26 10:21:52.440868	\N	\N	1209	t	20.00
1212	7	UNIFORM	JHS Boys Uniform Set	Grade 7-10	f	XS, S, M, L, XL, XXL, XXXL	1200.00	0	0	t	2026-07-26 10:21:52.440868	/static/img/JHS_BOYS_SET.jpg	\N	\N	f	20.00
1213	7	UNIFORM	Polo	Grade 7-10	f	XS, S, M, L, XL, XXL, XXXL	500.00	0	0	t	2026-07-26 10:21:52.440868	\N	\N	1212	t	20.00
1214	7	UNIFORM	Pants	Grade 7-10	f	XS, S, M, L, XL, XXL, XXXL	520.00	0	0	t	2026-07-26 10:21:52.440868	\N	\N	1212	t	20.00
1215	7	UNIFORM	JHS Girls Uniform Set	Grade 7-10	f	XS, S, M, L, XL, XXL, XXXL	1250.00	0	0	t	2026-07-26 10:21:52.440868	/static/img/JHS_GIRLS_SET.jpg	\N	\N	f	20.00
1216	7	UNIFORM	Blouse	Grade 7-10	f	XS, S, M, L, XL, XXL, XXXL	500.00	0	0	t	2026-07-26 10:21:52.440868	\N	\N	1215	t	20.00
1217	7	UNIFORM	Skirt	Grade 7-10	f	XS, S, M, L, XL, XXL, XXXL	550.00	0	0	t	2026-07-26 10:21:52.440868	\N	\N	1215	t	20.00
1218	7	UNIFORM	SHS Boys Uniform Set	Grade 11-12	f	XS, S, M, L, XL, XXL, XXXL	1300.00	0	0	t	2026-07-26 10:21:52.440868	/static/img/SHS_BOYS_SET.jpg	\N	\N	f	20.00
1219	7	UNIFORM	Polo	Grade 11-12	f	XS, S, M, L, XL, XXL, XXXL	550.00	0	0	t	2026-07-26 10:21:52.440868	\N	\N	1218	t	20.00
1220	7	UNIFORM	Pants	Grade 11-12	f	XS, S, M, L, XL, XXL, XXXL	580.00	0	0	t	2026-07-26 10:21:52.440868	\N	\N	1218	t	20.00
1221	7	UNIFORM	SHS Girls Uniform Set	Grade 11-12	f	XS, S, M, L, XL, XXL, XXXL	1350.00	0	0	t	2026-07-26 10:21:52.440868	/static/img/SHS_GIRLS_SET.jpg	\N	\N	f	20.00
1222	7	UNIFORM	Blouse	Grade 11-12	f	XS, S, M, L, XL, XXL, XXXL	550.00	0	0	t	2026-07-26 10:21:52.440868	\N	\N	1221	t	20.00
1223	7	UNIFORM	Skirt	Grade 11-12	f	XS, S, M, L, XL, XXL, XXXL	600.00	0	0	t	2026-07-26 10:21:52.440868	\N	\N	1221	t	20.00
1224	7	UNIFORM	PE Uniform	All Grades	f	XS, S, M, L, XL, XXL, XXXL	850.00	0	0	t	2026-07-26 10:21:52.440868	/static/img/PE_SET.jpg	\N	\N	f	20.00
1225	7	UNIFORM	PE Shirt	All Grades	f	XS, S, M, L, XL, XXL, XXXL	400.00	0	0	t	2026-07-26 10:21:52.440868	\N	\N	1224	t	20.00
113	1	BOOK	[JO-ES] Math- Math Builders	Nursery	f	\N	650.00	100	1	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
171	1	BOOK	[PHOENIX-SIBS] Math Buddies	Grade 6	f	\N	570.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
130	1	BOOK	[JO-ES] GMRC- Tanglaw sa kagandahang Asal at Wastong Pag-uugali	Grade 1	f	\N	560.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
192	1	BOOK	[REX] AP-Kayamanan - Ang Asya at Daigdig	Grade 8	f	\N	749.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
195	1	BOOK	[REX] ICT- D-Whiz in ICT Skills Dev't.	Grade 8	f	\N	599.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
1226	7	UNIFORM	PE Pants	All Grades	f	XS, S, M, L, XL, XXL, XXXL	450.00	0	0	t	2026-07-26 10:21:52.440868	\N	\N	1224	t	20.00
110	1	BOOK	[FNB] Religion	Nursery	f	\N	323.00	99	3	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
1242	10	BOOK	Ibong adarna	Nursery	f	FNB	100.00	100	0	t	2026-09-29 11:25:46.367331	\N	\N	\N	f	20.00
1142	1	UNIFORM	Pants	\N	f	XS, S, M, L, XL, XXL, XXXL	450.00	0	0	t	2026-07-26 09:54:48.893595	\N	\N	97	t	20.00
169	1	BOOK	[SIBS] Filipino- Pintig ng Lahing Pilipino Ikalawang Edisyon	Grade 6	f	\N	755.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
165	1	BOOK	[Book Choice] ICT-Global Tech Computer Series 5 Computer Application	Grade 5	f	\N	540.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
205	1	BOOK	[REX] ICT- D-Whiz /PROSKILLS	Grade 9	f	\N	657.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
201	1	BOOK	[DIWA] Math-Mathematics for Innovative Minds	Grade 9	f	\N	885.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
139	1	BOOK	[Book Choice] ICT- Global Tech Computer Series-Intro.to Comp.	Grade 2	f	\N	540.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
154	1	BOOK	[JO-ES] GMRC-Tanglaw sa kagandahang Asal at Wastong Pag-uugali	Grade 4	f	\N	560.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
162	1	BOOK	[REX] AP-Lahing Pilipino Kaagapay sa Ika-21 Siglo	Grade 5	f	\N	779.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
163	1	BOOK	[REX] MAPEH- Expeditions in MAPEH	Grade 5	f	\N	679.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
1167	4	UNIFORM	JHS Girls Uniform Set	Grade 7-10	f	XS, S, M, L, XL, XXL, XXXL	1050.00	0	0	t	2026-07-26 10:21:52.440868	/static/img/JHS_GIRLS_SET.jpg	\N	\N	f	20.00
1164	4	UNIFORM	JHS Boys Uniform Set	Grade 7-10	f	XS, S, M, L, XL, XXL, XXXL	1020.00	0	0	t	2026-07-26 10:21:52.440868	/static/img/JHS_BOYS_SET.jpg	\N	\N	f	20.00
1173	4	UNIFORM	SHS Girls Uniform Set	Grade 11-12	f	XS, S, M, L, XL, XXL, XXXL	1150.00	0	0	t	2026-07-26 10:21:52.440868	/static/img/SHS_GIRLS_SET.jpg	\N	\N	f	20.00
1158	4	UNIFORM	Pre-Elementary Girls Set	Nursery, Kinder, Grade 1-6	f	XS, S, M, L, XL, XXL, XXXL	910.00	0	0	t	2026-07-26 10:21:52.440868	/static/img/PRE_ELEM_GIRLS_SET.jpg	\N	\N	f	20.00
1155	4	UNIFORM	Pre-Elementary Boys Set	Nursery, Kinder, Grade 1-3	f	XS, S, M, L, XL, XXL, XXXL	910.00	0	0	t	2026-07-26 10:21:52.440868	/static/img/PRE_ELEM_BOYS_SET.jpg	\N	\N	f	20.00
1143	1	UNIFORM	Blouse	\N	f	XS, S, M, L, XL, XXL, XXXL	460.00	0	0	t	2026-07-26 09:55:52.863787	\N	\N	98	t	20.00
1227	4	BOOK	GMRC	Nursery	f	FNB	400.00	100	4	t	2026-08-19 07:54:28.295351	\N	\N	\N	f	20.00
1230	10	UNIFORM	Nursery-Kinder Unifrom Set (Boy)	Pre-Elementary	f	XS, S, M, L, XL, XXL, XXXL	1000.00	0	0	t	2026-08-31 08:55:15.170055	https://scontent.fpag2-1.fna.fbcdn.net/v/t1.15752-9/789005585_1591991295806037_4104727695058041962_n.jpg?_nc_cat=111&ccb=1-7&_nc_sid=9f807c&_nc_eui2=AeHNuFwj837xHJ1VCH6ktd7GSRDwA7SZedRJEPADtJl51OMzwJjMlQm8cRu3IkO1PRR9_jCHCST2unbiXNUZSRPZ&_nc_ohc=IUgvEaPYfosQ7kNvwH8AVQA&_nc_oc=AdoYFdE0LLmlHcLo9L1LpxiyKGMjOcrcaasq6cuM_fYmi61zScXQDM9utDLBvcOEE6E&_nc_zt=23&_nc_ht=scontent.fpag2-1.fna&_nc_ss=7b2a8&oh=03_Q7cD6QEMmxB5eq2PFqdvSqOLTJiGvv0vGkXmln9P_6iO3jk56Q&oe=6ABCC601	\N	\N	f	20.00
148	1	BOOK	[PHOENIX] Religion-MAPSA BSTSC: Jesus Sends Me...4	Grade 4	f	\N	640.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
151	1	BOOK	[PHOENIX] Realistic Math	Grade 4	f	\N	875.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
202	1	BOOK	[Brilliant] AP- Ugnayan at Kaunlaran 9:Ekonomiks	Grade 9	f	\N	610.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
203	1	BOOK	[Vibal] MAPEH- Living with Music Art Physical and Health	Grade 9	f	\N	750.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
204	1	BOOK	[EPHESIANS] ESP- Marangal	Grade 9	f	\N	555.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
166	1	BOOK	[REX] Science Links (Balatbat)	Grade 5	f	\N	779.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
167	1	BOOK	[FnB] EPP-Tagumpay	Grade 5	f	\N	573.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
168	1	BOOK	[FNB] Religion-Christian Life Education Series 4th Ed.	Grade 6	f	\N	600.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
210	1	BOOK	[ABIVA] English-English in Perspective	Grade 10	f	\N	705.00	99	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
1144	1	UNIFORM	Palda	\N	f	XS, S, M, L, XL, XXL, XXXL	470.00	0	0	t	2026-07-26 09:56:05.006045	\N	\N	98	t	20.00
1228	4	UNIFORM	Test	Pre-Elementary	f	XS, S, M, L, XL, XXL, XXXL	31.00	0	0	t	2026-08-22 06:00:58.300942	\N	\N	\N	f	20.00
1231	10	UNIFORM	Polo	Pre-Elementary	f	XS, S, M, L, XL, XXL, XXXL	500.00	0	0	t	2026-08-31 08:55:57.87151	\N	\N	1230	t	20.00
196	1	BOOK	[REX] Science-Science Links	Grade 8	f	\N	799.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
197	1	BOOK	[PISARA] TLE-TLE 8 Building Foundations	Grade 8	f	\N	870.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
146	1	BOOK	[REX] Science- Science Links	Grade 3	f	\N	779.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
164	1	BOOK	[JO-ES] GMRC-Tanglaw sa kagandahang Asal at Wastong Pag-uugali	Grade 5	f	\N	560.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
207	1	BOOK	[Inteligente] TLE- SPICE Book 1	Grade 9	f	\N	510.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
208	1	BOOK	[Vicarish] Religion-Christian Living: Evangelizers	Grade 10	f	\N	595.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
209	1	BOOK	[REX] Filipino- Punla: Mga Akdang Panitikan	Grade 10	f	\N	709.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
1145	1	UNIFORM	PE Pants	\N	f	XS, S, M, L, XL, XXL, XXXL	480.00	0	0	t	2026-07-26 09:57:12.669547	\N	\N	101	t	20.00
1232	10	UNIFORM	Short	Pre-Elementary	f	XS, S, M, L, XL, XXL, XXXL	500.00	0	0	t	2026-08-31 08:56:09.460271	\N	\N	1230	t	20.00
1176	4	UNIFORM	PE Uniform	All Grades	f	XS, S, M, L, XL, XXL, XXXL	850.00	0	0	t	2026-07-26 10:21:52.440868	/static/img/PE_SET.jpg	\N	\N	f	20.00
1161	4	UNIFORM	Elementary G4-6 Boys Set	Grade 4-6	f	XS, S, M, L, XL, XXL, XXXL	910.00	0	0	t	2026-07-26 10:21:52.440868	/static/img/ELEM_G4to6_BOYS_SET.jpg	\N	\N	f	20.00
1170	4	UNIFORM	SHS Boys Uniform Set	Grade 11-12	f	XS, S, M, L, XL, XXL, XXXL	1130.00	0	0	t	2026-07-26 10:21:52.440868	/static/img/SHS_BOYS_SET.jpg	\N	\N	f	20.00
211	1	BOOK	[DIWA] Math-Mathematics for Innovative Minds	Grade 10	f	\N	885.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
213	1	BOOK	[Vibal] MAPEH- Living with Music Art Physical and Health	Grade 10	f	\N	750.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
182	1	BOOK	[REX] AP-Kayamanan - Pilipinas sa Timog Silangang Asya	Grade 7	f	\N	749.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
183	1	BOOK	[REX] MAPEH- Expeditions in MAPEH	Grade 7	f	\N	699.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
175	1	BOOK	[Book Choice] ICT-CYBERWORLD I.T. ESSENTIALS Computer Knowledge	Grade 6	f	\N	540.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
1146	1	UNIFORM	PE Shirt	\N	f	XS, S, M, L, XL, XXL, XXXL	490.00	0	0	t	2026-07-26 09:57:26.689592	\N	\N	101	t	20.00
1233	10	BOOK	Religion	Nursery	f	FNB	323.00	98	0	t	2026-08-31 09:02:19.969815	\N	\N	\N	f	20.00
214	1	BOOK	[EPHESIANS] ESP- Marangal	Grade 10	f	\N	555.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
215	1	BOOK	[REX] ICT- D-Whiz/ PROSKILLS	Grade 10	f	\N	599.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
216	1	BOOK	[REX] Science- Science Links	Grade 10	f	\N	729.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
217	1	BOOK	[Inteligente] TLE- SPICE Book 2	Grade 10	f	\N	540.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
199	1	BOOK	[REX] Filipino- Punla: Mga Akdang Panitikan	Grade 9	f	\N	709.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
200	1	BOOK	[ABIVA] English-English in Perspective	Grade 9	f	\N	705.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
157	1	BOOK	[FnB] EPP-Tagumpay	Grade 4	f	\N	573.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
135	1	BOOK	[PHOENIX] English- Integrated English for Effective Com.	Grade 2	f	\N	670.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
136	1	BOOK	[PHOENIX] Math- Realistic MathBasic Beyond Breakthrough	Grade 2	f	\N	905.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
137	1	BOOK	[REX] Makabansa- Lahing Pilipino Kaagapay sa Ika-21 Siglo	Grade 2	f	\N	779.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
138	1	BOOK	[JO-ES] GMRC- Tanglaw sa Kagandahang Asal at Wastong Pag-uugali	Grade 2	f	\N	560.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
1147	1	UNIFORM	Polo	\N	f	XS, S, M, L, XL, XXL, XXXL	430.00	0	0	t	2026-07-26 09:58:11.315901	\N	\N	94	t	20.00
172	1	BOOK	[ABIVA] AP- Kamalayang Panlipunan	Grade 6	f	\N	635.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
173	1	BOOK	[EPHESIANS] MAPEH- The Joy of MAPEH	Grade 6	f	\N	670.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
174	1	BOOK	[JO-ES] ESP- Dakilang Pag-asa	Grade 6	f	\N	380.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
1234	10	UNIFORM	Pre-Elem Girl's Uniform	Pre-Elementary	f	XS, S, M, L, XL, XXL, XXXL	1000.00	0	0	t	2026-08-31 12:23:16.056007	https://scontent.fmnl13-6.fna.fbcdn.net/v/t1.15752-9/790266415_830837940056997_2185176685042107355_n.jpg?_nc_cat=104&ccb=1-7&_nc_sid=9f807c&_nc_eui2=AeHWXzPj1kng-GxMBtIEmogMecc19ctsRp15xzX1y2xGneAkCox4_7-MfoxuKjELhgR1slTpjxGtyCFukYndP6xx&_nc_ohc=RhC8VsvfjuQQ7kNvwHENbws&_nc_oc=AdoKHxGnMuwVQxIPYwwEnzZrVX7q7rrQhhXMqCuEH3Qtci_hlmnzStfhcpB4GGAwQ9nl18qHaVyA-QQDnHuSdDYL&_nc_zt=23&_nc_ht=scontent.fmnl13-6.fna&_nc_ss=7b2a8&oh=03_Q7cD6QGO68bMN711b9V4Vh98TzjBw2fFLk7pLL3vqGCy5E8exA&oe=6ABCEA35	\N	\N	f	20.00
212	1	BOOK	[Brilliant] AP- Ugnayan at Kaunlaran 10:Isyu ng Lipunan	Grade 10	f	\N	610.00	99	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
1148	1	UNIFORM	Short	\N	f	XS, S, M, L, XL, XXL, XXXL	420.00	0	0	t	2026-07-26 09:58:26.059844	\N	\N	94	t	20.00
1235	10	BOOK	Filipino	Nursery	f	JO-ES	535.00	100	0	t	2026-08-31 12:43:51.653648	\N	\N	\N	f	20.00
160	1	BOOK	[PHOENIX] English-Integrated English for Effective Communication	Grade 5	f	\N	670.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
161	1	BOOK	[PHOENIX] Realistic Math	Grade 5	f	\N	875.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
1149	1	UNIFORM	Blouse	\N	f	XS, S, M, L, XL, XXL, XXXL	430.00	0	0	t	2026-07-26 09:59:31.715683	\N	\N	95	t	20.00
1236	10	BOOK	English-Phonics	Nursery	f	NEO-ASIA	460.00	100	1	t	2026-08-31 12:44:31.980353	\N	\N	\N	f	20.00
179	1	BOOK	[DIWA] Filipino- Filipino sa Modernong Panahon	Grade 7	f	\N	885.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
206	1	BOOK	[REX] Science- Science Links	Grade 9	f	\N	729.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
186	1	BOOK	[REX] Science Links	Grade 7	f	\N	799.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
125	1	BOOK	[PHOENIX] Religion-MAPSA BSTSC: I Believe in Jesus 1	Grade 1	f	\N	620.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
126	1	BOOK	[PHOENIX] Language- Integrated English for Effective Com.-3rd Ed	Grade 1	f	\N	440.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
127	1	BOOK	[PHOENIX] Reading and Literacy-Integrated Eng.for Effective Com.3rdEd	Grade 1	f	\N	460.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
128	1	BOOK	[PHOENIX] Mathematics-Realistic Math	Grade 1	f	\N	890.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
129	1	BOOK	[REX] MAKABANSA- Lahing Pilipino(Unang Edisyon)	Grade 1	f	\N	779.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
1150	1	UNIFORM	Padla	\N	f	XS, S, M, L, XL, XXL, XXXL	440.00	0	0	t	2026-07-26 09:59:41.047101	\N	\N	95	t	20.00
1237	10	BOOK	Math-Math Builders	Nursery	f	JO-ES	650.00	100	0	t	2026-08-31 12:45:21.431048	\N	\N	\N	f	20.00
155	1	BOOK	[Book Choice] ICT-Global Tech Computer Series MS Office Application	Grade 4	f	\N	540.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
118	1	BOOK	[ABIVA] MAKABANSA(AP)-Serye ng Hakbang sa Pag-unlad	Kinder	f	\N	435.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
119	1	BOOK	[The Library] LANGUAGE/READING/WRITING-Smart Language K1	Kinder	f	\N	430.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
120	1	BOOK	[N/A] Learn Ahead in Reading K1	Kinder	f	\N	435.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
121	1	BOOK	[N/A] Basic Writing for Early Learners(K)	Kinder	f	\N	450.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
122	1	BOOK	[ABIVA] SCIENCE-Ladders to Learning Series K	Kinder	f	\N	435.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
123	1	BOOK	[The Library] MATHEMATICS-Global Mathematics K	Kinder	f	\N	445.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
193	1	BOOK	[REX] MAPEH- Expeditions in MAPEH	Grade 8	f	\N	699.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
149	1	BOOK	[DIWA] Filipino-Wikang Filipino sa Mabisang Kom.	Grade 4	f	\N	785.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
150	1	BOOK	[PHOENIX] English-Integrated English for Effective Communication	Grade 4	f	\N	670.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
152	1	BOOK	[REX] AP-Lahing Pilipino Kaagapay sa Ika-21 Siglo	Grade 4	f	\N	779.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
185	1	BOOK	[SPDCSS] ICT- Module	Grade 7	f	\N	0.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
1151	1	UNIFORM	Polo	\N	f	XS, S, M, L, XL, XXL, XXXL	470.00	0	0	t	2026-07-26 10:00:39.594242	\N	\N	99	t	20.00
132	1	BOOK	[ABIVA] SRA	Grade 1	f	\N	390.00	101	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
1238	10	BOOK	AP	Nursery	f	NEO-ASIA	460.00	100	1	t	2026-08-31 12:46:40.641766	\N	\N	\N	f	20.00
131	1	BOOK	[Book Choice] ICT-CYBERWORLD I.T. ESSENTIALS Getting to Know My Computer	Grade 1	f	\N	540.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
133	1	BOOK	[PHOENIX] Religion-MAPSA BSTSC: I Grow in Jesus 2	Grade 2	f	\N	620.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
134	1	BOOK	[DIWA] Filipino-Wikang Filipino sa Mabisang Kom.	Grade 2	f	\N	785.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
176	1	BOOK	[TECHFACTOR] Science-Science Tek Inquiry-based Approach	Grade 6	f	\N	750.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
177	1	BOOK	[FNB] EPP- Tagumpay	Grade 6	f	\N	605.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
178	1	BOOK	[PHOENIX] Religion-MAPSA CLE-BTSC: Jesus Announces God...7	Grade 7	f	\N	620.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
1152	1	UNIFORM	Pants	\N	f	XS, S, M, L, XL, XXL, XXXL	460.00	0	0	t	2026-07-26 10:00:48.622875	\N	\N	99	t	20.00
1239	10	BOOK	Science- Exploring Science	Nursery	f	JO-ES	619.00	100	0	t	2026-08-31 12:47:49.321399	\N	\N	\N	f	20.00
153	1	BOOK	[REX] MAPEH- Expeditions in MAPEH	Grade 4	f	\N	679.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
187	1	BOOK	[PISARA] TLE	Grade 7	f	\N	680.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
181	1	BOOK	[PHOENIX] Mathematics- Realistic Math	Grade 7	f	\N	580.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
198	1	BOOK	[Vicarish] Religion-Christian Living: Sent Forth	Grade 9	f	\N	630.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
140	1	BOOK	[PHOENIX] Religion-MAPSA BSTSC: I Celebrate Jesus 3	Grade 3	f	\N	620.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
188	1	BOOK	[PHOENIX] Religion-MAPSA CLE-BTSC: Jesus Conveys God...8	Grade 8	f	\N	640.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
189	1	BOOK	[DIWA] Filipino- Filipino sa Modernong Panahon	Grade 8	f	\N	885.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
190	1	BOOK	[PHOENIX] English-English Communication Arts & Skills (ECAS)	Grade 8	f	\N	530.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
191	1	BOOK	[PHOENIX] Mathematics- Realistic Math	Grade 8	f	\N	725.00	100	0	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
1153	1	UNIFORM	Blouse	\N	f	XS, S, M, L, XL, XXL, XXXL	470.00	0	0	t	2026-07-26 10:01:14.411586	\N	\N	100	t	20.00
124	1	BOOK	[ABIVA] GMRC-Hakbang sa Kabutihang Asal K1	Kinder	f	\N	380.00	100	1	t	2026-04-28 13:08:07.406859	\N	\N	\N	f	20.00
1240	10	BOOK	ESP	Nursery	f	SIBS	353.00	100	0	t	2026-08-31 12:48:24.694848	\N	\N	\N	f	20.00
\.


--
-- Data for Name: inventory_sizes; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.inventory_sizes (size_id, item_id, size_label, stock_qty, reserved_qty) FROM stdin;
\.


--
-- Data for Name: login_2fa_tokens; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.login_2fa_tokens (token_id, token_hash, user_id, user_role, ip_address, status, created_at, expires_at) FROM stdin;
\.


--
-- Data for Name: parent_notifications; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.parent_notifications (notif_id, parent_id, student_id, title, message, link, is_read, created_at) FROM stdin;
3	149	489	SWAFO Parent Conference Notice	May nakatakdang patawag / parent conference kaugnay ng iyong anak (Petsa: 2026-09-30).	/parent/swafo-conferences	f	2026-09-29 11:34:35.741621
\.


--
-- Data for Name: parent_student; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.parent_student (id, parent_id, student_id, relationship, created_at) FROM stdin;
24	122	135	guardian	2026-08-19 05:13:03.226969
25	122	139	guardian	2026-08-19 08:14:46.433999
27	132	138	guardian	2026-08-31 23:48:10.643857
23	106	150	guardian	2026-08-18 03:16:14.580981
28	106	134	guardian	2026-09-22 03:21:09.730075
30	107	134	guardian	2026-09-22 03:21:09.730075
31	135	145	guardian	2026-09-22 03:21:09.730075
33	95	139	guardian	2026-09-22 03:21:09.730075
34	127	140	guardian	2026-09-22 03:21:09.730075
36	82	142	guardian	2026-09-22 03:21:09.730075
37	128	142	guardian	2026-09-22 03:21:09.730075
38	123	142	guardian	2026-09-22 03:21:09.730075
40	89	137	guardian	2026-09-22 03:21:09.730075
42	87	137	guardian	2026-09-22 03:21:09.730075
44	88	137	guardian	2026-09-22 03:21:09.730075
45	119	137	guardian	2026-09-22 03:21:09.730075
46	120	137	guardian	2026-09-22 03:21:09.730075
47	117	137	guardian	2026-09-22 03:21:09.730075
48	113	137	guardian	2026-09-22 03:21:09.730075
49	111	137	guardian	2026-09-22 03:21:09.730075
50	118	137	guardian	2026-09-22 03:21:09.730075
51	116	137	guardian	2026-09-22 03:21:09.730075
52	115	137	guardian	2026-09-22 03:21:09.730075
53	140	136	guardian	2026-09-22 03:21:09.730075
54	130	136	guardian	2026-09-22 03:21:09.730075
55	136	146	guardian	2026-09-22 03:21:09.730075
56	137	148	guardian	2026-09-22 03:21:09.730075
58	95	135	guardian	2026-09-22 03:21:09.730075
61	107	150	guardian	2026-09-22 03:21:09.730075
130	148	490	guardian	2026-09-22 07:21:12.973007
131	108	490	guardian	2026-09-22 07:21:12.973007
134	90	490	guardian	2026-09-22 07:21:12.973007
136	129	490	guardian	2026-09-22 07:21:12.973007
137	149	489	guardian	2026-09-22 07:21:12.973007
139	150	492	guardian	2026-09-22 08:32:05.498011
140	150	139	guardian	2026-09-22 08:32:05.498011
141	150	135	guardian	2026-09-22 08:32:05.498011
142	150	493	guardian	2026-09-22 08:32:05.498011
143	151	492	guardian	2026-09-22 08:34:06.754339
144	151	139	guardian	2026-09-22 08:34:06.754339
145	151	135	guardian	2026-09-22 08:34:06.754339
146	151	493	guardian	2026-09-22 08:34:06.754339
153	122	492	guardian	2026-09-22 11:32:03.531943
154	95	492	guardian	2026-09-22 11:32:03.531943
188	122	493	guardian	2026-09-22 11:32:03.531943
189	95	493	guardian	2026-09-22 11:32:03.531943
200	107	491	guardian	2026-09-22 11:32:03.531943
3756	169	140	guardian	2026-10-01 22:47:38.724615
3791	83	490	guardian	2026-10-01 22:47:38.724615
3793	84	490	guardian	2026-10-01 22:47:38.724615
3797	106	491	guardian	2026-10-01 22:47:38.724615
4563	172	325	guardian	2026-10-06 01:15:18.662121
4694	86	141	guardian	2026-10-06 05:09:49.963307
4709	85	137	guardian	2026-10-06 05:09:49.963307
\.


--
-- Data for Name: participation_scores; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.participation_scores (id, enrollment_id, section_id, subject_id, grading_period, score, updated_at, teacher_id, year_id, max_score) FROM stdin;
7	491	138	156	1st	7.00	2026-10-01 02:38:12.430615	114	\N	10.0
8	490	138	156	1st	9.00	2026-10-01 02:38:12.430615	114	\N	10.0
9	489	138	156	1st	5.00	2026-10-01 02:38:12.430615	114	\N	10.0
\.


--
-- Data for Name: password_reset_tokens; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.password_reset_tokens (id, token_hash, user_id, student_account_id, email, created_at, expires_at, used_at) FROM stdin;
4	6f7b63cb5a0d8c12e5478aa4ca122bd0394006a46cd8cbde568973d57ae890d9	105	\N	marizjunterial2@gmail.com	2026-07-31 02:37:53.855054	2026-07-31 03:07:53.865645	\N
\.


--
-- Data for Name: payments; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.payments (payment_id, bill_id, enrollment_id, branch_id, amount, payment_method, payment_date, receipt_number, notes, received_by, year_id, target_type, target_id) FROM stdin;
10	12	134	4	1020.00	cash	2026-08-18 03:45:16.064602	OR-20260818-EDD039		84	10	general	\N
11	12	134	4	1020.00	cash	2026-08-18 07:40:35.409722	OR-20260818-5E9548		84	10	uniform_order	7
12	12	134	4	13980.00	cash	2026-08-18 07:43:21.916562	OR-20260818-10348E		84	10	general	\N
15	12	134	4	2330.00	cash	2026-08-19 07:56:15.309049	OR-20260819-0F036F		84	10	tuition	\N
16	13	135	4	930.00	cash	2026-08-19 08:02:54.331782	OR-20260819-1203F2		84	10	uniform_order	12
17	13	135	4	400.00	cash	2026-08-19 08:02:54.331782	OR-20260819-E4C9DF		84	10	reservation	15
18	13	135	4	14000.00	cash	2026-08-19 08:07:20.136805	OR-20260819-4F5FB0		84	10	tuition	\N
19	13	135	4	930.00	cash	2026-08-19 08:07:20.136805	OR-20260819-BC6523		84	10	uniform_order	13
20	13	135	4	910.00	cash	2026-08-19 08:07:20.136805	OR-20260819-510757		84	10	uniform_order	14
21	13	135	4	400.00	cash	2026-08-19 08:07:20.136805	OR-20260819-F853EA		84	10	reservation	16
22	14	136	10	14000.00	cash	2026-08-31 08:58:21.789644	OR-20260831-78288E		131	26	tuition	\N
23	14	136	10	1000.00	cash	2026-08-31 08:58:21.789644	OR-20260831-E948D9		131	26	uniform_order	20
24	14	136	10	1000.00	cash	2026-08-31 08:58:21.789644	OR-20260831-B67564		131	26	uniform_order	22
25	14	136	10	323.00	cash	2026-08-31 09:05:31.468406	OR-20260831-385E76		131	26	reservation	17
26	16	489	10	4000.00	cash	2026-09-22 08:08:02.593211	OR-20260922-98CBF2		131	30	tuition	\N
27	16	489	10	10000.00	cash	2026-09-22 08:37:49.829002	OR-20260922-41E02E		131	30	tuition	\N
28	17	496	10	1000.00	cash	2026-09-29 11:22:45.80079	OR-20260929-84ACC2		131	30	tuition	\N
\.


--
-- Data for Name: posted_grades; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.posted_grades (id, enrollment_id, subject_id, grading_period, grade, posted_by, posted_at, section_id, year_id) FROM stdin;
\.


--
-- Data for Name: reservation_items; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.reservation_items (reservation_item_id, reservation_id, item_id, qty, size_label, unit_price, line_total, publisher) FROM stdin;
19	13	1227	1	FNB	400.00	400.00	\N
20	14	1227	1	FNB	400.00	400.00	\N
21	15	1227	1	FNB	400.00	400.00	\N
22	16	1227	1	FNB	400.00	400.00	\N
23	17	1233	1	FNB	323.00	323.00	\N
24	18	1238	1	NEO-ASIA	460.00	460.00	\N
25	19	1236	1	NEO-ASIA	460.00	460.00	\N
\.


--
-- Data for Name: reservations; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.reservations (reservation_id, student_user_id, branch_id, student_grade_level, status, created_at, paid_at, claimed_at, cancelled_at, reserved_by_user_id, enrollment_id) FROM stdin;
14	107	4	Nursery	RESERVED	2026-08-19 07:56:50.507215	\N	\N	\N	107	134
13	107	4	Nursery	RESERVED	2026-08-19 07:55:04.317963	\N	\N	\N	107	134
15	125	4	Nursery	PAID	2026-08-19 08:02:03.849482	\N	\N	\N	125	135
16	125	4	Nursery	PAID	2026-08-19 08:03:49.003701	\N	\N	\N	125	135
18	129	10	Nursery	RESERVED	2026-09-01 03:13:45.353944	\N	\N	\N	129	141
19	129	10	Nursery	RESERVED	2026-09-01 03:13:45.353944	\N	\N	\N	129	141
17	130	10	Nursery	CLAIMED	2026-08-31 09:05:08.400088	\N	\N	\N	130	136
\.


--
-- Data for Name: schedules; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schedules (schedule_id, subject_id, section_id, teacher_id, day_of_week, start_time, end_time, room, year_id, branch_id, is_archived, term_name) FROM stdin;
87	22	134	144	Monday	09:30:00	10:30:00	4	18	1	f	\N
16	33	87	119	Monday	07:00:00	09:00:00	1	26	10	f	\N
17	34	87	119	Monday	10:00:00	12:00:00	2	26	10	f	\N
18	37	87	119	Monday	13:00:00	14:00:00	3	26	10	f	\N
19	30	87	119	Monday	14:00:00	15:00:00	4	26	10	f	\N
20	35	87	119	Monday	15:00:00	16:00:00	5	26	10	f	\N
21	28	87	119	Monday	16:00:00	17:00:00	7	26	10	f	\N
22	27	84	121	Monday	13:30:00	14:30:00	10	10	4	f	\N
23	27	84	121	Tuesday	13:00:00	14:00:00	11	10	4	f	\N
24	22	84	86	Tuesday	14:00:00	15:30:00	12	10	4	f	\N
25	33	87	119	Tuesday	09:00:00	12:00:00	3	26	10	f	\N
26	33	85	114	Monday	07:00:00	09:00:00	7	26	10	f	\N
27	33	85	114	Tuesday	09:00:00	11:00:00	8	26	10	f	\N
28	33	85	114	Wednesday	13:00:00	15:00:00	6	26	10	f	\N
29	33	85	114	Thursday	16:00:00	17:00:00	2	26	10	f	\N
30	33	85	114	Friday	07:00:00	08:00:00	5	26	10	f	\N
88	22	134	144	Tuesday	09:30:00	10:30:00	4	18	1	f	\N
35	33	116	124	Friday	07:15:00	08:15:00	1	30	10	t	\N
31	33	116	124	Monday	07:15:00	09:15:00	1	30	10	t	\N
34	33	116	124	Thursday	07:15:00	09:15:00	1	30	10	t	\N
32	33	116	124	Tuesday	07:15:00	09:15:00	1	30	10	t	\N
33	33	116	124	Wednesday	07:15:00	09:15:00	1	30	10	t	\N
36	33	116	124	Monday	07:15:00	09:15:00	1	30	10	f	\N
37	33	116	124	Tuesday	07:15:00	09:15:00	1	30	10	f	\N
38	33	116	124	Wednesday	07:15:00	09:15:00	1	30	10	f	\N
39	33	116	124	Thursday	07:15:00	09:15:00	1	30	10	f	\N
40	33	116	124	Friday	07:15:00	09:15:00	1	30	10	f	\N
41	34	116	124	Monday	09:30:00	10:00:00	1	30	10	f	\N
51	21	132	147	Monday	09:05:00	09:55:00	2	18	1	f	\N
52	21	132	147	Tuesday	09:05:00	09:55:00	2	18	1	f	\N
53	21	132	147	Wednesday	09:05:00	09:55:00	2	18	1	f	\N
54	21	132	147	Thursday	09:05:00	09:55:00	2	18	1	f	\N
55	135	132	147	Monday	07:15:00	08:05:00	2	18	1	f	\N
56	135	132	147	Tuesday	07:15:00	08:05:00	2	18	1	f	\N
57	135	132	147	Wednesday	07:15:00	08:05:00	2	18	1	f	\N
58	135	132	147	Thursday	07:15:00	08:05:00	2	18	1	f	\N
59	22	132	147	Monday	08:05:00	08:55:00	2	18	1	f	\N
60	22	132	147	Tuesday	08:05:00	08:55:00	2	18	1	f	\N
61	22	132	147	Wednesday	08:05:00	08:55:00	2	18	1	f	\N
62	22	132	147	Thursday	08:05:00	08:55:00	2	18	1	f	\N
63	19	132	147	Monday	09:55:00	10:45:00	2	18	1	f	\N
64	19	132	147	Tuesday	09:55:00	10:45:00	2	18	1	f	\N
65	19	132	147	Wednesday	09:55:00	10:45:00	2	18	1	f	\N
66	19	132	147	Thursday	09:55:00	10:45:00	2	18	1	f	\N
67	49	132	147	Monday	10:45:00	11:30:00	2	18	1	f	\N
68	49	132	147	Tuesday	10:45:00	11:30:00	2	18	1	f	\N
69	49	132	147	Wednesday	10:45:00	11:30:00	2	18	1	f	\N
70	49	132	147	Thursday	10:45:00	11:30:00	2	18	1	f	\N
71	23	132	147	Monday	12:00:00	13:00:00	2	18	1	f	\N
72	23	132	147	Tuesday	12:00:00	13:00:00	2	18	1	f	\N
73	43	132	147	Friday	07:15:00	08:05:00	2	18	1	f	\N
74	23	132	147	Friday	08:05:00	08:55:00	2	18	1	f	\N
76	143	132	147	Friday	09:05:00	11:30:00	2	18	1	f	\N
77	164	132	147	Wednesday	12:00:00	13:00:00	2	18	1	f	\N
78	164	132	147	Thursday	12:00:00	13:00:00	2	18	1	f	\N
79	60	134	162	Monday	07:15:00	08:15:00	4	18	1	f	\N
80	60	134	162	Tuesday	07:15:00	08:15:00	4	18	1	f	\N
81	60	134	162	Wednesday	07:15:00	08:15:00	4	18	1	f	\N
82	60	134	162	Thursday	07:15:00	08:15:00	4	18	1	f	\N
83	19	134	152	Monday	08:15:00	09:15:00	4	18	1	f	\N
84	19	134	152	Tuesday	08:15:00	09:15:00	4	18	1	f	\N
85	19	134	152	Wednesday	08:15:00	09:15:00	4	18	1	f	\N
86	19	134	152	Thursday	08:15:00	09:15:00	4	18	1	f	\N
89	22	134	144	Wednesday	09:30:00	10:30:00	4	18	1	f	\N
90	22	134	144	Thursday	09:30:00	10:30:00	4	18	1	f	\N
91	21	134	146	Monday	10:30:00	11:30:00	4	18	1	f	\N
92	21	134	146	Tuesday	10:30:00	11:30:00	4	18	1	f	\N
93	21	134	146	Wednesday	10:30:00	11:30:00	4	18	1	f	\N
94	21	134	146	Thursday	10:30:00	11:30:00	4	18	1	f	\N
47	65	134	145	Monday	13:00:00	14:00:00	4	18	1	f	\N
48	65	134	145	Tuesday	13:00:00	14:00:00	4	18	1	f	\N
49	65	134	145	Wednesday	13:00:00	14:00:00	4	18	1	f	\N
50	65	134	145	Thursday	13:00:00	14:00:00	4	18	1	f	\N
95	20	134	142	Monday	12:00:00	13:00:00	4	18	1	f	\N
96	20	134	142	Tuesday	12:00:00	13:00:00	4	18	1	f	\N
97	20	134	142	Wednesday	12:00:00	13:00:00	4	18	1	f	\N
98	20	134	142	Thursday	12:00:00	13:00:00	4	18	1	f	\N
99	23	134	146	Monday	14:15:00	15:15:00	4	18	1	f	\N
100	23	134	146	Tuesday	14:15:00	15:15:00	4	18	1	f	\N
101	23	134	146	Wednesday	14:15:00	15:15:00	4	18	1	f	\N
102	135	134	147	Monday	16:15:00	17:00:00	4	18	1	f	\N
103	135	134	147	Tuesday	16:15:00	17:00:00	4	18	1	f	\N
104	135	134	147	Wednesday	16:15:00	17:00:00	4	18	1	f	\N
105	135	134	147	Thursday	16:15:00	17:00:00	4	18	1	f	\N
106	175	134	146	Friday	08:15:00	09:15:00	4	18	1	f	\N
107	135	134	147	Friday	10:30:00	11:30:00	4	18	1	f	\N
108	43	134	147	Friday	07:15:00	08:15:00	4	18	1	f	\N
109	135	135	152	Monday	07:15:00	08:15:00	5	18	1	f	\N
110	135	135	152	Tuesday	07:15:00	08:15:00	5	18	1	f	\N
111	135	135	152	Wednesday	07:15:00	08:15:00	5	18	1	f	\N
112	135	135	152	Thursday	07:15:00	08:15:00	5	18	1	f	\N
113	43	135	152	Friday	07:15:00	08:15:00	5	18	1	f	\N
114	20	135	142	Monday	08:15:00	09:15:00	5	18	1	f	\N
115	20	135	142	Tuesday	08:15:00	09:15:00	5	18	1	f	\N
116	20	135	142	Wednesday	08:15:00	09:15:00	5	18	1	f	\N
117	20	135	142	Thursday	08:15:00	09:15:00	5	18	1	f	\N
118	37	135	142	Friday	08:15:00	09:15:00	5	18	1	f	\N
119	21	135	146	Monday	09:30:00	10:30:00	5	18	1	f	\N
120	21	135	146	Tuesday	09:30:00	10:30:00	5	18	1	f	\N
121	21	135	146	Wednesday	09:30:00	10:30:00	5	18	1	f	\N
122	21	135	146	Thursday	09:30:00	10:30:00	5	18	1	f	\N
123	80	135	146	Friday	09:30:00	10:30:00	5	18	1	f	\N
124	22	135	144	Monday	10:30:00	11:30:00	5	18	1	f	\N
125	22	135	144	Tuesday	10:30:00	11:30:00	5	18	1	f	\N
126	22	135	144	Wednesday	10:30:00	11:30:00	5	18	1	f	\N
127	22	135	144	Thursday	10:30:00	11:30:00	5	18	1	f	\N
128	27	135	145	Monday	12:00:00	13:00:00	5	18	1	f	\N
129	27	135	145	Tuesday	12:00:00	13:00:00	5	18	1	f	\N
130	27	135	145	Wednesday	12:00:00	13:00:00	5	18	1	f	\N
131	27	135	145	Thursday	12:00:00	13:00:00	5	18	1	f	\N
132	23	135	146	Monday	13:00:00	14:00:00	5	18	1	f	\N
133	23	135	146	Tuesday	13:00:00	14:00:00	5	18	1	f	\N
134	23	135	146	Wednesday	13:00:00	14:00:00	5	18	1	f	\N
135	80	135	146	Thursday	13:00:00	14:00:00	5	18	1	f	\N
136	19	135	152	Monday	14:00:00	15:00:00	5	18	1	f	\N
137	19	135	152	Tuesday	14:00:00	15:00:00	5	18	1	f	\N
138	19	135	152	Wednesday	14:00:00	15:00:00	5	18	1	f	\N
139	19	135	152	Thursday	14:00:00	15:00:00	5	18	1	f	\N
140	60	135	147	Monday	15:15:00	16:15:00	5	18	1	f	\N
143	60	135	147	Thursday	15:15:00	16:15:00	5	18	1	f	\N
141	60	135	147	Tuesday	15:15:00	16:15:00	5	18	1	f	\N
142	60	135	147	Wednesday	15:15:00	16:15:00	5	18	1	f	\N
144	37	135	142	Monday	16:15:00	17:00:00	5	18	1	f	\N
145	37	135	142	Tuesday	16:15:00	17:00:00	5	18	1	f	\N
146	37	135	142	Wednesday	16:15:00	17:00:00	5	18	1	f	\N
147	37	135	142	Thursday	16:15:00	17:00:00	5	18	1	f	\N
148	135	136	144	Monday	07:15:00	08:15:00	6	18	1	f	\N
149	135	136	144	Tuesday	07:15:00	08:15:00	6	18	1	f	\N
150	135	136	144	Wednesday	07:15:00	08:15:00	6	18	1	f	\N
151	135	136	144	Thursday	07:15:00	08:15:00	6	18	1	f	\N
152	43	136	144	Friday	07:15:00	08:15:00	6	18	1	f	\N
153	21	136	146	Monday	08:15:00	09:15:00	6	18	1	f	\N
154	21	136	146	Tuesday	08:15:00	09:15:00	6	18	1	f	\N
155	21	136	146	Wednesday	08:15:00	09:15:00	6	18	1	f	\N
156	21	136	146	Thursday	08:15:00	09:15:00	6	18	1	f	\N
157	20	136	142	Monday	09:30:00	10:30:00	6	18	1	f	\N
158	20	136	142	Tuesday	09:30:00	10:30:00	6	18	1	f	\N
159	20	136	142	Wednesday	09:30:00	10:30:00	6	18	1	f	\N
160	20	136	142	Thursday	09:30:00	10:30:00	6	18	1	f	\N
161	28	136	141	Monday	10:30:00	11:30:00	6	18	1	f	\N
162	28	136	141	Tuesday	10:30:00	11:30:00	6	18	1	f	\N
163	28	136	141	Wednesday	10:30:00	11:30:00	6	18	1	f	\N
164	28	136	141	Thursday	10:30:00	11:30:00	6	18	1	f	\N
165	80	136	146	Friday	10:30:00	11:30:00	6	18	1	f	\N
166	22	136	144	Monday	12:00:00	13:00:00	6	18	1	f	\N
167	22	136	144	Tuesday	12:00:00	13:00:00	6	18	1	f	\N
168	22	136	144	Wednesday	12:00:00	13:00:00	6	18	1	f	\N
169	22	136	144	Thursday	12:00:00	13:00:00	6	18	1	f	\N
170	19	136	152	Monday	13:00:00	14:00:00	6	18	1	f	\N
171	19	136	152	Tuesday	13:00:00	14:00:00	6	18	1	f	\N
172	19	136	152	Wednesday	13:00:00	14:00:00	6	18	1	f	\N
173	19	136	152	Thursday	13:00:00	14:00:00	6	18	1	f	\N
174	60	136	147	Monday	14:15:00	15:15:00	6	18	1	f	\N
175	60	136	147	Tuesday	14:15:00	15:15:00	6	18	1	f	\N
176	60	136	147	Wednesday	14:15:00	15:15:00	6	18	1	f	\N
177	60	136	147	Thursday	14:15:00	15:15:00	6	18	1	f	\N
178	23	136	142	Monday	15:15:00	16:15:00	6	18	1	f	\N
179	23	136	142	Tuesday	15:15:00	16:15:00	6	18	1	f	\N
180	23	136	142	Wednesday	15:15:00	16:15:00	6	18	1	f	\N
181	23	136	142	Thursday	15:15:00	16:15:00	6	18	1	f	\N
182	92	137	146	Monday	07:15:00	08:15:00	7	18	1	f	\N
183	92	137	146	Tuesday	07:15:00	08:15:00	7	18	1	f	\N
184	92	137	146	Wednesday	07:15:00	08:15:00	7	18	1	f	\N
185	92	137	146	Thursday	07:15:00	08:15:00	7	18	1	f	\N
186	60	137	162	Monday	08:15:00	09:15:00	7	18	1	f	\N
187	60	137	162	Tuesday	08:15:00	09:15:00	7	18	1	f	\N
188	60	137	162	Wednesday	08:15:00	09:15:00	7	18	1	f	\N
189	60	137	162	Thursday	08:15:00	09:15:00	7	18	1	f	\N
190	43	137	146	Friday	07:15:00	08:15:00	7	18	1	f	\N
191	37	137	152	Friday	08:15:00	09:15:00	7	18	1	f	\N
192	19	137	164	Monday	09:15:00	10:15:00	7	18	1	f	\N
193	19	137	164	Tuesday	09:15:00	10:15:00	7	18	1	f	\N
194	19	137	164	Wednesday	09:15:00	10:15:00	7	18	1	f	\N
195	19	137	164	Thursday	09:15:00	10:15:00	7	18	1	f	\N
196	23	137	142	Friday	09:15:00	10:15:00	7	18	1	f	\N
197	20	137	142	Monday	10:30:00	11:30:00	7	18	1	f	\N
198	20	137	142	Tuesday	10:30:00	11:30:00	7	18	1	f	\N
199	20	137	142	Wednesday	10:30:00	11:30:00	7	18	1	f	\N
200	20	137	142	Thursday	10:30:00	11:30:00	7	18	1	f	\N
201	21	137	146	Monday	11:30:00	12:30:00	7	18	1	f	\N
202	21	137	146	Tuesday	11:30:00	12:30:00	7	18	1	f	\N
203	21	137	146	Wednesday	11:30:00	12:30:00	7	18	1	f	\N
204	21	137	146	Thursday	11:30:00	12:30:00	7	18	1	f	\N
205	22	137	144	Monday	13:00:00	14:00:00	7	18	1	f	\N
206	22	137	144	Tuesday	13:00:00	14:00:00	7	18	1	f	\N
207	22	137	144	Wednesday	13:00:00	14:00:00	7	18	1	f	\N
208	22	137	144	Thursday	13:00:00	14:00:00	7	18	1	f	\N
209	23	137	142	Monday	14:00:00	15:00:00	7	18	1	f	\N
210	23	137	142	Tuesday	14:00:00	15:00:00	7	18	1	f	\N
211	23	137	142	Wednesday	14:00:00	15:00:00	7	18	1	f	\N
212	23	137	142	Thursday	14:00:00	15:00:00	7	18	1	f	\N
213	37	137	152	Monday	15:15:00	16:00:00	7	18	1	f	\N
214	37	137	152	Tuesday	15:15:00	16:00:00	7	18	1	f	\N
215	37	137	152	Wednesday	15:15:00	16:00:00	7	18	1	f	\N
216	37	137	152	Thursday	15:15:00	16:00:00	7	18	1	f	\N
217	99	137	165	Monday	16:00:00	17:00:00	7	18	1	f	\N
218	99	137	165	Tuesday	16:00:00	17:00:00	7	18	1	f	\N
219	99	137	165	Wednesday	16:00:00	17:00:00	7	18	1	f	\N
220	99	137	165	Thursday	16:00:00	17:00:00	7	18	1	f	\N
221	92	122	145	Monday	07:15:00	08:15:00	9	18	1	f	\N
222	92	122	145	Tuesday	07:15:00	08:15:00	9	18	1	f	\N
223	92	122	145	Wednesday	07:15:00	08:15:00	9	18	1	f	\N
224	92	122	145	Thursday	07:15:00	08:15:00	9	18	1	f	\N
225	43	122	145	Friday	07:15:00	08:15:00	9	18	1	f	\N
226	19	122	163	Monday	08:15:00	09:15:00	9	18	1	f	\N
227	19	122	163	Tuesday	08:15:00	09:15:00	9	18	1	f	\N
228	19	122	163	Wednesday	08:15:00	09:15:00	9	18	1	f	\N
229	19	122	163	Thursday	08:15:00	09:15:00	9	18	1	f	\N
230	28	122	145	Friday	08:15:00	09:15:00	9	18	1	f	\N
231	20	122	143	Monday	09:15:00	10:15:00	9	18	1	f	\N
232	20	122	143	Tuesday	09:15:00	10:15:00	9	18	1	f	\N
233	20	122	143	Wednesday	09:15:00	10:15:00	9	18	1	f	\N
234	20	122	143	Thursday	09:15:00	10:15:00	9	18	1	f	\N
235	21	122	159	Monday	10:30:00	11:30:00	9	18	1	f	\N
236	21	122	159	Tuesday	10:30:00	11:30:00	9	18	1	f	\N
237	21	122	159	Wednesday	10:30:00	11:30:00	9	18	1	f	\N
238	21	122	159	Thursday	10:30:00	11:30:00	9	18	1	f	\N
239	22	122	158	Monday	11:30:00	12:30:00	9	18	1	f	\N
240	22	122	158	Tuesday	11:30:00	12:30:00	9	18	1	f	\N
241	22	122	158	Wednesday	11:30:00	12:30:00	9	18	1	f	\N
242	22	122	158	Thursday	11:30:00	12:30:00	9	18	1	f	\N
243	60	122	139	Monday	13:00:00	14:00:00	9	18	1	f	\N
244	60	122	139	Tuesday	13:00:00	14:00:00	9	18	1	f	\N
245	60	122	139	Wednesday	13:00:00	14:00:00	9	18	1	f	\N
246	60	122	139	Thursday	13:00:00	14:00:00	9	18	1	f	\N
247	23	122	158	Monday	14:00:00	15:00:00	9	18	1	f	\N
248	23	122	158	Tuesday	14:00:00	15:00:00	9	18	1	f	\N
249	23	122	158	Wednesday	14:00:00	15:00:00	9	18	1	f	\N
251	28	122	145	Monday	15:15:00	16:00:00	9	18	1	f	\N
252	28	122	145	Tuesday	15:15:00	16:00:00	9	18	1	f	\N
253	28	122	145	Wednesday	15:15:00	16:00:00	9	18	1	f	\N
254	28	122	145	Thursday	15:15:00	16:00:00	9	18	1	f	\N
255	37	122	158	Monday	16:00:00	17:00:00	9	18	1	f	\N
256	37	122	158	Tuesday	16:00:00	17:00:00	9	18	1	f	\N
257	37	122	158	Wednesday	16:00:00	17:00:00	9	18	1	f	\N
258	37	122	158	Thursday	16:00:00	17:00:00	9	18	1	f	\N
259	80	122	164	Friday	10:30:00	11:30:00	9	18	1	f	\N
260	80	122	164	Thursday	14:00:00	15:00:00	9	18	1	f	\N
265	43	125	141	Friday	07:15:00	08:15:00	10	18	1	f	\N
266	20	125	143	Monday	08:15:00	09:15:00	10	18	1	f	\N
267	20	125	143	Tuesday	08:15:00	09:15:00	10	18	1	f	\N
268	20	125	143	Wednesday	08:15:00	09:15:00	10	18	1	f	\N
269	20	125	143	Thursday	08:15:00	09:15:00	10	18	1	f	\N
270	21	125	159	Monday	09:15:00	10:15:00	10	18	1	f	\N
271	21	125	159	Tuesday	09:15:00	10:15:00	10	18	1	f	\N
272	21	125	159	Wednesday	09:15:00	10:15:00	10	18	1	f	\N
273	21	125	159	Thursday	09:15:00	10:15:00	10	18	1	f	\N
274	92	125	141	Monday	07:15:00	08:15:00	10	18	1	f	\N
275	92	125	141	Tuesday	07:15:00	08:15:00	10	18	1	f	\N
276	92	125	141	Wednesday	07:15:00	08:15:00	10	18	1	f	\N
277	92	125	141	Thursday	07:15:00	08:15:00	10	18	1	f	\N
278	28	125	145	Friday	08:15:00	09:15:00	10	18	1	f	\N
279	37	125	141	Friday	09:15:00	10:15:00	10	18	1	f	\N
280	19	125	163	Monday	10:30:00	11:30:00	10	18	1	f	\N
281	19	125	163	Tuesday	10:30:00	11:30:00	10	18	1	f	\N
282	19	125	163	Wednesday	10:30:00	11:30:00	10	18	1	f	\N
283	19	125	163	Thursday	10:30:00	11:30:00	10	18	1	f	\N
284	60	125	161	Friday	10:30:00	11:30:00	10	18	1	f	\N
285	22	125	141	Monday	11:30:00	12:30:00	10	18	1	f	\N
286	22	125	141	Tuesday	11:30:00	12:30:00	10	18	1	f	\N
287	22	125	141	Wednesday	11:30:00	12:30:00	10	18	1	f	\N
288	22	125	141	Thursday	11:30:00	12:30:00	10	18	1	f	\N
289	23	125	158	Monday	13:00:00	14:00:00	10	18	1	f	\N
290	23	125	158	Tuesday	13:00:00	14:00:00	10	18	1	f	\N
291	23	125	158	Wednesday	13:00:00	14:00:00	10	18	1	f	\N
293	28	125	145	Monday	14:00:00	15:00:00	10	18	1	f	\N
294	28	125	145	Tuesday	14:00:00	15:00:00	10	18	1	f	\N
295	28	125	145	Wednesday	14:00:00	15:00:00	10	18	1	f	\N
297	60	125	161	Monday	15:15:00	16:00:00	10	18	1	f	\N
298	60	125	161	Tuesday	15:15:00	16:00:00	10	18	1	f	\N
299	60	125	161	Wednesday	15:15:00	16:00:00	10	18	1	f	\N
300	60	125	161	Thursday	15:15:00	16:00:00	10	18	1	f	\N
301	37	125	141	Monday	16:00:00	16:45:00	10	18	1	f	\N
302	37	125	141	Tuesday	16:00:00	16:45:00	10	18	1	f	\N
303	37	125	141	Wednesday	16:00:00	16:45:00	10	18	1	f	\N
304	37	125	141	Thursday	16:00:00	16:45:00	10	18	1	f	\N
305	175	125	163	Thursday	13:00:00	14:00:00	10	18	1	f	\N
306	175	125	163	Thursday	14:00:00	15:00:00	10	18	1	f	\N
307	33	116	124	Monday	13:00:00	14:00:00	1	30	10	f	\N
308	33	116	124	Monday	10:30:00	11:30:00	1	30	10	f	\N
309	28	116	119	Tuesday	13:00:00	14:00:00	1	30	10	f	\N
310	28	116	119	Thursday	13:00:00	14:00:00	1	30	10	f	\N
311	153	138	114	Monday	13:00:00	14:00:00	7	30	10	f	\N
312	153	138	114	Tuesday	13:00:00	14:00:00	7	30	10	f	\N
313	150	138	114	Monday	07:15:00	08:15:00	4	30	10	f	\N
314	150	138	114	Wednesday	07:15:00	08:15:00	4	30	10	f	\N
316	151	138	114	Tuesday	11:30:00	12:30:00	7	30	10	f	\N
317	151	138	114	Wednesday	11:30:00	12:30:00	7	30	10	f	\N
318	151	138	114	Thursday	11:30:00	12:30:00	7	30	10	f	\N
319	151	138	114	Friday	11:30:00	12:30:00	7	30	10	f	\N
320	186	130	158	Monday	07:15:00	08:15:00	12	18	1	f	2nd Term
321	186	130	158	Tuesday	07:15:00	08:15:00	12	18	1	f	2nd Term
322	186	130	158	Wednesday	07:15:00	08:15:00	12	18	1	f	2nd Term
323	186	130	158	Thursday	07:15:00	08:15:00	12	18	1	f	2nd Term
324	187	130	145	Monday	08:15:00	10:15:00	12	18	1	f	2nd Term
325	187	130	145	Tuesday	08:15:00	10:15:00	12	18	1	f	2nd Term
326	187	130	145	Wednesday	08:15:00	10:15:00	12	18	1	f	2nd Term
327	188	130	159	Monday	12:00:00	15:00:00	12	18	1	f	2nd Term
328	188	130	159	Tuesday	12:00:00	15:00:00	12	18	1	f	2nd Term
329	23	130	143	Monday	10:30:00	11:30:00	12	18	1	f	\N
330	23	130	143	Tuesday	10:30:00	11:30:00	12	18	1	f	\N
331	23	130	143	Wednesday	10:30:00	11:30:00	12	18	1	f	\N
332	23	130	143	Thursday	10:30:00	11:30:00	12	18	1	f	\N
333	189	130	159	Wednesday	12:00:00	15:00:00	12	18	1	f	2nd Term
334	189	130	159	Thursday	12:00:00	15:00:00	12	18	1	f	2nd Term
335	125	130	141	Friday	08:15:00	09:15:00	12	18	1	f	\N
336	186	130	158	Friday	09:30:00	11:30:00	12	18	1	f	2nd Term
337	125	130	141	Thursday	09:30:00	10:30:00	12	18	1	f	\N
315	150	138	114	Thursday	07:15:00	08:15:00	4	30	10	t	\N
\.


--
-- Data for Name: school_years; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.school_years (year_id, label, branch_id, is_active) FROM stdin;
20	2027-2028	4	f
21	2027-2028	5	f
22	2027-2028	7	f
23	2027-2028	1	f
24	2027-2028	8	f
27	2027-2028	6	f
28	2027-2028	10	f
10	2025-2026	4	f
11	2025-2026	5	f
13	2025-2026	7	f
7	2025-2026	1	f
14	2025-2026	8	f
12	2025-2026	6	f
26	2025-2026	10	f
15	2026-2027	4	t
16	2026-2027	5	t
17	2026-2027	7	t
19	2026-2027	8	t
29	2026-2027	6	t
30	2026-2027	10	t
18	2026-2027	1	t
\.


--
-- Data for Name: section_teachers; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.section_teachers (id, section_id, teacher_id, subject_id, year_id, is_archived, term_name) FROM stdin;
110	87	\N	37	26	f	\N
50	87	\N	30	26	f	\N
62	87	\N	33	26	f	\N
74	87	\N	34	26	f	\N
86	87	\N	35	26	f	\N
113	90	\N	37	26	f	\N
98	87	\N	28	26	f	\N
114	91	\N	37	26	f	\N
115	92	\N	37	26	f	\N
116	93	\N	37	26	f	\N
117	94	\N	37	26	f	\N
118	95	\N	37	26	f	\N
119	96	\N	37	26	f	\N
442	130	158	186	18	f	2nd Term
445	130	159	189	18	f	2nd Term
109	86	117	37	26	f	\N
49	86	117	30	26	f	\N
61	86	117	33	26	f	\N
73	86	117	34	26	f	\N
85	86	117	35	26	f	\N
97	86	117	28	26	f	\N
120	84	121	20	10	f	\N
121	84	121	19	10	f	\N
47	84	121	27	10	f	\N
111	88	123	37	26	f	\N
51	88	123	30	26	f	\N
63	88	123	33	26	f	\N
75	88	123	34	26	f	\N
87	88	123	35	26	f	\N
99	88	123	28	26	f	\N
112	89	124	37	26	f	\N
52	89	124	30	26	f	\N
64	89	124	33	26	f	\N
22	47	\N	18	7	f	\N
25	47	69	21	7	f	\N
26	47	80	22	7	f	\N
28	65	\N	18	18	f	\N
29	65	\N	19	18	f	\N
30	65	\N	20	18	f	\N
31	65	\N	23	18	f	\N
32	65	\N	21	18	f	\N
33	65	\N	22	18	f	\N
34	83	\N	18	23	f	\N
35	83	\N	19	23	f	\N
36	83	\N	20	23	f	\N
37	83	\N	23	23	f	\N
38	83	\N	21	23	f	\N
39	83	\N	22	23	f	\N
41	64	\N	19	18	f	\N
42	64	\N	23	18	f	\N
43	64	\N	27	18	f	\N
40	64	69	21	18	f	\N
44	64	\N	28	18	f	\N
45	39	\N	20	7	f	\N
46	46	\N	30	7	f	\N
27	47	100	23	7	f	\N
23	47	100	19	7	f	\N
24	47	99	20	7	f	\N
53	90	\N	30	26	f	\N
54	91	\N	30	26	f	\N
55	92	\N	30	26	f	\N
56	93	\N	30	26	f	\N
57	94	\N	30	26	f	\N
58	95	\N	30	26	f	\N
59	96	\N	30	26	f	\N
65	90	\N	33	26	f	\N
66	91	\N	33	26	f	\N
67	92	\N	33	26	f	\N
68	93	\N	33	26	f	\N
69	94	\N	33	26	f	\N
70	95	\N	33	26	f	\N
71	96	\N	33	26	f	\N
77	90	\N	34	26	f	\N
78	91	\N	34	26	f	\N
79	92	\N	34	26	f	\N
80	93	\N	34	26	f	\N
81	94	\N	34	26	f	\N
82	95	\N	34	26	f	\N
83	96	\N	34	26	f	\N
89	90	\N	35	26	f	\N
90	91	\N	35	26	f	\N
91	92	\N	35	26	f	\N
92	93	\N	35	26	f	\N
93	94	\N	35	26	f	\N
94	95	\N	35	26	f	\N
95	96	\N	35	26	f	\N
101	90	\N	28	26	f	\N
102	91	\N	28	26	f	\N
103	92	\N	28	26	f	\N
104	93	\N	28	26	f	\N
105	94	\N	28	26	f	\N
106	95	\N	28	26	f	\N
107	96	\N	28	26	f	\N
76	89	124	34	26	f	\N
88	89	124	35	26	f	\N
100	89	124	28	26	f	\N
122	84	86	22	10	f	\N
123	97	\N	37	28	f	\N
124	98	\N	37	28	f	\N
125	99	\N	37	28	f	\N
126	100	\N	37	28	f	\N
127	101	\N	37	28	f	\N
128	102	\N	37	28	f	\N
129	103	\N	37	28	f	\N
130	104	\N	37	28	f	\N
131	104	\N	30	28	f	\N
132	104	\N	33	28	f	\N
133	104	\N	34	28	f	\N
134	104	\N	35	28	f	\N
135	104	\N	28	28	f	\N
136	105	\N	37	28	f	\N
137	105	\N	30	28	f	\N
138	105	\N	33	28	f	\N
139	105	\N	34	28	f	\N
140	105	\N	35	28	f	\N
141	105	\N	28	28	f	\N
142	107	\N	33	28	f	\N
108	85	\N	37	26	f	\N
48	85	\N	30	26	f	\N
60	85	\N	33	26	f	\N
72	85	\N	34	26	f	\N
84	85	\N	35	26	f	\N
96	85	\N	28	26	f	\N
143	107	\N	34	28	f	\N
144	106	\N	37	28	f	\N
145	106	\N	30	28	f	\N
146	106	\N	33	28	f	\N
147	106	\N	34	28	f	\N
148	106	\N	35	28	f	\N
149	106	\N	28	28	f	\N
150	107	\N	37	28	f	\N
151	107	\N	30	28	f	\N
152	107	\N	35	28	f	\N
153	107	\N	28	28	f	\N
154	108	\N	37	28	f	\N
155	108	\N	30	28	f	\N
156	108	\N	33	28	f	\N
157	97	\N	30	28	f	\N
158	98	\N	30	28	f	\N
159	99	\N	30	28	f	\N
160	100	\N	30	28	f	\N
161	101	\N	30	28	f	\N
162	102	\N	30	28	f	\N
163	103	\N	30	28	f	\N
164	97	\N	33	28	f	\N
165	98	\N	33	28	f	\N
166	99	\N	33	28	f	\N
167	100	\N	33	28	f	\N
168	101	\N	33	28	f	\N
169	102	\N	33	28	f	\N
170	103	\N	33	28	f	\N
171	97	\N	34	28	f	\N
172	98	\N	34	28	f	\N
173	99	\N	34	28	f	\N
174	100	\N	34	28	f	\N
175	101	\N	34	28	f	\N
176	102	\N	34	28	f	\N
177	103	\N	34	28	f	\N
178	97	\N	35	28	f	\N
179	98	\N	35	28	f	\N
180	99	\N	35	28	f	\N
181	100	\N	35	28	f	\N
182	101	\N	35	28	f	\N
183	102	\N	35	28	f	\N
184	103	\N	35	28	f	\N
185	97	\N	28	28	f	\N
186	98	\N	28	28	f	\N
187	99	\N	28	28	f	\N
188	100	\N	28	28	f	\N
189	101	\N	28	28	f	\N
190	102	\N	28	28	f	\N
191	103	\N	28	28	f	\N
192	108	\N	34	28	f	\N
193	108	\N	35	28	f	\N
194	108	\N	28	28	f	\N
195	109	\N	37	30	f	\N
196	109	\N	30	30	f	\N
197	109	\N	33	30	f	\N
198	109	\N	34	30	f	\N
199	109	\N	35	30	f	\N
200	109	\N	28	30	f	\N
201	110	\N	37	30	f	\N
202	110	\N	30	30	f	\N
203	110	\N	33	30	f	\N
204	110	\N	34	30	f	\N
205	110	\N	35	30	f	\N
206	110	\N	28	30	f	\N
207	111	\N	37	30	f	\N
208	111	\N	30	30	f	\N
209	111	\N	33	30	f	\N
210	111	\N	34	30	f	\N
211	111	\N	35	30	f	\N
212	111	\N	28	30	f	\N
213	112	\N	37	30	f	\N
214	112	\N	30	30	f	\N
215	112	\N	33	30	f	\N
216	112	\N	34	30	f	\N
217	112	\N	35	30	f	\N
218	112	\N	28	30	f	\N
219	113	\N	37	30	f	\N
220	113	\N	30	30	f	\N
221	113	\N	33	30	f	\N
222	113	\N	34	30	f	\N
223	113	\N	35	30	f	\N
224	113	\N	28	30	f	\N
225	114	\N	37	30	f	\N
226	114	\N	30	30	f	\N
227	114	\N	33	30	f	\N
228	114	\N	34	30	f	\N
229	114	\N	35	30	f	\N
230	114	\N	28	30	f	\N
231	115	\N	37	30	f	\N
232	115	\N	30	30	f	\N
233	115	\N	33	30	f	\N
234	115	\N	34	30	f	\N
235	115	\N	35	30	f	\N
238	116	\N	30	30	f	\N
290	134	142	20	18	f	\N
298	135	142	20	18	f	\N
241	116	\N	35	30	f	\N
243	117	\N	37	30	f	\N
244	117	\N	30	30	f	\N
245	117	\N	33	30	f	\N
246	117	\N	34	30	f	\N
247	117	\N	35	30	f	\N
248	117	\N	28	30	f	\N
249	118	\N	37	30	f	\N
250	118	\N	30	30	f	\N
251	118	\N	33	30	f	\N
252	118	\N	34	30	f	\N
253	118	\N	35	30	f	\N
254	118	\N	28	30	f	\N
255	119	\N	33	30	f	\N
256	119	\N	34	30	f	\N
257	119	\N	37	30	f	\N
258	119	\N	30	30	f	\N
259	119	\N	35	30	f	\N
260	119	\N	28	30	f	\N
261	120	\N	37	30	f	\N
262	120	\N	30	30	f	\N
263	120	\N	33	30	f	\N
264	120	\N	34	30	f	\N
265	120	\N	35	30	f	\N
266	120	\N	28	30	f	\N
267	121	\N	21	15	f	\N
291	134	145	65	18	f	\N
269	133	\N	43	18	f	\N
443	130	145	187	18	f	2nd Term
286	134	162	60	18	f	\N
273	133	\N	20	18	f	\N
242	116	119	28	30	f	\N
276	133	\N	50	18	f	\N
236	115	\N	28	30	f	3rd Term
446	119	\N	190	30	f	Full Year
296	134	\N	51	18	f	\N
293	134	\N	67	18	f	\N
237	116	\N	37	30	f	\N
305	135	142	37	18	f	\N
423	136	142	23	18	f	\N
429	137	142	23	18	f	\N
310	136	142	20	18	f	\N
307	135	\N	81	18	f	\N
321	137	142	20	18	f	\N
315	136	\N	37	18	f	\N
316	136	\N	81	18	f	\N
319	137	162	60	18	f	\N
318	137	146	92	18	f	\N
306	135	146	80	18	f	\N
317	136	146	80	18	f	\N
381	134	146	21	18	f	\N
405	135	152	43	18	f	\N
304	135	147	60	18	f	\N
314	136	147	60	18	f	\N
367	132	147	135	18	f	\N
374	132	147	43	18	f	\N
375	132	147	143	18	f	\N
380	132	147	23	18	f	\N
392	132	147	22	18	f	\N
393	132	147	21	18	f	\N
240	116	124	34	30	f	\N
239	116	124	33	30	f	\N
394	132	147	19	18	f	\N
395	132	147	49	18	f	\N
396	132	147	164	18	f	\N
404	134	147	43	18	f	\N
411	134	147	135	18	f	\N
324	137	152	37	18	f	\N
412	135	152	135	18	f	\N
414	134	152	19	18	f	\N
416	136	152	19	18	f	\N
415	135	152	19	18	f	\N
406	136	144	43	18	f	\N
413	136	144	135	18	f	\N
418	134	144	22	18	f	\N
419	135	144	22	18	f	\N
420	136	144	22	18	f	\N
384	138	\N	152	30	f	\N
386	138	\N	154	30	f	\N
387	138	\N	155	30	f	\N
389	138	\N	157	30	f	\N
390	138	\N	158	30	f	\N
388	138	114	156	30	f	\N
385	138	114	153	30	f	\N
383	138	114	151	30	f	\N
382	138	114	150	30	f	\N
391	116	\N	159	30	f	\N
435	137	144	22	18	f	\N
397	133	\N	135	18	f	\N
398	133	\N	22	18	f	\N
399	133	\N	21	18	f	\N
400	133	\N	19	18	f	\N
401	133	\N	23	18	f	\N
402	133	\N	49	18	f	\N
403	133	\N	143	18	f	\N
408	123	\N	43	18	f	\N
407	137	146	43	18	f	\N
417	134	146	175	18	f	\N
421	134	146	23	18	f	\N
422	135	146	23	18	f	\N
424	135	146	21	18	f	\N
425	136	146	21	18	f	\N
432	137	146	21	18	f	\N
325	137	165	99	18	f	\N
326	137	165	80	18	f	\N
329	122	143	20	18	f	\N
338	125	143	20	18	f	\N
439	130	143	23	18	f	\N
440	127	143	23	18	f	\N
441	129	143	23	18	f	\N
332	122	139	60	18	f	\N
336	122	164	80	18	f	\N
426	137	164	19	18	f	\N
362	129	158	130	18	f	\N
438	125	163	175	18	f	\N
365	129	163	127	18	f	\N
427	122	163	19	18	f	\N
428	125	163	19	18	f	\N
337	125	141	92	18	f	\N
311	136	141	28	18	f	\N
345	125	141	37	18	f	\N
350	127	141	122	18	f	\N
335	122	158	37	18	f	\N
356	127	141	125	18	f	\N
357	130	141	125	18	f	\N
366	129	141	125	18	f	\N
410	125	141	43	18	f	\N
437	125	141	22	18	f	\N
346	127	158	120	18	f	\N
348	127	161	121	18	f	\N
361	129	161	121	18	f	\N
344	125	161	60	18	f	\N
351	130	141	122	18	f	1st Term
359	130	163	127	18	f	1st Term
349	130	161	121	18	f	1st Term
360	129	158	120	18	f	\N
430	122	158	23	18	f	\N
431	125	158	23	18	f	\N
436	122	158	22	18	f	\N
347	130	158	120	18	f	1st Term
301	135	145	27	18	f	\N
327	122	145	92	18	f	\N
409	122	145	43	18	f	\N
334	122	145	28	18	f	\N
343	125	145	28	18	f	\N
354	127	159	124	18	f	\N
358	127	159	126	18	f	\N
364	129	159	124	18	f	\N
433	122	159	21	18	f	\N
434	125	159	21	18	f	\N
355	130	159	124	18	f	1st Term
444	130	159	188	18	f	2nd Term
\.


--
-- Data for Name: sections; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.sections (section_id, branch_id, grade_level, section_name, school_year, created_at, teacher_id, grade_level_id, capacity, year_id) FROM stdin;
131	1	\N	St. Raphael the Archangel	\N	2026-09-08 03:41:10.618074	\N	39	50	18
133	1	\N	St. Maria Goretti	\N	2026-09-08 03:42:16.070394	\N	41	50	18
89	10	\N	ST. PETER	\N	2026-08-19 03:34:42.622718	\N	80	50	26
137	1	\N	St. Mary, Mother of God	\N	2026-09-13 14:27:44.729614	146	45	55	18
87	10	\N	ST. JOSEPH	\N	2026-08-19 03:33:27.777485	\N	78	50	26
85	10	\N	ST. MARY	\N	2026-08-19 03:32:36.783508	\N	76	50	26
139	1	\N	St. Catherine of Siena	\N	2026-09-24 09:51:09.221423	\N	100	50	18
135	1	\N	St. Lorenzo Ruiz	\N	2026-09-08 03:43:12.330526	152	43	50	18
90	10	\N	ST. THOMAS	\N	2026-08-19 03:35:02.386921	\N	81	50	26
91	10	\N	ST. MARGARETTE	\N	2026-08-19 03:35:30.432957	\N	82	50	26
92	10	\N	ST. ANA	\N	2026-08-19 03:35:46.365994	\N	83	50	26
93	10	\N	ST. PAUL	\N	2026-08-19 03:36:43.189848	\N	84	50	26
94	10	\N	ST. MONICA	\N	2026-08-19 03:37:05.993702	\N	85	50	26
95	10	\N	ST. PADRE PIO	\N	2026-08-19 03:37:33.330325	\N	86	50	26
96	10	\N	ST. DOMINIC	\N	2026-08-19 03:37:59.331207	\N	87	50	26
86	10	\N	ST. THERESE	\N	2026-08-19 03:33:01.905683	117	77	50	26
84	4	\N	St. Bernadette	\N	2026-08-18 03:40:54.528869	121	75	50	10
88	10	\N	ST. GREGORY	\N	2026-08-19 03:33:48.2671	123	79	50	26
97	10	\N	ST. THOMAS	\N	2026-09-05 13:18:35.53363	\N	81	50	28
98	10	\N	ST. MARGARETTE	\N	2026-09-05 13:18:35.53363	\N	82	50	28
99	10	\N	ST. ANA	\N	2026-09-05 13:18:35.53363	\N	83	50	28
100	10	\N	ST. PAUL	\N	2026-09-05 13:18:35.53363	\N	84	50	28
101	10	\N	ST. MONICA	\N	2026-09-05 13:18:35.53363	\N	85	50	28
102	10	\N	ST. PADRE PIO	\N	2026-09-05 13:18:35.53363	\N	86	50	28
103	10	\N	ST. DOMINIC	\N	2026-09-05 13:18:35.53363	\N	87	50	28
104	10	\N	ST. MARY	\N	2026-09-05 13:18:35.53363	\N	76	50	28
105	10	\N	ST. THERESE	\N	2026-09-05 13:18:35.53363	\N	77	50	28
106	10	\N	ST. GREGORY	\N	2026-09-05 13:18:35.53363	\N	79	50	28
107	10	\N	ST. JOSEPH	\N	2026-09-05 13:18:35.53363	\N	78	50	28
108	10	\N	ST. PETER	\N	2026-09-05 13:18:35.53363	\N	80	50	28
109	10	\N	ST. THOMAS	\N	2026-09-05 13:30:58.130975	\N	81	50	30
110	10	\N	ST. MARGARETTE	\N	2026-09-05 13:30:58.130975	\N	82	50	30
111	10	\N	ST. ANA	\N	2026-09-05 13:30:58.130975	\N	83	50	30
112	10	\N	ST. PAUL	\N	2026-09-05 13:30:58.130975	\N	84	50	30
113	10	\N	ST. MONICA	\N	2026-09-05 13:30:58.130975	\N	85	50	30
114	10	\N	ST. PADRE PIO	\N	2026-09-05 13:30:58.130975	\N	86	50	30
115	10	\N	ST. DOMINIC	\N	2026-09-05 13:30:58.130975	\N	87	50	30
116	10	\N	ST. MARY	\N	2026-09-05 13:30:58.130975	\N	76	50	30
117	10	\N	ST. THERESE	\N	2026-09-05 13:30:58.130975	\N	77	50	30
118	10	\N	ST. GREGORY	\N	2026-09-05 13:30:58.130975	\N	79	50	30
119	10	\N	ST. JOSEPH	\N	2026-09-05 13:30:58.130975	\N	78	50	30
120	10	\N	ST. PETER	\N	2026-09-05 13:30:58.130975	\N	80	50	30
121	4	\N	St. Joseph	\N	2026-09-05 13:34:23.553586	\N	96	50	15
123	1	\N	St. Elizabeth	\N	2026-09-07 02:51:26.940608	\N	46	50	18
136	1	\N	St. John Bosco	\N	2026-09-08 03:43:35.56182	144	44	50	18
125	1	\N	St. Peter the Apostle	\N	2026-09-07 02:51:42.631765	141	48	50	18
129	1	\N	St. Augustine of Hippo	\N	2026-09-07 05:06:06.44934	158	248	50	18
130	1	\N	St. Gregory the Great	\N	2026-09-07 05:10:28.423279	158	247	50	18
127	1	\N	St. Leo The Great	\N	2026-09-07 05:05:19.003071	158	246	50	18
138	10	\N	St. Therese of the Child Jesus	\N	2026-09-22 06:14:49.911194	\N	182	55	30
140	1	\N	St. Therese of the Child Jesus	\N	2026-09-24 09:51:39.964219	\N	100	50	18
122	1	\N	St. Paul the Apostle	\N	2026-09-07 02:51:08.280798	145	47	50	18
126	1	\N	St. Thomas Aquinas	\N	2026-09-07 05:04:46.371371	143	245	50	18
134	1	\N	St. Pedro Calungsod	\N	2026-09-08 03:42:44.793135	147	42	50	18
132	1	\N	St. Dominic Savio	\N	2026-09-08 03:41:36.079342	147	40	50	18
\.


--
-- Data for Name: shs_elective_offerings; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.shs_elective_offerings (offering_id, branch_id, year_id, term_name, section_teacher_id, group_code, shs_track, capacity, status, created_at) FROM stdin;
1	10	30	2nd	388	AdMath	Academic	55	ACTIVE	2026-09-22 07:22:23.154092
2	10	30	2nd	390	ADMATH2	Academic	55	ACTIVE	2026-09-22 07:53:51.21626
3	10	30	2nd	389	precal	Academic	55	ACTIVE	2026-09-29 11:13:50.82785
\.


--
-- Data for Name: shs_pathways; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.shs_pathways (pathway_id, branch_id, track_name, pathway_name, description, is_active, display_order, created_at) FROM stdin;
2	10	Academic	Science	\N	t	0	2026-09-22 05:46:03.460215
1	10	Academic	Math	\N	t	0	2026-09-22 05:45:58.616593
\.


--
-- Data for Name: shs_selection_periods; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.shs_selection_periods (period_id, branch_id, year_id, term_name, status, opened_at, closed_at) FROM stdin;
1	10	30	2nd	OPEN	2026-10-07 13:16:44.322599	\N
\.


--
-- Data for Name: shs_student_elective_items; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.shs_student_elective_items (item_id, request_id, offering_id) FROM stdin;
\.


--
-- Data for Name: shs_student_elective_memberships; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.shs_student_elective_memberships (membership_id, enrollment_id, student_user_id, offering_id, term_name, year_id, status, enrolled_at, dropped_at) FROM stdin;
1	489	\N	1	2nd	30	ACTIVE	2026-09-22 07:22:54.696151	\N
2	491	\N	1	2nd	30	ACTIVE	2026-09-22 07:45:13.606437	\N
\.


--
-- Data for Name: shs_student_elective_requests; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.shs_student_elective_requests (request_id, enrollment_id, student_user_id, branch_id, year_id, term_name, status, revision_reason, submitted_at, reviewed_by, reviewed_at) FROM stdin;
\.


--
-- Data for Name: student_accounts; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.student_accounts (account_id, enrollment_id, branch_id, username, password, email, is_active, created_at, require_password_change, last_password_change, full_name, gender, contact_number, dob, profile_image) FROM stdin;
31	142	10	LDBB_0005	scrypt:32768:8:1$Nl4lKQKiiVxkL9Jo$b68c9a227044f529b470e0e3e46dfffd66cfbab9a6f5994a53861d9c62241ae33a472c0bac1d4fc6d9372c677dba2765891772c1c9f4996bf5e7a7425055cb05	chelzycada@gmail.com	t	2026-08-31 08:16:26.058434	f	\N	\N	\N	\N	\N	\N
30	141	10	LDBB_0004	scrypt:32768:8:1$NHDnwPUoF1sCxlbJ$b5d44670c24564d977042a73e26712cb46be91453c389101f8bd1f67efc10481538ba012dfd9842489faa891e375de2937841c86b951d9134385af1535bf384f	mariasierrajunterial@gmail.com	t	2026-08-31 08:16:13.782275	f	\N	\N	\N	\N	\N	\N
32	136	10	LDBB_0001	scrypt:32768:8:1$5eZNX4GkuprdpdHT$327c511386fb3ed2ad2d6a405b6b82c225170060e3422467420930cadf33be121bf527e6c5b8d4afe662ae7cb82918608271bb89d46c837323e8782251b677d4	biticonmr@gmail.com	t	2026-08-31 08:17:50.28213	f	\N	\N	\N	\N	\N	\N
33	138	10	LDBB_0003	scrypt:32768:8:1$jczC6PPfmLrFvcVu$75a4e99d8102f9abce71f5b61a75cf94759495857c33781dbe1eb16f412a95300ee487ef4720b3c38625de37d1e094a20362b5159143166db2c8054107647bf6	bakagoku3@gmail.com	t	2026-08-31 23:46:12.868143	t	\N	\N	\N	\N	\N	\N
34	137	10	LDBB_0002	scrypt:32768:8:1$HRW4Q1wwKjTt0ecU$492e2bbc4d63d6217a1bbc57b3147787e12e391283e12b56cf40c7d1b974e76248724bad281c7ef797b96973671d56493027e7825c5321cd09de586542c7f7f9	bakagokuto3@gmail.com	t	2026-08-31 23:50:45.351433	t	\N	\N	\N	\N	\N	\N
35	143	10	LDBB_0006	scrypt:32768:8:1$Y4JxCPgzlLzIbLJt$161a368ba0c78677cee060c7958ee511776913cbb5db24117b8fbe55876f0110f53b839d1a978ba8f45d11d3c4815e039b17c3dd49109c9750f6deb2090c649e	venice.caparros@gmail.com	t	2026-09-01 01:49:27.676312	f	\N	\N	\N	\N	\N	\N
36	144	10	LDBB_0007	scrypt:32768:8:1$MIVhvgBAu905HFLH$babfed3857387667cbf477ac34a02f9a18400fd062b93671f659b8d9d2752b56a6ac18cb42b6fd70fbde1617e321cad2dee4dd9cb0d62026c2d0ba71c8348153	oninnapiza4@gmail.com	t	2026-09-01 01:53:44.533135	f	\N	\N	\N	\N	\N	\N
42	487	10	LDBB_0013	scrypt:32768:8:1$FANwyeeRL5xSkfPQ$aafaa6bf7fae36c122a4cefbda345c08a429dcd4d7448faff0af87e533a7ed683ee63df64a89f793da4957f04f45422f61452d69b22c15118582dfc30feea741	bakagokuto@gmail.comgmail.com	t	2026-09-18 02:56:35.354919	t	\N	\N	\N	\N	\N	\N
27	135	4	LDPSJ_0002	scrypt:32768:8:1$Mn2aNdVNvg1PbjPk$4300be39ae4d35991b51f5d45dea20b3aa4a5c5e8fbfdb2eae7884dc80ca228424184310080bb524654f79018a3fb5afd5c7d590071963a5931ca65a4974d89b	bakagokuto1@gmail.com	t	2026-08-19 04:13:09.353524	f	\N	\N	\N	\N	\N	\N
28	139	4	LDPSJ_0003	scrypt:32768:8:1$v1MnyG4ovuSEINy8$0ed1a7f2734ff20732497a9920e767ea34004544b1fe0fcf273629f1148fd71abfc21b40c4691d12401fded8df8a54610d0e9f42a43d37d50afaf82ce2f85498	biticonmr1@gmail.com	t	2026-08-19 08:15:11.355736	t	\N	\N	\N	\N	\N	\N
29	140	4	LDPSJ_0004	scrypt:32768:8:1$Zn8CE3AttK3I6KDP$2fffe400c7a72ab2c74b65fab91f45c896a5e48c68f43fd17e733d8c1b0b405e109c07f718f1c90457bccab441c70834653f1585e34e8cffadacdb9426911f61	biticonmeryll@gmail.com	t	2026-08-19 11:33:22.320019	f	\N	\N	\N	\N	\N	\N
37	145	10	LDBB_0008	scrypt:32768:8:1$bIsOCSy1bvAS68hf$c8d35dc970ed744fe6ae7915473333363c192eb870e9c58fa5c93ea6f56b9f96a1c89059f3b5fbbe8155bd870dbb06ee9385bc3f428569588dd8c63c93977bcc	markjohnpascua08@gmail.com	t	2026-09-01 01:58:52.360847	f	\N	\N	\N	\N	\N	\N
38	146	10	LDBB_0009	scrypt:32768:8:1$2swlnFD3DeiK7J5y$b63af98ac61330df9c8dfb2720b2ecf452e4c3b63183f0af488857fa31da82db103d15d1eaab5d2a3f662b72151e2d62aab31eca2f6eaec506b56e4201c3fa7a	bladimierdiego9@gmail.com	t	2026-09-01 02:07:50.121922	f	\N	\N	\N	\N	\N	\N
39	147	10	LDBB_0010	scrypt:32768:8:1$D3WkADHuYYE7tAxI$c3f690e066d56c301f8068668a562387b2737ed9344c30e0405422caec6bc758d4bc8402233ca4c7b1f65951ec3f6ca2092fcbb803e6279810e9b1677c174218	timoteojocazphoebe@gmail.com	t	2026-09-01 02:16:58.36919	t	\N	\N	\N	\N	\N	\N
40	148	10	LDBB_0011	scrypt:32768:8:1$6zQ3E49VHqCVqPzz$3a44de8145a993c6e5ea05411f16faba7e8cf435e5ae5a76fb5022b2c0b0e49f025f4bbc5088de668679875cf1da1620551ffe474b91de186e34743e96f0ecb4	angeloponce209@gmail.com	t	2026-09-01 02:22:01.793759	f	\N	\N	\N	\N	\N	\N
41	149	10	LDBB_0012	scrypt:32768:8:1$stvCV2djS6CSQJIP$dcdcc58d5c30f75fe4560f22c8dcabc3c729ee647f9e031c6619808e13cc292330d5d3c81fea37049fbd3895c041bf1aed39645e010f10c6fca2f42e937c4b21	rcyciaronresurreccion841@gmail.com	t	2026-09-01 03:10:18.671751	t	\N	\N	\N	\N	\N	\N
26	150	4	LDPSJ_0001	scrypt:32768:8:1$23rOjaW6d6lEsNkA$f47b50a3885c251d4afbb5b89c13b09516c21b51c96c6675002d85a8b6dc93b8a795b8cffbf8504efcc3eaeb963f637c726b0c4f301a943a143e441488323b56	melbournebiticon@gmail.com	t	2026-08-18 03:18:14.073828	f	\N	\N	\N	\N	\N	https://res.cloudinary.com/diwiuseil/image/upload/v1787102652/liceo_uploads/profiles/arthur_15476d.jpg
43	488	10	LDBB_0014	scrypt:32768:8:1$owzGWIAE7l46gyVx$618cdc12aa09242c0393b8302406a3d7cf4c0a9fe65fee54ef5853ccd4c4a9d5a8dc9e809421c0590ac72cef5e287fb8090ee4cdd2f569f56c7e541ebf6de226	biticonmr@gmail.com	t	2026-09-18 02:58:11.592425	f	\N	\N	\N	\N	\N	\N
44	490	10	LDBB_0016	scrypt:32768:8:1$UnLSIjiMXWIuxC03$12c5036f3444c8b7b9e10070628d3a60d3f026cfef411fdd546a64360f9a3cf94c49bb0221c463ab8ab799fbea3baef38d7b7c7c34a08c4424075f712809f162	mariasierrajunterial@gmail.com	t	2026-09-22 07:03:42.249296	f	\N	\N	\N	\N	\N	\N
51	318	1	LDMAJ_0168	scrypt:32768:8:1$zEqatS8jRoFGikh8$b423e8ff5e90759a0857efaa48061382f97c571ebfbed451a72db8f44a7ab7a1bcb221b5e29189f9381143ffb0fbd13b4aa811f257c87d383b0a76cf54391f7e	Lucaskeanmillar@gmail.com	t	2026-09-24 09:18:58.056658	t	\N	\N	\N	\N	\N	\N
48	493	10	LDBB_0018	scrypt:32768:8:1$ZhDz1CZnUTZ6qj44$bcdbf9ccf967c6616044a57edcf954690486d1ca7ffc33b9d8e6905f281780d2be06730781d501b1cc0c6069dc970e45bbcd4a6c84558269087c7e9686a85e35	bakagokuto@gmail.com	t	2026-09-22 08:32:55.890558	f	\N	\N	\N	\N	\N	\N
45	489	10	LDBB_0015	12345678	melbournerb@gmail.com	t	2026-09-22 07:05:20.097259	f	\N	\N	\N	\N	\N	\N
46	491	10	LDBB_0017	scrypt:32768:8:1$K2ftnhB0rQUcsHAE$6590103a00e39d06348d08c9801a523cdb9a0321a88eb3cfd4e7eeaed581ee51bfc76228925fdc87b084b451c5f3c78c5d7a0329788be725ad95a499cae6e8d9	melbournebiticon@gmail.com	t	2026-09-22 07:45:13.484622	t	\N	\N	\N	\N	\N	\N
49	494	10	LDBB_0019	scrypt:32768:8:1$EsvRbFbkTYSKudbz$394647e1b43094e104c6bb044bd49c04b9c8718fad68cfca463b69a23b02db849d3e359409172972de4e7b2449753f9b76b6e362d999f149d4b53f085895b93b	imbonpogi@gmail.com	t	2026-09-22 12:42:12.364977	t	\N	\N	\N	\N	\N	\N
50	325	1	LDMAJ_0175	scrypt:32768:8:1$kTY2RZTZQWOKHy35$b8ee9aafa2db731ee369c9e613395dc4179bc72ff7eca012a31534c3685a372d06e2cfd5e0853e221825075679924982a4b5db58c06277cd7bc35902563f113d	elaine.badiola@deped.gov.ph	t	2026-09-24 09:18:41.064187	t	\N	\N	\N	\N	\N	\N
52	313	1	LDMAJ_0163	scrypt:32768:8:1$486gVBmL1jYOPumq$21713e4a667dfc6fe9a94f230c425434465109b52359ebba13752aefdcf0ccd1a67d5a7b78de695339a712f12c19908632329c639e7d98721b01d133b9acf1fc	reynvahomes@gmail.com	t	2026-09-24 09:19:11.524461	t	\N	\N	\N	\N	\N	\N
54	321	1	LDMAJ_0171	scrypt:32768:8:1$nkZUyM1zyfHIXxHY$e919221aa7cc58f70c793e33c02e27e4f513b2d9c3ef4829d54f0802adeae17b6d1c221741ae76fc92aa3ff7eee7e7b59e8fbeed5e78372f18326d498ab99cf1	villaraza.maricris25@gmail.com	t	2026-09-24 12:24:29.474621	t	\N	\N	\N	\N	\N	\N
55	225	1	LDMAJ_0075	scrypt:32768:8:1$afj2yQbssT8yxAlV$d6de9019599627e355b31a8e3e13ed1eb1454c1116afd875f4a930680cef8719b27fb5aca4f1d2ff89a1333f864d80a8adf4b0857855f9e1836fc5f993a3cd7d	abiadagianna@gmail.con	t	2026-09-24 12:24:36.944194	t	\N	\N	\N	\N	\N	\N
56	234	1	LDMAJ_0084	scrypt:32768:8:1$PXU2VGOlb2Eg9AAa$8cdd85a4dd9e5b2b7ad4db369ca695904b708f1eca2bfcb25c09f6d01404953fb3c1a53cdbdf15c4586421b8f956a036454763abd3948d01c1ada3cead63c2a4	kiziaarnuco@gmail.com	t	2026-09-24 12:24:44.699097	t	\N	\N	\N	\N	\N	\N
57	242	1	LDMAJ_0092	scrypt:32768:8:1$8r7TwDUbm4xxZm1P$24eca8fdcfe557b3c5ad3250bd90d0996ed1922074b5c5a5fed137a9a8f8b42886f4949f9a8d579070ac75912ecf91e63b32852c8029201324a106a6b413428b	reniellebernardo11@gmail.com	t	2026-09-24 12:25:21.582061	t	\N	\N	\N	\N	\N	\N
58	274	1	LDMAJ_0124	scrypt:32768:8:1$zAqVNYMWQLKrMdJo$3558244a3a16e4a000b6c6d73d133647ac6942a6ccaf428dfd5c3800b997880f99b69fcdd44d8fba071e7c54b768be2b311a2ad675e7087ad7348e3e007ad959	markmjbojabe@gmail.com	t	2026-09-24 12:25:27.964787	t	\N	\N	\N	\N	\N	\N
59	216	1	LDMAJ_0066	scrypt:32768:8:1$IgkeIVKAbUwZeBxD$677da89a59d4960bd3dd7b5bc94295f2f9c0dd0e888a75fe3f6fbc73ec625a9244e3884540c4f6c063cd7b539ab48b9bf1c770e7e9b1339bed115e307840eb15	rhonjacobadelsol@gmail.com	t	2026-09-24 12:25:37.147209	t	\N	\N	\N	\N	\N	\N
60	210	1	LDMAJ_0060	scrypt:32768:8:1$GD6DYB5CW1vWELa7$60c22a52040bdfdf2e75b4621e7d69836bba54621af0e177648801b96fba1d5bd320f2349d8eeba5bf5431a0ddc3ce06b078de3a3c2cabc11e663f3a3b7e617c	jacobespedido6@gmail.com	t	2026-09-24 12:25:49.510914	t	\N	\N	\N	\N	\N	\N
61	198	1	LDMAJ_0048	scrypt:32768:8:1$W87hyEJXJSqf8zZG$c371c1ad30cc1a4e42a31bb70e01b0a846b0391021950c53ccb71227faa2c60c97d6de0c89f005d915ba31de60c22591dc1bf615f4fb199277d2ccc6e8578972	valerieestebal1@gmail.com	t	2026-09-24 12:26:02.351897	t	\N	\N	\N	\N	\N	\N
62	181	1	LDMAJ_0031	scrypt:32768:8:1$ebbvR5D9k8Vv0Sis$d28245afff81f3dbaf0079174b454c4b64386d09c8086db1e4d858163963653775357c950199915cd5dfb7cdad611e725b19c017227a25bf45fa0746aaf9b4bd	sanjoseestuitamichaelbenedict@gmail.com	t	2026-09-24 12:26:16.537572	t	\N	\N	\N	\N	\N	\N
63	228	1	LDMAJ_0078	scrypt:32768:8:1$sa5AN01ltrbSK7wo$f7a13f42bca919cd4827cbaa3b9a35d7e4b08a0ad8c641f12f50a65c01d325c4f70c011b60e5ca7c272682bce038d668483c7eff022c8c9416bd11e4a2223cc7	theonlykurtyzy@gmail.com	t	2026-09-24 12:26:28.216021	t	\N	\N	\N	\N	\N	\N
53	323	1	LDMAJ_0173	scrypt:32768:8:1$hsfxxF2i4SAYE873$2feed0fc1891fffaff4a5f54174356bf46746712369ff4cf53c304b8307fe906d2133780a0fb2f93c57b2a255aaedfe03ac691017db6e5f9322e7a4de8b6fe80	jhoannaricamara@gmail.com	t	2026-09-24 12:24:20.806614	f	\N	\N	\N	\N	\N	\N
64	185	1	LDMAJ_0035	scrypt:32768:8:1$MvH8yiSSfuYoTKIp$80993fa73bb6426ac3a0aa77042d2f9f5ecb00065aef0bc0b3057dd474769ede9f571add6579b53d74184b1959919d5873ebfc9dfbf3f9b591ddbb2f40deb868	vashneefraginal@gmail.com	t	2026-09-24 12:27:19.365969	t	\N	\N	\N	\N	\N	\N
65	153	1	LDMAJ_0003	scrypt:32768:8:1$zy2ZutaFIg81j824$3d6cbfd3d89e6b7be54ede155b0e07953f8f61e305c5392ca06aa82476babd913bb2984454b1d80629c503d6c8a94a7ac71a90f3c3c4fc2d2d17316717287a9f	sereenakhloe@gmail.com	t	2026-09-24 12:27:28.839665	t	\N	\N	\N	\N	\N	\N
66	175	1	LDMAJ_0025	scrypt:32768:8:1$gwGEwKuj4PtiNmk3$02d8c1ac24cc580439a73146c6ddea5514039be105eccd9eec19bab6d98d36a65776d7cfdd1ff66522e108c7548a88beec233c2e6c04fc37d05698953175de47	shilohreesejavellana224@gmail.com	t	2026-09-24 12:27:37.654829	t	\N	\N	\N	\N	\N	\N
67	238	1	LDMAJ_0088	scrypt:32768:8:1$epoSc7uGzhT3zCPU$cc8b54fb3406c16faa3809093e3deba236c2902008fbab29e3f1b2435fd2355813972abe6f9f73fe3e82806df18c11cbb17c72ddc9b9df75af879131cceb2f6f	thirdymalait2006@gmail.com	t	2026-09-24 12:27:46.965462	t	\N	\N	\N	\N	\N	\N
68	239	1	LDMAJ_0089	scrypt:32768:8:1$VtITlnqjbmfljc5g$05c33831ccf59869dec924075febe66e5d8cc95373dfa0721e72fbdf3f7d3691cc7a19bcc87a21e2de4e7d560b116ae74c4b31fc3b356e06bfbb2c68e6bc563a	medinabarlleygrace@gmail.com	t	2026-09-24 12:27:57.048036	t	\N	\N	\N	\N	\N	\N
69	263	1	LDMAJ_0113	scrypt:32768:8:1$aaYbeSrDyilNv55d$b36fe9e3d5d1b99fcf438fcca42c01a4b670469c75cbdbee7f0c651153249a6afec75efa183c17e476e02faba7cab3262ffeeb679206536fc70cb75fad4ebf7d	briannajocellemiranda@gmail.com	t	2026-09-24 12:28:08.286255	t	\N	\N	\N	\N	\N	\N
70	485	1	LDMAJ_0335	scrypt:32768:8:1$VFF0IhDSwkZiCIFz$73509600968c85f24ade02e6cc16a1f655bc8694ad01e9618ad319dc46fa4e63766988fda7aa0a22563b6905556bfbce2d59b3ce0dbcb5de67e53189f0eb2cb2	howardleemodina@gmail.com	t	2026-09-24 12:28:22.660467	t	\N	\N	\N	\N	\N	\N
71	278	1	LDMAJ_0128	scrypt:32768:8:1$r6Y8WWVuIaTbQcZK$c8e98e8a6d052b849d1422d8932165498d8721036383581142c02ba6a0a41d6395496a078332e4a7d99c3de868899f715be2d9bf3b127fe5bf538fd6267ee4aa	princessannetaguiam@gmail.com	t	2026-09-24 12:28:33.617328	t	\N	\N	\N	\N	\N	\N
72	442	1	LDMAJ_0292	scrypt:32768:8:1$Z9Gdux6j2JwFnn4b$2413574f6c9b1f4f2a35ac12aaa9a92da29ecfaa3aef145f485f1bdf802a2d07812cbc035c0dac87974c006fe8fb4a8dbb13ef075c46ecc9188e1eddcc629d37	daneashleyarca@gmail.com	t	2026-09-24 12:31:34.753929	t	\N	\N	\N	\N	\N	\N
73	415	1	LDMAJ_0265	scrypt:32768:8:1$FxJiq5h8MWyevDcT$7a8d51fcf115b85b55538a953d5846ce0f590f973549d2a5c393360ae32915ffa34f3cc5ed8f3c7997eac84e1800241941a17d9cf854cad6b60ab088a7458ece	tommyasto6@gmail.com	t	2026-09-24 12:31:52.915521	t	\N	\N	\N	\N	\N	\N
74	411	1	LDMAJ_0261	scrypt:32768:8:1$bAdQjFt7iajYZy7T$e344f7bf4c9f01c814538896ac1685fdf2c4c3cef62b0dfb612f097a3e7885c79dd4f17e0d26d49a5be324858e38c857ebe969d833ff51a120f2e324d86cce71	bbeongbataabon@gmail.com	t	2026-09-24 12:32:08.808316	t	\N	\N	\N	\N	\N	\N
75	428	1	LDMAJ_0278	scrypt:32768:8:1$k6gq17cr8yV19c2n$5051553b6a34405e103ba2b7363fd96c18774951cb2d5b029f81e57ed5896ac40244e521c1170bab6d53f575e425961bc389bb9e209bfcb5d524dd0a4dc6583c	besoloren0520@gmail.com	t	2026-09-24 12:32:25.395268	t	\N	\N	\N	\N	\N	\N
76	430	1	LDMAJ_0280	scrypt:32768:8:1$9OWlICz5pTmKeanv$23dc4871214378441b1f190b905ddb7af5bc21e8b83a0f5707ad19db14b2cfbe13d0465f8ade0b5c939c9445e4b13fbcfe087e4bedf0e4a921e9b05535acba72	bbeongbataabon@gmail.com	t	2026-09-24 12:32:44.895982	t	\N	\N	\N	\N	\N	\N
77	438	1	LDMAJ_0288	scrypt:32768:8:1$w1ZNO0UoADS3fFKR$bfd127fde2e060a49da9f5cbce4a98a8f17d6dd26ac29d16f02efe889bbbeff9a5252fd6e46bf57cf6d2fe98a40906708d2e4bb5f962dcc16b116e1b6ed18c09	Queenb026880@gmail.com	t	2026-09-24 12:33:04.532335	t	\N	\N	\N	\N	\N	\N
78	406	1	LDMAJ_0256	scrypt:32768:8:1$D7gScRT30mI9EXFt$6a6ddfdc84e7685e42ed24f415d1ac7895d479062d71f98c7347b7158127ace356d1cb03007cd55001654a52d60e37c38b1af46a057a98e79e489faf0d41dca4	noahjoshcadag3@gmail.com	t	2026-09-24 12:33:22.195618	t	\N	\N	\N	\N	\N	\N
79	443	1	LDMAJ_0293	scrypt:32768:8:1$GflWzuLgafJ5hLqb$6ae2dfd5a9318e06440331a2d8a4bad21f2839a5677b9c8f2d184c318dd71c43d0c054e51a43255a65fb42922642fb082de74dc3ad92d945f046decdfe155f52	kylaceria18@gmail.com	t	2026-09-24 12:33:39.841749	t	\N	\N	\N	\N	\N	\N
80	431	1	LDMAJ_0281	scrypt:32768:8:1$vztSrPnum8HDd6am$937d28456fedb0bf8070d27ce0b143f483f50fb1245c212850ea8bd2692617dd37e4512988158d8b872247087f73ecd6cd10fa755e77aae83ea5dedd2d478ce6	comendadorelaiza8@gmail.com	t	2026-09-24 12:36:21.896409	t	\N	\N	\N	\N	\N	\N
81	398	1	LDMAJ_0248	scrypt:32768:8:1$gCB55tdJh2N1V6ke$1ceb3997e3d6df0bdc80b0b2da95b12686cf1f6aeaf81a9e898398e339332a5f13ffa255b86e1ff1a9f6a3ccb31ef9b190eb10433ca62ef12a504510c0ad57af	johndonsales167@gmail.com	t	2026-09-24 12:36:43.168698	t	\N	\N	\N	\N	\N	\N
82	439	1	LDMAJ_0289	scrypt:32768:8:1$daFal5GcrkU2Vfv7$82448c6ee2196021dca7349ff79441841bec8d373c4530657859b91f79dc0ca85e89fb99912849fc86d07898e5e0627f31e9c5f76bad339e3e6c8c0c858ad277	kyladurante5@gmail.com	t	2026-09-24 12:37:28.866463	t	\N	\N	\N	\N	\N	\N
83	451	1	LDMAJ_0301	scrypt:32768:8:1$WZcUUFeA3CBG9YGQ$7b4116a28e691dc7b6e42b6a20e451f8268bd01974b3ae87a11cf8b6fd7c066cf863f5badd0fe3ed3fe3c5deefe84ed6d656473ef689db7c27a3e6804b13bfb6	joyanngranada@gmail.com	t	2026-09-24 12:38:49.333364	t	\N	\N	\N	\N	\N	\N
84	450	1	LDMAJ_0300	scrypt:32768:8:1$FshOLVnjj6XryisZ$c862c34cff4d8a9708fda07b45bd58ef56391782c06fbaf6e5c85d27d3265f93aa6505527d2eacaef7253864f8870747234442a41c23b72614298c606ab783e3	granadacrystaljoyceann@gmail.com	t	2026-09-24 12:39:07.011662	t	\N	\N	\N	\N	\N	\N
85	448	1	LDMAJ_0298	scrypt:32768:8:1$Ir8k4EkZNEB5uK07$c8a207bb8ee78a1a105a5528eb917c864a616b907fa8d121b0dbcdcebf3b141235fbccb2c3d64b29fc974300ee0a653e686516f947959fe6be2097094f2b3a24	cybeeanngranada7@gmail.com	t	2026-09-24 12:39:34.852243	t	\N	\N	\N	\N	\N	\N
86	385	1	LDMAJ_0235	scrypt:32768:8:1$v53LgvC29FqeWf6F$97496cdf09e65046c4076ed0598d703d24262b76888b5d830f83f2ca2b237276eefdcdf663d4f54318984f2629d3f077bea68692c11cffe0fb23d48c1ecc6618	edzner056@gmail.com	t	2026-09-24 12:40:04.933938	t	\N	\N	\N	\N	\N	\N
87	446	1	LDMAJ_0296	scrypt:32768:8:1$kJjLmZNCnFggNpGm$e37be1148ed86800705db535151dfcc5c51215a7d76cc84a98633bfcf4f49be434f3258b4b6b53fff3f01c89b85f7dc016a9fe7776fde4eb4cbfe66741bcf6b9	jullianajuanillo@gmail.com	t	2026-09-24 12:40:25.868525	t	\N	\N	\N	\N	\N	\N
88	460	1	LDMAJ_0310	scrypt:32768:8:1$O3sh8MQ4k5MnIOH4$13da37eb8a14e75ae0610d3abffbaee1ed637c114b829c6de60e3c50a493e38f4b3e93abde60fe507c143b12f6b490300de3b7120d29d590b17d57b608f3918c	maliticmaricel10@gmail.com	t	2026-09-24 12:40:46.744473	t	\N	\N	\N	\N	\N	\N
89	426	1	LDMAJ_0276	scrypt:32768:8:1$9Xfz51mpigKOWSeU$9ad3b6d86d48e83bb661133a5b0d6069c27b97fa553507e8420d210203cd7c3e382da5b1d931e1991e14fb208c1056e7d5109627eeca2979e00aa880adfe04b1	forpersonalusesonlyy@gmail.com	t	2026-09-24 12:41:11.83244	t	\N	\N	\N	\N	\N	\N
90	458	1	LDMAJ_0308	scrypt:32768:8:1$NcaPc78su8hRbnBn$a03606f1efc162bb417a8e1ecd36a7929041e93fbb6e3881cf5da045da2fd793e901851f6493c31400be38b77c6d530a2d9442358be8d9f455cedcabc1b8c003	sphjlynamryn@gmail.com	t	2026-09-24 12:41:36.971045	t	\N	\N	\N	\N	\N	\N
91	417	1	LDMAJ_0267	scrypt:32768:8:1$yUssrAvTkF3lYmuL$3b2126a1bcbe3655576bfbdc03ef676270cada4ce5fffb01f0e271b5ebd2fccf6a078df5d40af3372036270e6182fdd758d54d88552cd3c66ff5d8b362d27b92	cianmercurio15@gmail.com	t	2026-09-24 12:42:37.953073	t	\N	\N	\N	\N	\N	\N
92	462	1	LDMAJ_0312	scrypt:32768:8:1$qgSCoHJ6feQdL7er$2089d3ac6ffbc5ca12ffd77988c7675c91bdd80aa9dde57d095e822a92a2b6a5ea7cf81879a43f3c9c5d73b64f1df73262ef6f7753656477263ed8dc551326f8	mercuriojewel3@gmail.com	t	2026-09-24 12:42:52.031234	t	\N	\N	\N	\N	\N	\N
93	414	1	LDMAJ_0264	scrypt:32768:8:1$cCY4ULzdqA0IiYdk$b1285062da4f382b8a24a7767e4d784a3d237f4d782c4aedf5bb3a474e3475fee275f572cf683b044f7d0e9171099a5c531cc989093569bfbd3a23f15dc90ad6	mercuriojm200@gmail.com	t	2026-09-24 12:43:08.405223	t	\N	\N	\N	\N	\N	\N
94	405	1	LDMAJ_0255	scrypt:32768:8:1$tNPdb5zw4beRT3Oi$c5a505d830fc7860b75cbe8b175930ce99a8c50cc6ebfd13a13c30beeb9550c37fd05b9c6a8da7f7bc21f968b5e1b24426f2abb0dd3c627c25831d36ae3df38a	khian@gmail.com	t	2026-09-24 12:43:38.835861	t	\N	\N	\N	\N	\N	\N
95	464	1	LDMAJ_0314	scrypt:32768:8:1$IrrE95OgB0r5cA0y$03b3e9f78915bb7e608ac6904a50b80956de53d1c7f88203d511edf3094072107a5355f1d06edf0d487110cfffb360e54609545e5948a289a39179aa75fb2a1d	nedicalyssa@gmail.com	t	2026-09-24 12:44:05.456361	t	\N	\N	\N	\N	\N	\N
96	423	1	LDMAJ_0273	scrypt:32768:8:1$D3o9LMa5jJsEBrxz$c316df0a9ec448af5b91f349b6baa881cc40ed341ab5b2dbc7f1b03e15ae866f1560512bde938ff32d8cf39410683cf63e182b4d830609ea5f903aca8eac748d	aeonperalta451@gmail.com	t	2026-09-24 12:44:36.590687	t	\N	\N	\N	\N	\N	\N
97	394	1	LDMAJ_0244	scrypt:32768:8:1$JUweR6x6G7gy0Xoz$4eec0742ff9021b6e6588a501bb0d45f3ad4d3048415198aeeeb99d60390dc4ea2f862fd5985c0e2af5da09fef4d30a0f3f4e53713a48c6efeaafe5b3ed73776	queianperez20@gmail.com	t	2026-09-24 12:44:53.79749	t	\N	\N	\N	\N	\N	\N
98	425	1	LDMAJ_0275	scrypt:32768:8:1$18115M8UVHN3avtf$33e7fdc7a85e2b2a7524feeed1fe41faa3bd6f53dead09093d75140436683fb83f379bcef6e12d9537acc2d5a7e8b28f18e058bc1a884b202d522257c8075200	noobhehe761@gmail.com	t	2026-09-24 12:45:26.821528	t	\N	\N	\N	\N	\N	\N
99	421	1	LDMAJ_0271	scrypt:32768:8:1$WwLEe6vfv1T5zQWy$5839ce199876a8604cf1aaa9b08de9a56bc9e3ae33bc75e0c66c3f8c699332bbd0763162d754be35f5646abaaa06bf908964fd89bf74571151b7ac47369a7c81	ronabiodenzel6@gmail.com	t	2026-09-24 12:45:55.208564	t	\N	\N	\N	\N	\N	\N
100	418	1	LDMAJ_0268	scrypt:32768:8:1$O0CFpNxFmvU3d6LP$98a6f86428865c63a054a46fa9e11214128ba87703a39fb81394ed1773113f97e8f3909e7b3b963404391065ac2997ab0499af5763c17f4233285988a6cca9b1	kerrphilipr@gmail.com	t	2026-09-24 12:46:11.9643	t	\N	\N	\N	\N	\N	\N
101	420	1	LDMAJ_0270	scrypt:32768:8:1$kMTtd0evV7rBv73r$29386d8225291fbf2a37d2e50b88895f3d47eb2542ef988601dfc63d76860d8e7b24d828c6815661a8003ac36f1adaef9380dd5a38a7b46cc4d5afb04f7d02c4	rondolajayar9@gmail.com	t	2026-09-24 12:46:44.097675	t	\N	\N	\N	\N	\N	\N
102	416	1	LDMAJ_0266	scrypt:32768:8:1$QzyS5MmGUXSDKcss$fa54f82b386503c71807c5f1fa69a5e902756bd78224ad3faf28d32a17e6ceeec0fbe6b7e2b2b00f0ab5914e05b282725ed6199dcb93c682785aba7a054142bc	johnpaulsanvictores143@gmail.com	t	2026-09-24 12:47:04.461874	t	\N	\N	\N	\N	\N	\N
103	469	1	LDMAJ_0319	scrypt:32768:8:1$sAt3hVaYIwkoZ48u$d2c850524691a9465d6d62b5d0fbfc4df0dfc75dbae1ebb4deeee54b0c988eaa226fcbcb1d49db08724f94225c2f8b556d794cd6a270cf3b4e28f36492592d65	vhiertuazon@gmail.com	t	2026-09-24 12:47:28.414538	t	\N	\N	\N	\N	\N	\N
104	407	1	LDMAJ_0257	scrypt:32768:8:1$1H4mMZxKUYTXket9$785f4cb1620de35e72ae516c0654caf467987a6d5a8d0dd2e5700df6c06b1f661bce1e4d9c40895ff8d469c262a47308bf3439c7d2aa539a4f6f3c6772e11c11	villanuevaeuricojoshc@gmail.com	t	2026-09-24 12:47:50.1109	t	\N	\N	\N	\N	\N	\N
105	167	1	LDMAJ_0017	scrypt:32768:8:1$1dxocS2RYKiYZRi3$297faa9b36cfe7ddacb5d6a116ad35e36064261f80bfeb9d7e00bde84fa9140ff00d4bb0b93f2da9ee65d04815b9c3040408b3a824039f21fe7a99415cd865aa	adorarosales124@gmail.com	t	2026-09-24 12:49:57.447134	t	\N	\N	\N	\N	\N	\N
106	270	1	LDMAJ_0120	scrypt:32768:8:1$yVxD368x5Em4LDwy$facf1741bdcc5b70d7d9871ec10015dfb87484f1ce584591df4a64b228f1767835a171627982ddf919b42270f03e3679d21a80d6115f9b07decd2936e0a2e0a7	dollyrubian2@gmail.com	t	2026-09-24 12:50:07.750546	t	\N	\N	\N	\N	\N	\N
107	155	1	LDMAJ_0005	scrypt:32768:8:1$l7HrovfUQCf8ADsb$7a9101005f49685683bb0e558430d269bd9a7dc09a02128dc3f9044c0f30e640202463ffeb0fa7c963d5c4266148a30f28d729fdf59e93b14462bfb89191644c	sioballiah0@gmail.com	t	2026-09-24 12:50:23.830116	t	\N	\N	\N	\N	\N	\N
108	255	1	LDMAJ_0105	scrypt:32768:8:1$LFswlUiMzhsvNFqj$8ca37d04cbdee5ea0cf8ed96e56d9893ddddb8f9813db8b9524ae1f011e8892b602e03cd543d03efb22deb0992258efd942f4f35387337b636cecfd0ae248295	angeliqueysha10@gmail.com	t	2026-09-24 12:51:02.812514	t	\N	\N	\N	\N	\N	\N
110	164	1	LDMAJ_0014	scrypt:32768:8:1$WEpjUX3isZrt5YYF$7a7dcefb55d73b16d33da06cfa6aac05f7000e03759ac9787dbddd71e206de9727d40ddf4c9110f769087a8098dcb41e9f21589a775a65ad9fe0a9804aa0f39f	jazzcerez@gmail.com	t	2026-09-24 12:52:45.275789	t	\N	\N	\N	\N	\N	\N
112	172	1	LDMAJ_0022	scrypt:32768:8:1$lsC2SYgROOiT4JkR$1935900b49ce3d306aa345a9d4cf0fdce7aace5fb713b86d0fb7a1cd66ca089d40947f6059f868a3b489a17a6ffc7ea73b4ad4b826eea61571e7d01ecb7d638d	rodleeisle10@gmail.com	t	2026-09-24 12:53:14.485993	t	\N	\N	\N	\N	\N	\N
113	273	1	LDMAJ_0123	scrypt:32768:8:1$iAmNc4lkPAkIbwPH$424d6ece939255ef38c1eb9c5017c9d8e21c0aff7eabcf14e96daddc673b90733c033fd802cd9185ab6203a10fe4e01e1d9f5c1daef201fc2ec008b994adca35	bert47004@gmail.com	t	2026-09-24 12:53:29.417389	t	\N	\N	\N	\N	\N	\N
109	177	1	LDMAJ_0027	scrypt:32768:8:1$laHZ2ubKvz1BrldZ$514cb1bfeb45b197fab257d9e3304dc2e5912bbbb0c65071d72a120719f4df50868c62d65a99b89d0c837961394a070446e46fc150ab2d8f0dbe000b1496b409	villaneraailamarie2@gmail.com	t	2026-09-24 12:51:12.369806	f	\N	\N	\N	\N	\N	\N
114	277	1	LDMAJ_0127	scrypt:32768:8:1$ciaCHJzD18MpccRl$2c77992599f547cfe2f8eb49e4a0eb8b0bda79dc6e3c0d61a0327347b577cc43b6f971fabe3e35d7c5d20ae9dd7db76e31bbbbd7150181bea269a61987deb6fc	esquillojadeen@gmail.com	t	2026-09-24 12:53:44.874224	t	\N	\N	\N	\N	\N	\N
115	262	1	LDMAJ_0112	scrypt:32768:8:1$dj5VllhgIlhZPOuk$492b72d7e4bbcf6afdee7f60557467060b169ff72396c08c3ce14793e7fd2d7ec8ce27f971d1abca152f643f9b6aa84d80020c870ef75864680acd6c41ccbbd5	grencioalthea@gmail.com	t	2026-09-24 12:53:58.936597	t	\N	\N	\N	\N	\N	\N
116	237	1	LDMAJ_0087	scrypt:32768:8:1$JLkIN7eT4wc6lVuq$3f7d37dd90a6673c4b76b02291b4db8b22793b8b5f04cad9f1a5c46a39c93fce5560b4de58ab32e26cf577f18e438bdc1a3da667d5644ee5a26b62e86f5ff420	janwellpontiveros@gmail.com	t	2026-09-24 12:54:15.94962	t	\N	\N	\N	\N	\N	\N
111	161	1	LDMAJ_0011	scrypt:32768:8:1$OWoKftdhBsRoBHTS$a1c039ce7b6b572180a6778c951a0898a16068e0efdb0555e63b018c44af903329bbbb02b6ba8525d21b5c389b28fc87f3b7d549545719cd446759232fabea43	ninaconejares@gmail.com	t	2026-09-24 12:53:00.374344	f	\N	\N	\N	\N	\N	\N
117	254	1	LDMAJ_0104	scrypt:32768:8:1$wdjhdSc3fzpiKPqv$9a14def2732d72e367861c193ea8889c66935a3ca033039952ab1939e3bb866ef334fc0e6ae9117fd2dfca530968f1287a1e27831f92623a1e8f92e42e886def	reyeseijifaye@gmail.com	t	2026-09-24 13:15:42.5701	t	\N	\N	\N	\N	\N	\N
118	261	1	LDMAJ_0111	scrypt:32768:8:1$SktU6vnwR2C5d13Y$c5f19babe0adb8c5b3a7f8c9d1386a9b884a4430446275a8b6b5c1b5eb72f8f2502200ce66080a00061bf9b0e4b335168a24cc143ddc555222ae574908c192b6	romerojai38@gmail.com	t	2026-09-24 13:15:57.499425	t	\N	\N	\N	\N	\N	\N
119	196	1	LDMAJ_0046	scrypt:32768:8:1$HpEOpotc87TekQsR$508bf23250bc910e0c40f2923f48b2d0ca90a004a2314692ffd8950970c75a559090c28a3c95e76b4f22cc3fb97d1990b3ec5c5bd11054d91deaa809be9d727f	vhanarubiales3@gmail.com	t	2026-09-24 13:16:16.84713	t	\N	\N	\N	\N	\N	\N
120	258	1	LDMAJ_0108	scrypt:32768:8:1$q3qB5N6baipoYsgx$602a6699c6f6bef8a35faeff4a1d4a408bc728a4b412b8163e4177310c1e0926aba8c0b6c38a87ac1333d69f7861ebf60af60b3dac56e1820a85fa779247aed2	monatanajlyn14@gmail.com	t	2026-09-24 13:16:36.172333	t	\N	\N	\N	\N	\N	\N
121	203	1	LDMAJ_0053	scrypt:32768:8:1$HbSZBNVNhoRNLSYU$b12d67427302d53d07707c9b188eb378b04aa1347c4f9440cbf5d6fa1e02ce8feccf492865902b45e852fcd7113cbd7e93ce1980e0c1f9fcba002519189ec4df	guillanaraza@gmail.com	t	2026-09-24 13:16:55.633778	t	\N	\N	\N	\N	\N	\N
122	290	1	LDMAJ_0140	scrypt:32768:8:1$O5FsEJGQy6b3buEE$30caf80025d1fd1654ca135cccd5732e4065da6ed9606f95d01caae98145c8b395b893e2c00e8aaff593f1c23abe3cc54e8389bc8b1dcae2d883eae421b0f3de	angelpasawa3@gmail.com	t	2026-09-24 13:17:11.218202	t	\N	\N	\N	\N	\N	\N
124	309	1	LDMAJ_0159	scrypt:32768:8:1$buVWSq5y6LoAEuLB$078e16bf06b7f1f9e3c41e1ebb38b691f26784b8c174c671e9bf2cc8990257dfba5e109b9494587ceb1afc6c8ad2cd842d4faa4395f4fd4d159b05067c36d75a	charisseromero90@gmail.com	t	2026-09-24 13:17:38.97941	t	\N	\N	\N	\N	\N	\N
126	211	1	LDMAJ_0061	scrypt:32768:8:1$q7Ld9NiVsj09TszN$0407c4612f161d4b0146b9b969936b30ba16626133a40cf2efb5751b1435bc3a7c5efbd2c971964e7419a7e5e50c456b07a7e824b6e57746061e59ab39131423	ailejairus@gmail.com	t	2026-09-24 13:18:04.016415	t	\N	\N	\N	\N	\N	\N
127	291	1	LDMAJ_0141	scrypt:32768:8:1$m1GjhsZCyl5lWDKx$7a721dc9cdb42f380469110af6958954deb3dd89d5a713a9265ddad0e1b50acafc3278244f6bbdfd3b42342437a0dc1b5cf8ff6466fbe2a3df9a2b8ab4796d29	marylilyrubian74@gmail.com	t	2026-09-24 13:18:18.405684	t	\N	\N	\N	\N	\N	\N
128	213	1	LDMAJ_0063	scrypt:32768:8:1$LhFwVqaUVVwSPjBy$5bf75b2e4150a40250c2f69782f5c3c655c45e4a5da0ddf55f57bbb0a00464e13726c075f9d3080eb27d01078aacceab0296addcb7a923bbee85c2f9a802db4d	johndhenver34@gmail.com	t	2026-09-24 13:18:37.127186	t	\N	\N	\N	\N	\N	\N
129	299	1	LDMAJ_0149	scrypt:32768:8:1$AHKZHc45BdKx9Ifk$ea808d6afdeaee3e212bab125d0d5f03e7630f4a9e0ee24f0b26eff3465bd81e8cd85cf09f0c7d4639593ebb0e85bf334b1a3a2017039edcd21ea2052bf1a71f	raphaelmike494@gmail.com	t	2026-09-24 13:19:04.492883	t	\N	\N	\N	\N	\N	\N
132	272	1	LDMAJ_0122	scrypt:32768:8:1$YykObFIqz8dv9Amk$de3c7d7aafc4ae9e47600710a1d15dfd3aae4615fedd47dd6ef4a0ed2703667fcbbe7902847324db099bdb87e741fce538df4caa466c5cc3ed8752d364e2950d	arceaiman143@gmail.com	t	2026-09-24 13:19:49.679176	t	\N	\N	\N	\N	\N	\N
133	305	1	LDMAJ_0155	scrypt:32768:8:1$CS7h5CNo7JG2OLJT$65c01a2790fe9719308d127a0feaffbaaeb0b949e3c63575c167e83ea4b42445ffef38b92481a5eb1959f8dfcd22bebe2c067fcec6dcf68013369a04d42ed2d0	phionajaneguera@gmail.com	t	2026-09-24 13:20:02.442321	t	\N	\N	\N	\N	\N	\N
134	199	1	LDMAJ_0049	scrypt:32768:8:1$HX4Xn730guGiTMPS$041ccef3900d52ab8bea3caca66ff884d43e11c2968388aaf9c2431b93208f3d54f26b05913fe432f30ab0ca287f8a3ac8716c079ba9ad259253c01c13efdff0	cjayguiruela06262009@gmail.com	t	2026-09-24 13:20:17.935167	t	\N	\N	\N	\N	\N	\N
135	300	1	LDMAJ_0150	scrypt:32768:8:1$ibnJs5jCb1u3FEMB$3da7912700895b03a9d54a24cc0c4180c1295eab70477f2210bfa990ec829b8da8547603f88916218b8b9173ac7d1ad4d518b5a62437b1563c4495727396402b	intaljames273@gmail.com	t	2026-09-24 13:20:40.822271	t	\N	\N	\N	\N	\N	\N
136	296	1	LDMAJ_0146	scrypt:32768:8:1$zCSmub5aDDd3qjH9$d0baf9ecaef8555ddf1ec46b3eec242cc582d9a36101f38af4755580fecf8b4f245a56bec7c2ebc50f76c32ae3d3f68c3688677e2f73d1e2e5139fb76afb05cd	latonerojomel@gmail.com	t	2026-09-24 13:20:59.978761	t	\N	\N	\N	\N	\N	\N
130	218	1	LDMAJ_0068	scrypt:32768:8:1$agxueWws0peg1Xgt$69304aeb072a759293efee853a195dc36d243f8b3a6c884c029cc0f996f9bc1bfe98f4308e87c98e2aec72f68276478c07bdf2cc9d2d9e654fc1eda914bfc5b0	tanesjanadrian@gmail.com	t	2026-09-24 13:19:18.488233	f	\N	\N	\N	\N	\N	\N
137	244	1	LDMAJ_0094	scrypt:32768:8:1$G1ln5nGueA54zrnq$6066543a60b4d17481f1f3b6a58581003ecfa831c2b3b2580ccaeb89883ae3e5a6b6f4d5705633f4a5d6ab12ee2e24fdf0fb05a9490dab2b11928201de5ff2cf	msherwin940@gmail.com	t	2026-09-24 13:21:15.676811	t	\N	\N	\N	\N	\N	\N
138	241	1	LDMAJ_0091	scrypt:32768:8:1$kibDCK6GJfC0BIkE$5d4e018d521a7f6b8e1e7b1e645c966e8506427e66f7e303a0af0c5e035a163d23403c0bb61ec3711d9dc40e924d077caa1ca7d14bed69c69dd56810d0d683bf	mercuriolanz77@gmail.com	t	2026-09-24 13:21:29.079097	t	\N	\N	\N	\N	\N	\N
139	236	1	LDMAJ_0086	scrypt:32768:8:1$tVjPaLOyctggNKxE$1ce1e2892da4d4587d25bf4139b9da851d5b973d34a3824eb64693416523abdf808980c98bd1c5d1f023d7b118565894b4bab40254b38d2ccfc659b219118456	wendellmercurio1@gmail.com	t	2026-09-24 13:21:50.078606	t	\N	\N	\N	\N	\N	\N
140	224	1	LDMAJ_0074	scrypt:32768:8:1$qtKSzjqdriD2LrzJ$684dec8915f7bd63fe3d79f18f28a86765adc512c9a2e3b50cde63aa25a521f666d959864b199f448adc4b6e3d4c0742456dab64af70076219ef0ab0e6b75c78	millenaalexandra2@gmail.com	t	2026-09-24 13:22:05.314074	t	\N	\N	\N	\N	\N	\N
131	207	1	LDMAJ_0057	scrypt:32768:8:1$UPseZ3y9TR4VGuun$2337ef493ab7e1721a3a8cdb5fe71c9cdd594f32593f3dd97d214fce81bb97ec03061a8f52d5929ac7dfee1e3d800087e23e4335120261f754b8a3a7523087eb	khaelmiguel.trovela@gmail.com	t	2026-09-24 13:19:33.749762	f	\N	\N	\N	\N	\N	\N
141	248	1	LDMAJ_0098	scrypt:32768:8:1$s9UTWApPfwlWgJ2F$f0e282499f86319fb4974e3f54467668c0cab464f82793ffb333fedda3f2c1c321b10be28ec68c15c5e50800c3f55493e5a29f88b1ed0dc170d36ae7aa1f6de1	markdavidmontemor586@gmail.com	t	2026-09-24 13:22:20.387928	t	\N	\N	\N	\N	\N	\N
142	230	1	LDMAJ_0080	scrypt:32768:8:1$XwIsfaMZxNOuKFQT$3edbe0d8128d7576f04fd79505c2c0db0ce992755e5864e879c8afaa6f3dde84d648cbbd36a921e3f5787ecb25bc5fe826c413a7b71c675bdc4cee2b3b8bb1d5	noveloteya@gmail.com	t	2026-09-24 13:22:39.663835	t	\N	\N	\N	\N	\N	\N
123	226	1	LDMAJ_0076	scrypt:32768:8:1$7spedjavXcH7Ykev$f5a6deb28d105b93067a48b7ea250816f7d46cb11613a5e2b13d78dfda33c1b10564c043ee82b60e90d01d6353147a8ba5ede1efe5fbea7d36cf06bfccb3d8e6	resquiburnok@gmail.com	t	2026-09-24 13:17:24.402882	f	\N	\N	\N	\N	\N	\N
143	298	1	LDMAJ_0148	scrypt:32768:8:1$jnx0OimfDHTFQaIw$e718ece4dbd83d9f431e01822fe82f1e9fe48f7d22f49f217f7d0f6fdb6a0e610f48c29e5dda82f06e510409e7976bf5e61ff8760e1d568b2aa0a322531f27e2	shedricbc@gmail.com	t	2026-09-24 13:22:58.194233	t	\N	\N	\N	\N	\N	\N
144	301	1	LDMAJ_0151	scrypt:32768:8:1$UKygKf8R1nJn1EpD$c81a1d99d68e08320ca017e1bf92f68be53802f8e20a19f99ae96fd28409e1f62042c630b60c0aef55171c5333730ec272cdc2d1b41e73c8dcbad89d7a6a6b25	estacajohaira@gmail.com	t	2026-09-24 13:23:13.082531	t	\N	\N	\N	\N	\N	\N
145	245	1	LDMAJ_0095	scrypt:32768:8:1$RHqntNjp8JRO5iqn$f3c7ea1797f2cb4691822bc2896412590defab324c5aabdfd3cea748adc2a50bdd176dde3f4b27d8a1adca3dd324f9dba24ff860fd0cb54ae65fd08e22deb4ed	kylacolignecarpio@gmail.com	t	2026-09-24 13:23:36.146926	t	\N	\N	\N	\N	\N	\N
147	310	1	LDMAJ_0160	scrypt:32768:8:1$ugEuvwBGAzVVNgEQ$f7945384a819f0230aaeffa0f6f088ceba2d53ce12c1b9790ac16884c1df415dade86db67eaa1c0d7d905b7b6e58996089fe2fb806dd34b3d5444b22ce08870c	jasminecordial92@gmail.com	t	2026-09-24 13:24:08.938737	t	\N	\N	\N	\N	\N	\N
148	191	1	LDMAJ_0041	scrypt:32768:8:1$hBbt1RhtIS4icEYU$6e6952e496eda16e9e11bb715e7d494e0b26fa72ee1ae7ee19b1bccf61f16931bc72f4e51ba1382081b6e19e5191a9f3d195e8994cced0efb6d06bdcea021685	corteznash10@gmail.com	t	2026-09-24 13:24:26.730776	t	\N	\N	\N	\N	\N	\N
149	303	1	LDMAJ_0153	scrypt:32768:8:1$jZUplRNpTd41LSBZ$99e97d1cfacb265691cb6a15d0baa7beab3ae2f92a872e21980a3842f172b0b4e215da95016f5ae0a49998a11d5595b7cb62f99854da276d6f1cbc1ea1e9992e	shanweinsd@gmail.com	t	2026-09-24 13:24:43.652251	t	\N	\N	\N	\N	\N	\N
150	294	1	LDMAJ_0144	scrypt:32768:8:1$YGMj9dc3YoaHwEBv$f0b573bc76ed9c7d7e9b2a9b6f6a36b8aeab9516d2c69880f92f12a2c6a3aa1e80bfc17b6c53c7e2b92e73865caf0f1a11ccfda7f4eb058c9ac6eda4c83a7271	rexd6466@gmail.com	t	2026-09-24 13:25:05.003665	t	\N	\N	\N	\N	\N	\N
151	293	1	LDMAJ_0143	scrypt:32768:8:1$sfzA4TVF3hZIctdS$75ab68448f0a94effd8d9ce7d30e0295808c93e33bfe2432eaec57507bb556d4532823c9d39ece53954674a60cf4626ea9252e361853abfbd96c5e1aae2f5c70	joannadelrey53029@gmail.com	t	2026-09-24 13:25:21.315664	t	\N	\N	\N	\N	\N	\N
152	292	1	LDMAJ_0142	scrypt:32768:8:1$Jy7xPMKLCRq5EFUj$b5145eefc65bc2ee9a0688256af6e2d9d85fbfe75a50b4c94e61c8ba710e10f3193331ec838e91577b8c0b36b47a1e1362153d1516ff41f9f035e47a451b6643	norissa14dorado@gmail.com	t	2026-09-24 13:25:39.359264	t	\N	\N	\N	\N	\N	\N
155	267	1	LDMAJ_0117	scrypt:32768:8:1$Q0eB2yHkmoW1zrBk$570409de50c5d36aaa91f4d5b3d68254982dff97732851fb441eda8a48c4f9c1d6a2edf94cb56d0bb2dd52a4cf7f4cb6f511988334262014fa4dc2ec1c972eae	espinaseandrea1@gmail.com	t	2026-09-24 13:28:28.282021	t	\N	\N	\N	\N	\N	\N
156	264	1	LDMAJ_0114	scrypt:32768:8:1$ASm3niVYVUnjt47p$83fdc8d2e049cd37d68d82817ba6389dfdf8afec26d7504ea3460a4ee6773a45507cf42d99141ccc642b1a9c6659c21f8e6361c48e9bd357fc8368448cf15637	ramilpontiga@gmail.com	t	2026-09-24 13:28:41.485088	t	\N	\N	\N	\N	\N	\N
157	208	1	LDMAJ_0058	scrypt:32768:8:1$NSLluCvuiqvn7FrU$99eade03ed13b8fb1612bb453bfb9ce00c003f6e624e932b2aa6de092420ca13ea1d3e17f1002fbcee3fe881ef5e8e4c154a2381e292661f6d4bf31755a4f40a	roselwendell05@gmail.com	t	2026-09-24 13:28:57.318483	t	\N	\N	\N	\N	\N	\N
158	279	1	LDMAJ_0129	scrypt:32768:8:1$p5jvqq2fS7e05CbM$8f79f83a979ca7f0101837b2ce114de63c03c941447ab3d36077a906ab27c15566b47dc89a2714f63f5178ce2e85048e69ced9b30c3c0f4969a91551c4d7bd55	esquillolieideen@gmail.com	t	2026-09-24 13:29:11.081916	t	\N	\N	\N	\N	\N	\N
159	282	1	LDMAJ_0132	scrypt:32768:8:1$7s3sfYlsdnqsgf4n$66f4d346be807595c140b265ffdf77bca6c1c858f98ba19c0ab8441597044a62f27b99cff63c7eb1925ea234524d63fa2e82fd1aa6051c11029904bf5bd5e772	kenmirano8@gmail.com	t	2026-09-24 13:29:24.13892	t	\N	\N	\N	\N	\N	\N
160	269	1	LDMAJ_0119	scrypt:32768:8:1$Bz9qmge1YknkG14n$94cdd3a5341e3ee20a238797094c4c93e31ebacb1c3c00817cd96a975fab78e62a0ce365bead9828582e87515e3f00c2d7cc3b533251669219583bb5c6dee06c	russelpalentinos0006@gmail.com	t	2026-09-24 13:29:42.267857	t	\N	\N	\N	\N	\N	\N
161	275	1	LDMAJ_0125	scrypt:32768:8:1$BQXKWCWbA8BG5O8c$2e9835e1949fc4bb7607b0861f06417f4da450d333f544480a6b068bff91031ef82a4bd87e363349a2ad0cfbdffbda4b0ba11918752b59390977f0017266a730	aaronvillarante40@gmail.com	t	2026-09-24 13:29:58.362604	t	\N	\N	\N	\N	\N	\N
162	190	1	LDMAJ_0040	scrypt:32768:8:1$pCifqzumiDjnQkeU$fae13c43e317a2889d2bae6d26a185c72c56cd2a19fe80898e6a5ba27762e0b9bf6e86740db539c5d5fdb9b206168e8f39c75ae9f98f92be5ddb66081b785581	aguilarayeshamae02@gmail.com	t	2026-09-24 13:30:15.837732	t	\N	\N	\N	\N	\N	\N
163	194	1	LDMAJ_0044	scrypt:32768:8:1$hMuSUic9tJg0OMxm$b056a6bdbe6c8755760bbaa4ea7828a12b204757ba8569d9b646f1fb764594103c920e6b8521f24b5f59b681c5647a1c6d3c967bc1300a227f4198df10fee8ff	naomearganosa0@gmail.com	t	2026-09-24 13:30:31.953616	t	\N	\N	\N	\N	\N	\N
164	302	1	LDMAJ_0152	scrypt:32768:8:1$a4RSEJRI6r0LPn1l$c7d8b0c2752335aef0d7f9d2ef77864fdf6055690f8e5c73e55a3d9702bc6027cc76ce771a9ab680f35eaf2374f8d06bdd28fb636741245d53e46152c7ca0dc3	earljohnarmenta@gmail.com	t	2026-09-24 13:30:47.532767	t	\N	\N	\N	\N	\N	\N
165	307	1	LDMAJ_0157	scrypt:32768:8:1$1RixEiTqbRrDKTsN$d3739a53c13b1f500bc98cf860a6905348eede3f01ffcbdc97c7c7b387f2a5eeb397055e3a2c16170d59e4129034c84b76458b1190de9f3b0c6507e98b6a27b1	azucenadaniella0@gmail.com	t	2026-09-24 13:31:07.922022	t	\N	\N	\N	\N	\N	\N
166	289	1	LDMAJ_0139	scrypt:32768:8:1$cv3DNruvKljS1dWx$27ac1262ba5e2e39a3961878b14f13a0b97235a845eea97f90e09eb7b78c38158ec231d802802f27eedb356468facc9c21ff54fb83dd2cfc86fc74c941effa48	corozaandrew24@gmail.com	t	2026-09-24 13:31:36.192356	t	\N	\N	\N	\N	\N	\N
168	306	1	LDMAJ_0156	scrypt:32768:8:1$drJu7UKmayDKTpCS$73d2fdec8f4ed439cb950b3f2957ef21878ec454bb8023de83de6dd1d099bdb160b54655af8ff71cbcf6711c3a0d8654fc5c12e8916754e240fee9ec9487cd41	eunicebarba07@gmail.com	t	2026-09-24 13:32:09.951845	t	\N	\N	\N	\N	\N	\N
169	297	1	LDMAJ_0147	scrypt:32768:8:1$8fYYmjk3dZVizGCb$2816e14e72ac7bac56a8974bb7e2c510802d2dfcea388e7f32e4734d3e93de1f8bf88bbe7b8a24ebaa2f10ff94d7fc98c6f444ea516a5308ce1fb4f9dc556c1c	montemorbianca1@gmail.com	t	2026-09-24 13:32:33.150694	t	\N	\N	\N	\N	\N	\N
146	215	1	LDMAJ_0065	scrypt:32768:8:1$nIRNovquCEgMTFf9$2bab9ff7fe94b982c7502e0b368fc8f96db7998ce63f802a78db285b9b4dd4e256f3ca08234d852647a3bfb446cca8543e4701542c7cd88c6905bf1590f5e1fe	coderajamila@gmail.com	t	2026-09-24 13:23:53.333464	f	\N	\N	\N	\N	\N	\N
154	205	1	LDMAJ_0055	scrypt:32768:8:1$65n2g8oQkQ9TLNBl$b4c51925a639d2f127472be615fbcc38b19d950ea8fdb3797e31ebbe77a850c1c2166c50079f3b471ae447f9d36f6a5579877cd22e3eba9c5bad9d4620cce4a7	rinalynchavez0913@gmail.com	t	2026-09-24 13:26:07.191721	f	\N	\N	\N	\N	\N	\N
125	250	1	LDMAJ_0100	scrypt:32768:8:1$lv8gvBUOmXQiDtrU$7b402e42c8b39f3bb003f0e6de9aedf4cf73032d9f47a507bb92157202b6206509142ccdae71ea286218465761364d673c0cb214d99f8137be4232d47ba5cc77	tyronrubian@gmail.com	t	2026-09-24 13:17:51.337155	f	\N	\N	\N	\N	\N	\N
153	189	1	LDMAJ_0039	scrypt:32768:8:1$IuxwVN5YwSutZNnH$1415b09b02a923a27c8f998433d7d1dd9217b7f6c26d608da9edf98be951f3e276f4777dedcd6fbbf8d40669f93d53c027d9b8d657f103a1f416357481c7090f	biticonmeryll@gmail.com	t	2026-09-24 13:25:54.656682	f	\N	\N	\N	\N	\N	\N
167	202	1	LDMAJ_0052	scrypt:32768:8:1$RIEcydYFcBVFLigz$23d716521c3af1d7291e93c417927f8f40a49ea1e1a75fb43aae830d9584b39419f7d1867d5a38c0829c2905285f7f5cb3808d96e2489705a2aea9b567d6e740	altheabala31@gmail.com	t	2026-09-24 13:31:53.530649	f	\N	\N	\N	\N	\N	\N
170	496	10	LDBB_0021	scrypt:32768:8:1$7MPZD84H2Y0ZVMWS$7ea567a45e320dc24647ab8dc612e214b12fbab6d923865c0f95dacbd1e59719657d9c5678e9116fd90c30c410b3ab4fcf6fbb0a3dca848ef271c570ab8e17d5	biticonmr2@gmail.com	t	2026-09-29 11:06:45.302896	t	\N	\N	\N	\N	\N	https://res.cloudinary.com/diwiuseil/image/upload/v1790680639/liceo_uploads/profiles/791102521_1707806513662980_5003035737954446297_n_1b3ef6.jpg
\.


--
-- Data for Name: student_notifications; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.student_notifications (id, student_id, title, message, link, is_read, created_at, notification_id) FROM stdin;
162	148	New Quiz: haha	A new quiz is now available: haha	/student/subject/156	f	2026-10-06 01:37:25.594197	\N
163	149	New Quiz: haha	A new quiz is now available: haha	/student/subject/156	f	2026-10-06 01:37:25.594197	\N
86	107	Uniform Pre-Order Submitted	Your uniform pre-order UO-20260818-17E3 is now For Ordering. You will be notified when it arrives onsite for payment and claim.	/student/reservations	t	2026-08-18 03:44:02.003577	\N
87	107	Uniform Ready for Claim	Your uniform order UO-20260818-17E3 is now onsite! Your bill has been activated. Please proceed to the cashier to pay and claim.	/student/reservations	t	2026-08-18 03:44:16.221278	\N
88	107	Uniform Pre-Order Submitted	Your uniform pre-order UO-20260818-FB7E is now For Ordering. You will be notified when it arrives onsite for payment and claim.	/student/reservations	t	2026-08-18 07:42:53.437256	\N
89	107	Uniform Ready for Claim	Your uniform order UO-20260818-FB7E is now onsite! Your bill has been activated. Please proceed to the cashier to pay and claim.	/student/reservations	t	2026-08-18 07:43:05.221026	\N
99	125	Uniform Pre-Order Submitted	Your uniform pre-order UO-20260819-98AA is now For Ordering. You will be notified when it arrives onsite for payment and claim.	/student/reservations	f	2026-08-19 08:02:03.849482	\N
100	125	Uniform Ready for Claim	Your uniform order UO-20260819-98AA is now onsite! Your bill has been activated. Please proceed to the cashier to pay and claim.	/student/reservations	f	2026-08-19 08:02:39.294153	\N
101	125	Uniform Pre-Order Submitted	Your uniform pre-order UO-20260819-D7A0 is now For Ordering. You will be notified when it arrives onsite for payment and claim.	/student/reservations	f	2026-08-19 08:03:14.566457	\N
102	125	Uniform Ready for Claim	Your uniform order UO-20260819-D7A0 is now onsite! Your bill has been activated. Please proceed to the cashier to pay and claim.	/student/reservations	f	2026-08-19 08:03:25.883399	\N
103	125	Uniform Pre-Order Submitted	Your uniform pre-order UO-20260819-41F1 is now For Ordering. You will be notified when it arrives onsite for payment and claim.	/student/reservations	f	2026-08-19 08:03:49.003701	\N
104	125	Uniform Ready for Claim	Your uniform order UO-20260819-41F1 is now onsite! Your bill has been activated. Please proceed to the cashier to pay and claim.	/student/reservations	f	2026-08-19 08:03:58.088593	\N
105	125	Uniform Pre-Order Submitted	Your uniform pre-order UO-20260819-1944 is now For Ordering. You will be notified when it arrives onsite for payment and claim.	/student/reservations	f	2026-08-19 08:07:43.398685	\N
106	125	Uniform Ready for Claim	Your uniform order UO-20260819-1944 is now onsite! Your bill has been activated. Please proceed to the cashier to pay and claim.	/student/reservations	f	2026-08-19 08:07:52.831631	\N
107	125	Uniform Pre-Order Submitted	Your uniform pre-order UO-20260819-EBEB is now For Ordering. You will be notified when it arrives onsite for payment and claim.	/student/reservations	f	2026-08-19 08:10:31.864928	\N
108	125	Uniform Ready for Claim	Your uniform order UO-20260819-EBEB is now onsite! Your bill has been activated. Please proceed to the cashier to pay and claim.	/student/reservations	f	2026-08-19 08:10:43.543893	\N
110	125	New Activity: Activity 1	Your teacher posted a new activity: Activity 1.	/student/activities/21	f	2026-08-19 11:38:12.331651	\N
91	107	New Announcement: Exhibit Tomorrow	Your teacher posted a new announcement.	/student/dashboard	t	2026-08-19 07:28:18.296096	\N
113	125	New Quiz: Quiz 2	A new quiz is now available: Quiz 2	/student/subject/22	f	2026-08-19 11:39:10.358584	\N
111	127	New Activity: Activity 1	Your teacher posted a new activity: Activity 1.	/student/activities/21	t	2026-08-19 11:38:12.331651	\N
114	127	New Quiz: Quiz 2	A new quiz is now available: Quiz 2	/student/subject/22	t	2026-08-19 11:39:10.358584	\N
115	127	Activity Graded	Your submission for 'Activity 1' has been graded.	/student/activities/21	t	2026-08-19 11:43:18.823288	\N
90	107	Uniform Pre-Order Submitted	Your uniform pre-order UO-20260819-D1C4 is now For Ordering. You will be notified when it arrives onsite for payment and claim.	/student/reservations	t	2026-08-19 06:42:30.109142	\N
92	107	New Activity: Exhibit	Your teacher posted a new activity: Exhibit.	/student/activities/20	t	2026-08-19 07:29:48.096671	\N
93	107	New Activity: Exhibit	Your teacher posted a new activity: Exhibit.	/student/activities/20	t	2026-08-19 07:30:47.951456	\N
94	107	New Quiz: Exhibit Quiz	A new quiz is now available: Exhibit Quiz	/student/subject/22	t	2026-08-19 07:33:29.805945	\N
95	107	New Exam: Exhibit	A new exam is now available: Exhibit	/student/exams	t	2026-08-19 07:37:03.447132	\N
96	107	Uniform Pre-Order Submitted	Your uniform pre-order UO-20260819-B224 is now For Ordering. You will be notified when it arrives onsite for payment and claim.	/student/reservations	t	2026-08-19 07:53:26.63832	\N
97	107	Uniform Pre-Order Submitted	Your uniform pre-order UO-20260819-2B6E is now For Ordering. You will be notified when it arrives onsite for payment and claim.	/student/reservations	t	2026-08-19 07:57:06.259532	\N
98	107	Uniform Ready for Claim	Your uniform order UO-20260819-2B6E is now onsite! Your bill has been activated. Please proceed to the cashier to pay and claim.	/student/reservations	t	2026-08-19 07:57:14.252578	\N
112	107	New Quiz: Quiz 2	A new quiz is now available: Quiz 2	/student/subject/22	t	2026-08-19 11:39:10.358584	\N
117	125	New Quiz: PAQUIZZZZZZZZ	A new quiz is now available: PAQUIZZZZZZZZ	/student/subject/22	f	2026-08-20 08:03:03.382174	\N
118	127	New Quiz: PAQUIZZZZZZZZ	A new quiz is now available: PAQUIZZZZZZZZ	/student/subject/22	f	2026-08-20 08:03:03.382174	\N
116	107	New Quiz: PAQUIZZZZZZZZ	A new quiz is now available: PAQUIZZZZZZZZ	/student/subject/22	t	2026-08-20 08:03:03.382174	\N
120	125	New Quiz: Quiz	A new quiz is now available: Quiz	/student/subject/22	f	2026-08-21 04:30:17.048928	\N
121	127	New Quiz: Quiz	A new quiz is now available: Quiz	/student/subject/22	f	2026-08-21 04:30:17.048928	\N
119	107	New Quiz: Quiz	A new quiz is now available: Quiz	/student/subject/22	t	2026-08-21 04:30:17.048928	\N
109	107	New Activity: Activity 1	Your teacher posted a new activity: Activity 1.	/student/activities/21	t	2026-08-19 11:38:12.331651	\N
122	107	Uniform Pre-Order Submitted	Your uniform pre-order UO-20260822-E828 is now For Ordering. You will be notified when it arrives onsite for payment and claim.	/student/reservations	t	2026-08-22 04:38:02.990823	\N
123	107	Uniform Pre-Order Submitted	Your uniform pre-order UO-20260823-50E5 is now For Ordering. You will be notified when it arrives onsite for payment and claim.	/student/reservations	t	2026-08-23 14:40:38.085863	\N
124	107	Activity Graded	Your submission for 'Activity 1' has been graded.	/student/activities/21	t	2026-08-27 04:47:11.471177	\N
125	107	Uniform Pre-Order Submitted	Your uniform pre-order UO-20260827-2BA7 is now For Ordering. You will be notified when it arrives onsite for payment and claim.	/student/reservations	t	2026-08-27 04:48:22.907048	\N
135	130	Uniform Pre-Order Submitted	Your uniform pre-order UO-20260831-75D9 is now For Ordering. You will be notified when it arrives onsite for payment and claim.	/student/reservations	f	2026-08-31 08:57:20.562566	\N
131	130	New Quiz: Exhibit 2026	A new quiz is now available: Exhibit 2026	/student/subject/33	f	2026-08-31 08:50:31.575079	\N
130	129	New Quiz: Exhibit 2026	A new quiz is now available: Exhibit 2026	/student/subject/33	t	2026-08-31 08:50:31.575079	\N
132	130	Uniform Pre-Order Submitted	Your uniform pre-order UO-20260831-43F0 is now For Ordering. You will be notified when it arrives onsite for payment and claim.	/student/reservations	f	2026-08-31 08:56:21.221897	\N
133	130	Uniform Ready for Claim	Your uniform order UO-20260831-43F0 is now onsite! Your bill has been activated. Please proceed to the cashier to pay and claim.	/student/reservations	f	2026-08-31 08:56:27.758063	\N
129	128	New Quiz: Exhibit 2026	A new quiz is now available: Exhibit 2026	/student/subject/33	t	2026-08-31 08:50:31.575079	\N
134	129	Uniform Pre-Order Submitted	Your uniform pre-order UO-20260831-7EA1 is now For Ordering. You will be notified when it arrives onsite for payment and claim.	/student/reservations	t	2026-08-31 08:56:47.662265	\N
136	129	Uniform Pre-Order Submitted	Your uniform pre-order UO-20260831-AC3E is now For Ordering. You will be notified when it arrives onsite for payment and claim.	/student/reservations	t	2026-08-31 09:03:08.988279	\N
137	129	Uniform Pre-Order Submitted	Your uniform pre-order UO-20260831-996A is now For Ordering. You will be notified when it arrives onsite for payment and claim.	/student/reservations	t	2026-08-31 09:12:08.379228	\N
138	129	Uniform Pre-Order Submitted	Your uniform pre-order UO-20260901-3EE5 is now For Ordering. You will be notified when it arrives onsite for payment and claim.	/student/reservations	f	2026-09-01 03:13:45.353944	\N
139	148	New Activity: Act 1	Your teacher posted a new activity: Act 1.	/student/activities/22	f	2026-09-22 07:23:51.855172	\N
142	149	New Quiz: Quiz 1	A new quiz is now available: Quiz 1	/student/subject/156	t	2026-09-22 07:28:12.715079	\N
140	149	New Activity: Act 1	Your teacher posted a new activity: Act 1.	/student/activities/22	t	2026-09-22 07:23:51.855172	\N
141	148	New Quiz: Quiz 1	A new quiz is now available: Quiz 1	/student/subject/156	f	2026-09-22 07:28:12.715079	\N
143	148	New Quiz: Quiz 1	A new quiz is now available: Quiz 1	/student/subject/156	f	2026-09-22 07:28:20.878408	\N
144	149	New Quiz: Quiz 1	A new quiz is now available: Quiz 1	/student/subject/156	t	2026-09-22 07:28:20.878408	\N
145	148	New Activity: Act 2	Your teacher posted a new activity: Act 2.	/student/activities/23	f	2026-09-22 07:57:17.77706	\N
148	148	New Exam: Exam	A new exam is now available: Exam	/student/exams	f	2026-09-22 08:01:57.294916	\N
146	149	New Activity: Act 2	Your teacher posted a new activity: Act 2.	/student/activities/23	t	2026-09-22 07:57:17.77706	\N
147	149	Activity Graded	Your submission for 'Act 1' has been graded.	/student/activities/22	t	2026-09-22 07:57:51.840699	\N
149	149	New Exam: Exam	A new exam is now available: Exam	/student/exams	t	2026-09-22 08:01:57.294916	\N
150	129	Uniform Ready for Claim	Your uniform order UO-20260901-3EE5 is now onsite! Your bill has been activated. Please proceed to the cashier to pay and claim.	/student/reservations	f	2026-09-22 08:08:40.705667	\N
151	148	New Quiz: Quiz 3	A new quiz is now available: Quiz 3	/student/subject/156	f	2026-09-23 11:37:44.250445	\N
152	149	New Quiz: Quiz 3	A new quiz is now available: Quiz 3	/student/subject/156	t	2026-09-23 11:37:44.250445	\N
153	148	New Quiz: Quiz 3	A new quiz is now available: Quiz 3	/student/subject/156	f	2026-09-23 12:48:37.732398	\N
154	149	New Quiz: Quiz 3	A new quiz is now available: Quiz 3	/student/subject/156	t	2026-09-23 12:48:37.732398	\N
155	129	Uniform Ready for Claim	Your uniform order UO-20260831-996A is now onsite! Your bill has been activated. Please proceed to the cashier to pay and claim.	/student/reservations	f	2026-09-29 11:23:19.992806	\N
156	148	New Activity: Act 3	Your teacher posted a new activity: Act 3.	/student/activities/25	f	2026-09-29 11:28:38.502826	\N
158	148	New Quiz: Quiz 3	A new quiz is now available: Quiz 3	/student/subject/156	f	2026-09-29 11:30:55.268052	\N
160	148	New Quiz: Quiz 3	A new quiz is now available: Quiz 3	/student/subject/156	f	2026-09-29 11:31:05.01849	\N
157	149	New Activity: Act 3	Your teacher posted a new activity: Act 3.	/student/activities/25	t	2026-09-29 11:28:38.502826	\N
159	149	New Quiz: Quiz 3	A new quiz is now available: Quiz 3	/student/subject/156	t	2026-09-29 11:30:55.268052	\N
161	149	New Quiz: Quiz 3	A new quiz is now available: Quiz 3	/student/subject/156	t	2026-09-29 11:31:05.01849	\N
\.


--
-- Data for Name: subjects; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.subjects (subject_id, name, units, deped_category, subject_type, track, pathway, prerequisite_subject_id) FROM stdin;
19	Mathematics	3	science_math	CORE	\N	\N	\N
21	English	3	language	CORE	\N	\N	\N
22	Filipino	3	language	CORE	\N	\N	\N
30	MATH	3	science_math	CORE	\N	\N	\N
33	ENGLISH	3	language	CORE	\N	\N	\N
34	FILIPINO	3	language	CORE	\N	\N	\N
35	SCIENCE	3	science_math	CORE	\N	\N	\N
175	Info & Comm. Tech.	3	language	CORE	\N	\N	\N
23	Religion	3	language	CORE	\N	\N	\N
124	21st Century Lit	3	language	CORE	\N	\N	\N
80	Info. & Comm. Tech.	3	skills	CORE	\N	\N	\N
92	Values Education	3	language	CORE	\N	\N	\N
20	Science	3	science_math	CORE	\N	\N	\N
120	Filipino sa Piling Larangan	3	language	CORE	\N	\N	\N
122	Intro to World Religions & Belief System	3	language	CORE	\N	\N	\N
127	Principles of Marketing	3	language	CORE	\N	\N	\N
121	Research in Daily Life 2	3	language	CORE	\N	\N	\N
50	ICT	3	skills	CORE	\N	\N	\N
60	Araling Panlipunan	3	language	CORE	\N	\N	\N
37	MAPEH	3	skills	CORE	\N	\N	\N
186	Contemporay Phil. Arts from the Religion	3	language	CORE	\N	\N	\N
126	Creative Nonfiction	3	skills	CORE	\N	\N	\N
65	E.P.P	3	science_math	CORE	\N	\N	\N
67	M.A.P.E.H	3	skills	CORE	\N	\N	\N
187	Entrepreneurship	3	language	CORE	\N	\N	\N
130	Business Ethics	3	science_math	CORE	\N	\N	\N
125	PEH	3	skills	CORE	\N	\N	\N
27	EPP	3	skills	CORE	\N	\N	\N
188	Immersion	3	language	CORE	\N	\N	\N
189	Research Subject	3	language	CORE	\N	\N	\N
51	Project PRIME	3	science_math	CORE	\N	\N	\N
28	TLE	3	skills	ELECTIVE	Academic	Science	\N
190	Hi	3	science_math	ELECTIVE	Academic	Math	158
59	Info. & Comm. Tech	3	language	CORE	\N	\N	\N
81	PROJECT PRIME	3	science_math	CORE	\N	\N	\N
144	hey	3	language	CORE	\N	\N	\N
99	Tech & Livelihood Educ.	3	skills	CORE	\N	\N	\N
18	GMRC	3	language	CORE	\N	\N	\N
150	General Mathematics	3	science_math	CORE	\N	\N	\N
151	General Science	3	science_math	CORE	\N	\N	\N
152	Effective Communication	3	language	CORE	\N	\N	\N
153	Life and Career Skills	3	language	CORE	\N	\N	\N
154	Mabisang Komunikasyon	3	language	CORE	\N	\N	\N
155	Pag-aaral ng Kasaysayan	3	language	CORE	\N	\N	\N
157	Pre-Calculus 1	3	science_math	ELECTIVE	\N	\N	\N
156	Advanced Mathematics 1	3	science_math	ELECTIVE	Academic	Math	\N
158	Advanced Mathematics 2	3	science_math	ELECTIVE	Academic	Math	156
159	Enggggg	3	language	CORE	\N	\N	\N
164	Info & Comm. Tech	3	skills	CORE	\N	\N	\N
49	Makabansa	3	language	CORE	\N	\N	\N
143	Project WISE (Writing Improvement and Skills Enhancement)	3	language	CORE	\N	\N	\N
43	H.G.P	3	language	CORE	\N	\N	\N
135	G.M.R.C	3	language	CORE	\N	\N	\N
179	math	3	science_math	CORE	\N	\N	\N
\.


--
-- Data for Name: swafo_discipline_log; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.swafo_discipline_log (log_id, enrollment_id, student_id, branch_id, logged_by, reported_by, incident_date, incident_type, offense_level, severity, description, action_taken, status, created_at, referred_to_swafo, referral_reason) FROM stdin;
1	490	\N	10	114	\N	2026-10-01	Late	\N	minor	Late Student		Pending	2026-10-01 02:36:52.081356	f	
\.


--
-- Data for Name: swafo_parent_conferences; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.swafo_parent_conferences (conference_id, branch_id, enrollment_id, discipline_log_id, scheduled_by, title, conference_date, conference_time, meeting_type, meeting_location, agenda, status, parent_notes, minutes_of_meeting, agreements, parent_acknowledged_at, created_at) FROM stdin;
1	10	489	\N	114	Guidance	2026-09-30	07:34 PM	in_person	https://meet.google.com/tud-xnzk-rzh?fbclid=IwY2xjawUoeWpleHRuA2FlbQIxMABwZG9mAWJyaWQRMUFQTnh6ZkdEZnQzSmlRVmtzcnRjBmFwcF9pZBAyMjIwMzkxNzg4MjAwODkyAAEeexH13Sp7bpbSbhqquMNOk4RZNUBc2lgwyQIgDrVRibr9CEmuLlX6GfvNQaA_aem_TA-1ZAJzkTzXrpGVoaFD4w		scheduled	\N	\N	\N	\N	2026-09-29 11:34:35.741621
\.


--
-- Data for Name: swafo_records; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.swafo_records (record_id, enrollment_id, student_id, family_members, health_info, education_history, summer_subjects, religion_info, vocation_info, general_info, status, teacher_notes, reviewed_by, reviewed_at, created_at, updated_at, submitted_at) FROM stdin;
\.


--
-- Data for Name: system_settings; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.system_settings (setting_key, setting_value, updated_at) FROM stdin;
break_times_config_10	{"DEFAULT": {"prayerStart": "06:45", "prayerEnd": "07:15", "recessStart": "09:15", "recessEnd": "09:30", "lunchStart": "12:30", "lunchEnd": "13:00", "dayBreaks": {}}}	2026-10-07 12:42:46.923739
liceo_break_times_config	{"DEFAULT": {"prayerStart": "06:45", "prayerEnd": "07:15", "recessStart": "09:15", "recessEnd": "09:30", "lunchStart": "12:30", "lunchEnd": "13:00", "dayBreaks": {}}}	2026-10-07 12:42:46.923739
maintenance_mode	off	2026-09-22 07:48:22.680871
break_times_config_1	{"DEFAULT": {"dayBreaks": {"Friday": {"recessEnd": "09:30", "recessStart": "09:15"}, "Thursday": {"recessEnd": "09:15", "recessStart": "08:15"}}, "lunchEnd": "12:00", "lunchStart": "11:30", "prayerEnd": "07:15", "prayerStart": "06:45", "recessEnd": "10:30", "recessStart": "10:15"}, "Grade 12-GAS": {"dayBreaks": {"Friday": {"recessEnd": "09:30", "recessStart": "09:15", "noLunch": true}, "Thursday": {"recessEnd": "09:15", "recessStart": "08:15", "noRecess": true}}, "lunchEnd": "12:00", "lunchStart": "11:30", "prayerEnd": "07:15", "prayerStart": "06:45", "recessEnd": "10:30", "recessStart": "10:15"}, "Grade 2": {"lunchEnd": "12:00", "lunchStart": "11:30", "prayerEnd": "07:15", "prayerStart": "06:45", "recessEnd": "09:05", "recessStart": "08:55"}, "Grade 4": {"lunchEnd": "12:00", "lunchStart": "11:30", "prayerEnd": "07:15", "prayerStart": "06:45", "recessEnd": "09:30", "recessStart": "09:15"}, "Grade 7": {"lunchEnd": "13:00", "lunchStart": "12:30", "prayerEnd": "07:15", "prayerStart": "06:45", "recessEnd": "10:30", "recessStart": "10:15"}, "Grade 9": {"lunchEnd": "13:00", "lunchStart": "12:30", "prayerEnd": "07:15", "prayerStart": "06:45", "recessEnd": "10:30", "recessStart": "10:15"}}	2026-10-03 13:11:07.069353
\.


--
-- Data for Name: teacher_announcements; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.teacher_announcements (announcement_id, teacher_user_id, branch_id, grade_level, title, body, created_at, year_id) FROM stdin;
5	86	4	Nursery:84	Exhibit Tomorrow	\N	2026-08-19 07:28:18.296096	10
\.


--
-- Data for Name: teacher_grade_levels; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.teacher_grade_levels (id, teacher_id, grade_level_id) FROM stdin;
\.


--
-- Data for Name: uniform_order_items; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.uniform_order_items (item_id, order_id, inventory_item_id, item_name, size_label, unit_price, quantity, line_total, created_at) FROM stdin;
7	7	1155	Pre-Elementary Boys Set	S	1020.00	1	1020.00	2026-08-18 03:44:02.003577
8	8	1155	Pre-Elementary Boys Set	XS	1000.00	1	1000.00	2026-08-18 07:42:53.437256
9	9	1155	Pre-Elementary Boys Set	XS	1000.00	1	1000.00	2026-08-19 06:42:30.109142
10	10	1155	Pre-Elementary Boys Set	S	930.00	1	930.00	2026-08-19 07:53:26.63832
11	11	1155	Pre-Elementary Boys Set	S	930.00	1	930.00	2026-08-19 07:57:06.259532
12	12	1155	Pre-Elementary Boys Set	S	930.00	1	930.00	2026-08-19 08:02:03.849482
13	13	1155	Pre-Elementary Boys Set	S	930.00	1	930.00	2026-08-19 08:03:14.566457
14	14	1155	Pre-Elementary Boys Set	XS	910.00	1	910.00	2026-08-19 08:03:49.003701
15	15	1155	Pre-Elementary Boys Set	XS	910.00	1	910.00	2026-08-19 08:07:43.398685
16	16	1155	Pre-Elementary Boys Set	XS	910.00	1	910.00	2026-08-19 08:10:31.864928
17	17	1155	Pre-Elementary Boys Set	XS	910.00	1	910.00	2026-08-22 04:38:02.990823
18	18	1228	Test	XS	31.00	1	31.00	2026-08-23 14:40:38.085863
19	19	1155	Pre-Elementary Boys Set	XS	910.00	1	910.00	2026-08-27 04:48:22.907048
20	20	1230	Nursery-Kinder Unifrom Set (Boy)	XS	1000.00	1	1000.00	2026-08-31 08:56:21.221897
21	21	1230	Nursery-Kinder Unifrom Set (Boy)	XS	1000.00	1	1000.00	2026-08-31 08:56:47.662265
22	22	1230	Nursery-Kinder Unifrom Set (Boy)	XS	1000.00	1	1000.00	2026-08-31 08:57:20.562566
23	23	1230	Nursery-Kinder Unifrom Set (Boy)	XXXL	1120.00	1	1120.00	2026-08-31 09:03:08.988279
24	24	1230	Nursery-Kinder Unifrom Set (Boy)	XS	1000.00	1	1000.00	2026-08-31 09:12:08.379228
25	25	1230	Nursery-Kinder Unifrom Set (Boy)	XS	1000.00	1	1000.00	2026-09-01 03:13:45.353944
26	26	1230	Nursery-Kinder Unifrom Set (Boy)	XS	1000.00	1	1000.00	2026-09-29 11:19:31.632971
27	27	1230	Nursery-Kinder Unifrom Set (Boy)	XS	1000.00	1	1000.00	2026-10-01 12:57:21.633468
\.


--
-- Data for Name: uniform_orders; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.uniform_orders (order_id, order_number, enrollment_id, student_user_id, branch_id, year_id, total_amount, payment_status, order_status, created_by_user_id, bill_id, created_at, onsite_arrived_at, claimed_at, claimed_by_user_id, updated_at) FROM stdin;
27	UO-20261001-15B9	137	\N	10	30	1000.00	Unpaid	For Ordering	113	\N	2026-10-01 12:57:21.633468	\N	\N	\N	2026-10-01 12:57:21.633468
7	UO-20260818-17E3	134	107	4	10	1020.00	Paid	Ready for Claim	107	12	2026-08-18 03:44:02.003577	2026-08-18 11:44:16.243703	\N	\N	2026-08-18 07:40:35.409722
8	UO-20260818-FB7E	134	107	4	10	1000.00	Paid	Ready for Claim	107	12	2026-08-18 07:42:53.437256	2026-08-18 15:43:05.244305	\N	\N	2026-08-18 07:43:23.977023
9	UO-20260819-D1C4	134	107	4	10	1000.00	Paid	For Ordering	107	\N	2026-08-19 06:42:30.109142	\N	\N	\N	2026-08-19 07:56:15.309049
10	UO-20260819-B224	134	107	4	10	930.00	Paid	For Ordering	107	\N	2026-08-19 07:53:26.63832	\N	\N	\N	2026-08-19 07:56:15.309049
11	UO-20260819-2B6E	134	107	4	10	930.00	Unpaid	Ready for Claim	107	12	2026-08-19 07:57:06.259532	2026-08-19 15:57:14.277782	\N	\N	2026-08-19 15:57:14.277782
12	UO-20260819-98AA	135	125	4	10	930.00	Paid	Ready for Claim	125	13	2026-08-19 08:02:03.849482	2026-08-19 16:02:39.316592	\N	\N	2026-08-19 08:02:54.331782
13	UO-20260819-D7A0	135	125	4	10	930.00	Paid	Ready for Claim	125	13	2026-08-19 08:03:14.566457	2026-08-19 16:03:25.90381	\N	\N	2026-08-19 08:07:20.136805
14	UO-20260819-41F1	135	125	4	10	910.00	Paid	Ready for Claim	125	13	2026-08-19 08:03:49.003701	2026-08-19 16:03:58.11024	\N	\N	2026-08-19 08:07:20.136805
15	UO-20260819-1944	135	125	4	10	910.00	Unpaid	Ready for Claim	125	13	2026-08-19 08:07:43.398685	2026-08-19 16:07:52.85153	\N	\N	2026-08-19 16:07:52.85153
16	UO-20260819-EBEB	135	125	4	10	910.00	Unpaid	Ready for Claim	122	13	2026-08-19 08:10:31.864928	2026-08-19 16:10:43.563895	\N	\N	2026-08-19 16:10:43.563895
17	UO-20260822-E828	134	107	4	10	910.00	Unpaid	For Ordering	107	\N	2026-08-22 04:38:02.990823	\N	\N	\N	2026-08-22 04:38:02.990823
18	UO-20260823-50E5	134	107	4	10	31.00	Unpaid	For Ordering	106	\N	2026-08-23 14:40:38.085863	\N	\N	\N	2026-08-23 14:40:38.085863
19	UO-20260827-2BA7	134	107	4	10	910.00	Unpaid	For Ordering	107	\N	2026-08-27 04:48:22.907048	\N	\N	\N	2026-08-27 04:48:22.907048
21	UO-20260831-7EA1	141	129	10	26	1000.00	Unpaid	For Ordering	129	\N	2026-08-31 08:56:47.662265	\N	\N	\N	2026-08-31 08:56:47.662265
20	UO-20260831-43F0	136	130	10	26	1000.00	Paid	Ready for Claim	130	14	2026-08-31 08:56:21.221897	2026-08-31 16:56:27.78465	\N	\N	2026-08-31 08:58:21.789644
22	UO-20260831-75D9	136	130	10	26	1000.00	Paid	For Ordering	130	\N	2026-08-31 08:57:20.562566	\N	\N	\N	2026-08-31 08:58:21.789644
23	UO-20260831-AC3E	141	129	10	26	1120.00	Unpaid	For Ordering	129	\N	2026-08-31 09:03:08.988279	\N	\N	\N	2026-08-31 09:03:08.988279
25	UO-20260901-3EE5	141	129	10	26	1000.00	Unpaid	Ready for Claim	129	15	2026-09-01 03:13:45.353944	2026-09-22 16:08:40.743647	\N	\N	2026-09-22 16:08:40.743647
26	UO-20260929-B41F	137	\N	10	30	1000.00	Unpaid	For Ordering	111	\N	2026-09-29 11:19:31.632971	\N	\N	\N	2026-09-29 11:19:31.632971
24	UO-20260831-996A	141	129	10	26	1000.00	Unpaid	Ready for Claim	129	15	2026-08-31 09:12:08.379228	2026-09-29 19:23:20.019749	\N	\N	2026-09-29 19:23:20.019749
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.users (user_id, branch_id, username, password, role, status, require_password_change, last_password_change, full_name, gender, grade_level, email, grade_level_id, enrollment_id, contact_number, dob, profile_image, last_login, teacher_type, specialization_subject, department, is_archived, first_name, middle_name, last_name, is_swafo, user_roles, is_dc) FROM stdin;
144	1	LDMAJ_Teacher_4	scrypt:32768:8:1$djRPDObro3R9Diqo$80324c76f18f9f43592c41b7d3e072729dcbc1c7c1e5cab1b7e4cf118d102aedef00ca5e80e71a5c6047fa71236e424b2b8d8c975783c9a023ba61d4076b5520	teacher	active	t	\N	Marilou Armenta Conejares	female	\N	marilouarmenta2@gmail.com	\N	\N	\N	\N	\N	\N	advisory	\N	\N	f	Marilou	Armenta	Conejares	f	["teacher"]	f
167	1	LDMAJ_0100	scrypt:32768:8:1$lv8gvBUOmXQiDtrU$7b402e42c8b39f3bb003f0e6de9aedf4cf73032d9f47a507bb92157202b6206509142ccdae71ea286218465761364d673c0cb214d99f8137be4232d47ba5cc77	student	active	f	2026-09-27 02:32:56.129019	\N	\N	\N	tyronrubian@gmail.com	\N	250	\N	\N	\N	\N	advisory	\N	\N	f	\N	\N	\N	f	["student"]	f
65	\N	superadmin	scrypt:32768:8:1$nCWvPNAJW1biuitd$6126e015fbe1fbcb8007a4d8ed272359d7283bd779bdb8d9c232f7a5990adbd598bc1f3741294aaae80bf232762e672cd10874fc83010082a86400200fb86ca9	super_admin	active	f	2026-09-10 04:18:57.780158	System Administrator	\N	\N	admin@liceo.edu.ph	\N	\N	\N	\N	\N	\N	advisory	\N	\N	f	System	\N	Administrator	f	["super_admin"]	f
161	1	LDMAJ_Teacher_12	scrypt:32768:8:1$2Gb5BFtROqSsYJOz$f74dd8034498812a309ea431877af0a038138f8ca9de81f6754af376e015dc3468274a5060432077a97fccfef929ee317cb6edd5690681907cdfda0dadbe1ff3	teacher	active	t	\N	Kristine F. Breganza	female	\N	tintinbreganza@gmail.com	\N	\N	\N	\N	\N	\N	advisory	\N	\N	f	Kristine	F.	Breganza	f	["teacher"]	t
139	1	LDMAJ_Registrar	scrypt:32768:8:1$O1Zw7QgVpGjLocZ2$f3c3b86045eeb547a8f8a666c5ff6eb22c056cfc48a8f778eecdbf07c1b8ceeefe51d56b229189d6fffcd5646a0ecd6539539b96a59e25b4245e2a1a7a869446	registrar	active	f	2026-09-07 02:46:15.353948	Precy Angela C. Roceo	female	\N	ela2960@gmail.com	\N	\N	\N	\N	\N	\N	advisory	\N	\N	f	Precy Angela	C.	Roceo	f	["teacher", "registrar"]	f
157	1	LDMAJ_0065	scrypt:32768:8:1$nIRNovquCEgMTFf9$2bab9ff7fe94b982c7502e0b368fc8f96db7998ce63f802a78db285b9b4dd4e256f3ca08234d852647a3bfb446cca8543e4701542c7cd88c6905bf1590f5e1fe	student	active	f	2026-09-24 14:04:37.111734	\N	\N	\N	coderajamila@gmail.com	\N	215	\N	\N	\N	\N	advisory	\N	\N	f	\N	\N	\N	f	["student"]	f
124	10	LDBB_Teacher_9	scrypt:32768:8:1$ccKkVqxwftKIMKvw$f1f7d322d4967959fcaa9a45f4d98164e083b1049c7ec64a3ccbab69345905d2ff10f51d7c83ee49bc92cdfd943050ca27ad4247d4ebc1e3ecf66d112b92e555	teacher	active	t	\N	Aria Hope Less	female	\N	kimberlychelsiemamaril@gmail.com	\N	\N	\N	\N	\N	\N	advisory	\N	\N	f	Aria	Hope	Less	f	["teacher"]	f
125	4	LDPSJ_0002	scrypt:32768:8:1$Mn2aNdVNvg1PbjPk$4300be39ae4d35991b51f5d45dea20b3aa4a5c5e8fbfdb2eae7884dc80ca228424184310080bb524654f79018a3fb5afd5c7d590071963a5931ca65a4974d89b	student	active	f	2026-08-19 08:01:24.941799	\N	\N	\N	bakagokuto1@gmail.com	\N	135	\N	\N	\N	\N	advisory	\N	\N	f	\N	\N	\N	f	["student"]	f
126	4	LDPSJ_Cashier_2	scrypt:32768:8:1$K6SlrYTIISJscYvL$efd0f1c4e642ead8c7d46e43051ff9d19a7c1c226118e511c23f60ec1244676d204d7ef5d86f677903bf7dc92f058e50c47622920b92ab05b1e7abb53d47bc80	cashier	active	f	2026-08-19 08:20:17.488441	HEY TRY	female	\N	bakagokuto2@gmail.com	\N	\N	\N	\N	\N	\N	advisory	\N	\N	f	HEY	\N	TRY	f	["cashier"]	f
129	10	LDBB_0004	scrypt:32768:8:1$NHDnwPUoF1sCxlbJ$b5d44670c24564d977042a73e26712cb46be91453c389101f8bd1f67efc10481538ba012dfd9842489faa891e375de2937841c86b951d9134385af1535bf384f	student	active	f	2026-08-31 08:18:21.628356	\N	\N	\N	mariasierrajunterial@gmail.com	\N	141	\N	\N	\N	\N	advisory	\N	\N	f	\N	\N	\N	f	["student", "parent"]	f
133	10	LDBB_0006	scrypt:32768:8:1$Y4JxCPgzlLzIbLJt$161a368ba0c78677cee060c7958ee511776913cbb5db24117b8fbe55876f0110f53b839d1a978ba8f45d11d3c4815e039b17c3dd49109c9750f6deb2090c649e	student	active	f	2026-09-01 01:50:23.387793	\N	\N	\N	venice.caparros@gmail.com	\N	143	\N	\N	\N	\N	advisory	\N	\N	f	\N	\N	\N	f	["student"]	f
134	10	LDBB_0007	scrypt:32768:8:1$MIVhvgBAu905HFLH$babfed3857387667cbf477ac34a02f9a18400fd062b93671f659b8d9d2752b56a6ac18cb42b6fd70fbde1617e321cad2dee4dd9cb0d62026c2d0ba71c8348153	student	active	f	2026-09-01 01:54:54.290885	\N	\N	\N	oninnapiza4@gmail.com	\N	144	\N	\N	\N	\N	advisory	\N	\N	f	\N	\N	\N	f	["student"]	f
127	4	LDPSJ_0004	scrypt:32768:8:1$Zn8CE3AttK3I6KDP$2fffe400c7a72ab2c74b65fab91f45c896a5e48c68f43fd17e733d8c1b0b405e109c07f718f1c90457bccab441c70834653f1585e34e8cffadacdb9426911f61	student	active	f	2026-08-19 11:35:35.461108	\N	\N	\N	biticonmeryll@gmail.com	\N	140	\N	\N	\N	\N	advisory	\N	\N	f	\N	\N	\N	f	["student", "parent"]	f
172	1	LDMAJ_Parent1	scrypt:32768:8:1$8pdH6i4pqfTxYklL$449ef8a09fb4a6dd194548b818869cfa6ebfc277a8f51089d505e6eaa37cac1aa97a4ca3f25b76dc5ed69a9bd52cc0785185b17c9a018e95b6a085433f31d3a0	parent	active	t	\N	Elaine Badiola	\N	\N	elaine.badiola@deped.gov.ph	\N	\N	\N	\N	\N	\N	advisory	\N	\N	f	Elaine	\N	Badiola	f	["parent"]	f
131	10	LDBB_Cashier	Cashier123	cashier	active	f	2026-08-31 08:45:58.098467	Mary Santos	female	\N	bakagokuto5@gmail.com	\N	\N	\N	\N	\N	\N	advisory	\N	\N	f	Mary	\N	Santos	f	["cashier"]	f
145	1	LDMAJ_Teacher_5	scrypt:32768:8:1$2DRDTrVDO4jkQ5Xc$7d4de226880f0ee87a7c41b10cf4ad3384815cdce0a3afe3cb5f796d402ffd45e849368fb31124a88ed051b8c4c3f622d6aa74e63a82c5e2ba8ec72a91fe29cf	teacher	active	t	\N	Norelyn C. Dorado	female	\N	doradonorelyn1@gmail.com	\N	\N	\N	\N	\N	\N	advisory	\N	\N	f	Norelyn	C.	Dorado	f	["teacher"]	f
83	4	LDPSJ_Registrar	scrypt:32768:8:1$v9IjFs79N2eY2aYa$0d297aaf2d2a5955eb37cfc8a46e7f2a1a7170554f6ce3edfe520ed7ee3b015aafb857683fa9df555d4c36d84e798d20956158001591ef4a55da75b947ccc704	registrar	active	f	2026-04-29 03:14:49.115225	Mateo De Leon	male	\N	mariasierrajunterial@gmail.com	\N	\N	\N	\N	\N	\N	advisory	\N	\N	f	Mateo	De	Leon	f	["registrar", "parent"]	f
86	4	LDPSJ_Teacher	scrypt:32768:8:1$OOMfVSHQqVZcSxLk$7facd8b17a13216eb1b3bf90812f91ef67ee9d3edb22a8c244cccecee6945253b66ea9ee041e65422ebe0596dfdfe9ef3fd98279e4e997d5e89929151d78cf6d	teacher	active	f	2026-04-29 03:16:25.053688	Joy Cruz	Female	\N	junterialmaris@gmail.com	75	\N	\N	\N	\N	\N	advisory	\N	\N	f	Joy	\N	Cruz	f	["teacher", "parent"]	f
90	8	LDMAJ1_Admin	scrypt:32768:8:1$IK70dhhrMiGLHrjE$258a646096e03ee6e9059e21a9459da205c01606dd4f0236ef80ee69528541ba84fd082f4cc13ee2aca2455e591155b252f75b345467063c703213e6692570cf	retired_admin	inactive	f	2026-04-29 06:54:34.593184	Jocelyn V. Ramirez	Female	\N	mariasierrajunterial@gmail.com	\N	\N	\N	\N	\N	\N	advisory	\N	\N	f	Jocelyn	V.	Ramirez	f	["retired_admin", "parent"]	f
84	4	LDPSJ_Cashier	scrypt:32768:8:1$px12fsXtoLZWNgf2$b22a8517d1b54019cc0bb52b832d1f6cdd87b8759767dfb5ae5356193cb47c797627ed15a726dd737e540a3773a9429de505028bd809f09c22881187b3423e8f	cashier	active	f	2026-04-29 03:13:47.726776	Severin Maria Clarke	female	\N	mariasierrajunterial@gmail.com	\N	\N	\N	\N	\N	\N	advisory	\N	\N	f	Severin	Maria	Clarke	f	["cashier", "parent"]	f
82	4	LDPSJ_Admin	scrypt:32768:8:1$km7tivtB1Q0fPbMW$688f3ba51b4357920049f634f29628a5cd2eb425d9465363982529ba45e5baf6ef955e6087a8647f475ea27f0fc91e9a9cf2804af28ac71a5c8365476f931869	retired_admin	inactive	f	2026-04-29 03:00:29.282485	Victor Rowan	Male	\N	chelzycada@gmail.com	\N	\N	\N	\N	\N	\N	advisory	\N	\N	f	Victor	\N	Rowan	f	["retired_admin", "parent"]	f
158	1	LDMAJ_Teacher_9	scrypt:32768:8:1$KvJgQBU8f6F4SpSf$9ed6566d53d59b0d730ee191b4c6ac0c3b4da991f043fe2bdef8d20d781fdf58d749863aef556bc819a302aa651749eb6408e581d6a3b4ce087e141da028fef4	teacher	active	t	\N	Charlene G. Umali	female	\N	umalicharlene1999@gmail.com	\N	\N	\N	\N	\N	\N	advisory	\N	\N	f	Charlene	G.	Umali	f	["teacher"]	f
89	7	LDCAL_Admin	scrypt:32768:8:1$gWq3VfbnvAIOzPBV$6269c5b242c839bc34f6cd3f41cd44d4d05615331afbed9c2870b07b30dfed81bbb8c52ed55da2d6f6b2c0f2c9aae0f586617d52c3e05b9b9dc5890a70c62cd1	retired_admin	inactive	t	\N	Victoria Lee	Female	\N	milknutdairy@gmail.com	\N	\N	\N	\N	\N	\N	advisory	\N	\N	f	Victoria	\N	Lee	f	["retired_admin", "parent"]	f
168	1	LDMAJ_0076	scrypt:32768:8:1$7spedjavXcH7Ykev$f5a6deb28d105b93067a48b7ea250816f7d46cb11613a5e2b13d78dfda33c1b10564c043ee82b60e90d01d6353147a8ba5ede1efe5fbea7d36cf06bfccb3d8e6	student	active	f	2026-09-28 07:33:19.25033	\N	\N	\N	resquiburnok@gmail.com	\N	226	\N	\N	\N	\N	advisory	\N	\N	f	\N	\N	\N	f	["student"]	f
85	4	LDPSJ_Librarian	scrypt:32768:8:1$j2cyWnG0GUrkPUpJ$4072e783ea9ab939cc224c40af3ccd2d4e9deb329b756e9a28217157190f91934ea9adbd426a137b934efb1b6f47e39838242bddbf33a9380b9149a3543c54c6	librarian	active	f	2026-04-29 03:11:54.90195	Maria Lee	female	\N	milknutdairy@gmail.com	\N	\N	\N	\N	\N	\N	advisory	\N	\N	f	Maria	\N	Lee	f	["librarian", "parent"]	f
87	5	LDLUI_Admin	scrypt:32768:8:1$TvztaAf9uVkJ0Mgc$52bc33cc388e63141dde23f5c7ae02c82bf70f169020fd24aa5c6a380c9b91245002579cd5208381bd6ff1278cb3974d5c4003acc402b7c3f0701324e6036524	retired_admin	inactive	t	\N	Nathaniel Ward	Male	\N	milknutdairy@gmail.com	\N	\N	\N	\N	\N	\N	advisory	\N	\N	f	Nathaniel	\N	Ward	f	["retired_admin", "parent"]	f
88	6	LDPAE_Admin	scrypt:32768:8:1$S1EFkAbMuRLWwa9q$34d4e1e3a135855276eba3e7a79ddcbb207b57b139df72b24512d08794529a5ee8a9c34a93f3ee490472fa5d29d1b3dc6ccf35decc29e07cb30c58fc1f02ed70	teacher	active	t	\N	Antonia Salazar	Female	\N	milknutdairy@gmail.com	\N	\N	\N	\N	\N	\N	advisory	\N	\N	f	Antonia	\N	Salazar	f	["teacher", "parent"]	f
136	10	LDBB_0009	scrypt:32768:8:1$2swlnFD3DeiK7J5y$b63af98ac61330df9c8dfb2720b2ecf452e4c3b63183f0af488857fa31da82db103d15d1eaab5d2a3f662b72151e2d62aab31eca2f6eaec506b56e4201c3fa7a	student	active	f	2026-09-01 02:09:16.936562	\N	\N	\N	bladimierdiego9@gmail.com	\N	146	\N	\N	\N	\N	advisory	\N	\N	f	\N	\N	\N	f	["student", "parent"]	f
137	10	LDBB_0011	scrypt:32768:8:1$6zQ3E49VHqCVqPzz$3a44de8145a993c6e5ea05411f16faba7e8cf435e5ae5a76fb5022b2c0b0e49f025f4bbc5088de668679875cf1da1620551ffe474b91de186e34743e96f0ecb4	student	active	f	2026-09-01 02:23:54.75067	\N	\N	\N	angeloponce209@gmail.com	\N	148	\N	\N	\N	\N	advisory	\N	\N	f	\N	\N	\N	f	["student", "parent"]	f
152	1	LDMAJ_Teacher_8	scrypt:32768:8:1$UbsVmIM7VVVyldCN$3e6e0dd1c18e0e9aba7b4d88f659f45497db954c4ae160d6a9fe84db76c7363b9c2e62789be280f66becdf463905e613764be9651e843b13a837ee34295dfb42	teacher	active	t	\N	Amelita Breganza Sta. Ana	female	\N	amelitastaana85@gmail.com	\N	\N	\N	\N	\N	\N	advisory	\N	\N	f	Amelita	Breganza	Sta. Ana	f	["teacher", "librarian"]	f
163	1	LDMAJ_Teacher_14	scrypt:32768:8:1$kmLfDG0Cb9HlQRZD$a01f06dd828aff0a2ddd1fe90f73811f20dc74b57a03335ac05e5093a28f04168f8aed9d22a25371cfe1509c4aa1aab027aa63f4f0d6580a6ed375d908ff2b47	teacher	active	t	\N	Angelica V. Caagbay	female	\N	caagbayangelica11@gmail.com	\N	\N	\N	\N	\N	\N	advisory	\N	\N	f	Angelica	V.	Caagbay	f	["teacher"]	f
138	1	LDMAJ_Admin	scrypt:32768:8:1$Iltf1rgVWqIVM3w1$a5b223442a3c06d56a9f65e21ed17046ce9a8c4c1fd600d63f8aa89d8aec604b2f408b2f6a3b1e24c8312ae9061c20e0dd4c097531f1f69edab9b010b6588502	branch_admin	active	f	2026-09-07 02:42:59.423895	Jocelyn Villaraza Ramirez	Female	\N	joieramirez01082000@gmail.com	\N	\N	\N	\N	\N	\N	advisory	\N	\N	f	Jocelyn	Villaraza	Ramirez	f	["branch_admin"]	f
159	1	LDMAJ_Teacher_10	scrypt:32768:8:1$8Yt1iJu4GXu7mzxV$1ab4c68b0b6a3d50122797236a0b8e9379405d26c759a9b2d21925bc1507a0d734a8d34d4cb7d81ace00a053bf312e4e7022dc9b228c3866aec06642f478699c	teacher	active	t	\N	Severina Esteba Doctolero	female	\N	severinadoctolera122@gmail.com	\N	\N	\N	\N	\N	\N	advisory	\N	\N	f	Severina	Esteba	Doctolero	f	["teacher"]	f
95	8	LDMAJ1_Admin_2	scrypt:32768:8:1$kTwMQ9i7bn8xQ4qU$7a986aac83c4aaed7fe34f43eeef8da4c51bab62a7c18b216da4ad16dd674dfcb57d7df8862efaed8a2834b56b0ad4b0d41b5e3a5159060eabb91ea05be3e315	retired_admin	inactive	t	\N	Melbourne Biticon	Male	\N	bakagokuto@gmail.com	\N	\N	\N	\N	\N	\N	advisory	\N	\N	f	Melbourne	\N	Biticon	f	["retired_admin", "parent"]	f
164	1	LDMAJ_Teacher_15	scrypt:32768:8:1$Rqz4XMCI3K4DgKje$07821caca71e2ea366c6138338fcce76f92d323f1fab483e65082e995e8d45ce5b27d0b346b59dc39905d9da8d3a13fb6aa10d909cd88e2279fac05891c9dfbe	teacher	active	t	\N	Faye Elaine M. Ronabio	female	\N	fayelaineronabio@gmail.com	\N	\N	\N	\N	\N	\N	advisory	\N	\N	f	Faye Elaine	M.	Ronabio	f	["teacher"]	f
146	1	LDMAJ_Teacher_6	scrypt:32768:8:1$JPuXraXQrcrcVPSG$a9f9b86f17188822d6b374dc8d1baab6d43cd54858ba82497ac0d22da4337219ba08d40dd31c140e3092943aeeeac6b9921172bbcdd41deafa53210bafe4a978	teacher	active	f	2026-09-21 07:38:02.815229	Nicelyn C. Arsolacia	female	\N	arsolacianicelyn@gmail.com	\N	\N	\N	\N	\N	\N	advisory	\N	\N	f	Nicelyn	C.	Arsolacia	f	["teacher"]	f
108	4	LDPSJ_Librarian_2	scrypt:32768:8:1$JJ5g5cRb7w4rvPoN$5fe227e36465257c41f11ee3357ce11c73a3379d9f1111f08823a8b341fd51306d40e31602db14b597ae0849689d28ccacded46523575515458b4a152ec0d664	librarian	active	f	2026-08-19 03:12:20.979127	Junterial Maria Sierra	female	\N	mariasierrajunterial@gmail.com	\N	\N	\N	\N	\N	\N	advisory	\N	\N	f	Junterial	Maria	Sierra	f	["librarian", "parent"]	f
105	6	LDPAE_Admin_2	scrypt:32768:8:1$XeoUh4ylPrssVbRE$7ce183f9fd9286321d6aa386c0c14072e572594c23ea1842fe82d1877efb7a83950643399aa4a03cd1183018381c4f88213785ea922769a7fe8028c7092764b2	branch_admin	active	t	\N	Maria Sierra Clarito Junterial	Male	\N	marizjunterial2@gmail.com	\N	\N	\N	\N	\N	\N	advisory	\N	\N	f	Maria Sierra	Clarito	Junterial	f	["branch_admin"]	f
97	4	LDPSJ_Admin_2	scrypt:32768:8:1$pZLE7AbXSIbwMEzn$0c40324cdcfbf3a68f0d75bc7f73d76642d90d05546c0c1d73bdb5cb8142e6d9d2d9f21032ece158d07da9c9990abb04761e5d768e992de17c235e0d03635ea3	branch_admin	active	f	2026-08-18 03:40:19.492362	Chelsie Cada	Female	\N	mamarilkimberlychelsie@gmail.com	\N	\N	\N	\N	\N	\N	advisory	\N	\N	f	Chelsie	\N	Cada	f	["branch_admin"]	f
110	4	LDPSJ_Registrar_2	scrypt:32768:8:1$wnTvTrO7Lc4iW0vk$a732f0803a24a21bc31f1f1f5d6ecdac20beb582bea1aa372f4abea28e9168462b797f0446814bab8db24751fb55d9b8b5dd8b38e0a2f9c1357e63f0dc9fee36	registrar	active	f	2026-08-19 03:35:44.370805	Junterial Maria Sierra	male	\N	marizjunterial2@gmail.com	\N	\N	\N	\N	\N	\N	advisory	\N	\N	f	Junterial	Maria	Sierra	f	["registrar"]	f
169	1	LDMAJ_0039	scrypt:32768:8:1$IuxwVN5YwSutZNnH$1415b09b02a923a27c8f998433d7d1dd9217b7f6c26d608da9edf98be951f3e276f4777dedcd6fbbf8d40669f93d53c027d9b8d657f103a1f416357481c7090f	student	active	f	2026-09-29 06:35:22.293541	\N	\N	\N	biticonmeryll@gmail.com	\N	189	\N	\N	\N	\N	advisory	\N	\N	f	\N	\N	\N	f	["student", "parent"]	f
153	1	LDMAJ_0173	scrypt:32768:8:1$hsfxxF2i4SAYE873$2feed0fc1891fffaff4a5f54174356bf46746712369ff4cf53c304b8307fe906d2133780a0fb2f93c57b2a255aaedfe03ac691017db6e5f9322e7a4de8b6fe80	student	active	f	2026-09-24 12:26:28.767956	\N	\N	\N	jhoannaricamara@gmail.com	\N	323	\N	\N	\N	\N	advisory	\N	\N	f	\N	\N	\N	f	["student"]	f
106	4	LDPSJ_Parent1	scrypt:32768:8:1$WGZPOd7cxwqQpQo2$a21176f4abac0adda2505c98311e70724c82870bceae13b56ccc061a5ea21b5cfb0547ff0d2db9d40aac1365552d53cd8a5cbf6ff914d10e95e66ce25dced1e3	parent	active	f	2026-08-18 03:20:02.253235	Brenda Robel Biticon	\N	\N	melbournebiticon@gmail.com	\N	\N	\N	\N	\N	\N	advisory	\N	\N	f	Brenda	Robel	Biticon	f	["parent"]	f
109	10	LDBB_Admin	scrypt:32768:8:1$vR4QjV2f7rQuvusV$1937749aadc0cd7832163d748f11d972f8076c4bea9b86efa1625b281afb5d541be73c0f7c9476f6b3b727f5079fbc57cb22d54608109ce0088918394615713e	branch_admin	active	f	2026-08-19 03:23:58.987961	Joseph Lim Cruz	Male	\N	rhealyncd123@gmail.com	\N	\N	\N	\N	\N	\N	advisory	\N	\N	f	Joseph	Lim	Cruz	f	["branch_admin"]	f
160	1	LDMAJ_Teacher_11	scrypt:32768:8:1$JKXLU57KxbJDsIgW$3359c6f3a5ab3586fb453d0cf3ba9fd917be58c2ab10b4de5d2f9383e5e544b33c4e8e9ab2ccfca56c3d35d97f27d21e88ba84c473bfd7521f00f60ba75e5800	teacher	inactive	t	\N	Precy Angela C. Roceo	female	\N	ela2960@gmail.com	\N	\N	\N	\N	\N	\N	advisory	\N	\N	t	Precy Angela	C.	Roceo	f	["teacher"]	f
165	1	LDMAJ_Teacher_16	scrypt:32768:8:1$F13A5ZIYlOSjOI6B$5b1e4e3e68655d3d843a3304a40f267f37fd34121d4c4380869595d4b6d7f81aceb01db512c6913e4f7fc389dced388532300cd3ce95bac318a9fc1f21f2bdda	teacher	active	t	\N	Joan S. Zulaybar	female	\N	ebengsobrevinas02@gmail.com	\N	\N	\N	\N	\N	\N	advisory	\N	\N	f	Joan	S.	Zulaybar	f	["teacher"]	f
170	1	LDMAJ_0052	scrypt:32768:8:1$RIEcydYFcBVFLigz$23d716521c3af1d7291e93c417927f8f40a49ea1e1a75fb43aae830d9584b39419f7d1867d5a38c0829c2905285f7f5cb3808d96e2489705a2aea9b567d6e740	student	active	f	2026-10-01 06:41:37.633472	\N	\N	\N	altheabala31@gmail.com	\N	202	\N	\N	\N	\N	advisory	\N	\N	f	\N	\N	\N	f	["student"]	f
114	10	LDBB_Teacher	scrypt:32768:8:1$Xno8bmCwpY2oRN6p$208866f611fd59a664172215f51faf24f82de77953d8f5876eb6d98a160841031c5ace56b7ca6b22d7afa3f76853d7138e3aada328e9f572962dbe5cc4e90e42	teacher	active	f	2026-08-19 04:06:40.719726	Zoe Anne Lim	\N	\N	milknutdairy11@gmail.com	\N	\N	\N	\N	\N	\N	advisory	\N	\N	f	Zoe	Anne	Lim	t	["teacher"]	t
154	1	LDMAJ_0011	scrypt:32768:8:1$OWoKftdhBsRoBHTS$a1c039ce7b6b572180a6778c951a0898a16068e0efdb0555e63b018c44af903329bbbb02b6ba8525d21b5c389b28fc87f3b7d549545719cd446759232fabea43	student	active	f	2026-09-24 12:56:55.38095	\N	\N	\N	ninaconejares@gmail.com	\N	161	\N	\N	\N	\N	advisory	\N	\N	f	\N	\N	\N	f	["student"]	f
121	4	LDPSJ_Teacher_2	scrypt:32768:8:1$NQXtMags8ilKrt3I$132722893de507ffbd34e752278b12d84e5d6cbaa14454090ba267ef37fb7ca1a2948c0b64f715fc76f884a1c3114a59e8b28d7321e9fc5e5778551e677c387f	teacher	active	t	\N	Mark Zuckerberg	male	\N	bakagokuto2@gmail.com	\N	\N	\N	\N	\N	\N	advisory	\N	\N	f	Mark	\N	Zuckerberg	f	["teacher"]	f
142	1	LDMAJ_Teacher_2	scrypt:32768:8:1$Gk39VB1y7NDF6iY7$f5f7de4d8f4eb2e247318f9e72b848012f2e501156f592316893ce98c855cd3817eb26070c69752b59cae4b1074063845c3826eb2ae993380144f0d675359423	teacher	active	f	2026-09-18 05:26:28.274236	Anna Marie Montemor Breganza	female	\N	ambreganza@gmail.com	\N	\N	\N	\N	\N	\N	advisory	\N	\N	f	Anna Marie	Montemor	Breganza	f	["teacher"]	f
147	1	LDMAJ_Teacher_7	scrypt:32768:8:1$TWSfDzGwVPcbqz8C$137ac77a560cd14a6e3ff6f65a1b2789b77a65dbb42dd5d2934030d3ba60a09269708201996cfe77b0bb632c36302acf34a13254a4f98c7c020fd9ae223fd8fc	teacher	active	t	\N	Corazon Palentinos Monfero	female	\N	corazon.monfero001@gmail.com	\N	\N	\N	\N	\N	\N	advisory	\N	\N	f	Corazon	Palentinos	Monfero	f	["teacher"]	f
141	1	LDMAJ_Teacher	scrypt:32768:8:1$UBBcTBLjg9V3QKMd$d439d9705248af62d10ea9f14a69cc11563ccb6553bd8d2cf68a828cbcdeeb9a4412e6b6f3bb274a53a42be62480e71911f257ba91cb94b07a23f50463f7a222	teacher	active	f	2026-09-18 05:21:35.770259	Rowena Rosel Del Rosario	female	\N	delrosariorowena78@gmail.com	\N	\N	\N	\N	\N	\N	advisory	\N	\N	f	Rowena	Rosel	Del Rosario	f	["teacher"]	f
122	4	LDPSJ_Parent2	scrypt:32768:8:1$yA138rJBizvFCWqG$43313bbfec90fecb798d4e843f8a36eb089df4ae33b818ac74fcb49994b3e45d1f58bd71926a91dc5d63894cfbc64a69a34c60e0a2d3086918bafa19f006aee5	parent	active	f	2026-08-19 08:10:10.795421	Brenda Robel Biticon	\N	\N	bakagokuto@gmail.com	\N	\N	\N	\N	\N	\N	advisory	\N	\N	f	Brenda	Robel	Biticon	f	["parent"]	f
132	10	LDBB_Parent1	scrypt:32768:8:1$BKhF6ecbCqgEa1Zp$4cb01c09e04e3ce033a6de5b8addcb752a888a44b08a4c5be80bf69b3110cf218272f297b019e18fceae158c7f2b7ec4cbb57d972d56e7fe157b8c83186736a9	parent	active	t	\N	Luke David Flores	\N	\N	bakagoku3@gmail.com	\N	\N	\N	\N	\N	\N	advisory	\N	\N	f	Luke	David	Flores	f	["parent"]	f
135	10	LDBB_0008	scrypt:32768:8:1$bIsOCSy1bvAS68hf$c8d35dc970ed744fe6ae7915473333363c192eb870e9c58fa5c93ea6f56b9f96a1c89059f3b5fbbe8155bd870dbb06ee9385bc3f428569588dd8c63c93977bcc	student	active	f	2026-09-01 02:00:39.841049	\N	\N	\N	markjohnpascua08@gmail.com	\N	145	\N	\N	\N	\N	advisory	\N	\N	f	\N	\N	\N	f	["student", "parent"]	f
128	10	LDBB_0005	scrypt:32768:8:1$Nl4lKQKiiVxkL9Jo$b68c9a227044f529b470e0e3e46dfffd66cfbab9a6f5994a53861d9c62241ae33a472c0bac1d4fc6d9372c677dba2765891772c1c9f4996bf5e7a7425055cb05	student	active	f	2026-08-31 08:17:16.501994	\N	\N	\N	chelzycada@gmail.com	\N	142	\N	\N	\N	\N	advisory	\N	\N	f	\N	\N	\N	f	["student", "parent"]	f
123	10	LDBB_Teacher_8	scrypt:32768:8:1$bYanoAQm4yLUwRtr$8e8b67522d87962d902c6486079d6a7f395876261d330faa65d2816394a1beec5b858964f8bf8756da3d76b9ce83c5bab9ce76189423403128f7be14ae8f92b1	teacher	active	t	\N	Leo Max Cruz	male	\N	chelzycada@gmail.com	\N	\N	\N	\N	\N	\N	advisory	\N	\N	f	Leo	Max	Cruz	f	["teacher", "parent"]	f
119	10	LDBB_Teacher_6	scrypt:32768:8:1$AGlxfD63b3n8sEOl$abfe77fec2a792e3e154372f679f33578cff5cf3f58189b3d8b2ff29a19d1e86426efcb79f4bd4cc1124ff714e39d9e8c62e5e4996c530c57c44283bd04e95cd	teacher	active	f	2026-08-19 05:53:46.501094	Chris John Brown	male	\N	milknutdairy@gmail.com	\N	\N	\N	\N	\N	\N	advisory	\N	\N	f	Chris	John	Brown	f	["teacher", "parent"]	f
120	10	LDBB_Teacher_7	scrypt:32768:8:1$RjOIBmtD6Sn3thJF$3b02946fb429cfe39c8c8f5eb83b042076930a08c9c1b131def8fc8c0ff852dd52f0e9af67686f5444a7a7df8ceebdc8c5e8a237893cd7e238c277c569b840a4	teacher	inactive	t	\N	Chris John Brown	male	\N	milknutdairy@gmail.com	\N	\N	\N	\N	\N	\N	advisory	\N	\N	t	Chris	John	Brown	f	["teacher", "parent"]	f
117	10	LDBB_Teacher_4	scrypt:32768:8:1$o3ma5q2rXxldUP34$4ae50c4c2097dc4283052525bfe5b709351522668c84275afc5b25e5b72e97f77e4f01b6293518fc9bd84c290db492d3a97b19bb8e2b6c4acc4678d43c8619af	teacher	active	f	2026-08-19 04:13:11.262864	Axel Jay Cruz	male	\N	milknutdairy@gmail.com	\N	\N	\N	\N	\N	\N	advisory	\N	\N	f	Axel	Jay	Cruz	f	["teacher", "parent"]	f
118	10	LDBB_Teacher_5	scrypt:32768:8:1$vWk6re52eL1pfERl$9d438c0faf1a1b386fff6333af6da9bef1774a7b3a7d43adc0a74ae2dfb3a06ddc8fe9463905a311c8052aed77c8ab751fbeb36819074ba32a0921fe56e37891	teacher	inactive	t	\N	Axel Jay Cruz	male	\N	milknutdairy@gmail.com	\N	\N	\N	\N	\N	\N	advisory	\N	\N	t	Axel	Jay	Cruz	f	["teacher", "parent"]	f
116	10	LDBB_Teacher_3	scrypt:32768:8:1$rT7MjnPVnmEFADcS$ed49dc911ed49b43695fc7a89f4951a24c21a9e2e6ac7f33d3b79b13cad913c2df91204e9b8614c10049c885923fccfeebe22a5d0d1f57599f5a84f8e3a32ec9	teacher	inactive	t	\N	Zoe Anne Lim	female	\N	milknutdairy@gmail.com	\N	\N	\N	\N	\N	\N	advisory	\N	\N	t	Zoe	Anne	Lim	f	["teacher", "parent"]	f
115	10	LDBB_Teacher_2	scrypt:32768:8:1$CV1PmDRdpeeSTOyr$33cbbcf911ca75da7fe8bda8d696a1bc83e332c8dea7b436d12f81e7d52a52018dcbf188b185bc21a5931861962f8d3e9a13032e0815ff0b42ca7a7670f89f05	teacher	inactive	t	\N	Zoe Anne Lim	female	\N	milknutdairy@gmail.com	\N	\N	\N	\N	\N	\N	advisory	\N	\N	t	Zoe	Anne	Lim	f	["teacher", "parent"]	f
140	10	LDBB_0014	scrypt:32768:8:1$owzGWIAE7l46gyVx$618cdc12aa09242c0393b8302406a3d7cf4c0a9fe65fee54ef5853ccd4c4a9d5a8dc9e809421c0590ac72cef5e287fb8090ee4cdd2f569f56c7e541ebf6de226	student	active	f	2026-09-18 02:59:16.141333	\N	\N	\N	biticonmr@gmail.com	\N	488	\N	\N	\N	\N	advisory	\N	\N	f	\N	\N	\N	f	["student", "parent"]	f
130	10	LDBB_0001	scrypt:32768:8:1$5eZNX4GkuprdpdHT$327c511386fb3ed2ad2d6a405b6b82c225170060e3422467420930cadf33be121bf527e6c5b8d4afe662ae7cb82918608271bb89d46c837323e8782251b677d4	student	active	f	2026-08-31 08:18:49.427966	\N	\N	\N	biticonmr@gmail.com	\N	136	\N	\N	\N	\N	advisory	\N	\N	f	\N	\N	\N	f	["student", "parent"]	f
107	4	LDPSJ_0001	scrypt:32768:8:1$23rOjaW6d6lEsNkA$f47b50a3885c251d4afbb5b89c13b09516c21b51c96c6675002d85a8b6dc93b8a795b8cffbf8504efcc3eaeb963f637c726b0c4f301a943a143e441488323b56	student	active	f	2026-08-18 03:22:28.42794	\N	\N	Kinder	melbournebiticon@gmail.com	\N	150	\N	\N	https://res.cloudinary.com/diwiuseil/image/upload/v1787102652/liceo_uploads/profiles/arthur_15476d.jpg	\N	advisory	\N	\N	f	\N	\N	\N	f	["student", "parent"]	f
148	10	LDBB_0016	scrypt:32768:8:1$UnLSIjiMXWIuxC03$12c5036f3444c8b7b9e10070628d3a60d3f026cfef411fdd546a64360f9a3cf94c49bb0221c463ab8ab799fbea3baef38d7b7c7c34a08c4424075f712809f162	student	active	f	2026-09-22 07:04:29.183843	\N	\N	\N	mariasierrajunterial@gmail.com	\N	490	\N	\N	\N	\N	advisory	\N	\N	f	\N	\N	\N	f	["student", "parent"]	f
143	1	LDMAJ_Teacher_3	scrypt:32768:8:1$n8Uw1Kg0IbYeMjd7$4f97303703663b1bef15898b6957988075e1f19f93cb1c6741274367c5117c501f30a012f6c0c12ea1804d90a36f828a4e03216f54038a17ce922105efb04b8f	teacher	active	f	2026-09-18 05:24:37.03898	Johanne Estela Mari Cobrado	female	\N	msjem.cobrado@gmail.com	\N	\N	\N	\N	\N	\N	advisory	\N	\N	f	Johanne Estela Mari	\N	Cobrado	t	["teacher"]	f
111	10	LDBB_Registrar	scrypt:32768:8:1$dsndRQLqWD6s5719$33ed494286256b6256e4dcdc1b9e003ecc36b66fccb0f6d5768d4815356f92a3421a9138098ca7324a3d0263bd2e6dbd6c12e7ba5438da866baf51c4fb71d52d	registrar	active	f	2026-08-19 04:09:34.525977	Mary Grace Reyes	female	\N	milknutdairy@gmail.com	\N	\N	\N	\N	\N	\N	advisory	\N	\N	f	Mary	Grace	Reyes	f	["registrar", "parent"]	f
155	1	LDMAJ_0068	scrypt:32768:8:1$agxueWws0peg1Xgt$69304aeb072a759293efee853a195dc36d243f8b3a6c884c029cc0f996f9bc1bfe98f4308e87c98e2aec72f68276478c07bdf2cc9d2d9e654fc1eda914bfc5b0	student	active	f	2026-09-24 13:20:30.639066	\N	\N	\N	tanesjanadrian@gmail.com	\N	218	\N	\N	\N	\N	advisory	\N	\N	f	\N	\N	\N	f	["student"]	f
113	10	LDBB_Librarian	scrypt:32768:8:1$KoqjkaweGoOGJmzg$0ad540d64f01296831155034c2343b07e58b79365f664dcda9704727486c89ee6c102e1cdbc703dc0410576aa9e5cfa4786b23e895cf4de663fd142afa4818ed	librarian	active	f	2026-08-19 04:10:55.22198	Jose Luis Mercedes	male	\N	milknutdairy@gmail.com	\N	\N	\N	\N	\N	\N	advisory	\N	\N	f	Jose	Luis	Mercedes	f	["librarian", "parent"]	f
149	10	LDBB_0015	scrypt:32768:8:1$BGWDBt9p78nGzXTK$4847ee96757e4247f5f9d7399ce8a160ac257c515e5a2432f1cced0b5e1eafa5a66a6e2974d3604892cb4f8fee4c2c1d6613b6a41da8df71d4fdd40fe35aee66	student	active	f	2026-09-22 07:17:55.022381	\N	\N	\N	melbournerb@gmail.com	\N	489	\N	\N	\N	\N	advisory	\N	\N	f	\N	\N	\N	f	["student", "parent"]	f
156	1	LDMAJ_0057	scrypt:32768:8:1$UPseZ3y9TR4VGuun$2337ef493ab7e1721a3a8cdb5fe71c9cdd594f32593f3dd97d214fce81bb97ec03061a8f52d5929ac7dfee1e3d800087e23e4335120261f754b8a3a7523087eb	student	active	f	2026-09-24 13:20:58.879242	\N	\N	\N	khaelmiguel.trovela@gmail.com	\N	207	\N	\N	\N	\N	advisory	\N	\N	f	\N	\N	\N	f	["student"]	f
150	1	LDMAJ_0337	scrypt:32768:8:1$6mIMrEfDdKFYaIqf$7f972a7b759cdc4fab1e353c51428e9733a5ae3a7fce39ab9c9c0f28bb1dd04bbfbe33101647656c890962e798a661332fa8d457f8708443e3a62334faf802ab	student	active	f	2026-09-22 08:31:37.643082	\N	\N	\N	bakagokuto@gmail.com	\N	492	\N	\N	\N	\N	advisory	\N	\N	f	\N	\N	\N	f	["student", "parent"]	f
151	10	LDBB_0018	scrypt:32768:8:1$ZhDz1CZnUTZ6qj44$bcdbf9ccf967c6616044a57edcf954690486d1ca7ffc33b9d8e6905f281780d2be06730781d501b1cc0c6069dc970e45bbcd4a6c84558269087c7e9686a85e35	student	active	f	2026-09-22 08:33:43.218821	\N	\N	\N	bakagokuto@gmail.com	\N	493	\N	\N	\N	\N	advisory	\N	\N	f	\N	\N	\N	f	["student", "parent"]	f
162	1	LDMAJ_Teacher_13	scrypt:32768:8:1$FRrN1A6ZFAyiwJIw$2452da329ae35cbcf9a06f3701700750f0fd56019f219f3fa3b912cbda4e33d846961da5503be4c631d7c338918d3c6ef33871b16846801ec07424728f63949e	teacher	active	t	\N	Maricris Sol Modina	female	\N	modinamaricris9@gmail.com	\N	\N	\N	\N	\N	\N	advisory	\N	\N	f	Maricris	Sol	Modina	f	["teacher", "cashier"]	f
166	1	LDMAJ_0055	scrypt:32768:8:1$65n2g8oQkQ9TLNBl$b4c51925a639d2f127472be615fbcc38b19d950ea8fdb3797e31ebbe77a850c1c2166c50079f3b471ae447f9d36f6a5579877cd22e3eba9c5bad9d4620cce4a7	student	active	f	2026-09-26 16:17:08.501028	\N	\N	\N	rinalynchavez0913@gmail.com	\N	205	\N	\N	\N	\N	advisory	\N	\N	f	\N	\N	\N	f	["student"]	f
171	1	LDMAJ_0027	scrypt:32768:8:1$laHZ2ubKvz1BrldZ$514cb1bfeb45b197fab257d9e3304dc2e5912bbbb0c65071d72a120719f4df50868c62d65a99b89d0c837961394a070446e46fc150ab2d8f0dbe000b1496b409	student	active	f	2026-10-01 09:21:57.682527	\N	\N	\N	villaneraailamarie2@gmail.com	\N	177	\N	\N	\N	\N	advisory	\N	\N	f	\N	\N	\N	f	["student"]	f
\.


--
-- Name: activities_activity_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.activities_activity_id_seq', 27, true);


--
-- Name: activity_grades_grade_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.activity_grades_grade_id_seq', 17, true);


--
-- Name: activity_submissions_submission_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.activity_submissions_submission_id_seq', 19, true);


--
-- Name: announcements_announcement_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.announcements_announcement_id_seq', 2, true);


--
-- Name: attendance_scores_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.attendance_scores_id_seq', 12, true);


--
-- Name: audit_logs_log_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.audit_logs_log_id_seq', 483, true);


--
-- Name: billing_bill_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.billing_bill_id_seq', 17, true);


--
-- Name: book_release_items_release_item_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.book_release_items_release_item_id_seq', 3, true);


--
-- Name: book_releases_release_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.book_releases_release_id_seq', 3, true);


--
-- Name: branches_branch_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.branches_branch_id_seq', 10, true);


--
-- Name: chatbot_faqs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.chatbot_faqs_id_seq', 11, true);


--
-- Name: daily_attendance_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.daily_attendance_id_seq', 3, true);


--
-- Name: daily_participation_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.daily_participation_id_seq', 3, true);


--
-- Name: enrollment_books_book_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.enrollment_books_book_id_seq', 1, false);


--
-- Name: enrollment_documents_doc_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.enrollment_documents_doc_id_seq', 582, true);


--
-- Name: enrollment_history_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.enrollment_history_id_seq', 1, false);


--
-- Name: enrollment_uniforms_uniform_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.enrollment_uniforms_uniform_id_seq', 1, false);


--
-- Name: enrollments_enrollment_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.enrollments_enrollment_id_seq', 496, true);


--
-- Name: exam_answers_answer_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.exam_answers_answer_id_seq', 474, true);


--
-- Name: exam_questions_question_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.exam_questions_question_id_seq', 297, true);


--
-- Name: exam_results_result_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.exam_results_result_id_seq', 92, true);


--
-- Name: exam_student_permissions_permission_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.exam_student_permissions_permission_id_seq', 1, false);


--
-- Name: exam_tab_switches_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.exam_tab_switches_id_seq', 481, true);


--
-- Name: exams_exam_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.exams_exam_id_seq', 82, true);


--
-- Name: failed_logins_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.failed_logins_id_seq', 176, true);


--
-- Name: finalized_grades_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.finalized_grades_id_seq', 1, false);


--
-- Name: grade_levels_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.grade_levels_id_seq', 248, true);


--
-- Name: grade_overrides_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.grade_overrides_id_seq', 1, false);


--
-- Name: grade_submission_requests_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.grade_submission_requests_id_seq', 6, true);


--
-- Name: grading_period_ranges_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.grading_period_ranges_id_seq', 14, true);


--
-- Name: grading_weights_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.grading_weights_id_seq', 20, true);


--
-- Name: holidays_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.holidays_id_seq', 1, false);


--
-- Name: individual_extensions_extension_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.individual_extensions_extension_id_seq', 10, true);


--
-- Name: inventory_item_sizes_size_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.inventory_item_sizes_size_id_seq', 481, true);


--
-- Name: inventory_items_item_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.inventory_items_item_id_seq', 1242, true);


--
-- Name: inventory_sizes_size_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.inventory_sizes_size_id_seq', 1, false);


--
-- Name: login_2fa_tokens_token_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.login_2fa_tokens_token_id_seq', 1, false);


--
-- Name: parent_notifications_notif_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.parent_notifications_notif_id_seq', 3, true);


--
-- Name: parent_student_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.parent_student_id_seq', 5576, true);


--
-- Name: participation_scores_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.participation_scores_id_seq', 12, true);


--
-- Name: password_reset_tokens_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.password_reset_tokens_id_seq', 4, true);


--
-- Name: payments_payment_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.payments_payment_id_seq', 28, true);


--
-- Name: posted_grades_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.posted_grades_id_seq', 2, true);


--
-- Name: reservation_items_reservation_item_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.reservation_items_reservation_item_id_seq', 25, true);


--
-- Name: reservations_reservation_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.reservations_reservation_id_seq', 19, true);


--
-- Name: schedules_schedule_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.schedules_schedule_id_seq', 337, true);


--
-- Name: school_years_year_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.school_years_year_id_seq', 30, true);


--
-- Name: section_teachers_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.section_teachers_id_seq', 446, true);


--
-- Name: sections_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.sections_id_seq', 140, true);


--
-- Name: shs_elective_offerings_offering_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.shs_elective_offerings_offering_id_seq', 3, true);


--
-- Name: shs_pathways_pathway_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.shs_pathways_pathway_id_seq', 2, true);


--
-- Name: shs_selection_periods_period_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.shs_selection_periods_period_id_seq', 3, true);


--
-- Name: shs_student_elective_items_item_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.shs_student_elective_items_item_id_seq', 1, false);


--
-- Name: shs_student_elective_memberships_membership_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.shs_student_elective_memberships_membership_id_seq', 2, true);


--
-- Name: shs_student_elective_requests_request_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.shs_student_elective_requests_request_id_seq', 1, false);


--
-- Name: student_accounts_account_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.student_accounts_account_id_seq', 170, true);


--
-- Name: student_notifications_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.student_notifications_id_seq', 163, true);


--
-- Name: subjects_subject_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.subjects_subject_id_seq', 191, true);


--
-- Name: swafo_discipline_log_log_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.swafo_discipline_log_log_id_seq', 1, true);


--
-- Name: swafo_parent_conferences_conference_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.swafo_parent_conferences_conference_id_seq', 1, true);


--
-- Name: swafo_records_record_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.swafo_records_record_id_seq', 1, false);


--
-- Name: teacher_announcements_announcement_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.teacher_announcements_announcement_id_seq', 5, true);


--
-- Name: teacher_grade_levels_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.teacher_grade_levels_id_seq', 14, true);


--
-- Name: teacher_section_assignments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.teacher_section_assignments_id_seq', 1, false);


--
-- Name: uniform_order_items_item_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.uniform_order_items_item_id_seq', 27, true);


--
-- Name: uniform_orders_order_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.uniform_orders_order_id_seq', 27, true);


--
-- Name: users_user_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.users_user_id_seq', 172, true);


--
-- Name: activities activities_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.activities
    ADD CONSTRAINT activities_pkey PRIMARY KEY (activity_id);


--
-- Name: activity_grades activity_grades_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.activity_grades
    ADD CONSTRAINT activity_grades_pkey PRIMARY KEY (grade_id);


--
-- Name: activity_submissions activity_submissions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.activity_submissions
    ADD CONSTRAINT activity_submissions_pkey PRIMARY KEY (submission_id);


--
-- Name: announcements announcements_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.announcements
    ADD CONSTRAINT announcements_pkey PRIMARY KEY (announcement_id);


--
-- Name: attendance_scores attendance_scores_enrollment_id_section_id_subject_id_gradi_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.attendance_scores
    ADD CONSTRAINT attendance_scores_enrollment_id_section_id_subject_id_gradi_key UNIQUE (enrollment_id, section_id, subject_id, grading_period);


--
-- Name: attendance_scores attendance_scores_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.attendance_scores
    ADD CONSTRAINT attendance_scores_pkey PRIMARY KEY (id);


--
-- Name: attendance_scores attendance_scores_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.attendance_scores
    ADD CONSTRAINT attendance_scores_unique UNIQUE (enrollment_id, subject_id, grading_period, year_id);


--
-- Name: attendance_scores attendance_scores_unique_idx; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.attendance_scores
    ADD CONSTRAINT attendance_scores_unique_idx UNIQUE (enrollment_id, subject_id, grading_period);


--
-- Name: audit_logs audit_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_pkey PRIMARY KEY (log_id);


--
-- Name: billing billing_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.billing
    ADD CONSTRAINT billing_pkey PRIMARY KEY (bill_id);


--
-- Name: book_release_items book_release_items_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.book_release_items
    ADD CONSTRAINT book_release_items_pkey PRIMARY KEY (release_item_id);


--
-- Name: book_releases book_releases_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.book_releases
    ADD CONSTRAINT book_releases_pkey PRIMARY KEY (release_id);


--
-- Name: branches branches_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.branches
    ADD CONSTRAINT branches_pkey PRIMARY KEY (branch_id);


--
-- Name: chatbot_faqs chatbot_faqs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chatbot_faqs
    ADD CONSTRAINT chatbot_faqs_pkey PRIMARY KEY (id);


--
-- Name: daily_attendance daily_attendance_enrollment_id_subject_id_attendance_date_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.daily_attendance
    ADD CONSTRAINT daily_attendance_enrollment_id_subject_id_attendance_date_key UNIQUE (enrollment_id, subject_id, attendance_date);


--
-- Name: daily_attendance daily_attendance_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.daily_attendance
    ADD CONSTRAINT daily_attendance_pkey PRIMARY KEY (id);


--
-- Name: daily_participation daily_participation_enrollment_id_subject_id_participation__key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.daily_participation
    ADD CONSTRAINT daily_participation_enrollment_id_subject_id_participation__key UNIQUE (enrollment_id, subject_id, participation_date);


--
-- Name: daily_participation daily_participation_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.daily_participation
    ADD CONSTRAINT daily_participation_pkey PRIMARY KEY (id);


--
-- Name: enrollment_books enrollment_books_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.enrollment_books
    ADD CONSTRAINT enrollment_books_pkey PRIMARY KEY (book_id);


--
-- Name: enrollment_documents enrollment_documents_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.enrollment_documents
    ADD CONSTRAINT enrollment_documents_pkey PRIMARY KEY (doc_id);


--
-- Name: enrollment_history enrollment_history_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.enrollment_history
    ADD CONSTRAINT enrollment_history_pkey PRIMARY KEY (id);


--
-- Name: enrollment_uniforms enrollment_uniforms_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.enrollment_uniforms
    ADD CONSTRAINT enrollment_uniforms_pkey PRIMARY KEY (uniform_id);


--
-- Name: enrollments enrollments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.enrollments
    ADD CONSTRAINT enrollments_pkey PRIMARY KEY (enrollment_id);


--
-- Name: exam_answers exam_answers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.exam_answers
    ADD CONSTRAINT exam_answers_pkey PRIMARY KEY (answer_id);


--
-- Name: exam_questions exam_questions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.exam_questions
    ADD CONSTRAINT exam_questions_pkey PRIMARY KEY (question_id);


--
-- Name: exam_results exam_results_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.exam_results
    ADD CONSTRAINT exam_results_pkey PRIMARY KEY (result_id);


--
-- Name: exam_student_permissions exam_student_permissions_exam_id_enrollment_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.exam_student_permissions
    ADD CONSTRAINT exam_student_permissions_exam_id_enrollment_id_key UNIQUE (exam_id, enrollment_id);


--
-- Name: exam_student_permissions exam_student_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.exam_student_permissions
    ADD CONSTRAINT exam_student_permissions_pkey PRIMARY KEY (permission_id);


--
-- Name: exam_tab_switches exam_tab_switches_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.exam_tab_switches
    ADD CONSTRAINT exam_tab_switches_pkey PRIMARY KEY (id);


--
-- Name: exams exams_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.exams
    ADD CONSTRAINT exams_pkey PRIMARY KEY (exam_id);


--
-- Name: failed_logins failed_logins_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.failed_logins
    ADD CONSTRAINT failed_logins_pkey PRIMARY KEY (id);


--
-- Name: finalized_grades finalized_grades_enrollment_id_subject_id_grading_period_ye_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.finalized_grades
    ADD CONSTRAINT finalized_grades_enrollment_id_subject_id_grading_period_ye_key UNIQUE (enrollment_id, subject_id, grading_period, year_id);


--
-- Name: finalized_grades finalized_grades_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.finalized_grades
    ADD CONSTRAINT finalized_grades_pkey PRIMARY KEY (id);


--
-- Name: grade_levels grade_levels_name_branch_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.grade_levels
    ADD CONSTRAINT grade_levels_name_branch_key UNIQUE (name, branch_id);


--
-- Name: grade_levels grade_levels_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.grade_levels
    ADD CONSTRAINT grade_levels_pkey PRIMARY KEY (id);


--
-- Name: grade_overrides grade_overrides_enrollment_id_subject_id_grading_period_yea_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.grade_overrides
    ADD CONSTRAINT grade_overrides_enrollment_id_subject_id_grading_period_yea_key UNIQUE (enrollment_id, subject_id, grading_period, year_id);


--
-- Name: grade_overrides grade_overrides_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.grade_overrides
    ADD CONSTRAINT grade_overrides_pkey PRIMARY KEY (id);


--
-- Name: grade_submission_requests grade_submission_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.grade_submission_requests
    ADD CONSTRAINT grade_submission_requests_pkey PRIMARY KEY (id);


--
-- Name: grade_submission_requests grade_submission_requests_section_id_subject_id_grading_per_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.grade_submission_requests
    ADD CONSTRAINT grade_submission_requests_section_id_subject_id_grading_per_key UNIQUE (section_id, subject_id, grading_period, year_id);


--
-- Name: grading_period_ranges grading_period_ranges_branch_id_year_id_period_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.grading_period_ranges
    ADD CONSTRAINT grading_period_ranges_branch_id_year_id_period_name_key UNIQUE (branch_id, year_id, period_name);


--
-- Name: grading_period_ranges grading_period_ranges_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.grading_period_ranges
    ADD CONSTRAINT grading_period_ranges_pkey PRIMARY KEY (id);


--
-- Name: grading_weights grading_weights_full_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.grading_weights
    ADD CONSTRAINT grading_weights_full_unique UNIQUE (teacher_id, section_id, subject_id, grading_period, year_id);


--
-- Name: grading_weights grading_weights_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.grading_weights
    ADD CONSTRAINT grading_weights_pkey PRIMARY KEY (id);


--
-- Name: grading_weights grading_weights_teacher_id_section_id_subject_id_grading_pe_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.grading_weights
    ADD CONSTRAINT grading_weights_teacher_id_section_id_subject_id_grading_pe_key UNIQUE (teacher_id, section_id, subject_id, grading_period);


--
-- Name: holidays holidays_branch_id_year_id_holiday_date_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.holidays
    ADD CONSTRAINT holidays_branch_id_year_id_holiday_date_key UNIQUE (branch_id, year_id, holiday_date);


--
-- Name: holidays holidays_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.holidays
    ADD CONSTRAINT holidays_pkey PRIMARY KEY (id);


--
-- Name: individual_extensions individual_extensions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.individual_extensions
    ADD CONSTRAINT individual_extensions_pkey PRIMARY KEY (extension_id);


--
-- Name: inventory_item_sizes inventory_item_sizes_item_id_size_label_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inventory_item_sizes
    ADD CONSTRAINT inventory_item_sizes_item_id_size_label_key UNIQUE (item_id, size_label);


--
-- Name: inventory_item_sizes inventory_item_sizes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inventory_item_sizes
    ADD CONSTRAINT inventory_item_sizes_pkey PRIMARY KEY (size_id);


--
-- Name: inventory_items inventory_items_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inventory_items
    ADD CONSTRAINT inventory_items_pkey PRIMARY KEY (item_id);


--
-- Name: inventory_sizes inventory_sizes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inventory_sizes
    ADD CONSTRAINT inventory_sizes_pkey PRIMARY KEY (size_id);


--
-- Name: login_2fa_tokens login_2fa_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.login_2fa_tokens
    ADD CONSTRAINT login_2fa_tokens_pkey PRIMARY KEY (token_id);


--
-- Name: login_2fa_tokens login_2fa_tokens_token_hash_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.login_2fa_tokens
    ADD CONSTRAINT login_2fa_tokens_token_hash_key UNIQUE (token_hash);


--
-- Name: parent_notifications parent_notifications_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parent_notifications
    ADD CONSTRAINT parent_notifications_pkey PRIMARY KEY (notif_id);


--
-- Name: parent_student parent_student_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parent_student
    ADD CONSTRAINT parent_student_pkey PRIMARY KEY (id);


--
-- Name: participation_scores participation_scores_enrollment_id_section_id_subject_id_gr_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.participation_scores
    ADD CONSTRAINT participation_scores_enrollment_id_section_id_subject_id_gr_key UNIQUE (enrollment_id, section_id, subject_id, grading_period);


--
-- Name: participation_scores participation_scores_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.participation_scores
    ADD CONSTRAINT participation_scores_pkey PRIMARY KEY (id);


--
-- Name: participation_scores participation_scores_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.participation_scores
    ADD CONSTRAINT participation_scores_unique UNIQUE (enrollment_id, subject_id, grading_period, year_id);


--
-- Name: participation_scores participation_scores_unique_idx; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.participation_scores
    ADD CONSTRAINT participation_scores_unique_idx UNIQUE (enrollment_id, subject_id, grading_period);


--
-- Name: password_reset_tokens password_reset_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.password_reset_tokens
    ADD CONSTRAINT password_reset_tokens_pkey PRIMARY KEY (id);


--
-- Name: password_reset_tokens password_reset_tokens_token_hash_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.password_reset_tokens
    ADD CONSTRAINT password_reset_tokens_token_hash_key UNIQUE (token_hash);


--
-- Name: payments payments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_pkey PRIMARY KEY (payment_id);


--
-- Name: payments payments_receipt_number_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_receipt_number_key UNIQUE (receipt_number);


--
-- Name: posted_grades posted_grades_enrollment_id_subject_id_grading_period_year_id_k; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.posted_grades
    ADD CONSTRAINT posted_grades_enrollment_id_subject_id_grading_period_year_id_k UNIQUE (enrollment_id, subject_id, grading_period, year_id);


--
-- Name: posted_grades posted_grades_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.posted_grades
    ADD CONSTRAINT posted_grades_pkey PRIMARY KEY (id);


--
-- Name: posted_grades posted_grades_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.posted_grades
    ADD CONSTRAINT posted_grades_unique UNIQUE (enrollment_id, subject_id, grading_period, year_id);


--
-- Name: reservation_items reservation_items_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reservation_items
    ADD CONSTRAINT reservation_items_pkey PRIMARY KEY (reservation_item_id);


--
-- Name: reservations reservations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reservations
    ADD CONSTRAINT reservations_pkey PRIMARY KEY (reservation_id);


--
-- Name: schedules schedules_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schedules
    ADD CONSTRAINT schedules_pkey PRIMARY KEY (schedule_id);


--
-- Name: school_years school_years_branch_label_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.school_years
    ADD CONSTRAINT school_years_branch_label_unique UNIQUE (branch_id, label);


--
-- Name: school_years school_years_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.school_years
    ADD CONSTRAINT school_years_pkey PRIMARY KEY (year_id);


--
-- Name: section_teachers section_teachers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.section_teachers
    ADD CONSTRAINT section_teachers_pkey PRIMARY KEY (id);


--
-- Name: sections sections_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sections
    ADD CONSTRAINT sections_pkey PRIMARY KEY (section_id);


--
-- Name: shs_elective_offerings shs_elective_offerings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shs_elective_offerings
    ADD CONSTRAINT shs_elective_offerings_pkey PRIMARY KEY (offering_id);


--
-- Name: shs_pathways shs_pathways_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shs_pathways
    ADD CONSTRAINT shs_pathways_pkey PRIMARY KEY (pathway_id);


--
-- Name: shs_selection_periods shs_selection_periods_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shs_selection_periods
    ADD CONSTRAINT shs_selection_periods_pkey PRIMARY KEY (period_id);


--
-- Name: shs_student_elective_items shs_student_elective_items_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shs_student_elective_items
    ADD CONSTRAINT shs_student_elective_items_pkey PRIMARY KEY (item_id);


--
-- Name: shs_student_elective_memberships shs_student_elective_memberships_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shs_student_elective_memberships
    ADD CONSTRAINT shs_student_elective_memberships_pkey PRIMARY KEY (membership_id);


--
-- Name: shs_student_elective_requests shs_student_elective_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shs_student_elective_requests
    ADD CONSTRAINT shs_student_elective_requests_pkey PRIMARY KEY (request_id);


--
-- Name: student_accounts student_accounts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_accounts
    ADD CONSTRAINT student_accounts_pkey PRIMARY KEY (account_id);


--
-- Name: student_accounts student_accounts_username_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_accounts
    ADD CONSTRAINT student_accounts_username_key UNIQUE (username);


--
-- Name: student_notifications student_notifications_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_notifications
    ADD CONSTRAINT student_notifications_pkey PRIMARY KEY (id);


--
-- Name: subjects subjects_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subjects
    ADD CONSTRAINT subjects_name_key UNIQUE (name);


--
-- Name: subjects subjects_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subjects
    ADD CONSTRAINT subjects_pkey PRIMARY KEY (subject_id);


--
-- Name: swafo_discipline_log swafo_discipline_log_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.swafo_discipline_log
    ADD CONSTRAINT swafo_discipline_log_pkey PRIMARY KEY (log_id);


--
-- Name: swafo_parent_conferences swafo_parent_conferences_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.swafo_parent_conferences
    ADD CONSTRAINT swafo_parent_conferences_pkey PRIMARY KEY (conference_id);


--
-- Name: swafo_records swafo_records_enrollment_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.swafo_records
    ADD CONSTRAINT swafo_records_enrollment_id_key UNIQUE (enrollment_id);


--
-- Name: swafo_records swafo_records_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.swafo_records
    ADD CONSTRAINT swafo_records_pkey PRIMARY KEY (record_id);


--
-- Name: system_settings system_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.system_settings
    ADD CONSTRAINT system_settings_pkey PRIMARY KEY (setting_key);


--
-- Name: teacher_announcements teacher_announcements_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teacher_announcements
    ADD CONSTRAINT teacher_announcements_pkey PRIMARY KEY (announcement_id);


--
-- Name: teacher_grade_levels teacher_grade_levels_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teacher_grade_levels
    ADD CONSTRAINT teacher_grade_levels_pkey PRIMARY KEY (id);


--
-- Name: teacher_grade_levels teacher_grade_levels_teacher_id_grade_level_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teacher_grade_levels
    ADD CONSTRAINT teacher_grade_levels_teacher_id_grade_level_id_key UNIQUE (teacher_id, grade_level_id);


--
-- Name: uniform_order_items uniform_order_items_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.uniform_order_items
    ADD CONSTRAINT uniform_order_items_pkey PRIMARY KEY (item_id);


--
-- Name: uniform_orders uniform_orders_order_number_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.uniform_orders
    ADD CONSTRAINT uniform_orders_order_number_key UNIQUE (order_number);


--
-- Name: uniform_orders uniform_orders_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.uniform_orders
    ADD CONSTRAINT uniform_orders_pkey PRIMARY KEY (order_id);


--
-- Name: parent_student unique_parent_student; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parent_student
    ADD CONSTRAINT unique_parent_student UNIQUE (parent_id, student_id);


--
-- Name: attendance_scores uq_attendance; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.attendance_scores
    ADD CONSTRAINT uq_attendance UNIQUE (enrollment_id, section_id, subject_id, grading_period);


--
-- Name: shs_selection_periods uq_branch_term_selection; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shs_selection_periods
    ADD CONSTRAINT uq_branch_term_selection UNIQUE (branch_id, year_id, term_name);


--
-- Name: shs_pathways uq_branch_track_pathway; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shs_pathways
    ADD CONSTRAINT uq_branch_track_pathway UNIQUE (branch_id, track_name, pathway_name);


--
-- Name: individual_extensions uq_extension; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.individual_extensions
    ADD CONSTRAINT uq_extension UNIQUE (enrollment_id, item_type, item_id);


--
-- Name: grading_weights uq_grading_weights; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.grading_weights
    ADD CONSTRAINT uq_grading_weights UNIQUE (section_id, subject_id, grading_period);


--
-- Name: participation_scores uq_participation; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.participation_scores
    ADD CONSTRAINT uq_participation UNIQUE (enrollment_id, section_id, subject_id, grading_period);


--
-- Name: shs_elective_offerings uq_section_teacher_term; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shs_elective_offerings
    ADD CONSTRAINT uq_section_teacher_term UNIQUE (section_teacher_id, term_name);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (user_id);


--
-- Name: users users_username_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_username_key UNIQUE (username);


--
-- Name: branches_branch_code_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX branches_branch_code_key ON public.branches USING btree (branch_code) WHERE (branch_code IS NOT NULL);


--
-- Name: idx_act_grades_activity; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_act_grades_activity ON public.activity_grades USING btree (activity_id);


--
-- Name: idx_act_grades_student; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_act_grades_student ON public.activity_grades USING btree (student_id);


--
-- Name: idx_act_grades_submission; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_act_grades_submission ON public.activity_grades USING btree (submission_id);


--
-- Name: idx_activities_period; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_activities_period ON public.activities USING btree (grading_period);


--
-- Name: idx_activities_sec_subj_p; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_activities_sec_subj_p ON public.activities USING btree (section_id, subject_id, grading_period);


--
-- Name: idx_activities_section; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_activities_section ON public.activities USING btree (section_id);


--
-- Name: idx_activities_subject; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_activities_subject ON public.activities USING btree (subject_id);


--
-- Name: idx_attend_scores_enroll; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_attend_scores_enroll ON public.attendance_scores USING btree (enrollment_id);


--
-- Name: idx_attend_scores_period; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_attend_scores_period ON public.attendance_scores USING btree (grading_period);


--
-- Name: idx_attend_scores_section; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_attend_scores_section ON public.attendance_scores USING btree (section_id);


--
-- Name: idx_audit_logs_action; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_logs_action ON public.audit_logs USING btree (action);


--
-- Name: idx_audit_logs_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_logs_created ON public.audit_logs USING btree (created_at DESC);


--
-- Name: idx_billing_branch_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_billing_branch_id ON public.billing USING btree (branch_id);


--
-- Name: idx_billing_enrollment_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_billing_enrollment_id ON public.billing USING btree (enrollment_id);


--
-- Name: idx_billing_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_billing_status ON public.billing USING btree (status);


--
-- Name: idx_enroll_branch_enroll_no; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_enroll_branch_enroll_no ON public.enrollments USING btree (branch_id, branch_enrollment_no);


--
-- Name: idx_enroll_branch_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_enroll_branch_id ON public.enrollments USING btree (branch_id);


--
-- Name: idx_enroll_branch_year; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_enroll_branch_year ON public.enrollments USING btree (branch_id, year_id);


--
-- Name: idx_enroll_branch_year_stat; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_enroll_branch_year_stat ON public.enrollments USING btree (branch_id, year_id, status);


--
-- Name: idx_enroll_docs_enroll_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_enroll_docs_enroll_id ON public.enrollment_documents USING btree (enrollment_id);


--
-- Name: idx_enroll_email; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_enroll_email ON public.enrollments USING btree (lower((email)::text));


--
-- Name: idx_enroll_guardian_email; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_enroll_guardian_email ON public.enrollments USING btree (lower((guardian_email)::text));


--
-- Name: idx_enroll_lrn; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_enroll_lrn ON public.enrollments USING btree (lrn);


--
-- Name: idx_enroll_section_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_enroll_section_id ON public.enrollments USING btree (section_id);


--
-- Name: idx_enroll_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_enroll_status ON public.enrollments USING btree (status);


--
-- Name: idx_enroll_year_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_enroll_year_id ON public.enrollments USING btree (year_id);


--
-- Name: idx_exam_answers_res; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_exam_answers_res ON public.exam_answers USING btree (result_id);


--
-- Name: idx_exam_results_enr; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_exam_results_enr ON public.exam_results USING btree (enrollment_id);


--
-- Name: idx_exam_results_enroll; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_exam_results_enroll ON public.exam_results USING btree (enrollment_id);


--
-- Name: idx_exam_results_exam; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_exam_results_exam ON public.exam_results USING btree (exam_id);


--
-- Name: idx_exams_branch; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_exams_branch ON public.exams USING btree (branch_id);


--
-- Name: idx_exams_period; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_exams_period ON public.exams USING btree (grading_period);


--
-- Name: idx_exams_section; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_exams_section ON public.exams USING btree (section_id);


--
-- Name: idx_exams_section_subj; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_exams_section_subj ON public.exams USING btree (section_id, subject_id);


--
-- Name: idx_exams_teacher; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_exams_teacher ON public.exams USING btree (teacher_id);


--
-- Name: idx_failed_logins_ip; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_failed_logins_ip ON public.failed_logins USING btree (ip_address, created_at DESC);


--
-- Name: idx_grade_sub_section; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_grade_sub_section ON public.grade_submission_requests USING btree (section_id, subject_id);


--
-- Name: idx_grade_sub_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_grade_sub_status ON public.grade_submission_requests USING btree (status);


--
-- Name: idx_grades_enroll_subj_p; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_grades_enroll_subj_p ON public.posted_grades USING btree (enrollment_id, subject_id, grading_period);


--
-- Name: idx_grades_enrollment_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_grades_enrollment_id ON public.posted_grades USING btree (enrollment_id);


--
-- Name: idx_grades_period; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_grades_period ON public.posted_grades USING btree (grading_period);


--
-- Name: idx_grades_section_subj; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_grades_section_subj ON public.posted_grades USING btree (section_id, subject_id);


--
-- Name: idx_inventory_branch; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_inventory_branch ON public.inventory_items USING btree (branch_id);


--
-- Name: idx_parent_notif_parent_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_parent_notif_parent_id ON public.parent_notifications USING btree (parent_id);


--
-- Name: idx_parent_notif_student_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_parent_notif_student_id ON public.parent_notifications USING btree (student_id);


--
-- Name: idx_parent_student_parent; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_parent_student_parent ON public.parent_student USING btree (parent_id);


--
-- Name: idx_parent_student_student; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_parent_student_student ON public.parent_student USING btree (student_id);


--
-- Name: idx_payments_bill_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_payments_bill_id ON public.payments USING btree (bill_id);


--
-- Name: idx_payments_branch_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_payments_branch_id ON public.payments USING btree (branch_id);


--
-- Name: idx_payments_enrollment_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_payments_enrollment_id ON public.payments USING btree (enrollment_id);


--
-- Name: idx_reservations_branch; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_reservations_branch ON public.reservations USING btree (branch_id);


--
-- Name: idx_reservations_student; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_reservations_student ON public.reservations USING btree (student_user_id);


--
-- Name: idx_school_years_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_school_years_active ON public.school_years USING btree (branch_id, is_active);


--
-- Name: idx_school_years_branch; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_school_years_branch ON public.school_years USING btree (branch_id);


--
-- Name: idx_sec_teachers_section; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sec_teachers_section ON public.section_teachers USING btree (section_id);


--
-- Name: idx_sec_teachers_teacher; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sec_teachers_teacher ON public.section_teachers USING btree (teacher_id);


--
-- Name: idx_sections_branch_year; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sections_branch_year ON public.sections USING btree (branch_id, year_id);


--
-- Name: idx_shs_pathways_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_shs_pathways_active ON public.shs_pathways USING btree (branch_id, is_active);


--
-- Name: idx_shs_pathways_branch; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_shs_pathways_branch ON public.shs_pathways USING btree (branch_id);


--
-- Name: idx_stud_acct_enrollment; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_stud_acct_enrollment ON public.student_accounts USING btree (enrollment_id);


--
-- Name: idx_stud_acct_username; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_stud_acct_username ON public.student_accounts USING btree (lower((username)::text));


--
-- Name: idx_stud_notif_is_read; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_stud_notif_is_read ON public.student_notifications USING btree (student_id, is_read);


--
-- Name: idx_stud_notif_student_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_stud_notif_student_id ON public.student_notifications USING btree (student_id);


--
-- Name: idx_swafo_discipline_branch; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_swafo_discipline_branch ON public.swafo_discipline_log USING btree (branch_id);


--
-- Name: idx_swafo_discipline_enrollment; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_swafo_discipline_enrollment ON public.swafo_discipline_log USING btree (enrollment_id);


--
-- Name: idx_users_branch_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_branch_id ON public.users USING btree (branch_id);


--
-- Name: idx_users_email; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_email ON public.users USING btree (lower((email)::text));


--
-- Name: idx_users_role; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_role ON public.users USING btree (role);


--
-- Name: idx_users_role_branch; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_role_branch ON public.users USING btree (role, branch_id);


--
-- Name: idx_users_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_status ON public.users USING btree (status);


--
-- Name: idx_users_username; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_username ON public.users USING btree (lower((username)::text));


--
-- Name: unique_year_per_branch; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX unique_year_per_branch ON public.school_years USING btree (branch_id, label);


--
-- Name: activity_grades activity_grades_activity_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.activity_grades
    ADD CONSTRAINT activity_grades_activity_id_fkey FOREIGN KEY (activity_id) REFERENCES public.activities(activity_id) ON DELETE CASCADE;


--
-- Name: activity_grades activity_grades_submission_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.activity_grades
    ADD CONSTRAINT activity_grades_submission_id_fkey FOREIGN KEY (submission_id) REFERENCES public.activity_submissions(submission_id) ON DELETE CASCADE;


--
-- Name: activity_submissions activity_submissions_activity_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.activity_submissions
    ADD CONSTRAINT activity_submissions_activity_id_fkey FOREIGN KEY (activity_id) REFERENCES public.activities(activity_id) ON DELETE CASCADE;


--
-- Name: activity_submissions activity_submissions_enrollment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.activity_submissions
    ADD CONSTRAINT activity_submissions_enrollment_id_fkey FOREIGN KEY (enrollment_id) REFERENCES public.enrollments(enrollment_id) ON DELETE CASCADE;


--
-- Name: attendance_scores attendance_scores_enrollment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.attendance_scores
    ADD CONSTRAINT attendance_scores_enrollment_id_fkey FOREIGN KEY (enrollment_id) REFERENCES public.enrollments(enrollment_id) ON DELETE CASCADE;


--
-- Name: attendance_scores attendance_scores_section_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.attendance_scores
    ADD CONSTRAINT attendance_scores_section_id_fkey FOREIGN KEY (section_id) REFERENCES public.sections(section_id) ON DELETE CASCADE;


--
-- Name: attendance_scores attendance_scores_subject_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.attendance_scores
    ADD CONSTRAINT attendance_scores_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES public.subjects(subject_id) ON DELETE CASCADE;


--
-- Name: billing billing_branch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.billing
    ADD CONSTRAINT billing_branch_id_fkey FOREIGN KEY (branch_id) REFERENCES public.branches(branch_id) ON DELETE CASCADE;


--
-- Name: billing billing_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.billing
    ADD CONSTRAINT billing_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: billing billing_enrollment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.billing
    ADD CONSTRAINT billing_enrollment_id_fkey FOREIGN KEY (enrollment_id) REFERENCES public.enrollments(enrollment_id) ON DELETE CASCADE;


--
-- Name: enrollment_books enrollment_books_enrollment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.enrollment_books
    ADD CONSTRAINT enrollment_books_enrollment_id_fkey FOREIGN KEY (enrollment_id) REFERENCES public.enrollments(enrollment_id) ON DELETE CASCADE;


--
-- Name: enrollment_documents enrollment_documents_enrollment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.enrollment_documents
    ADD CONSTRAINT enrollment_documents_enrollment_id_fkey FOREIGN KEY (enrollment_id) REFERENCES public.enrollments(enrollment_id);


--
-- Name: enrollment_uniforms enrollment_uniforms_enrollment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.enrollment_uniforms
    ADD CONSTRAINT enrollment_uniforms_enrollment_id_fkey FOREIGN KEY (enrollment_id) REFERENCES public.enrollments(enrollment_id) ON DELETE CASCADE;


--
-- Name: enrollments enrollments_branch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.enrollments
    ADD CONSTRAINT enrollments_branch_id_fkey FOREIGN KEY (branch_id) REFERENCES public.branches(branch_id);


--
-- Name: enrollments enrollments_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.enrollments
    ADD CONSTRAINT enrollments_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id);


--
-- Name: exam_answers exam_answers_question_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.exam_answers
    ADD CONSTRAINT exam_answers_question_id_fkey FOREIGN KEY (question_id) REFERENCES public.exam_questions(question_id);


--
-- Name: exam_answers exam_answers_result_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.exam_answers
    ADD CONSTRAINT exam_answers_result_id_fkey FOREIGN KEY (result_id) REFERENCES public.exam_results(result_id) ON DELETE CASCADE;


--
-- Name: exam_questions exam_questions_exam_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.exam_questions
    ADD CONSTRAINT exam_questions_exam_id_fkey FOREIGN KEY (exam_id) REFERENCES public.exams(exam_id) ON DELETE CASCADE;


--
-- Name: exam_results exam_results_enrollment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.exam_results
    ADD CONSTRAINT exam_results_enrollment_id_fkey FOREIGN KEY (enrollment_id) REFERENCES public.enrollments(enrollment_id) ON DELETE CASCADE;


--
-- Name: exam_results exam_results_exam_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.exam_results
    ADD CONSTRAINT exam_results_exam_id_fkey FOREIGN KEY (exam_id) REFERENCES public.exams(exam_id) ON DELETE CASCADE;


--
-- Name: exam_student_permissions exam_student_permissions_enrollment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.exam_student_permissions
    ADD CONSTRAINT exam_student_permissions_enrollment_id_fkey FOREIGN KEY (enrollment_id) REFERENCES public.enrollments(enrollment_id) ON DELETE CASCADE;


--
-- Name: exam_student_permissions exam_student_permissions_exam_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.exam_student_permissions
    ADD CONSTRAINT exam_student_permissions_exam_id_fkey FOREIGN KEY (exam_id) REFERENCES public.exams(exam_id) ON DELETE CASCADE;


--
-- Name: exam_tab_switches exam_tab_switches_result_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.exam_tab_switches
    ADD CONSTRAINT exam_tab_switches_result_id_fkey FOREIGN KEY (result_id) REFERENCES public.exam_results(result_id) ON DELETE CASCADE;


--
-- Name: exams exams_branch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.exams
    ADD CONSTRAINT exams_branch_id_fkey FOREIGN KEY (branch_id) REFERENCES public.branches(branch_id);


--
-- Name: exams exams_section_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.exams
    ADD CONSTRAINT exams_section_id_fkey FOREIGN KEY (section_id) REFERENCES public.sections(section_id);


--
-- Name: exams exams_subject_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.exams
    ADD CONSTRAINT exams_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES public.subjects(subject_id);


--
-- Name: exams exams_teacher_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.exams
    ADD CONSTRAINT exams_teacher_id_fkey FOREIGN KEY (teacher_id) REFERENCES public.users(user_id);


--
-- Name: chatbot_faqs fk_chatbot_branch; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chatbot_faqs
    ADD CONSTRAINT fk_chatbot_branch FOREIGN KEY (branch_id) REFERENCES public.branches(branch_id) ON DELETE CASCADE;


--
-- Name: enrollments fk_enrollments_year; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.enrollments
    ADD CONSTRAINT fk_enrollments_year FOREIGN KEY (year_id) REFERENCES public.school_years(year_id);


--
-- Name: school_years fk_school_year_branch; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.school_years
    ADD CONSTRAINT fk_school_year_branch FOREIGN KEY (branch_id) REFERENCES public.branches(branch_id);


--
-- Name: sections fk_sections_year; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sections
    ADD CONSTRAINT fk_sections_year FOREIGN KEY (year_id) REFERENCES public.school_years(year_id);


--
-- Name: grade_overrides grade_overrides_enrollment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.grade_overrides
    ADD CONSTRAINT grade_overrides_enrollment_id_fkey FOREIGN KEY (enrollment_id) REFERENCES public.enrollments(enrollment_id) ON DELETE CASCADE;


--
-- Name: grade_submission_requests grade_submission_requests_admin_approved_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.grade_submission_requests
    ADD CONSTRAINT grade_submission_requests_admin_approved_by_fkey FOREIGN KEY (admin_approved_by) REFERENCES public.users(user_id);


--
-- Name: grade_submission_requests grade_submission_requests_registrar_approved_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.grade_submission_requests
    ADD CONSTRAINT grade_submission_requests_registrar_approved_by_fkey FOREIGN KEY (registrar_approved_by) REFERENCES public.users(user_id);


--
-- Name: grade_submission_requests grade_submission_requests_rejected_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.grade_submission_requests
    ADD CONSTRAINT grade_submission_requests_rejected_by_fkey FOREIGN KEY (rejected_by) REFERENCES public.users(user_id);


--
-- Name: grade_submission_requests grade_submission_requests_section_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.grade_submission_requests
    ADD CONSTRAINT grade_submission_requests_section_id_fkey FOREIGN KEY (section_id) REFERENCES public.sections(section_id) ON DELETE CASCADE;


--
-- Name: grade_submission_requests grade_submission_requests_subject_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.grade_submission_requests
    ADD CONSTRAINT grade_submission_requests_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES public.subjects(subject_id) ON DELETE CASCADE;


--
-- Name: grade_submission_requests grade_submission_requests_submitted_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.grade_submission_requests
    ADD CONSTRAINT grade_submission_requests_submitted_by_fkey FOREIGN KEY (submitted_by) REFERENCES public.users(user_id);


--
-- Name: grading_weights grading_weights_section_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.grading_weights
    ADD CONSTRAINT grading_weights_section_id_fkey FOREIGN KEY (section_id) REFERENCES public.sections(section_id) ON DELETE CASCADE;


--
-- Name: grading_weights grading_weights_subject_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.grading_weights
    ADD CONSTRAINT grading_weights_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES public.subjects(subject_id) ON DELETE CASCADE;


--
-- Name: grading_weights grading_weights_teacher_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.grading_weights
    ADD CONSTRAINT grading_weights_teacher_id_fkey FOREIGN KEY (teacher_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: individual_extensions individual_extensions_enrollment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.individual_extensions
    ADD CONSTRAINT individual_extensions_enrollment_id_fkey FOREIGN KEY (enrollment_id) REFERENCES public.enrollments(enrollment_id) ON DELETE CASCADE;


--
-- Name: inventory_item_sizes inventory_item_sizes_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inventory_item_sizes
    ADD CONSTRAINT inventory_item_sizes_item_id_fkey FOREIGN KEY (item_id) REFERENCES public.inventory_items(item_id) ON DELETE CASCADE;


--
-- Name: inventory_items inventory_items_branch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inventory_items
    ADD CONSTRAINT inventory_items_branch_id_fkey FOREIGN KEY (branch_id) REFERENCES public.branches(branch_id) ON DELETE CASCADE;


--
-- Name: inventory_sizes inventory_sizes_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inventory_sizes
    ADD CONSTRAINT inventory_sizes_item_id_fkey FOREIGN KEY (item_id) REFERENCES public.inventory_items(item_id) ON DELETE CASCADE;


--
-- Name: parent_notifications parent_notifications_parent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parent_notifications
    ADD CONSTRAINT parent_notifications_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: parent_notifications parent_notifications_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parent_notifications
    ADD CONSTRAINT parent_notifications_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.enrollments(enrollment_id) ON DELETE CASCADE;


--
-- Name: parent_student parent_student_parent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parent_student
    ADD CONSTRAINT parent_student_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES public.users(user_id);


--
-- Name: parent_student parent_student_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parent_student
    ADD CONSTRAINT parent_student_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.enrollments(enrollment_id);


--
-- Name: participation_scores participation_scores_enrollment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.participation_scores
    ADD CONSTRAINT participation_scores_enrollment_id_fkey FOREIGN KEY (enrollment_id) REFERENCES public.enrollments(enrollment_id) ON DELETE CASCADE;


--
-- Name: participation_scores participation_scores_section_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.participation_scores
    ADD CONSTRAINT participation_scores_section_id_fkey FOREIGN KEY (section_id) REFERENCES public.sections(section_id) ON DELETE CASCADE;


--
-- Name: participation_scores participation_scores_subject_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.participation_scores
    ADD CONSTRAINT participation_scores_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES public.subjects(subject_id) ON DELETE CASCADE;


--
-- Name: password_reset_tokens password_reset_tokens_student_account_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.password_reset_tokens
    ADD CONSTRAINT password_reset_tokens_student_account_id_fkey FOREIGN KEY (student_account_id) REFERENCES public.student_accounts(account_id) ON DELETE CASCADE;


--
-- Name: password_reset_tokens password_reset_tokens_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.password_reset_tokens
    ADD CONSTRAINT password_reset_tokens_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: payments payments_bill_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_bill_id_fkey FOREIGN KEY (bill_id) REFERENCES public.billing(bill_id) ON DELETE CASCADE;


--
-- Name: payments payments_branch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_branch_id_fkey FOREIGN KEY (branch_id) REFERENCES public.branches(branch_id) ON DELETE CASCADE;


--
-- Name: payments payments_enrollment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_enrollment_id_fkey FOREIGN KEY (enrollment_id) REFERENCES public.enrollments(enrollment_id) ON DELETE CASCADE;


--
-- Name: payments payments_received_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_received_by_fkey FOREIGN KEY (received_by) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: posted_grades posted_grades_enrollment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.posted_grades
    ADD CONSTRAINT posted_grades_enrollment_id_fkey FOREIGN KEY (enrollment_id) REFERENCES public.enrollments(enrollment_id) ON DELETE CASCADE;


--
-- Name: posted_grades posted_grades_posted_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.posted_grades
    ADD CONSTRAINT posted_grades_posted_by_fkey FOREIGN KEY (posted_by) REFERENCES public.users(user_id);


--
-- Name: posted_grades posted_grades_section_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.posted_grades
    ADD CONSTRAINT posted_grades_section_id_fkey FOREIGN KEY (section_id) REFERENCES public.sections(section_id) ON DELETE CASCADE;


--
-- Name: posted_grades posted_grades_subject_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.posted_grades
    ADD CONSTRAINT posted_grades_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES public.subjects(subject_id) ON DELETE CASCADE;


--
-- Name: reservation_items reservation_items_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reservation_items
    ADD CONSTRAINT reservation_items_item_id_fkey FOREIGN KEY (item_id) REFERENCES public.inventory_items(item_id);


--
-- Name: reservation_items reservation_items_reservation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reservation_items
    ADD CONSTRAINT reservation_items_reservation_id_fkey FOREIGN KEY (reservation_id) REFERENCES public.reservations(reservation_id) ON DELETE CASCADE;


--
-- Name: reservations reservations_branch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reservations
    ADD CONSTRAINT reservations_branch_id_fkey FOREIGN KEY (branch_id) REFERENCES public.branches(branch_id) ON DELETE CASCADE;


--
-- Name: reservations reservations_reserved_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reservations
    ADD CONSTRAINT reservations_reserved_by_user_id_fkey FOREIGN KEY (reserved_by_user_id) REFERENCES public.users(user_id);


--
-- Name: reservations reservations_student_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reservations
    ADD CONSTRAINT reservations_student_user_id_fkey FOREIGN KEY (student_user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: schedules schedules_branch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schedules
    ADD CONSTRAINT schedules_branch_id_fkey FOREIGN KEY (branch_id) REFERENCES public.branches(branch_id);


--
-- Name: schedules schedules_school_year_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schedules
    ADD CONSTRAINT schedules_school_year_id_fkey FOREIGN KEY (year_id) REFERENCES public.school_years(year_id);


--
-- Name: schedules schedules_section_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schedules
    ADD CONSTRAINT schedules_section_id_fkey FOREIGN KEY (section_id) REFERENCES public.sections(section_id);


--
-- Name: schedules schedules_subject_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schedules
    ADD CONSTRAINT schedules_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES public.subjects(subject_id);


--
-- Name: schedules schedules_teacher_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schedules
    ADD CONSTRAINT schedules_teacher_id_fkey FOREIGN KEY (teacher_id) REFERENCES public.users(user_id);


--
-- Name: sections sections_branch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sections
    ADD CONSTRAINT sections_branch_id_fkey FOREIGN KEY (branch_id) REFERENCES public.branches(branch_id) ON DELETE CASCADE;


--
-- Name: shs_elective_offerings shs_elective_offerings_branch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shs_elective_offerings
    ADD CONSTRAINT shs_elective_offerings_branch_id_fkey FOREIGN KEY (branch_id) REFERENCES public.branches(branch_id) ON DELETE CASCADE;


--
-- Name: shs_elective_offerings shs_elective_offerings_section_teacher_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shs_elective_offerings
    ADD CONSTRAINT shs_elective_offerings_section_teacher_id_fkey FOREIGN KEY (section_teacher_id) REFERENCES public.section_teachers(id) ON DELETE CASCADE;


--
-- Name: shs_elective_offerings shs_elective_offerings_year_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shs_elective_offerings
    ADD CONSTRAINT shs_elective_offerings_year_id_fkey FOREIGN KEY (year_id) REFERENCES public.school_years(year_id) ON DELETE CASCADE;


--
-- Name: shs_pathways shs_pathways_branch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shs_pathways
    ADD CONSTRAINT shs_pathways_branch_id_fkey FOREIGN KEY (branch_id) REFERENCES public.branches(branch_id) ON DELETE CASCADE;


--
-- Name: shs_selection_periods shs_selection_periods_branch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shs_selection_periods
    ADD CONSTRAINT shs_selection_periods_branch_id_fkey FOREIGN KEY (branch_id) REFERENCES public.branches(branch_id) ON DELETE CASCADE;


--
-- Name: shs_selection_periods shs_selection_periods_year_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shs_selection_periods
    ADD CONSTRAINT shs_selection_periods_year_id_fkey FOREIGN KEY (year_id) REFERENCES public.school_years(year_id) ON DELETE CASCADE;


--
-- Name: shs_student_elective_items shs_student_elective_items_offering_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shs_student_elective_items
    ADD CONSTRAINT shs_student_elective_items_offering_id_fkey FOREIGN KEY (offering_id) REFERENCES public.shs_elective_offerings(offering_id) ON DELETE CASCADE;


--
-- Name: shs_student_elective_items shs_student_elective_items_request_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shs_student_elective_items
    ADD CONSTRAINT shs_student_elective_items_request_id_fkey FOREIGN KEY (request_id) REFERENCES public.shs_student_elective_requests(request_id) ON DELETE CASCADE;


--
-- Name: shs_student_elective_memberships shs_student_elective_memberships_enrollment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shs_student_elective_memberships
    ADD CONSTRAINT shs_student_elective_memberships_enrollment_id_fkey FOREIGN KEY (enrollment_id) REFERENCES public.enrollments(enrollment_id) ON DELETE CASCADE;


--
-- Name: shs_student_elective_memberships shs_student_elective_memberships_offering_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shs_student_elective_memberships
    ADD CONSTRAINT shs_student_elective_memberships_offering_id_fkey FOREIGN KEY (offering_id) REFERENCES public.shs_elective_offerings(offering_id) ON DELETE CASCADE;


--
-- Name: shs_student_elective_memberships shs_student_elective_memberships_student_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shs_student_elective_memberships
    ADD CONSTRAINT shs_student_elective_memberships_student_user_id_fkey FOREIGN KEY (student_user_id) REFERENCES public.users(user_id);


--
-- Name: shs_student_elective_memberships shs_student_elective_memberships_year_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shs_student_elective_memberships
    ADD CONSTRAINT shs_student_elective_memberships_year_id_fkey FOREIGN KEY (year_id) REFERENCES public.school_years(year_id) ON DELETE CASCADE;


--
-- Name: shs_student_elective_requests shs_student_elective_requests_enrollment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shs_student_elective_requests
    ADD CONSTRAINT shs_student_elective_requests_enrollment_id_fkey FOREIGN KEY (enrollment_id) REFERENCES public.enrollments(enrollment_id) ON DELETE CASCADE;


--
-- Name: shs_student_elective_requests shs_student_elective_requests_reviewed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shs_student_elective_requests
    ADD CONSTRAINT shs_student_elective_requests_reviewed_by_fkey FOREIGN KEY (reviewed_by) REFERENCES public.users(user_id);


--
-- Name: shs_student_elective_requests shs_student_elective_requests_student_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.shs_student_elective_requests
    ADD CONSTRAINT shs_student_elective_requests_student_user_id_fkey FOREIGN KEY (student_user_id) REFERENCES public.users(user_id);


--
-- Name: student_accounts student_accounts_branch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_accounts
    ADD CONSTRAINT student_accounts_branch_id_fkey FOREIGN KEY (branch_id) REFERENCES public.branches(branch_id);


--
-- Name: student_accounts student_accounts_enrollment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_accounts
    ADD CONSTRAINT student_accounts_enrollment_id_fkey FOREIGN KEY (enrollment_id) REFERENCES public.enrollments(enrollment_id) ON DELETE CASCADE;


--
-- Name: student_notifications student_notifications_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_notifications
    ADD CONSTRAINT student_notifications_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: subjects subjects_prerequisite_subject_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subjects
    ADD CONSTRAINT subjects_prerequisite_subject_id_fkey FOREIGN KEY (prerequisite_subject_id) REFERENCES public.subjects(subject_id) ON DELETE SET NULL;


--
-- Name: swafo_discipline_log swafo_discipline_log_enrollment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.swafo_discipline_log
    ADD CONSTRAINT swafo_discipline_log_enrollment_id_fkey FOREIGN KEY (enrollment_id) REFERENCES public.enrollments(enrollment_id) ON DELETE CASCADE;


--
-- Name: swafo_discipline_log swafo_discipline_log_logged_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.swafo_discipline_log
    ADD CONSTRAINT swafo_discipline_log_logged_by_fkey FOREIGN KEY (logged_by) REFERENCES public.users(user_id);


--
-- Name: swafo_discipline_log swafo_discipline_log_reported_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.swafo_discipline_log
    ADD CONSTRAINT swafo_discipline_log_reported_by_fkey FOREIGN KEY (reported_by) REFERENCES public.users(user_id);


--
-- Name: swafo_discipline_log swafo_discipline_log_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.swafo_discipline_log
    ADD CONSTRAINT swafo_discipline_log_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: swafo_parent_conferences swafo_parent_conferences_discipline_log_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.swafo_parent_conferences
    ADD CONSTRAINT swafo_parent_conferences_discipline_log_id_fkey FOREIGN KEY (discipline_log_id) REFERENCES public.swafo_discipline_log(log_id) ON DELETE SET NULL;


--
-- Name: swafo_parent_conferences swafo_parent_conferences_enrollment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.swafo_parent_conferences
    ADD CONSTRAINT swafo_parent_conferences_enrollment_id_fkey FOREIGN KEY (enrollment_id) REFERENCES public.enrollments(enrollment_id) ON DELETE CASCADE;


--
-- Name: swafo_parent_conferences swafo_parent_conferences_scheduled_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.swafo_parent_conferences
    ADD CONSTRAINT swafo_parent_conferences_scheduled_by_fkey FOREIGN KEY (scheduled_by) REFERENCES public.users(user_id) ON DELETE SET NULL;


--
-- Name: swafo_records swafo_records_enrollment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.swafo_records
    ADD CONSTRAINT swafo_records_enrollment_id_fkey FOREIGN KEY (enrollment_id) REFERENCES public.enrollments(enrollment_id) ON DELETE CASCADE;


--
-- Name: swafo_records swafo_records_reviewed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.swafo_records
    ADD CONSTRAINT swafo_records_reviewed_by_fkey FOREIGN KEY (reviewed_by) REFERENCES public.users(user_id);


--
-- Name: swafo_records swafo_records_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.swafo_records
    ADD CONSTRAINT swafo_records_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: teacher_grade_levels teacher_grade_levels_grade_level_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teacher_grade_levels
    ADD CONSTRAINT teacher_grade_levels_grade_level_id_fkey FOREIGN KEY (grade_level_id) REFERENCES public.grade_levels(id) ON DELETE CASCADE;


--
-- Name: teacher_grade_levels teacher_grade_levels_teacher_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teacher_grade_levels
    ADD CONSTRAINT teacher_grade_levels_teacher_id_fkey FOREIGN KEY (teacher_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: uniform_order_items uniform_order_items_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.uniform_order_items
    ADD CONSTRAINT uniform_order_items_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.uniform_orders(order_id) ON DELETE CASCADE;


--
-- Name: uniform_orders uniform_orders_enrollment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.uniform_orders
    ADD CONSTRAINT uniform_orders_enrollment_id_fkey FOREIGN KEY (enrollment_id) REFERENCES public.enrollments(enrollment_id) ON DELETE CASCADE;


--
-- Name: users users_branch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_branch_id_fkey FOREIGN KEY (branch_id) REFERENCES public.branches(branch_id);


--
-- PostgreSQL database dump complete
--

\unrestrict jkAStvQ7WoGuVFIipKGRuFlOll2KIwwVNaXJCUggmgI1LUAdDdy2TgMZf2P4U2m

