from flask import Blueprint, render_template, request, redirect, session, flash, url_for
from db import get_db_connection
from werkzeug.security import generate_password_hash
import logging
import psycopg2.extras
from cloudinary_helper import upload_file
from datetime import datetime

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
            WHERE r.student_user_id = %s AND r.status != 'CANCELLED'
            GROUP BY r.reservation_id, r.status, r.created_at
            ORDER BY r.created_at DESC
        """, (session.get("user_id"),))
        reservations = cursor.fetchall()

        # Sync billing totals to handle any discrepancies from cancelled reservations
        if bill:
            active_res_total = sum(float(r['total_amount'] or 0) for r in reservations)
            tuition = float(bill['tuition_fee'] or 0)
            other = float(bill['other_fees'] or 0)
            expected_total = tuition + other + active_res_total
            
            if abs(float(bill['total_amount'] or 0) - expected_total) > 0.01:
                new_balance = max(expected_total - float(bill['amount_paid'] or 0), 0)
                new_status = 'paid' if new_balance == 0 and expected_total > 0 else ('pending' if float(bill['amount_paid'] or 0) == 0 else 'partial')
                cursor.execute("UPDATE billing SET total_amount=%s, balance=%s, status=%s WHERE bill_id=%s",
                             (expected_total, new_balance, new_status, bill['bill_id']))
                db.commit()
                cursor.execute("SELECT * FROM billing WHERE bill_id=%s", (bill['bill_id'],))
                bill = cursor.fetchone()

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
            now=datetime.now(),
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
            SELECT sa.*, e.student_name, e.grade_level, e.branch_enrollment_no
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
            WHERE r.student_user_id = %s AND r.status != 'CANCELLED'
            GROUP BY r.reservation_id, r.status, r.created_at
            ORDER BY r.created_at DESC
        """, (session.get("user_id"),))
        reservations = cursor.fetchall()

        # Sync billing totals to handle any discrepancies from cancelled reservations
        if bill:
            active_res_total = sum(float(r['total_amount'] or 0) for r in reservations)
            tuition = float(bill['tuition_fee'] or 0)
            other = float(bill['other_fees'] or 0)
            expected_total = tuition + other + active_res_total
            
            if abs(float(bill['total_amount'] or 0) - expected_total) > 0.01:
                new_balance = max(expected_total - float(bill['amount_paid'] or 0), 0)
                new_status = 'paid' if new_balance == 0 and expected_total > 0 else ('pending' if float(bill['amount_paid'] or 0) == 0 else 'partial')
                cursor.execute("UPDATE billing SET total_amount=%s, balance=%s, status=%s WHERE bill_id=%s",
                             (expected_total, new_balance, new_status, bill['bill_id']))
                db.commit()
                cursor.execute("SELECT * FROM billing WHERE bill_id=%s", (bill['bill_id'],))
                bill = cursor.fetchone()

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


@student_portal_bp.route("/student/subject/<int:subject_id>")
def subject_view(subject_id):
    if not _require_student(): return redirect("/")
    
    enrollment_id = session.get("enrollment_id")
    student_user_id = session.get("user_id")
    
    db = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        # Get subject details and teacher
        cur.execute("""
            SELECT sub.subject_id, sub.name as subject_name, u.full_name as teacher_name, u.gender as teacher_gender,
                   s.section_id, s.section_name
            FROM subjects sub
            JOIN section_teachers st ON sub.subject_id = st.subject_id
            JOIN sections s ON st.section_id = s.section_id
            JOIN enrollments e ON e.section_id = s.section_id
            LEFT JOIN users u ON st.teacher_id = u.user_id
            WHERE sub.subject_id = %s AND e.enrollment_id = %s
        """, (subject_id, enrollment_id))
        subject_info = cur.fetchone()
        
        if not subject_info:
            flash("Subject not found or you are not enrolled in it.", "error")
            return redirect(url_for("student_portal.dashboard"))
        
        # Get activities for this subject
        cur.execute('''
            SELECT a.*, subm.status as submission_status, subm.submission_id
            FROM activities a
            LEFT JOIN activity_submissions subm ON a.activity_id = subm.activity_id AND subm.student_id = %s
            WHERE a.subject_id = %s AND a.section_id = %s AND a.status = 'Published'
            ORDER BY a.due_date ASC
        ''', (student_user_id, subject_id, subject_info['section_id']))
        activities = cur.fetchall()
        
    finally:
        cur.close()
        db.close()
        
    return render_template("student_subject_detail.html", subject=subject_info, activities=activities, now=datetime.now())


# ── ACTIVITIES MODULE (STUDENT SIDE) ──────────────────────

@student_portal_bp.route("/student/activities")
def activities():
    if not _require_student(): return redirect("/")
    
    student_user_id = session.get("user_id")
    enrollment_id = session.get("enrollment_id")
    
    db = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        # Get student's section safely
        cur.execute("SELECT section_id FROM enrollments WHERE enrollment_id = %s", (enrollment_id,))
        enrollment = cur.fetchone()
        
        activities = []
        if enrollment and enrollment.get("section_id"):
            section_id = enrollment["section_id"]
            
            # Fetch activities for the student's section
            cur.execute('''
                SELECT DISTINCT ON (a.activity_id)
                       a.*, 
                       s.section_name, 
                       sub.name AS subject_name,
                       u.full_name AS teacher_name,
                       subm.submission_id,
                       subm.status AS submission_status,
                       subm.is_late,
                       subm.allow_resubmit,
                       g.grade_id,
                       g.raw_score
                FROM activities a
                JOIN sections s ON a.section_id = s.section_id
                JOIN subjects sub ON a.subject_id = sub.subject_id
                LEFT JOIN users u ON a.teacher_id = u.user_id
                LEFT JOIN activity_submissions subm ON subm.activity_id = a.activity_id AND subm.student_id = %s
                LEFT JOIN activity_grades g ON g.submission_id = subm.submission_id
                WHERE a.section_id = %s AND a.status = 'Published'
                ORDER BY a.activity_id, subm.submitted_at DESC
            ''', (student_user_id, section_id))
            activities_raw = cur.fetchall()
            
            # Sort by ascending due date in python since we used distinct on activity_id
            activities = sorted(activities_raw, key=lambda x: (x['due_date'] is None, x['due_date']))
            subjects = sorted(list(set(a['subject_name'] for a in activities)))
        else:
            subjects = []
            
    finally:
        cur.close()
        db.close()
        
    return render_template("student_activities.html", activities=activities, subjects=subjects, now=datetime.now())


@student_portal_bp.route("/student/activities/<int:activity_id>")
def activity_detail(activity_id):
    if not _require_student(): return redirect("/")
    
    student_user_id = session.get("user_id")
    enrollment_id = session.get("enrollment_id")
    
    db = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        # Get student section
        cur.execute("SELECT section_id FROM enrollments WHERE enrollment_id = %s", (enrollment_id,))
        enrollment = cur.fetchone()
        
        if not enrollment or not enrollment.get("section_id"):
            flash("No section assigned.", "error")
            return redirect(url_for("student_portal.activities"))
            
        cur.execute('''
            SELECT a.*, sub.name AS subject_name, u.full_name AS teacher_name
            FROM activities a
            JOIN subjects sub ON a.subject_id = sub.subject_id
            LEFT JOIN users u ON a.teacher_id = u.user_id
            WHERE a.activity_id = %s AND a.section_id = %s AND a.status = 'Published'
        ''', (activity_id, enrollment['section_id']))
        activity = cur.fetchone()
        
        if not activity:
            flash("Activity not found or not available.", "error")
            return redirect(url_for("student_portal.activities"))
            
        # Get submission if exists
        cur.execute('''
            SELECT sub.*, g.grade_id, g.raw_score, g.percentage, g.remarks
            FROM activity_submissions sub
            LEFT JOIN activity_grades g ON g.submission_id = sub.submission_id
            WHERE sub.activity_id = %s AND sub.student_id = %s
            ORDER BY sub.submitted_at DESC LIMIT 1
        ''', (activity_id, student_user_id))
        submission = cur.fetchone()
        
    finally:
        cur.close()
        db.close()
        
    return render_template("student_activity_detail.html", activity=activity, submission=submission, now=datetime.now())


@student_portal_bp.route("/student/activities/<int:activity_id>/submit", methods=["POST"])
def submit_activity(activity_id):
    if not _require_student(): return redirect("/")
    
    student_user_id = session.get("user_id")
    enrollment_id = session.get("enrollment_id")
    
    db = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    try:
        # Ensure student is allowed to submit
        cur.execute("SELECT section_id FROM enrollments WHERE enrollment_id = %s", (enrollment_id,))
        enrollment = cur.fetchone()
        
        cur.execute("SELECT * FROM activities WHERE activity_id = %s AND section_id = %s AND status = 'Published'", 
                   (activity_id, enrollment['section_id']))
        activity = cur.fetchone()
        
        if not activity:
            flash("Activity not available.", "error")
            return redirect(url_for("student_portal.activities"))
            
        if activity['status'] == 'Closed':
            flash("Submissions for this activity are closed.", "error")
            return redirect(request.referrer)
            
        # Check if already graded
        cur.execute('''
            SELECT sub.submission_id, sub.allow_resubmit, g.grade_id 
            FROM activity_submissions sub
            LEFT JOIN activity_grades g ON sub.submission_id = g.submission_id
            WHERE sub.activity_id = %s AND sub.student_id = %s
        ''', (activity_id, student_user_id))
        existing_sub = cur.fetchone()
        
        if existing_sub:
            if not existing_sub['allow_resubmit']:
                flash("You have already submitted this activity. Resubmission is not currently allowed.", "error")
                return redirect(request.referrer)
            if existing_sub['grade_id']:
                flash("This activity has already been graded.", "error")
                return redirect(request.referrer)
            
        # Proceed with file upload
        if 'submission_file' not in request.files:
            flash("No file provided.", "error")
            return redirect(request.referrer)
            
        file = request.files['submission_file']
        if file.filename == '':
            flash("No file selected.", "error")
            return redirect(request.referrer)
            
        # Basic extension check
        if activity['allowed_file_types']:
            allowed = [x.strip().lower() for x in str(activity['allowed_file_types']).split(',')]
            ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
            if ext not in allowed:
                flash(f"Invalid file type. Allowed: {activity['allowed_file_types']}", "error")
                return redirect(request.referrer)
                
        try:
            file_path = upload_file(file, folder="liceo_submissions")
        except Exception as e:
            flash(f"File upload failed: {e}", "error")
            return redirect(request.referrer)
            
        is_late = bool(activity['due_date'] and datetime.now() > activity['due_date'])
        
        if existing_sub:
            # Update existing submission
            cur.execute('''
                UPDATE activity_submissions SET 
                    file_path = %s, original_filename = %s, submitted_at = NOW(), is_late = %s, 
                    status = 'Resubmitted', allow_resubmit = FALSE
                WHERE submission_id = %s
            ''', (file_path, file.filename, is_late, existing_sub['submission_id']))
        else:
            # Create new submission
            cur.execute('''
                INSERT INTO activity_submissions (activity_id, student_id, enrollment_id, file_path, original_filename, is_late)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (activity_id, student_user_id, enrollment_id, file_path, file.filename, is_late))
            
        # Delete notification for this activity if it exists
        cur.execute("""
            DELETE FROM student_notifications 
            WHERE student_id = %s 
              AND link LIKE %s
        """, (student_user_id, f"%/student/activities/{activity_id}%"))

        db.commit()
        flash("Your work has been submitted successfully!", "success")
        
    finally:
        cur.close()
        db.close()
        
    return redirect(request.referrer)
