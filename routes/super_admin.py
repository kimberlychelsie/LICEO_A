from flask import Blueprint, render_template, request, session, redirect, flash, url_for
from db import get_db_connection
from werkzeug.security import generate_password_hash
import psycopg2.extras
import secrets
import string
import logging
from utils.send_email import send_email

super_admin_bp = Blueprint("super_admin", __name__)

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

def generate_password(length=8):
    characters = string.ascii_letters + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))


# =======================
# SUPER ADMIN DASHBOARD (new — stats + alerts)
# =======================
@super_admin_bp.route("/super-admin", methods=["GET"])
def super_admin_dashboard():
    if session.get("role") != "super_admin":
        return redirect(url_for("auth.login"))

    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        # ── Stats ──
        cursor.execute("SELECT COUNT(*) AS cnt FROM branches")
        total_branches = cursor.fetchone()["cnt"]

        cursor.execute("SELECT COUNT(*) AS cnt FROM branches WHERE is_active = TRUE")
        active_branches = cursor.fetchone()["cnt"]

        cursor.execute("SELECT COUNT(*) AS cnt FROM enrollments")
        total_students = cursor.fetchone()["cnt"]

        cursor.execute("SELECT COUNT(*) AS cnt FROM enrollments WHERE status = 'pending'")
        total_pending = cursor.fetchone()["cnt"]

        cursor.execute("""
            SELECT COUNT(*) AS cnt FROM users
            WHERE role NOT IN ('super_admin', 'branch_admin')
            AND COALESCE(status, 'active') = 'active'
        """)
        total_staff = cursor.fetchone()["cnt"]

        # ── Alerts ──
        cursor.execute("""
            SELECT branch_id, branch_name
            FROM branches
            WHERE branch_code IS NULL OR branch_code = ''
        """)
        missing_code = cursor.fetchall() or []

        cursor.execute("""
            SELECT b.branch_id, b.branch_name
            FROM branches b
            LEFT JOIN users u ON u.branch_id = b.branch_id AND u.role = 'branch_admin'
            WHERE u.user_id IS NULL
        """)
        missing_admin = cursor.fetchall() or []

        cursor.execute("""
            SELECT branch_id, branch_name
            FROM branches
            WHERE is_active = FALSE
        """)
        inactive_branches = cursor.fetchall() or []

        # ── Branch health table ──
        cursor.execute("""
            SELECT
                b.branch_id,
                b.branch_name,
                b.is_active,
                b.branch_code,
                COALESCE(e_all.cnt, 0)     AS total_students,
                COALESCE(e_pend.cnt, 0)    AS pending_count
            FROM branches b
            LEFT JOIN (
                SELECT branch_id, COUNT(*) AS cnt
                FROM enrollments
                GROUP BY branch_id
            ) e_all  ON e_all.branch_id  = b.branch_id
            LEFT JOIN (
                SELECT branch_id, COUNT(*) AS cnt
                FROM enrollments WHERE status = 'pending'
                GROUP BY branch_id
            ) e_pend ON e_pend.branch_id = b.branch_id
            ORDER BY b.branch_name
        """)
        branch_health = cursor.fetchall() or []

        return render_template(
            "super_admin_dashboard.html",
            total_branches=total_branches,
            active_branches=active_branches,
            total_students=total_students,
            total_pending=total_pending,
            total_staff=total_staff,
            missing_code=missing_code,
            missing_admin=missing_admin,
            inactive_branches=inactive_branches,
            branch_health=branch_health,
        )

    except Exception as e:
        logger.error(f"Dashboard error: {str(e)}")
        flash("Error loading dashboard.", "error")
        return redirect(url_for("auth.login"))
    finally:
        cursor.close()
        db.close()


# =======================
# BRANCHES PAGE (moved from old dashboard)
# =======================
@super_admin_bp.route("/super-admin/branches", methods=["GET", "POST"])
def super_admin_branches():
    if session.get("role") != "super_admin":
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        branch_name = request.form.get("branch_name", "").strip()
        branch_code = (request.form.get("branch_code") or "").strip().upper()
        location    = request.form.get("location", "").strip()
        admin_email = request.form.get("admin_email", "").strip()

        if not branch_name or not location or not branch_code or not admin_email:
            flash("Branch name, code, location, and admin email are required.", "error")
            return redirect(url_for("super_admin.super_admin_branches"))

        username      = branch_name.lower().replace(" ", "_") + "_admin"
        temp_password = generate_password()
        hashed        = generate_password_hash(temp_password)

        db = get_db_connection()
        cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute("BEGIN;")

            cursor.execute("SELECT 1 FROM branches WHERE branch_name=%s", (branch_name,))
            if cursor.fetchone():
                db.rollback()
                flash("Branch name already exists.", "error")
                return redirect(url_for("super_admin.super_admin_branches"))

            cursor.execute("SELECT 1 FROM branches WHERE branch_code=%s", (branch_code,))
            if cursor.fetchone():
                db.rollback()
                flash("Branch code already exists.", "error")
                return redirect(url_for("super_admin.super_admin_branches"))

            cursor.execute(
                "INSERT INTO branches (branch_name, location, branch_code, is_active) VALUES (%s, %s, %s, TRUE) RETURNING branch_id",
                (branch_name, location, branch_code)
            )
            branch_id = cursor.fetchone()["branch_id"]

            cursor.execute(
                "INSERT INTO users (branch_id, username, password, role, email, require_password_change) VALUES (%s, %s, %s, %s, %s, TRUE)",
                (branch_id, username, hashed, "branch_admin", admin_email)
            )
            db.commit()

            db.commit()

            subject = f"Liceo Branch Admin Credentials for {branch_name}"
            body = f"""Hello,

            Your branch admin account for {branch_name} has been created!

            Username: {username}
            Password: {temp_password}
            Login URL: https://liceolms.up.railway.app/

            Please log in and change your password immediately.

            If you have any questions, contact your super admin.

            -- The Liceo LMS Team
            """

            email_sent = send_email(admin_email, subject, body)
            if not email_sent:
                flash("Branch admin account created, but failed to send email.", "warning")

            return render_template(
                "branch_admin_created.html",
                branch_name=branch_name,
                location=location,
                username=username,
                password=temp_password
            )

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create branch/admin: {str(e)}")
            flash("Failed to create branch/admin. Please try again.", "error")
            return redirect(url_for("super_admin.super_admin_branches"))
        finally:
            cursor.close()
            db.close()

    # GET
    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cursor.execute("""
            SELECT
                b.branch_id, b.branch_name, b.location,
                b.is_active, b.created_at, b.branch_code,
                u.username AS admin_username,
                u.email AS admin_email,
                u.user_id  AS admin_id
            FROM branches b
            LEFT JOIN users u ON u.branch_id = b.branch_id AND u.role = 'branch_admin'
            ORDER BY b.created_at DESC
        """)
        branches = cursor.fetchall()
        return render_template("superadmin_branches.html", branches=branches)

    except Exception as e:
        logger.error(f"Error fetching branches: {str(e)}")
        flash("Error fetching branches.", "error")
        return redirect(url_for("super_admin.super_admin_dashboard"))
    finally:
        cursor.close()
        db.close()


# =======================
# EDIT BRANCH
# =======================
@super_admin_bp.route("/super-admin/branches/<int:branch_id>/edit", methods=["POST"])
def super_admin_edit_branch(branch_id):
    if session.get("role") != "super_admin":
        return redirect(url_for("auth.login"))

    branch_name = (request.form.get("branch_name") or "").strip()
    branch_code = (request.form.get("branch_code") or "").strip().upper()
    location    = (request.form.get("location") or "").strip()
    admin_email = (request.form.get("admin_email") or "").strip()

    if not branch_name or not branch_code or not location or not admin_email:
        flash("All fields are required.", "error")
        return redirect(url_for("super_admin.super_admin_branches"))

    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cursor.execute(
            "SELECT branch_id FROM branches WHERE branch_code = %s AND branch_id != %s",
            (branch_code, branch_id)
        )
        if cursor.fetchone():
            flash(f"Branch code '{branch_code}' is already used by another branch.", "error")
            return redirect(url_for("super_admin.super_admin_branches"))

        cursor.execute("""
            UPDATE branches
            SET branch_name = %s, branch_code = %s, location = %s
            WHERE branch_id = %s
        """, (branch_name, branch_code, location, branch_id))
        
        cursor.execute("""
            UPDATE users
            SET email = %s
            WHERE branch_id = %s AND role = 'branch_admin'
        """, (admin_email, branch_id))
        db.commit()
        flash(f"Branch updated! Code set to: {branch_code}", "success")

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to edit branch: {str(e)}")
        flash(f"Could not update branch: {str(e)}", "error")
    finally:
        cursor.close()
        db.close()

    return redirect(url_for("super_admin.super_admin_branches"))


# =======================
# TOGGLE BRANCH STATUS
# =======================
@super_admin_bp.route("/super-admin/branch/<int:branch_id>/toggle-status", methods=["POST"])
def superadmin_branch_toggle_status(branch_id):
    if session.get("role") != "super_admin":
        return redirect(url_for("auth.login"))

    db = get_db_connection()
    cur = db.cursor()
    try:
        cur.execute("BEGIN;")
        cur.execute("SELECT is_active, branch_name FROM branches WHERE branch_id = %s", (branch_id,))
        row = cur.fetchone()
        if not row:
            db.rollback()
            flash("Branch not found.", "error")
            return redirect(url_for("super_admin.super_admin_branches"))

        new_status     = not row[0]
        new_status_str = 'active' if new_status else 'inactive'

        cur.execute(
            "UPDATE branches SET is_active = %s, status = %s WHERE branch_id = %s",
            (new_status, new_status_str, branch_id)
        )
        db.commit()
        action = "reactivated" if new_status else "deactivated"
        flash(f"Branch '{row[1]}' has been {action} successfully.", "success")

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to toggle branch status: {str(e)}")
        flash("Failed to update branch status.", "error")
    finally:
        try:
            cur.close()
        except Exception:
            pass
        db.close()

    return redirect(url_for("super_admin.super_admin_branches"))


# =======================
# FAQ MANAGEMENT
# =======================
@super_admin_bp.route("/super-admin/faqs", methods=["GET", "POST"])
def superadmin_faqs():
    if session.get("role") != "super_admin":
        return redirect(url_for("auth.login"))

    message = None
    error   = None
    db  = get_db_connection()
    cur = db.cursor()

    try:
        if request.method == "POST":
            question = request.form.get("question", "").strip()
            answer   = request.form.get("answer", "").strip()
            if question and answer:
                try:
                    cur.execute(
                        "INSERT INTO chatbot_faqs (question, answer, branch_id) VALUES (%s, %s, NULL)",
                        (question, answer)
                    )
                    db.commit()
                    message = "General FAQ added successfully!"
                except Exception as e:
                    db.rollback()
                    error = "Error adding FAQ. Please try again."
            else:
                error = "Question and answer are required."

        cur.execute("SELECT id, question, answer FROM chatbot_faqs WHERE branch_id IS NULL ORDER BY id ASC")
        faqs = cur.fetchall() or []
        return render_template("superadmin_faqs.html", faqs=faqs, message=message, error=error)

    finally:
        try:
            cur.close()
        except Exception:
            pass
        db.close()


@super_admin_bp.route("/super-admin/faqs/<int:faq_id>/delete", methods=["POST"])
def superadmin_faq_delete(faq_id):
    if session.get("role") != "super_admin":
        return redirect(url_for("auth.login"))
    db  = get_db_connection()
    cur = db.cursor()
    try:
        cur.execute("DELETE FROM chatbot_faqs WHERE id=%s AND branch_id IS NULL", (faq_id,))
        db.commit()
        flash("FAQ deleted.", "success")
    except Exception as e:
        db.rollback()
        flash("Failed to delete FAQ.", "error")
    finally:
        try: cur.close()
        except Exception: pass
        db.close()
    return redirect(url_for("super_admin.superadmin_faqs"))


@super_admin_bp.route("/super-admin/faqs/<int:faq_id>/edit", methods=["POST"])
def superadmin_faq_edit(faq_id):
    if session.get("role") != "super_admin":
        return redirect(url_for("auth.login"))
    question = request.form.get("question", "").strip()
    answer   = request.form.get("answer", "").strip()
    if not question or not answer:
        flash("Question and answer are required.", "error")
        return redirect(url_for("super_admin.superadmin_faqs"))
    db  = get_db_connection()
    cur = db.cursor()
    try:
        cur.execute(
            "UPDATE chatbot_faqs SET question=%s, answer=%s WHERE id=%s AND branch_id IS NULL",
            (question, answer, faq_id)
        )
        db.commit()
        flash("FAQ updated.", "success")
    except Exception as e:
        db.rollback()
        flash("Failed to update FAQ.", "error")
    finally:
        try: cur.close()
        except Exception: pass
        db.close()
    return redirect(url_for("super_admin.superadmin_faqs"))


@super_admin_bp.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
    response.headers["Pragma"]        = "no-cache"
    response.headers["Expires"]       = "0"
    return response