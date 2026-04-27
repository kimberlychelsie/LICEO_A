from flask import Blueprint, render_template, request, redirect, session, flash, url_for, jsonify
from db import get_db_connection
from werkzeug.security import generate_password_hash
import logging
import psycopg2.extras
from cloudinary_helper import upload_file
from datetime import datetime, timezone
import json
from datetime import timedelta
import pytz

# Setup logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

student_portal_bp = Blueprint("student_portal", __name__)

def _require_student():
    return session.get("role") == "student"

def _to_manila_naive(dt_value):
    """
    Normalize DB datetimes for UI/runtime checks.
    If datetime is naive, treat it as already Asia/Manila local time.
    If datetime is timezone-aware, convert it to Asia/Manila.
    """
    if not dt_value:
        return None
    ph_tz = pytz.timezone("Asia/Manila")
    if getattr(dt_value, "tzinfo", None) is None:
        # Teacher-set schedules are stored as local wall-clock time.
        return dt_value.replace(tzinfo=None)
    return dt_value.astimezone(ph_tz).replace(tzinfo=None)



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
                       e.branch_enrollment_no, e.section_id, e.profile_image,
                       br.branch_name, br.location
                FROM student_accounts sa
                JOIN enrollments e ON sa.enrollment_id = e.enrollment_id
                LEFT JOIN branches br ON e.branch_id = br.branch_id
                WHERE sa.account_id = %s
            """, (account_id,))
        elif enrollment_id:
            # Path B: logged in via users table with enrollment_id
            cursor.execute("""
                SELECT NULL AS account_id, e.enrollment_id,
                       e.branch_enrollment_no, e.section_id,
                       CAST(%s AS text) AS username, NULL AS email,
                       e.student_name, e.grade_level, e.status, e.branch_id, e.profile_image,
                       br.branch_name, br.location
                FROM enrollments e
                LEFT JOIN branches br ON e.branch_id = br.branch_id
                WHERE e.enrollment_id = %s
            """, (session.get("username"), enrollment_id,))
        else:
            session.clear()
            flash("Session expired or student account not found. Please log in again.", "error")
            return redirect("/login")

        student = cursor.fetchone()

        if not student:
            session.clear()
            flash("Student account not found", "error")
            return redirect("/login")

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

        now_naive = _to_manila_naive(datetime.now(timezone.utc))

        school_year_label = None
        if student.get("section_id"):
            cursor.execute("""
    SELECT sy.label
    FROM sections s
    LEFT JOIN school_years sy ON s.year_id = sy.year_id
    WHERE s.section_id = %s
""", (student["section_id"],))

        row = cursor.fetchone()
        school_year_label = row["label"] if row and row.get("label") else None


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
            now=now_naive,
            school_year_label=school_year_label,
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
        account_id = session.get("student_account_id")
        enrollment_id = session.get("enrollment_id")

        if account_id:
            cursor.execute("""
                SELECT sa.*, e.*, br.branch_name, br.location
                FROM student_accounts sa
                JOIN enrollments e ON sa.enrollment_id = e.enrollment_id
                JOIN branches br ON e.branch_id = br.branch_id
                WHERE sa.account_id = %s
            """, (account_id,))
        elif enrollment_id:
            cursor.execute("""
                SELECT NULL::bigint AS account_id,
                       e.enrollment_id,
                       e.branch_enrollment_no,
                       e.student_name,
                       e.grade_level,
                       e.status,
                       e.branch_id,
                       e.guardian_name,
                       e.guardian_contact,
                       e.guardian_email,
                       e.contact_number,
                       e.email,
                       e.address,
                       e.profile_image,
                       e.section_id,
                       e.created_at,
                       br.branch_name,
                       br.location
                FROM enrollments e
                JOIN branches br ON e.branch_id = br.branch_id
                WHERE e.enrollment_id = %s
                LIMIT 1
            """, (enrollment_id,))
        else:
            flash("Student account not found", "error")
            return redirect(url_for("student_portal.dashboard"))
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
        account_id = session.get("student_account_id")
        enrollment_id = session.get("enrollment_id")

        if account_id:
            cursor.execute("""
                SELECT sa.*, e.student_name, e.grade_level, e.branch_enrollment_no
                FROM student_accounts sa
                JOIN enrollments e ON sa.enrollment_id = e.enrollment_id
                WHERE sa.account_id = %s
            """, (account_id,))
        elif enrollment_id:
            cursor.execute("""
                SELECT NULL::bigint AS account_id,
                       e.enrollment_id,
                       CAST(%s AS text) AS username,
                       e.student_name,
                       e.grade_level,
                       e.branch_enrollment_no,
                       e.email
                FROM enrollments e
                WHERE e.enrollment_id = %s
                LIMIT 1
            """, (session.get("username"), enrollment_id))
        else:
            flash("Student account not found", "error")
            return redirect("/")
        student = cursor.fetchone()

        if not student:
            flash("Student account not found", "error")
            return redirect("/")

        cursor.execute("SELECT * FROM billing WHERE enrollment_id=%s", (student["enrollment_id"],))
        bill = cursor.fetchone()

        payments = []
        if bill:
            cursor.execute("""
                SELECT p.*, p.receipt_number as reference_number, u.username as received_by_name
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
            
            # If there are active reservations, we trust the dynamic total from them.
            # However, we must also account for books_fee and uniform_fee if they were 
            # manually entered without a reservation record (e.g. legacy or direct sale).
            # To avoid double counting, we only add them if active_res_total is 0 OR 
            # if we want to support both. Given the system design, reservations usually 
            # populate these fields. 
            
            # Improved logic: If a reservation exists, it contributes to active_res_total.
            # The bill.books_fee and bill.uniform_fee are snapshots.
            # We'll include them in the expected total if they are set.
            books = float(bill['books_fee'] or 0)
            uniform = float(bill['uniform_fee'] or 0)
            
            # Note: If active_res_total is used, it usually covers what would be in books/uniform.
            # But the sync logic was wiping out manual fees.
            # Let's check if the reservations already account for the type of fees.
            expected_total = tuition + other + active_res_total
            
            # If active_res_total is 0, then we MUST include the bill's books/uniform fees 
            # because they might be manual entries.
            if active_res_total == 0:
                expected_total += books + uniform

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
    print("SESSION VALUES:", session.get("user_id"), session.get("enrollment_id"))
    
    db = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        # Get student's section and branch
        cur.execute("""
            SELECT section_id, branch_id, year_id
            FROM enrollments
            WHERE enrollment_id = %s
        """, (enrollment_id,))
        enr = cur.fetchone()
        if not enr or not enr.get('section_id'):
            flash("No section assigned. Please contact your branch admin.", "error")
            return redirect(url_for("student_portal.dashboard"))

        student_section_id = enr['section_id']
        student_branch_id  = enr['branch_id']
        student_year_id = enr.get('year_id')

        # Get subject details and teacher
        cur.execute("""
            SELECT sub.subject_id, sub.name as subject_name, u.full_name as teacher_name, u.gender as teacher_gender,
                   s.section_id, s.section_name
            FROM subjects sub
            JOIN section_teachers st ON sub.subject_id = st.subject_id
            JOIN sections s ON st.section_id = s.section_id
            LEFT JOIN users u ON st.teacher_id = u.user_id
            WHERE sub.subject_id = %s AND s.section_id = %s
              AND st.year_id = %s
        """, (subject_id, student_section_id, student_year_id))
        subject_info = cur.fetchone()
        
        if not subject_info:
            flash("Subject not found or you are not enrolled in it.", "error")
            return redirect(url_for("student_portal.dashboard"))
        
        # Get activities for this subject/section/branch — section-based, not student-based
        if enrollment_id and student_user_id:
            cur.execute('''
                SELECT a.*, subm.status as submission_status, subm.submission_id,
                       ext.new_due_date AS individual_extension
                FROM activities a
                LEFT JOIN activity_submissions subm 
                    ON a.activity_id = subm.activity_id 
                    AND subm.student_id = %s 
                    AND subm.enrollment_id = %s
                LEFT JOIN individual_extensions ext
                    ON ext.item_id = a.activity_id AND ext.enrollment_id = %s AND ext.item_type = 'activity'
                WHERE a.subject_id = %s 
                  AND a.section_id = %s 
                  AND a.branch_id = %s 
                  AND a.year_id = %s
                  AND a.status = 'Published'
                ORDER BY a.due_date ASC
            ''', (student_user_id, enrollment_id, enrollment_id, subject_id, student_section_id, student_branch_id, student_year_id))
            activities_raw = cur.fetchall()
            
            activities = []
            for a in activities_raw:
                a = dict(a)
                a["effective_due"] = _to_manila_naive(a.get("individual_extension") or a.get("due_date"))
                activities.append(a)
        else:
            activities = []
            print("DEBUG VALUES:", student_user_id, enrollment_id, subject_id, student_section_id, student_branch_id)

        # Get quizzes for this subject/section — shown on the same page as activities
        cur.execute("""
            SELECT e.*,
                   r.result_id, r.score, r.total_points, r.status AS result_status,
                   ext.new_due_date AS individual_extension
            FROM exams e
            LEFT JOIN exam_results r ON r.exam_id = e.exam_id AND r.enrollment_id = %s
            LEFT JOIN individual_extensions ext
                ON ext.item_id = e.exam_id AND ext.enrollment_id = %s AND ext.item_type = 'quiz'
            WHERE e.subject_id = %s AND e.section_id = %s
              AND COALESCE(e.year_id, %s) = %s
              AND e.exam_type = 'quiz'
              AND LOWER(COALESCE(e.status, '')) IN ('published', 'closed')
              AND e.is_visible = TRUE
            ORDER BY e.created_at DESC
        """, (enrollment_id, enrollment_id, subject_id, student_section_id, student_year_id, student_year_id))
        quizzes_raw = cur.fetchall() or []

        ph_tz = pytz.timezone("Asia/Manila")
        now_naive = datetime.now(timezone.utc).astimezone(ph_tz).replace(tzinfo=None)

        quizzes = []
        for q in quizzes_raw:
            q = dict(q)
            duration = int(q.get("duration_mins") or 0)
            
            if q.get("individual_extension"):
                q["effective_start"] = _to_manila_naive(q["individual_extension"])
                q["effective_end"] = q["effective_start"] + timedelta(minutes=duration)
            else:
                q["effective_start"] = _to_manila_naive(q.get("scheduled_start"))
                if q["effective_start"]:
                    q["effective_end"] = q["effective_start"] + timedelta(minutes=duration)
                else:
                    q["effective_end"] = None
                    
            quizzes.append(q)

    finally:
        cur.close()
        db.close()
        
    return render_template("student_subject_detail.html", subject=subject_info, activities=activities, quizzes=quizzes, now=now_naive, timedelta=timedelta)


# ── ACTIVITIES MODULE (STUDENT SIDE) ──────────────────────

@student_portal_bp.route("/student/activities")
def activities():
    if not _require_student(): return redirect("/")
    
    student_user_id = session.get("user_id")
    enrollment_id = session.get("enrollment_id")
    
    db = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        # Get student's section AND branch safely
        cur.execute("SELECT section_id, branch_id FROM enrollments WHERE enrollment_id = %s", (enrollment_id,))
        enrollment = cur.fetchone()
        
        activities = []
        if enrollment and enrollment.get("section_id"):
            section_id = enrollment["section_id"]
            branch_id  = enrollment["branch_id"]
            
            # Fetch all Published activities for the student's section (section-based, not student-based)
            # This means even activities created before the student was assigned will appear
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
                       g.raw_score,
                       ext.new_due_date AS individual_extension
                FROM activities a
                JOIN sections s ON a.section_id = s.section_id
                JOIN subjects sub ON a.subject_id = sub.subject_id
                LEFT JOIN users u ON a.teacher_id = u.user_id
                LEFT JOIN activity_submissions subm ON subm.activity_id = a.activity_id AND subm.student_id = %s AND subm.enrollment_id = %s  
                LEFT JOIN activity_grades g ON g.submission_id = subm.submission_id
                LEFT JOIN individual_extensions ext ON ext.item_id = a.activity_id AND ext.enrollment_id = %s AND ext.item_type = 'activity'
                WHERE a.section_id = %s AND a.branch_id = %s AND a.status = 'Published'
                ORDER BY a.activity_id, subm.submitted_at DESC
            ''', (student_user_id, enrollment_id, enrollment_id, section_id, branch_id))
            activities_raw = cur.fetchall()
            
            # Sort by ascending due date in python since we used distinct on activity_id
            activities = sorted(activities_raw, key=lambda x: (x['due_date'] is None, x['due_date']))
            subjects = sorted(list(set(a['subject_name'] for a in activities)))
        else:
            subjects = []
            
    finally:
        cur.close()
        db.close()
        
    ph_tz = pytz.timezone("Asia/Manila")
    now_naive = datetime.now(timezone.utc).astimezone(ph_tz).replace(tzinfo=None)
        
    return render_template("student_activities.html", activities=activities, subjects=subjects, now=now_naive)


@student_portal_bp.route("/student/activities/<int:activity_id>")
def activity_detail(activity_id):
    if not _require_student(): return redirect("/")
    
    student_user_id = session.get("user_id")
    enrollment_id = session.get("enrollment_id")
    
    db = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        # Get student section and branch
        cur.execute("SELECT section_id, branch_id FROM enrollments WHERE enrollment_id = %s", (enrollment_id,))
        enrollment = cur.fetchone()
        
        if not enrollment or not enrollment.get("section_id"):
            flash("No section assigned.", "error")
            return redirect(url_for("student_portal.activities"))
            
        cur.execute('''
            SELECT a.*, sub.name AS subject_name, u.full_name AS teacher_name,
                   ext.new_due_date AS individual_extension
            FROM activities a
            JOIN subjects sub ON a.subject_id = sub.subject_id
            LEFT JOIN users u ON a.teacher_id = u.user_id
            LEFT JOIN individual_extensions ext ON ext.item_id = a.activity_id AND ext.enrollment_id = %s AND ext.item_type = 'activity'
            WHERE a.activity_id = %s AND a.section_id = %s AND a.branch_id = %s AND a.status = 'Published'
        ''', (enrollment_id, activity_id, enrollment['section_id'], enrollment['branch_id']))
        activity = cur.fetchone()
        
        if not activity:
            flash("Activity not found or not available.", "error")
            return redirect(url_for("student_portal.activities"))
            
        # Get submission if exists
        cur.execute('''
    SELECT sub.*, g.grade_id, g.raw_score, g.percentage, g.remarks
    FROM activity_submissions sub
    LEFT JOIN activity_grades g ON g.submission_id = sub.submission_id
    WHERE sub.activity_id = %s AND sub.student_id = %s AND sub.enrollment_id = %s
    ORDER BY sub.submitted_at DESC LIMIT 1
    ''', (activity_id, student_user_id, enrollment_id))
        submission = cur.fetchone() 
        if submission:
            if submission.get("submitted_at"):
                submission["submitted_at"] = _to_manila_naive(submission["submitted_at"])
            
            # Parse attachments JSON if present
            if submission.get("attachments"):
                if isinstance(submission["attachments"], str):
                    try:
                        submission["attachments"] = json.loads(submission["attachments"])
                    except:
                        submission["attachments"] = []
            else:
                # Fallback for old submissions with only one file
                if submission.get("file_path"):
                    submission["attachments"] = [{
                        "path": submission["file_path"],
                        "name": submission.get("original_filename") or "Attachment",
                        "type": submission["file_path"].rsplit('.', 1)[-1].lower() if '.' in submission["file_path"] else ''
                    }]
                else:
                    submission["attachments"] = []
    finally:
        cur.close()
        db.close()
        
    ph_tz = pytz.timezone("Asia/Manila")
    now_naive = datetime.now(timezone.utc).astimezone(ph_tz).replace(tzinfo=None)
        
    return render_template("student_activity_detail.html", activity=activity, submission=submission, now=now_naive)


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
        
        cur.execute("""
            SELECT a.*, ext.new_due_date AS individual_extension 
            FROM activities a 
            LEFT JOIN individual_extensions ext ON ext.item_id = a.activity_id AND ext.enrollment_id = %s AND ext.item_type = 'activity'
            WHERE a.activity_id = %s AND a.section_id = %s AND a.status = 'Published'
            """, (enrollment_id, activity_id, enrollment['section_id']))
        activity = cur.fetchone()
        
        if not activity:
            flash("Activity not available.", "error")
            return redirect(url_for("student_portal.activities"))
            
        # Define now_naive for Philippine time
        import pytz
        from datetime import datetime, timezone
        now_naive = datetime.now(timezone.utc).astimezone(pytz.timezone("Asia/Manila")).replace(tzinfo=None)
        
        # Check if closed, but bypass if there is an active individual extension
        effective_due_date = activity['individual_extension'] if activity['individual_extension'] else activity['due_date']
        is_extended = bool(activity['individual_extension'] and now_naive <= activity['individual_extension'])

        if activity['status'] == 'Closed' and not is_extended:
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
        files = request.files.getlist('submission_file')
        if not files or all(f.filename == '' for f in files):
            flash("No files selected.", "error")
            return redirect(request.referrer)
            
        uploaded_files = []
        for file in files:
            if file.filename == '': continue
            
            # Basic extension check
            if activity['allowed_file_types']:
                allowed = [x.strip().lower() for x in str(activity['allowed_file_types']).split(',')]
                ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
                if ext not in allowed:
                    flash(f"Invalid file type for {file.filename}. Allowed: {activity['allowed_file_types']}", "error")
                    return redirect(request.referrer)
            
            try:
                path = upload_file(file, folder="liceo_submissions")
                uploaded_files.append({
                    "path": path,
                    "name": file.filename,
                    "type": file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
                })
            except Exception as e:
                flash(f"Upload failed for {file.filename}: {e}", "error")
                return redirect(request.referrer)
            
        if not uploaded_files:
            flash("No valid files uploaded.", "error")
            return redirect(request.referrer)

        # Main file (for backward compatibility)
        primary_path = uploaded_files[0]['path']
        primary_name = uploaded_files[0]['name']
        attachments_json = json.dumps(uploaded_files)
            
        ph_tz = pytz.timezone("Asia/Manila")
        now_naive = datetime.now(timezone.utc).astimezone(ph_tz).replace(tzinfo=None)
        
        effective_due_date = activity['individual_extension'] if activity['individual_extension'] else activity['due_date']
        is_late = bool(effective_due_date and now_naive > effective_due_date)
        
        if existing_sub:
            # Update existing submission
            cur.execute('''
                UPDATE activity_submissions SET 
                    file_path = %s, original_filename = %s, attachments = %s,
                    submitted_at = %s, is_late = %s, 
                    status = 'Resubmitted', allow_resubmit = FALSE
                WHERE submission_id = %s
            ''', (primary_path, primary_name, attachments_json, now_naive, is_late, existing_sub['submission_id']))
        else:
            # Create new submission
            cur.execute('''
                INSERT INTO activity_submissions (
                    activity_id, student_id, enrollment_id, file_path, original_filename, attachments, submitted_at, is_late
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''', (activity_id, student_user_id, enrollment_id, primary_path, primary_name, attachments_json, now_naive, is_late))
            
        # Delete notification for this activity if it exists
        # Mark activity notification as read when student submits
        cur.execute("""
            UPDATE student_notifications 
            SET is_read = TRUE
            WHERE student_id = %s 
              AND link LIKE %s
        """, (student_user_id, f"%/student/activities/{activity_id}%"))

        db.commit()
        flash("Your work has been submitted successfully!", "success")
        
    finally:
        cur.close()
        db.close()
        
    return redirect(request.referrer)


@student_portal_bp.route("/student/notifications/mark-read", methods=["POST"])
def mark_notifications_read():
    """Mark all unread notifications as read for this student (called when bell is opened)."""
    if not _require_student():
        return jsonify({"ok": False}), 403

    user_id = session.get("user_id")
    db = get_db_connection()
    cur = db.cursor()
    try:
        cur.execute("""
            UPDATE student_notifications
            SET is_read = TRUE
            WHERE student_id = %s AND is_read = FALSE
        """, (user_id,))
        db.commit()
        return jsonify({"ok": True})
    except Exception as e:
        db.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        cur.close()
        db.close()


# ══════════════════════════════════════════
# EXAM ROUTES — STUDENT PORTAL
# ══════════════════════════════════════════

@student_portal_bp.route("/student/exams")
def student_exams():
    if session.get("role") != "student":
        return redirect("/")

    enrollment_id = session.get("enrollment_id")
    branch_id     = session.get("branch_id")

    # ✅ Define now_naive at the TOP before any checks
    now_naive = _to_manila_naive(datetime.now(timezone.utc))

    db  = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("SELECT section_id, grade_level, year_id FROM enrollments WHERE enrollment_id=%s",
                    (enrollment_id,))
        enr = cur.fetchone()
        if not enr:
            flash("Enrollment not found.", "error")
            return redirect(url_for("student_portal.dashboard"))

        section_id = enr["section_id"]
        year_id = enr["year_id"]

        # ✅ section check now works because now_naive is already defined
        if not section_id:
            flash("You have not been assigned to a section yet. Please contact your school admin.", "warning")
            return render_template("student_exams.html", exams=[], timedelta=timedelta, now_utc=now_naive)

        cur.execute("""
            SELECT
                e.exam_id, e.title, e.exam_type, e.duration_mins,
                e.scheduled_start, e.status, e.grading_period,
                sub.name AS subject_name,
                (SELECT COUNT(*) FROM exam_questions q WHERE q.exam_id = e.exam_id) AS question_count,
                r.result_id, r.score, r.total_points, r.status AS result_status,
                r.submitted_at,
                ext.new_due_date AS individual_extension
            FROM exams e
            JOIN subjects sub ON e.subject_id = sub.subject_id
            LEFT JOIN exam_results r
                ON r.exam_id = e.exam_id AND r.enrollment_id = %s
            LEFT JOIN individual_extensions ext
                ON ext.item_id = e.exam_id AND ext.enrollment_id = %s AND ext.item_type IN ('exam', 'quiz')
            WHERE e.section_id = %s
              AND COALESCE(e.year_id, %s) = %s
              AND LOWER(COALESCE(e.status, '')) IN ('published', 'closed')
              AND e.exam_type != 'quiz'
              AND e.is_visible = TRUE
            ORDER BY e.created_at DESC
        """, (enrollment_id, enrollment_id, section_id, year_id, year_id))
        exams_raw = cur.fetchall() or []

        # Normalize scheduled_start to PH naive time for correct comparison in Jinja
        exams = []
        for e in exams_raw:
            e = dict(e)
            # Treat individual_extension as a NEW START TIME (Reschedule)
            # If present, it replaces the scheduled_start
            duration = int(e.get("duration_mins") or 0)
            
            if e.get("individual_extension"):
                e["effective_start"] = _to_manila_naive(e["individual_extension"])
                e["effective_end"] = e["effective_start"] + timedelta(minutes=duration)
            else:
                e["effective_start"] = _to_manila_naive(e.get("scheduled_start"))
                if e["effective_start"]:
                    e["effective_end"] = e["effective_start"] + timedelta(minutes=duration)
                else:
                    e["effective_end"] = None
                    
            exams.append(e)

        return render_template(
            "student_exams.html",
            exams=exams,
            timedelta=timedelta,
            now_utc=now_naive)
    finally:
        cur.close()
        db.close()


@student_portal_bp.route("/student/quizzes")
def student_quizzes():
    if session.get("role") != "student":
        return redirect("/")

    enrollment_id = session.get("enrollment_id")

    now_naive = _to_manila_naive(datetime.now(timezone.utc))

    db  = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("SELECT section_id, year_id FROM enrollments WHERE enrollment_id=%s", (enrollment_id,))
        enr = cur.fetchone()
        if not enr:
            return redirect(url_for("student_portal.dashboard"))

        section_id = enr["section_id"]
        year_id = enr["year_id"]

        if not section_id:
            flash("You have not been assigned to a section yet. Please contact your school admin.", "warning")
            return render_template("student_quizzes.html", quizzes=[], timedelta=timedelta, now_utc=now_naive)

        cur.execute("""
            SELECT
                e.exam_id, e.title, e.exam_type, e.duration_mins,
                e.scheduled_start, e.status, e.grading_period,
                sub.name AS subject_name,
                (SELECT COUNT(*) FROM exam_questions q WHERE q.exam_id = e.exam_id) AS question_count,
                r.result_id, r.score, r.total_points, r.status AS result_status,
                r.submitted_at,
                ext.new_due_date AS individual_extension
            FROM exams e
            JOIN subjects sub ON e.subject_id = sub.subject_id
            LEFT JOIN exam_results r
                ON r.exam_id = e.exam_id AND r.enrollment_id = %s
            LEFT JOIN individual_extensions ext
                ON ext.item_id = e.exam_id AND ext.enrollment_id = %s AND ext.item_type = 'quiz'
            WHERE e.section_id = %s
              AND COALESCE(e.year_id, %s) = %s
              AND LOWER(COALESCE(e.status, '')) IN ('published', 'closed')
              AND e.exam_type = 'quiz'
            ORDER BY e.created_at DESC
        """, (enrollment_id, enrollment_id, section_id, year_id, year_id))
        quizzes_raw = cur.fetchall() or []

        quizzes = []
        for q in quizzes_raw:
            q = dict(q)
            # Treat individual_extension as a NEW START TIME (Reschedule)
            # If present, it replaces the scheduled_start
            duration = int(q.get("duration_mins") or 0)
            
            if q.get("individual_extension"):
                q["effective_start"] = _to_manila_naive(q["individual_extension"])
                q["effective_end"] = q["effective_start"] + timedelta(minutes=duration)
            else:
                q["effective_start"] = _to_manila_naive(q.get("scheduled_start"))
                if q["effective_start"]:
                    q["effective_end"] = q["effective_start"] + timedelta(minutes=duration)
                else:
                    q["effective_end"] = None

            quizzes.append(q)

        return render_template(
            "student_quizzes.html",
            quizzes=quizzes,
            timedelta=timedelta,
            now_utc=now_naive)
    finally:
        cur.close()
        db.close()


@student_portal_bp.route("/student/exams/<int:exam_id>/take", methods=["GET", "POST"])
def student_exam_take(exam_id):
    if session.get("role") != "student":
        return redirect("/")

    enrollment_id = session.get("enrollment_id")

    db  = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        cur.execute("""
            SELECT e.*, sub.name AS subject_name, s.section_name,
                   ext.new_due_date AS individual_extension
            FROM exams e
            JOIN subjects sub ON e.subject_id = sub.subject_id
            JOIN sections s   ON e.section_id  = s.section_id
            JOIN enrollments en ON en.section_id = e.section_id
            LEFT JOIN individual_extensions ext
                ON ext.item_id = e.exam_id AND ext.enrollment_id = %s AND ext.item_type IN ('exam', 'quiz')
            WHERE e.exam_id = %s
              AND en.enrollment_id = %s
              AND COALESCE(e.year_id, en.year_id) = en.year_id
              AND LOWER(COALESCE(e.status, '')) = 'published'
        """, (enrollment_id, exam_id, enrollment_id))
        exam = cur.fetchone()
        if not exam:
            flash("Exam not available.", "error")
            return redirect(url_for("student_portal.student_exams"))

        # ✅ Determine type + correct back URL
        now_naive = _to_manila_naive(datetime.now(timezone.utc))
        is_quiz  = exam.get("exam_type") == "quiz"
        back_url = url_for("student_portal.student_quizzes") if is_quiz else url_for("student_portal.student_exams")

        # ✅ Effective Timing Logic (Individual Rescheduling)
        duration = int(exam["duration_mins"] or 0)
        if exam["individual_extension"]:
            effective_start = _to_manila_naive(exam["individual_extension"])
            effective_end   = effective_start + timedelta(minutes=duration)
        else:
            effective_start = _to_manila_naive(exam["scheduled_start"])
            effective_end   = (effective_start + timedelta(minutes=duration)) if effective_start else None

        if effective_start and now_naive < effective_start:
            flash("This quiz has not started yet." if is_quiz else "This exam has not started yet.", "warning")
            return redirect(back_url)

        if effective_end and now_naive > effective_end:
            flash("This quiz has already ended." if is_quiz else "This exam has already ended.", "warning")
            return redirect(back_url)
        
        # ✅ Max attempts check
        cur.execute("""
            SELECT COUNT(*) AS cnt FROM exam_results
            WHERE exam_id=%s AND enrollment_id=%s
            AND status IN ('submitted', 'auto_submitted')
        """, (exam_id, enrollment_id))
        attempt_count = cur.fetchone()["cnt"]
        max_attempts  = exam["max_attempts"] or 1
        if attempt_count >= max_attempts:
            flash(f"You have reached the maximum attempts ({max_attempts}).", "warning")
            return redirect(back_url)

        # ✅ Check if already submitted
        cur.execute("""
            SELECT * FROM exam_results
            WHERE exam_id=%s AND enrollment_id=%s
        """, (exam_id, enrollment_id))
        existing = cur.fetchone()
        if existing and existing["status"] in ("submitted", "auto_submitted"):
            flash("You have already submitted this.", "warning")
            return redirect(url_for("student_portal.student_exam_result",
                                    result_id=existing["result_id"]))

        if request.method == "POST":
            result_id    = request.form.get("result_id")
            tab_switches = int(request.form.get("tab_switches", 0))
            submit_type  = request.form.get("submit_type", "manual")
            status       = "auto_submitted" if submit_type == "auto" else "submitted"

            if not result_id:
                flash("Session error. Please try again.", "error")
                return redirect(back_url)

            cur.execute("SELECT * FROM exam_questions WHERE exam_id=%s ORDER BY order_num",
                        (exam_id,))
            questions    = cur.fetchall()
            score        = 0
            total_points = 0

            for q in questions:
                ans        = (request.form.get(f"answer_{q['question_id']}") or "").strip()
                correct    = str(q["correct_answer"]).strip()
                is_correct = ans.upper() == correct.upper()
                if is_correct:
                    score += q["points"]
                total_points += q["points"]

                cur.execute("""
                    INSERT INTO exam_answers (result_id, question_id, student_answer, is_correct)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (result_id, q["question_id"], ans, is_correct))

            cur.execute("""
                UPDATE exam_results
                SET score=%s, total_points=%s, status=%s,
                    submitted_at=NOW(), tab_switches=%s
                WHERE result_id=%s AND enrollment_id=%s
            """, (score, total_points, status, tab_switches, result_id, enrollment_id))
            db.commit()
            return redirect(url_for("student_portal.student_exam_result",
                                    result_id=result_id))

        # GET — show instructions page first if not yet confirmed
        if exam.get("instructions") and not request.args.get("start"):
            return render_template("student_exam_instructions.html", exam=exam)

        # GET — create or resume result row
        if existing and existing["status"] == "in_progress":
            result_id  = existing["result_id"]
            started_at = existing["started_at"]
        else:
            cur.execute("""
                INSERT INTO exam_results (exam_id, enrollment_id, status, started_at)
                VALUES (%s, %s, 'in_progress', NOW())
                RETURNING result_id, started_at
            """, (exam_id, enrollment_id))
            row        = cur.fetchone()
            result_id  = row["result_id"]
            started_at = row["started_at"]
            db.commit()

        # ✅ Timezone-safe remaining time
        now_utc       = datetime.now(timezone.utc).replace(tzinfo=None)
        started_naive = started_at.replace(tzinfo=None)
        elapsed       = int((now_utc - started_naive).total_seconds())
        total_secs    = int(exam["duration_mins"]) * 60
        remaining     = max(0, total_secs - elapsed)

        if remaining <= 0:
            flash("Time has expired.", "warning")
            return redirect(back_url)

        cur.execute("SELECT * FROM exam_questions WHERE exam_id=%s ORDER BY order_num",
                    (exam_id,))
        questions = cur.fetchall()

        # ✅ Randomize question order
        if exam.get("randomize"):
            import random
            questions = list(questions)
            random.shuffle(questions)

        shared_matching_opts = None
        for q in questions:
            if q["choices"]:
                q["choices"] = json.loads(q["choices"]) if isinstance(q["choices"], str) else q["choices"]

            if q.get("question_type") == "matching" and q.get("choices") and "options" in q["choices"]:
                if shared_matching_opts is None:
                    import random
                    shared_matching_opts = list(q["choices"]["options"])
                    random.shuffle(shared_matching_opts)
                q["choices"]["options"] = shared_matching_opts

        cur.execute("SELECT tab_switches FROM exam_results WHERE result_id=%s", (result_id,))
        tab_row = cur.fetchone()
        current_tab_switches = tab_row["tab_switches"] if tab_row else 0

        return render_template("student_exam_take.html",
                               exam=exam,
                               questions=questions,
                               result_id=result_id,
                               remaining_secs=remaining,
                               current_tab_switches=current_tab_switches)
    finally:
        cur.close()
        db.close()


@student_portal_bp.route("/student/exams/tab-switch", methods=["POST"])
def student_exam_tab_switch():
    """AJAX endpoint — called every time student switches tab"""
    if session.get("role") != "student":
        return jsonify({"ok": False}), 403

    data      = request.get_json()
    result_id = data.get("result_id")
    enrollment_id = session.get("enrollment_id")

    if not result_id:
        return jsonify({"ok": False}), 400

    db  = get_db_connection()
    cur = db.cursor()
    try:
        # Verify ownership
        cur.execute("SELECT 1 FROM exam_results WHERE result_id=%s AND enrollment_id=%s",
                    (result_id, enrollment_id))
        if not cur.fetchone():
            return jsonify({"ok": False}), 403

        cur.execute("INSERT INTO exam_tab_switches (result_id) VALUES (%s)", (result_id,))
        cur.execute("UPDATE exam_results SET tab_switches = tab_switches + 1 WHERE result_id=%s",
                    (result_id,))
        db.commit()
        return jsonify({"ok": True})
    except Exception:
        db.rollback()
        return jsonify({"ok": False}), 500
    finally:
        cur.close()
        db.close()


@student_portal_bp.route("/student/exams/result/<int:result_id>")
def student_exam_result(result_id):
    if session.get("role") != "student":
        return redirect("/")

    enrollment_id = session.get("enrollment_id")

    db  = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
            SELECT r.*, e.title, e.exam_type, e.duration_mins,
                   e.passing_score, e.subject_id,
                   sub.name AS subject_name
            FROM exam_results r
            JOIN exams e      ON r.exam_id = e.exam_id
            JOIN subjects sub ON e.subject_id = sub.subject_id
            WHERE r.result_id=%s AND r.enrollment_id=%s
        """, (result_id, enrollment_id))
        result = cur.fetchone()
        if not result:
            flash("Result not found.", "error")
            return redirect(url_for("student_portal.student_exams"))

        cur.execute("""
            SELECT q.question_text, q.question_type, q.choices,
                   q.correct_answer, q.points,
                   a.student_answer, a.is_correct
            FROM exam_questions q
            LEFT JOIN exam_answers a
                ON a.question_id = q.question_id AND a.result_id = %s
            WHERE q.exam_id = %s
            ORDER BY q.order_num
        """, (result_id, result["exam_id"]))
        answers = cur.fetchall() or []

        for a in answers:
            if a["choices"]:
                a["choices"] = json.loads(a["choices"]) if isinstance(a["choices"], str) else a["choices"]

        percentage = round((result["score"] / result["total_points"] * 100), 1) \
                     if result["total_points"] else 0

        # ✅ 5. Passing score check
        passing_score = result["passing_score"] or 75
        passed        = percentage >= passing_score

        return render_template("student_exam_result.html",
                               result=result,
                               answers=answers,
                               percentage=percentage,
                               passed=passed,
                               passing_score=passing_score)
    finally:
        cur.close()
        db.close()


# ══════════════════════════════════════════════════════════════
# GRADES VIEW — STUDENT PORTAL
# ══════════════════════════════════════════════════════════════

GRADING_PERIODS = ["1st", "2nd", "3rd", "4th"]


@student_portal_bp.route("/student/grades")
def student_grades():
    if not _require_student():
        return redirect("/")

    user_id       = session.get("user_id")
    curr_enr_id   = session.get("enrollment_id") # Anchor
    selected_enrollment_id = request.args.get("enrollment_id", type=int)
    
    db  = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        # 0. Get the "Anchor" enrollment to find who this student is
        anchor_enr = None
        if curr_enr_id:
            cur.execute("SELECT * FROM enrollments WHERE enrollment_id = %s", (curr_enr_id,))
            anchor_enr = cur.fetchone()

        # 1. Fetch ALL enrollments for this student (by user_id or name/branch_no)
        all_enrollments = []
        if anchor_enr:
            # We have a current enrollment, find all related ones:
            # 1. Match by user_id if valid
            # 2. Match by student_name
            cur.execute("""
                SELECT e.enrollment_id, e.student_name, e.section_id, e.status, e.branch_enrollment_no,
                       s.section_name, s.school_year, gl.name as grade_level_name
                FROM enrollments e
                LEFT JOIN sections s ON e.section_id = s.section_id
                LEFT JOIN grade_levels gl ON s.grade_level_id = gl.id
                WHERE (e.enrollment_id = %s)
                   OR (e.user_id IS NOT NULL AND e.user_id = %s)
                   OR (e.student_name = %s)
                ORDER BY e.created_at DESC
            """, (curr_enr_id, anchor_enr['user_id'], anchor_enr['student_name']))
            all_enrollments = cur.fetchall() or []
        elif user_id:
            # Fallback if no curr_enr_id but have user_id
            cur.execute("""
                SELECT e.enrollment_id, e.student_name, e.section_id, e.status, e.branch_enrollment_no,
                       s.section_name, s.school_year, gl.name as grade_level_name
                FROM enrollments e
                LEFT JOIN sections s ON e.section_id = s.section_id
                LEFT JOIN grade_levels gl ON s.grade_level_id = gl.id
                WHERE e.user_id = %s
                ORDER BY e.created_at DESC
            """, (user_id,))
            all_enrollments = cur.fetchall() or []

        if not all_enrollments:
            # Provide empty placeholders instead of redirecting
            return render_template("student_grades.html",
                                   student={"student_name": session.get("username", "Student")},
                                   all_enrollments=[],
                                   selected_enrollment_id=None,
                                   grade_data=[],
                                   grading_periods=GRADING_PERIODS)

        # 2. Determine which enrollment to show
        enr = None
        if selected_enrollment_id:
            enr = next((e for e in all_enrollments if e['enrollment_id'] == selected_enrollment_id), None)
        
        if not enr:
            # Try to match the session one first
            sess_eid = session.get("enrollment_id")
            enr = next((e for e in all_enrollments if e['enrollment_id'] == sess_eid), None)
            
            # If still no match or no section, try to find the newest one THAT HAS a section
            if not enr or not enr.get("section_id"):
                enr_with_section = next((e for e in all_enrollments if e.get("section_id")), None)
                if enr_with_section:
                    enr = enr_with_section
                else:
                    # Absolute fallback to the first one available
                    enr = all_enrollments[0]
        
        enrollment_id = enr["enrollment_id"]
        section_id    = enr["section_id"]

        if not section_id:
            # flash(f"No section assigned for {enr.get('school_year', 'this term')}.", "warning")
            subjects = []
            posted_map = {}
        else:
            # 3. Get subjects for this specific enrollment's section
            cur.execute("""
                SELECT sub.subject_id, sub.name AS subject_name
                FROM section_teachers st
                JOIN subjects sub ON st.subject_id = sub.subject_id
                WHERE st.section_id = %s
                ORDER BY sub.name
            """, (section_id,))
            subjects = cur.fetchall() or []

            # 4. Get posted grades
            cur.execute("""
                SELECT subject_id, grading_period, grade
                FROM posted_grades
                WHERE enrollment_id = %s
            """, (enrollment_id,))
            posted = cur.fetchall() or []

            posted_map = {}
            for p in posted:
                sid = p["subject_id"]
                if sid not in posted_map: posted_map[sid] = {}
                # Round to nearest integer for student view
                posted_map[sid][p["grading_period"]] = int(round(float(p["grade"])))

        # Final record list
        grade_data = []
        for s in subjects:
            sid = s["subject_id"]
            grades = posted_map.get(sid, {})
            period_vals = [float(v) for v in grades.values()]
            # Final average only shows if ALL 4 periods are posted (rounded to whole number)
            final_avg = int(round(sum(period_vals) / 4)) if len(period_vals) == 4 else None

            grade_data.append({
                "subject_name": s["subject_name"],
                "units":        3, # Default
                "grades":       grades,
                "final_grade":  final_avg
            })

        return render_template("student_grades.html",
                               student=enr,
                               all_enrollments=all_enrollments,
                               selected_enrollment_id=enrollment_id,
                               grade_data=grade_data,
                               grading_periods=GRADING_PERIODS)
    finally:
        cur.close()
        db.close()


@student_portal_bp.route("/student/my-schedule")
def student_my_schedule():
    if not _require_student():
        return redirect("/")

    enrollment_id = session.get("enrollment_id")
    branch_id     = session.get("branch_id")   # ✅ safe .get() — avoids KeyError

    db  = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        # Get enrollment info (section, grade level, branch)
        cur.execute("""
            SELECT e.enrollment_id, e.student_name, e.grade_level,
                   e.section_id, e.branch_id, e.year_id,
                   s.section_name, s.school_year
            FROM enrollments e
            LEFT JOIN sections s ON e.section_id = s.section_id
            WHERE e.enrollment_id = %s
        """, (enrollment_id,))
        enr = cur.fetchone()

        if not enr:
            flash("Enrollment record not found.", "error")
            return redirect(url_for("student_portal.dashboard"))

        # Use branch_id from enrollment if not in session
        effective_branch_id = enr["branch_id"] or branch_id
        section_id = enr["section_id"]

        schedules = []
        if section_id:
            cur.execute("""
                SELECT sc.*,
                       sub.name AS subject_name,
                       u.full_name AS teacher_name
                FROM schedules sc
                LEFT JOIN subjects sub ON sc.subject_id = sub.subject_id
                LEFT JOIN users u ON sc.teacher_id = u.user_id
                WHERE sc.section_id = %s
                  AND sc.year_id = %s
                  AND sc.is_archived = FALSE
                ORDER BY
                    CASE sc.day_of_week
                        WHEN 'Monday'    THEN 1
                        WHEN 'Tuesday'   THEN 2
                        WHEN 'Wednesday' THEN 3
                        WHEN 'Thursday'  THEN 4
                        WHEN 'Friday'    THEN 5
                        WHEN 'Saturday'  THEN 6
                        WHEN 'Sunday'    THEN 7
                        ELSE 8
                    END,
                    sc.start_time
            """, (section_id, enr.get("year_id")))
            schedules = cur.fetchall() or []

        return render_template("student_my_schedule.html",
                               enrollment=enr,
                               schedules=schedules)
    finally:
        cur.close()
        db.close()


@student_portal_bp.route("/student/profile")
def student_profile():
    if not _require_student():
        return redirect("/")

    enrollment_id = session.get("enrollment_id")
    if not enrollment_id:
        flash("Enrollment ID not found.", "error")
        return redirect("/")

    db = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
            SELECT e.enrollment_id, e.branch_enrollment_no, e.student_name, e.grade_level, e.status, e.profile_image,
                   e.gender, e.dob, e.address, e.contact_number, e.guardian_name, e.guardian_contact,
                   e.previous_school, e.email, e.guardian_email, e.lrn,
                   s.section_name,
                   br.branch_name, br.location
            FROM enrollments e
            LEFT JOIN sections s ON e.section_id = s.section_id
            JOIN branches br ON e.branch_id = br.branch_id
            WHERE e.enrollment_id = %s
        """, (enrollment_id,))
        student = cur.fetchone()

        if not student:
            flash("Student profile not found.", "error")
            return redirect(url_for("student_portal.dashboard"))
        
        return render_template("student_profile.html", student=student)
    finally:
        cur.close()
        db.close()

