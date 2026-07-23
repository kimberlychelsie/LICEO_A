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
            first_name   = (request.form.get("first_name")   or "").strip()
            middle_name  = (request.form.get("middle_name")  or "").strip()
            last_name    = (request.form.get("last_name")    or "").strip()
            gender       = (request.form.get("gender")       or "").strip().lower()
            custom_uname = (request.form.get("username")     or "").strip()
            user_email   = (request.form.get("email")        or "").strip()

            full_name = f"{first_name} {middle_name} {last_name}".strip().replace("  ", " ")

            if role not in ("registrar", "cashier", "librarian", "teacher"):
                flash("Invalid role selected.", "error")
                return redirect("/branch-admin/manage-accounts")

            if not first_name or not last_name:
                flash("First name and Last name are required.", "error")
                return redirect("/branch-admin/manage-accounts")
            if role == "teacher":
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
                         grade_level_id, first_name, middle_name, last_name, full_name, gender, email)
                    VALUES (%s, %s, %s, %s, TRUE, %s, %s, %s, %s, %s, %s, %s)
                """, (branch_id, username, hashed_password, role,
                      grade_level or None, first_name, middle_name or None, last_name, full_name, gender or None, user_email))
            else:
                cursor.execute("""
                    INSERT INTO users
                        (branch_id, username, password, role, require_password_change, first_name, middle_name, last_name, full_name, gender, email)
                    VALUES (%s, %s, %s, %s, TRUE, %s, %s, %s, %s, %s, %s)
                """, (branch_id, username, hashed_password, role, first_name, middle_name or None, last_name, full_name, gender or None, user_email))
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
                    sa.account_id, sa.username, 'student' AS role, CONCAT_WS(' ', e.student_first_name, e.student_middle_name, e.student_last_name) AS full_name,
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
                query += " AND (sa.username ILIKE %s OR e.student_first_name ILIKE %s OR e.student_last_name ILIKE %s)"
                params.extend([f"%{filter_search}%", f"%{filter_search}%", f"%{filter_search}%"])
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
            first_name = request.form.get("first_name", "").strip()
            middle_name = request.form.get("middle_name", "").strip()
            last_name = request.form.get("last_name", "").strip()
            email = request.form.get("email")
            gender = request.form.get("gender")
            grade_level_id = request.form.get("grade_level")
            
            if not first_name or not last_name:
                flash("First name and Last name are required.", "error")
                return redirect(request.referrer or url_for("branch_admin.branch_admin_manage_accounts"))
                
            full_name = f"{first_name} {middle_name} {last_name}".strip().replace("  ", " ")
            cursor.execute("""
                UPDATE users SET first_name=%s, middle_name=%s, last_name=%s, full_name=%s, email=%s, gender=%s, grade_level_id=%s
                WHERE user_id=%s AND branch_id=%s
            """, (first_name, middle_name or None, last_name, full_name, email, gender, grade_level_id or None, user_id, session.get("branch_id")))
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
            parts = full_name.split(" ", 1)
            fname = parts[0]
            lname = parts[1] if len(parts) > 1 else ""
            cursor.execute("""
                UPDATE enrollments SET student_first_name=%s, student_last_name=%s, gender=%s, grade_level=%s
                WHERE enrollment_id = (SELECT enrollment_id FROM student_accounts WHERE account_id=%s)
            """, (fname, lname, gender, grade_level, account_id))
            db.commit()
            flash("Student account updated successfully.", "success")
            return redirect(request.referrer or url_for("branch_admin.branch_admin_manage_accounts", role='student'))
        cursor.execute("""
            SELECT sa.*, CONCAT_WS(' ', e.student_first_name, e.student_middle_name, e.student_last_name) AS full_name, e.gender, e.grade_level
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
        # Also fetch the enrollment_id to delete the enrollment record
        cursor.execute("SELECT enrollment_id FROM student_accounts WHERE account_id=%s AND branch_id=%s", (account_id, session.get("branch_id")))
        res = cursor.fetchone()
        
        cursor.execute("DELETE FROM student_accounts WHERE account_id=%s AND branch_id=%s", (account_id, session.get("branch_id")))
        
        if res:
            enrollment_id = res[0]
            
            # Explicitly delete child records because CASCADE might fail due to DB permissions
            tables_to_clear = [
                'attendance_scores', 'book_releases', 'payments', 'individual_extensions', 
                'billing', 'daily_participation', 'finalized_grades', 'daily_attendance', 
                'exam_student_permissions', 'exam_results', 'participation_scores', 
                'activity_submissions', 'enrollment_books', 'enrollment_documents', 
                'enrollment_uniforms', 'enrollment_history', 'posted_grades', 'extensions', 'reservations'
            ]
            for t in tables_to_clear:
                try:
                    cursor.execute(f"SAVEPOINT delete_{t}")
                    cursor.execute(f"DELETE FROM {t} WHERE enrollment_id=%s", (enrollment_id,))
                    cursor.execute(f"RELEASE SAVEPOINT delete_{t}")
                except Exception:
                    cursor.execute(f"ROLLBACK TO SAVEPOINT delete_{t}")
            
            # Now safe to delete the enrollment record
            cursor.execute("DELETE FROM enrollments WHERE enrollment_id=%s", (enrollment_id,))
            
        db.commit()
        flash("Student account and related enrollment deleted.", "success")
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
                    sa.account_id, sa.username, 'student' AS role, CONCAT_WS(' ', e.student_first_name, e.student_middle_name, e.student_last_name) AS full_name,
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
            
            query += " ORDER BY e.student_last_name ASC, e.student_first_name ASC"
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
                periods = ["1st", "2nd", "3rd"]
                try:
                    for p in periods:
                        start_d_str = request.form.get(f"{p}_start")
                        end_d_str   = request.form.get(f"{p}_end")
                        
                        if start_d_str and end_d_str:
                            # Server-side validation: end date at least 1.5 months (approx 45 days) after start
                            s_dt = datetime.strptime(start_d_str, '%Y-%m-%d')
                            e_dt = datetime.strptime(end_d_str, '%Y-%m-%d')
                            if (e_dt - s_dt).days < 45:
                                period_labels = {"1st": "1st Term", "2nd": "2nd Term", "3rd": "3rd Term"}
                                flash(f"For {period_labels.get(p, p)}: Period must be at least 45 days (1.5 months).", "error")
                                continue

                            cur.execute("""
                                INSERT INTO grading_period_ranges (branch_id, year_id, period_name, start_date, end_date)
                                VALUES (%s, %s, %s, %s, %s)
                                ON CONFLICT (branch_id, year_id, period_name) DO UPDATE
                                SET start_date = EXCLUDED.start_date, end_date = EXCLUDED.end_date
                            """, (branch_id, year_id, p, start_d_str, end_d_str))
                    db.commit()
                    flash("Terms updated successfully.", "success")
                except Exception as e:
                    db.rollback()
                    flash(f"Error saving ranges: {str(e)}", "error")



        # Fetch ranges
        cur.execute("""
            SELECT period_name, start_date, end_date 
            FROM grading_period_ranges 
            WHERE branch_id = %s AND year_id = %s
        """, (branch_id, year_id))
        ranges_raw = cur.fetchall() or []
        ranges = {r["period_name"]: r for r in ranges_raw}

        return render_template("branch_admin_academic_calendar.html", 
                               ranges=ranges, today=today_str)

    finally:
        cur.close()
        db.close()








# --- MOVED FROM REGISTRAR ---

@branch_admin_bp.route("/branch-admin/schedules", methods=['GET', 'POST'])
def list_and_add_schedules():
    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    branch_id = session["branch_id"]

    # Only show combos for SECTIONS in ACTIVE years for THIS branch:
    cursor.execute("""
        SELECT st.section_id, sec.section_name, st.subject_id, subj.name AS subject_name,
               st.teacher_id, u.full_name AS teacher_name, sec.year_id, g.name AS grade_name
        FROM section_teachers st
        JOIN sections sec ON st.section_id = sec.section_id
        JOIN grade_levels g ON sec.grade_level_id = g.id
        JOIN school_years y ON sec.year_id = y.year_id
        JOIN subjects subj ON st.subject_id = subj.subject_id
        JOIN users u ON st.teacher_id = u.user_id
        WHERE sec.branch_id = %s
          AND y.is_active = TRUE
        ORDER BY g.id ASC, sec.section_name ASC, subj.name ASC
    """, (branch_id,))
    combinations = cursor.fetchall()

    # Only fetch ACTIVE school years for the dropdown
    cursor.execute("""
        SELECT year_id, label FROM school_years 
        WHERE is_active = TRUE AND branch_id = %s 
        ORDER BY label DESC
    """, (branch_id,))
    school_years = cursor.fetchall()
    active_year = school_years[0] if school_years else None

    # Fetch unique Grades and Sections for filtering
    cursor.execute("SELECT name FROM grade_levels WHERE name NOT IN ('Grade 11', 'Grade 12') ORDER BY id ASC")
    all_grades_list = [row["name"] for row in cursor.fetchall()]
    cursor.execute("""
        SELECT s.section_id, s.section_name, g.name AS grade_name
        FROM sections s
        JOIN grade_levels g ON g.id = s.grade_level_id
        WHERE s.branch_id = %s
        ORDER BY g.id, s.section_name
    """, (branch_id,))
    all_sections_list = cursor.fetchall()

    if request.method == "POST":
        combo = request.form["combo"]
        section_id, subject_id, teacher_id = combo.split('|')
        day_of_week = request.form["day_of_week"]
        start_time = request.form["start_time"]
        end_time = request.form["end_time"]
        room = request.form["room"]
        # Use active year automatically
        year_id = active_year["year_id"] if active_year else None

        if not year_id:
            flash("No active school year found. Cannot add schedule.", "danger")
            cursor.close(); db.close()
            return redirect(url_for("branch_admin.list_and_add_schedules"))

        # --- TIME VALIDATION: must be within 07:00 and 17:00, and start < end ---
        start_t = datetime.strptime(start_time, "%H:%M").time()
        end_t = datetime.strptime(end_time, "%H:%M").time()
        if not (time(7,0) <= start_t <= time(17,0)) or not (time(7,0) <= end_t <= time(17,0)):
            flash("Invalid schedule: Times must be between 07:00 and 17:00.", "danger")
            cursor.close(); db.close()
            return redirect(url_for("branch_admin.list_and_add_schedules"))
        if start_t >= end_t:
            flash("Invalid schedule: Start time must be before end time.", "danger")
            cursor.close(); db.close()
            return redirect(url_for("branch_admin.list_and_add_schedules"))
        if (start_t.minute % 15) != 0 or (end_t.minute % 15) != 0:
            flash("Invalid schedule: Times must be in 15-minute increments.", "danger")
            cursor.close(); db.close()
            return redirect(url_for("branch_admin.list_and_add_schedules"))

        # --- ROOM VALIDATION: must be a number between 1 and 30 ---
        try:
            room_val = int(room)
            if not (1 <= room_val <= 30):
                flash("Invalid Room: Room number must be between 1 and 30.", "danger")
                cursor.close(); db.close()
                return redirect(url_for("branch_admin.list_and_add_schedules"))
        except (ValueError, TypeError):
            flash("Invalid Room: Please enter a numeric room number (1-30).", "danger")
            cursor.close(); db.close()
            return redirect(url_for("branch_admin.list_and_add_schedules"))

        # --- DETAILED COLLISION CHECK ---
        cursor.execute("""
            SELECT s.*, subj.name AS conflict_subject_name, sec.section_name AS conflict_section_name, 
                   u.full_name AS conflict_teacher_name, y.label AS conflict_year_label
            FROM schedules s
            JOIN subjects subj ON s.subject_id = subj.subject_id
            JOIN sections sec ON s.section_id = sec.section_id
            JOIN users u ON s.teacher_id = u.user_id
            JOIN school_years y ON s.year_id = y.year_id
            WHERE s.year_id = %s AND s.branch_id = %s
              AND s.day_of_week = %s
              AND s.is_archived = FALSE
              AND (s.start_time < %s AND s.end_time > %s)
              AND (
                    s.teacher_id = %s
                 OR s.section_id = %s
                 OR s.room = %s
              )
            LIMIT 1
        """, (year_id, branch_id, day_of_week, end_time, start_time, teacher_id, section_id, room))
        conflict = cursor.fetchone()
        if conflict:
            reasons = []
            if str(conflict["teacher_id"]) == str(teacher_id):
                reasons.append(f"Teacher {conflict['conflict_teacher_name']}")
            if str(conflict["section_id"]) == str(section_id):
                reasons.append(f"Section {conflict['conflict_section_name']}")
            if str(conflict["room"]) == str(room):
                reasons.append(f"Room {conflict['room']}")

            conflict_types = " and ".join(reasons)
            conflict_slot = f"{conflict['day_of_week']} {conflict['start_time'].strftime('%H:%M')}-{conflict['end_time'].strftime('%H:%M')}"
            conflict_subj = conflict.get("conflict_subject_name", "")
            message = (f"Conflict detected: {conflict_types} already has "
                       f"{conflict_subj} scheduled on {conflict_slot}. "
                       "Please choose a different time or resource.")
            flash(message, "danger")
            cursor.close(); db.close()
            return redirect(url_for("branch_admin.list_and_add_schedules"))

        # --- INSERT IF NO ISSUES ---
        cursor.execute("""
            INSERT INTO schedules
            (subject_id, section_id, teacher_id, day_of_week, start_time, end_time, room, year_id, branch_id)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            subject_id, section_id, teacher_id,
            day_of_week, start_time, end_time, room, year_id, branch_id
        ))
        db.commit()
        flash("Schedule added!", "success")
        cursor.close(); db.close()
        return redirect(url_for("branch_admin.list_and_add_schedules"))

    # Filter by Archive Status
    show_archived = request.args.get("show_archived") == "true"
    
    # List all schedules for this branch's sections 
    cursor.execute("""
        SELECT s.*, subj.name AS subject_name, sec.section_name AS section_name, 
               u.full_name AS teacher_name, y.label AS year_label,
               g.name AS grade_name
        FROM schedules s
        JOIN subjects subj ON s.subject_id = subj.subject_id
        JOIN sections sec ON s.section_id = sec.section_id
        JOIN grade_levels g ON g.id = sec.grade_level_id
        JOIN users u ON s.teacher_id = u.user_id
        JOIN school_years y ON s.year_id = y.year_id
        WHERE s.branch_id = %s
          AND y.branch_id = %s
          AND y.is_active = TRUE
          AND s.is_archived = %s
        ORDER BY y.label DESC, sec.section_name, subj.name, s.day_of_week, s.start_time
    """, (branch_id, branch_id, show_archived))
    schedules = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "schedules_allinone.html",
        schedules=schedules,
        combinations=combinations,
        active_year=active_year,
        show_archived=show_archived,
        all_grades=all_grades_list,
        all_sections=all_sections_list
    )



from datetime import datetime, time

@branch_admin_bp.route("/branch-admin/schedules/<int:schedule_id>/edit", methods=["GET", "POST"])
def edit_schedule(schedule_id):
    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    branch_id = session.get("branch_id")

    cursor.execute("""
        SELECT s.*, 
               subj.name AS subject_name, 
               sec.section_name AS section_name, 
               u.full_name AS teacher_name,
               y.label AS year_label
        FROM schedules s
        JOIN subjects subj ON s.subject_id = subj.subject_id
        JOIN sections sec ON s.section_id = sec.section_id
        JOIN users u ON s.teacher_id = u.user_id
        JOIN school_years y ON s.year_id = y.year_id
        WHERE s.schedule_id = %s AND s.branch_id = %s
    """, (schedule_id, branch_id))
    schedule = cursor.fetchone()
    if not schedule:
        cursor.close(); db.close()
        abort(404)

    # Repopulate combinations as in add view
    cursor.execute("""
        SELECT st.section_id, sec.section_name, st.subject_id, subj.name AS subject_name,
               st.teacher_id, u.full_name AS teacher_name, sec.year_id
        FROM section_teachers st
        JOIN sections sec ON st.section_id = sec.section_id
        JOIN school_years y ON sec.year_id = y.year_id
        JOIN subjects subj ON st.subject_id = subj.subject_id
        JOIN users u ON st.teacher_id = u.user_id
        WHERE sec.branch_id = %s
          AND y.is_active = TRUE
        ORDER BY y.label DESC, sec.section_name, subj.name, u.full_name
    """, (branch_id,))
    combinations = cursor.fetchall()

    # Only fetch ACTIVE school years for the dropdown
    cursor.execute("""
        SELECT year_id, label FROM school_years 
        WHERE is_active = TRUE AND branch_id = %s
        ORDER BY label DESC
    """, (branch_id,))
    school_years = cursor.fetchall()
    active_year = school_years[0] if school_years else None

    if request.method == "POST":
        combo = request.form["combo"]
        section_id, subject_id, teacher_id = combo.split('|')
        day_of_week = request.form["day_of_week"]
        start_time = request.form["start_time"]
        end_time = request.form["end_time"]
        room = request.form["room"]
        year_id = request.form["year_id"]

        # --- TIME VALIDATION: must be within 07:00 and 17:00, and start < end ---
        start_t = datetime.strptime(start_time, "%H:%M").time()
        end_t = datetime.strptime(end_time, "%H:%M").time()
        if not (time(7,0) <= start_t <= time(17,0)) or not (time(7,0) <= end_t <= time(17,0)):
            flash("Invalid schedule: Times must be between 07:00 and 17:00.", "danger")
            cursor.close(); db.close()
            return redirect(url_for("branch_admin.list_and_add_schedules"))
        if start_t >= end_t:
            flash("Invalid schedule: Start time must be before end time.", "danger")
            cursor.close(); db.close()
            return redirect(url_for("branch_admin.list_and_add_schedules"))
        if (start_t.minute % 15) != 0 or (end_t.minute % 15) != 0:
            flash("Invalid schedule: Times must be in 15-minute increments.", "danger")
            cursor.close(); db.close()
            return redirect(url_for("branch_admin.list_and_add_schedules"))

        # --- ROOM VALIDATION: must be a number between 1 and 30 ---
        try:
            room_val = int(room)
            if not (1 <= room_val <= 30):
                flash("Invalid Room: Room number must be between 1 and 30.", "danger")
                cursor.close(); db.close()
                return redirect(url_for("branch_admin.list_and_add_schedules"))
        except (ValueError, TypeError):
            flash("Invalid Room: Please enter a numeric room number (1-30).", "danger")
            cursor.close(); db.close()
            return redirect(url_for("branch_admin.list_and_add_schedules"))

        # --- DETAILED COLLISION CHECK ---
        cursor.execute("""
            SELECT s.*, subj.name AS conflict_subject_name, sec.section_name AS conflict_section_name, 
                   u.full_name AS conflict_teacher_name, y.label AS conflict_year_label
            FROM schedules s
            JOIN subjects subj ON s.subject_id = subj.subject_id
            JOIN sections sec ON s.section_id = sec.section_id
            JOIN users u ON s.teacher_id = u.user_id
            JOIN school_years y ON s.year_id = y.year_id
            WHERE s.year_id = %s AND s.branch_id = %s
              AND s.day_of_week = %s
              AND s.is_archived = FALSE
              AND (s.start_time < %s AND s.end_time > %s)
              AND (
                    s.teacher_id = %s
                 OR s.section_id = %s
                 OR s.room = %s
              )
              AND s.schedule_id != %s
            LIMIT 1
        """, (year_id, branch_id, day_of_week, end_time, start_time, teacher_id, section_id, room, schedule_id))

        conflict = cursor.fetchone()
        if conflict:
            reasons = []
            if str(conflict["teacher_id"]) == str(teacher_id):
                reasons.append(f"Teacher {conflict['conflict_teacher_name']}")
            if str(conflict["section_id"]) == str(section_id):
                reasons.append(f"Section {conflict['conflict_section_name']}")
            if str(conflict["room"]) == str(room):
                reasons.append(f"Room {conflict['room']}")

            conflict_types = " and ".join(reasons)
            conflict_slot = f"{conflict['day_of_week']} {conflict['start_time'].strftime('%H:%M')}-{conflict['end_time'].strftime('%H:%M')}"
            conflict_subj = conflict.get("conflict_subject_name", "")
            message = (f"Conflict detected: {conflict_types} already has "
                       f"{conflict_subj} scheduled on {conflict_slot}. "
                       "Please choose a different time or resource.")
            flash(message, "danger")
            cursor.close(); db.close()
            return redirect(url_for("branch_admin.list_and_add_schedules"))

        cursor.execute("""
            UPDATE schedules
            SET subject_id=%s, section_id=%s, teacher_id=%s, day_of_week=%s,
                start_time=%s, end_time=%s, room=%s, year_id=%s
            WHERE schedule_id=%s AND branch_id=%s
        """, (subject_id, section_id, teacher_id, day_of_week, start_time, end_time, room, active_year["year_id"] if active_year else year_id, schedule_id, branch_id))
        db.commit()
        cursor.close(); db.close()
        flash("Schedule updated!", "success")
        return redirect(url_for("branch_admin.list_and_add_schedules"))

    cursor.close(); db.close()
    return render_template(
        "schedule_edit.html",
        schedule=schedule,
        combinations=combinations,
        active_year=active_year
    )


@branch_admin_bp.route("/branch-admin/schedules/<int:schedule_id>/archive", methods=["POST"])
def archive_schedule(schedule_id):
    db = get_db_connection()
    cursor = db.cursor()
    branch_id = session.get("branch_id")
    cursor.execute("""
        UPDATE schedules SET is_archived = TRUE WHERE schedule_id = %s AND branch_id = %s
    """, (schedule_id, branch_id))
    db.commit()
    cursor.close(); db.close()
    flash("Schedule archived.", "warning")
    return redirect(url_for("branch_admin.list_and_add_schedules"))

@branch_admin_bp.route("/branch-admin/schedules/<int:schedule_id>/unarchive", methods=["POST"])
def unarchive_schedule(schedule_id):
    db = get_db_connection()
    cursor = db.cursor()
    branch_id = session.get("branch_id")
    cursor.execute("""
        UPDATE schedules SET is_archived = FALSE WHERE schedule_id = %s AND branch_id = %s
    """, (schedule_id, branch_id))
    db.commit()
    cursor.close(); db.close()
    flash("Schedule restored!", "success")
    return redirect(url_for("branch_admin.list_and_add_schedules", show_archived="true"))

@branch_admin_bp.route("/branch-admin/schedules/<int:schedule_id>/delete_permanent", methods=["POST"])
def delete_schedule_permanent(schedule_id):
    db = get_db_connection()
    cursor = db.cursor()
    branch_id = session.get("branch_id")
    cursor.execute("""
        DELETE FROM schedules WHERE schedule_id = %s AND branch_id = %s
    """, (schedule_id, branch_id))
    db.commit()
    cursor.close(); db.close()
    flash("Schedule permanently deleted.", "danger")
    return redirect(url_for("branch_admin.list_and_add_schedules", show_archived="true"))
@branch_admin_bp.route("/branch-admin/grade-levels", methods=["GET", "POST"])
def branch_admin_grade_levels():
    if session.get("role") != "branch_admin":
        return redirect("/")

    branch_id = session.get("branch_id")
    db = get_db_connection()
    cursor = db.cursor()

    # Fetch all unique grade names from the system, sorted by their academic order
    cursor.execute("SELECT name FROM grade_levels GROUP BY name ORDER BY MIN(display_order)")
    available_grade_names = [row[0] for row in cursor.fetchall()]
    
    # Defaults if DB is empty
    if not available_grade_names:
        available_grade_names = [
            "Nursery", "Kinder", "Grade 1", "Grade 2", "Grade 3",
            "Grade 4", "Grade 5", "Grade 6", "Grade 7", "Grade 8",
            "Grade 9", "Grade 10", "Grade 11", "Grade 12"
        ]

    if request.method == "POST":
        name = (request.form.get("name") or "").strip()

        # ? validation
        if name not in available_grade_names:
            flash("Invalid grade level selected.", "error")
            return redirect(url_for('branch_admin.branch_admin_grade_levels'))

        cursor.execute("SELECT COUNT(*) FROM grade_levels WHERE branch_id = %s", (branch_id,))
        current_count = cursor.fetchone()[0]

        if current_count >= 20:
            flash("Maximum limit of 20 grade levels reached. You cannot add more.", "error")
            return redirect(url_for('branch_admin.branch_admin_grade_levels'))

        cursor.execute("SELECT COALESCE(MAX(display_order), 0) + 1 FROM grade_levels WHERE branch_id = %s", (branch_id,))
        order_int = cursor.fetchone()[0]

        if not name:
            flash("Name is required.", "error")
        else:
            try:
                cursor.execute(
                    "INSERT INTO grade_levels (name, display_order, branch_id) VALUES (%s, %s, %s)",
                    (name, order_int, branch_id)
                )
                db.commit()
                flash("Grade level added!", "success")
                return redirect(url_for('branch_admin.branch_admin_grade_levels'))
            except Exception as e:
                db.rollback()
                if "duplicate key" in str(e).lower():
                    flash(f"Grade level '{name}' already exists for this branch.", "error")
                else:
                    flash(f"Could not add grade level: {str(e)}", "error")

    cursor.execute(
        "SELECT id, name, display_order, description FROM grade_levels WHERE branch_id = %s ORDER BY display_order",
        (branch_id,)
    )
    grades = cursor.fetchall()
    
    next_order = max([g[2] for g in grades]) + 1 if grades else 1

    cursor.close()
    db.close()

    return render_template("branch_admin_grade_levels.html", grades=grades, next_order=next_order, available_grade_names=available_grade_names)

@branch_admin_bp.route("/branch-admin/grade-levels/<int:grade_id>/edit", methods=["POST"])
def branch_admin_grade_level_edit(grade_id):
    if session.get("role") != "branch_admin":
        return redirect("/")
    branch_id = session.get("branch_id")
    name = (request.form.get("edit_name") or "").strip()
    order = request.form.get("edit_display_order") or None
    if not name or order is None:
        flash("All fields required.", "error")
        return redirect(url_for("branch_admin.branch_admin_grade_levels"))
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute(
        "UPDATE grade_levels SET name=%s, display_order=%s WHERE id=%s AND branch_id=%s",
        (name, int(order), grade_id, branch_id)
    )
    db.commit()
    cursor.close(); db.close()
    flash("Grade level updated.", "success")
    return redirect(url_for("branch_admin.branch_admin_grade_levels"))

@branch_admin_bp.route("/branch-admin/grade-levels/<int:grade_id>/delete", methods=["POST"])
def branch_admin_grade_level_delete(grade_id):
    if session.get("role") != "branch_admin":
        return redirect("/")
    branch_id = session.get("branch_id")
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute("DELETE FROM grade_levels WHERE id=%s AND branch_id=%s", (grade_id, branch_id))
    db.commit()
    cursor.close(); db.close()
    flash("Grade level deleted.", "success")
    return redirect(url_for("branch_admin.branch_admin_grade_levels"))

@branch_admin_bp.route("/branch-admin/sections", methods=["GET", "POST"])
def branch_admin_sections():
    if session.get("role") != "branch_admin":
        return redirect("/")

    branch_id = session.get("branch_id")
    if not branch_id:
        flash("No branch assigned.", "error")
        return redirect(url_for("auth.login"))

    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute(
        "SELECT id, name FROM grade_levels WHERE branch_id = %s ORDER BY display_order",
        (branch_id,)
    )
    grades = cursor.fetchall() or []

    cursor.execute("""
    SELECT year_id, label 
    FROM school_years 
    WHERE is_active = TRUE AND branch_id = %s 
    ORDER BY label DESC
""", (branch_id,))
    years = cursor.fetchall() or []

    if request.method == "POST":
        section_name = (request.form.get("section_name") or "").strip()
        grade_level_id_raw = request.form.get("grade_level_id")
        year_id_raw = request.form.get("year_id")

        try:
            capacity = int(request.form.get("capacity") or 50)
            if capacity < 1: capacity = 50
        except (TypeError, ValueError):
            capacity = 50

        try:
            grade_level_id = int(grade_level_id_raw)
        except (TypeError, ValueError):
            grade_level_id = None

        try:
            year_id = int(year_id_raw)
        except (TypeError, ValueError):
            year_id = None

        if section_name and grade_level_id and year_id:
            cursor.execute(
                "SELECT 1 FROM grade_levels WHERE id = %s AND branch_id = %s",
                (grade_level_id, branch_id)
            )
            if not cursor.fetchone():
                flash("Invalid grade level.", "error")
                return redirect(url_for("branch_admin.branch_admin_sections"))

            cursor.execute("""
                SELECT 1 FROM school_years 
                WHERE year_id = %s AND branch_id = %s
            """, (year_id, branch_id))
            if not cursor.fetchone():
                flash("Invalid school year selected.", "error")
                return redirect(url_for("branch_admin.branch_admin_sections"))

            try:
                cursor.execute("""
                    INSERT INTO sections (branch_id, year_id, section_name, grade_level_id, capacity)
                    VALUES (%s, %s, %s, %s, %s)
                """, (branch_id, year_id, section_name, grade_level_id, capacity))
                db.commit()
                flash("Section added.", "success")
            except Exception as e:
                db.rollback()
                flash(f"Could not add section: {str(e)}", "error")
        else:
            flash("Section name, grade level, and year are required.", "error")

        return redirect(url_for("branch_admin.branch_admin_sections"))

    cursor.execute("""
        SELECT s.*, g.name AS grade_level_name, y.label AS school_year_label
    FROM sections s
    LEFT JOIN grade_levels g ON s.grade_level_id = g.id
    LEFT JOIN school_years y 
        ON s.year_id = y.year_id AND y.branch_id = s.branch_id
    WHERE s.branch_id = %s AND y.is_active = TRUE
    ORDER BY y.label DESC, g.display_order, s.section_name
    """, (branch_id,))
    sections = cursor.fetchall() or []

    cursor.close()
    db.close()

    return render_template(
        "branch_admin_sections.html",
        sections=sections,
        grades=grades,
        years=years
    )

@branch_admin_bp.route("/branch-admin/sections/<int:section_id>/delete", methods=["POST"])
def branch_admin_section_delete(section_id):
    if session.get("role") != "branch_admin":
        return redirect("/")

    branch_id = session.get("branch_id")
    db = get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute(
            "DELETE FROM sections WHERE section_id = %s AND branch_id = %s",
            (section_id, branch_id)
        )
        db.commit()
        flash("Section deleted.", "success")
    except Exception as e:
        db.rollback()
        flash(f"Could not delete section: {str(e)}", "error")
    finally:
        cursor.close()
        db.close()

    return redirect(url_for("branch_admin.branch_admin_sections"))

@branch_admin_bp.route("/branch-admin/sections/<int:section_id>/edit", methods=["POST"])
def branch_admin_section_edit(section_id):
    if session.get("role") != "branch_admin":
        return redirect("/")

    branch_id = session.get("branch_id")
    section_name = (request.form.get("section_name") or "").strip()
    grade_level_id_raw = request.form.get("grade_level_id")
    
    try:
        capacity = int(request.form.get("capacity") or 50)
        if capacity < 1: capacity = 50
    except (TypeError, ValueError):
        capacity = 50
    
    try:
        grade_level_id = int(grade_level_id_raw)
    except (TypeError, ValueError):
        grade_level_id = None

    if not section_name or not grade_level_id:
        flash("Section name and grade level are required.", "error")
        return redirect(url_for("branch_admin.branch_admin_sections"))

    db = get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute("SELECT 1 FROM grade_levels WHERE id = %s AND branch_id = %s", (grade_level_id, branch_id))
        if not cursor.fetchone():
            flash("Invalid grade level.", "error")
            return redirect(url_for("branch_admin.branch_admin_sections"))

        cursor.execute("""
            UPDATE sections 
            SET section_name = %s, grade_level_id = %s, capacity = %s
            WHERE section_id = %s AND branch_id = %s
        """, (section_name, grade_level_id, capacity, section_id, branch_id))
        db.commit()
        flash("Section updated successfully.", "success")
    except Exception as e:
        db.rollback()
        flash(f"Failed to update section: {e}", "error")
    finally:
        cursor.close()
        db.close()

    return redirect(url_for("branch_admin.branch_admin_sections"))

@branch_admin_bp.route("/branch-admin/subjects", methods=["GET", "POST"])
def branch_admin_subjects():
    if session.get("role") != "branch_admin":
        return redirect("/")

    branch_id = session.get("branch_id")
    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute("""
        SELECT s.section_id, s.section_name, g.id AS grade_level_id, g.name AS grade_level_name
        FROM sections s
        INNER JOIN grade_levels g ON s.grade_level_id = g.id
        INNER JOIN school_years y ON s.year_id = y.year_id           
        WHERE s.branch_id = %s AND y.is_active = TRUE
        ORDER BY g.display_order, s.section_name
    """, (branch_id,))
    section_options = cursor.fetchall() or []

    if request.method == "POST":
        names = request.form.getlist("names")
        categories = request.form.getlist("categories")
        section_ids = request.form.getlist("section_ids")

        if not names or not section_ids:
            flash("At least one subject and one section are required.", "error")
            return redirect(url_for("branch_admin.branch_admin_subjects"))

        try:
            for i in range(len(names)):
                name = names[i].strip()
                if not name: continue
                deped_category = categories[i] if i < len(categories) else "language"

                cursor.execute("""
                    INSERT INTO subjects (name, deped_category)
                    VALUES (%s, %s)
                    ON CONFLICT (name) DO UPDATE SET deped_category = EXCLUDED.deped_category
                    RETURNING subject_id
                """, (name, deped_category))
                res = cursor.fetchone()
                subject_id = res["subject_id"] if res else None
                if not subject_id:
                    cursor.execute("SELECT subject_id FROM subjects WHERE name=%s", (name,))
                    subject_id = cursor.fetchone()["subject_id"]

                for sid_raw in section_ids:
                    sid = int(sid_raw)
                    cursor.execute("SELECT 1 FROM sections WHERE section_id=%s AND branch_id=%s", (sid, branch_id))
                    if not cursor.fetchone(): continue

                    cursor.execute("""
                        INSERT INTO section_teachers (section_id, teacher_id, subject_id, year_id)
                        SELECT %s, NULL, %s, year_id FROM sections WHERE section_id = %s
                        ON CONFLICT DO NOTHING
                    """, (sid, subject_id, sid))

            db.commit()
            flash("Curriculum deployed!", "success")
        except Exception as e:
            db.rollback()
            flash(f"Error: {str(e)}", "error")

        return redirect(url_for("branch_admin.branch_admin_subjects"))

    section_id_filter = request.args.get("section_id")
    # Default to first section if no filter is selected
    if not section_id_filter and section_options:
        section_id_filter = str(section_options[0]['section_id'])

    query = """
        SELECT st.subject_id, sub.name, sub.deped_category, s.section_id, s.section_name, g.name AS grade_level_name, st.is_archived
        FROM section_teachers st
        INNER JOIN subjects sub ON st.subject_id = sub.subject_id
        INNER JOIN sections s ON st.section_id = s.section_id
        INNER JOIN grade_levels g ON s.grade_level_id = g.id
        INNER JOIN school_years y ON s.year_id = y.year_id           
        WHERE s.branch_id = %s AND y.is_active = TRUE
    """
    params = [branch_id]
    if section_id_filter:
        query += " AND s.section_id = %s "
        params.append(section_id_filter)
    query += " ORDER BY g.display_order, s.section_name, sub.name"
    
    cursor.execute(query, tuple(params))
    assignments = cursor.fetchall() or []

    cursor.close(); db.close()

    return render_template(
        "branch_admin_subjects.html",
        assignments=assignments,
        section_options=section_options,
        selected_section_id=section_id_filter
    )

@branch_admin_bp.route("/branch-admin/subjects/<int:subject_id>/<int:section_id>/toggle-archive", methods=["POST"])
def branch_admin_subject_toggle_archive(subject_id, section_id):
    if session.get("role") != "branch_admin":
        return redirect("/")
    branch_id = session.get("branch_id")
    db = get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute("SELECT 1 FROM sections WHERE section_id=%s AND branch_id=%s", (section_id, branch_id))
        if cursor.fetchone():
            cursor.execute("""
                UPDATE section_teachers SET is_archived = NOT is_archived 
                WHERE subject_id = %s AND section_id = %s
                RETURNING is_archived
            """, (subject_id, section_id))
            db.commit()
            flash("Subject status updated.", "success")
    except Exception as e:
        db.rollback()
        flash(f"Error: {str(e)}", "error")
    finally:
        cursor.close(); db.close()
    return redirect(url_for("branch_admin.branch_admin_subjects", section_id=section_id))

@branch_admin_bp.route("/branch-admin/subjects/<int:subject_id>/delete", methods=["POST"])
def branch_admin_subject_delete(subject_id):
    if session.get("role") != "branch_admin":
        return redirect("/")
    branch_id = session.get("branch_id")
    db = get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute("""
            DELETE FROM section_teachers st
            USING sections s
            WHERE st.section_id = s.section_id AND s.branch_id = %s AND st.subject_id = %s
        """, (branch_id, subject_id))
        db.commit()
        flash("Subject removed.", "success")
    except Exception as e:
        db.rollback()
        flash(f"Error: {str(e)}", "error")
    finally:
        cursor.close(); db.close()
    return redirect(url_for("branch_admin.branch_admin_subjects"))

@branch_admin_bp.route("/branch-admin/subjects/<int:subject_id>/edit", methods=["POST"])
def branch_admin_subject_edit(subject_id):
    if session.get("role") != "branch_admin":
        return redirect("/")
    branch_id = session.get("branch_id")
    new_name = (request.form.get("name") or "").strip()
    section_id = request.form.get("section_id")
    deped_category = request.form.get("deped_category", "language")

    if not new_name or not section_id:
        flash("Required fields missing.", "error")
        return redirect(url_for("branch_admin.branch_admin_subjects"))

    db = get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute("SELECT 1 FROM sections WHERE section_id=%s AND branch_id=%s", (section_id, branch_id))
        if not cursor.fetchone():
            flash("Invalid section.", "error")
            return redirect(url_for("branch_admin.branch_admin_subjects"))

        cursor.execute("UPDATE subjects SET name = %s, deped_category = %s WHERE subject_id = %s", (new_name, deped_category, subject_id))
        db.commit()
        flash("Subject updated.", "success")
    except Exception as e:
        db.rollback()
        flash(f"Error: {str(e)}", "error")
    finally:
        cursor.close(); db.close()
    return redirect(url_for("branch_admin.branch_admin_subjects"))

@branch_admin_bp.route("/branch-admin/assign-teachers", methods=["GET", "POST"])
def branch_admin_assign_teachers():
    if session.get("role") != "branch_admin":
        return redirect("/")

    branch_id = session.get("branch_id")
    grade_filter = (request.args.get("grade") or "").strip()

    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        cursor.execute("SELECT year_id FROM school_years WHERE branch_id = %s AND is_active = TRUE LIMIT 1", (branch_id,))
        active_year = cursor.fetchone()
        active_year_id = active_year["year_id"] if active_year else None
        if not active_year_id:
            flash("No active school year found.", "error")
            return redirect(url_for("branch_admin.dashboard"))

        cursor.execute("""
            SELECT DISTINCT g.id, g.name, g.display_order
            FROM sections s
            JOIN grade_levels g ON s.grade_level_id = g.id
            JOIN school_years y ON s.year_id = y.year_id
            WHERE s.branch_id = %s AND y.is_active = TRUE
            ORDER BY g.display_order
        """, (branch_id,))
        grade_options = cursor.fetchall() or []
        
        if not grade_filter and grade_options:
            grade_filter = str(grade_options[0]['id'])

        if request.method == "POST":
            section_id = int(request.form.get("section_id"))
            subject_id = int(request.form.get("subject_id"))
            teacher_id = int(request.form.get("teacher_id")) if request.form.get("teacher_id") else None

            cursor.execute("SELECT 1 FROM sections s JOIN school_years y ON y.year_id = s.year_id WHERE s.section_id=%s AND s.branch_id=%s AND y.is_active = TRUE", (section_id, branch_id))
            if not cursor.fetchone():
                flash("Invalid section.", "error")
                return redirect(url_for("branch_admin.branch_admin_assign_teachers"))

            cursor.execute("UPDATE section_teachers SET teacher_id = %s WHERE section_id = %s AND subject_id = %s AND year_id = %s", (teacher_id, section_id, subject_id, active_year_id))
            db.commit()
            flash("Teacher assigned successfully!", "success")
            return redirect(url_for("branch_admin.branch_admin_assign_teachers", grade=grade_filter))

        cursor.execute(
            """SELECT user_id, username, full_name FROM users
               WHERE branch_id = %s AND role = 'teacher' AND COALESCE(is_archived, FALSE) = FALSE
               ORDER BY full_name""",
            (branch_id,),
        )
        teachers = cursor.fetchall() or []

        base_query = """
            SELECT st.id AS section_teacher_id, st.section_id, st.subject_id, st.teacher_id, s.section_name, g.name AS grade_level_name, sub.name AS subject_name, u.full_name AS teacher_full_name
            FROM section_teachers st
            JOIN sections s ON st.section_id = s.section_id
            JOIN grade_levels g ON s.grade_level_id = g.id
            JOIN subjects sub ON st.subject_id = sub.subject_id
            LEFT JOIN users u ON st.teacher_id = u.user_id
            JOIN school_years y ON s.year_id = y.year_id
            WHERE s.branch_id = %s AND y.is_active = TRUE
        """
        params = [branch_id]
        if grade_filter:
            base_query += " AND g.id = %s"
            params.append(grade_filter)
        base_query += " ORDER BY g.display_order, s.section_name, sub.name"

        cursor.execute(base_query, tuple(params))
        assignments = cursor.fetchall() or []

        cursor.execute("SELECT s.section_id, CONCAT(g.name, ' - ', s.section_name) AS section_display, g.id AS grade_level_id FROM sections s JOIN grade_levels g ON s.grade_level_id = g.id JOIN school_years y ON s.year_id = y.year_id WHERE s.branch_id = %s AND y.is_active = TRUE ORDER BY g.display_order, s.section_name", (branch_id,))
        section_options = cursor.fetchall() or []

    except Exception as e:
        db.rollback()
        flash(f"Error: {str(e)}", "error")
        teachers, assignments, grade_options, section_options = [], [], [], []
    finally:
        cursor.close(); db.close()

    return render_template(
        "branch_admin_assign_teachers.html",
        teachers=teachers,
        assignments=assignments,
        grade_options=grade_options,
        grade_filter=grade_filter,
        section_options=section_options,
    )

@branch_admin_bp.route("/branch-admin/api/get-all-subjects/<int:teacher_id>", methods=["GET"])
def branch_admin_api_get_all_subjects(teacher_id):
    if session.get("role") != "branch_admin":
        return {"error": "Unauthorized"}, 403
    branch_id = session.get("branch_id")
    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cursor.execute(
            """SELECT 1 FROM users
               WHERE user_id=%s AND branch_id=%s AND role='teacher'
                 AND COALESCE(is_archived, FALSE) = FALSE""",
            (teacher_id, branch_id),
        )
        if not cursor.fetchone():
            return {"error": "Teacher not found"}, 404

        # ── Subject slots (for Subject Loads tab) ──
        query = """
            SELECT st.id AS assignment_id, st.subject_id, st.section_id, st.teacher_id,
                   sub.name AS subject_name, s.section_name,
                   g.name AS grade_level_name,
                   (st.teacher_id = %s) AS is_assigned_to_this_teacher,
                   (st.teacher_id IS NOT NULL AND st.teacher_id != %s) AS is_currently_assigned,
                   u.full_name AS current_teacher_name
            FROM section_teachers st
            JOIN sections s ON st.section_id = s.section_id
            JOIN grade_levels g ON s.grade_level_id = g.id
            JOIN subjects sub ON st.subject_id = sub.subject_id
            JOIN school_years y ON s.year_id = y.year_id
            LEFT JOIN users u ON st.teacher_id = u.user_id
            WHERE s.branch_id = %s AND y.is_active = TRUE
            ORDER BY g.display_order, s.section_name, sub.name
        """
        cursor.execute(query, (teacher_id, teacher_id, branch_id))
        subjects = cursor.fetchall() or []

        # ── Sections list (for Advisory Class tab) ──
        cursor.execute("""
            SELECT s.section_id, s.section_name, g.name AS grade_level_name,
                   s.teacher_id AS adviser_id,
                   adv.full_name AS adviser_name,
                   (s.teacher_id = %s) AS is_my_advisory
            FROM sections s
            JOIN grade_levels g ON s.grade_level_id = g.id
            JOIN school_years y ON s.year_id = y.year_id
            LEFT JOIN users adv ON s.teacher_id = adv.user_id
            WHERE s.branch_id = %s AND y.is_active = TRUE
            ORDER BY g.display_order, s.section_name
        """, (teacher_id, branch_id))
        sections = cursor.fetchall() or []

        return {
            "success": True,
            "subjects": [dict(row) for row in subjects],
            "sections": [dict(row) for row in sections],
        }
    except Exception as e:
        return {"error": str(e)}, 500
    finally:
        cursor.close(); db.close()

@branch_admin_bp.route("/branch-admin/assign-teachers-bulk", methods=["POST"])
def branch_admin_assign_teachers_bulk():
    if session.get("role") != "branch_admin":
        return {"error": "Unauthorized"}, 403
    branch_id = session.get("branch_id")
    data = request.get_json()
    teacher_id = data.get("teacher_id")
    assignment_ids = data.get("assignment_ids", [])
    advisory_section_id = data.get("advisory_section_id")  # can be None

    if not teacher_id:
        return {"success": False, "message": "Missing teacher ID"}, 400

    db = get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute(
            """SELECT 1 FROM users WHERE user_id = %s AND branch_id = %s AND role = 'teacher'
               AND COALESCE(is_archived, FALSE) = FALSE""",
            (teacher_id, branch_id),
        )
        if not cursor.fetchone():
            return {"success": False, "message": "That teacher is not available (archived or missing)."}, 400

        # ── Advisory assignment ──
        # First clear this teacher from any section they currently advise
        cursor.execute(
            """UPDATE sections SET teacher_id = NULL
               WHERE teacher_id = %s AND branch_id = %s""",
            (teacher_id, branch_id),
        )
        # Then assign new advisory section if one was picked
        if advisory_section_id:
            cursor.execute(
                """UPDATE sections SET teacher_id = %s
                   WHERE section_id = %s AND branch_id = %s""",
                (teacher_id, advisory_section_id, branch_id),
            )

        # ── Subject assignments ──
        if assignment_ids:
            cursor.execute(
                """UPDATE section_teachers SET teacher_id = %s
                   WHERE id = ANY(%s)
                     AND section_id IN (SELECT section_id FROM sections WHERE branch_id = %s)""",
                (teacher_id, assignment_ids, branch_id),
            )

        db.commit()
        return {"success": True}
    except Exception as e:
        db.rollback()
        return {"success": False, "message": str(e)}, 500
    finally:
        cursor.close(); db.close()

@branch_admin_bp.route("/branch-admin/api/remove-teacher-assignment", methods=["POST"])
def branch_admin_remove_teacher_assignment():
    if session.get("role") != "branch_admin":
        return {"success": False, "message": "Unauthorized"}, 403
    branch_id = session.get("branch_id")
    data = request.get_json()
    section_teacher_id = data.get("section_teacher_id")

    if not section_teacher_id:
        return {"success": False, "message": "Missing ID"}, 400

    db = get_db_connection()
    cursor = db.cursor()
    try:
        # Verify it belongs to the branch
        cursor.execute("""
            UPDATE section_teachers 
            SET teacher_id = NULL 
            WHERE id = %s 
              AND section_id IN (SELECT section_id FROM sections WHERE branch_id = %s)
        """, (section_teacher_id, branch_id))
        db.commit()
        return {"success": True}
    except Exception as e:
        db.rollback()
        return {"success": False, "message": str(e)}, 500
    finally:
        cursor.close(); db.close()


# ══════════════════════════════════════════════════════
# MANAGE TEACHERS — Branch Admin Module
# ══════════════════════════════════════════════════════

def _ensure_teacher_tables(cursor):
    cursor.execute("""
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS is_archived BOOLEAN DEFAULT FALSE
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS teacher_grade_levels (
            id             SERIAL PRIMARY KEY,
            teacher_id     INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
            grade_level_id INTEGER NOT NULL REFERENCES grade_levels(id) ON DELETE CASCADE,
            UNIQUE(teacher_id, grade_level_id)
        )
    """)



@branch_admin_bp.route("/branch-admin/assign-students", methods=["GET", "POST"])
def branch_admin_assign_students():
    if session.get("role") != "branch_admin":
        return redirect("/")

    branch_id = session.get("branch_id")
    grade_filter = (request.args.get("grade") or "").strip()

    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        cursor.execute("SELECT year_id FROM school_years WHERE branch_id = %s AND is_active = TRUE LIMIT 1", (branch_id,))
        active_year = cursor.fetchone()
        active_year_id = active_year["year_id"] if active_year else None
        if not active_year_id:
            flash("No active school year found.", "error")
            return redirect(url_for("branch_admin.dashboard"))

        cursor.execute("SELECT id, name, display_order FROM grade_levels WHERE branch_id = %s ORDER BY display_order", (branch_id,))
        grade_options = cursor.fetchall() or []
        
        if not grade_filter and grade_options:
            grade_filter = str(grade_options[0]['id'])

        if request.method == "POST":
            enrollment_id = int(request.form.get("enrollment_id"))
            section_id = int(request.form.get("section_id")) if request.form.get("section_id") else None

            cursor.execute("SELECT 1 FROM enrollments WHERE enrollment_id=%s AND branch_id=%s AND year_id=%s", (enrollment_id, branch_id, active_year_id))
            if not cursor.fetchone():
                flash("Enrollment not found.", "error")
                return redirect(url_for("branch_admin.branch_admin_assign_students", grade=grade_filter))

            if section_id:
                cursor.execute("""
                    SELECT capacity, (SELECT COUNT(*) FROM enrollments WHERE section_id = s.section_id AND status IN ('approved', 'enrolled', 'open_for_enrollment', 'completed')) AS current_count
                    FROM sections s JOIN school_years y ON s.year_id = y.year_id
                    WHERE s.section_id=%s AND s.branch_id=%s AND y.is_active = TRUE
                """, (section_id, branch_id))
                sec_info = cursor.fetchone()
                if not sec_info:
                    flash("Section not found.", "error")
                    return redirect(url_for("branch_admin.branch_admin_assign_students", grade=grade_filter))
                if sec_info['current_count'] >= sec_info['capacity']:
                    flash("Section is full.", "error")
                    return redirect(url_for("branch_admin.branch_admin_assign_students", grade=grade_filter))

            cursor.execute("UPDATE enrollments SET section_id=%s, status = CASE WHEN %s IS NOT NULL AND status = 'approved' THEN 'enrolled' ELSE status END WHERE enrollment_id=%s AND year_id=%s", (section_id, section_id, enrollment_id, active_year_id))
            db.commit()
            flash("Student section updated!", "success")
            return redirect(url_for("branch_admin.branch_admin_assign_students", grade=grade_filter))

        cursor.execute("SELECT s.section_id, s.section_name, g.name AS grade_level_name, g.id AS grade_level_id, s.capacity, (SELECT COUNT(*) FROM enrollments e2 WHERE e2.section_id = s.section_id AND e2.status IN ('approved', 'enrolled', 'open_for_enrollment', 'completed')) AS current_count FROM sections s JOIN grade_levels g ON s.grade_level_id = g.id JOIN school_years y ON s.year_id = y.year_id WHERE s.branch_id = %s AND y.is_active = TRUE ORDER BY g.display_order, s.section_name", (branch_id,))
        all_sections = cursor.fetchall() or []
        filtered_sections = [s for s in all_sections if str(s['grade_level_id']) == grade_filter]

        grade_name = ""
        if grade_filter:
            cursor.execute("SELECT name FROM grade_levels WHERE id = %s AND branch_id = %s", (grade_filter, branch_id))
            grade_row = cursor.fetchone()
            grade_name = grade_row['name'] if grade_row else ""

        cursor.execute("""
            SELECT e.enrollment_id, e.student_first_name,
    e.student_middle_name,
    e.student_last_name, e.grade_level, e.branch_enrollment_no, e.section_id, s.section_name
            FROM enrollments e LEFT JOIN sections s ON e.section_id = s.section_id
            WHERE e.branch_id = %s AND e.year_id = %s AND e.status IN ('approved', 'enrolled', 'open_for_enrollment', 'completed') AND (e.grade_level ILIKE %s OR e.grade_level ILIKE %s)
            ORDER BY e.student_last_name,
    e.student_first_name,
    e.student_middle_name
        """, (branch_id, active_year_id, grade_name, grade_name.replace("Grade ", "")))
        students = cursor.fetchall() or []
        for s in students:
            s["student_name"] = " ".join(filter(None, [
                s.get("student_first_name"),
                s.get("student_middle_name"),
                s.get("student_last_name"),
            ]))

    except Exception as e:
        db.rollback()
        flash(f"Error: {str(e)}", "error")
        grade_options, filtered_sections, students = [], [], []
    finally:
        cursor.close(); db.close()

    return render_template(
        "branch_admin_assign_students.html",
        grade_options=grade_options,
        sections=filtered_sections,
        students=students,
        grade_filter=grade_filter
    )


@branch_admin_bp.route("/branch-admin/manage-teachers", methods=["GET", "POST"])
def branch_admin_manage_teachers():
    if session.get("role") != "branch_admin":
        return redirect("/")

    branch_id     = session.get("branch_id")
    created_user  = None
    filter_search = request.args.get("search", "").strip()

    db     = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:

        cursor.execute(
            "SELECT id, name FROM grade_levels WHERE branch_id = %s ORDER BY display_order",
            (branch_id,)
        )
        grades = cursor.fetchall() or []

        if request.method == "POST":
            first_name     = (request.form.get("first_name")   or "").strip()
            middle_name    = (request.form.get("middle_name")  or "").strip()
            last_name      = (request.form.get("last_name")    or "").strip()
            gender         = (request.form.get("gender")       or "").strip().lower()
            user_email     = (request.form.get("email")        or "").strip()

            if not first_name or not last_name:
                flash("Please enter the teacher's first name and last name.", "error")
                return redirect("/branch-admin/manage-teachers")
            if gender not in ("male", "female"):
                flash("Please choose male or female.", "error")
                return redirect("/branch-admin/manage-teachers")
            if not user_email:
                flash("Please enter an email address.", "error")
                return redirect("/branch-admin/manage-teachers")

            cursor.execute("SELECT branch_code FROM branches WHERE branch_id=%s", (branch_id,))
            b_row = cursor.fetchone()
            branch_code = ((b_row['branch_code'] or "") if b_row else "").strip().upper()
            if not branch_code:
                flash("This branch has no short code yet. Ask admin to set branch code first.", "error")
                return redirect("/branch-admin/manage-teachers")

            full_name = f"{first_name} {middle_name} {last_name}".strip().replace("  ", " ")
            base_username = f"{branch_code}_Teacher"

            username = base_username
            suffix_counter = 2
            while True:
                cursor.execute("SELECT 1 FROM users WHERE username=%s", (username,))
                if not cursor.fetchone():
                    break
                username = f"{base_username}_{suffix_counter}"
                suffix_counter += 1

            temp_password   = generate_password()
            hashed_password = generate_password_hash(temp_password)

            cursor.execute("""
                INSERT INTO users
                    (branch_id, username, password, role, require_password_change,
                     first_name, middle_name, last_name, full_name, gender, email)
                VALUES (%s, %s, %s, 'teacher', TRUE, %s, %s, %s, %s, %s, %s)
                RETURNING user_id
            """, (branch_id, username, hashed_password,
                  first_name, middle_name or None, last_name, full_name, gender, user_email))
            new_user_id = cursor.fetchone()['user_id']

            db.commit()
            created_user = {"username": username, "password": temp_password}

            if user_email:
                subject_line = "Your Teacher Account — Liceo LMS"
                body = f"""Hello {full_name},

Your teacher account has been created by the Registrar.

Username: {username}
Temporary Password: {temp_password}
Login URL: https://www.liceo-lms.com/

Please log in and change your password immediately.

-- The Liceo LMS Team"""
                try:
                    send_email(user_email, subject_line, body)
                    flash(f"Account created. Login details were emailed to {user_email}.", "success")
                except Exception as mail_err:
                    flash(
                        f"Account created, but the email could not be sent ({mail_err}). "
                        "Copy the username and password from the green box below.",
                        "warning",
                    )
            else:
                flash("Account created.", "success")

        query = """
            SELECT
                u.user_id, u.username, u.first_name, u.middle_name, u.last_name, u.full_name, u.gender, u.email,
                COALESCE(u.status, 'active') AS status,
                adv_sec.section_name AS advisory_section,
                adv_grade.name AS advisory_grade,
                (
                    SELECT STRING_AGG(DISTINCT g.name || ' - ' || s.section_name || ' (' || sub.name || ')', ', ')
                    FROM section_teachers st
                    JOIN sections s ON st.section_id = s.section_id
                    JOIN grade_levels g ON s.grade_level_id = g.id
                    JOIN subjects sub ON st.subject_id = sub.subject_id
                    WHERE st.teacher_id = u.user_id
                ) AS assigned_sections
            FROM users u
            LEFT JOIN sections adv_sec ON adv_sec.teacher_id = u.user_id AND adv_sec.branch_id = u.branch_id
            LEFT JOIN grade_levels adv_grade ON adv_sec.grade_level_id = adv_grade.id
            WHERE u.branch_id = %s AND u.role = 'teacher' AND COALESCE(u.is_archived, FALSE) = FALSE
        """
        params = [branch_id]
        if filter_search:
            query += " AND (u.full_name ILIKE %s OR u.username ILIKE %s)"
            params.extend([f"%{filter_search}%", f"%{filter_search}%"])
        
        query += " ORDER BY u.full_name"
        cursor.execute(query, params)
        teachers = cursor.fetchall() or []

        cursor.execute("""
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE COALESCE(status,'active') = 'active') AS active_count,
                COUNT(*) FILTER (
                    WHERE EXISTS (SELECT 1 FROM sections s WHERE s.teacher_id = users.user_id)
                ) AS advisory_count,
                COUNT(*) FILTER (
                    WHERE NOT EXISTS (SELECT 1 FROM sections s WHERE s.teacher_id = users.user_id)
                      AND EXISTS (SELECT 1 FROM section_teachers st WHERE st.teacher_id = users.user_id)
                ) AS subject_count
            FROM users WHERE branch_id = %s AND role = 'teacher'
              AND COALESCE(is_archived, FALSE) = FALSE
        """, (branch_id,))
        stats = cursor.fetchone()

    except Exception as e:
        db.rollback()
        flash(f"Something went wrong: {str(e)}", "error")
        teachers, grades, stats = [], [], None
    finally:
        cursor.close()
        db.close()

    return render_template(
        "branch_admin_manage_teachers.html",
        teachers=teachers,
        grades=grades,
        stats=stats,
        filter_search=filter_search,
        created_user=created_user,
    )


@branch_admin_bp.route("/branch-admin/manage-teachers/<int:user_id>/edit", methods=["POST"])
def branch_admin_edit_teacher(user_id):
    if session.get("role") != "branch_admin":
        return redirect("/")
    first_name  = (request.form.get("first_name") or "").strip()
    middle_name = (request.form.get("middle_name") or "").strip()
    last_name   = (request.form.get("last_name") or "").strip()
    gender = (request.form.get("gender") or "").strip().lower()
    user_email = (request.form.get("email") or "").strip()
    if not first_name or not last_name:
        flash("Please enter the teacher's first name and last name.", "error")
        return redirect("/branch-admin/manage-teachers")
    if gender not in ("male", "female"):
        flash("Please choose male or female.", "error")
        return redirect("/branch-admin/manage-teachers")
    if not user_email:
        flash("Please enter an email address.", "error")
        return redirect("/branch-admin/manage-teachers")
    
    full_name = f"{first_name} {middle_name} {last_name}".strip().replace("  ", " ")

    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cursor.execute(
            """SELECT 1 FROM users WHERE user_id = %s AND branch_id = %s AND role = 'teacher'
               AND COALESCE(is_archived, FALSE) = FALSE""",
            (user_id, branch_id),
        )
        if not cursor.fetchone():
            flash("Teacher not found.", "error")
            return redirect("/branch-admin/manage-teachers")

        cursor.execute(
            """
            UPDATE users SET
                first_name = %s, middle_name = %s, last_name = %s, full_name = %s, email = %s, gender = %s
            WHERE user_id = %s AND branch_id = %s AND role = 'teacher'
              AND COALESCE(is_archived, FALSE) = FALSE
            """,
            (
                first_name,
                middle_name or None,
                last_name,
                full_name,
                user_email,
                gender,
                user_id,
                session.get("branch_id"),
            ),
        )

        db.commit()

        db.commit()
        flash("Teacher details saved.", "success")
    except Exception as e:
        db.rollback()
        flash(f"Could not save changes: {str(e)}", "error")
    finally:
        cursor.close()
        db.close()
    return redirect("/branch-admin/manage-teachers")


@branch_admin_bp.route("/branch-admin/manage-teachers/<int:user_id>/toggle", methods=["POST"])
def branch_admin_toggle_teacher(user_id):
    if session.get("role") != "branch_admin":
        return redirect("/")
    db = get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute("""
            UPDATE users
            SET status = CASE WHEN COALESCE(status,'active') = 'active' THEN 'inactive' ELSE 'active' END
            WHERE user_id = %s AND branch_id = %s AND role = 'teacher'
              AND COALESCE(is_archived, FALSE) = FALSE
        """, (user_id, session.get("branch_id")))
        db.commit()
        flash("Login status updated.", "success")
    except Exception as e:
        db.rollback()
        flash(f"Failed: {str(e)}", "error")
    finally:
        cursor.close(); db.close()
    return redirect(request.referrer or "/branch-admin/manage-teachers")


@branch_admin_bp.route("/branch-admin/manage-teachers/<int:user_id>/archive", methods=["POST"])
def branch_admin_archive_teacher(user_id):
    """Soft-hide teacher from the main list and free section slots; login is turned off."""
    if session.get("role") != "branch_admin":
        return redirect("/")
    branch_id = session.get("branch_id")
    db = get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute(
            """UPDATE users SET is_archived = TRUE, status = 'inactive'
               WHERE user_id = %s AND branch_id = %s AND role = 'teacher'
                 AND COALESCE(is_archived, FALSE) = FALSE""",
            (user_id, branch_id),
        )
        if cursor.rowcount == 0:
            flash("Teacher not found or already archived.", "error")
        else:
            cursor.execute(
                """
                UPDATE section_teachers st
                SET teacher_id = NULL
                FROM sections s
                WHERE st.section_id = s.section_id
                  AND st.teacher_id = %s AND s.branch_id = %s
                """,
                (user_id, branch_id),
            )
            flash("Teacher archived. You can permanently delete them from the Archive page.", "success")
        db.commit()
    except Exception as e:
        db.rollback()
        flash(f"Could not archive: {str(e)}", "error")
    finally:
        cursor.close()
        db.close()
    return redirect(request.referrer or "/branch-admin/manage-teachers")


@branch_admin_bp.route("/branch-admin/manage-teachers/archive", methods=["GET"])
def branch_admin_archived_teachers():
    if session.get("role") != "branch_admin":
        return redirect("/")
    branch_id = session.get("branch_id")
    filter_search = request.args.get("search", "").strip()
    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    teachers = []
    try:
        _ensure_teacher_tables(cursor)
        db.commit()
        query = """
            SELECT
                u.user_id, u.username, u.full_name, u.gender, u.email,
                u.grade_level_id,
                COALESCE(u.status, 'active') AS status,
                COALESCE(u.teacher_type, 'advisory') AS teacher_type,
                COALESCE(g.name, '') AS primary_grade,
                u.specialization_subject,
                u.department
            FROM users u
            LEFT JOIN grade_levels g ON u.grade_level_id = g.id
            WHERE u.branch_id = %s AND u.role = 'teacher' AND COALESCE(u.is_archived, FALSE) = TRUE
        """
        params = [branch_id]
        if filter_search:
            query += " AND (u.full_name ILIKE %s OR u.username ILIKE %s)"
            params.extend([f"%{filter_search}%", f"%{filter_search}%"])
        query += " ORDER BY u.full_name"
        cursor.execute(query, params)
        teachers = cursor.fetchall() or []
    except Exception as e:
        db.rollback()
        flash(f"Something went wrong: {str(e)}", "error")
    finally:
        cursor.close()
        db.close()
    return render_template(
        "branch_admin_archived_teachers.html",
        teachers=teachers,
        filter_search=filter_search,
    )


@branch_admin_bp.route("/branch-admin/manage-teachers/archive/<int:user_id>/unarchive", methods=["POST"])
def branch_admin_unarchive_teacher(user_id):
    """Restore teacher from archive back to main list."""
    if session.get("role") != "branch_admin":
        return redirect("/")
    branch_id = session.get("branch_id")
    db = get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute(
            """UPDATE users SET is_archived = FALSE, status = 'active'
               WHERE user_id = %s AND branch_id = %s AND role = 'teacher'
                 AND COALESCE(is_archived, FALSE) = TRUE""",
            (user_id, branch_id),
        )
        if cursor.rowcount == 0:
            flash("Teacher not found or not archived.", "error")
        else:
            flash("Teacher restored. They are now back in the main list.", "success")
        db.commit()
    except Exception as e:
        db.rollback()
        flash(f"Could not restore: {str(e)}", "error")
    finally:
        cursor.close()
        db.close()
    return redirect("/branch-admin/manage-teachers/archive")


@branch_admin_bp.route("/branch-admin/manage-teachers/archive/<int:user_id>/delete", methods=["POST"])
def branch_admin_delete_archived_teacher(user_id):
    """Permanent delete — only allowed for archived teacher accounts."""
    if session.get("role") != "branch_admin":
        return redirect("/")
    branch_id = session.get("branch_id")
    db = get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute(
            """SELECT 1 FROM users WHERE user_id = %s AND branch_id = %s AND role = 'teacher'
               AND COALESCE(is_archived, FALSE) = TRUE""",
            (user_id, branch_id),
        )
        if not cursor.fetchone():
            flash("Only archived teachers can be deleted here.", "error")
            return redirect("/branch-admin/manage-teachers/archive")
        cursor.execute("DELETE FROM teacher_grade_levels WHERE teacher_id = %s", (user_id,))
        cursor.execute(
            "DELETE FROM users WHERE user_id = %s AND branch_id = %s AND role = 'teacher' AND COALESCE(is_archived, FALSE) = TRUE",
            (user_id, branch_id),
        )
        db.commit()
        flash("Teacher permanently removed.", "success")
    except Exception as e:
        db.rollback()
        flash(f"Failed to delete: {str(e)}", "error")
    finally:
        cursor.close()
        db.close()
    return redirect("/branch-admin/manage-teachers/archive")


@branch_admin_bp.route("/branch-admin/manage-teachers/<int:user_id>/delete", methods=["POST"])
def branch_admin_delete_teacher_deprecated(user_id):
    """Old URL: permanent delete now lives under /manage-teachers/archive/…/delete."""
    if session.get("role") != "branch_admin":
        return redirect("/")
    flash("To remove a teacher permanently, open Teachers → Archive, then use Delete there.", "info")
    return redirect("/branch-admin/manage-teachers")
