import os
from dotenv import load_dotenv
load_dotenv()  # loads .env file locally; no effect in Railway (env vars set directly)

from flask import Flask, request, session, flash, redirect, url_for, render_template
from routes import init_routes
from db import is_branch_active
from extensions import limiter

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "liceo_secret_key_dev")
limiter.init_app(app)
# Session cookie security (panel / security scan)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
if os.getenv("FLASK_ENV") == "production" or os.getenv("RAILWAY_ENVIRONMENT"):
    app.config["SESSION_COOKIE_SECURE"] = True

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
                    fallback = url_for('registrar.dashboard')
                elif role == 'teacher':
                    fallback = url_for('teacher.teacher_dashboard')
                elif role == 'student':
                    fallback = url_for('student_portal.dashboard')
                elif role == 'librarian':
                    fallback = url_for('librarian.dashboard')
                elif role == 'parent':
                    fallback = url_for('parent.dashboard')

                return redirect(request.referrer or fallback)

@app.context_processor
def inject_is_branch_active():
    branch_id = session.get('branch_id')
    is_active = True
    if branch_id and session.get('role') != 'super_admin':
        is_active = is_branch_active(branch_id)
    return dict(is_branch_active_status=is_active)


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
def inject_student_notifications():
    if session.get('role') == 'student':
        user_id = session.get('user_id')
        from db import get_db_connection
        import psycopg2.extras
        db = get_db_connection()
        cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute('''
                SELECT n.* FROM student_notifications n
                WHERE n.student_id = %s 
                  AND (
                    n.link NOT LIKE '/student/activities/%'
                    OR NOT EXISTS (
                        SELECT 1 FROM activity_submissions subm
                        WHERE subm.student_id = n.student_id
                          AND n.link LIKE '%%/student/activities/' || subm.activity_id || '%%'
                    )
                  )
                ORDER BY n.created_at DESC LIMIT 10
            ''', (user_id,))
            notifs = cursor.fetchall()
            return dict(student_global_notifs=notifs)
        except:
            return dict(student_global_notifs=[])
        finally:
            cursor.close()
            db.close()
    return dict(student_global_notifs=[])


@app.after_request
def add_security_headers(response):
    """Add security headers for browser protection and security scans."""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
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


if __name__ == "__main__":
    app.run(debug=True, port=5001)

