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
            SELECT role, COUNT(*) AS cnt 
            FROM users 
            WHERE role NOT IN ('super_admin', 'branch_admin')
            AND COALESCE(status, 'active') = 'active'
            GROUP BY role
        """)
        workforce_stats = cursor.fetchall() or []
        total_staff = sum(row['cnt'] for row in workforce_stats)

        # ── Global Enrollment Funnel ──
        cursor.execute("""
            SELECT status, COUNT(*) AS cnt
            FROM enrollments
            GROUP BY status
        """)
        funnel_stats = cursor.fetchall() or []

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
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='last_login'")
        has_last_login = cursor.fetchone() is not None
        
        login_col = "u.last_login AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Manila'" if has_last_login else "NULL"

        cursor.execute(f"""
            SELECT
                b.branch_id,
                b.branch_name,
                b.is_active,
                b.branch_code,
                u.full_name AS admin_name,
                {login_col} AS last_active,
                COALESCE(e_all.cnt, 0)     AS total_students,
                COALESCE(e_pend.cnt, 0)    AS pending_count
            FROM branches b
            LEFT JOIN users u ON u.branch_id = b.branch_id AND u.role = 'branch_admin'
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
            ORDER BY total_students DESC
        """)
        branch_health = cursor.fetchall() or []
        
        top_branches = branch_health[:3]

        return render_template(
            "super_admin_dashboard.html",
            total_branches=total_branches,
            active_branches=active_branches,
            total_students=total_students,
            total_pending=total_pending,
            total_staff=total_staff,
            workforce_stats=workforce_stats,
            funnel_stats=funnel_stats,
            branch_health=branch_health,
            top_branches=top_branches,
            missing_code=missing_code,
            missing_admin=missing_admin,
            inactive_branches=inactive_branches
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
        admin_name  = request.form.get("admin_name", "").strip()
        gender      = request.form.get("gender", "").strip()

        if not branch_name or not branch_code or not location or not admin_email or not admin_name or not gender:
            flash("All fields (Branch Name, Code, Coordinates, Admin Name, Gender, Email) are required.", "error")
            return redirect(url_for("super_admin.super_admin_branches"))

        # USERNAME CONVENTION: [BRANCH_CODE]_Admin
        username      = f"{branch_code}_Admin"
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
                "INSERT INTO users (branch_id, username, password, role, email, full_name, gender, require_password_change) VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE)",
                (branch_id, username, hashed, "branch_admin", admin_email, admin_name, gender)
            )
            
            # Auto-insert active school year for new branch
            cursor.execute("SELECT label FROM school_years WHERE is_active=TRUE LIMIT 1")
            active_sy = cursor.fetchone()
            if active_sy:
                cursor.execute(
                    "INSERT INTO school_years (label, is_active, branch_id) VALUES (%s, TRUE, %s)",
                    (active_sy["label"], branch_id)
                )

            db.commit()

            db.commit()

            subject = f"Liceo Management System: Admin Credentials for {branch_name}"
            
            # Premium HTML Template
            honorific = "Mr." if gender == "Male" else "Ms."
            html_body = f"""
            <div style="font-family: 'Plus Jakarta Sans', sans-serif; background: #f8fafc; padding: 40px; border-radius: 24px; color: #0f172a; max-width: 600px; margin: 0 auto; border: 1px solid rgba(26, 58, 143, 0.1);">
                <div style="background: linear-gradient(135deg, #1a3a8f 0%, #0c2461 100%); padding: 32px; border-radius: 20px 20px 0 0; text-align: center; color: #ffffff;">
                    <h2 style="margin: 0; font-size: 24px; font-weight: 800; letter-spacing: -0.02em;">Liceo Management System</h2>
                    <p style="margin: 8px 0 0 0; opacity: 0.8; font-weight: 500;">Secure Node Deployment Protocols</p>
                </div>
                <div style="background: #ffffff; padding: 32px; border-radius: 0 0 20px 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.05);">
                    <p style="font-size: 16px; line-height: 1.6;">Hello <strong>{honorific} {admin_name}</strong>,</p>
                    <p style="font-size: 16px; line-height: 1.6;">Your administrative node for <strong>{branch_name}</strong> has been successfully initialized. Below are your secure access credentials:</p>
                    
                    <div style="background: #f1f5f9; padding: 24px; border-radius: 16px; margin: 24px 0; border: 1px dashed #cbd5e1;">
                        <div style="margin-bottom: 12px; font-size: 14px; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em;">Access Protocol</div>
                        <div style="font-size: 15px; margin-bottom: 8px;"><strong>Username:</strong> <code style="color: #1a3a8f;">{username}</code></div>
                        <div style="font-size: 15px;"><strong>Secure Key:</strong> <code style="color: #1a3a8f;">{temp_password}</code></div>
                    </div>

                    <div style="text-align: center; margin: 32px 0;">
                        <a href="https://liceolms.up.railway.app/" style="background: #facc15; color: #1a3a8f; text-decoration: none; padding: 16px 32px; border-radius: 12px; font-weight: 800; font-size: 15px; box-shadow: 0 4px 12px rgba(250, 204, 21, 0.4);">Access Dashboard</a>
                    </div>

                    <p style="font-size: 13px; color: #64748b; line-height: 1.6; font-style: italic;">Note: For security reasons, you will be required to update your "Secure Key" upon your first successful protocol authentication.</p>
                    
                    <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 32px 0;">
                    <p style="font-size: 12px; color: #94a3b8; text-align: center; margin: 0;">&copy; 2026 Liceo Management System. All rights reserved.</p>
                </div>
            </div>
            """
            body = f"Hello {honorific} {admin_name}, your credentials for {branch_name} are: Username: {username}, Password: {temp_password}. Login at https://liceolms.up.railway.app/"

            email_sent = send_email(admin_email, subject, body, html_body=html_body)
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
                u.user_id  AS admin_id,
                u.full_name AS admin_full_name,
                u.gender AS admin_gender
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
    admin_name  = (request.form.get("admin_name") or "").strip()
    gender      = (request.form.get("gender") or "").strip()

    if not branch_name or not branch_code or not admin_email or not admin_name or not gender:
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
            SET email = %s, full_name = %s, gender = %s
            WHERE branch_id = %s AND role = 'branch_admin'
        """, (admin_email, admin_name, gender, branch_id))
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
@super_admin_bp.route("/superadmin/school-years", methods=["GET", "POST"])
def superadmin_school_years():
    if "user_id" not in session or session.get("role") != "super_admin":
        return redirect(url_for("auth.login"))

    db = get_db_connection()
    cursor = db.cursor()

    if request.method == "POST":
        label = (request.form.get("label") or "").strip()
        if not label:
            flash("School Year label is required.", "error")
        else:
            try:
                # Insert this label for EVERY active branch
                cursor.execute("SELECT branch_id FROM branches WHERE is_active=TRUE")
                branches = cursor.fetchall()

                # Check if it already exists for any branch to avoid duplicates
                cursor.execute("SELECT 1 FROM school_years WHERE label=%s LIMIT 1", (label,))
                if cursor.fetchone():
                    flash(f"School Year '{label}' already exists globally.", "error")
                else:
                    for b in branches:
                        cursor.execute(
                            "INSERT INTO school_years (label, is_active, branch_id) VALUES (%s, FALSE, %s)",
                            (label, b[0])
                        )
                    db.commit()
                    flash(f"Successfully broadcasted '{label}' to all active branches.", "success")
            except Exception as e:
                db.rollback()
                flash(f"Error broadcasting school year: {e}", "error")
        return redirect(url_for("super_admin.superadmin_school_years"))

    # Display unique school years and their global active status
    cursor.execute("""
        SELECT label, bool_or(is_active) as is_active 
        FROM school_years 
        GROUP BY label 
        ORDER BY label DESC
    """)
    unique_years = cursor.fetchall()
    
    cursor.close()
    db.close()

    return render_template("superadmin_school_years.html", unique_years=unique_years)

@super_admin_bp.route("/superadmin/school-years/activate", methods=["POST"])
def superadmin_set_active_year():
    if "user_id" not in session or session.get("role") != "super_admin":
        return redirect(url_for("auth.login"))

    label = (request.form.get("label") or "").strip()
    if not label:
        flash("School Year label is required.", "error")
        return redirect(url_for("super_admin.superadmin_school_years"))

    db = get_db_connection()
    cursor = db.cursor()

    try:
        cursor.execute("BEGIN;")
        # Find the new active year label
        cursor.execute("SELECT branch_id FROM branches WHERE is_active = TRUE")
        branches = cursor.fetchall()

        for b in branches:
            branch_id = b[0]
            
            # Get old active year for this branch
            cursor.execute("SELECT year_id FROM school_years WHERE branch_id = %s AND is_active = TRUE LIMIT 1", (branch_id,))
            old = cursor.fetchone()
            old_year_id = old[0] if old else None

            # Deactivate all for this branch
            cursor.execute("UPDATE school_years SET is_active = FALSE WHERE branch_id = %s", (branch_id,))

            # Activate the new one and get its year_id
            cursor.execute("UPDATE school_years SET is_active = TRUE WHERE label = %s AND branch_id = %s RETURNING year_id", (label, branch_id))
            new = cursor.fetchone()
            new_year_id = new[0] if new else None

            if new_year_id and old_year_id and new_year_id != old_year_id:
                # Check if sections already exist for the new year
                cursor.execute("SELECT COUNT(*) FROM sections WHERE year_id = %s AND branch_id = %s", (new_year_id, branch_id))
                if cursor.fetchone()[0] == 0:
                    # Copy sections
                    cursor.execute("""
                        INSERT INTO sections (branch_id, year_id, section_name, grade_level_id, capacity)
                        SELECT branch_id, %s, section_name, grade_level_id, capacity
                        FROM sections
                        WHERE year_id = %s AND branch_id = %s
                    """, (new_year_id, old_year_id, branch_id))

                    # Copy section teachers (without the teacher assignment)
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
                    """, (new_year_id, old_year_id, branch_id))

        db.commit()
        flash(f"'{label}' is now active globally and sections were copied where needed.", "success")
    except Exception as e:
        db.rollback()
        flash(f"Error setting active school year: {e}", "error")
    finally:
        cursor.close()
        db.close()

    return redirect(url_for("super_admin.superadmin_school_years"))


@super_admin_bp.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
    response.headers["Pragma"]        = "no-cache"
    response.headers["Expires"]       = "0"
    return response