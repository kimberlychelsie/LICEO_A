from flask import Blueprint, render_template, request, session, redirect, flash, url_for, jsonify
from datetime import datetime
import pytz
from db import get_db_connection
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
import re
import os
import uuid
import psycopg2.extras
import secrets
import string
from cloudinary_helper import upload_announcement_photo
from utils.send_email import send_email

branch_admin_bp = Blueprint("branch_admin", __name__)

# =======================
# HELPERS
# =======================
def generate_password(length: int = 8) -> str:
    """Generate a cryptographically secure random password for staff accounts."""
    characters = string.ascii_letters + string.digits
    return "".join(secrets.choice(characters) for _ in range(length))

# =======================
# GRADE RANGE MAPPINGS (for inventory grade filter / display)
# =======================
GRADE_MAPPINGS = {
    'Pre-Elementary Boys Set': ['Nursery', 'Kinder', 'Grade 1', 'Grade 2', 'Grade 3'],
    'Pre-Elementary Girls Set': ['Nursery', 'Kinder', 'Grade 1', 'Grade 2', 'Grade 3', 'Grade 4', 'Grade 5', 'Grade 6'],
    'Elementary G4-6 Boys Set': ['Grade 4', 'Grade 5', 'Grade 6'],
    'JHS Boys Uniform Set': ['Grade 7', 'Grade 8', 'Grade 9', 'Grade 10'],
    'JHS Girls Uniform Set': ['Grade 7', 'Grade 8', 'Grade 9', 'Grade 10'],
    'SHS Boys Uniform Set': ['Grade 11', 'Grade 12', '11-GAS', '11-STEM', '11-HUMSS', '12-GAS', '12-STEM', '12-HUMSS'],
    'SHS Girls Uniform Set': ['Grade 11', 'Grade 12', '11-GAS', '11-STEM', '11-HUMSS', '12-GAS', '12-STEM', '12-HUMSS'],
    'PE Uniform': ['Nursery', 'Kinder'] + [f'Grade {i}' for i in range(1, 13)] + ['11-GAS', '11-STEM', '11-HUMSS', '12-GAS', '12-STEM', '12-HUMSS'],
}

SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]  # xs to double XL

def get_grade_display(item_name, stored_grade):
    if item_name in GRADE_MAPPINGS:
        grades = GRADE_MAPPINGS[item_name]
        if len(grades) > 3:
            return f"{grades[0]} - {grades[-1]}"
        return ", ".join(grades)
    return stored_grade or "All"

def item_matches_grade_filter(item_name, stored_grade, grade_filter):
    if not grade_filter:
        return True
    if item_name in GRADE_MAPPINGS:
        return grade_filter in GRADE_MAPPINGS[item_name]
    return stored_grade == grade_filter or stored_grade is None

def get_grade_order(item_name, grade_level):
    """
    Determines sorting order. 
    Nursery/Kinder < Elementary < JHS < SHS < PE (Last)
    """
    name_lower = str(item_name or "").lower()
    
    # PE is always dead last
    if 'pe uniform' in name_lower or 'p.e.' in name_lower or 'p.e' in name_lower:
        return 1000
    
    # Try to get order from grade_level column first
    if grade_level:
        grade_str = str(grade_level).strip().lower()
        if 'nursery' in grade_str: return 10
        if 'kinder' in grade_str or 'pre' in grade_str: return 20
        match = re.search(r'(\d+)', grade_str)
        if match:
            return 100 + int(match.group(1))
    
    # If no grade_level, check item_name for uniform sets
    if 'pre-elementary' in name_lower or 'pre elem' in name_lower:
        return 15
    if 'elementary' in name_lower:
        return 110 # approx Grade 1-6 area
    if 'jhs' in name_lower or 'junior high' in name_lower:
        return 115 # Grade 7-10 area
    if 'shs' in name_lower or 'senior high' in name_lower:
        return 125 # Grade 11-12 area
        
    return 999

# =======================
# SIZE HELPERS (inventory_item_sizes table)
# =======================
def size_sort_key(size_label: str) -> int:
    if not size_label:
        return 999
    s = str(size_label).strip().upper()
    return SIZE_ORDER.index(s) if s in SIZE_ORDER else 998

def ensure_default_sizes_exist(cursor, item_id: int):
    """
    Create default size rows (XS-XXL) if none exist for item_id.
    Assumes table name: inventory_item_sizes
      columns: size_id, item_id, size_label, stock_total, reserved_qty
    """
    cursor.execute("""
        SELECT COUNT(*)
        FROM inventory_item_sizes
        WHERE item_id = %s
    """, (item_id,))
    cnt = cursor.fetchone()[0] or 0

    if cnt > 0:
        return False  # already exists

    for sz in SIZE_ORDER:
        cursor.execute("""
            INSERT INTO inventory_item_sizes (item_id, size_label, stock_total, reserved_qty)
            VALUES (%s, %s, 0, 0)
        """, (item_id, sz))
    return True

def recompute_item_totals_from_sizes(cursor, item_id: int, branch_id: int):
    """
    Updates inventory_items.stock_total and inventory_items.reserved_qty based on sizes table totals.
    """
    cursor.execute("""
        UPDATE inventory_items
        SET
            stock_total = COALESCE((
                SELECT SUM(stock_total) FROM inventory_item_sizes WHERE item_id = %s
            ), 0),
            reserved_qty = COALESCE((
                SELECT SUM(reserved_qty) FROM inventory_item_sizes WHERE item_id = %s
            ), 0)
        WHERE item_id = %s AND branch_id = %s
    """, (item_id, item_id, item_id, branch_id))

def _get_viewed_year_id(cursor, branch_id):
    """Returns the viewed year_id, defaulting to active year."""
    viewed = session.get("viewed_year_id")
    if viewed:
        cursor.execute("SELECT year_id FROM school_years WHERE year_id = %s AND branch_id = %s", (viewed, branch_id))
        if cursor.fetchone():
            return viewed
    cursor.execute("SELECT year_id FROM school_years WHERE branch_id = %s AND is_active = TRUE LIMIT 1", (branch_id,))
    row = cursor.fetchone()
    return row["year_id"] if row else None

# =======================
# BRANCH ADMIN DASHBOARD
# =======================
@branch_admin_bp.route("/branch-admin", methods=["GET", "POST"])
def dashboard():
    if session.get("role") != "branch_admin":
        return redirect("/")
    if not session.get("branch_id"):
        flash("No branch assigned. Please contact admin.", "error")
        return redirect(url_for("auth.login"))

    created_user = None
    # Defaults for metrics
    metrics = {
        'total_enrolled': 0,
        'pending_reservations': 0,
        'total_teachers': 0,
        'total_staff': 0,
        'grade_stats': [],
        'status_stats': []
    }

    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        # ✅ Auto-seed grade levels if table is empty
        cursor.execute("SELECT COUNT(*) FROM grade_levels")
        if cursor.fetchone()['count'] == 0:
            default_grades = [
                ("Nursery", 1), ("Kinder", 2),
                ("Grade 1", 3), ("Grade 2", 4), ("Grade 3", 5),
                ("Grade 4", 6), ("Grade 5", 7), ("Grade 6", 8),
                ("Grade 7", 9), ("Grade 8", 10), ("Grade 9", 11), ("Grade 10", 12),
                ("Grade 11", 13), ("Grade 12", 14)
            ]
            for g_name, g_order in default_grades:
                cursor.execute(
                    "INSERT INTO grade_levels (name, display_order) VALUES (%s, %s)",
                    (g_name, g_order)
                )
            db.commit()

        # ✅ Load grade levels for teacher creation
        cursor.execute("SELECT id, name FROM grade_levels ORDER BY display_order")
        grades = cursor.fetchall() or []

        # ✅ Load announcements for THIS branch only (Simplified for dash)
        cursor.execute("""
            SELECT announcement_id AS id, title, message, is_active, image_url
            FROM announcements
            WHERE branch_id = %s
            ORDER BY created_at DESC LIMIT 5
        """, (session.get("branch_id"),))
        announcements_list = cursor.fetchall() or []
        
        # ✅ Fetch Metrics
        b_id = session.get("branch_id")
        year_id = _get_viewed_year_id(cursor, b_id)
        
        if year_id:
            cursor.execute("SELECT COUNT(*) FROM enrollments WHERE status IN ('enrolled', 'approved') AND branch_id=%s AND year_id=%s", (b_id, year_id))
            metrics['total_enrolled'] = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) FROM enrollments WHERE status='pending' AND branch_id=%s AND year_id=%s", (b_id, year_id))
            metrics['pending_reservations'] = cursor.fetchone()['count']
            
            # Chart Data: Enrollment by Grade
            cursor.execute("""
                SELECT grade_level, COUNT(*) 
                FROM enrollments 
                WHERE status IN ('enrolled', 'approved') AND branch_id=%s AND year_id=%s
                GROUP BY grade_level
                ORDER BY COUNT(*) DESC
            """, (b_id, year_id))
            metrics['grade_stats'] = cursor.fetchall() or []
            
            # Chart Data: Status Breakdown
            cursor.execute("""
                SELECT status, COUNT(*) 
                FROM enrollments 
                WHERE branch_id=%s AND year_id=%s
                GROUP BY status
            """, (b_id, year_id))
            metrics['status_stats'] = cursor.fetchall() or []
        else:
            metrics['total_enrolled'] = 0
            metrics['pending_reservations'] = 0
            metrics['grade_stats'] = []
            metrics['status_stats'] = []

        # Teachers and Staff are not year-bound right now unless requested
        cursor.execute("SELECT COUNT(*) FROM users WHERE role='teacher' AND COALESCE(status, 'active')='active' AND branch_id=%s", (b_id,))
        metrics['total_teachers'] = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE role IN ('registrar', 'cashier', 'librarian') AND COALESCE(status, 'active')='active' AND branch_id=%s", (b_id,))
        metrics['total_staff'] = cursor.fetchone()['count']

        # ✅ Inventory Count (Uniforms & Supplies)
        cursor.execute("SELECT SUM(stock_total) FROM inventory_items WHERE branch_id=%s AND category != 'BOOK'", (b_id,))
        metrics['total_inventory'] = cursor.fetchone()['sum'] or 0

        # ✅ Map total_enrolled to total_students for template
        metrics['total_students'] = metrics['total_enrolled']
        
    except Exception as e:
        print(f"Error loading dashboard metrics: {e}")
    finally:
        cursor.close()
        db.close()

    return render_template(
        "branch_admin_dashboard.html",
        announcements_list=announcements_list,
        grades=grades,
        metrics=metrics
    )

@branch_admin_bp.route("/branch-admin/broadcast-station", methods=["GET", "POST"])
def branch_admin_broadcast_station():
    if session.get("role") != "branch_admin":
        return redirect("/")
    
    branch_id = session.get("branch_id")
    if not branch_id:
        flash("No branch assigned.", "error")
        return redirect(url_for("auth.login"))

    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    announcements_list = []

    try:
        if request.method == "POST":
            # -----------------------
            # Add Homepage Announcement
            # -----------------------
            if request.form.get("add_announcement") == "1":
                title   = (request.form.get("announcement_title") or "").strip()
                message = (request.form.get("announcement_message") or "").strip()
                if title:
                    image_url = None
                    photo = request.files.get("announcement_photo")
                    if photo and photo.filename:
                        ALLOWED = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
                        ext = photo.filename.rsplit('.', 1)[-1].lower() if '.' in photo.filename else ''
                        if ext in ALLOWED:
                            image_url = upload_announcement_photo(photo)
                        else:
                            flash("Photo must be PNG, JPG, GIF, or WEBP.", "warning")

                    audience = (request.form.get("audience") or "all").strip().lower()
                    if audience not in ("all", "teacher"):
                        audience = "all"

                    cursor.execute("""
                        INSERT INTO announcements (title, message, is_active, image_url, branch_id, audience)
                        VALUES (%s, %s, TRUE, %s, %s, %s)
                    """, (title, message, image_url, branch_id, audience))
                    db.commit()
                    flash("Announcement added to homepage!", "success")
                else:
                    flash("Announcement title is required.", "error")
                return redirect(url_for("branch_admin.branch_admin_broadcast_station"))

        # Load announcements
        cursor.execute("""
            SELECT announcement_id AS id, title, message, (created_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Manila') AS created_at_local, is_active,
                   image_url, branch_id, audience
            FROM announcements
            WHERE branch_id = %s
            ORDER BY created_at DESC
        """, (branch_id,))
        announcements_list = cursor.fetchall() or []

    except Exception as e:
        flash(f"Error in broadcast station: {e}", "error")
    finally:
        cursor.close()
        db.close()

    return render_template("branch_admin_announcements.html", announcements_list=announcements_list)

@branch_admin_bp.route("/branch-admin/announcements/<int:announcement_id>/toggle", methods=["POST"])
def announcement_toggle(announcement_id):
    if session.get("role") != "branch_admin":
        return redirect("/")

    branch_id = session.get("branch_id")
    if not branch_id:
        return redirect("/")

    db = get_db_connection()
    cur = db.cursor()
    try:
        cur.execute("""
            UPDATE announcements
            SET is_active = NOT is_active
            WHERE announcement_id = %s AND branch_id = %s
            RETURNING is_active
        """, (announcement_id, branch_id))
        row = cur.fetchone()
        db.commit()
        
        status = "published" if row[0] else "archived"
        flash(f"Announcement is now {status}.", "success")
    except Exception:
        db.rollback()
        flash("Could not update announcement status.", "error")
    finally:
        cur.close()
        db.close()
    
    if request.form.get("from_station"):
        return redirect(url_for("branch_admin.branch_admin_broadcast_station"))
    return redirect(url_for("branch_admin.dashboard"))

@branch_admin_bp.route("/branch-admin/announcements/<int:announcement_id>/delete", methods=["POST"])
def announcement_delete(announcement_id):
    if session.get("role") != "branch_admin":
        return redirect("/")

    branch_id = session.get("branch_id")
    if not branch_id:
        return redirect("/")

    db = get_db_connection()
    cur = db.cursor()
    try:
        cur.execute("""
            DELETE FROM announcements
            WHERE announcement_id = %s AND branch_id = %s
        """, (announcement_id, branch_id))
        db.commit()
        flash("Announcement permanently deleted.", "success")
    except Exception as e:
        db.rollback()
        flash(f"Could not delete announcement: {str(e)}", "error")
    finally:
        cur.close()
        db.close()

    if request.form.get("from_station"):
        return redirect(url_for("branch_admin.branch_admin_broadcast_station"))
    return redirect(url_for("branch_admin.dashboard"))

@branch_admin_bp.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# =======================
# BRANCH ADMIN: FAQ MANAGEMENT
# =======================
@branch_admin_bp.route("/branch-admin/faqs", methods=["GET"])
def branch_admin_faqs():
    if session.get("role") != "branch_admin":
        return redirect("/")

    branch_id = session.get("branch_id")

    db = get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute("""
            SELECT id, question, answer
            FROM chatbot_faqs
            WHERE branch_id IS NULL
            ORDER BY id ASC
        """)
        general_faqs = cursor.fetchall() or []

        cursor.execute("""
            SELECT id, question, answer
            FROM chatbot_faqs
            WHERE branch_id = %s
            ORDER BY id ASC
        """, (branch_id,))
        branch_faqs = cursor.fetchall() or []
    finally:
        cursor.close()
        db.close()

    return render_template(
        "branch_admin_faqs.html",
        general_faqs=general_faqs,
        branch_faqs=branch_faqs
    )

@branch_admin_bp.route("/branch-admin/faqs/add", methods=["POST"])
def branch_admin_faq_add():
    if session.get("role") != "branch_admin":
        return redirect("/")

    branch_id = session.get("branch_id")
    question = (request.form.get("question") or "").strip()
    answer = (request.form.get("answer") or "").strip()

    if not question or not answer:
        flash("Question and Answer are required.", "error")
        return redirect("/branch-admin/faqs")

    db = get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute("""
            INSERT INTO chatbot_faqs (question, answer, branch_id)
            VALUES (%s, %s, %s)
        """, (question, answer, branch_id))
        db.commit()
        flash("FAQ added successfully!", "success")
    except Exception:
        db.rollback()
        flash("Failed to add FAQ.", "error")
    finally:
        cursor.close()
        db.close()

    return redirect("/branch-admin/faqs")

@branch_admin_bp.route("/branch-admin/faqs/<int:faq_id>/edit", methods=["POST"])
def branch_admin_faq_edit(faq_id):
    if session.get("role") != "branch_admin":
        return redirect("/")

    branch_id = session.get("branch_id")
    question = (request.form.get("question") or "").strip()
    answer = (request.form.get("answer") or "").strip()

    if not question or not answer:
        flash("Question and Answer are required.", "error")
        return redirect("/branch-admin/faqs")

    db = get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute("""
            UPDATE chatbot_faqs
            SET question=%s, answer=%s
            WHERE id=%s AND branch_id=%s
        """, (question, answer, faq_id, branch_id))
        db.commit()
        flash("FAQ updated successfully!", "success")
    except Exception:
        db.rollback()
        flash("Failed to update FAQ.", "error")
    finally:
        cursor.close()
        db.close()

    return redirect("/branch-admin/faqs")

@branch_admin_bp.route("/branch-admin/faqs/<int:faq_id>/delete", methods=["POST"])
def branch_admin_faq_delete(faq_id):
    if session.get("role") != "branch_admin":
        return redirect("/")

    branch_id = session.get("branch_id")

    db = get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute("""
            DELETE FROM chatbot_faqs
            WHERE id=%s AND branch_id=%s
        """, (faq_id, branch_id))
        db.commit()
        flash("FAQ deleted.", "success")
    except Exception:
        db.rollback()
        flash("Failed to delete FAQ.", "error")
    finally:
        cursor.close()
        db.close()

    return redirect("/branch-admin/faqs")


# =======================
# MANAGE ACCOUNTS
# =======================
@branch_admin_bp.route("/branch-admin/manage-accounts", methods=["GET", "POST"])
def branch_admin_manage_accounts():
    if session.get("role") != "branch_admin":
        return redirect("/")

    branch_id = session.get("branch_id")
    if not branch_id:
        flash("No branch assigned.", "error")
        return redirect(url_for("auth.login"))

    role_filter = (request.args.get("role") or "registrar").strip().lower()
    view_mode = (request.args.get("view") or "flat").strip().lower()
    created_user = None
    filter_grade = request.args.get("grade", "")
    filter_section = request.args.get("section", "")
    filter_search = request.args.get("search", "").strip()

    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        # ✅ Only load THIS branch's grade levels for teacher dropdown
        cursor.execute(
            "SELECT id, name FROM grade_levels WHERE branch_id = %s ORDER BY display_order",
            (branch_id,)
        )
        grades = cursor.fetchall() or []

        if request.method == "POST":
            role         = (request.form.get("role")         or "").strip().lower()
            grade_level  = (request.form.get("grade_level")  or "").strip()
            full_name    = (request.form.get("full_name")    or "").strip()
            gender       = (request.form.get("gender")       or "").strip().lower()
            custom_uname = (request.form.get("username")     or "").strip()
            user_email = (request.form.get("email") or "").strip()

            if role not in ("registrar", "cashier", "librarian", "teacher"):
                flash("Invalid role selected.", "error")
                return redirect("/branch-admin/manage-accounts")

            if role == "teacher":
                if not full_name:
                    flash("Full name is required for teacher accounts.", "error")
                    return redirect("/branch-admin/manage-accounts")
                if gender not in ("male", "female"):
                    flash("Please select a gender for the teacher account.", "error")
                    return redirect("/branch-admin/manage-accounts")

            if custom_uname and not re.match(r'^[A-Za-z0-9_]+$', custom_uname):
                flash("Username can only contain letters, numbers, and underscores.", "error")
                return redirect("/branch-admin/manage-accounts")

            cursor.execute("SELECT branch_code FROM branches WHERE branch_id=%s", (branch_id,))
            row = cursor.fetchone()
# ✅ guard against both missing row AND NULL column value
            branch_code = (row['branch_code'] or "" if row else "").strip().upper()
            if not branch_code:
                flash("Branch code not configured for this branch. Please ask the admin to set one.", "error")
                return redirect("/branch-admin/manage-accounts")
            if custom_uname:
                base_username = custom_uname
            elif role in ("registrar", "cashier", "librarian"):
                base_username = f"{branch_code}_{role.capitalize()}"
            elif role == "teacher":
                grade_suffix = ""
                if grade_level:
                    # grade_level is the ID. Fetch the real name.
                    try:
                        cursor.execute("SELECT name FROM grade_levels WHERE id=%s", (grade_level,))
                        g_row = cursor.fetchone()
                        if g_row:
                            g_name = g_row['name']
                            m = re.search(r"(\d+)", g_name)
                            if m:
                                grade_suffix = m.group(1)
                            elif "kinder" in g_name.lower():
                                grade_suffix = "K"
                            elif "nursery" in g_name.lower():
                                grade_suffix = "N"
                    except Exception:
                        pass
                base_username = f"{branch_code}_Teacher{grade_suffix}" if grade_suffix else f"{branch_code}_Teacher"
            else:
                base_username = f"{branch_code}_{role.capitalize()}"

            username = base_username
            suffix_counter = 2
            while True:
                cursor.execute("SELECT 1 FROM users WHERE username=%s", (username,))
                if not cursor.fetchone():
                    break
                if custom_uname:
                    flash(f"Username '{username}' already exists. Please choose a different one.", "error")
                    return redirect("/branch-admin/manage-accounts")
                username = f"{base_username}_{suffix_counter}"
                suffix_counter += 1

            temp_password   = generate_password()
            hashed_password = generate_password_hash(temp_password)

            if role == "teacher":
                cursor.execute("""
                    INSERT INTO users
                        (branch_id, username, password, role, require_password_change,
                         grade_level_id, full_name, gender, email)
                    VALUES (%s, %s, %s, %s, TRUE, %s, %s, %s, %s)
                """, (branch_id, username, hashed_password, role,
                      grade_level or None, full_name or None, gender or None, user_email))
            else:
                cursor.execute("""
                    INSERT INTO users
                        (branch_id, username, password, role, require_password_change, full_name, gender, email)
                    VALUES (%s, %s, %s, %s, TRUE, %s, %s, %s)
                """, (branch_id, username, hashed_password, role, full_name or None, gender or None, user_email))
            db.commit()
            flash(f"Account for {full_name} created successfully! Credentials sent to {user_email}.", "success")
            created_user = {"username": username, "password": temp_password, "role": role}
            if created_user and user_email:
                subject = f"Your {role.capitalize()} Account for Liceo Branch"
                body = f"""Hello,

        Your account has been created!

        Username: {created_user['username']}
        Password: {created_user['password']}
        Login URL: https://www.liceo-lms.com/

        Please log in and change your password immediately.

        If you have any questions, contact your branch admin.

        -- The Liceo LMS Team
        """
                email_sent = send_email(user_email, subject, body)
                if not email_sent:
                    flash(f"User account created, but failed to send email.", "warning")
                
                flash("User created successfully!", "success")
                role_filter = role

        # Fetch section options for filtering
        cursor.execute("""
            SELECT s.section_id, s.section_name, g.name as grade_level_name 
            FROM sections s 
            JOIN grade_levels g ON s.grade_level_id = g.id 
            WHERE s.branch_id = %s 
            ORDER BY g.display_order, s.section_name
        """, (branch_id,))
        section_options = cursor.fetchall() or []

        # Fetch accounts based on role
        # Fetch accounts based on role
        if role_filter == "student":
            query = """
                SELECT 
                    sa.account_id, sa.username, 'student' AS role, e.student_name AS full_name,
                    e.gender, e.grade_level, sa.is_active, sa.email, e.enrollment_id,
                    s.section_name
                FROM student_accounts sa
                JOIN enrollments e ON sa.enrollment_id = e.enrollment_id
                LEFT JOIN sections s ON e.section_id = s.section_id
                WHERE sa.branch_id = %s
            """
            params = [branch_id]
            if filter_grade:
                query += " AND e.grade_level = %s"
                params.append(filter_grade)
            if filter_section:
                query += " AND e.section_id = %s"
                params.append(int(filter_section))
            if filter_search:
                query += " AND (sa.username ILIKE %s OR e.student_name ILIKE %s)"
                params.extend([f"%{filter_search}%", f"%{filter_search}%"])
            cursor.execute(query, tuple(params))
        elif role_filter == "teacher" and view_mode == "grouped":
            # Categorized by Section logic: One row per teacher-section pairing
            query = """
                SELECT
                    u.user_id, u.username, u.role, u.full_name, u.gender,
                    u.email, COALESCE(g_u.name, u.grade_level) AS teacher_grade, u.status,
                    s.section_name, g_s.name AS section_grade
                FROM users u
                LEFT JOIN grade_levels g_u ON u.grade_level_id = g_u.id
                JOIN section_teachers st ON u.user_id = st.teacher_id
                JOIN sections s ON st.section_id = s.section_id
                JOIN grade_levels g_s ON s.grade_level_id = g_s.id
                WHERE u.branch_id = %s AND u.role = 'teacher'
            """
            params = [branch_id]
            if filter_search:
                query += " AND (u.username ILIKE %s OR u.full_name ILIKE %s)"
                params.extend([f"%{filter_search}%", f"%{filter_search}%"])
            cursor.execute(query, tuple(params))
        else:
            query = """
                SELECT
                    u.user_id, u.username, u.role, u.full_name, u.gender,
                    u.email, COALESCE(g.name, u.grade_level) AS grade_level, u.status,
                    (SELECT STRING_AGG(DISTINCT s2.section_name, ', ') 
                     FROM section_teachers st2 
                     JOIN sections s2 ON st2.section_id = s2.section_id 
                     WHERE st2.teacher_id = u.user_id) AS sections
                FROM users u
                LEFT JOIN grade_levels g ON u.grade_level_id = g.id
                WHERE u.branch_id = %s AND u.role = %s
            """
            params = [branch_id, role_filter]
            if filter_grade and role_filter == "teacher":
                query += " AND u.grade_level_id = %s"
                params.append(int(filter_grade))
            if filter_section and role_filter == "teacher":
                query += " AND EXISTS (SELECT 1 FROM section_teachers st2 WHERE st2.teacher_id = u.user_id AND st2.section_id = %s)"
                params.append(int(filter_section))
            if filter_search:
                query += " AND (u.username ILIKE %s OR u.full_name ILIKE %s)"
                params.extend([f"%{filter_search}%", f"%{filter_search}%"])
            cursor.execute(query, tuple(params))

        accounts = cursor.fetchall() or []

        # --- ADVANCED ACADEMIC SORTING (PYTHON BASED) ---
        import re
        def academic_sort_key(item):
            # Extract grade string safely from various possible keys
            grade_str = (item.get('grade_level') or item.get('teacher_grade') or item.get('section_grade') or '').lower().strip()
            
            # 1. Nursery/Kinder priority
            if 'nursery' in grade_str: return (1, (item.get('full_name') or '').lower())
            if 'kinder' in grade_str: return (2, (item.get('full_name') or '').lower())
            
            # 2. Sequential Grades (extracting number from "Grade 1", "Grade 11 – STEM", etc)
            nums = re.findall(r'\d+', grade_str)
            if nums:
                return (int(nums[0]) + 10, (item.get('full_name') or '').lower())
            
            # 3. Fallback (Alphabetical for others)
            return (999, (item.get('full_name') or '').lower())

        accounts.sort(key=academic_sort_key)

    except Exception as e:
        db.rollback()
        flash(f"An error occurred: {str(e)}", "error")
        accounts, grades = [], []
    finally:
        cursor.close()
        db.close()

    return render_template(
        "branch_admin_manage_accounts.html",
        role_filter=role_filter,
        view_mode=view_mode,
        accounts=accounts,
        grades=grades,
        section_options=section_options,
        filter_grade=filter_grade,
        filter_section=filter_section,
        filter_search=filter_search
    )


@branch_admin_bp.route("/branch-admin/manage-accounts/<int:user_id>/toggle", methods=["POST"])
def branch_admin_toggle_account(user_id):
    if session.get("role") != "branch_admin":
        return redirect("/")

    db = get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute("""
            UPDATE users 
            SET status = CASE WHEN COALESCE(status, 'active') = 'active' THEN 'inactive' ELSE 'active' END
            WHERE user_id = %s AND branch_id = %s
        """, (user_id, session.get("branch_id")))
        db.commit()
        flash("Account status updated.", "success")
    except Exception as e:
        db.rollback()
        flash(f"Failed to update account: {str(e)}", "error")
    finally:
        cursor.close()
        db.close()
    
    return redirect(request.referrer or url_for("branch_admin.branch_admin_manage_accounts"))
@branch_admin_bp.route("/branch-admin/manage-accounts/<int:user_id>/edit", methods=["GET", "POST"])
def branch_admin_edit_account(user_id):
    if session.get("role") != "branch_admin":
        return redirect("/")
    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        if request.method == "POST":
            full_name = request.form.get("full_name")
            email = request.form.get("email")
            gender = request.form.get("gender")
            grade_level_id = request.form.get("grade_level")
            cursor.execute("""
                UPDATE users SET full_name=%s, email=%s, gender=%s, grade_level_id=%s
                WHERE user_id=%s AND branch_id=%s
            """, (full_name, email, gender, grade_level_id or None, user_id, session.get("branch_id")))
            db.commit()
            flash("Account updated successfully.", "success")
            return redirect(request.referrer or url_for("branch_admin.branch_admin_manage_accounts"))
        cursor.execute("SELECT * FROM users WHERE user_id=%s AND branch_id=%s", (user_id, session.get("branch_id")))
        user = cursor.fetchone()
        cursor.execute("SELECT id, name FROM grade_levels WHERE branch_id=%s ORDER BY display_order", (session.get("branch_id"),))
        grades = cursor.fetchall()
        return render_template("branch_admin_edit_account.html", user=user, grades=grades)
    finally:
        cursor.close()
        db.close()

@branch_admin_bp.route("/branch-admin/manage-accounts/student/<int:account_id>/edit", methods=["GET", "POST"])
def branch_admin_edit_student_account(account_id):
    if session.get("role") != "branch_admin":
        return redirect("/")
    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        if request.method == "POST":
            full_name = request.form.get("full_name")
            email = request.form.get("email")
            gender = request.form.get("gender")
            grade_level = request.form.get("grade_level")
            cursor.execute("UPDATE student_accounts SET email=%s WHERE account_id=%s AND branch_id=%s", 
                           (email, account_id, session.get("branch_id")))
            cursor.execute("""
                UPDATE enrollments SET student_name=%s, gender=%s, grade_level=%s
                WHERE enrollment_id = (SELECT enrollment_id FROM student_accounts WHERE account_id=%s)
            """, (full_name, gender, grade_level, account_id))
            db.commit()
            flash("Student account updated successfully.", "success")
            return redirect(request.referrer or url_for("branch_admin.branch_admin_manage_accounts", role='student'))
        cursor.execute("""
            SELECT sa.*, e.student_name AS full_name, e.gender, e.grade_level
            FROM student_accounts sa
            JOIN enrollments e ON sa.enrollment_id = e.enrollment_id
            WHERE sa.account_id=%s AND sa.branch_id=%s
        """, (account_id, session.get("branch_id")))
        student = cursor.fetchone()
        return render_template("branch_admin_edit_student_account.html", student=student)
    finally:
        cursor.close()
        db.close()

@branch_admin_bp.route("/branch-admin/manage-accounts/<int:user_id>/delete", methods=["POST"])
def branch_admin_delete_account(user_id):
    if session.get("role") != "branch_admin":
        return redirect("/")
    db = get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute("DELETE FROM users WHERE user_id=%s AND branch_id=%s", (user_id, session.get("branch_id")))
        db.commit()
        flash("Account deleted.", "success")
    except Exception as e:
        db.rollback()
        flash(f"Failed to delete: {str(e)}", "error")
    finally:
        cursor.close()
        db.close()
    return redirect(request.referrer or url_for("branch_admin.branch_admin_manage_accounts"))

@branch_admin_bp.route("/branch-admin/manage-accounts/student/<int:account_id>/delete", methods=["POST"])
def branch_admin_delete_student_account(account_id):
    if session.get("role") != "branch_admin":
        return redirect("/")
    db = get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute("DELETE FROM student_accounts WHERE account_id=%s AND branch_id=%s", (account_id, session.get("branch_id")))
        db.commit()
        flash("Student account deleted.", "success")
    except Exception as e:
        db.rollback()
        flash(f"Failed to delete student account: {str(e)}", "error")
    finally:
        cursor.close()
        db.close()
    return redirect(request.referrer or url_for("branch_admin.branch_admin_manage_accounts", role='student'))

@branch_admin_bp.route("/api/branch-admin/filtered-accounts")
def get_filtered_accounts_api():
    if session.get("role") != "branch_admin":
        return jsonify({"error": "Unauthorized"}), 403
    
    branch_id = session.get("branch_id")
    role = request.args.get("role", "registrar").strip().lower()
    grade = request.args.get("grade", "")
    section = request.args.get("section", "")
    
    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    try:
        if role == "student":
            query = """
                SELECT 
                    sa.account_id, sa.username, 'student' AS role, e.student_name AS full_name,
                    e.gender, e.grade_level, sa.is_active, sa.email, e.enrollment_id,
                    s.section_name
                FROM student_accounts sa
                JOIN enrollments e ON sa.enrollment_id = e.enrollment_id
                LEFT JOIN sections s ON e.section_id = s.section_id
                WHERE sa.branch_id = %s
            """
            params = [branch_id]
            if grade:
                query += " AND e.grade_level = %s"
                params.append(grade)
            if section:
                query += " AND e.section_id = %s"
                params.append(int(section))
            
            query += " ORDER BY e.student_name ASC"
            cursor.execute(query, tuple(params))
        else:
            query = """
                SELECT
                    u.user_id, u.username, u.role, u.full_name, u.gender,
                    u.email, COALESCE(g.name, u.grade_level) AS grade_level, u.status,
                    STRING_AGG(DISTINCT s.section_name, ', ') AS sections
                FROM users u
                LEFT JOIN grade_levels g ON u.grade_level_id = g.id
                LEFT JOIN section_teachers st ON u.user_id = st.teacher_id
                LEFT JOIN sections s ON st.section_id = s.section_id
                WHERE u.branch_id = %s AND u.role = %s
            """
            params = [branch_id, role]
            if grade and role == "teacher":
                query += " AND u.grade_level_id = %s"
                params.append(int(grade))
            if section and role == "teacher":
                query += " AND EXISTS (SELECT 1 FROM section_teachers st2 WHERE st2.teacher_id = u.user_id AND st2.section_id = %s)"
                params.append(int(section))
            
            query += " GROUP BY u.user_id, g.name ORDER BY u.user_id DESC"
            cursor.execute(query, tuple(params))
        
        accounts = cursor.fetchall() or []
        
        # Also return section options for this branch
        cursor.execute("""
            SELECT s.section_id, s.section_name, g.name as grade_level_name, g.id as grade_level_id
            FROM sections s 
            JOIN grade_levels g ON s.grade_level_id = g.id 
            WHERE s.branch_id = %s 
            ORDER BY g.display_order, s.section_name
        """, (branch_id,))
        section_options = cursor.fetchall() or []

        return jsonify({
            "accounts": accounts,
            "section_options": section_options
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        db.close()

def _get_active_school_year(cur, branch_id):
    cur.execute("""
        SELECT year_id 
        FROM school_years 
        WHERE is_active = TRUE AND branch_id = %s
        LIMIT 1
    """, (branch_id,))
    row = cur.fetchone()
    if not row:
        return None
    if isinstance(row, tuple):
        return row[0]
    return row["year_id"]

# =======================
# ACADEMIC CALENDAR (Branch Admin)
# =======================
@branch_admin_bp.route("/branch-admin/academic-calendar", methods=["GET", "POST"])
def branch_admin_academic_calendar():
    if session.get("role") != "branch_admin":
        return redirect(url_for("auth.login"))

    branch_id = session.get("branch_id")
    db = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        year_id = _get_active_school_year(cur, branch_id)
        if not year_id:
            flash("No active school year found for this branch.", "error")
            return redirect(url_for("branch_admin.branch_admin_dashboard"))

        today = datetime.now().date()
        today_str = today.strftime('%Y-%m-%d')

        if request.method == "POST":
            action = request.form.get("action")

            if action == "save_ranges":
                periods = ["1st", "2nd", "3rd", "4th"]
                try:
                    for p in periods:
                        start_d_str = request.form.get(f"{p}_start")
                        end_d_str   = request.form.get(f"{p}_end")
                        
                        if start_d_str and end_d_str:
                            # Server-side validation: end date at least 1.5 months (approx 45 days) after start
                            s_dt = datetime.strptime(start_d_str, '%Y-%m-%d')
                            e_dt = datetime.strptime(end_d_str, '%Y-%m-%d')
                            if (e_dt - s_dt).days < 45:
                                flash(f"For {p} Grading: Period must be at least 45 days (1.5 months).", "error")
                                continue

                            cur.execute("""
                                INSERT INTO grading_period_ranges (branch_id, year_id, period_name, start_date, end_date)
                                VALUES (%s, %s, %s, %s, %s)
                                ON CONFLICT (branch_id, year_id, period_name) DO UPDATE
                                SET start_date = EXCLUDED.start_date, end_date = EXCLUDED.end_date
                            """, (branch_id, year_id, p, start_d_str, end_d_str))
                    db.commit()
                    flash("Grading periods updated successfully.", "success")
                except Exception as e:
                    db.rollback()
                    flash(f"Error saving ranges: {str(e)}", "error")

            elif action == "add_holiday":
                h_date_str = request.form.get("holiday_date")
                h_name = request.form.get("holiday_name")
                if h_date_str and h_name:
                    try:
                        cur.execute("""
                                INSERT INTO holidays (branch_id, year_id, holiday_date, holiday_name)
                                VALUES (%s, %s, %s, %s)
                                ON CONFLICT (branch_id, year_id, holiday_date) DO UPDATE
                                SET holiday_name = EXCLUDED.holiday_name
                            """, (branch_id, year_id, h_date_str, h_name))
                        db.commit()
                        flash("Local holiday added.", "success")
                    except Exception as e:
                        db.rollback()
                        flash(f"Error: {str(e)}", "error")

        # Fetch ranges
        cur.execute("""
            SELECT period_name, start_date, end_date 
            FROM grading_period_ranges 
            WHERE branch_id = %s AND year_id = %s
        """, (branch_id, year_id))
        ranges_raw = cur.fetchall() or []
        ranges = {r["period_name"]: r for r in ranges_raw}

        # Fetch holidays (Local and Global)
        cur.execute("""
            SELECT id, holiday_date, holiday_name, branch_id
            FROM holidays 
            WHERE (branch_id = %s OR branch_id IS NULL) AND year_id = %s
            ORDER BY holiday_date ASC
        """, (branch_id, year_id))
        holidays = cur.fetchall() or []

        return render_template("branch_admin_academic_calendar.html", 
                               ranges=ranges, holidays=holidays, today=today_str)

    finally:
        cur.close()
        db.close()

@branch_admin_bp.route("/branch-admin/academic-calendar/delete-holiday/<int:holiday_id>", methods=["POST"])
def branch_admin_delete_holiday(holiday_id):
    if session.get("role") != "branch_admin":
        return redirect(url_for("auth.login"))

    branch_id = session.get("branch_id")
    db = get_db_connection()
    cur = db.cursor()
    try:
        # Only allow deleting local holidays
        cur.execute("DELETE FROM holidays WHERE id = %s AND branch_id = %s", (holiday_id, branch_id))
        db.commit()
        flash("Local holiday deleted.", "success")
    except Exception as e:
        db.rollback()
        flash(f"Error: {str(e)}", "error")
    finally:
        cur.close()
        db.close()
    return redirect(url_for("branch_admin.branch_admin_academic_calendar"))

@branch_admin_bp.route("/branch-admin/attendance")
def branch_admin_attendance():
    if session.get("role") != "branch_admin":
        return redirect(url_for("auth.login"))

    branch_id = session.get("branch_id")
    db = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    try:
        year_id = _get_active_school_year(cur, branch_id)
        
        ph_tz = pytz.timezone("Asia/Manila")
        today = datetime.now(ph_tz).date()

        # 1. Teachers Missing Attendance Today
        # We find all schedules for today, and check if there's a daily_attendance record for that section/subject today.
        today_name = today.strftime('%A')
        cur.execute("""
            SELECT sc.teacher_id, u.full_name AS teacher_name, sub.name AS subject_name,
                   g.name AS grade_level, s.section_name, sc.start_time, sc.end_time
            FROM schedules sc
            JOIN users u ON sc.teacher_id = u.user_id
            JOIN subjects sub ON sc.subject_id = sub.subject_id
            JOIN sections s ON sc.section_id = s.section_id
            JOIN grade_levels g ON s.grade_level_id = g.id
            WHERE sc.branch_id = %s AND sc.year_id = %s AND sc.day_of_week = %s
              AND NOT EXISTS (
                  SELECT 1 FROM daily_attendance da
                  JOIN enrollments e ON da.enrollment_id = e.enrollment_id
                  WHERE da.subject_id = sc.subject_id 
                    AND da.attendance_date = %s
                    AND e.section_id = sc.section_id
              )
            ORDER BY sc.start_time
        """, (branch_id, year_id, today_name, today))
        missing_attendance = cur.fetchall()

        # 2. Habitual Absentees (>= 3 absences across any subject)
        cur.execute("""
            SELECT e.enrollment_id, e.student_name, g.name AS grade_level, s.section_name,
                   COUNT(da.id) as absent_count,
                   MAX(da.attendance_date) as last_absence
            FROM daily_attendance da
            JOIN enrollments e ON da.enrollment_id = e.enrollment_id
            LEFT JOIN sections s ON e.section_id = s.section_id
            LEFT JOIN grade_levels g ON (e.grade_level = g.name AND g.branch_id = %s)
            WHERE da.branch_id = %s AND da.year_id = %s AND da.status = 'A'
            GROUP BY e.enrollment_id, e.student_name, g.name, s.section_name
            HAVING COUNT(da.id) >= 3
            ORDER BY absent_count DESC
        """, (branch_id, branch_id, year_id))
        habitual_absentees = cur.fetchall()

        # 3. Overall Branch Attendance Stats for Today
        cur.execute("""
            SELECT status, COUNT(*) as count
            FROM daily_attendance
            WHERE branch_id = %s AND year_id = %s AND attendance_date = %s
            GROUP BY status
        """, (branch_id, year_id, today))
        today_stats_rows = cur.fetchall()
        
        today_stats = {'P': 0, 'A': 0, 'L': 0, 'E': 0, 'H': 0}
        total_records = 0
        for row in today_stats_rows:
            status = row['status']
            count = row['count']
            if status in today_stats:
                today_stats[status] = count
            total_records += count
            
        attendance_rate = 0
        if total_records > 0:
            # P, L, E, H are all considered "Present/Excused" in the rate calculation
            present_total = today_stats['P'] + today_stats['L'] + today_stats['H'] + today_stats['E']
            attendance_rate = (present_total / total_records) * 100
            if attendance_rate % 1 == 0:
                attendance_rate = int(attendance_rate)
            else:
                attendance_rate = round(attendance_rate, 1)

        return render_template(
            "branch_admin_attendance.html",
            missing_attendance=missing_attendance,
            habitual_absentees=habitual_absentees,
            today_stats=today_stats,
            attendance_rate=attendance_rate,
            today_date=today.strftime('%B %d, %Y')
        )

    except Exception as e:
        flash(f"Error fetching attendance data: {str(e)}", "error")
        return redirect(url_for("branch_admin.dashboard"))
    finally:
        cur.close()
        db.close()

