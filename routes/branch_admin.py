from flask import Blueprint, render_template, request, session, redirect, flash, url_for
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
    'Pre-Elementary Boys Set': ['Kinder', 'Grade 1', 'Grade 2', 'Grade 3'],
    'Pre-Elementary Girls Set': ['Kinder', 'Grade 1', 'Grade 2', 'Grade 3', 'Grade 4', 'Grade 5', 'Grade 6'],
    'Elementary G4-6 Boys Set': ['Grade 4', 'Grade 5', 'Grade 6'],
    'JHS Boys Uniform Set': ['Grade 7', 'Grade 8', 'Grade 9', 'Grade 10'],
    'JHS Girls Uniform Set': ['Grade 7', 'Grade 8', 'Grade 9', 'Grade 10'],
    'SHS Boys Uniform Set': ['Grade 11', 'Grade 12'],
    'SHS Girls Uniform Set': ['Grade 11', 'Grade 12'],
    'PE Uniform': ['Kinder'] + [f'Grade {i}' for i in range(1, 13)],
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

def get_grade_order(grade_level):
    if not grade_level:
        return 999
    grade_str = str(grade_level).strip().lower()
    if 'nursery' in grade_str:
        return -1
    if 'kinder' in grade_str or 'pre' in grade_str:
        return 0
    match = re.search(r'(\d+)', grade_str)
    if match:
        return int(match.group(1))
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
    announcements_list = []
    
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

        # ✅ Load announcements for THIS branch only
        cursor.execute("""
            SELECT announcement_id AS id, title, message, created_at, is_active,
                   image_url, branch_id
            FROM announcements
            WHERE branch_id = %s
            ORDER BY created_at DESC
        """, (session.get("branch_id"),))
        announcements_list = cursor.fetchall() or []
        
        # ✅ Fetch Metrics
        b_id = session.get("branch_id")
        
        cursor.execute("SELECT COUNT(*) FROM enrollments WHERE status='approved' AND branch_id=%s", (b_id,))
        metrics['total_enrolled'] = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) FROM enrollments WHERE status='pending' AND branch_id=%s", (b_id,))
        metrics['pending_reservations'] = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE role='teacher' AND COALESCE(status, 'active')='active' AND branch_id=%s", (b_id,))
        metrics['total_teachers'] = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE role IN ('registrar', 'cashier', 'librarian') AND COALESCE(status, 'active')='active' AND branch_id=%s", (b_id,))
        metrics['total_staff'] = cursor.fetchone()['count']
        
        # Chart Data: Enrollment by Grade
        cursor.execute("""
            SELECT grade_level, COUNT(*) 
            FROM enrollments 
            WHERE status='approved' AND branch_id=%s 
            GROUP BY grade_level
            ORDER BY COUNT(*) DESC
        """, (b_id,))
        metrics['grade_stats'] = cursor.fetchall() or []
        
        # Chart Data: Status Breakdown
        cursor.execute("""
            SELECT status, COUNT(*) 
            FROM enrollments 
            WHERE branch_id=%s 
            GROUP BY status
        """, (b_id,))
        metrics['status_stats'] = cursor.fetchall() or []
        
    except Exception as e:
        print(f"Error loading dashboard metrics: {e}")
    finally:
        cursor.close()
        db.close()

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
                        # Upload to Cloudinary (prod) or local (dev)
                        image_url = upload_announcement_photo(photo)
                    else:
                        flash("Photo must be PNG, JPG, GIF, or WEBP.", "warning")

                db = get_db_connection()
                cur = db.cursor()
                try:
                    cur.execute("""
                        INSERT INTO announcements (title, message, is_active, image_url, branch_id)
                        VALUES (%s, %s, TRUE, %s, %s)
                    """, (title, message, image_url, session.get("branch_id")))
                    db.commit()
                    flash("Announcement added to homepage!", "success")
                except Exception as e:
                    db.rollback()
                    flash(f"Could not add announcement: {str(e)}", "error")
                finally:
                    cur.close()
                    db.close()
            else:
                flash("Announcement title is required.", "error")
            return redirect(url_for("branch_admin.dashboard"))
        # Create User logic removed from here

    return render_template(
        "branch_admin_dashboard.html",
        announcements_list=announcements_list,
        grades=grades,
        metrics=metrics
    )

@branch_admin_bp.route("/branch-admin/announcements/<int:announcement_id>/hide", methods=["POST"])
def announcement_hide(announcement_id):
    if session.get("role") != "branch_admin":
        return redirect("/")

    branch_id = session.get("branch_id")
    if not branch_id:
        return redirect("/")

    db = get_db_connection()
    cur = db.cursor()
    try:
        # ✅ correct column + scope by branch
        cur.execute("""
            UPDATE announcements
            SET is_active = FALSE
            WHERE announcement_id = %s AND branch_id = %s
        """, (announcement_id, branch_id))
        db.commit()
        flash("Announcement hidden from homepage.", "success")
    except Exception:
        db.rollback()
        flash("Could not hide announcement.", "error")
    finally:
        cur.close()
        db.close()
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
# BRANCH ADMIN: INVENTORY
# =======================
@branch_admin_bp.route("/branch-admin/inventory", methods=["GET"])
def branch_admin_inventory():
    if session.get("role") != "branch_admin":
        return redirect("/")

    branch_id = session.get("branch_id")

    search = (request.args.get("search") or "").strip()
    category_filter = (request.args.get("category") or "").strip()
    grade_filter = (request.args.get("grade") or "").strip()
    status_filter = (request.args.get("status") or "active").strip()

    if not category_filter or category_filter.upper() == 'BOOK':
        return redirect("/branch-admin/inventory?category=UNIFORM&status=" + status_filter)

    db = get_db_connection()
    cursor = db.cursor()
    try:
        where = ["branch_id = %s", "category = %s"]
        params = [branch_id, category_filter]

        if status_filter in ("active", "inactive"):
            where.append("is_active = %s")
            params.append(status_filter == "active")

        if search:
            where.append("""
                (
                  item_name ILIKE %s OR
                  category ILIKE %s OR
                  COALESCE(grade_level,'') ILIKE %s OR
                  COALESCE(size_label,'') ILIKE %s
                )
            """)
            like = f"%{search}%"
            params.extend([like, like, like, like])

        where_sql = " AND ".join(where)

        cursor.execute(f"""
            SELECT
                item_id, category, item_name, grade_level, is_common,
                size_label, price, stock_total, reserved_qty, image_url, is_active
            FROM inventory_items
            WHERE {where_sql}
        """, params)

        all_items = cursor.fetchall() or []

        if grade_filter:
            items = []
            for item in all_items:
                item_name = item[2]
                stored_grade = item[3]
                if item_matches_grade_filter(item_name, stored_grade, grade_filter):
                    items.append(item)
        else:
            items = all_items

        enhanced_items = []
        for item in items:
            item_list = list(item)
            item_list.append(get_grade_display(item[2], item[3]))  # index 11
            enhanced_items.append(tuple(item_list))

        def sort_key(item):
            category = item[1]
            grade_level = item[3]
            item_name = item[2]
            cat = str(category or "").strip().upper()
            cat_order = 0 if cat == "BOOK" else (1 if cat == "UNIFORM" else 2)
            return (cat_order, get_grade_order(grade_level), item_name.lower())

        enhanced_items = sorted(enhanced_items, key=sort_key)

        cursor.execute("""
            SELECT
              COUNT(*) AS total_items,
              COALESCE(SUM(stock_total),0) AS total_stock,
              COALESCE(SUM(reserved_qty),0) AS total_reserved,
              COALESCE(SUM(CASE WHEN (stock_total - reserved_qty) < 10 THEN 1 ELSE 0 END),0) AS low_stock_items
            FROM inventory_items
            WHERE branch_id = %s AND is_active = TRUE AND category != 'BOOK'
        """, (branch_id,))
        stats = cursor.fetchone()

    finally:
        cursor.close()
        db.close()

    return render_template(
        "branch_admin_inventory.html",
        items=enhanced_items,
        stats=stats,
        search=search,
        category_filter=category_filter,
        grade_filter=grade_filter,
        status_filter=status_filter
    )

@branch_admin_bp.route("/branch-admin/inventory/add", methods=["GET", "POST"])
def branch_admin_inventory_add():
    if session.get("role") != "branch_admin":
        return redirect("/")

    branch_id = session.get("branch_id")
    message = None
    error = None

    if request.method == "POST":
        category = (request.form.get("category") or "").strip()
        item_name = (request.form.get("item_name") or "").strip()
        grade_level = (request.form.get("grade_level") or "").strip()
        is_common = request.form.get("is_common") == "on"
        size_label = (request.form.get("size_label") or "").strip() or None
        price = (request.form.get("price") or "").strip()
        stock_total = (request.form.get("stock_total") or "").strip()
        image_url = (request.form.get("image_url") or "").strip() or None

        if not (category and item_name and price and stock_total):
            flash("Missing required fields", "error")
            return redirect("/branch-admin/inventory/add")

        db = get_db_connection()
        cursor = db.cursor()
        try:
            cursor.execute("""
                INSERT INTO inventory_items
                (branch_id, category, item_name, grade_level, is_common, size_label,
                 price, stock_total, reserved_qty, image_url, is_active)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,0,%s,TRUE)
                RETURNING item_id
            """, (branch_id, category, item_name, grade_level, is_common, size_label,
                  price, stock_total, image_url))
            cursor.fetchone()
            db.commit()

            flash("Item added successfully!", "success")
            return redirect("/branch-admin/inventory?category=" + category)
        except Exception as e:
            db.rollback()
            flash(f"Failed to add item: {e}", "error")
        finally:
            cursor.close()
            db.close()

    return render_template("branch_admin_inventory_add.html", message=message, error=error)

@branch_admin_bp.route("/branch-admin/inventory/<int:item_id>/restock", methods=["GET", "POST"])
def branch_admin_inventory_restock(item_id):
    if session.get("role") != "branch_admin":
        return redirect("/")

    branch_id = session.get("branch_id")
    error = None
    message = None

    db = get_db_connection()
    cursor = db.cursor()

    try:
        cursor.execute("""
            SELECT item_id, item_name, category, stock_total, reserved_qty, price
            FROM inventory_items
            WHERE item_id = %s AND branch_id = %s
            LIMIT 1
        """, (item_id, branch_id))
        item = cursor.fetchone()

        if not item:
            return "Item not found", 404

        cursor.execute("""
            SELECT size_id, size_label, stock_total, reserved_qty
            FROM inventory_item_sizes
            WHERE item_id = %s
        """, (item_id,))
        size_rows = cursor.fetchall() or []
        size_rows = sorted(size_rows, key=lambda r: size_sort_key(r[1]))

        if request.method == "POST":
            action = (request.form.get("action") or "").strip()

            if action == "create_sizes":
                created = ensure_default_sizes_exist(cursor, item_id)
                recompute_item_totals_from_sizes(cursor, item_id, branch_id)
                db.commit()
                if created:
                    flash("✅ Size rows created (XS-XXL). You can now restock per size.", "success")
                else:
                    flash("Sizes already exist for this item.", "info")

                return redirect(url_for("branch_admin.branch_admin_inventory_restock", item_id=item_id))

            size_label = (request.form.get("size_label") or "").strip().upper()
            add_stock = (request.form.get("add_stock") or "").strip()

            if not size_label:
                raise Exception("Please select a size (XS-XXL).")
            if not add_stock:
                raise Exception("Please enter stock quantity to add.")

            add_stock = int(add_stock)
            if add_stock <= 0:
                raise Exception("Stock quantity must be greater than 0.")

            cursor.execute("""
                SELECT 1
                FROM inventory_item_sizes
                WHERE item_id = %s AND UPPER(size_label) = %s
                LIMIT 1
            """, (item_id, size_label))
            exists = cursor.fetchone()

            if not exists:
                raise Exception("Selected size row does not exist. Click 'Create default sizes' first.")

            cursor.execute("""
                UPDATE inventory_item_sizes
                SET stock_total = stock_total + %s
                WHERE item_id = %s AND UPPER(size_label) = %s
            """, (add_stock, item_id, size_label))

            recompute_item_totals_from_sizes(cursor, item_id, branch_id)

            db.commit()
            flash(f"✅ Restocked {add_stock} for size {size_label}.", "success")
            return redirect(url_for("branch_admin.branch_admin_inventory_restock", item_id=item_id))

        cursor.execute("""
            SELECT size_id, size_label, stock_total, reserved_qty
            FROM inventory_item_sizes
            WHERE item_id = %s
        """, (item_id,))
        size_rows = cursor.fetchall() or []
        size_rows = sorted(size_rows, key=lambda r: size_sort_key(r[1]))

    except Exception as e:
        db.rollback()
        error = str(e)
        flash(error, "error")
    finally:
        cursor.close()
        db.close()

    return render_template(
        "branch_admin_inventory_restock.html",
        item=item,
        size_rows=size_rows,
        size_order=SIZE_ORDER,
        message=message,
        error=error
    )

@branch_admin_bp.route("/branch-admin/inventory/<int:item_id>/price", methods=["GET", "POST"])
def branch_admin_inventory_price(item_id):
    if session.get("role") != "branch_admin":
        return redirect("/")

    branch_id = session.get("branch_id")
    message = None
    error = None

    db = get_db_connection()
    cursor = db.cursor()

    try:
        cursor.execute("""
            SELECT item_id, item_name, category, price, stock_total
            FROM inventory_items
            WHERE item_id = %s AND branch_id = %s
        """, (item_id, branch_id))
        item = cursor.fetchone()

        if not item:
            return "Item not found", 404

        if request.method == "POST":
            new_price = (request.form.get("new_price") or "").strip()
            if not new_price:
                raise Exception("Please enter new price")

            new_price = float(new_price)
            if new_price <= 0:
                raise Exception("Price must be greater than 0")

            cursor.execute("""
                UPDATE inventory_items
                SET price = %s
                WHERE item_id = %s AND branch_id = %s
            """, (new_price, item_id, branch_id))
            db.commit()
            flash("Price updated successfully!", "success")

            cursor.execute("""
                SELECT item_id, item_name, category, price, stock_total
                FROM inventory_items
                WHERE item_id = %s AND branch_id = %s
            """, (item_id, branch_id))
            item = cursor.fetchone()

    except Exception as e:
        db.rollback()
        error = str(e)
        flash(error, "error")
    finally:
        cursor.close()
        db.close()

    return render_template("branch_admin_inventory_price.html", item=item, message=message, error=error)

@branch_admin_bp.route("/branch-admin/inventory/<int:item_id>/toggle", methods=["POST"])
def branch_admin_inventory_toggle(item_id):
    if session.get("role") != "branch_admin":
        return redirect("/")

    branch_id = session.get("branch_id")

    db = get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute("""
            UPDATE inventory_items
            SET is_active = NOT is_active
            WHERE item_id = %s AND branch_id = %s
        """, (item_id, branch_id))
        db.commit()
        flash("Item status updated.", "success")
    except Exception:
        db.rollback()
        flash("Failed to toggle item.", "error")
    finally:
        cursor.close()
        db.close()

    return redirect(request.referrer or "/branch-admin/inventory?category=UNIFORM")

@branch_admin_bp.route("/branch-admin/grade-levels", methods=["GET", "POST"])
def branch_admin_grade_levels():
    if session.get("role") != "branch_admin":
        return redirect("")

    branch_id = session.get("branch_id")
    db = get_db_connection()
    cursor = db.cursor()

    VALID_GRADES = [
        "Nursery", "Kinder",
        "Grade 1", "Grade 2", "Grade 3",
        "Grade 4", "Grade 5", "Grade 6",
        "Grade 7", "Grade 8", "Grade 9",
        "Grade 10", "Grade 11", "Grade 12"
    ]

    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        order = request.form.get("display_order") or None
        description = (request.form.get("description") or "").strip()

        # ✅ validation
        if name not in VALID_GRADES:
            flash("Invalid grade level selected.", "error")
            return redirect(url_for('branch_admin.branch_admin_grade_levels'))

        try:
            order_int = int(order)
        except (TypeError, ValueError):
            order_int = 0

        if not name or order is None or order_int < 1:
            flash("Name and order (must be 1 or greater) are required.", "error")
        else:
            try:
                cursor.execute(
                    "INSERT INTO grade_levels (name, display_order, description, branch_id) VALUES (%s, %s, %s, %s)",
                    (name, order_int, description if description else None, branch_id)
                )
                db.commit()
                flash("Grade level added!", "success")
                return redirect(url_for('branch_admin.branch_admin_grade_levels'))  # ✅ important
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

    cursor.close()
    db.close()

    return render_template("branch_admin_grade_levels.html", grades=grades)

@branch_admin_bp.route("/branch-admin/grade-levels/<int:grade_id>/edit", methods=["POST"])
def branch_admin_grade_level_edit(grade_id):
    if session.get("role") != "branch_admin":
        return redirect("")
    branch_id = session.get("branch_id")
    name = (request.form.get("edit_name") or "").strip()
    order = request.form.get("edit_display_order") or None
    description = (request.form.get("edit_description") or "").strip()
    if not name or order is None:
        flash("All fields required.", "error")
        return redirect(url_for("branch_admin.branch_admin_grade_levels"))
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute(
        "UPDATE grade_levels SET name=%s, display_order=%s, description=%s WHERE id=%s AND branch_id=%s",
        (name, int(order), description if description else None, grade_id, branch_id)
    )
    db.commit()
    cursor.close(); db.close()
    flash("Grade level updated.", "success")
    return redirect(url_for("branch_admin.branch_admin_grade_levels"))

@branch_admin_bp.route("/branch-admin/grade-levels/<int:grade_id>/delete", methods=["POST"])
def branch_admin_grade_level_delete(grade_id):
    if session.get("role") != "branch_admin":
        return redirect("")
    branch_id = session.get("branch_id")
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute("DELETE FROM grade_levels WHERE id=%s AND branch_id=%s", (grade_id, branch_id))
    db.commit()
    cursor.close(); db.close()
    flash("Grade level deleted.", "success")
    return redirect(url_for("branch_admin.branch_admin_grade_levels"))

# SCHOOL YEAR
@branch_admin_bp.route('/branch_admin/add_year', methods=['GET', 'POST'])
def add_year():
    db = get_db_connection()
    cursor = db.cursor()

    branch_id = int(session.get("branch_id"))

    if not branch_id:
        flash("No branch found in session.", "error")
        return redirect(url_for("auth.login"))

    try:
        # ── ADD NEW YEAR ──
        if request.method == 'POST':
            label = request.form['label'].strip()

            # Check if exists first to avoid ON CONFLICT errors on DBs without unique constraints
            cursor.execute("SELECT 1 FROM school_years WHERE label=%s AND branch_id=%s", (label, branch_id))
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO school_years (label, branch_id)
                    VALUES (%s, %s)
                """, (label, branch_id))
                db.commit()  # ✅ YOU MISSED THIS BEFORE
                flash("School year added!", "success")
            else:
                flash("School year already exists.", "warning")
                
            return redirect(url_for('branch_admin.add_year'))

        # ── ACTIVATE / DEACTIVATE ──
        action = request.args.get('action')
        year_id = request.args.get('year_id')

        if action in ['activate', 'deactivate'] and year_id:
            year_id = int(year_id)

            if action == 'activate':
                # ✅ 1. Get current active year (PER BRANCH ONLY)
                cursor.execute("""
                    SELECT year_id FROM school_years
                    WHERE is_active = TRUE AND branch_id = %s
                    LIMIT 1
                """, (branch_id,))
                old = cursor.fetchone()
                old_year_id = old[0] if old else None

                # ✅ 2. Deactivate ONLY this branch
                cursor.execute("""
                    UPDATE school_years
                    SET is_active = FALSE
                    WHERE branch_id = %s
                """, (branch_id,))

                # ✅ 3. Activate selected year (same branch only)
                cursor.execute("""
                    UPDATE school_years
                    SET is_active = TRUE
                    WHERE year_id = %s AND branch_id = %s
                """, (year_id, branch_id))

                # ✅ 4. Check sections for this year + branch
                cursor.execute("""
                    SELECT COUNT(*) FROM sections 
                    WHERE year_id = %s AND branch_id = %s
                """, (year_id, branch_id))
                section_count = cursor.fetchone()[0]

                if section_count == 0 and old_year_id:
                    # ✅ 5. Copy sections from old year (same branch)
                    cursor.execute("""
                        INSERT INTO sections (branch_id, year_id, section_name, grade_level_id, capacity)
                        SELECT branch_id, %s, section_name, grade_level_id, capacity
                        FROM sections
                        WHERE year_id = %s AND branch_id = %s
                    """, (year_id, old_year_id, branch_id))

                    # ✅ 6. Copy subjects (no teacher yet)
                    cursor.execute("""
                        INSERT INTO section_teachers (section_id, subject_id, teacher_id)
                        SELECT new_s.section_id, st.subject_id, NULL
                        FROM section_teachers st
                        JOIN sections old_s ON st.section_id = old_s.section_id
                        JOIN sections new_s 
                            ON new_s.section_name = old_s.section_name
                            AND new_s.grade_level_id = old_s.grade_level_id
                            AND new_s.branch_id = old_s.branch_id
                            AND new_s.year_id = %s
                        WHERE old_s.year_id = %s
                        AND old_s.branch_id = %s
                    """, (year_id, old_year_id, branch_id))

                    db.commit()
                    flash("✅ School year activated and sections copied!", "success")
                else:
                    db.commit()
                    flash("✅ School year activated! Sections already exist.", "success")

            else:
                # ── DEACTIVATE (branch-specific) ──
                cursor.execute("""
                    UPDATE school_years
                    SET is_active = FALSE
                    WHERE year_id = %s AND branch_id = %s
                """, (year_id, branch_id))

                db.commit()
                flash("School year deactivated!", "success")

            return redirect(url_for('branch_admin.add_year'))

        # ── FETCH YEARS (branch only) ──
        cursor.execute("""
            SELECT year_id, label, is_active 
            FROM school_years 
            WHERE branch_id = %s
            ORDER BY label DESC
        """, (branch_id,))
        years = cursor.fetchall()

    finally:
        cursor.close()
        db.close()

    return render_template('branch_admin_school_years.html', years=years)
# =======================
# SECTIONS (branch-scoped)
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

    # -- UNCHANGED: Check and populate grade levels --
    cursor.execute("SELECT COUNT(*) FROM grade_levels WHERE branch_id = %s", (branch_id,))
    if cursor.fetchone()['count'] == 0:
        default_grades = [
            ("Nursery", 1), ("Kinder", 2), ("Grade 1", 3), ("Grade 2", 4), ("Grade 3", 5),
            ("Grade 4", 6), ("Grade 5", 7), ("Grade 6", 8), ("Grade 7", 9), ("Grade 8", 10),
            ("Grade 9", 11), ("Grade 10", 12), ("Grade 11", 13), ("Grade 12", 14)
        ]
        for g_name, g_order in default_grades:
            cursor.execute(
                "INSERT INTO grade_levels (name, display_order, branch_id) VALUES (%s, %s, %s)",
                (g_name, g_order, branch_id)
            )
        db.commit()

    cursor.execute(
        "SELECT id, name FROM grade_levels WHERE branch_id = %s ORDER BY display_order",
        (branch_id,)
    )
    grades = cursor.fetchall() or []

    # --- NEW: Fetch available years for dropdown
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
            if capacity < 1:
                capacity = 50
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
                flash("Invalid grade level for this branch.", "error")
                cursor.close()
                db.close()
                return redirect("/branch-admin/sections")

            cursor.execute("""
                SELECT 1 FROM school_years 
                WHERE year_id = %s AND branch_id = %s
            """, (year_id, branch_id))
            if not cursor.fetchone():
                flash("Invalid school year selected.", "error")
                cursor.close()
                db.close()
                return redirect("/branch-admin/sections")

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

        cursor.close()
        db.close()
        return redirect("/branch-admin/sections")

    # -- Update to include school year label
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
        years=years  # <-- Pass to template!
    )


@branch_admin_bp.route("/branch-admin/sections/<int:section_id>/delete", methods=["POST"])
def branch_admin_section_delete(section_id):
    if session.get("role") != "branch_admin":
        return redirect("/")

    branch_id = session.get("branch_id")
    if not branch_id:
        return redirect("/")

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
        if capacity < 1:
            capacity = 50
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
        # Verify grade level belongs to this branch
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

# =======================
# SUBJECTS (branch-scoped via sections)
# =======================
@branch_admin_bp.route("/branch-admin/subjects", methods=["GET", "POST"])
def branch_admin_subjects():
    if session.get("role") != "branch_admin":
        return redirect("/")

    branch_id = session.get("branch_id")
    if not branch_id:
        flash("No branch assigned.", "error")
        return redirect(url_for("auth.login"))

    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # ✅ dropdown only for this branch sections
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
        name = (request.form.get("name") or "").strip()
        section_id_raw = request.form.get("section_id")

        try:
            section_id = int(section_id_raw)
        except (TypeError, ValueError):
            section_id = None

        if not name or not section_id:
            flash("Subject name and section are required.", "error")
            cursor.close(); db.close()
            return redirect("/branch-admin/subjects")

        try:
            # ✅ enforce section belongs to this branch
            cursor.execute("SELECT 1 FROM sections WHERE section_id=%s AND branch_id=%s", (section_id, branch_id))
            if not cursor.fetchone():
                flash("Invalid section for this branch.", "error")
                cursor.close(); db.close()
                return redirect("/branch-admin/subjects")

            # create subject if not exists
            cursor.execute("""
                INSERT INTO subjects (name)
                VALUES (%s)
                ON CONFLICT (name) DO NOTHING
                RETURNING subject_id
            """, (name,))
            res = cursor.fetchone()
            if res and res.get("subject_id"):
                subject_id = res["subject_id"]
            else:
                cursor.execute("SELECT subject_id FROM subjects WHERE name=%s", (name,))
                subject_id = cursor.fetchone()["subject_id"]

            # ✅ link subject to section with teacher_id NULL (manual exists check)
            cursor.execute("""
                SELECT 1
                FROM section_teachers
                WHERE section_id=%s AND subject_id=%s AND teacher_id IS NULL
                LIMIT 1
            """, (section_id, subject_id))
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO section_teachers (section_id, teacher_id, subject_id)
                    VALUES (%s, NULL, %s)
                """, (section_id, subject_id))

            db.commit()
            flash("Subject added and assigned to section!", "success")

        except Exception as e:
            db.rollback()
            flash(f"Could not add subject: {str(e)}", "error")

        cursor.close()
        db.close()
        return redirect("/branch-admin/subjects")

    # ✅ only show subjects used by this branch
    cursor.execute("""
        SELECT DISTINCT sub.subject_id, sub.name
        FROM subjects sub
        JOIN section_teachers st ON st.subject_id = sub.subject_id
        JOIN sections s ON s.section_id = st.section_id
        INNER JOIN school_years y ON s.year_id = y.year_id           
        WHERE s.branch_id = %s AND y.is_active = TRUE
        ORDER BY sub.name
    """, (branch_id,))
    subjects = cursor.fetchall() or []

    # assignments for this branch only
    cursor.execute("""
        SELECT
            st.subject_id,
            s.section_id,
            s.section_name,
            g.name AS grade_level_name
        FROM section_teachers st
        INNER JOIN sections s ON st.section_id = s.section_id
        INNER JOIN grade_levels g ON s.grade_level_id = g.id
        INNER JOIN school_years y ON s.year_id = y.year_id           
        WHERE s.branch_id = %s AND y.is_active = TRUE
        ORDER BY st.subject_id, g.display_order, s.section_name
    """, (branch_id,))
    assignments = cursor.fetchall() or []

    subject_to_sections = {}
    subject_first_section = {}
    for a in assignments:
        sid = a["subject_id"]
        subject_to_sections.setdefault(sid, []).append(
            f"{a['grade_level_name']} - {a['section_name']}"
        )
        if sid not in subject_first_section:
            subject_first_section[sid] = a["section_id"]

    cursor.close()
    db.close()

    return render_template(
        "branch_admin_subjects.html",
        subjects=subjects,
        section_options=section_options,
        subject_to_sections=subject_to_sections,
        subject_first_section=subject_first_section
    )

@branch_admin_bp.route("/branch-admin/subjects/<int:subject_id>/delete", methods=["POST"])
def branch_admin_subject_delete(subject_id):
    if session.get("role") != "branch_admin":
        return redirect("/")

    branch_id = session.get("branch_id")
    if not branch_id:
        return redirect("/")

    db = get_db_connection()
    cursor = db.cursor()
    try:
        # ✅ unlink subject only for this branch
        cursor.execute("""
            DELETE FROM section_teachers st
            USING sections s
            WHERE st.section_id = s.section_id
              AND s.branch_id = %s
              AND st.subject_id = %s
        """, (branch_id, subject_id))

        # optional: delete subject if not used anywhere else
        cursor.execute("SELECT 1 FROM section_teachers WHERE subject_id=%s LIMIT 1", (subject_id,))
        still_used = cursor.fetchone()
        if not still_used:
            cursor.execute("DELETE FROM subjects WHERE subject_id=%s", (subject_id,))

        db.commit()
        flash("Subject removed for this branch.", "success")
    except Exception as e:
        db.rollback()
        flash(f"Could not delete subject: {str(e)}", "error")
    finally:
        cursor.close()
        db.close()

    return redirect("/branch-admin/subjects")

@branch_admin_bp.route("/branch-admin/subjects/<int:subject_id>/edit", methods=["POST"])
def branch_admin_subject_edit(subject_id):
    if session.get("role") != "branch_admin":
        return redirect("/")

    branch_id = session.get("branch_id")
    new_name = (request.form.get("name") or "").strip()
    section_id_raw = request.form.get("section_id")

    try:
        section_id = int(section_id_raw)
    except (TypeError, ValueError):
        section_id = None

    if not new_name or not section_id:
        flash("Subject name and section are required.", "error")
        return redirect("/branch-admin/subjects")

    db = get_db_connection()
    cursor = db.cursor()
    try:
        # Verify section belongs to this branch
        cursor.execute("SELECT 1 FROM sections WHERE section_id=%s AND branch_id=%s", (section_id, branch_id))
        if not cursor.fetchone():
            flash("Invalid section.", "error")
            return redirect("/branch-admin/subjects")

        # Check if new name already exists for a different subject
        cursor.execute("SELECT subject_id FROM subjects WHERE LOWER(name) = LOWER(%s)", (new_name,))
        existing_subject = cursor.fetchone()
        
        if existing_subject and existing_subject[0] != subject_id:
            flash(f"Subject '{new_name}' already exists in the system. To use it, add it as a new subject to your section instead.", "error")
            return redirect("/branch-admin/subjects")

        # In order to allow redefining the section assignment securely, we can drop the old assignments of this subject for THIS branch, and recreate a new single assignment, or just rename the subject itself locally.
        # Let's globally update the subject name, and then replace the section assignment for this branch.
        cursor.execute("UPDATE subjects SET name = %s WHERE subject_id = %s", (new_name, subject_id))
        
        cursor.execute("""
            DELETE FROM section_teachers st
            USING sections s
            WHERE st.section_id = s.section_id
              AND s.branch_id = %s
              AND st.subject_id = %s
        """, (branch_id, subject_id))
        
        cursor.execute("""
            INSERT INTO section_teachers (section_id, teacher_id, subject_id)
            VALUES (%s, NULL, %s)
        """, (section_id, subject_id))

        db.commit()
        flash("Subject updated successfully.", "success")
    except Exception as e:
        db.rollback()
        flash(f"Could not update subject: {str(e)}", "error")
    finally:
        cursor.close()
        db.close()

    return redirect("/branch-admin/subjects")

# =======================
# TEACHER → SECTION + SUBJECT ASSIGNMENT (branch-scoped)
# =======================
@branch_admin_bp.route("/branch-admin/assign-teachers", methods=["GET", "POST"])
def branch_admin_assign_teachers():
    if session.get("role") != "branch_admin":
        return redirect("/")

    branch_id = session.get("branch_id")
    if not branch_id:
        flash("No branch assigned.", "error")
        return redirect(url_for("auth.login"))

    grade_filter = (request.args.get("grade") or "").strip()

    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        # ── GET: Load unique grade levels used in the current branch ──
        cursor.execute("""
            SELECT DISTINCT g.id, g.name, g.display_order
            FROM sections s
            JOIN grade_levels g ON s.grade_level_id = g.id
            JOIN school_years y ON s.year_id = y.year_id
            WHERE s.branch_id = %s AND y.is_active = TRUE
            ORDER BY g.display_order
        """, (branch_id,))
        grade_options = cursor.fetchall() or []
        
        # Default to the first available grade if no filter is set
        if not grade_filter and grade_options:
            grade_filter = str(grade_options[0]['id'])

        if request.method == "POST":
            section_id_raw  = request.form.get("section_id")
            subject_id_raw  = request.form.get("subject_id")
            teacher_id_raw  = request.form.get("teacher_id")  # empty = unassign

            try:
                section_id = int(section_id_raw)
                subject_id = int(subject_id_raw)
                teacher_id = int(teacher_id_raw) if teacher_id_raw else None
            except (TypeError, ValueError):
                flash("Invalid input. Please try again.", "error")
                return redirect(url_for("branch_admin.branch_admin_assign_teachers"))

            # ── Verify section belongs to THIS branch ──
            cursor.execute(
                "SELECT 1 FROM sections WHERE section_id=%s AND branch_id=%s",
                (section_id, branch_id)
            )
            if not cursor.fetchone():
                flash("Section not found in this branch.", "error")
                return redirect(url_for("branch_admin.branch_admin_assign_teachers"))

            # ── Verify teacher belongs to THIS branch (if assigning) ──
            if teacher_id:
                cursor.execute(
                    "SELECT 1 FROM users WHERE user_id=%s AND branch_id=%s AND role='teacher'",
                    (teacher_id, branch_id)
                )
                if not cursor.fetchone():
                    flash("Teacher not found in this branch.", "error")
                    return redirect(url_for("branch_admin.branch_admin_assign_teachers"))

            cursor.execute("""
                UPDATE section_teachers
                SET teacher_id = %s
                WHERE section_id = %s AND subject_id = %s
            """, (teacher_id, section_id, subject_id))
            db.commit()

            action_label = "assigned" if teacher_id else "unassigned"
            flash(f"Teacher {action_label} successfully!", "success")
            
            # Preserve the query param on redirect
            return redirect(url_for("branch_admin.branch_admin_assign_teachers", grade=request.args.get("grade", "")))

        # ── GET: load teachers for this branch ──
        cursor.execute("""
            SELECT user_id, username, full_name, gender, grade_level
            FROM users
            WHERE branch_id = %s AND role = 'teacher'
            ORDER BY full_name NULLS LAST, username
        """, (branch_id,))
        teachers = cursor.fetchall() or []

        # ── GET: load all section+subject combos for this branch ──
        base_query = """
            SELECT
                st.id          AS section_teacher_id,
                st.section_id,
                st.subject_id,
                st.teacher_id,
                s.section_name,
                g.name       AS grade_level_name,
                g.display_order,
                sub.name     AS subject_name,
                u.username   AS teacher_username,
                u.full_name  AS teacher_full_name,
                u.gender     AS teacher_gender
            FROM section_teachers st
            JOIN sections s    ON st.section_id  = s.section_id
            JOIN grade_levels g ON s.grade_level_id = g.id
            JOIN subjects sub  ON st.subject_id  = sub.subject_id
            LEFT JOIN users u  ON st.teacher_id  = u.user_id
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

        # ── GET: Load section dropdown options for this branch ──
        cursor.execute("""
            SELECT
                s.section_id,
                CONCAT(g.name, ' - ', s.section_name) AS section_display,
                g.id AS grade_level_id
            FROM sections s
            JOIN grade_levels g ON s.grade_level_id = g.id
            JOIN school_years y ON s.year_id = y.year_id
            WHERE s.branch_id = %s AND y.is_active = TRUE
            ORDER BY g.display_order, s.section_name
        """, (branch_id,))
        section_options = cursor.fetchall() or []

    except Exception as e:
        db.rollback()
        flash(f"Error loading data: {str(e)}", "error")
        teachers, assignments, grade_options, section_options = [], [], [], []
    finally:
        cursor.close()
        db.close()

    return render_template(
        "branch_admin_assign_teachers.html",
        teachers=teachers,
        assignments=assignments,
        grade_options=grade_options,
        grade_filter=grade_filter,
        section_options=section_options,
    )

@branch_admin_bp.route("/branch-admin/api/get-all-subjects/<int:teacher_id>", methods=["GET"])
def api_get_all_subjects(teacher_id):
    """Get ALL subjects available for a teacher with assignment status"""
    if session.get("role") != "branch_admin":
        return {"error": "Unauthorized"}, 403

    branch_id = session.get("branch_id")
    if not branch_id:
        return {"error": "No branch assigned"}, 400

    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        # Verify teacher belongs to this branch
        cursor.execute(
            "SELECT user_id, full_name FROM users WHERE user_id=%s AND branch_id=%s AND role='teacher'",
            (teacher_id, branch_id)
        )
        teacher = cursor.fetchone()
        if not teacher:
            return {"error": "Teacher not found"}, 404

        # Get all subjects in all sections for this branch
        # IMPORTANT: Check if ANYONE (not just this teacher) is assigned
        cursor.execute("""
            SELECT
                st.subject_id,
                st.section_id,
                st.teacher_id,
                sub.name AS subject_name,
                s.section_name,
                g.name AS grade_level_name,
                g.id AS grade_level_id,
                u.full_name AS current_teacher_name,
                u.user_id AS current_teacher_id,
                (st.teacher_id IS NOT NULL) AS is_currently_assigned,
                (st.teacher_id = %s) AS is_assigned_to_this_teacher
            FROM section_teachers st
            JOIN sections s ON st.section_id = s.section_id
            JOIN grade_levels g ON s.grade_level_id = g.id
            JOIN subjects sub ON st.subject_id = sub.subject_id
            LEFT JOIN users u ON st.teacher_id = u.user_id
            JOIN school_years y ON s.year_id = y.year_id
            WHERE s.branch_id = %s AND y.is_active = TRUE
            ORDER BY g.display_order, s.section_name, sub.name
        """, (teacher_id, branch_id))
        
        subjects = cursor.fetchall() or []

        print(f"✅ DEBUG: Found {len(subjects)} total subjects for teacher {teacher_id}")
        for subj in subjects:
            print(f"   - {subj['subject_name']}: currently_assigned={subj['is_currently_assigned']}, assigned_to_this_teacher={subj['is_assigned_to_this_teacher']}, current_teacher={subj['current_teacher_name']}")

        return {
            "success": True,
            "teacher_name": teacher['full_name'],
            "teacher_id": teacher_id,
            "subjects": [dict(row) for row in subjects]
        }

    except Exception as e:
        print(f"❌ ERROR in api_get_all_subjects: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}, 500
    finally:
        cursor.close()
        db.close()


@branch_admin_bp.route("/branch-admin/assign-teachers-bulk", methods=["POST"])
def assign_teachers_bulk():
    """Bulk assign a teacher to multiple subjects"""
    if session.get("role") != "branch_admin":
        return {"error": "Unauthorized"}, 403

    branch_id = session.get("branch_id")
    if not branch_id:
        return {"error": "No branch assigned"}, 400

    data = request.get_json()
    teacher_id = data.get("teacher_id")
    subject_ids = data.get("subject_ids", [])

    if not teacher_id or not subject_ids:
        return {"success": False, "message": "Missing teacher or subjects"}, 400

    db = get_db_connection()
    cursor = db.cursor()

    try:
        # Verify teacher belongs to this branch
        cursor.execute(
            "SELECT 1 FROM users WHERE user_id=%s AND branch_id=%s AND role='teacher'",
            (teacher_id, branch_id)
        )
        if not cursor.fetchone():
            return {"success": False, "message": "Teacher not found"}, 404

        count = 0
        for subject_id in subject_ids:
            try:
                # Verify the subject exists in a section of this branch
                cursor.execute("""
                    SELECT st.section_id FROM section_teachers st
                    JOIN sections s ON st.section_id = s.section_id
                    WHERE st.subject_id = %s AND s.branch_id = %s
                    LIMIT 1
                """, (subject_id, branch_id))
                
                if cursor.fetchone():
                    # Update the assignment
                    cursor.execute("""
                        UPDATE section_teachers
                        SET teacher_id = %s
                        WHERE subject_id = %s
                        AND section_id IN (
                            SELECT section_id FROM sections WHERE branch_id = %s
                        )
                    """, (teacher_id, subject_id, branch_id))
                    count += cursor.rowcount

            except Exception as e:
                print(f"Error assigning subject {subject_id}: {str(e)}")
                continue

        db.commit()
        print(f"✅ Bulk assigned {count} subjects to teacher {teacher_id}")

        return {
            "success": True,
            "count": count,
            "message": f"Successfully assigned {count} subjects"
        }

    except Exception as e:
        db.rollback()
        print(f"ERROR in bulk assignment: {str(e)}")
        return {"success": False, "message": str(e)}, 500
    finally:
        cursor.close()
        db.close()


@branch_admin_bp.route("/branch-admin/remove-teacher-assignment", methods=["POST"])
def remove_teacher_assignment():
    """Remove (unassign) a teacher from a section+subject"""
    if session.get("role") != "branch_admin":
        return {"error": "Unauthorized"}, 403

    branch_id = session.get("branch_id")
    data = request.get_json()
    section_teacher_id = data.get("section_teacher_id")

    if not section_teacher_id:
        return {"success": False, "message": "Missing section_teacher_id"}, 400

    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        # Verify this row belongs to this branch
        cursor.execute("""
            SELECT st.id FROM section_teachers st
            JOIN sections s ON st.section_id = s.section_id
            WHERE st.id = %s AND s.branch_id = %s
        """, (section_teacher_id, branch_id))
        if not cursor.fetchone():
            return {"success": False, "message": "Assignment not found"}, 404

        cursor.execute(
            "UPDATE section_teachers SET teacher_id = NULL WHERE id = %s",
            (section_teacher_id,)
        )
        db.commit()
        return {"success": True}
    except Exception as e:
        db.rollback()
        return {"success": False, "message": str(e)}, 500
    finally:
        cursor.close()
        db.close()

@branch_admin_bp.route("/branch-admin/api/get-subjects/<int:section_id>", methods=["GET"])
def api_get_section_subjects(section_id):
    """Returns JSON list of subjects for a given section"""
    if session.get("role") != "branch_admin":
        return {"error": "Unauthorized"}, 403

    branch_id = session.get("branch_id")
    if not branch_id:
        return {"error": "No branch assigned"}, 400

    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        # Verify section belongs to this branch
        cursor.execute(
            "SELECT 1 FROM sections s JOIN school_years y ON s.year_id = y.year_id WHERE section_id=%s AND branch_id=%s AND y.is_active = TRUE",
            (section_id, branch_id)
        )
        if not cursor.fetchone():
            return {"error": "Section not found in this branch"}, 404

        # Get all subjects for this section
        cursor.execute("""
            SELECT
                st.subject_id,
                sub.name AS subject_name,
                st.teacher_id,
                u.full_name AS teacher_full_name,
                u.username AS teacher_username
            FROM section_teachers st
            JOIN subjects sub ON st.subject_id = sub.subject_id
            JOIN school_years y ON s.year_id = y.year_id
            LEFT JOIN users u ON st.teacher_id = u.user_id
            WHERE st.section_id = %s
            AND y.is_active = TRUE
            ORDER BY sub.name
        """, (section_id,))
        subjects = cursor.fetchall() or []

        return {
            "success": True,
            "subjects": [dict(row) for row in subjects]
        }

    except Exception as e:
        return {"error": str(e)}, 500
    finally:
        cursor.close()
        db.close()


# =======================
# STUDENT → SECTION ASSIGNMENT
# =======================
@branch_admin_bp.route("/branch-admin/assign-students", methods=["GET", "POST"])
def branch_admin_assign_students():
    if session.get("role") != "branch_admin":
        return redirect("/")

    branch_id = session.get("branch_id")
    if not branch_id:
        flash("No branch assigned.", "error")
        return redirect(url_for("auth.login"))

    grade_filter = (request.args.get("grade") or "").strip()

    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        # ✅ Only load THIS branch's grade levels
        cursor.execute(
            "SELECT id, name, display_order FROM grade_levels WHERE branch_id = %s ORDER BY display_order",
            (branch_id,)
        )
        grade_options = cursor.fetchall() or []
        
        if not grade_filter and grade_options:
            grade_filter = str(grade_options[0]['id'])

        if request.method == "POST":
            enrollment_id_raw = request.form.get("enrollment_id")
            section_id_raw    = request.form.get("section_id")

            try:
                enrollment_id = int(enrollment_id_raw)
                section_id    = int(section_id_raw) if section_id_raw else None
            except (TypeError, ValueError):
                flash("Invalid input.", "error")
                return redirect(url_for("branch_admin.branch_admin_assign_students", grade=grade_filter))

            cursor.execute("SELECT 1 FROM enrollments WHERE enrollment_id=%s AND branch_id=%s", (enrollment_id, branch_id))
            if not cursor.fetchone():
                flash("Enrollment not found.", "error")
                return redirect(url_for("branch_admin.branch_admin_assign_students", grade=grade_filter))

            if section_id:
                cursor.execute("""
                    SELECT capacity,
                           (SELECT COUNT(*) FROM enrollments WHERE section_id = s.section_id AND status IN ('approved', 'enrolled')) AS current_count
                    FROM sections s
                    JOIN school_years y ON s.year_id = y.year_id
                    WHERE s.section_id=%s AND s.branch_id=%s AND y.is_active = TRUE
                """, (section_id, branch_id))
                sec_info = cursor.fetchone()
                if not sec_info:
                    flash("Section not found.", "error")
                    return redirect(url_for("branch_admin.branch_admin_assign_students", grade=grade_filter))
                if sec_info['current_count'] >= sec_info['capacity']:
                    flash(f"👉 Section is already full ({sec_info['current_count']} students). Please choose another section.", "error")
                    return redirect(url_for("branch_admin.branch_admin_assign_students", grade=grade_filter))

            cursor.execute("UPDATE enrollments SET section_id=%s WHERE enrollment_id=%s", (section_id, enrollment_id))
            db.commit()

            # ── Auto-notify student about all existing Published activities in this section ──
            if section_id:
                try:
                    # Get the student's user_id via enrollments.user_id
                    cursor.execute("""
                        SELECT user_id
                        FROM enrollments
                        WHERE enrollment_id = %s
                        LIMIT 1
                    """, (enrollment_id,))
                    student_user_row = cursor.fetchone()

                    if student_user_row:
                        student_user_id = student_user_row['user_id']

                        # Fetch all Published activities for this section that the student hasn't been notified about
                        cursor.execute("""
                            SELECT a.activity_id, a.title
                            FROM activities a
                            WHERE a.section_id = %s
                              AND a.branch_id  = %s
                              AND a.status     = 'Published'
                              AND NOT EXISTS (
                                  SELECT 1 FROM student_notifications sn
                                  WHERE sn.student_id = %s
                                    AND sn.link = CONCAT('/student/activities/', a.activity_id::text)
                              )
                        """, (section_id, branch_id, student_user_id))
                        pending_activities = cursor.fetchall() or []

                        for act in pending_activities:
                            cursor.execute("""
                                INSERT INTO student_notifications (student_id, title, message, link)
                                VALUES (%s, %s, %s, %s)
                            """, (
                                student_user_id,
                                f"Activity Available: {act['title']}",
                                f"You have been added to a section with an existing activity: {act['title']}.",
                                f"/student/activities/{act['activity_id']}"
                            ))
                        db.commit()
                except Exception as notif_err:
                    # Non-critical: don't rollback the section assignment for a notification failure
                    db.rollback()
                    print(f"[WARN] Could not send activity notifications for enrollment {enrollment_id}: {notif_err}")

            flash("Student section updated successfully!", "success")
            return redirect(url_for("branch_admin.branch_admin_assign_students", grade=grade_filter))

        # ── Load data for GET ──
        cursor.execute("""
            SELECT s.section_id, s.section_name, g.name AS grade_level_name, g.id AS grade_level_id,
                   s.capacity,
                   (SELECT COUNT(*) FROM enrollments e2 WHERE e2.section_id = s.section_id AND e2.status IN ('approved', 'enrolled')) AS current_count
            FROM sections s
            JOIN grade_levels g ON s.grade_level_id = g.id
            JOIN school_years y ON s.year_id = y.year_id
            WHERE s.branch_id = %s
            AND y.is_active = TRUE
            ORDER BY g.display_order, s.section_name
        """, (branch_id,))
        all_sections = cursor.fetchall() or []

        filtered_sections = [s for s in all_sections if str(s['grade_level_id']) == grade_filter]

        # ✅ Also filter grade_levels lookup by branch_id
        grade_name = ""
        if grade_filter:
            cursor.execute(
                "SELECT name FROM grade_levels WHERE id = %s AND branch_id = %s",
                (grade_filter, branch_id)
            )
            grade_row = cursor.fetchone()
            grade_name = grade_row['name'] if grade_row else ""

        cursor.execute("""
            SELECT e.enrollment_id, e.student_name, e.grade_level, e.branch_enrollment_no, e.section_id,
                   s.section_name
            FROM enrollments e
            LEFT JOIN sections s ON e.section_id = s.section_id
            WHERE e.branch_id = %s AND e.status IN ('approved', 'enrolled')
              AND (e.grade_level ILIKE %s OR e.grade_level ILIKE %s)
            ORDER BY e.student_name
        """, (branch_id, grade_name, grade_name.replace("Grade ", "")))
        students = cursor.fetchall() or []

    except Exception as e:
        db.rollback()
        flash(f"Error: {str(e)}", "error")
        grade_options, filtered_sections, students = [], [], []
    finally:
        cursor.close()
        db.close()

    return render_template(
        "branch_admin_assign_students.html",
        grade_options=grade_options,
        sections=filtered_sections,
        students=students,
        grade_filter=grade_filter
    )


@branch_admin_bp.route("/branch-admin/api/assign-student-section", methods=["POST"])
def api_assign_student_section():
    """AJAX: assign a single student to a section (or clear it)"""
    if session.get("role") != "branch_admin":
        return {"error": "Unauthorized"}, 403

    branch_id = session.get("branch_id")
    data = request.get_json()
    enrollment_id = data.get("enrollment_id")
    section_id = data.get("section_id")  # None = unassign

    if not enrollment_id:
        return {"success": False, "message": "Missing enrollment_id"}, 400

    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        # Verify enrollment belongs to this branch
        cursor.execute(
            "SELECT 1 FROM enrollments WHERE enrollment_id=%s AND branch_id=%s",
            (enrollment_id, branch_id)
        )
        if not cursor.fetchone():
            return {"success": False, "message": "Enrollment not found"}, 404

        if section_id:
            # Check capacity
            cursor.execute("""
                SELECT capacity,
                       (SELECT COUNT(*) FROM enrollments
                        WHERE section_id = s.section_id
                          AND status IN ('approved','enrolled')) AS current_count
                FROM sections s
                JOIN school_years y ON s.year_id = y.year_id
                WHERE s.section_id=%s AND s.branch_id=%s AND y.is_active = TRUE
            """, (section_id, branch_id))
            sec = cursor.fetchone()
            if not sec:
                return {"success": False, "message": "Section not found"}, 404
            if sec["current_count"] >= sec["capacity"]:
                return {"success": False, "message": f"Section is full ({sec['current_count']}/{sec['capacity']})"}, 400

        cursor.execute(
            "UPDATE enrollments SET section_id=%s WHERE enrollment_id=%s",
            (section_id, enrollment_id)
        )
        db.commit()

        # Auto-notify student about existing published activities in the new section
        if section_id:
            try:
                cursor.execute("SELECT user_id FROM enrollments WHERE enrollment_id=%s LIMIT 1", (enrollment_id,))
                student_row = cursor.fetchone()
                if student_row:
                    student_user_id = student_row["user_id"]
                    cursor.execute("""
                        SELECT a.activity_id, a.title FROM activities a
                        WHERE a.section_id=%s AND a.branch_id=%s AND a.status='Published'
                          AND NOT EXISTS (
                              SELECT 1 FROM student_notifications sn
                              WHERE sn.student_id=%s AND sn.link=CONCAT('/student/activities/', a.activity_id::text)
                          )
                    """, (section_id, branch_id, student_user_id))
                    for act in (cursor.fetchall() or []):
                        cursor.execute("""
                            INSERT INTO student_notifications (student_id, title, message, link)
                            VALUES (%s, %s, %s, %s)
                        """, (student_user_id,
                              f"Activity Available: {act['title']}",
                              f"You have been added to a section with an existing activity: {act['title']}.",
                              f"/student/activities/{act['activity_id']}"))
                    db.commit()
            except Exception:
                db.rollback()

        return {"success": True}
    except Exception as e:
        db.rollback()
        return {"success": False, "message": str(e)}, 500
    finally:
        cursor.close()
        db.close()


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
    created_user = None
    filter_grade = request.args.get("grade", "")
    filter_section = request.args.get("section", "")

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
            created_user = {"username": username, "password": temp_password, "role": role}

            db.commit()
            if created_user and user_email:
                subject = f"Your {role.capitalize()} Account for Liceo Branch"
                body = f"""Hello,

        Your account has been created!

        Username: {created_user['username']}
        Password: {created_user['password']}
        Login URL: https://liceolms.up.railway.app/

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
            params = [branch_id, role_filter]
            if filter_grade and role_filter == "teacher":
                query += " AND u.grade_level_id = %s"
                params.append(int(filter_grade))
            if filter_section and role_filter == "teacher":
                query += " AND EXISTS (SELECT 1 FROM section_teachers st2 WHERE st2.teacher_id = u.user_id AND st2.section_id = %s)"
                params.append(int(filter_section))

            query += " GROUP BY u.user_id, g.name ORDER BY u.user_id DESC"
            cursor.execute(query, tuple(params))
        accounts = cursor.fetchall() or []

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
        accounts=accounts,
        grades=grades,
        section_options=section_options,
        filter_grade=filter_grade,
        filter_section=filter_section,
        created_user=created_user
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
