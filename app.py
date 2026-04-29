import os
from dotenv import load_dotenv
load_dotenv()  # loads .env file locally; no effect in Railway (env vars set directly)

from flask import Flask, request, session, flash, redirect, url_for, render_template, send_from_directory
from routes import init_routes
from db import is_branch_active, get_db_connection
from extensions import limiter
from routes.teacher import _get_active_school_year
from flask import send_from_directory, make_response


app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "liceo_secret_key_dev")
limiter.init_app(app)
app.jinja_env.add_extension('jinja2.ext.loopcontrols')
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), "uploads")

import mimetypes

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    response = make_response(send_from_directory(app.config['UPLOAD_FOLDER'], filename))
    mime_type, _ = mimetypes.guess_type(filename)
    if mime_type:
        response.headers["Content-Type"] = mime_type
    response.headers["Content-Disposition"] = "inline"
    return response

app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.hostinger.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 465))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'False') == 'True'
app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'True') == 'True'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', os.getenv('MAIL_USERNAME'))

# Session cookie security (panel / security scan)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
if os.getenv("FLASK_ENV") == "production" or os.getenv("RAILWAY_ENVIRONMENT"):
    app.config["SESSION_COOKIE_SECURE"] = True

# Max upload size: 100MB total
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024

@app.before_request
def check_branch_active_status():
    if request.method in ['POST', 'PUT', 'DELETE']:
        if request.endpoint and (request.endpoint.startswith('auth.') or request.endpoint.startswith('super_admin.')):
            return
            
        branch_id = session.get('branch_id')
        if branch_id:
            if not is_branch_active(branch_id):
                flash("This branch is currently deactivated. You cannot perform this action.", "error")
                # Need to return a response to block the request. Redirect back or to a safe page.
                # Assuming most forms are submitted from a GET page, request.referrer usually works.
                # Otherwise, fallback to a safe default like the user's dashboard based on role.
                role = session.get('role')
                fallback = '/'
                if role == 'branch_admin':
                    fallback = url_for('branch_admin.dashboard')
                elif role == 'cashier':
                    fallback = url_for('cashier.dashboard')
                elif role == 'registrar':
                    fallback = url_for('registrar.registrar_home')
                elif role == 'teacher':
                    fallback = url_for('teacher.teacher_dashboard')
                elif role == 'student':
                    fallback = url_for('student_portal.dashboard')
                elif role == 'librarian':
                    fallback = url_for('librarian.dashboard')
                elif role == 'parent':
                    fallback = url_for('parent.dashboard')

                return redirect(request.referrer or fallback)

@app.errorhandler(413)
def request_entity_too_large(error):
    flash("The total size of your submission exceeds the 100MB limit.", "error")
    return redirect(request.referrer or '/')

@app.context_processor
def inject_is_branch_active():
    branch_id = session.get('branch_id')
    is_active = True
    if branch_id and session.get('role') != 'super_admin':
        is_active = is_branch_active(branch_id)
    return dict(is_branch_active_status=is_active)

@app.context_processor
def inject_branch_logo():
    import os
    logo_filename = 'img/spdcss_logo.webp' # Default to webp if available
    branch_name = session.get('branch_name')
    if branch_name:
        clean_name = branch_name.replace(" ", "") + "Logo"
        base_dir = os.path.join(app.root_path, 'static', 'img')
        for ext in ['.webp', '.png', '.jpg', '.jpeg']:
            if os.path.exists(os.path.join(base_dir, clean_name + ext)):
                logo_filename = f"img/{clean_name}{ext}"
                break
    return dict(dynamic_branch_logo=logo_filename)

@app.context_processor
def inject_profile_image():
    img = session.get('profile_image')
    role = session.get('role')
    user_id = session.get('user_id')
    enrollment_id = session.get('enrollment_id')
    
    if role and (user_id or enrollment_id):
        from db import get_db_connection
        import psycopg2.extras
        db = None
        cursor = None
        try:
            db = get_db_connection()
            cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            if role == 'student' and enrollment_id:
                cursor.execute("SELECT profile_image FROM enrollments WHERE enrollment_id = %s", (enrollment_id,))
                row = cursor.fetchone()
                if row: img = row['profile_image']
            elif user_id:
                cursor.execute("SELECT profile_image FROM users WHERE user_id = %s", (user_id,))
                row = cursor.fetchone()
                if row: img = row['profile_image']
        except:
            pass
        finally:
            if cursor: cursor.close()
            if db: db.close()

    return dict(live_profile_image=img)


@app.context_processor
def inject_student_subjects():
    if session.get('role') == 'student':
        enrollment_id = session.get('enrollment_id')
        from db import get_db_connection
        import psycopg2.extras
        db = get_db_connection()
        cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute("SELECT section_id FROM enrollments WHERE enrollment_id = %s", (enrollment_id,))
            enroll_row = cursor.fetchone()
            if enroll_row and enroll_row['section_id']:
                cursor.execute("""
                    SELECT sub.subject_id, sub.name as subject_name
                    FROM section_teachers st
                    JOIN subjects sub ON st.subject_id = sub.subject_id
                    WHERE st.section_id = %s
                    ORDER BY sub.name
                """, (enroll_row['section_id'],))
                subjects = cursor.fetchall()
                return dict(student_global_subjects=subjects)
        except:
            pass
        finally:
            cursor.close()
            db.close()
    return dict(student_global_subjects=[])
@app.context_processor
def inject_teacher_subjects():
    if session.get('role') == 'teacher':
        user_id = session.get('user_id')
        branch_id = session.get('branch_id')
        from db import get_db_connection
        import psycopg2.extras

        db = get_db_connection()
        # FIX: Use RealDictCursor so fetchone() returns dict, not tuple
        cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            # Get the active school year for THIS branch
            cursor.execute("""
                SELECT year_id
                FROM school_years
                WHERE is_active = TRUE AND branch_id = %s
                LIMIT 1
            """, (branch_id,))
            row = cursor.fetchone()
            if not row:
                return dict(teacher_global_classes=[])
            # Now this is safe:
            year_id = row["year_id"]

            cursor.execute("""
                SELECT 
                    st.subject_id, 
                    sub.name AS subject_name,
                    s.section_id,
                    s.section_name,
                    gl.name AS grade_level_name
                FROM section_teachers st
                JOIN sections s ON st.section_id = s.section_id
                JOIN subjects sub ON st.subject_id = sub.subject_id
                JOIN grade_levels gl ON s.grade_level_id = gl.id
                WHERE st.teacher_id = %s
                  AND s.branch_id = %s
                  AND s.year_id = %s
                  AND st.is_archived = FALSE
                ORDER BY gl.display_order, s.section_name, sub.name
            """, (user_id, branch_id, year_id))

            classes = cursor.fetchall()
            return dict(teacher_global_classes=classes)
        finally:
            cursor.close()
            db.close()

    return dict(teacher_global_classes=[])


@app.context_processor
def inject_student_notifications():
    if session.get('role') == 'student':
        user_id = session.get('user_id')
        from db import get_db_connection
        import psycopg2.extras
        from datetime import timezone
        import pytz
        db = get_db_connection()
        cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            # All recent notifications (for the dropdown list — stays visible even after reading)
            cursor.execute('''
                SELECT * FROM student_notifications
                WHERE student_id = %s
                ORDER BY created_at DESC LIMIT 15
            ''', (user_id,))
            notifs = cursor.fetchall()
            ph_tz = pytz.timezone("Asia/Manila")
            for n in notifs:
                ts = n.get("created_at")
                if not ts:
                    continue
                if getattr(ts, "tzinfo", None) is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                n["created_at"] = ts.astimezone(ph_tz).replace(tzinfo=None)
            # Count only unread (for the red badge)
            unread_count = sum(1 for n in notifs if not n.get('is_read'))
            return dict(student_global_notifs=notifs, student_unread_count=unread_count)
        except:
            return dict(student_global_notifs=[], student_unread_count=0)
        finally:
            cursor.close()
            db.close()
    return dict(student_global_notifs=[])


@app.context_processor
def inject_parent_notifications():
    if session.get('role') == 'parent':
        user_id = session.get('user_id')
        from db import get_db_connection
        import psycopg2.extras
        from datetime import timezone
        import pytz
        db = get_db_connection()
        cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute('''
                SELECT * FROM parent_notifications
                WHERE parent_id = %s
                ORDER BY created_at DESC LIMIT 15
            ''', (user_id,))
            notifs = cursor.fetchall()
            ph_tz = pytz.timezone("Asia/Manila")
            for n in notifs:
                ts = n.get("created_at")
                if not ts:
                    continue
                if getattr(ts, "tzinfo", None) is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                n["created_at"] = ts.astimezone(ph_tz).replace(tzinfo=None)
            unread_count = sum(1 for n in notifs if not n.get('is_read'))
            return dict(parent_global_notifs=notifs, parent_unread_count=unread_count)
        except:
            return dict(parent_global_notifs=[], parent_unread_count=0)
        finally:
            cursor.close()
            db.close()
    return dict(parent_global_notifs=[], parent_unread_count=0)


@app.context_processor
def inject_super_admin_notifications():
    if session.get('role') == 'super_admin':
        from db import get_db_connection
        import psycopg2.extras
        from datetime import datetime, timezone
        db = get_db_connection()
        cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            alerts = []
            
            # 1. Missing Branch Code
            cursor.execute("""
                SELECT COUNT(*) as cnt FROM branches
                WHERE branch_code IS NULL OR branch_code = ''
            """)
            no_code = cursor.fetchone()
            if no_code and no_code['cnt'] > 0:
                alerts.append({
                    'title': 'Credential Gap',
                    'message': f"{no_code['cnt']} branches missing branch codes",
                    'link': url_for('super_admin.super_admin_branches'),
                    'is_read': False,
                    'created_at': datetime.now(timezone.utc)
                })

            # 2. Missing Admin
            cursor.execute("""
                SELECT COUNT(*) as cnt
                FROM branches b
                LEFT JOIN users u ON u.branch_id = b.branch_id AND u.role = 'branch_admin'
                WHERE u.user_id IS NULL
            """)
            no_admin = cursor.fetchone()
            if no_admin and no_admin['cnt'] > 0:
                alerts.append({
                    'title': 'Leadership Gap',
                    'message': f"{no_admin['cnt']} branches without administrators",
                    'link': url_for('super_admin.super_admin_branches'),
                    'is_read': False,
                    'created_at': datetime.now(timezone.utc)
                })

            # 3. Inactive Branches
            cursor.execute("""
                SELECT COUNT(*) as cnt FROM branches
                WHERE is_active = FALSE
            """)
            inactive = cursor.fetchone()
            if inactive and inactive['cnt'] > 0:
                alerts.append({
                    'title': 'System Status',
                    'message': f"{inactive['cnt']} branches are currently inactive",
                    'link': url_for('super_admin.super_admin_branches'),
                    'is_read': False,
                    'created_at': datetime.now(timezone.utc)
                })

            unread_count = len(alerts)
            return dict(super_global_notifs=alerts, super_unread_count=unread_count)
        except Exception as e:
            print(f"Error in Super Admin context processor: {e}")
            return dict(super_global_notifs=[], super_unread_count=0)
        finally:
            cursor.close()
            db.close()
    return dict(super_global_notifs=[], super_unread_count=0)


@app.context_processor
def inject_branch_admin_notifications():
    if session.get('role') == 'branch_admin':
        branch_id = session.get('branch_id')
        from db import get_db_connection
        import psycopg2.extras
        from datetime import datetime, timezone
        import pytz
        
        db = get_db_connection()
        cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            alerts = []
            ph_tz = pytz.timezone("Asia/Manila")
            now_ph = datetime.now(timezone.utc).astimezone(ph_tz).replace(tzinfo=None)
            
            # 1. Low Stock Alerts (Stock - Reserved < 10)
            cursor.execute("""
                SELECT item_name, stock_total, reserved_qty 
                FROM inventory_items 
                WHERE branch_id = %s 
                  AND is_active = TRUE 
                  AND category != 'BOOK'
                  AND (stock_total - reserved_qty) < 10
                ORDER BY (stock_total - reserved_qty) ASC
                LIMIT 10
            """, (branch_id,))
            
            low_stock_items = cursor.fetchall()
            from urllib.parse import quote
            for item in low_stock_items:
                available = item['stock_total'] - item['reserved_qty']
                safe_name = quote(item['item_name'])
                alerts.append({
                    'title': 'Low Stock Alert',
                    'message': f"Item '{item['item_name']}' is running low ({available} remaining).",
                    'link': f"/branch-admin/inventory?search={safe_name}",
                    'is_read': False,
                    'created_at': now_ph
                })
            
            unread_count = len(alerts)
            return dict(branch_global_notifs=alerts, branch_unread_count=unread_count)
        except Exception as e:
            print(f"Error in Branch Admin context processor: {e}")
            return dict(branch_global_notifs=[], branch_unread_count=0)
        finally:
            cursor.close()
            db.close()
    return dict(branch_global_notifs=[], branch_unread_count=0)

@app.context_processor
def inject_librarian_notifications():
    if session.get('role') == 'librarian':
        branch_id = session.get('branch_id')
        from db import get_db_connection
        import psycopg2.extras
        from datetime import datetime, timezone
        import pytz
        
        db = get_db_connection()
        cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            alerts = []
            ph_tz = pytz.timezone("Asia/Manila")
            now_ph = datetime.now(timezone.utc).astimezone(ph_tz).replace(tzinfo=None)
            
            # Low Stock Alerts for BOOKS (Stock - Reserved < 10)
            cursor.execute("""
                SELECT item_name, stock_total, reserved_qty 
                FROM inventory_items 
                WHERE branch_id = %s 
                  AND is_active = TRUE 
                  AND category = 'BOOK'
                  AND (stock_total - reserved_qty) < 10
                ORDER BY (stock_total - reserved_qty) ASC
                LIMIT 10
            """, (branch_id,))
            
            low_stock_items = cursor.fetchall()
            from urllib.parse import quote
            for item in low_stock_items:
                available = item['stock_total'] - item['reserved_qty']
                safe_name = quote(item['item_name'])
                alerts.append({
                    'title': 'Low Book Stock',
                    'message': f"Book '{item['item_name']}' is running low ({available} remaining).",
                    'link': f"/librarian/books?search={safe_name}",
                    'is_read': False,
                    'created_at': now_ph
                })
            
            unread_count = len(alerts)
            return dict(librarian_global_notifs=alerts, librarian_unread_count=unread_count)
        except Exception as e:
            print(f"Error in Librarian context processor: {e}")
            return dict(librarian_global_notifs=[], librarian_unread_count=0)
        finally:
            cursor.close()
            db.close()
    return dict(librarian_global_notifs=[], librarian_unread_count=0)


@app.after_request
def add_security_headers(response):
    """Add security headers for browser protection and security scans."""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    # Do not cache dynamic HTML pages to secure the 'Back' button behavior
    if "text/html" in response.headers.get("Content-Type", ""):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        
    return response


# initialize all routes (register blueprints + uploads route)
init_routes(app)


# ── Global error pages (no internal paths/stack trace for security) ──
@app.errorhandler(404)
def not_found(e):
    return (
        render_template(
            "error_page.html",
            title="Page not found",
            message="The page you are looking for does not exist.",
        ),
        404,
    )


@app.errorhandler(403)
def forbidden(e):
    return (
        render_template(
            "error_page.html",
            title="Access denied",
            message="You do not have permission to view this page.",
        ),
        403,
    )


@app.errorhandler(500)
def server_error(e):
    return (
        render_template(
            "error_page.html",
            title="Something went wrong",
            message="An error occurred. Please try again later.",
        ),
        500,
    )


@app.errorhandler(429)
def rate_limit_exceeded(e):
    return (
        render_template(
            "error_page.html",
            title="Too many attempts",
            message="Too many login attempts from your IP. Please wait a minute and try again.",
        ),
        429,
    )

@app.context_processor
def inject_active_school_year():
    branch_id = session.get("branch_id")

    if not branch_id:
        return {"active_school_year": None}

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute("""
        SELECT label 
        FROM school_years 
        WHERE is_active = TRUE AND branch_id = %s
        LIMIT 1
    """, (branch_id,))

    row = cursor.fetchone()

    cursor.close()
    db.close()

    return {"active_school_year": row[0] if row else None}

if __name__ == "__main__":
    app.run(debug=True, port=5001)

