from flask import Blueprint, render_template, request, session, redirect, flash, url_for
from db import get_db_connection
from werkzeug.security import generate_password_hash
import psycopg2.extras
import secrets
import string
import logging

super_admin_bp = Blueprint("super_admin", __name__)

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

def generate_password(length=8):
    """Generate a cryptographically secure random password"""
    characters = string.ascii_letters + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))


# =======================
# SUPER ADMIN DASHBOARD
# =======================
@super_admin_bp.route("/super-admin", methods=["GET", "POST"])
def super_admin_dashboard():
    if session.get("role") != "super_admin":
        return redirect(url_for("auth.login"))

    # POST: create branch + admin
    if request.method == "POST":
        branch_name = request.form.get("branch_name", "").strip()
        branch_code = (request.form.get("branch_code") or "").strip().upper()
        location = request.form.get("location", "").strip()

        if not branch_name or not location or not branch_code:
            flash("Branch name and location are required.", "error")
            return redirect(url_for("super_admin.super_admin_dashboard"))

        # Generate credentials
        username = branch_name.lower().replace(" ", "_") + "_admin"
        temp_password = generate_password()
        hashed_password = generate_password_hash(temp_password)

        db = get_db_connection()
        cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        try:
            cursor.execute("BEGIN;")

            # Check for duplicate branch names / codes
            cursor.execute("SELECT 1 FROM branches WHERE branch_name=%s", (branch_name,))
            if cursor.fetchone():
                db.rollback()
                flash("Branch name already exists.", "error")
                return redirect(url_for("super_admin.super_admin_dashboard"))

            cursor.execute("SELECT 1 FROM branches WHERE branch_code=%s", (branch_code,))
            if cursor.fetchone():
                db.rollback()
                flash("Branch code already exists.", "error")
                return redirect(url_for("super_admin.super_admin_dashboard"))

            # Insert branch and get branch_id (store branch_code)
            cursor.execute(
                "INSERT INTO branches (branch_name, location, branch_code, is_active) VALUES (%s, %s, %s, TRUE) RETURNING branch_id",
                (branch_name, location, branch_code)
            )
            branch_id = cursor.fetchone()["branch_id"]

            # Insert branch admin (require password change)
            cursor.execute(
                """INSERT INTO users (branch_id, username, password, role, require_password_change)
                   VALUES (%s, %s, %s, %s, TRUE)""",
                (branch_id, username, hashed_password, "branch_admin")
            )

            db.commit()

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
            return redirect(url_for("super_admin.super_admin_dashboard"))

        finally:
            cursor.close()
            db.close()

    # GET: show branches
    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        cursor.execute("""
            SELECT
                b.branch_id,
                b.branch_name,
                b.location,
                b.is_active,
                b.created_at,
                b.branch_code,       
                u.username as admin_username,
                u.user_id as admin_id
            FROM branches b
            LEFT JOIN users u ON u.branch_id = b.branch_id AND u.role = 'branch_admin'
            ORDER BY b.created_at DESC
        """)
        branches = cursor.fetchall()

        return render_template("super_admin_dashboard.html", branches=branches)

    except Exception as e:
        logger.error(f"Error fetching branches: {str(e)}")
        flash("Error fetching branches.", "error")
        return redirect(url_for("auth.login"))

    finally:
        cursor.close()
        db.close()
        
 # =======================
# EDIT BRANCH (super admin)
# =======================
@super_admin_bp.route("/super-admin/branches/<int:branch_id>/edit", methods=["POST"])
def super_admin_edit_branch(branch_id):
    if session.get("role") != "super_admin":
        return redirect(url_for("auth.login"))

    branch_name = (request.form.get("branch_name") or "").strip()
    branch_code = (request.form.get("branch_code") or "").strip().upper()
    location    = (request.form.get("location") or "").strip()

    if not branch_name or not branch_code or not location:
        flash("All fields (branch name, code, location) are required.", "error")
        return redirect(url_for("super_admin.super_admin_dashboard"))

    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        # Check duplicate code on a DIFFERENT branch
        cursor.execute(
            "SELECT branch_id FROM branches WHERE branch_code = %s AND branch_id != %s",
            (branch_code, branch_id)
        )
        if cursor.fetchone():
            flash(f"Branch code '{branch_code}' is already used by another branch.", "error")
            return redirect(url_for("super_admin.super_admin_dashboard"))

        cursor.execute("""
            UPDATE branches
            SET branch_name = %s,
                branch_code = %s,
                location    = %s
            WHERE branch_id = %s
        """, (branch_name, branch_code, location, branch_id))
        db.commit()
        flash(f"Branch updated! Code set to: {branch_code}", "success")

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to edit branch: {str(e)}")
        flash(f"Could not update branch: {str(e)}", "error")
    finally:
        cursor.close()
        db.close()

    return redirect(url_for("super_admin.super_admin_dashboard"))       


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
            return redirect(url_for("super_admin.super_admin_dashboard"))
        
        current_status = row[0]
        branch_name = row[1]
        new_status = not current_status
        new_status_str = 'active' if new_status else 'inactive'

        cur.execute(
            "UPDATE branches SET is_active = %s, status = %s WHERE branch_id = %s",
            (new_status, new_status_str, branch_id)
        )
        db.commit()

        action = "reactivated" if new_status else "deactivated"
        flash(f"Branch '{branch_name}' has been {action} successfully.", "success")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to toggle branch status: {str(e)}")
        flash("Failed to update branch status. Please try again.", "error")
    finally:
        try:
            cur.close()
        except Exception:
            pass
        db.close()

    return redirect(url_for("super_admin.super_admin_dashboard"))


# =======================
# SUPER ADMIN: FAQ MANAGEMENT (GENERAL FAQs = branch_id IS NULL)
# =======================
@super_admin_bp.route("/super-admin/faqs", methods=["GET", "POST"])
def superadmin_faqs():
    if session.get("role") != "super_admin":
        return redirect(url_for("auth.login"))

    message = None
    error = None

    db = get_db_connection()
    cur = db.cursor()  # tuples are fine for template faq[0], faq[1], faq[2]

    try:
        if request.method == "POST":
            question = request.form.get("question", "").strip()
            answer = request.form.get("answer", "").strip()

            if question and answer:
                try:
                    cur.execute("""
                        INSERT INTO chatbot_faqs (question, answer, branch_id)
                        VALUES (%s, %s, NULL)
                    """, (question, answer))
                    db.commit()
                    message = "General FAQ added successfully!"
                except Exception as e:
                    db.rollback()
                    logger.error(f"Error adding FAQ: {str(e)}")
                    error = "Error adding FAQ. Please try again."
            else:
                error = "Question and answer are required."

        cur.execute("""
            SELECT id, question, answer
            FROM chatbot_faqs
            WHERE branch_id IS NULL
            ORDER BY id ASC
        """)
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

    db = get_db_connection()
    cur = db.cursor()

    try:
        cur.execute("DELETE FROM chatbot_faqs WHERE id=%s AND branch_id IS NULL", (faq_id,))
        db.commit()
        flash("FAQ deleted.", "success")
    except Exception as e:
        db.rollback()
        logger.error(f"FAQ delete failed: {str(e)}")
        flash("Failed to delete FAQ.", "error")
    finally:
        try:
            cur.close()
        except Exception:
            pass
        db.close()

    return redirect(url_for("super_admin.superadmin_faqs"))


@super_admin_bp.route("/super-admin/faqs/<int:faq_id>/edit", methods=["POST"])
def superadmin_faq_edit(faq_id):
    if session.get("role") != "super_admin":
        return redirect(url_for("auth.login"))

    question = request.form.get("question", "").strip()
    answer = request.form.get("answer", "").strip()

    if not question or not answer:
        flash("Question and answer are required.", "error")
        return redirect(url_for("super_admin.superadmin_faqs"))

    db = get_db_connection()
    cur = db.cursor()

    try:
        cur.execute("""
            UPDATE chatbot_faqs
            SET question=%s, answer=%s
            WHERE id=%s AND branch_id IS NULL
        """, (question, answer, faq_id))
        db.commit()
        flash("FAQ updated.", "success")
    except Exception as e:
        db.rollback()
        logger.error(f"FAQ update failed: {str(e)}")
        flash("Failed to update FAQ.", "error")
    finally:
        try:
            cur.close()
        except Exception:
            pass
        db.close()

    return redirect(url_for("super_admin.superadmin_faqs"))


@super_admin_bp.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response
