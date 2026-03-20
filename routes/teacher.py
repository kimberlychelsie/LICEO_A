import re as _re
from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify
from db import get_db_connection
import psycopg2.extras
from cloudinary_helper import upload_file
import os
import json
import pandas as pd
import pdfplumber
from docx import Document
from datetime import timezone
import pytz

teacher_bp = Blueprint("teacher", __name__)

GRADE_LEVELS = [
    "Kinder", "Grade 1", "Grade 2", "Grade 3",
    "Grade 4", "Grade 5", "Grade 6",
    "Grade 7", "Grade 8", "Grade 9", "Grade 10",
    "Grade 11", "Grade 12",
]


# ── helpers ──────────────────────────────────────────────
def _require_teacher():
    return session.get("role") == "teacher"


def _normalize_grade(grade_str):
    """Accept both '7' and 'Grade 7' — returns (grade_full, grade_short)."""
    m = _re.match(r'^Grade\s+(\d+)$', grade_str, _re.IGNORECASE)
    num = m.group(1) if m else None
    return grade_str, (num or grade_str)

def parse_docx(file):
    """Parse questions from a .docx file."""
    questions = []
    document = Document(file)
    current_question = {}

    for para in document.paragraphs:
        line = para.text.strip()
        if not line:
            continue

        if line.lower().startswith('question:'):
            if current_question:
                questions.append(current_question)
                current_question = {}
            current_question['question_text'] = line.split(':', 1)[1].strip()
        elif line.lower().startswith('type:'):
            current_question['question_type'] = line.split(':', 1)[1].strip()
        elif line.lower().startswith('a:'):
            current_question['choice_a'] = line.split(':', 1)[1].strip()
        elif line.lower().startswith('b:'):
            current_question['choice_b'] = line.split(':', 1)[1].strip()
        elif line.lower().startswith('c:'):
            current_question['choice_c'] = line.split(':', 1)[1].strip()
        elif line.lower().startswith('d:'):
            current_question['choice_d'] = line.split(':', 1)[1].strip()
        elif line.lower().startswith('answer:'):
            current_question['correct_answer'] = line.split(':', 1)[1].strip()
        elif line.lower().startswith('points:'):
            current_question['points'] = line.split(':', 1)[1].strip()

    if current_question:
        questions.append(current_question)

    return questions


def parse_pdf(file):
    """Parse questions from a .pdf file."""
    questions = []
    current_question = {}

    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
            for line in text.split('\n'):
                line = line.strip()
                if not line:
                    continue

                if line.lower().startswith('question:'):
                    if current_question:
                        questions.append(current_question)
                        current_question = {}
                    current_question['question_text'] = line.split(':', 1)[1].strip()
                elif line.lower().startswith('type:'):
                    current_question['question_type'] = line.split(':', 1)[1].strip()
                elif line.lower().startswith('a:'):
                    current_question['choice_a'] = line.split(':', 1)[1].strip()
                elif line.lower().startswith('b:'):
                    current_question['choice_b'] = line.split(':', 1)[1].strip()
                elif line.lower().startswith('c:'):
                    current_question['choice_c'] = line.split(':', 1)[1].strip()
                elif line.lower().startswith('d:'):
                    current_question['choice_d'] = line.split(':', 1)[1].strip()
                elif line.lower().startswith('answer:'):
                    current_question['correct_answer'] = line.split(':', 1)[1].strip()
                elif line.lower().startswith('points:'):
                    current_question['points'] = line.split(':', 1)[1].strip()

    if current_question:
        questions.append(current_question)

    return questions



# ── Dashboard ─────────────────────────────────────────────
@teacher_bp.route("/teacher")
def teacher_dashboard():
    if not _require_teacher():
        return redirect("/")

    user_id   = session.get("user_id")
    branch_id = session.get("branch_id")

    db = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
        SELECT COALESCE(g.name, u.grade_level) AS grade_level
        FROM users u
        LEFT JOIN grade_levels g ON u.grade_level_id = g.id
        WHERE u.user_id = %s
    """, (user_id,))
        row = cur.fetchone()
        teacher_grade = row["grade_level"] if row else None
    finally:
        cur.close()
        db.close()

    selected_grade = (request.args.get("grade") or teacher_grade or "").strip()
    selected_section_id = request.args.get("section_id", type=int)

    students = []
    announcements = []
    teacher_assignments = []
    stats = {"total": 0, "cleared": 0, "pending_bill": 0,
             "reserved": 0, "claimed": 0, "no_reservation": 0}

    if selected_grade:
        grade_full, grade_short = _normalize_grade(selected_grade)

        db  = get_db_connection()
        cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            # ── Students ──
            query_str = """
                SELECT
                    e.enrollment_id,
                    e.student_name,
                    e.grade_level,
                    e.status            AS enrollment_status,

                    COALESCE((
                        SELECT CASE
                            WHEN SUM(b.total_amount - COALESCE(b.amount_paid,0)) <= 0
                            THEN 'CLEARED' ELSE 'PENDING'
                        END
                        FROM billing b
                        WHERE b.enrollment_id = e.enrollment_id
                    ), 'NO_BILL') AS billing_status,

                    COALESCE((
                        SELECT UPPER(r.status)
                        FROM reservations r
                        WHERE r.enrollment_id = e.enrollment_id
                          AND r.branch_id = %(branch_id)s
                        ORDER BY r.created_at DESC
                        LIMIT 1
                    ), 'NONE') AS reservation_status

                FROM enrollments e
                WHERE e.branch_id = %(branch_id)s
                  AND (
                      e.grade_level ILIKE %(grade_full)s
                      OR e.grade_level ILIKE %(grade_short)s
                  )
                  AND e.status IN ('approved', 'enrolled')
            """
            
            query_params = {
                "branch_id":   branch_id,
                "grade_full":  grade_full,
                "grade_short": grade_short,
            }
            
            if selected_section_id:
                query_str += " AND e.section_id = %(section_id)s "
                query_params["section_id"] = selected_section_id
                
            query_str += " ORDER BY e.student_name ASC "
            
            cur.execute(query_str, query_params)
            students = cur.fetchall() or []

            stats["total"] = len(students)
            for s in students:
                billing = (s["billing_status"] or "").upper()
                if billing == "CLEARED":
                    stats["cleared"] += 1
                elif billing in ("PENDING", "NO_BILL"):
                    stats["pending_bill"] += 1

                res = (s["reservation_status"] or "").upper()
                if res == "CLAIMED":
                    stats["claimed"] += 1
                elif res in ("PENDING", "RESERVED"):
                    stats["reserved"] += 1
                else:
                    stats["no_reservation"] += 1

            # ── Announcements for this grade ──
            cur.execute("""
                SELECT a.announcement_id, a.title, a.body,
                       a.created_at, u.username AS posted_by,
                       u.full_name, u.gender
                FROM teacher_announcements a
                JOIN users u ON u.user_id = a.teacher_user_id
                WHERE a.branch_id   = %(branch_id)s
                  AND (
                      a.grade_level ILIKE %(grade_full)s
                      OR a.grade_level ILIKE %(grade_short)s
                  )
                ORDER BY a.created_at DESC
            """, {
                "branch_id":   branch_id,
                "grade_full":  grade_full,
                "grade_short": grade_short,
            })
            raw_ann = cur.fetchall() or []

            # Build display name: "Ms. Joy Cruz" or "Mr. Juan dela Cruz"
            announcements = []
            for a in raw_ann:
                a = dict(a)
                prefix = ""
                if a.get("gender") == "female":
                    prefix = "Ms. "
                elif a.get("gender") == "male":
                    prefix = "Mr. "
                a["display_name"] = prefix + (a.get("full_name") or a.get("posted_by") or "Teacher")
                announcements.append(a)

            # ── Sections + subjects assigned to this teacher (for this branch) ──
            cur.execute(
                """
                SELECT
                    s.section_id,
                    s.section_name,
                    g.name  AS grade_level_name,
                    sub.subject_id,
                    sub.name AS subject_name
                FROM section_teachers st
                JOIN sections s     ON st.section_id = s.section_id
                JOIN grade_levels g ON s.grade_level_id = g.id
                JOIN subjects sub   ON st.subject_id  = sub.subject_id
                WHERE st.teacher_id = %s
                  AND s.branch_id   = %s
                ORDER BY g.display_order, s.section_name, sub.name
                """,
                (user_id, branch_id),
            )
            teacher_assignments = cur.fetchall() or []

        finally:
            cur.close()
            db.close()

    return render_template(
        "teacher_dashboard.html",
        students=students,
        stats=stats,
        teacher_grade=teacher_grade,
        selected_grade=selected_grade,
        grade_levels=GRADE_LEVELS,
        announcements=announcements,
        teacher_assignments=teacher_assignments,
        teacher_user_id=session.get("user_id"),
        selected_section_id=selected_section_id,
    )


# ── Save grade assignment ─────────────────────────────────
@teacher_bp.route("/teacher/set-grade", methods=["POST"])
def teacher_set_grade():
    if not _require_teacher():
        return redirect("/")

    user_id = session.get("user_id")
    grade   = (request.form.get("grade_level") or "").strip()

    if grade not in GRADE_LEVELS:
        flash("Invalid grade level.", "error")
        return redirect(url_for("teacher.teacher_dashboard"))

    db  = get_db_connection()
    cur = db.cursor()
    try:
        # Check if branch admin already assigned a grade — if so, block the change
        cur.execute("""
    SELECT g.name AS grade_level
    FROM users u
    LEFT JOIN grade_levels g ON u.grade_level_id = g.id
    WHERE u.user_id = %s
""", (user_id,))
        row = cur.fetchone()
        existing_grade = row[0] if row else None

        if existing_grade:
            flash(f"Your grade level ({existing_grade}) is assigned by the Branch Admin and cannot be changed.", "warning")
            return redirect(url_for("teacher.teacher_dashboard") + f"?grade={existing_grade}")

        cur.execute(
            "UPDATE users SET grade_level = %s WHERE user_id = %s",
            (grade, user_id)
        )
        db.commit()
        flash(f"Grade level set to {grade}.", "success")

    except Exception as e:
        db.rollback()
        flash(str(e), "error")
    finally:
        cur.close()
        db.close()

    return redirect(url_for("teacher.teacher_dashboard") + f"?grade={grade}")


# ── Post Announcement ─────────────────────────────────────
@teacher_bp.route("/teacher/announce", methods=["POST"])
def teacher_announce():
    if not _require_teacher():
        return redirect("/")

    user_id   = session.get("user_id")
    branch_id = session.get("branch_id")
    title     = (request.form.get("title") or "").strip()
    body      = (request.form.get("body")  or "").strip()
    grade     = (request.form.get("grade_level") or "").strip()

    # grade comes from hidden field (current selected_grade in dashboard)
    back_url = url_for("teacher.teacher_dashboard") + (f"?grade={grade}" if grade else "")

    if not title:
        flash("Announcement title is required.", "error")
        return redirect(back_url)

    if not grade:
        flash("Please select your grade level first.", "error")
        return redirect(url_for("teacher.teacher_dashboard"))

    db  = get_db_connection()
    cur = db.cursor()
    try:
        cur.execute("""
            INSERT INTO teacher_announcements
                (teacher_user_id, branch_id, grade_level, title, body)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING announcement_id
        """, (user_id, branch_id, grade, title, body or None))
        ann_id = cur.fetchone()[0]

        # Send Notifications to students in this grade level
        import re as _re
        if _re.match(r'^\d+$', grade.strip()):
            grade_short = grade.strip()
            grade_full  = "Grade " + grade_short
        else:
            grade_full  = grade.strip()
            _m2 = _re.match(r'^Grade\s+(\d+)$', grade_full, _re.IGNORECASE)
            grade_short = _m2.group(1) if _m2 else grade_full

        cur.execute("""
            SELECT DISTINCT u.user_id 
            FROM enrollments e
            JOIN users u ON u.user_id = e.user_id
            WHERE e.branch_id = %s 
              AND (e.grade_level ILIKE %s OR e.grade_level ILIKE %s)
              AND e.status IN ('approved', 'enrolled')
            UNION
            SELECT DISTINCT u.user_id
            FROM enrollments e
            JOIN student_accounts sa ON sa.enrollment_id = e.enrollment_id
            JOIN users u ON u.username = sa.username
            WHERE e.branch_id = %s 
              AND (e.grade_level ILIKE %s OR e.grade_level ILIKE %s)
              AND e.status IN ('approved', 'enrolled')
        """, (branch_id, grade_full, grade_short, branch_id, grade_full, grade_short))
        students = cur.fetchall()
        if students:
            notif_title = f"New Announcement: {title}"
            notif_msg = f"Your teacher posted a new announcement."
            for s in students:
                cur.execute("""
                    INSERT INTO student_notifications (student_id, title, message, link)
                    VALUES (%s, %s, %s, %s)
                """, (s[0], notif_title, notif_msg, f"/student/dashboard"))

        db.commit()
        flash("Announcement posted! Students in your class will see it.", "success")
    except Exception as e:
        db.rollback()
        flash(f"Could not post announcement: {e}", "error")
    finally:
        cur.close()
        db.close()

    return redirect(back_url)


# ── Delete Announcement ───────────────────────────────────
@teacher_bp.route("/teacher/announce/<int:announcement_id>/delete", methods=["POST"])
def teacher_announce_delete(announcement_id):
    if not _require_teacher():
        return redirect("/")

    user_id = session.get("user_id")
    grade   = (request.form.get("grade_level") or "").strip()
    back_url = url_for("teacher.teacher_dashboard") + (f"?grade={grade}" if grade else "")

    db  = get_db_connection()
    cur = db.cursor()
    try:
        # Only allow deleting own announcements
        cur.execute("""
            DELETE FROM teacher_announcements
            WHERE announcement_id = %s AND teacher_user_id = %s
        """, (announcement_id, user_id))
        db.commit()
        if cur.rowcount:
            flash("Announcement deleted.", "success")
        else:
            flash("Announcement not found or not yours.", "error")
    except Exception as e:
        db.rollback()
        flash(str(e), "error")
    finally:
        cur.close()
        db.close()

    return redirect(back_url)


# ── Edit Announcement ─────────────────────────────────────
@teacher_bp.route("/teacher/announce/<int:announcement_id>/edit", methods=["POST"])
def teacher_announce_edit(announcement_id):
    if not _require_teacher():
        return redirect("/")

    user_id = session.get("user_id")
    grade   = (request.form.get("grade_level") or "").strip()
    title   = (request.form.get("title") or "").strip()
    body    = (request.form.get("body")  or "").strip()
    back_url = url_for("teacher.teacher_dashboard") + (f"?grade={grade}" if grade else "")

    if not title:
        flash("Title cannot be empty.", "error")
        return redirect(back_url)

    db  = get_db_connection()
    cur = db.cursor()
    try:
        cur.execute("""
            UPDATE teacher_announcements
               SET title = %s, body = %s
             WHERE announcement_id = %s AND teacher_user_id = %s
        """, (title, body or None, announcement_id, user_id))
        db.commit()
        if cur.rowcount:
            flash("Announcement updated.", "success")
        else:
            flash("Announcement not found or not yours.", "error")
    except Exception as e:
        db.rollback()
        flash(str(e), "error")
    finally:
        cur.close()
        db.close()

    return redirect(back_url)


# ── DELETE ROUTES ──────────────────────────────────────────

@teacher_bp.route("/teacher/activities/<int:activity_id>/delete", methods=["POST"])
def delete_activity(activity_id):
    if not _require_teacher(): return redirect("/")
    user_id = session.get("user_id")
    db = get_db_connection()
    cur = db.cursor()
    try:
        cur.execute("SELECT activity_id FROM activities WHERE activity_id=%s AND teacher_id=%s", (activity_id, user_id))
        if not cur.fetchone():
            flash("Activity not found or unauthorized.", "error")
            return redirect(url_for("teacher.activities"))
        # Cascade delete
        cur.execute("DELETE FROM activity_grades WHERE activity_id=%s", (activity_id,))
        cur.execute("DELETE FROM activity_submissions WHERE activity_id=%s", (activity_id,))
        cur.execute("DELETE FROM student_notifications WHERE link LIKE %s", (f"%/student/activities/{activity_id}%",))
        cur.execute("DELETE FROM activities WHERE activity_id=%s AND teacher_id=%s", (activity_id, user_id))
        db.commit()
        flash("Activity deleted successfully.", "success")
    except Exception as e:
        db.rollback()
        flash(f"Could not delete: {str(e)}", "error")
    finally:
        cur.close()
        db.close()
    return redirect(url_for("teacher.activities"))


@teacher_bp.route("/teacher/exams/<int:exam_id>/delete", methods=["POST"])
def delete_exam(exam_id):
    if not _require_teacher(): return redirect("/")
    user_id = session.get("user_id")
    db = get_db_connection()
    cur = db.cursor()
    try:
        cur.execute("SELECT exam_id, exam_type FROM exams WHERE exam_id=%s AND teacher_id=%s", (exam_id, user_id))
        row = cur.fetchone()
        if not row:
            flash("Not found or unauthorized.", "error")
            return redirect(url_for("teacher.teacher_exams"))
        is_quiz = (row[1] if isinstance(row, tuple) else row.get("exam_type")) == "quiz"
        # Cascade delete
        cur.execute("DELETE FROM exam_results WHERE exam_id=%s", (exam_id,))
        cur.execute("DELETE FROM exam_questions WHERE exam_id=%s", (exam_id,))
        cur.execute("DELETE FROM student_notifications WHERE link LIKE %s", (f"%/student/exams%",))
        cur.execute("DELETE FROM exams WHERE exam_id=%s AND teacher_id=%s", (exam_id, user_id))
        db.commit()
        flash("Deleted successfully.", "success")
        return redirect(url_for("teacher.teacher_quizzes") if is_quiz else url_for("teacher.teacher_exams"))
    except Exception as e:
        db.rollback()
        flash(f"Could not delete: {str(e)}", "error")
        return redirect(url_for("teacher.teacher_exams"))
    finally:
        cur.close()
        db.close()


# ── ACTIVITIES MODULE (TEACHER SIDE) ──────────────────────

@teacher_bp.route("/teacher/activities")
def activities():
    if not _require_teacher(): return redirect("/")
    user_id = session.get("user_id")
    branch_id = session.get("branch_id")
    
    db = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute('''
            SELECT a.*, 
                   s.section_name, 
                   sub.name AS subject_name,
                   (SELECT COUNT(*) FROM activity_submissions sub2 WHERE sub2.activity_id = a.activity_id) AS submission_count
            FROM activities a
            JOIN sections s ON a.section_id = s.section_id
            JOIN subjects sub ON a.subject_id = sub.subject_id
            WHERE a.teacher_id = %s AND a.branch_id = %s
            ORDER BY a.created_at DESC
        ''', (user_id, branch_id))
        activities = cur.fetchall()
        
        stats = {
            'total': len(activities),
            'published': sum(1 for a in activities if a['status'] == 'Published'),
            'drafts': sum(1 for a in activities if a['status'] == 'Draft'),
            'closed': sum(1 for a in activities if a['status'] == 'Closed')
        }
    finally:
        cur.close()
        db.close()
        
    return render_template("teacher_activities.html", activities=activities, stats=stats)


@teacher_bp.route("/teacher/activities/create", methods=["GET", "POST"])
def create_activity():
    if not _require_teacher(): return redirect("/")
    user_id = session.get("user_id")
    branch_id = session.get("branch_id")
    
    db = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    try:
        if request.method == "POST":
            title = request.form.get("title", "").strip()
            assignment = request.form.get("assignment", "") # section_id_subject_id
            category = request.form.get("category", "")
            instructions = request.form.get("instructions", "").strip()
            max_score = int(request.form.get("max_score", 100))
            due_date = request.form.get("due_date", "")
            status = request.form.get("status", "Draft")
            allowed_file_types = request.form.get("allowed_file_types", "").strip()
            grading_period = request.form.get("grading_period")
            
            if "_" not in assignment:
                flash("Invalid section/subject assignment", "error")
                return redirect(url_for("teacher.create_activity"))
            
            section_id, subject_id = assignment.split("_", 1)
            
            attachment_path = None
            if 'attachment' in request.files:
                file = request.files['attachment']
                if file.filename != '':
                    try:
                        attachment_path = upload_file(file, folder="liceo_activities")
                    except Exception as e:
                        flash(f"File upload failed: {e}", "error")
                        return redirect(url_for("teacher.create_activity"))
                        
            cur.execute('''
                INSERT INTO activities (
                    branch_id, section_id, subject_id, teacher_id, 
                    title, category, instructions, max_score, due_date, 
                    status, allowed_file_types, attachment_path, grading_period
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING activity_id
            ''', (branch_id, section_id, subject_id, user_id, 
                  title, category, instructions, max_score, due_date or None, 
                  status, allowed_file_types, attachment_path, grading_period))
            activity_id = cur.fetchone()['activity_id']
            
            if status == 'Published':
                cur.execute("""
                    SELECT DISTINCT u.user_id 
                    FROM enrollments e 
                    JOIN users u ON u.user_id = e.user_id 
                    WHERE e.section_id = %s AND e.status IN ('approved', 'enrolled')
                    UNION
                    SELECT DISTINCT u.user_id
                    FROM enrollments e
                    JOIN student_accounts sa ON sa.enrollment_id = e.enrollment_id
                    JOIN users u ON u.username = sa.username
                    WHERE e.section_id = %s AND e.status IN ('approved', 'enrolled')
                """, (section_id, section_id))
                student_users = cur.fetchall()
                if student_users:
                    notifs = [(su['user_id'], f"New Activity: {title}", f"Your teacher posted a new activity: {title}.", f"/student/activities/{activity_id}") for su in student_users]
                    for notif in notifs:
                        cur.execute("""
                            INSERT INTO student_notifications (student_id, title, message, link) 
                            VALUES (%s, %s, %s, %s)
                        """, notif)
                        
            db.commit()
            
            flash("Activity created successfully!", "success")
            return redirect(url_for("teacher.activities"))
        
        # GET: fetch sections and subjects for this teacher
        cur.execute('''
            SELECT s.section_id, s.section_name, g.name AS grade_level_name, 
                   sub.subject_id, sub.name AS subject_name 
            FROM section_teachers st
            JOIN sections s ON st.section_id = s.section_id
            JOIN grade_levels g ON s.grade_level_id = g.id
            JOIN subjects sub ON st.subject_id = sub.subject_id
            WHERE st.teacher_id = %s AND s.branch_id = %s
            ORDER BY g.display_order, s.section_name, sub.name
        ''', (user_id, branch_id))
        teacher_assignments = cur.fetchall()
        
    finally:
        cur.close()
        db.close()
        
    return render_template("teacher_create_activity.html", teacher_assignments=teacher_assignments)


@teacher_bp.route("/teacher/activities/<int:activity_id>/edit", methods=["GET", "POST"])
def edit_activity(activity_id):
    if not _require_teacher(): return redirect("/")
    user_id = session.get("user_id")
    branch_id = session.get("branch_id")
    
    db = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    try:
        # Check ownership
        cur.execute("SELECT * FROM activities WHERE activity_id = %s AND teacher_id = %s", (activity_id, user_id))
        activity = cur.fetchone()
        if not activity:
            flash("Activity not found or unauthorized.", "error")
            return redirect(url_for("teacher.activities"))
            
        if request.method == "POST":
            title = request.form.get("title", "").strip()
            category = request.form.get("category", "")
            instructions = request.form.get("instructions", "").strip()
            max_score = int(request.form.get("max_score", 100))
            due_date = request.form.get("due_date", "")
            status = request.form.get("status", "Draft")
            allowed_file_types = request.form.get("allowed_file_types", "").strip()
            grading_period = request.form.get("grading_period")
            
            attachment_path = activity['attachment_path']
            if 'attachment' in request.files:
                file = request.files['attachment']
                if file.filename != '':
                    try:
                        attachment_path = upload_file(file, folder="liceo_activities")
                    except Exception as e:
                        flash(f"File upload failed: {e}", "error")
                        return redirect(url_for("teacher.edit_activity", activity_id=activity_id))
            
            cur.execute('''
                UPDATE activities SET
                    title = %s, category = %s, instructions = %s, max_score = %s, 
                    due_date = %s, status = %s, allowed_file_types = %s, attachment_path = %s,
                    grading_period = %s, updated_at = NOW()
                WHERE activity_id = %s
            ''', (title, category, instructions, max_score, due_date or None, 
                  status, allowed_file_types, attachment_path, grading_period, activity_id))
                  
            if status == 'Published' and activity['status'] != 'Published':
                cur.execute("""
                    SELECT DISTINCT u.user_id 
                    FROM enrollments e 
                    JOIN users u ON u.user_id = e.user_id 
                    WHERE e.section_id = %s AND e.status IN ('approved', 'enrolled')
                    UNION
                    SELECT DISTINCT u.user_id
                    FROM enrollments e
                    JOIN student_accounts sa ON sa.enrollment_id = e.enrollment_id
                    JOIN users u ON u.username = sa.username
                    WHERE e.section_id = %s AND e.status IN ('approved', 'enrolled')
                """, (activity['section_id'], activity['section_id']))
                student_users = cur.fetchall()
                if student_users:
                    notifs = [(su['user_id'], f"New Activity: {title}", f"Your teacher posted a new activity: {title}.", f"/student/activities/{activity_id}") for su in student_users]
                    for notif in notifs:
                        cur.execute("""
                            INSERT INTO student_notifications (student_id, title, message, link) 
                            VALUES (%s, %s, %s, %s)
                        """, notif)
            
            db.commit()
            
            flash("Activity updated successfully!", "success")
            return redirect(url_for("teacher.activities"))
            
    finally:
        cur.close()
        db.close()
        
    return render_template("teacher_edit_activity.html", activity=activity)


@teacher_bp.route("/teacher/activities/<int:activity_id>/submissions")
def activity_submissions(activity_id):
    if not _require_teacher(): return redirect("/")
    user_id = session.get("user_id")
    
    db = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        # Get activity context
        cur.execute("SELECT * FROM activities WHERE activity_id = %s AND teacher_id = %s", (activity_id, user_id))
        activity = cur.fetchone()
        if not activity:
            flash("Activity not found or unauthorized", "error")
            return redirect(url_for("teacher.activities"))
            
        # Get all students enrolled in this section/class
        cur.execute('''
            SELECT e.enrollment_id, e.student_name, u.user_id as student_user_id
            FROM enrollments e
            LEFT JOIN users u ON u.user_id = e.user_id
            WHERE e.section_id = %s AND e.status IN ('approved', 'enrolled') AND e.branch_id = %s
            ORDER BY e.student_name ASC
        ''', (activity['section_id'], activity['branch_id']))
        students = cur.fetchall()
        
        # Get all submissions for this activity
        cur.execute('''
            SELECT sub.*, g.grade_id, g.raw_score, g.percentage, g.remarks,
                   ext.new_due_date AS individual_extension
            FROM activity_submissions sub
            LEFT JOIN activity_grades g ON sub.submission_id = g.submission_id
            LEFT JOIN individual_extensions ext ON ext.enrollment_id = sub.enrollment_id AND ext.item_id = %s AND ext.item_type = 'activity'
            WHERE sub.activity_id = %s
            ORDER BY sub.submitted_at ASC
        ''', (activity_id, activity_id))
        submissions_raw = {row['enrollment_id']: row for row in cur.fetchall()}
        
        # Also need students who haven't submitted but might have extensions
        cur.execute('''
            SELECT enrollment_id, new_due_date 
            FROM individual_extensions 
            WHERE item_id = %s AND item_type = 'activity'
        ''', (activity_id,))
        extensions_only = {row['enrollment_id']: row['new_due_date'] for row in cur.fetchall()}
        
        submissions_data = []
        for s in students:
            sub = submissions_raw.get(s['enrollment_id'])
            item = {
                'student_name': s['student_name'],
                'student_user_id': s['student_user_id'],
                'enrollment_id': s['enrollment_id'],
                'individual_extension': extensions_only.get(s['enrollment_id'])
            }
            if sub:
                item.update(sub)
                item['feedback'] = sub['remarks'] # maps correctly
            submissions_data.append(item)
            
        stats = {
            'total': len(students),
            'submitted': sum(1 for s in submissions_data if 'submission_id' in s and s['submission_id']),
            'graded': sum(1 for s in submissions_data if 'grade_id' in s and s['grade_id']),
            'not_submitted': len(students) - sum(1 for s in submissions_data if 'submission_id' in s and s['submission_id'])
        }
    finally:
        cur.close()
        db.close()
        
    return render_template("teacher_activity_submissions.html", activity=activity, submissions=submissions_data, stats=stats)


@teacher_bp.route("/teacher/activities/submissions/<int:submission_id>/grade", methods=["POST"])
def grade_submission(submission_id):
    if not _require_teacher(): return redirect("/")
    user_id = session.get("user_id")
    raw_score = request.form.get("raw_score")
    remarks = request.form.get("remarks", "")
    
    if not raw_score:
        flash("Score is required.", "error")
        return redirect(request.referrer)
        
    raw_score = float(raw_score)
    
    db = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        # Check permissions and get context
        cur.execute('''
            SELECT sub.activity_id, sub.student_id, a.max_score, a.teacher_id
            FROM activity_submissions sub
            JOIN activities a ON sub.activity_id = a.activity_id
            WHERE sub.submission_id = %s
        ''', (submission_id,))
        sub = cur.fetchone()
        
        if not sub or sub['teacher_id'] != user_id:
            flash("Unauthorized or submission not found.", "error")
            return redirect(request.referrer)
            
        if raw_score > sub['max_score']:
            flash(f"Score cannot exceed maximum score ({sub['max_score']}).", "error")
            return redirect(request.referrer)
            
        percentage = (raw_score / sub['max_score']) * 100 if sub['max_score'] > 0 else 0
        
        # Proceed with upserting grade
        cur.execute("SELECT grade_id FROM activity_grades WHERE submission_id = %s", (submission_id,))
        grade = cur.fetchone()
        
        if grade:
            cur.execute('''
                UPDATE activity_grades SET 
                    raw_score = %s, percentage = %s, remarks = %s, updated_at = NOW()
                WHERE grade_id = %s
            ''', (raw_score, percentage, remarks, grade['grade_id']))
        else:
            cur.execute('''
                INSERT INTO activity_grades (submission_id, activity_id, student_id, raw_score, max_score, percentage, remarks)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (submission_id, sub['activity_id'], sub['student_id'], raw_score, sub['max_score'], percentage, remarks))
            
        # Update submission status
        cur.execute('''
            UPDATE activity_submissions SET status = 'Graded', graded_at = NOW(), graded_by = %s 
            WHERE submission_id = %s
        ''', (user_id, submission_id))
        
        db.commit()

        # Send Notification to student
        cur.execute("SELECT title FROM activities WHERE activity_id = %s", (sub['activity_id'],))
        act_title = (cur.fetchone() or {}).get('title', 'Activity')
        
        cur.execute("""
            INSERT INTO student_notifications (student_id, title, message, link)
            VALUES (%s, %s, %s, %s)
        """, (sub['student_id'], "Activity Graded", f"Your submission for '{act_title}' has been graded.", f"/student/activities/{sub['activity_id']}"))
        
        db.commit()

        flash("Grade saved successfully.", "success")
        
    finally:
        cur.close()
        db.close()
        
    return redirect(request.referrer)


@teacher_bp.route("/teacher/activities/submissions/<int:submission_id>/allow_resubmit", methods=["POST"])
def allow_resubmission(submission_id):
    if not _require_teacher(): return redirect("/")
    
    db = get_db_connection()
    cur = db.cursor()
    try:
        # Verify ownership inside? It's fine for simple access.
        cur.execute("UPDATE activity_submissions SET allow_resubmit = TRUE WHERE submission_id = %s", (submission_id,))
        db.commit()
        flash("Resubmission explicitly allowed for this student.", "success")
    finally:
        cur.close()
        db.close()
        
    return redirect(request.referrer)

# ══════════════════════════════════════════
# EXAM ROUTES — TEACHER
# ══════════════════════════════════════════

@teacher_bp.route("/teacher/exams")
def teacher_exams():
    if not _require_teacher():
        return redirect("/")

    user_id   = session.get("user_id")
    branch_id = session.get("branch_id")

    db  = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
            SELECT
                e.exam_id, e.title, e.exam_type, e.duration_mins,
                e.scheduled_date, e.status, e.created_at, e.grading_period,
                s.section_name,
                g.name AS grade_level_name,
                sub.name AS subject_name,
                (SELECT COUNT(*) FROM exam_questions q WHERE q.exam_id = e.exam_id) AS question_count,
                (SELECT COUNT(*) FROM exam_results r WHERE r.exam_id = e.exam_id) AS attempt_count
            FROM exams e
            JOIN sections s      ON e.section_id  = s.section_id
            JOIN grade_levels g  ON s.grade_level_id = g.id
            JOIN subjects sub    ON e.subject_id  = sub.subject_id
            WHERE e.teacher_id = %s AND e.branch_id = %s AND e.exam_type != 'quiz'
            ORDER BY e.created_at DESC
        """, (user_id, branch_id))
        exams = cur.fetchall() or []
        return render_template("teacher_exams.html", exams=exams)
    finally:
        cur.close()
        db.close()


@teacher_bp.route("/teacher/exams/create", methods=["GET", "POST"])
def teacher_exam_create():
    if not _require_teacher():
        return redirect("/")

    user_id   = session.get("user_id")
    branch_id = session.get("branch_id")

    db  = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    if request.method == "POST":
        title           = (request.form.get("title") or "").strip()
        section_id      = request.form.get("section_id")
        subject_id      = request.form.get("subject_id")
        exam_type       = "exam"  # always 'exam' for this route
        duration_mins   = int(request.form.get("duration_mins", 60))
        scheduled_start = request.form.get("scheduled_start") or None
        max_attempts    = int(request.form.get("max_attempts", 1))
        passing_score   = int(request.form.get("passing_score", 60))
        randomize       = request.form.get("randomize") == "1"
        instructions    = (request.form.get("instructions") or "").strip() or None
        grading_period  = request.form.get("grading_period")

        if not title or not section_id or not subject_id:
            flash("Title, section, and subject are required.", "error")
            return redirect(url_for("teacher.teacher_exam_create"))

        try:
            cur.execute("""
                INSERT INTO exams (
                    branch_id, section_id, subject_id, teacher_id,
                    title, exam_type, duration_mins,
                    scheduled_start,
                    max_attempts, passing_score,
                    randomize,
                    instructions, status, grading_period
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'draft',%s)
                RETURNING exam_id
            """, (
                branch_id, section_id, subject_id, user_id,
                title, exam_type, duration_mins,
                scheduled_start,
                max_attempts, passing_score,
                 randomize,
                instructions, grading_period
            ))
            exam_id = cur.fetchone()["exam_id"]
            db.commit()
            flash("Exam created! Now add your questions.", "success")
            return redirect(url_for("teacher.teacher_exam_questions", exam_id=exam_id))
        except Exception as e:
            db.rollback()
            flash(f"Could not create exam: {str(e)}", "error")
            return redirect(url_for("teacher.teacher_exam_create"))
        finally:
            cur.close()
            db.close()

    # GET
    try:
        cur.execute("""
            SELECT DISTINCT s.section_id, s.section_name, g.name AS grade_level_name
            FROM section_teachers st
            JOIN sections s     ON st.section_id = s.section_id
            JOIN grade_levels g ON s.grade_level_id = g.id
            WHERE st.teacher_id = %s AND s.branch_id = %s
            ORDER BY g.name, s.section_name
        """, (user_id, branch_id))
        sections = cur.fetchall() or []

        cur.execute("""
            SELECT st.section_id, sub.subject_id, sub.name AS subject_name
            FROM section_teachers st
            JOIN subjects sub ON st.subject_id = sub.subject_id
            WHERE st.teacher_id = %s
            ORDER BY sub.name
        """, (user_id,))
        assignments = cur.fetchall() or []

        return render_template("teacher_exam_create.html",
                               sections=sections,
                               assignments=assignments)
    finally:
        cur.close()
        db.close()

@teacher_bp.route("/teacher/exams/<int:exam_id>/questions", methods=["GET", "POST"])
def teacher_exam_questions(exam_id):
    if not _require_teacher():
        return redirect("/")

    user_id   = session.get("user_id")
    branch_id = session.get("branch_id")

    db  = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    if request.method == "POST":
        question_type = request.form.get("question_type", "mcq")
        points = int(request.form.get("points", 1))

        if question_type == "matching":
            match_prompts = request.form.getlist("match_prompt[]")
            match_answers = request.form.getlist("match_answer[]")

            pairs = []
            for p, a in zip(match_prompts, match_answers):
                p_clean = p.strip()
                a_clean = a.strip()
                if p_clean and a_clean:
                    pairs.append((p_clean, a_clean))

            if not pairs:
                flash("At least one valid matching pair is required.", "error")
                return redirect(url_for("teacher.teacher_exam_questions", exam_id=exam_id))

            all_answers = list(set([a for _, a in pairs]))
            choices = json.dumps({"options": all_answers})

            try:
                cur.execute("SELECT 1 FROM exams WHERE exam_id=%s AND teacher_id=%s AND branch_id=%s",
                            (exam_id, user_id, branch_id))
                if not cur.fetchone():
                    flash("Exam not found.", "error")
                    return redirect(url_for("teacher.teacher_exams"))

                for prompt, answer in pairs:
                    cur.execute("""
                        INSERT INTO exam_questions
                            (exam_id, question_text, question_type, choices, correct_answer, points, order_num)
                        VALUES (%s, %s, %s, %s, %s, %s,
                            (SELECT COALESCE(MAX(order_num),0)+1 FROM exam_questions WHERE exam_id=%s))
                    """, (exam_id, prompt, 'matching', choices, answer, points, exam_id))
                db.commit()
                flash(f"Added {len(pairs)} matching pairs!", "success")
            except Exception as e:
                db.rollback()
                flash(f"Could not add matching questions: {str(e)}", "error")
            finally:
                cur.close()
                db.close()
            return redirect(url_for("teacher.teacher_exam_questions", exam_id=exam_id))

        else:
            question_text = (request.form.get("question_text") or "").strip()
            correct_answer = (request.form.get("correct_answer") or "").strip()

            choices = None
            if question_type == "mcq":
                a = (request.form.get("choice_a") or "").strip()
                b = (request.form.get("choice_b") or "").strip()
                c = (request.form.get("choice_c") or "").strip()
                d = (request.form.get("choice_d") or "").strip()
                if not all([a, b, c, d]):
                    flash("All 4 choices are required for MCQ.", "error")
                    return redirect(url_for("teacher.teacher_exam_questions", exam_id=exam_id))
                choices = json.dumps({"A": a, "B": b, "C": c, "D": d})

            if not question_text or not correct_answer:
                flash("Question text and correct answer are required.", "error")
                return redirect(url_for("teacher.teacher_exam_questions", exam_id=exam_id))

            try:
                cur.execute("SELECT 1 FROM exams WHERE exam_id=%s AND teacher_id=%s AND branch_id=%s",
                            (exam_id, user_id, branch_id))
                if not cur.fetchone():
                    flash("Exam not found.", "error")
                    return redirect(url_for("teacher.teacher_exams"))

                cur.execute("""
                    INSERT INTO exam_questions
                        (exam_id, question_text, question_type, choices, correct_answer, points, order_num)
                    VALUES (%s, %s, %s, %s, %s, %s,
                        (SELECT COALESCE(MAX(order_num),0)+1 FROM exam_questions WHERE exam_id=%s))
                """, (exam_id, question_text, question_type,
                      choices, correct_answer, points, exam_id))
                db.commit()
                flash("Question added!", "success")
            except Exception as e:
                db.rollback()
                flash(f"Could not add question: {str(e)}", "error")
            finally:
                cur.close()
                db.close()

            return redirect(url_for("teacher.teacher_exam_questions", exam_id=exam_id))

    # GET
    try:
        cur.execute("""
            SELECT e.*, s.section_name, sub.name AS subject_name
            FROM exams e
            JOIN sections s ON e.section_id = s.section_id
            JOIN subjects sub ON e.subject_id = sub.subject_id
            WHERE e.exam_id = %s AND e.teacher_id = %s
        """, (exam_id, user_id))
        exam = cur.fetchone()
        if not exam:
            flash("Exam not found.", "error")
            return redirect(url_for("teacher.teacher_exams"))

        cur.execute("""
            SELECT * FROM exam_questions
            WHERE exam_id = %s ORDER BY order_num
        """, (exam_id,))
        questions = cur.fetchall() or []

        # Parse choices JSON
        for q in questions:
            if q["choices"]:
                q["choices"] = json.loads(q["choices"]) if isinstance(q["choices"], str) else q["choices"]

        return render_template("teacher_exam_questions.html",
                               exam=exam, questions=questions)
    finally:
        cur.close()
        db.close()


@teacher_bp.route("/teacher/exams/<int:exam_id>/publish", methods=["POST"])
def teacher_exam_publish(exam_id):
    if not _require_teacher():
        return redirect("/")

    user_id   = session.get("user_id")
    branch_id = session.get("branch_id")

    db  = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("SELECT COUNT(*) AS cnt FROM exam_questions WHERE exam_id=%s", (exam_id,))
        if cur.fetchone()["cnt"] == 0:
            flash("Cannot publish — add at least 1 question first.", "error")
            return redirect(url_for("teacher.teacher_exam_questions", exam_id=exam_id))

        cur.execute("""
            UPDATE exams SET status='published'
            WHERE exam_id=%s AND teacher_id=%s AND branch_id=%s
            RETURNING title, section_id, subject_id, exam_type
        """, (exam_id, user_id, branch_id))
        exam_info = cur.fetchone()
        
        if exam_info:
            notif_label = "Quiz" if exam_info['exam_type'] == 'quiz' else "Exam"
            # Send notifications to students in the section
            # Use UNION to capture students in `users` table AND students via `student_accounts`
            cur.execute("""
                SELECT DISTINCT u.user_id
                FROM enrollments e 
                JOIN users u ON u.user_id = e.user_id
                WHERE e.section_id = %s AND e.status IN ('approved', 'enrolled')
                UNION
                SELECT DISTINCT u.user_id
                FROM enrollments e
                JOIN student_accounts sa ON sa.enrollment_id = e.enrollment_id
                JOIN users u ON u.username = sa.username
                WHERE e.section_id = %s AND e.status IN ('approved', 'enrolled')
            """, (exam_info['section_id'], exam_info['section_id']))
            students = cur.fetchall()
            for s in students:
                notif_link = f"/student/subject/{exam_info['subject_id']}" if exam_info['exam_type'] == 'quiz' else "/student/exams"
                cur.execute("""
                    INSERT INTO student_notifications (student_id, title, message, link)
                    VALUES (%s, %s, %s, %s)
                """, (s['user_id'], f"New {notif_label}: {exam_info['title']}", f"A new {notif_label.lower()} has been published: {exam_info['title']}", notif_link))

        db.commit()
        flash(f"{notif_label} published! Students can now take it.", "success")
    except Exception as e:
        db.rollback()
        flash(f"Could not publish: {str(e)}", "error")
    finally:
        cur.close()
        db.close()

    return redirect(url_for("teacher.teacher_exam_questions", exam_id=exam_id))


@teacher_bp.route("/teacher/exams/<int:exam_id>/close", methods=["POST"])
def teacher_exam_close(exam_id):
    if not _require_teacher():
        return redirect("/")

    user_id   = session.get("user_id")
    branch_id = session.get("branch_id")

    db  = get_db_connection()
    cur = db.cursor()
    try:
        cur.execute("""
            UPDATE exams SET status='closed'
            WHERE exam_id=%s AND teacher_id=%s AND branch_id=%s
        """, (exam_id, user_id, branch_id))
        db.commit()
        flash("Exam closed.", "success")
    except Exception as e:
        db.rollback()
        flash(f"Could not close exam: {str(e)}", "error")
    finally:
        cur.close()
        db.close()

    return redirect(url_for("teacher.teacher_exams"))



# ══════════════════════════════════════════
# QUIZ ROUTES — TEACHER (separate from Exams)
# ══════════════════════════════════════════

@teacher_bp.route("/teacher/quizzes")
def teacher_quizzes():
    if not _require_teacher():
        return redirect("/")

    user_id   = session.get("user_id")
    branch_id = session.get("branch_id")

    db  = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
            SELECT
                e.exam_id, e.title, e.exam_type, e.duration_mins,
                e.scheduled_date, e.status, e.created_at, e.grading_period,
                s.section_name,
                g.name AS grade_level_name,
                sub.name AS subject_name,
                (SELECT COUNT(*) FROM exam_questions q WHERE q.exam_id = e.exam_id) AS question_count,
                (SELECT COUNT(*) FROM exam_results r WHERE r.exam_id = e.exam_id) AS attempt_count
            FROM exams e
            JOIN sections s      ON e.section_id  = s.section_id
            JOIN grade_levels g  ON s.grade_level_id = g.id
            JOIN subjects sub    ON e.subject_id  = sub.subject_id
            WHERE e.teacher_id = %s AND e.branch_id = %s AND e.exam_type = 'quiz'
            ORDER BY e.created_at DESC
        """, (user_id, branch_id))
        quizzes = cur.fetchall() or []
        return render_template("teacher_quizzes.html", quizzes=quizzes)
    finally:
        cur.close()
        db.close()


@teacher_bp.route("/teacher/quizzes/create", methods=["GET", "POST"])
def teacher_quiz_create():
    if not _require_teacher():
        return redirect("/")

    user_id   = session.get("user_id")
    branch_id = session.get("branch_id")

    db  = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    if request.method == "POST":
        title         = (request.form.get("title") or "").strip()
        assignment    = request.form.get("assignment", "")  # section_id_subject_id
        duration_mins = int(request.form.get("duration_mins", 30))
        scheduled_start = request.form.get("scheduled_start") or None
        max_attempts  = int(request.form.get("max_attempts", 1))
        passing_score = int(request.form.get("passing_score", 60))
        randomize     = request.form.get("randomize") == "1"
        instructions  = (request.form.get("instructions") or "").strip() or None
        grading_period = request.form.get("grading_period")

        if not title or "_" not in assignment:
            flash("Title and Section/Subject are required.", "error")
            return redirect(url_for("teacher.teacher_quiz_create"))

        section_id, subject_id = assignment.split("_", 1)

        if not title or not section_id or not subject_id:
            flash("Title, section, and subject are required.", "error")
            return redirect(url_for("teacher.teacher_quiz_create"))

        try:
            cur.execute("""
                INSERT INTO exams (
                    branch_id, section_id, subject_id, teacher_id,
                    title, exam_type, duration_mins,
                    scheduled_start,
                    max_attempts, passing_score,
                    randomize,
                    instructions, status, grading_period
                )
                VALUES (%s,%s,%s,%s,%s,'quiz',%s,%s,%s,%s,%s,%s,'draft', %s)
                RETURNING exam_id
            """, (
                branch_id, section_id, subject_id, user_id,
                title, duration_mins,
                scheduled_start,
                max_attempts, passing_score,
                randomize,
                instructions, grading_period
            ))
            exam_id = cur.fetchone()["exam_id"]
            db.commit()
            flash("Quiz created! Now add your questions.", "success")
            return redirect(url_for("teacher.teacher_exam_questions", exam_id=exam_id))
        except Exception as e:
            db.rollback()
            flash(f"Could not create quiz: {str(e)}", "error")
            return redirect(url_for("teacher.teacher_quiz_create"))
        finally:
            cur.close()
            db.close()

    # GET — load teacher's section+subject assignments
    try:
        cur.execute("""
            SELECT s.section_id, s.section_name, g.name AS grade_level_name,
                   sub.subject_id, sub.name AS subject_name
            FROM section_teachers st
            JOIN sections s    ON st.section_id = s.section_id
            JOIN grade_levels g ON s.grade_level_id = g.id
            JOIN subjects sub  ON st.subject_id = sub.subject_id
            WHERE st.teacher_id = %s AND s.branch_id = %s
            ORDER BY g.display_order, s.section_name, sub.name
        """, (user_id, branch_id))
        teacher_assignments = cur.fetchall() or []
        return render_template("teacher_quiz_create.html", teacher_assignments=teacher_assignments)
    finally:
        cur.close()
        db.close()



@teacher_bp.route("/teacher/exams/<int:exam_id>/results")
def teacher_exam_results(exam_id):
    if not _require_teacher():
        return redirect("/")

    user_id   = session.get("user_id")
    branch_id = session.get("branch_id")

    db  = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
            SELECT e.*, s.section_name, sub.name AS subject_name
            FROM exams e
            JOIN sections s   ON e.section_id  = s.section_id
            JOIN subjects sub ON e.subject_id  = sub.subject_id
            WHERE e.exam_id = %s AND e.teacher_id = %s
        """, (exam_id, user_id))
        exam = cur.fetchone()
        if not exam:
            flash("Exam not found.", "error")
            return redirect(url_for("teacher.teacher_exams"))

        cur.execute("""
            SELECT
                r.result_id, r.enrollment_id, r.score, r.total_points, r.status,
                r.submitted_at, r.started_at, r.tab_switches,
                e.student_name, e.grade_level,
                (SELECT COUNT(*) FROM exam_tab_switches ts WHERE ts.result_id = r.result_id) AS switch_count
            FROM exam_results r
            JOIN enrollments e ON r.enrollment_id = e.enrollment_id
            WHERE r.exam_id = %s
            ORDER BY r.submitted_at DESC NULLS LAST
        """, (exam_id,))
        results = cur.fetchall() or []

        # ✅ ADD THIS — convert UTC → PH time for display
        ph_tz = pytz.timezone("Asia/Manila")
        results_display = []
        for r in results:
            r = dict(r)
            if r.get("submitted_at"):
                r["submitted_at"] = r["submitted_at"].replace(tzinfo=timezone.utc).astimezone(ph_tz)
            if r.get("started_at"):
                r["started_at"] = r["started_at"].replace(tzinfo=timezone.utc).astimezone(ph_tz)
            results_display.append(r)
        # ✅ END ADD

        return render_template("teacher_exam_results.html",
                               exam=exam, results=results_display)  # ← use results_display
    finally:
        cur.close()
        db.close()

@teacher_bp.route("/teacher/exams/<int:exam_id>/questions/<int:question_id>/delete", methods=["POST"])
def teacher_exam_question_delete(exam_id, question_id):
    if not _require_teacher():
        return redirect("/")

    user_id = session.get("user_id")
    db  = get_db_connection()
    cur = db.cursor()
    try:
        # Verify ownership
        cur.execute("SELECT 1 FROM exams WHERE exam_id=%s AND teacher_id=%s AND status='draft'",
                    (exam_id, user_id))
        if not cur.fetchone():
            flash("Cannot delete — exam not found or already published.", "error")
            return redirect(url_for("teacher.teacher_exam_questions", exam_id=exam_id))

        cur.execute("DELETE FROM exam_questions WHERE question_id=%s AND exam_id=%s",
                    (question_id, exam_id))
        db.commit()
        flash("Question deleted.", "success")
    except Exception as e:
        db.rollback()
        flash(f"Could not delete: {str(e)}", "error")
    finally:
        cur.close()
        db.close()

    return redirect(url_for("teacher.teacher_exam_questions", exam_id=exam_id))


@teacher_bp.route("/teacher/exams/<int:exam_id>/import-questions", methods=["POST"])
def teacher_exam_import_questions(exam_id):
    if not _require_teacher():
        return redirect("/")

    user_id   = session.get("user_id")
    branch_id = session.get("branch_id")

    if 'question_file' not in request.files:
        flash("No file selected.", "error")
        return redirect(url_for("teacher.teacher_exam_questions", exam_id=exam_id))

    file = request.files['question_file']
    if not file or file.filename == '':
        flash("No file selected.", "error")
        return redirect(url_for("teacher.teacher_exam_questions", exam_id=exam_id))

    db  = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        # Verify exam belongs to teacher and is still draft
        cur.execute("""
            SELECT 1 FROM exams
            WHERE exam_id=%s AND teacher_id=%s AND branch_id=%s AND status='draft'
        """, (exam_id, user_id, branch_id))
        if not cur.fetchone():
            flash("Exam not found or already published.", "error")
            return redirect(url_for("teacher.teacher_exams"))

        ext = os.path.splitext(file.filename)[1].lower()

        # Parse file into list of question dicts
        if ext == '.docx':
            questions = parse_docx(file)
        elif ext == '.pdf':
            questions = parse_pdf(file)
        elif ext == '.csv':
            import pandas as pd
            df = pd.read_csv(file).fillna('')
            df.columns = [c.lower().strip() for c in df.columns]
            questions = df.to_dict(orient='records')
        elif ext in ('.xls', '.xlsx'):
            import pandas as pd
            df = pd.read_excel(file).fillna('')
            df.columns = [c.lower().strip() for c in df.columns]
            questions = df.to_dict(orient='records')
        else:
            flash("Unsupported file format. Use .docx, .pdf, .csv, or .xlsx", "error")
            return redirect(url_for("teacher.teacher_exam_questions", exam_id=exam_id))

        inserted = 0
        skipped  = 0
        errors   = []

        for i, q in enumerate(questions, start=1):
            question_text  = str(q.get('question_text', '') or '').strip()
            correct_answer = str(q.get('correct_answer', '') or '').strip()
            question_type  = str(q.get('question_type', '') or '').strip().lower()
            points         = int(q.get('points', 1) or 1)

            if not question_text or not correct_answer:
                errors.append(f"Row {i}: Missing question text or correct answer — skipped.")
                skipped += 1
                continue

            # Auto-detect type if not specified
            choice_a = str(q.get('choice_a', '') or q.get('option_a', '') or '').strip()
            choice_b = str(q.get('choice_b', '') or q.get('option_b', '') or '').strip()
            choice_c = str(q.get('choice_c', '') or q.get('option_c', '') or '').strip()
            choice_d = str(q.get('choice_d', '') or q.get('option_d', '') or '').strip()

            if not question_type:
                if choice_a and choice_b:
                    question_type = 'mcq'
                elif correct_answer.lower() in ('true', 'false'):
                    question_type = 'truefalse'
                else:
                    question_type = 'mcq'

            # Normalize type
            if question_type in ('multiple choice', 'multiple_choice', 'mcq'):
                question_type = 'mcq'
            elif question_type in ('true/false', 'truefalse', 'true_false', 'tf'):
                question_type = 'truefalse'

            # Build choices JSON for MCQ
            choices = None
            if question_type == 'mcq':
                if not all([choice_a, choice_b, choice_c, choice_d]):
                    errors.append(f"Row {i}: MCQ missing some choices — skipped.")
                    skipped += 1
                    continue
                choices = json.dumps({"A": choice_a, "B": choice_b,
                                      "C": choice_c, "D": choice_d})
                # Normalize correct answer to uppercase A/B/C/D
                correct_answer = correct_answer.upper()
                if correct_answer not in ('A', 'B', 'C', 'D'):
                    errors.append(f"Row {i}: MCQ correct answer must be A/B/C/D — skipped.")
                    skipped += 1
                    continue

            elif question_type == 'truefalse':
                # Normalize True/False
                if correct_answer.lower() == 'true':
                    correct_answer = 'True'
                elif correct_answer.lower() == 'false':
                    correct_answer = 'False'
                else:
                    errors.append(f"Row {i}: True/False answer must be True or False — skipped.")
                    skipped += 1
                    continue

            # Check duplicate
            cur.execute("""
                SELECT 1 FROM exam_questions
                WHERE exam_id=%s AND question_text=%s
            """, (exam_id, question_text))
            if cur.fetchone():
                errors.append(f"Row {i}: Duplicate question — skipped.")
                skipped += 1
                continue

            cur.execute("""
                INSERT INTO exam_questions
                    (exam_id, question_text, question_type, choices, correct_answer, points, order_num)
                VALUES (%s, %s, %s, %s, %s, %s,
                    (SELECT COALESCE(MAX(order_num), 0) + 1 FROM exam_questions WHERE exam_id=%s))
            """, (exam_id, question_text, question_type,
                  choices, correct_answer, points, exam_id))
            inserted += 1

        db.commit()

        if errors:
            for e in errors:
                flash(e, "warning")

        flash(f"Import done! {inserted} question(s) added, {skipped} skipped.", "success")

    except Exception as e:
        db.rollback()
        flash(f"Import failed: {str(e)}", "error")
    finally:
        cur.close()
        db.close()

    return redirect(url_for("teacher.teacher_exam_questions", exam_id=exam_id))


# ══════════════════════════════════════════
# PRIORITY 2 — EDIT QUESTION
# ══════════════════════════════════════════

@teacher_bp.route("/teacher/exams/<int:exam_id>/questions/<int:question_id>/edit",
                  methods=["GET", "POST"])
def teacher_exam_question_edit(exam_id, question_id):
    if not _require_teacher():
        return redirect("/")

    user_id   = session.get("user_id")
    branch_id = session.get("branch_id")

    db  = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        # Verify exam ownership + still draft
        cur.execute("""
            SELECT 1 FROM exams
            WHERE exam_id=%s AND teacher_id=%s AND branch_id=%s AND status='draft'
        """, (exam_id, user_id, branch_id))
        if not cur.fetchone():
            flash("Exam not found or already published.", "error")
            return redirect(url_for("teacher.teacher_exams"))

        cur.execute("SELECT * FROM exam_questions WHERE question_id=%s AND exam_id=%s",
                    (question_id, exam_id))
        question = cur.fetchone()
        if not question:
            flash("Question not found.", "error")
            return redirect(url_for("teacher.teacher_exam_questions", exam_id=exam_id))

        # Parse choices JSON for template
        if question["choices"]:
            question = dict(question)
            question["choices"] = json.loads(question["choices"]) \
                if isinstance(question["choices"], str) else question["choices"]

        if request.method == "POST":
            question_text  = (request.form.get("question_text") or "").strip()
            question_type  = request.form.get("question_type", "mcq")
            correct_answer = (request.form.get("correct_answer") or "").strip()
            points         = int(request.form.get("points", 1))

            choices = None
            if question_type == "mcq":
                a = (request.form.get("choice_a") or "").strip()
                b = (request.form.get("choice_b") or "").strip()
                c = (request.form.get("choice_c") or "").strip()
                d = (request.form.get("choice_d") or "").strip()
                if not all([a, b, c, d]):
                    flash("All 4 choices are required for MCQ.", "error")
                    return redirect(request.url)
                choices = json.dumps({"A": a, "B": b, "C": c, "D": d})

            if not question_text or not correct_answer:
                flash("Question text and correct answer are required.", "error")
                return redirect(request.url)

            cur.execute("""
                UPDATE exam_questions
                SET question_text=%s, question_type=%s, choices=%s,
                    correct_answer=%s, points=%s
                WHERE question_id=%s AND exam_id=%s
            """, (question_text, question_type, choices,
                  correct_answer, points, question_id, exam_id))
            db.commit()
            flash("Question updated!", "success")
            return redirect(url_for("teacher.teacher_exam_questions", exam_id=exam_id))

        # GET — fetch exam info for breadcrumb
        cur.execute("""
            SELECT e.*, s.section_name, sub.name AS subject_name
            FROM exams e
            JOIN sections s ON e.section_id = s.section_id
            JOIN subjects sub ON e.subject_id = sub.subject_id
            WHERE e.exam_id = %s
        """, (exam_id,))
        exam = cur.fetchone()

        return render_template("teacher_exam_question_edit.html",
                               exam=exam, question=question)
    finally:
        cur.close()
        db.close()


# ══════════════════════════════════════════
# PRIORITY 3 — RESET EXAM ATTEMPT
# ══════════════════════════════════════════

@teacher_bp.route("/teacher/exams/<int:exam_id>/reset/<int:enrollment_id>", methods=["POST"])
def teacher_exam_reset(exam_id, enrollment_id):
    if not _require_teacher():
        return redirect("/")

    user_id   = session.get("user_id")
    branch_id = session.get("branch_id")

    db  = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        # Verify exam belongs to this teacher
        cur.execute("""
            SELECT 1 FROM exams
            WHERE exam_id=%s AND teacher_id=%s AND branch_id=%s
        """, (exam_id, user_id, branch_id))
        if not cur.fetchone():
            flash("Exam not found or unauthorized.", "error")
            return redirect(url_for("teacher.teacher_exams"))

        # Delete answers first (FK constraint)
        cur.execute("""
            DELETE FROM exam_answers
            WHERE result_id IN (
                SELECT result_id FROM exam_results
                WHERE exam_id=%s AND enrollment_id=%s
            )
        """, (exam_id, enrollment_id))

        # Delete tab switches
        cur.execute("""
            DELETE FROM exam_tab_switches
            WHERE result_id IN (
                SELECT result_id FROM exam_results
                WHERE exam_id=%s AND enrollment_id=%s
            )
        """, (exam_id, enrollment_id))

        # Delete the result row entirely so student gets a fresh start
        cur.execute("""
            DELETE FROM exam_results
            WHERE exam_id=%s AND enrollment_id=%s
        """, (exam_id, enrollment_id))

        db.commit()

        if cur.rowcount > 0:
            flash("Exam attempt reset. Student can now retake the exam.", "success")
        else:
            flash("No exam attempt found for this student.", "warning")

    except Exception as e:
        db.rollback()
        flash(f"Error resetting exam: {str(e)}", "error")
    finally:
        cur.close()
        db.close()

    return redirect(url_for("teacher.teacher_exam_results", exam_id=exam_id))


# ══════════════════════════════════════════════════════════════
# GRADING PERIOD SYSTEM — TEACHER
# ══════════════════════════════════════════════════════════════

GRADING_PERIODS = ["1st", "2nd", "3rd", "4th"]


def _get_teacher_assignments(cur, user_id, branch_id):
    """Helper: fetch all section+subject assignments for a teacher."""
    cur.execute("""
        SELECT st.section_id, s.section_name, g.name AS grade_level_name,
               st.subject_id, sub.name AS subject_name
        FROM section_teachers st
        JOIN sections s      ON st.section_id = s.section_id
        JOIN grade_levels g  ON s.grade_level_id = g.id
        JOIN subjects sub    ON st.subject_id = sub.subject_id
        WHERE st.teacher_id = %s AND s.branch_id = %s
        ORDER BY g.display_order, s.section_name, sub.name
    """, (user_id, branch_id))
    return cur.fetchall() or []


# ── Grading Weights Setup ─────────────────────────────────────────────────────

@teacher_bp.route("/teacher/grading-weights")
def grading_weights():
    if not _require_teacher():
        return redirect("/")

    user_id   = session.get("user_id")
    branch_id = session.get("branch_id")

    db  = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        assignments = _get_teacher_assignments(cur, user_id, branch_id)

        # Fetch existing weights so we can pre-fill the form
        cur.execute("""
            SELECT section_id, subject_id, grading_period,
                   quiz_pct, exam_pct, activity_pct, participation_pct, attendance_pct
            FROM grading_weights
            WHERE teacher_id = %s
        """, (user_id,))
        raw_weights = cur.fetchall() or []

        # Build a quick lookup dict: (section_id, subject_id, period) → row
        weights_map = {}
        for w in raw_weights:
            key = (w['section_id'], w['subject_id'], w['grading_period'])
            weights_map[key] = w

    finally:
        cur.close()
        db.close()

    return render_template("teacher_grading_weights.html",
                           assignments=assignments,
                           weights_map=weights_map,
                           grading_periods=GRADING_PERIODS)


@teacher_bp.route("/teacher/grading-weights/set", methods=["POST"])
def grading_weights_set():
    if not _require_teacher():
        return redirect("/")

    user_id   = session.get("user_id")
    branch_id = session.get("branch_id")

    section_id  = request.form.get("section_id")
    subject_id  = request.form.get("subject_id")
    period      = request.form.get("grading_period")

    try:
        quiz_pct          = float(request.form.get("quiz_pct", 0) or 0)
        exam_pct          = float(request.form.get("exam_pct", 0) or 0)
        activity_pct      = float(request.form.get("activity_pct", 0) or 0)
        participation_pct = float(request.form.get("participation_pct", 0) or 0)
        attendance_pct    = float(request.form.get("attendance_pct", 0) or 0)
    except ValueError:
        flash("All percentage values must be numbers.", "error")
        return redirect(url_for("teacher.grading_weights"))

    if period not in GRADING_PERIODS:
        flash("Invalid grading period.", "error")
        return redirect(url_for("teacher.grading_weights"))

    total = quiz_pct + exam_pct + activity_pct + participation_pct + attendance_pct
    if abs(total - 100.0) > 0.01:
        flash(f"Percentages must total exactly 100%. Current total: {total:.1f}%", "error")
        return redirect(url_for("teacher.grading_weights"))

    db  = get_db_connection()
    cur = db.cursor()
    try:
        cur.execute("""
            INSERT INTO grading_weights
                (teacher_id, section_id, subject_id, grading_period,
                 quiz_pct, exam_pct, activity_pct, participation_pct, attendance_pct)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (teacher_id, section_id, subject_id, grading_period)
            DO UPDATE SET
                quiz_pct          = EXCLUDED.quiz_pct,
                exam_pct          = EXCLUDED.exam_pct,
                activity_pct      = EXCLUDED.activity_pct,
                participation_pct = EXCLUDED.participation_pct,
                attendance_pct    = EXCLUDED.attendance_pct
        """, (user_id, section_id, subject_id, period,
              quiz_pct, exam_pct, activity_pct, participation_pct, attendance_pct))
        db.commit()
        flash(f"Grading weights for {period} Grading saved successfully!", "success")
    except Exception as e:
        db.rollback()
        flash(f"Could not save weights: {e}", "error")
    finally:
        cur.close()
        db.close()

    return redirect(url_for("teacher.grading_weights"))


def _compute_period_grades(cur, user_id, branch_id, section_id, subject_id, period):
    """Internal helper to compute grades for all students in a section/subject/period."""
    # All students in the section
    cur.execute("""
        SELECT e.enrollment_id, e.student_name
        FROM enrollments e
        WHERE e.section_id = %s AND e.branch_id = %s AND e.status IN ('approved','enrolled')
        ORDER BY e.student_name ASC
    """, (section_id, branch_id))
    students = cur.fetchall() or []
    
    # Grading weights for this period
    cur.execute("""
        SELECT quiz_pct, exam_pct, activity_pct, participation_pct, attendance_pct
        FROM grading_weights
        WHERE teacher_id=%s AND section_id=%s AND subject_id=%s AND grading_period=%s
    """, (user_id, section_id, subject_id, period))
    weights = cur.fetchone()
    
    # --- Fetch scores per student for this period ---
    enrollment_ids = [s['enrollment_id'] for s in students]
    quiz_scores = {}
    exam_scores = {}
    if enrollment_ids:
        cur.execute("""
            SELECT er.enrollment_id,
                   AVG(CASE WHEN er.total_points > 0
                            THEN (er.score / er.total_points * 100) ELSE 0 END) AS avg_pct
            FROM exam_results er
            JOIN exams e ON er.exam_id = e.exam_id
            WHERE e.section_id = %s AND e.subject_id = %s
              AND e.exam_type = 'quiz' AND e.grading_period = %s
              AND er.enrollment_id = ANY(%s)
              AND er.status IN ('submitted', 'auto_submitted')
            GROUP BY er.enrollment_id
        """, (section_id, subject_id, period, enrollment_ids))
        for row in cur.fetchall():
            quiz_scores[row['enrollment_id']] = float(row['avg_pct'] or 0)

        cur.execute("""
            SELECT er.enrollment_id,
                   AVG(CASE WHEN er.total_points > 0
                            THEN (er.score / er.total_points * 100) ELSE 0 END) AS avg_pct
            FROM exam_results er
            JOIN exams e ON er.exam_id = e.exam_id
            WHERE e.section_id = %s AND e.subject_id = %s
              AND e.exam_type = 'exam' AND e.grading_period = %s
              AND er.enrollment_id = ANY(%s)
              AND er.status IN ('submitted', 'auto_submitted')
            GROUP BY er.enrollment_id
        """, (section_id, subject_id, period, enrollment_ids))
        for row in cur.fetchall():
            exam_scores[row['enrollment_id']] = float(row['avg_pct'] or 0)

    activity_scores = {}
    cur.execute("""
        SELECT ag.submission_id, asub.enrollment_id, ag.percentage
        FROM activity_grades ag
        JOIN activity_submissions asub ON ag.submission_id = asub.submission_id
        JOIN activities a ON ag.activity_id = a.activity_id
        WHERE a.section_id = %s AND a.subject_id = %s AND a.grading_period = %s
    """, (section_id, subject_id, period))
    act_raw = cur.fetchall() or []
    act_bucket = {}
    for row in act_raw:
        eid = row['enrollment_id']
        act_bucket.setdefault(eid, []).append(float(row['percentage'] or 0))
    for eid, pcts in act_bucket.items():
        activity_scores[eid] = sum(pcts) / len(pcts)

    participation_scores = {}
    cur.execute("""
        SELECT enrollment_id, score FROM participation_scores
        WHERE section_id=%s AND subject_id=%s AND grading_period=%s
    """, (section_id, subject_id, period))
    for row in cur.fetchall():
        participation_scores[row['enrollment_id']] = float(row['score'] or 0)

    attendance_scores = {}
    cur.execute("""
        SELECT enrollment_id, score FROM attendance_scores
        WHERE section_id=%s AND subject_id=%s AND grading_period=%s
    """, (section_id, subject_id, period))
    for row in cur.fetchall():
        attendance_scores[row['enrollment_id']] = float(row['score'] or 0)

    records = []
    for s in students:
        eid = s['enrollment_id']
        q = quiz_scores.get(eid, 0)
        e2 = exam_scores.get(eid, 0)
        a = activity_scores.get(eid, 0)
        p = participation_scores.get(eid, 0)
        att = attendance_scores.get(eid, 0)

        if weights:
            period_grade = (
                q   * (float(weights['quiz_pct']) / 100) +
                e2  * (float(weights['exam_pct']) / 100) +
                a   * (float(weights['activity_pct']) / 100) +
                p   * (float(weights['participation_pct']) / 100) +
                att * (float(weights['attendance_pct']) / 100)
            )
            period_grade = round(period_grade, 2)
        else:
            period_grade = None

        records.append({
            'enrollment_id':   eid,
            'student_name':    s['student_name'],
            'quiz':            round(q, 2),
            'exam':            round(e2, 2),
            'activity':        round(a, 2),
            'participation':   round(p, 2),
            'attendance':      round(att, 2),
            'period_grade':    period_grade
        })
    return students, weights, records

# ── Class Record ──────────────────────────────────────────────────────────────

@teacher_bp.route("/teacher/class-record/<int:section_id>/<int:subject_id>")
def class_record(section_id, subject_id):
    if not _require_teacher():
        return redirect("/")

    user_id   = session.get("user_id")
    branch_id = session.get("branch_id")
    period    = request.args.get("period", "1st")
    if period not in GRADING_PERIODS:
        period = "1st"

    db  = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        # Verify teacher owns this section+subject
        cur.execute("""
            SELECT 1 FROM section_teachers
            WHERE teacher_id=%s AND section_id=%s AND subject_id=%s
        """, (user_id, section_id, subject_id))
        if not cur.fetchone():
            flash("Unauthorized or assignment not found.", "error")
            return redirect(url_for("teacher.teacher_dashboard"))

        # Section and subject info
        cur.execute("""
            SELECT s.section_name, g.name AS grade_level_name, sub.name AS subject_name
            FROM sections s
            JOIN grade_levels g ON s.grade_level_id = g.id
            JOIN subjects sub ON sub.subject_id = %s
            WHERE s.section_id = %s
        """, (subject_id, section_id))
        context = cur.fetchone()

        _, weights, records = _compute_period_grades(cur, user_id, branch_id, section_id, subject_id, period)

        return render_template("teacher_class_record.html",
                               context=context,
                               section_id=section_id,
                               subject_id=subject_id,
                               records=records,
                               weights=weights,
                               period=period,
                               grading_periods=GRADING_PERIODS)
    finally:
        cur.close()
        db.close()

@teacher_bp.route("/teacher/post-grades/<int:section_id>/<int:subject_id>/<string:period>", methods=["POST"])
def teacher_post_grades(section_id, subject_id, period):
    if not _require_teacher(): return redirect("/")
    user_id   = session.get("user_id")
    branch_id = session.get("branch_id")
    if period not in GRADING_PERIODS: return redirect(url_for("teacher.teacher_dashboard"))

    db  = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("SELECT 1 FROM section_teachers WHERE teacher_id=%s AND section_id=%s AND subject_id=%s", (user_id, section_id, subject_id))
        if not cur.fetchone():
            flash("Unauthorized.", "error")
            return redirect(url_for("teacher.teacher_dashboard"))

        _, weights, records = _compute_period_grades(cur, user_id, branch_id, section_id, subject_id, period)
        if not weights:
            flash(f"Cannot post grades: Weights not set for {period} Grading.", "error")
            return redirect(url_for("teacher.class_record", section_id=section_id, subject_id=subject_id, period=period))

        for r in records:
            if r['period_grade'] is not None:
                cur.execute("""
                    INSERT INTO posted_grades (enrollment_id, section_id, subject_id, grading_period, grade, posted_by, posted_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (enrollment_id, subject_id, grading_period)
                    DO UPDATE SET grade = EXCLUDED.grade, posted_at = NOW(), posted_by = EXCLUDED.posted_by
                """, (r['enrollment_id'], section_id, subject_id, period, r['period_grade'], user_id))
        
        db.commit()
        flash(f"Grades for {period} Grading have been posted to the Student Portal!", "success")
    except Exception as e:
        db.rollback()
        flash(f"Error posting grades: {str(e)}", "error")
    finally:
        cur.close()
        db.close()
    return redirect(url_for("teacher.class_record", section_id=section_id, subject_id=subject_id, period=period))


# ── Participation Scores ──────────────────────────────────────────────────────

@teacher_bp.route("/teacher/participation/<int:section_id>/<int:subject_id>/<period>",
                  methods=["GET", "POST"])
def participation_input(section_id, subject_id, period):
    if not _require_teacher():
        return redirect("/")

    user_id   = session.get("user_id")
    branch_id = session.get("branch_id")

    if period not in GRADING_PERIODS:
        flash("Invalid grading period.", "error")
        return redirect(url_for("teacher.grading_weights"))

    db  = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        # Verify ownership
        cur.execute("""
            SELECT 1 FROM section_teachers
            WHERE teacher_id=%s AND section_id=%s AND subject_id=%s
        """, (user_id, section_id, subject_id))
        if not cur.fetchone():
            flash("Unauthorized.", "error")
            return redirect(url_for("teacher.teacher_dashboard"))

        # Context info
        cur.execute("""
            SELECT s.section_name, sub.name AS subject_name
            FROM sections s, subjects sub
            WHERE s.section_id=%s AND sub.subject_id=%s
        """, (section_id, subject_id))
        ctx = cur.fetchone()

        if request.method == "POST":
            scores = request.form.to_dict()
            for key, val in scores.items():
                if key.startswith("score_"):
                    try:
                        eid   = int(key.split("_", 1)[1])
                        score = max(0.0, min(100.0, float(val or 0)))
                        cur.execute("""
                            INSERT INTO participation_scores
                                (teacher_id, enrollment_id, section_id, subject_id, grading_period, score, updated_at)
                            VALUES (%s,%s,%s,%s,%s,%s,NOW())
                            ON CONFLICT ON CONSTRAINT uq_participation
                            DO UPDATE SET score=EXCLUDED.score, updated_at=NOW()
                        """, (user_id, eid, section_id, subject_id, period, score))
                    except (ValueError, IndexError):
                        continue
            db.commit()
            flash("Participation scores saved!", "success")
            return redirect(url_for("teacher.class_record",
                                    section_id=section_id,
                                    subject_id=subject_id,
                                    period=period))

        # GET — load students + existing scores
        cur.execute("""
            SELECT e.enrollment_id, e.student_name,
                   COALESCE(ps.score, 0) AS score
            FROM enrollments e
            LEFT JOIN participation_scores ps
                ON ps.enrollment_id = e.enrollment_id
               AND ps.subject_id = %s AND ps.grading_period = %s
            WHERE e.section_id = %s AND e.branch_id = %s AND e.status IN ('approved','enrolled')
            ORDER BY e.student_name
        """, (subject_id, period, section_id, branch_id))
        students = cur.fetchall() or []

    finally:
        cur.close()
        db.close()

    return render_template("teacher_participation_input.html",
                           ctx=ctx, students=students,
                           section_id=section_id, subject_id=subject_id,
                           period=period)


# ── Attendance Scores ─────────────────────────────────────────────────────────

@teacher_bp.route("/teacher/attendance/<int:section_id>/<int:subject_id>/<period>",
                  methods=["GET", "POST"])
def attendance_input(section_id, subject_id, period):
    if not _require_teacher():
        return redirect("/")

    user_id   = session.get("user_id")
    branch_id = session.get("branch_id")

    if period not in GRADING_PERIODS:
        flash("Invalid grading period.", "error")
        return redirect(url_for("teacher.grading_weights"))

    db  = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
            SELECT 1 FROM section_teachers
            WHERE teacher_id=%s AND section_id=%s AND subject_id=%s
        """, (user_id, section_id, subject_id))
        if not cur.fetchone():
            flash("Unauthorized.", "error")
            return redirect(url_for("teacher.teacher_dashboard"))

        cur.execute("""
            SELECT s.section_name, sub.name AS subject_name
            FROM sections s, subjects sub
            WHERE s.section_id=%s AND sub.subject_id=%s
        """, (section_id, subject_id))
        ctx = cur.fetchone()

        if request.method == "POST":
            scores = request.form.to_dict()
            for key, val in scores.items():
                if key.startswith("score_"):
                    try:
                        eid   = int(key.split("_", 1)[1])
                        score = max(0.0, min(100.0, float(val or 0)))
                        cur.execute("""
                            INSERT INTO attendance_scores
                                (teacher_id, enrollment_id, section_id, subject_id, grading_period, score, updated_at)
                            VALUES (%s,%s,%s,%s,%s,%s,NOW())
                            ON CONFLICT ON CONSTRAINT uq_attendance
                            DO UPDATE SET score=EXCLUDED.score, updated_at=NOW()
                        """, (user_id, eid, section_id, subject_id, period, score))
                    except (ValueError, IndexError):
                        continue
            db.commit()
            flash("Attendance scores saved!", "success")
            return redirect(url_for("teacher.class_record",
                                    section_id=section_id,
                                    subject_id=subject_id,
                                    period=period))

        cur.execute("""
            SELECT e.enrollment_id, e.student_name,
                   COALESCE(att.score, 0) AS score
            FROM enrollments e
            LEFT JOIN attendance_scores att
                ON att.enrollment_id = e.enrollment_id
               AND att.subject_id = %s AND att.grading_period = %s
            WHERE e.section_id = %s AND e.branch_id = %s AND e.status IN ('approved','enrolled')
            ORDER BY e.student_name
        """, (subject_id, period, section_id, branch_id))
        students = cur.fetchall() or []

    finally:
        cur.close()
        db.close()

    return render_template("teacher_attendance_input.html",
                           ctx=ctx, students=students,
                           section_id=section_id, subject_id=subject_id,
                           period=period)

# ── API for Teacher Sidebar Classlist ─────────────────────

@teacher_bp.route("/api/teacher/sections")
def api_teacher_sections():
    if not _require_teacher(): return jsonify({"error": "Unauthorized"}), 403
    user_id = session.get("user_id")
    branch_id = session.get("branch_id")
    db = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
            SELECT s.section_id, s.section_name, g.name AS grade_level_name 
            FROM section_teachers st
            JOIN sections s ON st.section_id = s.section_id
            JOIN grade_levels g ON s.grade_level_id = g.id
            WHERE st.teacher_id = %s AND s.branch_id = %s
            GROUP BY s.section_id, s.section_name, g.name, g.display_order
            ORDER BY g.display_order, s.section_name
        """, (user_id, branch_id))
        sections = cur.fetchall()
        return jsonify({"sections": sections})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        db.close()


@teacher_bp.route("/api/teacher/classlist/<int:section_id>")
def api_teacher_classlist(section_id):
    if not _require_teacher(): return jsonify({"error": "Unauthorized"}), 403
    branch_id = session.get("branch_id")
    user_id = session.get("user_id")
    db = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        # Verify ownership
        cur.execute("SELECT 1 FROM section_teachers WHERE teacher_id = %s AND section_id = %s", (user_id, section_id))
        if not cur.fetchone():
            return jsonify({"error": "Unauthorized section access"}), 403

        cur.execute("""
            SELECT e.enrollment_id, e.student_name, u.user_id as student_user_id
            FROM enrollments e
            LEFT JOIN users u ON u.user_id = e.user_id
            WHERE e.section_id = %s AND e.branch_id = %s AND e.status IN ('approved', 'enrolled')
            ORDER BY e.student_name ASC
        """, (section_id, branch_id))
        students = cur.fetchall()
        return jsonify({"students": students})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        db.close()

@teacher_bp.route("/teacher/reschedule", methods=["POST"])
def teacher_reschedule():
    if not _require_teacher():
        return jsonify({"error": "Unauthorized"}), 403

    user_id = session.get("user_id")
    branch_id = session.get("branch_id")

    if request.is_json:
        data = request.get_json()
    else:
        data = request.form

    enrollment_id = data.get("enrollment_id")
    item_type     = data.get("item_type")  # 'activity', 'exam', 'quiz'
    item_id       = data.get("item_id")
    new_due_date  = data.get("new_due_date")

    if not all([enrollment_id, item_type, item_id, new_due_date]):
        return jsonify({"error": "Missing required fields"}), 400

    # 0. Validate date is not in the past
    try:
        ph_tz = pytz.timezone("Asia/Manila")
        now_pht = datetime.now(timezone.utc).astimezone(ph_tz).replace(tzinfo=None)
        dt_val = datetime.strptime(new_due_date, '%Y-%m-%dT%H:%M')
        if dt_val < now_pht:
            return jsonify({"error": "Cannot reschedule to a past date."}), 400
    except Exception as e:
        print(f"Date validation error: {e}")
        # If parsing fails, we skip this check and let DB handle format, 
        # but 400 error is usually better.
        pass

    db = get_db_connection()
    cur = db.cursor()
    try:
        # 1. Verify ownership of the item
        if item_type == 'activity':
            cur.execute("SELECT 1 FROM activities WHERE activity_id = %s AND teacher_id = %s", (item_id, user_id))
        else:
            cur.execute("SELECT 1 FROM exams WHERE exam_id = %s AND teacher_id = %s", (item_id, user_id))

        if not cur.fetchone():
            return jsonify({"error": "Unauthorized item access or item not found."}), 403

        # 2. Verify student enrollment in the same branch
        cur.execute("SELECT 1 FROM enrollments WHERE enrollment_id = %s AND branch_id = %s", (enrollment_id, branch_id))
        if not cur.fetchone():
            return jsonify({"error": "Invalid student or branch mismatch."}), 403

        # 3. Upsert into individual_extensions
        cur.execute("""
            INSERT INTO individual_extensions (enrollment_id, item_type, item_id, new_due_date)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT ON CONSTRAINT uq_extension
            DO UPDATE SET new_due_date = EXCLUDED.new_due_date
        """, (enrollment_id, item_type, item_id, new_due_date))

        db.commit()
        return jsonify({"ok": True, "message": "Rescheduled successfully!"})
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        db.close()

@teacher_bp.route("/teacher/activities/<int:activity_id>/toggle-status", methods=["POST"])
def toggle_activity_status(activity_id):
    if not _require_teacher(): return jsonify({"error": "Unauthorized"}), 403
    user_id = session.get("user_id")
    
    db = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("SELECT status, section_id, title FROM activities WHERE activity_id = %s AND teacher_id = %s", (activity_id, user_id))
        act = cur.fetchone()
        if not act:
            return jsonify({"error": "Activity not found"}), 404
            
        new_status = 'Published' if act['status'] == 'Draft' else 'Draft'
        cur.execute("UPDATE activities SET status = %s, updated_at = NOW() WHERE activity_id = %s", (new_status, activity_id))
        
        # If toggled to Published, send notifications
        if new_status == 'Published':
            section_id = act['section_id']
            title = act['title']
            cur.execute("""
                SELECT DISTINCT u.user_id 
                FROM enrollments e 
                JOIN users u ON u.user_id = e.user_id 
                WHERE e.section_id = %s AND e.status IN ('approved', 'enrolled')
                UNION
                SELECT DISTINCT u.user_id
                FROM enrollments e
                JOIN student_accounts sa ON sa.enrollment_id = e.enrollment_id
                JOIN users u ON u.username = sa.username
                WHERE e.section_id = %s AND e.status IN ('approved', 'enrolled')
            """, (section_id, section_id))
            student_users = cur.fetchall()
            if student_users:
                for su in student_users:
                    cur.execute("""
                        INSERT INTO student_notifications (student_id, title, message, link) 
                        VALUES (%s, %s, %s, %s)
                    """, (su['user_id'], f"New Activity: {title}", f"Your teacher posted a new activity: {title}.", f"/student/activities/{activity_id}"))
        
        db.commit()
        return jsonify({"ok": True, "new_status": new_status})
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        db.close()
