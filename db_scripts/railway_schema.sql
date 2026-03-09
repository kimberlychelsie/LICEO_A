-- ============================================================
-- LICEO_A Railway Schema
-- Run this in Railway: Postgres → Database → Query tab
-- ============================================================

-- Sequences
CREATE SEQUENCE IF NOT EXISTS announcements_announcement_id_seq;
CREATE SEQUENCE IF NOT EXISTS billing_bill_id_seq;
CREATE SEQUENCE IF NOT EXISTS branches_branch_id_seq;
CREATE SEQUENCE IF NOT EXISTS chatbot_faqs_id_seq;
CREATE SEQUENCE IF NOT EXISTS enrollment_books_book_id_seq;
CREATE SEQUENCE IF NOT EXISTS enrollment_documents_doc_id_seq;
CREATE SEQUENCE IF NOT EXISTS enrollment_uniforms_uniform_id_seq;
CREATE SEQUENCE IF NOT EXISTS enrollments_enrollment_id_seq;
CREATE SEQUENCE IF NOT EXISTS inventory_item_sizes_size_id_seq;
CREATE SEQUENCE IF NOT EXISTS inventory_items_item_id_seq;
CREATE SEQUENCE IF NOT EXISTS inventory_sizes_size_id_seq;
CREATE SEQUENCE IF NOT EXISTS parent_student_id_seq;
CREATE SEQUENCE IF NOT EXISTS payments_payment_id_seq;
CREATE SEQUENCE IF NOT EXISTS reservation_items_reservation_item_id_seq;
CREATE SEQUENCE IF NOT EXISTS reservations_reservation_id_seq;
CREATE SEQUENCE IF NOT EXISTS student_accounts_account_id_seq;
CREATE SEQUENCE IF NOT EXISTS users_user_id_seq;
CREATE SEQUENCE IF NOT EXISTS grade_levels_id_seq;
CREATE SEQUENCE IF NOT EXISTS sections_id_seq;
CREATE SEQUENCE IF NOT EXISTS teacher_section_assignments_id_seq;

-- ── branches (must be first — others depend on it) ──────────
CREATE TABLE IF NOT EXISTS public.branches (
    branch_id   integer NOT NULL DEFAULT nextval('branches_branch_id_seq'),
    branch_name character varying(100) NOT NULL,
    location    character varying(100),
    status      character varying(10) DEFAULT 'active',
    created_at  timestamp NOT NULL DEFAULT now(),
    is_active   boolean NOT NULL DEFAULT true,
    CONSTRAINT branches_pkey PRIMARY KEY (branch_id)
);

-- ── users ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.users (
    user_id                 integer NOT NULL DEFAULT nextval('users_user_id_seq'),
    branch_id               integer,
    username                character varying(50) NOT NULL,
    password                character varying(255) NOT NULL,
    role                    character varying(20),
    status                  character varying(10) DEFAULT 'active',
    require_password_change boolean DEFAULT false,
    last_password_change    timestamp,
    CONSTRAINT users_pkey PRIMARY KEY (user_id),
    CONSTRAINT users_username_key UNIQUE (username),
    CONSTRAINT users_branch_id_fkey FOREIGN KEY (branch_id)
        REFERENCES public.branches (branch_id)
);

-- ── enrollments ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.enrollments (
    enrollment_id      integer NOT NULL DEFAULT nextval('enrollments_enrollment_id_seq'),
    student_name       character varying(100) NOT NULL,
    grade_level        character varying(50),
    branch_id          integer NOT NULL,
    status             character varying(20),
    created_at         timestamp NOT NULL DEFAULT now(),
    user_id            integer,
    gender             character varying(20),
    dob                date,
    address            text,
    contact_number     character varying(20),
    guardian_name      character varying(100),
    guardian_contact   character varying(20),
    previous_school    character varying(150),
    branch_enrollment_no integer,
    section_id         integer,
    email              character varying(255),
    guardian_email     character varying(255),
    lrn                character varying(12),
    CONSTRAINT enrollments_pkey PRIMARY KEY (enrollment_id),
    CONSTRAINT uq_enrollments_branch_no UNIQUE (branch_id, branch_enrollment_no),
    CONSTRAINT enrollments_branch_id_fkey FOREIGN KEY (branch_id)
        REFERENCES public.branches (branch_id),
    CONSTRAINT enrollments_user_id_fkey FOREIGN KEY (user_id)
        REFERENCES public.users (user_id)
);

-- ── announcements ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.announcements (
    announcement_id integer NOT NULL DEFAULT nextval('announcements_announcement_id_seq'),
    title           character varying(255) NOT NULL,
    message         text NOT NULL,
    is_active       boolean DEFAULT true,
    created_at      timestamp NOT NULL DEFAULT now(),
    image_url       text,
    branch_id       integer,
    CONSTRAINT announcements_pkey PRIMARY KEY (announcement_id)
);

-- ── billing ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.billing (
    bill_id        integer NOT NULL DEFAULT nextval('billing_bill_id_seq'),
    enrollment_id  integer NOT NULL,
    branch_id      integer NOT NULL,
    tuition_fee    numeric(10,2) DEFAULT 0.00,
    books_fee      numeric(10,2) DEFAULT 0.00,
    uniform_fee    numeric(10,2) DEFAULT 0.00,
    other_fees     numeric(10,2) DEFAULT 0.00,
    total_amount   numeric(10,2) NOT NULL,
    amount_paid    numeric(10,2) DEFAULT 0.00,
    balance        numeric(10,2) NOT NULL,
    status         character varying(10) DEFAULT 'pending',
    created_by     integer NOT NULL,
    created_at     timestamp NOT NULL DEFAULT now(),
    updated_at     timestamp NOT NULL DEFAULT now(),
    CONSTRAINT billing_pkey PRIMARY KEY (bill_id),
    CONSTRAINT billing_branch_id_fkey FOREIGN KEY (branch_id)
        REFERENCES public.branches (branch_id) ON DELETE CASCADE,
    CONSTRAINT billing_created_by_fkey FOREIGN KEY (created_by)
        REFERENCES public.users (user_id) ON DELETE CASCADE,
    CONSTRAINT billing_enrollment_id_fkey FOREIGN KEY (enrollment_id)
        REFERENCES public.enrollments (enrollment_id) ON DELETE CASCADE
);

-- ── chatbot_faqs ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.chatbot_faqs (
    id         integer NOT NULL DEFAULT nextval('chatbot_faqs_id_seq'),
    branch_id  integer,
    question   text NOT NULL,
    answer     text NOT NULL,
    created_at timestamp DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chatbot_faqs_pkey PRIMARY KEY (id),
    CONSTRAINT fk_chatbot_branch FOREIGN KEY (branch_id)
        REFERENCES public.branches (branch_id) ON DELETE CASCADE
);

-- ── enrollment_documents ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.enrollment_documents (
    doc_id        integer NOT NULL DEFAULT nextval('enrollment_documents_doc_id_seq'),
    enrollment_id integer NOT NULL,
    file_name     character varying(255) NOT NULL,
    file_path     character varying(500) NOT NULL,
    uploaded_at   timestamp NOT NULL DEFAULT now(),
    CONSTRAINT enrollment_documents_pkey PRIMARY KEY (doc_id),
    CONSTRAINT enrollment_documents_enrollment_id_fkey FOREIGN KEY (enrollment_id)
        REFERENCES public.enrollments (enrollment_id)
);

-- ── enrollment_books ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.enrollment_books (
    book_id       integer NOT NULL DEFAULT nextval('enrollment_books_book_id_seq'),
    enrollment_id integer NOT NULL,
    book_name     character varying(100) NOT NULL,
    quantity      integer DEFAULT 1,
    created_at    timestamp NOT NULL DEFAULT now(),
    CONSTRAINT enrollment_books_pkey PRIMARY KEY (book_id),
    CONSTRAINT enrollment_books_enrollment_id_fkey FOREIGN KEY (enrollment_id)
        REFERENCES public.enrollments (enrollment_id) ON DELETE CASCADE
);

-- ── enrollment_uniforms ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.enrollment_uniforms (
    uniform_id    integer NOT NULL DEFAULT nextval('enrollment_uniforms_uniform_id_seq'),
    enrollment_id integer NOT NULL,
    uniform_type  character varying(50) NOT NULL,
    size          character varying(10) NOT NULL,
    quantity      integer NOT NULL DEFAULT 1,
    created_at    timestamp NOT NULL DEFAULT now(),
    CONSTRAINT enrollment_uniforms_pkey PRIMARY KEY (uniform_id),
    CONSTRAINT enrollment_uniforms_enrollment_id_fkey FOREIGN KEY (enrollment_id)
        REFERENCES public.enrollments (enrollment_id) ON DELETE CASCADE
);

-- ── inventory_items ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.inventory_items (
    item_id      integer NOT NULL DEFAULT nextval('inventory_items_item_id_seq'),
    branch_id    integer NOT NULL,
    category     text NOT NULL,
    item_name    text NOT NULL,
    grade_level  text,
    is_common    boolean NOT NULL DEFAULT false,
    size_label   text,
    price        numeric(12,2) NOT NULL DEFAULT 0,
    stock_total  integer NOT NULL DEFAULT 0,
    reserved_qty integer NOT NULL DEFAULT 0,
    is_active    boolean NOT NULL DEFAULT true,
    created_at   timestamp NOT NULL DEFAULT now(),
    image_url    text,
    publisher    character varying(100),
    CONSTRAINT inventory_items_pkey PRIMARY KEY (item_id),
    CONSTRAINT inventory_items_branch_id_fkey FOREIGN KEY (branch_id)
        REFERENCES public.branches (branch_id) ON DELETE CASCADE,
    CONSTRAINT inventory_items_category_check CHECK (category = ANY (ARRAY['BOOK'::text, 'UNIFORM'::text]))
);

-- ── inventory_item_sizes ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.inventory_item_sizes (
    size_id      integer NOT NULL DEFAULT nextval('inventory_item_sizes_size_id_seq'),
    item_id      integer NOT NULL,
    size_label   character varying(10) NOT NULL,
    stock_total  integer NOT NULL DEFAULT 0,
    reserved_qty integer NOT NULL DEFAULT 0,
    CONSTRAINT inventory_item_sizes_pkey PRIMARY KEY (size_id),
    CONSTRAINT inventory_item_sizes_item_id_size_label_key UNIQUE (item_id, size_label),
    CONSTRAINT inventory_item_sizes_item_id_fkey FOREIGN KEY (item_id)
        REFERENCES public.inventory_items (item_id) ON DELETE CASCADE
);

-- ── inventory_sizes (legacy) ─────────────────────────────────
CREATE TABLE IF NOT EXISTS public.inventory_sizes (
    size_id      integer NOT NULL DEFAULT nextval('inventory_sizes_size_id_seq'),
    item_id      integer,
    size_label   character varying(10),
    stock_qty    integer DEFAULT 0,
    reserved_qty integer DEFAULT 0,
    CONSTRAINT inventory_sizes_pkey PRIMARY KEY (size_id),
    CONSTRAINT inventory_sizes_item_id_fkey FOREIGN KEY (item_id)
        REFERENCES public.inventory_items (item_id) ON DELETE CASCADE
);

-- ── reservations ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.reservations (
    reservation_id     integer NOT NULL DEFAULT nextval('reservations_reservation_id_seq'),
    student_user_id    integer,
    branch_id          integer NOT NULL,
    student_grade_level text,
    status             text NOT NULL DEFAULT 'RESERVED',
    created_at         timestamp NOT NULL DEFAULT now(),
    paid_at            timestamp,
    claimed_at         timestamp,
    cancelled_at       timestamp,
    reserved_by_user_id integer,
    enrollment_id      integer,
    CONSTRAINT reservations_pkey PRIMARY KEY (reservation_id),
    CONSTRAINT reservations_branch_id_fkey FOREIGN KEY (branch_id)
        REFERENCES public.branches (branch_id) ON DELETE CASCADE,
    CONSTRAINT reservations_reserved_by_user_id_fkey FOREIGN KEY (reserved_by_user_id)
        REFERENCES public.users (user_id),
    CONSTRAINT reservations_student_user_id_fkey FOREIGN KEY (student_user_id)
        REFERENCES public.users (user_id) ON DELETE CASCADE,
    CONSTRAINT reservations_status_check CHECK (status = ANY (ARRAY['RESERVED','PAID','CLAIMED','CANCELLED']))
);

-- ── reservation_items ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.reservation_items (
    reservation_item_id integer NOT NULL DEFAULT nextval('reservation_items_reservation_item_id_seq'),
    reservation_id      integer NOT NULL,
    item_id             integer NOT NULL,
    qty                 integer NOT NULL,
    size_label          text,
    unit_price          numeric(12,2) NOT NULL DEFAULT 0,
    line_total          numeric(12,2) NOT NULL DEFAULT 0,
    CONSTRAINT reservation_items_pkey PRIMARY KEY (reservation_item_id),
    CONSTRAINT reservation_items_item_id_fkey FOREIGN KEY (item_id)
        REFERENCES public.inventory_items (item_id),
    CONSTRAINT reservation_items_reservation_id_fkey FOREIGN KEY (reservation_id)
        REFERENCES public.reservations (reservation_id) ON DELETE CASCADE,
    CONSTRAINT reservation_items_qty_check CHECK (qty > 0)
);

-- ── payments ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.payments (
    payment_id     integer NOT NULL DEFAULT nextval('payments_payment_id_seq'),
    bill_id        integer NOT NULL,
    enrollment_id  integer NOT NULL,
    branch_id      integer NOT NULL,
    amount         numeric(10,2) NOT NULL,
    payment_method character varying(20) DEFAULT 'cash',
    payment_date   timestamp NOT NULL DEFAULT now(),
    receipt_number character varying(50),
    notes          text,
    received_by    integer NOT NULL,
    CONSTRAINT payments_pkey PRIMARY KEY (payment_id),
    CONSTRAINT payments_receipt_number_key UNIQUE (receipt_number),
    CONSTRAINT payments_bill_id_fkey FOREIGN KEY (bill_id)
        REFERENCES public.billing (bill_id) ON DELETE CASCADE,
    CONSTRAINT payments_branch_id_fkey FOREIGN KEY (branch_id)
        REFERENCES public.branches (branch_id) ON DELETE CASCADE,
    CONSTRAINT payments_enrollment_id_fkey FOREIGN KEY (enrollment_id)
        REFERENCES public.enrollments (enrollment_id) ON DELETE CASCADE,
    CONSTRAINT payments_received_by_fkey FOREIGN KEY (received_by)
        REFERENCES public.users (user_id) ON DELETE CASCADE
);

-- ── parent_student ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.parent_student (
    id           integer NOT NULL DEFAULT nextval('parent_student_id_seq'),
    parent_id    integer NOT NULL,
    student_id   integer NOT NULL,
    relationship character varying(20) DEFAULT 'guardian',
    created_at   timestamp NOT NULL DEFAULT now(),
    CONSTRAINT parent_student_pkey PRIMARY KEY (id),
    CONSTRAINT unique_parent_student UNIQUE (parent_id, student_id),
    CONSTRAINT parent_student_parent_id_fkey FOREIGN KEY (parent_id)
        REFERENCES public.users (user_id),
    CONSTRAINT parent_student_student_id_fkey FOREIGN KEY (student_id)
        REFERENCES public.enrollments (enrollment_id)
);

-- ── student_accounts ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.student_accounts (
    account_id              integer NOT NULL DEFAULT nextval('student_accounts_account_id_seq'),
    enrollment_id           integer NOT NULL,
    branch_id               integer NOT NULL,
    username                character varying(100) NOT NULL,
    password                character varying(255) NOT NULL,
    email                   character varying(255),
    is_active               boolean DEFAULT true,
    created_at              timestamp NOT NULL DEFAULT now(),
    require_password_change boolean DEFAULT false,
    last_password_change    timestamp,
    CONSTRAINT student_accounts_pkey PRIMARY KEY (account_id),
    CONSTRAINT student_accounts_username_key UNIQUE (username),
    CONSTRAINT student_accounts_branch_id_fkey FOREIGN KEY (branch_id)
        REFERENCES public.branches (branch_id),
    CONSTRAINT student_accounts_enrollment_id_fkey FOREIGN KEY (enrollment_id)
        REFERENCES public.enrollments (enrollment_id)
);

-- ── grade_levels ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.grade_levels (
    id            integer NOT NULL DEFAULT nextval('grade_levels_id_seq'),
    name          character varying(50) NOT NULL,
    display_order integer DEFAULT 0,
    description   text,
    CONSTRAINT grade_levels_pkey PRIMARY KEY (id)
);

-- ── sections ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.sections (
    id            integer NOT NULL DEFAULT nextval('sections_id_seq'),
    branch_id     integer NOT NULL,
    grade_level   character varying(50),
    section_name  character varying(100) NOT NULL,
    school_year   character varying(20),
    created_at    timestamp DEFAULT now(),
    CONSTRAINT sections_pkey PRIMARY KEY (id),
    CONSTRAINT sections_branch_id_fkey FOREIGN KEY (branch_id)
        REFERENCES public.branches (branch_id) ON DELETE CASCADE
);

-- ── teacher_section_assignments ──────────────────────────────
CREATE TABLE IF NOT EXISTS public.teacher_section_assignments (
    id         integer NOT NULL DEFAULT nextval('teacher_section_assignments_id_seq'),
    teacher_id integer NOT NULL,
    section_id integer NOT NULL,
    subject    character varying(100),
    created_at timestamp DEFAULT now(),
    CONSTRAINT teacher_section_assignments_pkey PRIMARY KEY (id),
    CONSTRAINT tsa_teacher_fkey FOREIGN KEY (teacher_id)
        REFERENCES public.users (user_id) ON DELETE CASCADE,
    CONSTRAINT tsa_section_fkey FOREIGN KEY (section_id)
        REFERENCES public.sections (id) ON DELETE CASCADE
);

-- ── Indexes ──────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_billing_branch_id ON public.billing (branch_id);
CREATE INDEX IF NOT EXISTS idx_billing_enrollment_id ON public.billing (enrollment_id);
CREATE INDEX IF NOT EXISTS idx_billing_status ON public.billing (status);
CREATE INDEX IF NOT EXISTS idx_inventory_branch ON public.inventory_items (branch_id);
CREATE INDEX IF NOT EXISTS idx_parent_student_parent ON public.parent_student (parent_id);
CREATE INDEX IF NOT EXISTS idx_parent_student_student ON public.parent_student (student_id);
CREATE INDEX IF NOT EXISTS idx_payments_bill_id ON public.payments (bill_id);
CREATE INDEX IF NOT EXISTS idx_payments_branch_id ON public.payments (branch_id);
CREATE INDEX IF NOT EXISTS idx_payments_enrollment_id ON public.payments (enrollment_id);
CREATE INDEX IF NOT EXISTS idx_reservations_branch ON public.reservations (branch_id);
CREATE INDEX IF NOT EXISTS idx_reservations_student ON public.reservations (student_user_id);

-- ── Default super admin ──────────────────────────────────────
-- Password: admin123 (hashed with werkzeug pbkdf2:sha256)
INSERT INTO public.users (username, password, role, status)
VALUES (
    'superadmin',
    'scrypt:32768:8:1$liceo$bfe9c5e2b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9',
    'super_admin',
    'active'
)
ON CONFLICT (username) DO NOTHING;
