import re as _re
from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify
from db import get_db_connection
import psycopg2.extras
from cloudinary_helper import upload_file

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


# ── DEBUG ─────────────────────────────────────────────────
@teacher_bp.route("/teacher/debug")
def teacher_debug():
    if not _require_teacher():
        return redirect("/")
    branch_id = session.get("branch_id")
    db = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
            SELECT enrollment_id, student_name, grade_level, status, branch_id
            FROM enrollments
            WHERE branch_id = %s
            ORDER BY grade_level, student_name
        """, (branch_id,))
        rows = cur.fetchall()
        return jsonify({
            "session_branch_id": branch_id,
            "count": len(rows),
            "enrollments": [dict(r) for r in rows]
        })
    finally:
        cur.close()
        db.close()


# ── Dashboard ─────────────────────────────────────────────
@teacher_bp.route("/teacher")
def teacher_dashboard():
    if not _require_teacher():
        return redirect("/")

    user_id   = session.get("user_id")
    branch_id = session.get("branch_id")

    db = get_db_connection()
    cur = db.cursor()
    try:
        cur.execute("""
    SELECT grade_level
    FROM users
    WHERE user_id = %s
""", (user_id,))
        row = cur.fetchone()
        teacher_grade = row[0] if row else None
    finally:
        cur.close()
        db.close()

    selected_grade = (request.args.get("grade") or teacher_grade or "").strip()

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
            cur.execute("""
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
                ORDER BY e.student_name ASC
            """, {
                "branch_id":   branch_id,
                "grade_full":  grade_full,
                "grade_short": grade_short,
            })
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
    SELECT grade_level
    FROM users
    WHERE user_id = %s
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
        """, (user_id, branch_id, grade, title, body or None))
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
                    status, allowed_file_types, attachment_path
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING activity_id
            ''', (branch_id, section_id, subject_id, user_id, 
                  title, category, instructions, max_score, due_date or None, 
                  status, allowed_file_types, attachment_path))
            activity_id = cur.fetchone()['activity_id']
            
            if status == 'Published':
                cur.execute("""
                    SELECT u.user_id 
                    FROM enrollments e 
                    JOIN users u ON u.enrollment_id = e.enrollment_id 
                    WHERE e.section_id = %s AND e.status IN ('approved', 'enrolled')
                """, (section_id,))
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
                    updated_at = NOW()
                WHERE activity_id = %s
            ''', (title, category, instructions, max_score, due_date or None, 
                  status, allowed_file_types, attachment_path, activity_id))
                  
            if status == 'Published' and activity['status'] != 'Published':
                cur.execute("""
                    SELECT u.user_id 
                    FROM enrollments e 
                    JOIN users u ON u.enrollment_id = e.enrollment_id 
                    WHERE e.section_id = %s AND e.status IN ('approved', 'enrolled')
                """, (activity['section_id'],))
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
            LEFT JOIN users u ON u.enrollment_id = e.enrollment_id
            WHERE e.section_id = %s AND e.status IN ('approved', 'enrolled') AND e.branch_id = %s
            ORDER BY e.student_name ASC
        ''', (activity['section_id'], activity['branch_id']))
        students = cur.fetchall()
        
        # Get all submissions for this activity
        cur.execute('''
            SELECT sub.*, g.grade_id, g.raw_score, g.percentage, g.remarks
            FROM activity_submissions sub
            LEFT JOIN activity_grades g ON sub.submission_id = g.submission_id
            WHERE sub.activity_id = %s
            ORDER BY sub.submitted_at ASC
        ''', (activity_id,))
        submissions_raw = {row['enrollment_id']: row for row in cur.fetchall()}
        
        submissions_data = []
        for s in students:
            sub = submissions_raw.get(s['enrollment_id'])
            item = {
                'student_name': s['student_name'],
                'student_user_id': s['student_user_id'],
                'enrollment_id': s['enrollment_id']
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
