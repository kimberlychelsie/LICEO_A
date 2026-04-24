from flask import Blueprint, render_template, request, redirect, session, flash, url_for, jsonify
from db import get_db_connection
from werkzeug.security import generate_password_hash
import logging
import psycopg2.extras

# Setup logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

parent_bp = Blueprint("parent", __name__)

def _require_parent():
    return session.get("role") == "parent"


@parent_bp.route("/parent/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()

        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not username or not password:
            flash("Username and password are required", "error")
            return redirect(url_for("parent.register"))

        if password != confirm_password:
            flash("Passwords do not match", "error")
            return redirect(url_for("parent.register"))

        hashed_password = generate_password_hash(password)

        db = get_db_connection()
        cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        try:
            cursor.execute("SELECT 1 FROM users WHERE username=%s", (username,))
            if cursor.fetchone():
                flash("Username already exists", "error")
                return redirect(url_for("parent.register"))

            cursor.execute("""
                INSERT INTO users (username, password, role, branch_id, require_password_change)
                VALUES (%s, %s, 'parent', NULL, 1)
                RETURNING user_id
            """, (username, hashed_password))

            user_id = cursor.fetchone()["user_id"]
            db.commit()

            session["user_id"] = user_id
            session["role"] = "parent"
            session["branch_id"] = None

            flash("Registration successful! Set your new password, then you can link your children.", "success")
            return redirect(url_for("auth.change_password"))

        except Exception as e:
            db.rollback()
            logger.error(f"Parent registration failed: {str(e)}")
            flash("Registration failed. Please try again.", "error")
            return redirect(url_for("parent.register"))

        finally:
            cursor.close()
            db.close()

    return render_template("parent_register.html")


@parent_bp.route("/parent/dashboard")
def dashboard():
    if not _require_parent():
        return redirect("/")

    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        cursor.execute("""
            SELECT ps.*, e.student_name, e.grade_level, e.status,
                   br.branch_name, br.location,
                   b.bill_id, b.total_amount, b.amount_paid, b.balance, b.status as bill_status,
                   e.enrollment_id
            FROM parent_student ps
            JOIN enrollments e ON ps.student_id = e.enrollment_id
            JOIN branches br ON e.branch_id = br.branch_id
            LEFT JOIN billing b ON e.enrollment_id = b.enrollment_id
            WHERE ps.parent_id = %s
            ORDER BY e.created_at DESC
        """, (session.get("user_id"),))

        children = cursor.fetchall()
        return render_template("parent_dashboard.html", children=children)

    finally:
        cursor.close()
        db.close()


@parent_bp.route("/parent/link-child", methods=["GET", "POST"])
def link_child():
    if not _require_parent():
        return redirect("/")

    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        cursor.execute("SELECT branch_id, branch_name FROM branches WHERE is_active = TRUE ORDER BY branch_name")
        branches = cursor.fetchall()

        if request.method == "POST":
            branch_id = request.form.get("branch_id")
            enrollment_no = request.form.get("enrollment_id", "").strip() # the input name in template is enrollment_id
            relationship = request.form.get("relationship", "").strip()

            if not branch_id or not enrollment_no.isdigit():
                flash("Branch and valid Enrollment ID are required", "error")
                return redirect(url_for("parent.link_child"))

            enrollment_no_int = int(enrollment_no)
            branch_id_int = int(branch_id)

            cursor.execute("""
                SELECT * FROM enrollments 
                WHERE branch_enrollment_no=%s AND branch_id=%s
            """, (enrollment_no_int, branch_id_int))
            enrollment = cursor.fetchone()

            if not enrollment:
                flash("No student found with that ID in the selected branch.", "error")
                return redirect(url_for("parent.link_child"))

            enrollment_id = enrollment["enrollment_id"] # Internal global ID

            cursor.execute("""
                SELECT 1 FROM parent_student
                WHERE parent_id=%s AND student_id=%s
            """, (session.get("user_id"), enrollment_id))

            if cursor.fetchone():
                flash("This child is already linked to your account", "warning")
                return redirect(url_for("parent.dashboard"))

            cursor.execute("""
                INSERT INTO parent_student (parent_id, student_id, relationship)
                VALUES (%s, %s, %s)
            """, (session.get("user_id"), enrollment_id, relationship))

            db.commit()
            flash(f"Successfully linked {enrollment.get('student_name', 'child')} to your account", "success")
            return redirect(url_for("parent.dashboard"))

        return render_template("parent_link_child.html", branches=branches)

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to link child: {str(e)}")
        flash("Failed to link child. Please try again.", "error")
        return redirect(url_for("parent.link_child"))

    finally:
        cursor.close()
        db.close()

@parent_bp.route("/parent/child/<int:enrollment_id>")
def child_detail(enrollment_id):
    if not _require_parent():
        return redirect("/")

    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        cursor.execute("""
            SELECT ps.*, e.*, br.branch_name, br.location
            FROM parent_student ps
            JOIN enrollments e ON ps.student_id = e.enrollment_id
            JOIN branches br ON e.branch_id = br.branch_id
            WHERE ps.parent_id=%s AND ps.student_id=%s
        """, (session.get("user_id"), enrollment_id))

        child = cursor.fetchone()
        if not child:
            flash("Child not found or access denied", "error")
            return redirect(url_for("parent.dashboard"))

        cursor.execute("SELECT * FROM enrollment_documents WHERE enrollment_id=%s", (enrollment_id,))
        documents = cursor.fetchall()

        cursor.execute("SELECT * FROM enrollment_books WHERE enrollment_id=%s", (enrollment_id,))
        books = cursor.fetchall() or []

        cursor.execute("SELECT * FROM enrollment_uniforms WHERE enrollment_id=%s", (enrollment_id,))
        uniforms = cursor.fetchall() or []

        # -- Fetch items from reservations system --
        cursor.execute("""
            SELECT
                ii.item_name, ri.qty, ii.category
            FROM reservation_items ri
            JOIN reservations r ON r.reservation_id = ri.reservation_id
            JOIN inventory_items ii ON ri.item_id = ii.item_id
            WHERE (r.enrollment_id = %s OR r.student_user_id IN (
                SELECT u.user_id FROM student_accounts sa 
                JOIN users u ON sa.username = u.username 
                WHERE sa.enrollment_id = %s
            )) 
            AND UPPER(r.status) NOT IN ('CANCELLED', 'REJECTED')
        """, (enrollment_id, enrollment_id))
        reserved_items = cursor.fetchall()

        # Merge reserved items into books/uniforms lists for unified display
        for item in reserved_items:
            if item['category'].lower() == 'book':
                books.append({
                    'book_name': item['item_name'],
                    'quantity': item['qty'],
                    'is_reservation': True
                })
            elif item['category'].lower() == 'uniform':
                uniforms.append({
                    'uniform_type': item['item_name'],
                    'size': 'N/A', # Size info might be in item name for inventory items
                    'quantity': item['qty'],
                    'is_reservation': True
                })

        cursor.execute("""
            SELECT s.name AS subject_name, a.title AS activity_title,
                   g.raw_score, g.percentage, g.remarks, a.due_date, a.grading_period
            FROM activities a
            JOIN subjects s ON a.subject_id = s.subject_id
            JOIN activity_submissions sub ON sub.activity_id = a.activity_id
            LEFT JOIN activity_grades g ON g.submission_id = sub.submission_id
            WHERE sub.enrollment_id = %s AND g.raw_score IS NOT NULL
            ORDER BY a.due_date DESC
        """, (enrollment_id,))
        activity_scores = cursor.fetchall()

        cursor.execute("""
            SELECT e.title AS exam_title, sub.name AS subject_name,
                   r.score, r.total_points, r.status AS result_status, r.submitted_at,
                   e.exam_type, e.passing_score, e.grading_period
            FROM exam_results r
            JOIN exams e ON r.exam_id = e.exam_id
            JOIN subjects sub ON e.subject_id = sub.subject_id
            WHERE r.enrollment_id = %s
              AND r.status IN ('submitted', 'auto_submitted')
            ORDER BY r.submitted_at DESC
        """, (enrollment_id,))
        all_exam_scores = cursor.fetchall()

        # Split scores into quizzes and exams for tabbed UI
        quiz_scores = [e for e in all_exam_scores if e["exam_type"] == "quiz"]
        exam_scores = [e for e in all_exam_scores if e["exam_type"] != "quiz"]

        # -- Fetch Posted Grades (Final Grades) --
        grade_data = []
        if child.get("section_id"):
            # Get subjects for this section
            cursor.execute("""
                SELECT sub.subject_id, sub.name AS subject_name
                FROM section_teachers st
                JOIN subjects sub ON st.subject_id = sub.subject_id
                WHERE st.section_id = %s
                ORDER BY sub.name
            """, (child["section_id"],))
            subjects = cursor.fetchall() or []

            # Get posted grades
            cursor.execute("""
                SELECT subject_id, grading_period, grade
                FROM posted_grades
                WHERE enrollment_id = %s
            """, (enrollment_id,))
            posted = cursor.fetchall() or []

            posted_map = {}
            for p in posted:
                sid = p["subject_id"]
                if sid not in posted_map: posted_map[sid] = {}
                posted_map[sid][p["grading_period"]] = int(round(float(p["grade"])))

            for s in subjects:
                sid = s["subject_id"]
                grades = posted_map.get(sid, {})
                period_vals = [float(v) for v in grades.values()]
                final_avg = int(round(sum(period_vals) / 4)) if len(period_vals) == 4 else None

                grade_data.append({
                    "subject_name": s["subject_name"],
                    "units": 3,
                    "grades": grades,
                    "final_grade": final_avg
                })

        # -- Fetch Class Schedule --
        schedules = []
        if child.get("section_id"):
            cursor.execute("""
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
            """, (child["section_id"], child.get("year_id")))
            schedules = cursor.fetchall() or []

        # -- Academic Status Calculation --
        total_grades = []
        for s in grade_data:
            if s.get('final_grade'):
                total_grades.append(s['final_grade'])
            for g in s.get('grades', {}).values():
                if g: total_grades.append(float(g))
        
        # Also consider quiz/exam scores if no official grades yet
        if not total_grades:
            for q in quiz_scores:
                if q.get('score') and q.get('total_points'):
                    total_grades.append((float(q['score']) / float(q['total_points'])) * 100)
            for e in exam_scores:
                if e.get('score') and e.get('total_points'):
                    total_grades.append((float(e['score']) / float(e['total_points'])) * 100)

        avg_grade = sum(total_grades) / len(total_grades) if total_grades else None
        
        # -- Check for Missing Activities (Nagpapabaya check) --
        missing_count = 0
        if child.get("section_id"):
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM activities a
                WHERE a.section_id = %s 
                  AND a.status = 'Published'
                  AND a.due_date < NOW()
                  AND NOT EXISTS (
                      SELECT 1 FROM activity_submissions sub 
                      WHERE sub.activity_id = a.activity_id AND sub.enrollment_id = %s
                  )
            """, (child["section_id"], enrollment_id))
            m_row = cursor.fetchone()
            missing_count = m_row['count'] if m_row else 0

        academic_status = "Good Standing"
        status_color = "#16a34a" # Success green
        
        if avg_grade is not None:
            if avg_grade >= 90:
                academic_status = "Excelling"
                status_color = "#2563eb" # Info blue
            elif avg_grade < 75:
                academic_status = "Critical / Failing"
                status_color = "#dc2626" # Error red
            elif avg_grade < 80:
                academic_status = "Needs Attention"
                status_color = "#d97706" # Warning orange
        
        # Override if too many missing tasks
        if missing_count >= 5:
            academic_status = "At Risk (Neglecting Tasks)"
            status_color = "#991b1b" # Dark red
        elif missing_count >= 3 and academic_status == "Good Standing":
            academic_status = "Needs Attention (Missing Tasks)"
            status_color = "#d97706"

        # Sync with DB if needed
        if academic_status != child.get('academic_status'):
            cursor.execute("UPDATE enrollments SET academic_status = %s WHERE enrollment_id = %s", (academic_status, enrollment_id))
            db.commit()

        # Notify parent if status is concerning
        if academic_status in ["Critical / Failing", "Needs Attention", "At Risk (Neglecting Tasks)", "Needs Attention (Missing Tasks)"]:
            cursor.execute("""
                SELECT 1 FROM parent_notifications 
                WHERE parent_id = %s AND student_id = %s AND title LIKE 'Academic Alert%%'
                AND created_at > NOW() - INTERVAL '7 days'
            """, (session.get("user_id"), enrollment_id))
            if not cursor.fetchone():
                notif_title = f"Academic Alert: {child['student_name']}"
                notif_msg = f"Alert: {child['student_name']} is currently '{academic_status}'. Please review their performance and missing tasks in the portal."
                cursor.execute("""
                    INSERT INTO parent_notifications (parent_id, student_id, title, message, link)
                    VALUES (%s, %s, %s, %s, %s)
                """, (session.get("user_id"), enrollment_id, notif_title, notif_msg, url_for('parent.child_detail', enrollment_id=enrollment_id)))
                db.commit()

        return render_template(
            "parent_child_detail.html",
            child=child,
            documents=documents,
            books=books,
            uniforms=uniforms,
            activity_scores=activity_scores,
            quiz_scores=quiz_scores,
            exam_scores=exam_scores,
            grade_data=grade_data,
            schedules=schedules,
            grading_periods=['1st', '2nd', '3rd', '4th'],
            academic_status=academic_status,
            status_color=status_color
        )

    finally:
        cursor.close()
        db.close()


@parent_bp.route("/parent/child/<int:enrollment_id>/bills")
def child_bills(enrollment_id):
    if not _require_parent():
        return redirect("/")

    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        cursor.execute("""
            SELECT ps.*, e.student_name, e.grade_level, e.enrollment_id, e.branch_enrollment_no
            FROM parent_student ps
            JOIN enrollments e ON ps.student_id = e.enrollment_id
            WHERE ps.parent_id=%s AND ps.student_id=%s
        """, (session.get("user_id"), enrollment_id))

        child = cursor.fetchone()
        if not child:
            flash("Child not found or access denied", "error")
            return redirect(url_for("parent.dashboard"))

        cursor.execute("SELECT * FROM billing WHERE enrollment_id=%s", (enrollment_id,))
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

        # Fetch detailed reservations for breakdown
        reservation_details = []
        if bill:
            cursor.execute("""
                SELECT
                    r.reservation_id, ii.item_name, ri.qty, ri.line_total, ii.category
                FROM reservation_items ri
                JOIN reservations r ON r.reservation_id = ri.reservation_id
                JOIN inventory_items ii ON ri.item_id = ii.item_id
                WHERE (r.enrollment_id = %s OR r.student_user_id IN (
                    SELECT u.user_id FROM student_accounts sa 
                    JOIN users u ON sa.username = u.username 
                    WHERE sa.enrollment_id = %s
                )) 
                AND UPPER(r.status) NOT IN ('CANCELLED', 'REJECTED')
                ORDER BY r.reservation_id ASC
            """, (enrollment_id, enrollment_id))
            reservation_details = cursor.fetchall()

        return render_template(
            "parent_child_bills.html",
            child=child,
            bill=bill,
            payments=payments,
            reservation_details=reservation_details
        )

    finally:
        cursor.close()
        db.close()


# ✅ Sidebar "Reserve Items" — smart redirect
@parent_bp.route("/parent/reserve")
def parent_reserve():
    if not _require_parent():
        return redirect("/")

    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cursor.execute("""
            SELECT e.enrollment_id, e.student_name, e.grade_level
            FROM parent_student ps
            JOIN enrollments e ON ps.student_id = e.enrollment_id
            WHERE ps.parent_id = %s
            ORDER BY e.student_name
        """, (session.get("user_id"),))
        children = cursor.fetchall()

        if not children:
            flash("No linked children found. Please link a child first.", "warning")
            return redirect(url_for("parent.link_child"))

        if len(children) == 1:
            # Only one child — go straight to reservation
            return redirect(url_for(
                "student.student_reservation",
                enrollment_id=children[0]["enrollment_id"]
            ))

        # Multiple children — show picker
        return render_template("parent_reserve_picker.html", children=children)

    finally:
        cursor.close()
        db.close()


# ✅ Parent → Reserve items for this child (redirect to student reservation page)
@parent_bp.route("/parent/child/<int:enrollment_id>/reserve")
def child_reserve(enrollment_id):
    if not _require_parent():
        return redirect("/")

    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cursor.execute("""
            SELECT 1
            FROM parent_student
            WHERE parent_id=%s AND student_id=%s
            LIMIT 1
        """, (session.get("user_id"), enrollment_id))

        if not cursor.fetchone():
            flash("Child not found or access denied", "error")
            return redirect(url_for("parent.dashboard"))

        # Redirect to the existing student reservation route, passing enrollment_id in query string
        return redirect(url_for("student.student_reservation", enrollment_id=enrollment_id))

    finally:
        cursor.close()
        db.close()


@parent_bp.route("/parent/notifications/mark-read", methods=["POST"])
def parent_mark_notifs_read():
    if not _require_parent():
        return jsonify({"error": "Unauthorized"}), 403

    db = get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute("""
            UPDATE parent_notifications 
            SET is_read = TRUE 
            WHERE parent_id = %s AND is_read = FALSE
        """, (session.get("user_id"),))
        db.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        db.close()


@parent_bp.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response