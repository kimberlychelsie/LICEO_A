from flask import Blueprint, render_template, request, redirect, session, flash, url_for
from db import get_db_connection
from werkzeug.security import generate_password_hash
import logging
import psycopg2.extras

# Setup logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

student_portal_bp = Blueprint("student_portal", __name__)

def _require_student():
    return session.get("role") == "student"



@student_portal_bp.route("/student/dashboard")
def dashboard():
    if not _require_student():
        return redirect("/")

    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        account_id    = session.get("student_account_id")
        enrollment_id = session.get("enrollment_id")

        if account_id:
            # Path A: logged in via student_accounts table
            cursor.execute("""
                SELECT sa.account_id, sa.enrollment_id, sa.username, sa.email,
                       e.student_name, e.grade_level, e.status, e.branch_id,
                       e.branch_enrollment_no, e.section_id,
                       br.branch_name, br.location
                FROM student_accounts sa
                JOIN enrollments e ON sa.enrollment_id = e.enrollment_id
                JOIN branches br ON e.branch_id = br.branch_id
                WHERE sa.account_id = %s
            """, (account_id,))
        elif enrollment_id:
            # Path B: logged in via users table with enrollment_id
            cursor.execute("""
                SELECT NULL AS account_id, e.enrollment_id,
                       e.branch_enrollment_no, e.section_id,
                       u.username, NULL AS email,
                       e.student_name, e.grade_level, e.status, e.branch_id,
                       br.branch_name, br.location
                FROM enrollments e
                JOIN branches br ON e.branch_id = br.branch_id
                JOIN users u ON u.enrollment_id = e.enrollment_id
                WHERE e.enrollment_id = %s
            """, (enrollment_id,))
        else:
            flash("Session expired or student account not found. Please log in again.", "error")
            return redirect("/")

        student = cursor.fetchone()

        if not student:
            flash("Student account not found", "error")
            return redirect("/")

        # Billing info
        cursor.execute("SELECT * FROM billing WHERE enrollment_id=%s", (student["enrollment_id"],))
        bill = cursor.fetchone()

        # Counts (use COALESCE for safety)
        cursor.execute("""
            SELECT COUNT(*) AS doc_count
            FROM enrollment_documents
            WHERE enrollment_id=%s
        """, (student["enrollment_id"],))
        doc_count = (cursor.fetchone() or {}).get("doc_count", 0)

        cursor.execute("""
            SELECT COUNT(*) AS book_count
            FROM enrollment_books
            WHERE enrollment_id=%s
        """, (student["enrollment_id"],))
        book_count = (cursor.fetchone() or {}).get("book_count", 0)

        cursor.execute("""
            SELECT COUNT(*) AS uniform_count
            FROM enrollment_uniforms
            WHERE enrollment_id=%s
        """, (student["enrollment_id"],))
        uniform_count = (cursor.fetchone() or {}).get("uniform_count", 0)

        # Teacher announcements — match both "7" and "Grade 7" formats
        raw_grade = student.get("grade_level") or ""
        import re as _re
        if _re.match(r'^\d+$', raw_grade.strip()):
            # DB has plain number e.g. "7"
            grade_short = raw_grade.strip()
            grade_full  = "Grade " + grade_short
        else:
            # DB has "Grade 7" or "Kinder"
            grade_full  = raw_grade.strip()
            _m2 = _re.match(r'^Grade\s+(\d+)$', grade_full, _re.IGNORECASE)
            grade_short = _m2.group(1) if _m2 else grade_full

        cursor.execute("""
            SELECT a.title, a.body, a.created_at,
                   u.username AS posted_by, u.full_name, u.gender
            FROM teacher_announcements a
            JOIN users u ON u.user_id = a.teacher_user_id
            WHERE a.branch_id = %(branch_id)s
              AND (
                  a.grade_level ILIKE %(grade_full)s
                  OR a.grade_level ILIKE %(grade_short)s
              )
            ORDER BY a.created_at DESC
            LIMIT 20
        """, {
            "branch_id":   student.get("branch_id"),
            "grade_full":  grade_full,
            "grade_short": grade_short,
        })
        raw_ann = cursor.fetchall() or []


        teacher_announcements = []
        for a in raw_ann:
            a = dict(a)
            prefix = "Ms. " if a.get("gender") == "female" else ("Mr. " if a.get("gender") == "male" else "")
            a["display_name"] = prefix + (a.get("full_name") or a.get("posted_by") or "Teacher")
            teacher_announcements.append(a)

        # Subjects & teachers for this student's section (if assigned)
        subject_rows = []
        if student.get("section_id"):
            cursor.execute("""
                SELECT
                    g.name      AS grade_level_name,
                    s.section_name,
                    sub.name    AS subject_name,
                    u.full_name AS teacher_full_name,
                    u.username  AS teacher_username,
                    u.gender    AS teacher_gender
                FROM sections s
                JOIN grade_levels g      ON s.grade_level_id = g.id
                JOIN section_teachers st ON st.section_id    = s.section_id
                JOIN subjects sub        ON st.subject_id    = sub.subject_id
                LEFT JOIN users u        ON st.teacher_id    = u.user_id
                WHERE s.section_id = %(section_id)s
                ORDER BY sub.name
            """, {
                "section_id": student["section_id"],
            })
            subject_rows = cursor.fetchall() or []
        else:
            # Fallback: keep existing logic but show "Please contact admin for section"
            # Or just show subjects for grade as fallback if you want
            cursor.execute("""
                SELECT
                    g.name      AS grade_level_name,
                    s.section_name,
                    sub.name    AS subject_name,
                    u.full_name AS teacher_full_name,
                    u.username  AS teacher_username,
                    u.gender    AS teacher_gender
                FROM sections s
                JOIN grade_levels g      ON s.grade_level_id = g.id
                JOIN section_teachers st ON st.section_id    = s.section_id
                JOIN subjects sub        ON st.subject_id    = sub.subject_id
                LEFT JOIN users u        ON st.teacher_id    = u.user_id
                WHERE s.branch_id = %(branch_id)s
                  AND (
                      g.name ILIKE %(grade_full)s
                      OR g.name ILIKE %(grade_short)s
                  )
                ORDER BY s.section_name, sub.name
            """, {
                "branch_id":   student.get("branch_id"),
                "grade_full":  grade_full,
                "grade_short": grade_short,
            })
            subject_rows = cursor.fetchall() or []

        cursor.execute("""
            SELECT
                r.reservation_id,
                r.status,
                r.created_at,
                COALESCE(SUM(ri.line_total), 0) AS total_amount,
                STRING_AGG(DISTINCT ii.item_name, ', ' ORDER BY ii.item_name) AS items
            FROM reservations r
            LEFT JOIN reservation_items ri ON ri.reservation_id = r.reservation_id
            LEFT JOIN inventory_items ii ON ii.item_id = ri.item_id
            WHERE r.student_user_id = %s
            GROUP BY r.reservation_id, r.status, r.created_at
            ORDER BY r.created_at DESC
        """, (session.get("user_id"),))
        reservations = cursor.fetchall()

        return render_template(
            "student_dashboard.html",
            student=student,
            bill=bill,
            doc_count=doc_count,
            book_count=book_count,
            uniform_count=uniform_count,
            teacher_announcements=teacher_announcements,
            subjects_for_grade=subject_rows,
            reservations=reservations,
        )

    finally:
        cursor.close()
        db.close()


@student_portal_bp.route("/student/enrollment-status")
def enrollment_status():
    if not _require_student():
        return redirect("/")

    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        cursor.execute("""
            SELECT sa.*, e.*, br.branch_name, br.location
            FROM student_accounts sa
            JOIN enrollments e ON sa.enrollment_id = e.enrollment_id
            JOIN branches br ON e.branch_id = br.branch_id
            WHERE sa.account_id = %s
        """, (session.get("student_account_id"),))
        enrollment = cursor.fetchone()

        if not enrollment:
            flash("Enrollment not found", "error")
            return redirect(url_for("student_portal.dashboard"))

        cursor.execute("SELECT * FROM enrollment_documents WHERE enrollment_id=%s", (enrollment["enrollment_id"],))
        documents = cursor.fetchall()

        cursor.execute("SELECT * FROM enrollment_books WHERE enrollment_id=%s", (enrollment["enrollment_id"],))
        books = cursor.fetchall()

        cursor.execute("SELECT * FROM enrollment_uniforms WHERE enrollment_id=%s", (enrollment["enrollment_id"],))
        uniforms = cursor.fetchall()

        return render_template(
            "student_enrollment_detail.html",
            enrollment=enrollment,
            documents=documents,
            books=books,
            uniforms=uniforms
        )

    finally:
        cursor.close()
        db.close()


@student_portal_bp.route("/student/billing")
def billing():
    if not _require_student():
        return redirect("/")

    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        cursor.execute("""
            SELECT sa.*, e.student_name, e.grade_level
            FROM student_accounts sa
            JOIN enrollments e ON sa.enrollment_id = e.enrollment_id
            WHERE sa.account_id = %s
        """, (session.get("student_account_id"),))
        student = cursor.fetchone()

        if not student:
            flash("Student account not found", "error")
            return redirect("/")

        cursor.execute("SELECT * FROM billing WHERE enrollment_id=%s", (student["enrollment_id"],))
        bill = cursor.fetchone()

        payments = []
        if bill:
            cursor.execute("""
                SELECT p.*, u.username as received_by_name
                FROM payments p
                LEFT JOIN users u ON p.received_by = u.user_id
                WHERE p.bill_id=%s
                ORDER BY p.payment_date DESC
            """, (bill["bill_id"],))
            payments = cursor.fetchall()

        cursor.execute("""
            SELECT
                r.reservation_id,
                r.status,
                r.created_at,
                COALESCE(SUM(ri.line_total), 0) AS total_amount,
                STRING_AGG(DISTINCT ii.item_name, ', ' ORDER BY ii.item_name) AS items
            FROM reservations r
            LEFT JOIN reservation_items ri ON ri.reservation_id = r.reservation_id
            LEFT JOIN inventory_items ii ON ii.item_id = ri.item_id
            WHERE r.student_user_id = %s
            GROUP BY r.reservation_id, r.status, r.created_at
            ORDER BY r.created_at DESC
        """, (session.get("user_id"),))
        reservations = cursor.fetchall()

        return render_template(
            "student_billing_view.html",
            student=student,
            bill=bill,
            payments=payments,
            reservations=reservations
        )

    finally:
        cursor.close()
        db.close()


@student_portal_bp.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response
