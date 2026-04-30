from flask import Blueprint, render_template, session, redirect, request, flash, url_for, jsonify
from db import get_db_connection, is_branch_active
from werkzeug.security import generate_password_hash
import secrets
import string
import logging
import psycopg2.extras
import json
from utils.send_email import send_email
from flask import abort
import re
from datetime import datetime
import pytz

# Setup logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

registrar_bp = Blueprint("registrar", __name__)

def generate_password(length=8):
    characters = string.ascii_letters + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))

def is_valid_email(email):
    # Strict email validation: username@domain.com
    # Username: a-z, 0-9, ., _, -
    # Explicitly block #, %, &, spaces
    if not email:
        return False
    import re
    email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(email_regex, email))


# ══════════════════════════════════════════
# HOME — Overview Dashboard
# ══════════════════════════════════════════

@registrar_bp.route("/registrar")
def registrar_home():
    if session.get("role") != "registrar":
        return redirect("/")

    branch_id = session.get("branch_id")
    if not branch_id:
        flash("Missing branch in session. Please login again.", "error")
        return redirect("/logout")

    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cursor.execute("""
            SELECT year_id
            FROM school_years
            WHERE branch_id = %s AND is_active = TRUE
            LIMIT 1
        """, (branch_id,))
        active_year = cursor.fetchone()
        active_year_id = active_year["year_id"] if active_year else None

        if not active_year_id:
            flash("No active school year found for this branch.", "warning")
            return render_template(
                "registrar_home.html",
                pending_count=0,
                enrolled_count=0,
                no_section_count=0,
                reenroll_count=0,
                no_account_count=0,
                recent_pending=[],
                enrollment_by_grade=[],
            )

        # ✅ All stats in ONE query
        cursor.execute("""
            SELECT
                COUNT(*) FILTER (WHERE status = 'pending')                                     AS pending_count,
                COUNT(*) FILTER (WHERE status IN ('enrolled','approved','open_for_enrollment')) AS enrolled_count,
                COUNT(*) FILTER (WHERE status IN ('enrolled','approved','open_for_enrollment')
                                   AND section_id IS NULL)                                     AS no_section_count,
                COUNT(*) FILTER (WHERE status = 'open_for_enrollment')                         AS reenroll_count
            FROM enrollments
            WHERE branch_id = %s
              AND year_id = %s
        """, (branch_id, active_year_id))
        stats = cursor.fetchone()

        # ✅ no_account_count still needs subquery — separate but single query
        cursor.execute("""
            SELECT COUNT(*) AS cnt FROM enrollments e
            WHERE e.branch_id = %s
              AND e.year_id = %s
              AND e.status IN ('enrolled','approved','open_for_enrollment')
              AND NOT EXISTS (
                  SELECT 1 FROM student_accounts sa WHERE sa.enrollment_id = e.enrollment_id
              )
        """, (branch_id, active_year_id))
        no_account_count = cursor.fetchone()["cnt"]

        # ✅ Recent 5 pending enrollments for preview
        cursor.execute("""
            SELECT student_name, grade_level, created_at, branch_enrollment_no AS display_no
            FROM enrollments
            WHERE branch_id=%s AND year_id=%s AND status='pending'
            ORDER BY created_at DESC
            LIMIT 5
        """, (branch_id, active_year_id))
        recent_pending = cursor.fetchall()
        
        # ✅ Enrollment by Grade for Chart
        cursor.execute("""
            SELECT grade_level, COUNT(*) AS student_count
            FROM enrollments
            WHERE branch_id = %s AND year_id = %s
              AND status IN ('enrolled', 'approved', 'open_for_enrollment')
            GROUP BY grade_level
            ORDER BY grade_level
        """, (branch_id, active_year_id))
        enrollment_by_grade = cursor.fetchall()

        return render_template(
            "registrar_home.html",
            pending_count    = stats["pending_count"],
            enrolled_count   = stats["enrolled_count"],
            no_section_count = stats["no_section_count"],
            reenroll_count   = stats["reenroll_count"],
            no_account_count = no_account_count,
            recent_pending   = recent_pending,
            enrollment_by_grade = enrollment_by_grade,
        )
    finally:
        cursor.close()
        db.close()


# ══════════════════════════════════════════
# ENROLLMENTS — Full Tab Table
# ══════════════════════════════════════════
@registrar_bp.route("/registrar/enrollments", methods=["GET", "POST"])
def registrar_enrollments():
    if session.get("role") != "registrar":
        return redirect("/")

    branch_id = session.get("branch_id")
    if not branch_id:
        flash("Missing branch in session. Please login again.", "error")
        return redirect("/logout")

    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        # --- ACTIVE YEAR (for safe actions) ---
        cursor.execute("""
            SELECT year_id
            FROM school_years
            WHERE branch_id = %s AND is_active = TRUE
            LIMIT 1
        """, (branch_id,))
        active_year = cursor.fetchone()
        active_year_id = active_year["year_id"] if active_year else None
        if not active_year_id:
            flash("No active school year found for this branch.", "error")
            return redirect("/registrar")

        # --- YEAR SWITCHER & PAGINATION (view context) ---
        selected_year_id = request.args.get("year_id", type=int) or active_year_id
        
        limit = 10
        p_new = request.args.get("p_new", type=int, default=1)
        if p_new < 1: p_new = 1
        offset_new = (p_new - 1) * limit
        
        p_enrolled = request.args.get("p_enrolled", type=int, default=1)
        if p_enrolled < 1: p_enrolled = 1
        offset_enrolled = (p_enrolled - 1) * limit

        # SEARCH QUERIES
        q_new = (request.args.get("q_new") or "").strip()
        q_enrolled = (request.args.get("q_enrolled") or "").strip()

        # dropdown data: active + inactive
        cursor.execute("""
            SELECT year_id, label, is_active
            FROM school_years
            WHERE branch_id = %s
            ORDER BY label DESC
        """, (branch_id,))
        all_school_years = cursor.fetchall()

        # can user modify on this page?
        can_modify = (selected_year_id == active_year_id)

        # Keep status consistent: once section is assigned, approved -> enrolled (ACTIVE YEAR ONLY)
        cursor.execute("""
            UPDATE enrollments
            SET status = 'enrolled'
            WHERE branch_id = %s
              AND year_id = %s
              AND status = 'approved'
              AND section_id IS NOT NULL
        """, (branch_id, active_year_id))
        db.commit()

        # --- POST actions: ACTIVE YEAR ONLY ---
        if request.method == "POST":
            if not can_modify:
                flash("You can only approve/reject enrollments in the ACTIVE school year.", "error")
                return redirect(url_for("registrar.registrar_enrollments", year_id=selected_year_id))

            enrollment_id = request.form.get("enrollment_id")
            action = request.form.get("action")
            rejection_reason = (request.form.get("rejection_reason") or "").strip()

            if not enrollment_id or action not in ("approved", "rejected"):
                flash("Invalid action.", "error")
                return redirect(url_for("registrar.registrar_enrollments", year_id=selected_year_id))

            if action == "rejected" and not rejection_reason:
                flash("Please provide a rejection reason.", "error")
                return redirect(f"/registrar/enrollment/{enrollment_id}#reject")

            if action == "rejected":
                cursor.execute(
                    """
                    UPDATE enrollments
                    SET status=%s, rejection_reason=%s, rejected_at=NOW()
                    WHERE enrollment_id=%s AND branch_id=%s AND year_id=%s
                    """,
                    (action, rejection_reason, enrollment_id, branch_id, active_year_id),
                )
            else:
                cursor.execute(
                    """
                    UPDATE enrollments
                    SET status=%s, rejection_reason=NULL, rejected_at=NULL
                    WHERE enrollment_id=%s AND branch_id=%s AND year_id=%s
                    """,
                    (action, enrollment_id, branch_id, active_year_id),
                )

            if cursor.rowcount == 0:
                db.rollback()
                flash("Enrollment not found for your branch.", "error")
                return redirect(url_for("registrar.registrar_enrollments", year_id=selected_year_id))

            db.commit()
            cursor.execute(
                "SELECT branch_enrollment_no AS display_no FROM enrollments WHERE enrollment_id=%s",
                (enrollment_id,)
            )
            disp_row = cursor.fetchone()
            display_no = disp_row["display_no"] if disp_row else "???"
            # ─────── SEND EMAIL ON REJECTION ───────
            if action == "rejected":
                try:
                    cursor.execute("""
                        SELECT e.student_name, e.email, e.guardian_email, e.branch_enrollment_no, b.branch_name
                        FROM enrollments e
                        JOIN branches b ON e.branch_id = b.branch_id
                        WHERE e.enrollment_id = %s
                    """, (enrollment_id,))
                    student_data = cursor.fetchone()
                    
                    if student_data:
                        target_email = student_data["email"] or student_data["guardian_email"]
                        if target_email:
                            branch_name = student_data["branch_name"]
                            student_name = student_data["student_name"]
                            display_no = student_data["branch_enrollment_no"]
                            
                            subject = f"Enrollment Update - Action Required ({branch_name})"
                            
                            body = (
                                f"Action Required: Enrollment Correction\n\n"
                                f"Hello {student_name},\n"
                                f"Your enrollment application for {branch_name} requires correction.\n\n"
                                f"Reason: {rejection_reason}\n\n"
                                f"Please visit the tracking page at https://www.liceo-lms.com/track to fix your application."
                            )
                            
                            html_body = f"""
                            <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 600px; margin: 20px auto; border: 1px solid #e0e0e0; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.05);">
                                <div style="background-color: #991b1b; padding: 30px; text-align: center; color: white;">
                                    <h1 style="margin: 0; font-size: 24px; font-weight: 700;">Action Required</h1>
                                    <p style="margin: 5px 0 0; opacity: 0.9;">Enrollment Application Update</p>
                                </div>
                                <div style="padding: 40px; color: #334155; line-height: 1.6;">
                                    <p style="font-size: 16px;">Hello <strong>{student_name}</strong>,</p>
                                    <p style="font-size: 16px;">Your enrollment application (ID: <strong>{display_no}</strong>) at <strong>{branch_name}</strong> requires your attention before it can be approved.</p>
                                    
                                    <div style="background-color: #fef2f2; border-left: 4px solid #ef4444; padding: 20px; margin: 25px 0;">
                                        <p style="margin: 0 0 8px 0; font-size: 14px; color: #991b1b; font-weight: 800; text-transform: uppercase;">Message from Registrar:</p>
                                        <p style="margin: 0; font-size: 16px; color: #1e293b; font-weight: 500;">{rejection_reason}</p>
                                    </div>

                                    <p style="font-size: 16px;">Please log in to the tracking portal to update your information or re-upload the necessary documents.</p>
                                    
                                    <div style="text-align: center; margin-top: 30px;">
                                        <a href="https://www.liceo-lms.com/track" 
                                           style="display: inline-block; padding: 14px 28px; background-color: #1a2a4e; color: white; text-decoration: none; border-radius: 8px; font-weight: 700; font-size: 16px;">
                                            Fix Application &rarr;
                                        </a>
                                    </div>
                                </div>
                                <div style="background-color: #f1f5f9; padding: 20px; text-align: center; font-size: 12px; color: #94a3b8;">
                                    &copy; 2026 LiceoLMS - Liceo de Majayjay System
                                </div>
                            </div>
                            """
                            send_email(target_email, subject, body, html_body=html_body)
                except Exception as email_err:
                    logger.error(f"Failed to send rejection email: {str(email_err)}")

            flash(
                f"Enrollment #{display_no} {'approved' if action == 'approved' else 'notified for correction'}.",
                "success" if action == "approved" else "warning"
            )

        # --- NEW enrollments list (VIEW selected year) with Pagination ---
        new_where = "e.branch_id=%s AND e.year_id=%s AND e.status IN ('pending', 'rejected')"
        new_params = [branch_id, selected_year_id]
        if q_new:
            new_where += " AND (e.student_name ILIKE %s OR CAST(e.branch_enrollment_no AS TEXT) ILIKE %s)"
            new_params.extend([f"%{q_new}%", f"%{q_new}%"])

        cursor.execute(f"SELECT COUNT(DISTINCT e.enrollment_id) FROM enrollments e WHERE {new_where}", tuple(new_params))
        total_new = cursor.fetchone()["count"]
        total_pages_new = (total_new + limit - 1) // limit

        new_query_params = new_params + [limit, offset_new]
        cursor.execute(f"""
            SELECT e.*,
                   e.branch_enrollment_no AS display_no,
                   COALESCE(
                       json_agg(
                           json_build_object(
                               'file_name', d.file_name,
                               'file_path', d.file_path,
                               'document_type', d.doc_type
                           )
                       ) FILTER (WHERE d.doc_id IS NOT NULL),
                       '[]'
                   ) AS documents
            FROM enrollments e
            LEFT JOIN enrollment_documents d ON d.enrollment_id = e.enrollment_id
            WHERE {new_where}
            GROUP BY e.enrollment_id
            ORDER BY e.branch_enrollment_no ASC NULLS LAST, e.created_at DESC
            LIMIT %s OFFSET %s
        """, tuple(new_query_params))
        new_enrollments_raw = cursor.fetchall()

        new_enrollments = []
        for e in new_enrollments_raw:
            e = dict(e)
            if isinstance(e["documents"], str):
                e["documents"] = json.loads(e["documents"])
            new_enrollments.append(e)

        # --- ENROLLED students list (VIEW selected year) with Pagination ---
        enrolled_where = "e.branch_id=%s AND e.year_id=%s AND e.status IN ('enrolled', 'open_for_enrollment', 'approved')"
        enrolled_params = [branch_id, selected_year_id]
        if q_enrolled:
            enrolled_where += " AND (e.student_name ILIKE %s OR CAST(e.branch_enrollment_no AS TEXT) ILIKE %s)"
            enrolled_params.extend([f"%{q_enrolled}%", f"%{q_enrolled}%"])

        cursor.execute(f"SELECT COUNT(*) FROM enrollments e WHERE {enrolled_where}", tuple(enrolled_params))
        total_enrolled = cursor.fetchone()["count"]
        total_pages_enrolled = (total_enrolled + limit - 1) // limit

        enrolled_query_params = enrolled_params + [limit, offset_enrolled]
        cursor.execute(f"""
            SELECT e.*,
                   e.branch_enrollment_no AS display_no,
                   s.section_name,
                   CASE WHEN sa.enrollment_id IS NOT NULL THEN TRUE ELSE FALSE END AS has_student_account,
                   CASE WHEN ps.student_id   IS NOT NULL THEN TRUE ELSE FALSE END AS has_parent_account,
                   u.username AS parent_username,
                   -- Correlated subquery: find existing parent account from a sibling enrollment
                   -- with the same guardian_email (returns at most 1 row — no duplication)
                   (SELECT ps2.parent_id
                    FROM enrollments e2
                    JOIN parent_student ps2 ON ps2.student_id = e2.enrollment_id
                    WHERE e.guardian_email IS NOT NULL
                      AND LOWER(e2.guardian_email) = LOWER(e.guardian_email)
                      AND e2.enrollment_id <> e.enrollment_id
                    LIMIT 1) AS existing_parent_user_id,
                   (SELECT u2.username
                    FROM enrollments e2
                    JOIN parent_student ps2 ON ps2.student_id = e2.enrollment_id
                    JOIN users u2           ON u2.user_id     = ps2.parent_id
                    WHERE e.guardian_email IS NOT NULL
                      AND LOWER(e2.guardian_email) = LOWER(e.guardian_email)
                      AND e2.enrollment_id <> e.enrollment_id
                    LIMIT 1) AS existing_parent_username
            FROM enrollments e
            LEFT JOIN sections s          ON s.section_id    = e.section_id
            LEFT JOIN student_accounts sa ON sa.enrollment_id = e.enrollment_id
            LEFT JOIN parent_student ps   ON ps.student_id   = e.enrollment_id
            LEFT JOIN users u             ON u.user_id        = ps.parent_id
            WHERE {enrolled_where}
            ORDER BY e.grade_level ASC, e.student_name ASC
            LIMIT %s OFFSET %s
        """, tuple(enrolled_query_params))
        enrolled_students = cursor.fetchall()

        cursor.execute("SELECT name FROM grade_levels WHERE branch_id = %s AND name NOT IN ('Grade 11', 'Grade 12') ORDER BY display_order", (branch_id,))
        grade_levels = [row["name"] for row in cursor.fetchall()]

        # Re-enrollment open should only consider ACTIVE year data (otherwise confusing)
        reenrollment_open = False
        if can_modify:
            reenrollment_open = any(e["status"] == "open_for_enrollment" for e in enrolled_students)

        # Section options stay ACTIVE year only (since assigning sections is an active-year operation)
        cursor.execute("""
            SELECT s.section_id, s.section_name, g.name AS grade_level_name,
                   CONCAT(g.name, ' — ', s.section_name) AS section_display
            FROM sections s
            JOIN grade_levels g ON g.id = s.grade_level_id
            JOIN school_years sy ON sy.year_id = s.year_id
            WHERE s.branch_id = %s
              AND sy.branch_id = %s
              AND sy.is_active = TRUE
            ORDER BY g.name, s.section_name
        """, (branch_id, branch_id))
        section_options = cursor.fetchall()

        is_branch_active_status = is_branch_active(branch_id)

        return render_template(
            "registrar_dashboard.html",
            new_enrollments=new_enrollments,
            enrolled_students=enrolled_students,
            grade_levels=grade_levels,
            reenrollment_open=reenrollment_open,
            section_options=section_options,
            is_branch_active_status=is_branch_active_status,

            # NEW template vars for year switcher
            all_school_years=all_school_years,
            selected_year_id=selected_year_id,
            active_year_id=active_year_id,
            can_modify=can_modify,

            # PAGINATION
            total_pages_new=total_pages_new,
            current_page_new=p_new,
            total_new=total_new,
            total_pages_enrolled=total_pages_enrolled,
            current_page_enrolled=p_enrolled,
            total_enrolled=total_enrolled,

            # SEARCH QUERIES
            q_new=q_new,
            q_enrolled=q_enrolled,
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Registrar enrollments error: {str(e)}")
        flash("Something went wrong. Please try again.", "error")
        return redirect("/registrar")
    finally:
        cursor.close()
        db.close()


# ══════════════════════════════════════════
# ENROLLMENT DETAIL
# ══════════════════════════════════════════

@registrar_bp.route("/registrar/enrollment/<int:enrollment_id>", methods=["GET", "POST"])
def enrollment_detail(enrollment_id):
    if session.get("role") != "registrar":
        return redirect("/")

    branch_id = session.get("branch_id")
    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        if request.method == "POST":
            EDITABLE_FIELDS = [
                "student_name", "grade_level", "gender", "dob", "birthplace",
                "lrn", "address", "contact_number", "email",
                "guardian_name", "guardian_contact", "guardian_email",
                "father_name", "father_contact", "father_occupation",
                "mother_name", "mother_contact", "mother_occupation",
                "previous_school", "enroll_type", "remarks",
            ]
            sets = []
            vals = []
            for f in EDITABLE_FIELDS:
                raw = request.form.get(f)
                if raw is not None:
                    val = raw.strip() or None
                    # ── EMAIL VALIDATION ──
                    if f in ["email", "guardian_email"] and val:
                        if not is_valid_email(val):
                            flash(f"The email address '{val}' is invalid. Please follow the correct format (e.g., name@domain.com) and avoid special characters like # % &.", "error")
                            return redirect(request.url)

                    sets.append(f"{f} = %s")
                    vals.append(val)

            if sets:
                vals.extend([enrollment_id, branch_id])
                cursor.execute(
                    f"UPDATE enrollments SET {', '.join(sets)} WHERE enrollment_id = %s AND branch_id = %s",
                    vals,
                )
                db.commit()
                flash("Enrollment details updated!", "success")
            return redirect("/registrar/enrollments")

        cursor.execute("""
            SELECT e.*, s.section_name, sy.label AS school_year_label
            FROM enrollments e
            LEFT JOIN sections s ON s.section_id = e.section_id
            LEFT JOIN school_years sy ON sy.year_id = e.year_id
            WHERE e.enrollment_id = %s AND e.branch_id = %s
        """, (enrollment_id, branch_id))
        enrollment = cursor.fetchone()

        if not enrollment:
            flash("Enrollment not found.", "error")
            return redirect("/registrar/enrollments")

        cursor.execute("SELECT * FROM enrollment_documents WHERE enrollment_id = %s", (enrollment_id,))
        documents = cursor.fetchall()

        cursor.execute("SELECT name FROM grade_levels WHERE branch_id = %s AND name NOT IN ('Grade 11', 'Grade 12') ORDER BY display_order", (branch_id,))
        grade_levels = [row["name"] for row in cursor.fetchall()]

        return render_template(
            "registrar_enrollment_detail.html",
            enrollment=enrollment,
            documents=documents,
            grade_levels=grade_levels,
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Enrollment detail error: {str(e)}")
        flash(f"Error: {str(e)}", "error")
        return redirect(f"/registrar/enrollment/{enrollment_id}")
    finally:
        cursor.close()
        db.close()


# ══════════════════════════════════════════
# TOGGLE RE-ENROLLMENT
# ══════════════════════════════════════════

@registrar_bp.route("/registrar/toggle-reenrollment", methods=["POST"])
def toggle_reenrollment():
    if session.get("role") != "registrar":
        return redirect("/")

    branch_id = session.get("branch_id")
    if not branch_id:
        flash("Missing branch in session.", "error")
        return redirect("/logout")

    action = request.form.get("action")
    if action not in ("open", "close"):
        flash("Invalid action.", "error")
        return redirect("/registrar/enrollments")

    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        if action == "open":
            cursor.execute("""
                UPDATE enrollments SET status = 'open_for_enrollment'
                WHERE branch_id = %s AND status IN ('enrolled', 'approved')
            """, (branch_id,))
            count = cursor.rowcount
            db.commit()
            flash(f"Re-enrollment opened for {count} student(s).", "success")
        else:
            cursor.execute("""
                UPDATE enrollments SET status = 'enrolled'
                WHERE branch_id = %s AND status = 'open_for_enrollment'
            """, (branch_id,))
            count = cursor.rowcount
            db.commit()
            flash(f"Re-enrollment closed for {count} student(s).", "warning")
    except Exception as e:
        db.rollback()
        logger.error(f"Toggle re-enrollment error: {str(e)}")
        flash("Something went wrong. Please try again.", "error")
    finally:
        cursor.close()
        db.close()

    return redirect("/registrar/enrollments#enrolled")


# ══════════════════════════════════════════
# CREATE STUDENT ACCOUNT
# ══════════════════════════════════════════

@registrar_bp.route("/registrar/create-student-account/<int:enrollment_id>", methods=["POST"])
def create_student_account(enrollment_id):
    if session.get("role") != "registrar":
        return redirect("/")

    branch_id = session.get("branch_id")
    if not branch_id:
        flash("Missing branch in session. Please login again.", "error")
        return redirect("/logout")

    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cursor.execute("""
            SELECT * FROM enrollments
            WHERE enrollment_id=%s AND branch_id=%s AND status IN ('approved', 'enrolled', 'open_for_enrollment')
        """, (enrollment_id, branch_id))
        enrollment = cursor.fetchone()

        if not enrollment:
            flash("Enrollment not found or not approved", "error")
            return redirect("/registrar/enrollments")

        cursor.execute("SELECT 1 FROM student_accounts WHERE enrollment_id=%s", (enrollment_id,))
        if cursor.fetchone():
            flash("Student account already exists for this enrollment", "warning")
            return redirect("/registrar/enrollments")

        cursor.execute("SELECT branch_code FROM branches WHERE branch_id=%s", (branch_id,))
        brow = cursor.fetchone()
        branch_code = (brow["branch_code"] if brow and brow.get("branch_code") else "").strip().upper() or f"B{branch_id}"

        branch_no = enrollment.get("branch_enrollment_no") or enrollment_id
        try:
            branch_no_str = f"{int(branch_no):04d}"
        except Exception:
            branch_no_str = str(branch_no)

        username = f"{branch_code}_{branch_no_str}"
        temp_password = generate_password()
        hashed_password = generate_password_hash(temp_password)

        try:
            cursor.execute("""
                INSERT INTO student_accounts
                  (enrollment_id, branch_id, username, password, is_active, require_password_change, email)
                VALUES (%s, %s, %s, %s, TRUE, TRUE, %s)
            """, (enrollment_id, enrollment["branch_id"], username, hashed_password, enrollment.get("email")))
            db.commit()

            section_id = request.form.get("section_id", "").strip()
            if section_id and section_id.isdigit():
                try:
                    cursor.execute("""
                        SELECT s.section_id FROM sections s
                        JOIN grade_levels g ON s.grade_level_id = g.id
                        WHERE s.section_id = %s AND s.branch_id = %s AND g.name ILIKE %s
                    """, (int(section_id), branch_id, enrollment.get("grade_level", "")))
                    if cursor.fetchone():
                        cursor.execute("""
                            UPDATE enrollments e
                            SET section_id = s.section_id,
                                year_id = s.year_id,
                                status = CASE
                                    WHEN e.status = 'approved' THEN 'enrolled'
                                    ELSE e.status
                                END
                            FROM sections s
                            WHERE e.enrollment_id = %s
                            AND e.branch_id = %s
                            AND s.section_id = %s
                            AND s.branch_id = %s
                        """, (enrollment_id, branch_id, int(section_id), branch_id))
                        db.commit()
                except Exception as e:
                    db.rollback()
                    logger.warning(f"Section assign failed (non-fatal): {str(e)}")

            # ─────── SEND EMAIL WITH CREDENTIALS ───────
            student_email = enrollment.get("email")
            if student_email:
                subject = f"Enrollment Approved & Account Credentials - {enrollment.get('student_name')}"
                
                body = (
                    f"Congratulations! Your enrollment is approved.\n\n"
                    f"Hello {enrollment.get('student_name')},\n"
                    f"Your student account has been created.\n\n"
                    f"Username: {username}\n"
                    f"Temporary Password: {temp_password}\n\n"
                    f"Login at: https://www.liceo-lms.com/"
                )

                html_body = f"""
                <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 600px; margin: 20px auto; border: 1px solid #e0e0e0; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.05);">
                    <div style="background-color: #1a2a4e; padding: 40px; text-align: center; color: white;">
                        <div style="font-size: 48px; margin-bottom: 10px;">🎉</div>
                        <h1 style="margin: 0; font-size: 28px; font-weight: 800;">Congratulations!</h1>
                        <p style="margin: 5px 0 0; opacity: 0.9; font-size: 16px;">Your Enrollment is Approved</p>
                    </div>
                    <div style="padding: 40px; color: #334155; line-height: 1.6;">
                        <p style="font-size: 16px;">Hello <strong>{enrollment.get('student_name')}</strong>,</p>
                        <p style="font-size: 16px;">We are pleased to inform you that your enrollment has been approved. Your student account is now ready for use.</p>
                        
                        <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 25px; margin: 30px 0;">
                            <h3 style="margin: 0 0 15px 0; font-size: 14px; text-transform: uppercase; color: #64748b; letter-spacing: 1px;">Your Login Credentials</h3>
                            <div style="margin-bottom: 15px;">
                                <span style="display: block; font-size: 12px; color: #94a3b8;">Username</span>
                                <span style="font-size: 18px; font-weight: 700; color: #1e293b;">{username}</span>
                            </div>
                            <div>
                                <span style="display: block; font-size: 12px; color: #94a3b8;">Temporary Password</span>
                                <span style="font-size: 18px; font-weight: 700; color: #1e293b;">{temp_password}</span>
                            </div>
                        </div>

                        <div style="text-align: center; margin-top: 30px;">
                            <a href="https://www.liceo-lms.com/login" 
                               style="display: inline-block; padding: 16px 32px; background-color: #1a2a4e; color: white; text-decoration: none; border-radius: 8px; font-weight: 700; font-size: 16px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                                Log In to Portal &rarr;
                            </a>
                        </div>
                        
                        <p style="font-size: 13px; color: #94a3b8; margin-top: 30px; text-align: center;">
                            Note: You will be required to change your password upon your first login.
                        </p>
                    </div>
                    <div style="background-color: #f1f5f9; padding: 20px; text-align: center; font-size: 12px; color: #94a3b8;">
                        &copy; 2026 LiceoLMS - Liceo de Majayjay System
                    </div>
                </div>
                """
                send_email(student_email, subject, body, html_body=html_body)

            flash(f"Student account for {enrollment.get('student_name')} created! Credentials sent to {student_email}.", "success")
            return redirect("/registrar/enrollments")
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create student account: {str(e)}")
            flash("Failed to create student account. Please try again.", "error")
            return redirect("/registrar/enrollments")

    except Exception as e:
        db.rollback()
        logger.error(f"Create student account error: {str(e)}")
        flash("Something went wrong while creating student account.", "error")
        return redirect("/registrar/enrollments")
    finally:
        cursor.close()
        db.close()


# ══════════════════════════════════════════
# CREATE PARENT ACCOUNT
# ══════════════════════════════════════════

@registrar_bp.route("/registrar/create-parent-account/<int:enrollment_id>", methods=["POST"])
def create_parent_account(enrollment_id):
    if session.get("role") != "registrar":
        return redirect("/")

    branch_id = session.get("branch_id")
    if not branch_id:
        flash("Missing branch in session. Please login again.", "error")
        return redirect("/logout")

    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cursor.execute("""
            SELECT * FROM enrollments
            WHERE enrollment_id=%s AND branch_id=%s AND status IN ('approved', 'enrolled', 'open_for_enrollment')
        """, (enrollment_id, branch_id))
        enrollment = cursor.fetchone()

        if not enrollment:
            flash("Enrollment not found or not approved", "error")
            return redirect("/registrar/enrollments")

        cursor.execute("""
            SELECT ps.*, u.username FROM parent_student ps
            JOIN users u ON ps.parent_id = u.user_id
            WHERE ps.student_id = %s
        """, (enrollment_id,))
        existing_parent = cursor.fetchone()

        if existing_parent:
            flash(f"Parent account already exists (Username: {existing_parent['username']})", "warning")
            return redirect("/registrar/enrollments")

        cursor.execute("SELECT branch_code FROM branches WHERE branch_id=%s", (branch_id,))
        brow = cursor.fetchone()
        branch_code = (brow["branch_code"] if brow and brow.get("branch_code") else "").strip().upper() or f"B{branch_id}"

        # ── Safety net: check if another enrollment with the same guardian_email already has a parent account ──
        guardian_email = (enrollment.get("guardian_email") or "").strip().lower()
        if guardian_email:
            cursor.execute("""
                SELECT u.user_id, u.username
                FROM enrollments e_sib
                JOIN parent_student ps_sib ON ps_sib.student_id = e_sib.enrollment_id
                JOIN users u               ON u.user_id          = ps_sib.parent_id
                WHERE LOWER(e_sib.guardian_email) = %s
                  AND e_sib.enrollment_id <> %s
                LIMIT 1
            """, (guardian_email, enrollment_id))
            existing_by_email = cursor.fetchone()
            if existing_by_email:
                cursor.execute("""
                    INSERT INTO parent_student (parent_id, student_id, relationship)
                    VALUES (%s, %s, 'guardian')
                    ON CONFLICT DO NOTHING
                """, (existing_by_email["user_id"], enrollment_id))
                db.commit()
                flash(
                    f"A parent account for this guardian email already exists "
                    f"('{existing_by_email['username']}'). "
                    f"Student was linked to that account instead of creating a duplicate.",
                    "success"
                )
                return redirect("/registrar/enrollments#enrolled")

        cursor.execute("""
            SELECT COUNT(*) AS cnt FROM users
            WHERE role='parent' AND branch_id=%s AND username ILIKE %s
        """, (branch_id, f"{branch_code}_Parent%"))
        prow = cursor.fetchone() or {}
        next_no = (prow.get("cnt") or 0) + 1

        username = f"{branch_code}_Parent{next_no}"
        temp_password = generate_password()
        hashed_password = generate_password_hash(temp_password)

        try:
            parent_email = enrollment.get("guardian_email") or enrollment.get("email")
            cursor.execute("""
                INSERT INTO users (username, password, role, branch_id, require_password_change, email)
                VALUES (%s, %s, 'parent', %s, TRUE, %s)
                RETURNING user_id
            """, (username, hashed_password, branch_id, parent_email))
            parent_id = cursor.fetchone()["user_id"]

            cursor.execute("""
                INSERT INTO parent_student (parent_id, student_id, relationship)
                VALUES (%s, %s, 'guardian')
            """, (parent_id, enrollment_id))
            db.commit()

            cursor.execute("""
                SELECT username
                FROM student_accounts
                WHERE enrollment_id=%s
            """, (enrollment_id,))
            sturow = cursor.fetchone()
            student_username = sturow["username"] if sturow else None
            student_temp_password = request.form.get("student_temp_password")

            # ─────── SEND EMAIL WITH CREDENTIALS ───────
            parent_email = enrollment.get("guardian_email") or enrollment.get("email")
            if parent_email:
                # Determine relationship word based on student gender
                rel_word = "daughter" if enrollment.get("gender") == "Female" else "son"
                student_name = enrollment.get("student_name")
                
                subject = f"Parent Account Created - Parent of {student_name}"
                
                body = (
                    f"Congratulations! Your {rel_word}'s enrollment is approved.\n\n"
                    f"Hello,\n"
                    f"Your parent account has been created for {student_name}.\n\n"
                    f"Parent Username: {username}\n"
                    f"Parent Password: {temp_password}\n\n"
                    f"Student Username: {student_username or 'N/A'}\n"
                    f"Student Password: {student_temp_password or 'N/A'}\n"
                )

                html_body = f"""
                <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 600px; margin: 20px auto; border: 1px solid #e0e0e0; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.05);">
                    <div style="background-color: #1a2a4e; padding: 40px; text-align: center; color: white;">
                        <div style="font-size: 48px; margin-bottom: 10px;">🛡️</div>
                        <h1 style="margin: 0; font-size: 26px; font-weight: 800;">Congratulations!</h1>
                        <p style="margin: 5px 0 0; opacity: 0.9; font-size: 16px;">Your {rel_word}'s enrollment is approved</p>
                    </div>
                    <div style="padding: 40px; color: #334155; line-height: 1.6;">
                        <p style="font-size: 16px;">Hello,</p>
                        <p style="font-size: 16px;">We are happy to inform you that your {rel_word}, <strong>{student_name}</strong>, is now officially enrolled. Your parent account and the student's account are ready.</p>
                        
                        <!-- Parent Section -->
                        <div style="background-color: #f0f9ff; border: 1px solid #bae6fd; border-radius: 10px; padding: 20px; margin: 25px 0;">
                            <h3 style="margin: 0 0 12px 0; font-size: 13px; text-transform: uppercase; color: #0369a1; letter-spacing: 1px;">Parent Account Details</h3>
                            <div style="margin-bottom: 10px;">
                                <span style="font-size: 14px; color: #64748b;">Username:</span>
                                <strong style="font-size: 16px; color: #0c4a6e; margin-left: 5px;">{username}</strong>
                            </div>
                            <div>
                                <span style="font-size: 14px; color: #64748b;">Password:</span>
                                <strong style="font-size: 16px; color: #0c4a6e; margin-left: 5px;">{temp_password}</strong>
                            </div>
                        </div>

                        <!-- Student Section -->
                        <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 20px; margin: 0 0 25px 0;">
                            <h3 style="margin: 0 0 12px 0; font-size: 13px; text-transform: uppercase; color: #64748b; letter-spacing: 1px;">Student Account Details</h3>
                            <div style="margin-bottom: 10px;">
                                <span style="font-size: 14px; color: #64748b;">Username:</span>
                                <strong style="font-size: 16px; color: #1e293b; margin-left: 5px;">{student_username or '[See Registrar]'}</strong>
                            </div>
                            <div>
                                <span style="font-size: 14px; color: #64748b;">Password:</span>
                                <strong style="font-size: 16px; color: #1e293b; margin-left: 5px;">{student_temp_password or '[See Registrar]'}</strong>
                            </div>
                        </div>

                        <div style="text-align: center; margin-top: 10px;">
                            <a href="https://www.liceo-lms.com/login" 
                               style="display: inline-block; padding: 16px 32px; background-color: #1a2a4e; color: white; text-decoration: none; border-radius: 8px; font-weight: 700; font-size: 16px;">
                                Access the Portal &rarr;
                            </a>
                        </div>
                    </div>
                    <div style="background-color: #f1f5f9; padding: 20px; text-align: center; font-size: 12px; color: #94a3b8;">
                        &copy; 2026 LiceoLMS - Liceo de Majayjay System
                    </div>
                </div>
                """
                send_email(parent_email, subject, body, html_body=html_body)

            flash(f"Parent account for {enrollment.get('student_name')} created! Credentials sent to {parent_email}.", "success")
            return redirect("/registrar/enrollments")
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create parent account: {str(e)}")
            flash("Failed to create parent account. Please try again.", "error")
            return redirect("/registrar/enrollments")

    except Exception as e:
        db.rollback()
        logger.error(f"Create parent account error: {str(e)}")
        flash("Something went wrong while creating parent account.", "error")
        return redirect("/registrar/enrollments")
    finally:
        cursor.close()
        db.close()


# ══════════════════════════════════════════
# LINK EXISTING PARENT ACCOUNT TO STUDENT
# ══════════════════════════════════════════

@registrar_bp.route("/registrar/link-parent/<int:enrollment_id>", methods=["POST"])
def link_parent_account(enrollment_id):
    """Link an existing parent account (matched by guardian email) to this student
    instead of creating a duplicate parent account."""
    if session.get("role") != "registrar":
        return redirect("/")

    branch_id = session.get("branch_id")
    if not branch_id:
        flash("Missing branch in session. Please login again.", "error")
        return redirect("/logout")

    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cursor.execute("""
            SELECT * FROM enrollments
            WHERE enrollment_id=%s AND branch_id=%s
              AND status IN ('approved', 'enrolled', 'open_for_enrollment')
        """, (enrollment_id, branch_id))
        enrollment = cursor.fetchone()

        if not enrollment:
            flash("Enrollment not found or not approved.", "error")
            return redirect("/registrar/enrollments#enrolled")

        # Guard: already linked?
        cursor.execute("SELECT 1 FROM parent_student WHERE student_id = %s", (enrollment_id,))
        if cursor.fetchone():
            flash("This student already has a linked parent account.", "warning")
            return redirect("/registrar/enrollments#enrolled")

        guardian_email = (enrollment.get("guardian_email") or "").strip().lower()
        if not guardian_email:
            flash("No guardian email on record. Cannot auto-link.", "error")
            return redirect("/registrar/enrollments#enrolled")

        # Find existing parent account via another enrollment with the same guardian_email
        cursor.execute("""
            SELECT u.user_id, u.username
            FROM enrollments e_sib
            JOIN parent_student ps_sib ON ps_sib.student_id = e_sib.enrollment_id
            JOIN users u               ON u.user_id          = ps_sib.parent_id
            WHERE LOWER(e_sib.guardian_email) = %s
              AND e_sib.enrollment_id <> %s
            LIMIT 1
        """, (guardian_email, enrollment_id))
        parent_user = cursor.fetchone()

        if not parent_user:
            flash("No existing parent account found for that guardian email. Use Create Parent Account instead.", "warning")
            return redirect("/registrar/enrollments#enrolled")

        # Create the parent_student link
        cursor.execute("""
            INSERT INTO parent_student (parent_id, student_id, relationship)
            VALUES (%s, %s, 'guardian')
            ON CONFLICT DO NOTHING
        """, (parent_user["user_id"], enrollment_id))
        db.commit()

        flash(
            f"Student successfully linked to existing parent account '{parent_user['username']}'. No new account was created.",
            "success"
        )
        return redirect("/registrar/enrollments#enrolled")

    except Exception as e:
        db.rollback()
        logger.error(f"Link parent account error: {str(e)}")
        flash("Something went wrong while linking the parent account.", "error")
        return redirect("/registrar/enrollments#enrolled")
    finally:
        cursor.close()
        db.close()


# ══════════════════════════════════════════
# PROFILE PICTURES
# ══════════════════════════════════════════

import os
from werkzeug.utils import secure_filename
from cloudinary_helper import upload_file_to_subfolder

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@registrar_bp.route("/registrar/profile-pictures", methods=["GET", "POST"])
def registrar_profile_pictures():
    # Only registrar
    if session.get("role") != "registrar":
        return redirect("/")

    branch_id = session.get("branch_id")
    if not branch_id:
        flash("Missing branch in session. Please login again.", "error")
        return redirect("/logout")

    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Get connection info for debugging
    import os
    db_host = os.getenv("DB_HOST", "127.0.0.1")
    db_name = os.getenv("DB_NAME", "liceo_db")

    try:
        if request.method == "POST":
            print(f"[DEBUG] POST Connection: Host={db_host}, DB={db_name}")
            user_type = request.form.get("user_type") # 'student' or 'teacher'
            target_id = request.form.get("target_id") # enrollment_id or user_id
            
            if 'profile_image' not in request.files:
                flash("No file part", "error")
                return redirect(request.url)
            
            file = request.files['profile_image']
            if file.filename == '':
                flash("No selected file", "error")
                return redirect(request.url)

            if file and allowed_file(file.filename):
                try:
                    # Upload to Cloudinary (returns a secure URL)
                    file_url = upload_file_to_subfolder(file, "profiles")

                    # DEBUG: Print to console for local monitoring
                    print(f"[DEBUG] Profile Upload: type={user_type}, id={target_id}, file={file.filename}")

                    if user_type == 'student':
                        # Explicitly cast target_id to int for PostgreSQL compatibility
                        t_id = int(target_id)
                        
                        # 1. Primary update: enrollments
                        cursor.execute("UPDATE enrollments SET profile_image = %s WHERE enrollment_id = %s", (file_url, t_id))
                        affected = cursor.rowcount
                        
                        if affected > 0:
                            # 2. Sync with users table (students have a users row for portal access)
                            try:
                                cursor.execute("SAVEPOINT user_sync")
                                cursor.execute("UPDATE users SET profile_image = %s WHERE enrollment_id = %s", (file_url, t_id))
                                cursor.execute("RELEASE SAVEPOINT user_sync")
                            except Exception as e:
                                cursor.execute("ROLLBACK TO SAVEPOINT user_sync")
                                print(f"[DEBUG] users sync failed: {e}")

                            # 3. Sync with student_accounts table
                            try:
                                cursor.execute("SAVEPOINT sa_sync")
                                cursor.execute("UPDATE student_accounts SET profile_image = %s WHERE enrollment_id = %s", (file_url, t_id))
                                cursor.execute("RELEASE SAVEPOINT sa_sync")
                            except Exception as e:
                                cursor.execute("ROLLBACK TO SAVEPOINT sa_sync")
                                print(f"[DEBUG] student_accounts fallback failed: {e}")
                        
                        # IMMEDIATE RE-CHECK for debug logs
                        cursor.execute("SELECT student_name, profile_image FROM enrollments WHERE enrollment_id = %s", (t_id,))
                        recheck = cursor.fetchone()
                        print(f"[DEBUG] Student Update Affected: {affected}")
                        print(f"[DEBUG] Verification Fetch (ID={t_id}): {recheck}")
                        
                        if affected == 0:
                            db.rollback()
                            flash("Upload failed: No student record found with ID #" + str(target_id), "error")
                            return redirect(request.referrer or url_for('registrar.registrar_profile_pictures'))

                    elif user_type == 'teacher':
                        t_id = int(target_id)
                        cursor.execute("UPDATE users SET profile_image = %s WHERE user_id = %s", (file_url, t_id))
                        affected = cursor.rowcount
                        print(f"[DEBUG] Teacher Update Affected: {affected}")
                        
                        if affected == 0:
                            db.rollback()
                            flash("Upload failed: No faculty record found with ID #" + str(target_id), "error")
                            return redirect(request.referrer or url_for('registrar.registrar_profile_pictures'))
                    
                    db.commit()
                    print(f"[DEBUG] Database COMMITTED successfully.")
                    flash("Profile picture uploaded successfully!", "success")
                except Exception as e:
                    db.rollback()
                    flash(f"Error uploading image: {e}", "error")
            else:
                flash("Invalid file type. Allowed: png, jpg, jpeg, gif", "error")

            # redirect back to same tab/filter
            return redirect(request.referrer or url_for('registrar.registrar_profile_pictures'))

        # GET request
        print(f"[DEBUG] GET Connection: Host={db_host}, DB={db_name}")
        tab = request.args.get("tab", "students")
        grade_filter = request.args.get("grade", "")
        section_filter = request.args.get("section_id", "")

        students = []
        teachers = []
        all_grades = []
        all_sections = []

        if tab == "students":
            # Get grades for filter
            cursor.execute("SELECT name FROM grade_levels WHERE name NOT IN ('Grade 11', 'Grade 12') ORDER BY id ASC")
            all_grades = [row["name"] for row in cursor.fetchall()]

            # Get all sections
            cursor.execute("""
                SELECT s.section_id, s.section_name, g.name AS grade_level
                FROM sections s
                JOIN grade_levels g ON g.id = s.grade_level_id
                WHERE s.branch_id = %s
                ORDER BY g.id, s.section_name
            """, (branch_id,))
            all_sections = cursor.fetchall()

            query = """
                SELECT e.enrollment_id, e.branch_enrollment_no, e.student_name, e.grade_level, 
                       s.section_name, e.profile_image AS student_pic, e.status
                FROM enrollments e
                LEFT JOIN sections s ON e.section_id = s.section_id
                WHERE e.branch_id = %s AND e.status IN ('enrolled', 'approved', 'open_for_enrollment')
            """
            params = [branch_id]
            
            # ... (rest of filtering logic)
            if grade_filter:
                query += " AND e.grade_level = %s"
                params.append(grade_filter)
            if section_filter:
                query += " AND e.section_id = %s"
                params.append(section_filter)

            query += """
                ORDER BY CASE e.grade_level
                    WHEN 'Nursery' THEN 1 WHEN 'Kinder' THEN 2 WHEN 'Grade 1' THEN 3
                    WHEN 'Grade 2' THEN 4 WHEN 'Grade 3' THEN 5 WHEN 'Grade 4' THEN 6
                    WHEN 'Grade 5' THEN 7 WHEN 'Grade 6' THEN 8 WHEN 'Grade 7' THEN 9
                    WHEN 'Grade 8' THEN 10 WHEN 'Grade 9' THEN 11 WHEN 'Grade 10' THEN 12
                    WHEN 'Grade 11' THEN 13 WHEN 'Grade 12' THEN 14 ELSE 99
                END, e.student_name
            """
            
            cursor.execute(query, tuple(params))
            students = cursor.fetchall()

            # DEBUG: Print first 5 students to console to verify DB values
            print(f"[DEBUG] GET Profile Pictures - Branch: {branch_id}, Tab: {tab}")
            for s in students[:5]:
                print(f"  > Student: {s['student_name']} (ID:{s['enrollment_id']}), Path: {s['student_pic']}")

        elif tab == "teachers":
            cursor.execute("""
                SELECT u.user_id, u.full_name, u.username, u.profile_image,
                       STRING_AGG(DISTINCT sub.name, ', ') as subjects
                FROM users u
                LEFT JOIN section_teachers st ON u.user_id = st.teacher_id
                LEFT JOIN subjects sub ON st.subject_id = sub.subject_id
                WHERE u.branch_id = %s AND u.role = 'teacher'
                GROUP BY u.user_id, u.full_name, u.username, u.profile_image
                ORDER BY u.full_name
            """, (branch_id,))
            teachers = cursor.fetchall()

        return render_template(
            "registrar_profile_pictures.html",
            tab=tab,
            grade_filter=grade_filter,
            section_filter=section_filter,
            all_grades=all_grades,
            all_sections=all_sections,
            students=students,
            teachers=teachers
        )

    finally:
        cursor.close()
        db.close()


# ══════════════════════════════════════════
# STUDENTS BY GRADE
# ══════════════════════════════════════════

@registrar_bp.route("/registrar/students-by-grade", methods=["GET"])
def registrar_students_by_grade():
    if session.get("role") != "registrar":
        return redirect("/")

    branch_id = session.get("branch_id")
    if not branch_id:
        flash("Missing branch in session. Please login again.", "error")
        return redirect("/logout")

    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        grade_filter = request.args.get("grade", "")
        section_filter = request.args.get("section_id", "")
        year_filter = request.args.get("year_id", "")

        # Fetch school years for the dropdown
        cursor.execute("SELECT year_id, label, is_active FROM school_years WHERE branch_id = %s ORDER BY label DESC", (branch_id,))
        school_years = cursor.fetchall()
        
        # Determine the active year id or fallback
        active_year_id = None
        for sy in school_years:
            if sy["is_active"]:
                active_year_id = sy["year_id"]
                break
        
        if not year_filter:
            year_filter = active_year_id

        cursor.execute("SELECT name FROM grade_levels WHERE name NOT IN ('Grade 11', 'Grade 12') ORDER BY id ASC")
        all_grades = [row["name"] for row in cursor.fetchall()]
        cursor.execute("""
    SELECT branch_id, branch_name
    FROM branches
    WHERE branch_id = %s
""", (branch_id,))
        branch = cursor.fetchone()

        # Fetch sections filtered by year_id
        cursor.execute("""
            SELECT s.section_id, s.section_name, g.name AS grade_level
            FROM sections s
            JOIN grade_levels g ON g.id = s.grade_level_id
            WHERE s.branch_id = %s AND s.year_id = %s
            ORDER BY g.id, s.section_name
        """, (branch_id, year_filter))
        all_sections = cursor.fetchall()

        query = """
            SELECT e.*, s.section_name, sa.username AS account_username,
                   COALESCE(
                       json_agg(
                           json_build_object(
                               'file_name', d.file_name,
                               'file_path', d.file_path,
                               'document_type', d.doc_type
                           )
                       ) FILTER (WHERE d.doc_id IS NOT NULL),
                       '[]'
                   ) AS documents
            FROM enrollments e
            LEFT JOIN sections s ON s.section_id = e.section_id
            LEFT JOIN enrollment_documents d ON d.enrollment_id = e.enrollment_id
            LEFT JOIN student_accounts sa ON sa.enrollment_id = e.enrollment_id
            WHERE e.branch_id = %s AND e.year_id = %s
              AND e.status IN ('enrolled', 'approved', 'open_for_enrollment')
        """
        params = [branch_id, year_filter]

        if grade_filter:
            query += " AND e.grade_level = %s"
            params.append(grade_filter)
            if section_filter:
                query += " AND e.section_id = %s"
                params.append(section_filter)

        query += """
            GROUP BY e.enrollment_id, s.section_name, sa.username
            ORDER BY e.grade_level ASC, s.section_name ASC NULLS LAST, e.student_name ASC
        """

        cursor.execute(query, tuple(params))
        students_raw = cursor.fetchall()
        
        students = []
        for e in students_raw:
            e = dict(e)
            if isinstance(e["documents"], str):
                e["documents"] = json.loads(e["documents"])
            students.append(e)

        return render_template(
            "registrar_students_by_grade.html",
            students=students,
            all_grades=all_grades,
            all_sections=all_sections,
            grade_filter=grade_filter,
            section_filter=section_filter,
            school_years=school_years,
            year_filter=str(year_filter) if year_filter else "",
            branch=branch
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Registrar students by grade error: {str(e)}")
        flash("Something went wrong.", "error")
        return redirect("/registrar")
    finally:
        cursor.close()
        db.close()


@registrar_bp.route("/registrar/students-by-grade/update/<int:enrollment_id>", methods=["POST"])
def registrar_students_by_grade_update(enrollment_id):
    if session.get("role") != "registrar":
        return redirect("/")

    branch_id = session.get("branch_id")
    if not branch_id:
        flash("Missing branch in session.", "error")
        return redirect("/logout")

    db = get_db_connection()
    cursor = db.cursor()
    try:
        # Fields to update based on the inline form
        fields = [
            "gender", "dob", "lrn", "email", "contact_number", "address",
            "guardian_name", "guardian_contact", "guardian_email",
            "father_name", "father_contact", "father_occupation",
            "mother_name", "mother_contact", "mother_occupation",
            "previous_school", "enroll_type"
        ]
        
        sets = []
        vals = []
        for f in fields:
            raw = request.form.get(f)
            if raw is not None:
                val = raw.strip() or None
                sets.append(f"{f} = %s")
                vals.append(val)

        if sets:
            final_vals = vals + [enrollment_id, branch_id]
            sql = f"UPDATE enrollments SET {', '.join(sets)} WHERE enrollment_id = %s AND branch_id = %s"
            
            cursor.execute(sql, final_vals)
            db.commit()
            flash("Student details updated successfully!", "success")
            
    except Exception as e:
        db.rollback()
        logger.error(f"Inline update error (Enrollment ID: {enrollment_id}): {str(e)}")
        flash("Error updating details. Please try again.", "error")
    finally:
        cursor.close()
        db.close()
        
    return redirect(request.referrer or "/registrar/students-by-grade")

from datetime import datetime, time

@registrar_bp.route("/registrar/schedules", methods=['GET', 'POST'])
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
            return redirect(url_for("registrar.list_and_add_schedules"))

        # --- TIME VALIDATION: must be within 07:00 and 17:00, and start < end ---
        start_t = datetime.strptime(start_time, "%H:%M").time()
        end_t = datetime.strptime(end_time, "%H:%M").time()
        if not (time(7,0) <= start_t <= time(17,0)) or not (time(7,0) <= end_t <= time(17,0)):
            flash("Invalid schedule: Times must be between 07:00 and 17:00.", "danger")
            cursor.close(); db.close()
            return redirect(url_for("registrar.list_and_add_schedules"))
        if start_t >= end_t:
            flash("Invalid schedule: Start time must be before end time.", "danger")
            cursor.close(); db.close()
            return redirect(url_for("registrar.list_and_add_schedules"))
        if (start_t.minute % 15) != 0 or (end_t.minute % 15) != 0:
            flash("Invalid schedule: Times must be in 15-minute increments.", "danger")
            cursor.close(); db.close()
            return redirect(url_for("registrar.list_and_add_schedules"))

        # --- ROOM VALIDATION: must be a number between 1 and 30 ---
        try:
            room_val = int(room)
            if not (1 <= room_val <= 30):
                flash("Invalid Room: Room number must be between 1 and 30.", "danger")
                cursor.close(); db.close()
                return redirect(url_for("registrar.list_and_add_schedules"))
        except (ValueError, TypeError):
            flash("Invalid Room: Please enter a numeric room number (1-30).", "danger")
            cursor.close(); db.close()
            return redirect(url_for("registrar.list_and_add_schedules"))

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
            return redirect(url_for("registrar.list_and_add_schedules"))

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
        return redirect(url_for("registrar.list_and_add_schedules"))

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

@registrar_bp.route("/registrar/schedules/<int:schedule_id>/edit", methods=["GET", "POST"])
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
            return redirect(url_for("registrar.list_and_add_schedules"))
        if start_t >= end_t:
            flash("Invalid schedule: Start time must be before end time.", "danger")
            cursor.close(); db.close()
            return redirect(url_for("registrar.list_and_add_schedules"))
        if (start_t.minute % 15) != 0 or (end_t.minute % 15) != 0:
            flash("Invalid schedule: Times must be in 15-minute increments.", "danger")
            cursor.close(); db.close()
            return redirect(url_for("registrar.list_and_add_schedules"))

        # --- ROOM VALIDATION: must be a number between 1 and 30 ---
        try:
            room_val = int(room)
            if not (1 <= room_val <= 30):
                flash("Invalid Room: Room number must be between 1 and 30.", "danger")
                cursor.close(); db.close()
                return redirect(url_for("registrar.list_and_add_schedules"))
        except (ValueError, TypeError):
            flash("Invalid Room: Please enter a numeric room number (1-30).", "danger")
            cursor.close(); db.close()
            return redirect(url_for("registrar.list_and_add_schedules"))

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
            return redirect(url_for("registrar.list_and_add_schedules"))

        cursor.execute("""
            UPDATE schedules
            SET subject_id=%s, section_id=%s, teacher_id=%s, day_of_week=%s,
                start_time=%s, end_time=%s, room=%s, year_id=%s
            WHERE schedule_id=%s AND branch_id=%s
        """, (subject_id, section_id, teacher_id, day_of_week, start_time, end_time, room, active_year["year_id"] if active_year else year_id, schedule_id, branch_id))
        db.commit()
        cursor.close(); db.close()
        flash("Schedule updated!", "success")
        return redirect(url_for("registrar.list_and_add_schedules"))

    cursor.close(); db.close()
    return render_template(
        "schedule_edit.html",
        schedule=schedule,
        combinations=combinations,
        active_year=active_year
    )


@registrar_bp.route("/registrar/schedules/<int:schedule_id>/archive", methods=["POST"])
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
    return redirect(url_for("registrar.list_and_add_schedules"))

@registrar_bp.route("/registrar/schedules/<int:schedule_id>/unarchive", methods=["POST"])
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
    return redirect(url_for("registrar.list_and_add_schedules", show_archived="true"))

@registrar_bp.route("/registrar/schedules/<int:schedule_id>/delete_permanent", methods=["POST"])
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
    return redirect(url_for("registrar.list_and_add_schedules", show_archived="true"))
# ══════════════════════════════════════════
# ACCOUNT RESET
# ══════════════════════════════════════════

@registrar_bp.route("/registrar/reset-password/<int:enrollment_id>", methods=["POST"])
def registrar_reset_student_password(enrollment_id):
    if session.get("role") != "registrar":
        return {"success": False, "message": "Unauthorized"}, 403

    branch_id = session.get("branch_id")
    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        # Check if enrollment and account exist
        cursor.execute("""
            SELECT e.enrollment_id, e.student_name, e.email as enr_email, sa.username, sa.email as acc_email
            FROM enrollments e
            JOIN student_accounts sa ON e.enrollment_id = sa.enrollment_id
            WHERE e.enrollment_id = %s AND e.branch_id = %s
        """, (enrollment_id, branch_id))
        data = cursor.fetchone()

        if not data:
            return {"success": False, "message": "Student account not found."}, 404

        target_email = data["acc_email"] or data["enr_email"]
        if not target_email:
            return {"success": False, "message": "Student email not found. Please provide an email address first."}, 400

        # Generate new password
        temp_password = generate_password()
        from werkzeug.security import generate_password_hash
        hashed_pw = generate_password_hash(temp_password)

        # Update DB
        cursor.execute("""
            UPDATE student_accounts
            SET password = %s, require_password_change = TRUE, last_password_change = NOW()
            WHERE enrollment_id = %s
        """, (hashed_pw, enrollment_id))
        db.commit()

        # Send Email
        subject = "Account Password Reset - LiceoLMS"
        body = f"""
        Hello {data['student_name']},
        
        Your student portal password has been reset by the Registrar.
        
        Username: {data['username']}
        New Temporary Password: {temp_password}
        
        Please log in and update your password immediately.
        """
        
        html_body = f"""
        <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 600px; margin: 20px auto; border: 1px solid #e2e8f0; border-radius: 16px; overflow: hidden; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);">
            <div style="background-color: #1e3a8a; padding: 40px; text-align: center; color: #ffffff;">
                <div style="font-size: 40px; margin-bottom: 12px;">🔐</div>
                <h1 style="margin: 0; font-size: 24px; font-weight: 800; letter-spacing: -0.02em;">Password Reset</h1>
                <p style="margin: 8px 0 0; opacity: 0.9; font-size: 15px;">Your credentials have been updated</p>
            </div>
            <div style="padding: 40px; background-color: #ffffff; color: #1e293b;">
                <p style="font-size: 16px; margin-bottom: 24px;">Hello <strong>{data['student_name']}</strong>,</p>
                <p style="font-size: 15px; line-height: 1.6; color: #64748b; margin-bottom: 32px;">
                    Your student portal password has been reset by the Registrar. You can now use the temporary credentials below to log in to your account.
                </p>
                
                <div style="background-color: #f8fafc; border: 1.5px solid #e2e8f0; border-radius: 12px; padding: 24px; margin-bottom: 32px;">
                    <div style="margin-bottom: 16px;">
                        <span style="display: block; font-size: 11px; text-transform: uppercase; font-weight: 800; color: #94a3b8; letter-spacing: 0.05em; margin-bottom: 4px;">Username</span>
                        <span style="font-size: 17px; font-weight: 700; color: #1e3a8a;">{data['username']}</span>
                    </div>
                    <div>
                        <span style="display: block; font-size: 11px; text-transform: uppercase; font-weight: 800; color: #94a3b8; letter-spacing: 0.05em; margin-bottom: 4px;">Temporary Password</span>
                        <span style="font-size: 17px; font-weight: 700; color: #1e3a8a;">{temp_password}</span>
                    </div>
                </div>
                
                <div style="text-align: center; margin-bottom: 32px;">
                    <a href="https://www.liceo-lms.com/login" style="display: inline-block; padding: 14px 28px; background-color: #1e3a8a; color: #ffffff; text-decoration: none; border-radius: 12px; font-weight: 700; font-size: 15px; box-shadow: 0 4px 6px -1px rgba(30, 58, 138, 0.2);">Log In to Portal</a>
                </div>
                
                <p style="font-size: 13px; color: #94a3b8; font-style: italic; text-align: center;">Note: You will be required to choose a new password upon your next login.</p>
            </div>
            <div style="background-color: #f1f5f9; padding: 20px; text-align: center; font-size: 12px; color: #94a3b8;">
                &copy; 2026 LiceoLMS - System Managed Registry
            </div>
        </div>
        """
        send_email(target_email, subject, body, html_body=html_body)

        return {"success": True, "message": "Password reset successful and email sent."}

    except Exception as e:
        db.rollback()
        logger.error(f"Password reset failed: {e}")
        return {"success": False, "message": str(e)}, 500
    finally:
        cursor.close()
        db.close()

# ══════════════════════════════════════════
# NO CACHE
# ══════════════════════════════════════════

@registrar_bp.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response
# ------------------------------------------
# ACADEMIC MANAGEMENT (Grade Levels, Sections, Subjects)
# ------------------------------------------

@registrar_bp.route("/registrar/grade-levels", methods=["GET", "POST"])
def registrar_grade_levels():
    if session.get("role") != "registrar":
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
            return redirect(url_for('registrar.registrar_grade_levels'))

        cursor.execute("SELECT COUNT(*) FROM grade_levels WHERE branch_id = %s", (branch_id,))
        current_count = cursor.fetchone()[0]

        if current_count >= 20:
            flash("Maximum limit of 20 grade levels reached. You cannot add more.", "error")
            return redirect(url_for('registrar.registrar_grade_levels'))

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
                return redirect(url_for('registrar.registrar_grade_levels'))
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

    return render_template("registrar_grade_levels.html", grades=grades, next_order=next_order, available_grade_names=available_grade_names)

@registrar_bp.route("/registrar/grade-levels/<int:grade_id>/edit", methods=["POST"])
def registrar_grade_level_edit(grade_id):
    if session.get("role") != "registrar":
        return redirect("/")
    branch_id = session.get("branch_id")
    name = (request.form.get("edit_name") or "").strip()
    order = request.form.get("edit_display_order") or None
    if not name or order is None:
        flash("All fields required.", "error")
        return redirect(url_for("registrar.registrar_grade_levels"))
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute(
        "UPDATE grade_levels SET name=%s, display_order=%s WHERE id=%s AND branch_id=%s",
        (name, int(order), grade_id, branch_id)
    )
    db.commit()
    cursor.close(); db.close()
    flash("Grade level updated.", "success")
    return redirect(url_for("registrar.registrar_grade_levels"))

@registrar_bp.route("/registrar/grade-levels/<int:grade_id>/delete", methods=["POST"])
def registrar_grade_level_delete(grade_id):
    if session.get("role") != "registrar":
        return redirect("/")
    branch_id = session.get("branch_id")
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute("DELETE FROM grade_levels WHERE id=%s AND branch_id=%s", (grade_id, branch_id))
    db.commit()
    cursor.close(); db.close()
    flash("Grade level deleted.", "success")
    return redirect(url_for("registrar.registrar_grade_levels"))

@registrar_bp.route("/registrar/sections", methods=["GET", "POST"])
def registrar_sections():
    if session.get("role") != "registrar":
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
                return redirect(url_for("registrar.registrar_sections"))

            cursor.execute("""
                SELECT 1 FROM school_years 
                WHERE year_id = %s AND branch_id = %s
            """, (year_id, branch_id))
            if not cursor.fetchone():
                flash("Invalid school year selected.", "error")
                return redirect(url_for("registrar.registrar_sections"))

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

        return redirect(url_for("registrar.registrar_sections"))

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
        "registrar_sections.html",
        sections=sections,
        grades=grades,
        years=years
    )

@registrar_bp.route("/registrar/sections/<int:section_id>/delete", methods=["POST"])
def registrar_section_delete(section_id):
    if session.get("role") != "registrar":
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

    return redirect(url_for("registrar.registrar_sections"))

@registrar_bp.route("/registrar/sections/<int:section_id>/edit", methods=["POST"])
def registrar_section_edit(section_id):
    if session.get("role") != "registrar":
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
        return redirect(url_for("registrar.registrar_sections"))

    db = get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute("SELECT 1 FROM grade_levels WHERE id = %s AND branch_id = %s", (grade_level_id, branch_id))
        if not cursor.fetchone():
            flash("Invalid grade level.", "error")
            return redirect(url_for("registrar.registrar_sections"))

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

    return redirect(url_for("registrar.registrar_sections"))

@registrar_bp.route("/registrar/subjects", methods=["GET", "POST"])
def registrar_subjects():
    if session.get("role") != "registrar":
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
            return redirect(url_for("registrar.registrar_subjects"))

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

        return redirect(url_for("registrar.registrar_subjects"))

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
        "registrar_subjects.html",
        assignments=assignments,
        section_options=section_options,
        selected_section_id=section_id_filter
    )

@registrar_bp.route("/registrar/subjects/<int:subject_id>/<int:section_id>/toggle-archive", methods=["POST"])
def registrar_subject_toggle_archive(subject_id, section_id):
    if session.get("role") != "registrar":
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
    return redirect(url_for("registrar.registrar_subjects", section_id=section_id))

@registrar_bp.route("/registrar/subjects/<int:subject_id>/delete", methods=["POST"])
def registrar_subject_delete(subject_id):
    if session.get("role") != "registrar":
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
    return redirect(url_for("registrar.registrar_subjects"))

@registrar_bp.route("/registrar/subjects/<int:subject_id>/edit", methods=["POST"])
def registrar_subject_edit(subject_id):
    if session.get("role") != "registrar":
        return redirect("/")
    branch_id = session.get("branch_id")
    new_name = (request.form.get("name") or "").strip()
    section_id = request.form.get("section_id")
    deped_category = request.form.get("deped_category", "language")

    if not new_name or not section_id:
        flash("Required fields missing.", "error")
        return redirect(url_for("registrar.registrar_subjects"))

    db = get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute("SELECT 1 FROM sections WHERE section_id=%s AND branch_id=%s", (section_id, branch_id))
        if not cursor.fetchone():
            flash("Invalid section.", "error")
            return redirect(url_for("registrar.registrar_subjects"))

        cursor.execute("UPDATE subjects SET name = %s, deped_category = %s WHERE subject_id = %s", (new_name, deped_category, subject_id))
        db.commit()
        flash("Subject updated.", "success")
    except Exception as e:
        db.rollback()
        flash(f"Error: {str(e)}", "error")
    finally:
        cursor.close(); db.close()
    return redirect(url_for("registrar.registrar_subjects"))

@registrar_bp.route("/registrar/assign-teachers", methods=["GET", "POST"])
def registrar_assign_teachers():
    if session.get("role") != "registrar":
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
            return redirect(url_for("registrar.registrar_home"))

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
                return redirect(url_for("registrar.registrar_assign_teachers"))

            cursor.execute("UPDATE section_teachers SET teacher_id = %s WHERE section_id = %s AND subject_id = %s AND year_id = %s", (teacher_id, section_id, subject_id, active_year_id))
            db.commit()
            flash("Teacher assigned successfully!", "success")
            return redirect(url_for("registrar.registrar_assign_teachers", grade=grade_filter))

        cursor.execute("SELECT user_id, username, full_name FROM users WHERE branch_id = %s AND role = 'teacher' ORDER BY full_name", (branch_id,))
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
        "registrar_assign_teachers.html",
        teachers=teachers,
        assignments=assignments,
        grade_options=grade_options,
        grade_filter=grade_filter,
        section_options=section_options,
    )

@registrar_bp.route("/registrar/api/get-all-subjects/<int:teacher_id>", methods=["GET"])
def registrar_api_get_all_subjects(teacher_id):
    if session.get("role") != "registrar":
        return {"error": "Unauthorized"}, 403
    branch_id = session.get("branch_id")
    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cursor.execute("SELECT teacher_type, specialization_subject, department FROM users WHERE user_id=%s AND branch_id=%s AND role='teacher'", (teacher_id, branch_id))
        teacher = cursor.fetchone()
        if not teacher: return {"error": "Teacher not found"}, 404

        teacher_type = teacher.get('teacher_type')
        spec_sub = teacher.get('specialization_subject')
        department = teacher.get('department')

        query = """
            SELECT st.id AS assignment_id, st.subject_id, st.section_id, st.teacher_id, sub.name AS subject_name, s.section_name, g.name AS grade_level_name, (st.teacher_id = %s) AS is_assigned_to_this_teacher,
            (st.teacher_id IS NOT NULL AND st.teacher_id != %s) as is_currently_assigned,
            u.full_name as current_teacher_name
            FROM section_teachers st
            JOIN sections s ON st.section_id = s.section_id
            JOIN grade_levels g ON s.grade_level_id = g.id
            JOIN subjects sub ON st.subject_id = sub.subject_id
            JOIN school_years y ON s.year_id = y.year_id
            LEFT JOIN users u ON st.teacher_id = u.user_id
            WHERE s.branch_id = %s AND y.is_active = TRUE
        """
        params = [teacher_id, teacher_id, branch_id]

        # Filter by specialization subject (Applies to both Advisory and Subject specialists)
        if spec_sub:
            query += " AND sub.name ILIKE %s"
            params.append(f"%{spec_sub}%")
        
        # Filter by grades they are allowed to handle based on their department
        if department == 'elementary':
            query += " AND g.name IN ('Nursery', 'Kinder', 'Grade 1', 'Grade 2', 'Grade 3', 'Grade 4', 'Grade 5', 'Grade 6')"
        elif department == 'jhs':
            query += " AND g.name IN ('Grade 7', 'Grade 8', 'Grade 9', 'Grade 10')"
        elif department == 'shs':
            query += " AND g.name IN ('Grade 11', 'Grade 12')"

        query += " ORDER BY g.display_order, s.section_name, sub.name"
        
        cursor.execute(query, tuple(params))
        subjects = cursor.fetchall() or []
        return {"success": True, "subjects": [dict(row) for row in subjects]}
    except Exception as e:
        return {"error": str(e)}, 500
    finally:
        cursor.close(); db.close()

@registrar_bp.route("/registrar/assign-teachers-bulk", methods=["POST"])
def registrar_assign_teachers_bulk():
    if session.get("role") != "registrar":
        return {"error": "Unauthorized"}, 403
    branch_id = session.get("branch_id")
    data = request.get_json()
    teacher_id = data.get("teacher_id")
    assignment_ids = data.get("assignment_ids", [])

    if not teacher_id or not assignment_ids:
        return {"success": False, "message": "Missing data"}, 400

    db = get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute("UPDATE section_teachers SET teacher_id = %s WHERE id = ANY(%s) AND section_id IN (SELECT section_id FROM sections WHERE branch_id = %s)", (teacher_id, assignment_ids, branch_id))
        db.commit()
        return {"success": True, "count": cursor.rowcount}
    except Exception as e:
        db.rollback()
        return {"success": False, "message": str(e)}, 500
    finally:
        cursor.close(); db.close()

@registrar_bp.route("/registrar/api/remove-teacher-assignment", methods=["POST"])
def registrar_remove_teacher_assignment():
    if session.get("role") != "registrar":
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

# ══════════════════════════════════════════
# INVENTORY MANAGEMENT (Uniform & Supplies)
# ══════════════════════════════════════════

import re as _re

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
SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]

def _get_grade_display(item_name, stored_grade):
    if item_name in GRADE_MAPPINGS:
        grades = GRADE_MAPPINGS[item_name]
        return f"{grades[0]} - {grades[-1]}" if len(grades) > 3 else ", ".join(grades)
    return stored_grade or "All"

def _item_matches_grade_filter(item_name, stored_grade, grade_filter):
    if not grade_filter: return True
    if item_name in GRADE_MAPPINGS: return grade_filter in GRADE_MAPPINGS[item_name]
    return stored_grade == grade_filter or stored_grade is None

def _get_grade_order(item_name, grade_level):
    name_lower = str(item_name or "").lower()
    if 'pe uniform' in name_lower or 'p.e.' in name_lower: return 1000
    if grade_level:
        grade_str = str(grade_level).strip().lower()
        if 'nursery' in grade_str: return 10
        if 'kinder' in grade_str or 'pre' in grade_str: return 20
        m = _re.search(r'(\d+)', grade_str)
        if m: return 100 + int(m.group(1))
    if 'pre-elementary' in name_lower: return 15
    if 'elementary' in name_lower: return 110
    if 'jhs' in name_lower or 'junior high' in name_lower: return 115
    if 'shs' in name_lower or 'senior high' in name_lower: return 125
    return 999

def _size_sort_key(size_label: str) -> int:
    if not size_label: return 999
    s = str(size_label).strip().upper()
    return SIZE_ORDER.index(s) if s in SIZE_ORDER else 998

def _ensure_default_sizes_exist(cursor, item_id: int):
    cursor.execute("SELECT COUNT(*) FROM inventory_item_sizes WHERE item_id = %s", (item_id,))
    if cursor.fetchone()[0] > 0: return False
    for sz in SIZE_ORDER:
        cursor.execute("INSERT INTO inventory_item_sizes (item_id, size_label, stock_total, reserved_qty) VALUES (%s, %s, 0, 0)", (item_id, sz))
    return True

def _recompute_item_totals_from_sizes(cursor, item_id: int, branch_id: int):
    cursor.execute("""
        UPDATE inventory_items
        SET stock_total = COALESCE((SELECT SUM(stock_total) FROM inventory_item_sizes WHERE item_id = %s), 0),
            reserved_qty = COALESCE((SELECT SUM(reserved_qty) FROM inventory_item_sizes WHERE item_id = %s), 0)
        WHERE item_id = %s AND branch_id = %s
    """, (item_id, item_id, item_id, branch_id))


@registrar_bp.route("/registrar/inventory", methods=["GET"])
def registrar_inventory():
    if session.get("role") != "registrar":
        return redirect("/")
    branch_id = session.get("branch_id")
    search = (request.args.get("search") or "").strip()
    category_filter = (request.args.get("category") or "").strip()
    grade_filter = (request.args.get("grade") or "").strip()
    status_filter = (request.args.get("status") or "active").strip()

    if not category_filter or category_filter.upper() == 'BOOK':
        return redirect("/registrar/inventory?category=UNIFORM&status=" + status_filter)

    db = get_db_connection()
    cursor = db.cursor()
    try:
        where = ["branch_id = %s", "category = %s"]
        params = [branch_id, category_filter]
        if status_filter in ("active", "inactive"):
            where.append("is_active = %s")
            params.append(status_filter == "active")
        if search:
            where.append("(item_name ILIKE %s OR category ILIKE %s OR COALESCE(grade_level,'') ILIKE %s OR COALESCE(size_label,'') ILIKE %s)")
            like = f"%{search}%"
            params.extend([like, like, like, like])

        where_sql = " AND ".join(where)
        cursor.execute(f"""
            SELECT item_id, category, item_name, grade_level, is_common,
                   size_label, price, stock_total, reserved_qty, image_url, is_active
            FROM inventory_items WHERE {where_sql}
        """, params)
        all_items = cursor.fetchall() or []
        items = [i for i in all_items if _item_matches_grade_filter(i[2], i[3], grade_filter)] if grade_filter else all_items
        enhanced_items = sorted(
            [tuple(list(i) + [_get_grade_display(i[2], i[3])]) for i in items],
            key=lambda item: (0 if str(item[1] or "").upper() == "BOOK" else (1 if str(item[1] or "").upper() == "UNIFORM" else 2),
                              _get_grade_order(item[2], item[3]), item[2].lower())
        )
        cursor.execute("""
            SELECT COUNT(*) AS total_items, COALESCE(SUM(stock_total),0) AS total_stock,
                   COALESCE(SUM(reserved_qty),0) AS total_reserved,
                   COALESCE(SUM(CASE WHEN (stock_total - reserved_qty) < 10 THEN 1 ELSE 0 END),0) AS low_stock_items
            FROM inventory_items WHERE branch_id = %s AND is_active = TRUE AND category != 'BOOK'
        """, (branch_id,))
        stats = cursor.fetchone()
    finally:
        cursor.close(); db.close()

    return render_template("registrar_inventory.html",
        items=enhanced_items, stats=stats, search=search,
        category_filter=category_filter, grade_filter=grade_filter, status_filter=status_filter)


@registrar_bp.route("/registrar/inventory/stats-api")
def registrar_inventory_stats_api():
    if session.get("role") != "registrar":
        return jsonify({"error": "Unauthorized"}), 403
    branch_id = session.get("branch_id")
    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cursor.execute("""
            SELECT COUNT(*) AS total_items, COALESCE(SUM(stock_total),0) AS total_stock,
                   COALESCE(SUM(reserved_qty),0) AS total_reserved,
                   COALESCE(SUM(CASE WHEN (stock_total - reserved_qty) < 10 THEN 1 ELSE 0 END),0) AS low_stock_items
            FROM inventory_items WHERE branch_id = %s AND is_active = TRUE AND category != 'BOOK'
        """, (branch_id,))
        stats = cursor.fetchone()
        total_stock = int(stats['total_stock'] or 0)
        reserved = int(stats['total_reserved'] or 0)
        return jsonify({"total_items": stats['total_items'], "total_stock": total_stock,
                        "reserved": reserved, "available": total_stock - reserved, "low_stock": stats['low_stock_items']})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close(); db.close()


@registrar_bp.route("/registrar/inventory/add", methods=["GET", "POST"])
def registrar_inventory_add():
    if session.get("role") != "registrar":
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
        sizes = request.form.getlist("sizes")
        price = (request.form.get("price") or "").strip()
        stock_total = (request.form.get("stock_total") or "").strip()
        image_url = (request.form.get("image_url") or "").strip() or None

        if not (category and item_name and price and stock_total):
            flash("Missing required fields", "error")
            return redirect("/registrar/inventory/add")

        if category == "UNIFORM" and not image_url:
            uniform_images = {
                'Pre-Elementary Boys Set': '/static/img/PRE_ELEM_BOYS_SET.jpg',
                'Pre-Elementary Girls Set': '/static/img/PRE_ELEM_GIRLS_SET.jpg',
                'Elementary G4-6 Boys Set': '/static/img/ELEM_G4to6_BOYS_SET.jpg',
                'JHS Boys Uniform Set': '/static/img/JHS_BOYS_SET.jpg',
                'JHS Girls Uniform Set': '/static/img/JHS_GIRLS_SET.jpg',
                'SHS Boys Uniform Set': '/static/img/SHS_BOYS_SET.jpg',
                'SHS Girls Uniform Set': '/static/img/SHS_GIRLS_SET.jpg',
                'PE Uniform': '/static/img/PE_SET.jpg'
            }
            if item_name in uniform_images:
                image_url = uniform_images[item_name]

        db = get_db_connection()
        cursor = db.cursor()
        try:
            total_initial_stock = (len(sizes) * int(stock_total)) if sizes else int(stock_total)
            cursor.execute("""
                INSERT INTO inventory_items
                (branch_id, category, item_name, grade_level, is_common, size_label,
                 price, stock_total, reserved_qty, image_url, is_active)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,0,%s,TRUE) RETURNING item_id
            """, (branch_id, category, item_name, grade_level, is_common, size_label, price, total_initial_stock, image_url))
            item_id = cursor.fetchone()[0]
            for sz in sizes:
                cursor.execute("INSERT INTO inventory_item_sizes (item_id, size_label, stock_total, reserved_qty) VALUES (%s, %s, %s, 0)", (item_id, sz, int(stock_total)))
            db.commit()
            flash("Item added successfully!", "success")
            return redirect("/registrar/inventory?category=" + category)
        except Exception as e:
            db.rollback()
            flash(f"Failed to add item: {e}", "error")
        finally:
            cursor.close(); db.close()

    return render_template("registrar_inventory_add.html", message=message, error=error)


@registrar_bp.route("/registrar/inventory/<int:item_id>/restock", methods=["GET", "POST"])
def registrar_inventory_restock(item_id):
    if session.get("role") != "registrar":
        return redirect("/")
    branch_id = session.get("branch_id")
    error = None
    message = None
    item = None
    size_rows = []

    db = get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute("SELECT item_id, item_name, category, stock_total, reserved_qty, price FROM inventory_items WHERE item_id = %s AND branch_id = %s LIMIT 1", (item_id, branch_id))
        item = cursor.fetchone()
        if not item:
            return "Item not found", 404

        cursor.execute("SELECT size_id, size_label, stock_total, reserved_qty FROM inventory_item_sizes WHERE item_id = %s", (item_id,))
        size_rows = sorted(cursor.fetchall() or [], key=lambda r: _size_sort_key(r[1]))

        if request.method == "POST":
            action = (request.form.get("action") or "").strip()
            if action == "create_sizes":
                created = _ensure_default_sizes_exist(cursor, item_id)
                _recompute_item_totals_from_sizes(cursor, item_id, branch_id)
                db.commit()
                flash("✅ Size rows created (XS-XXL)." if created else "Sizes already exist.", "success" if created else "info")
                return redirect(url_for("registrar.registrar_inventory_restock", item_id=item_id))

            size_label = (request.form.get("size_label") or "").strip().upper()
            add_stock = (request.form.get("add_stock") or "").strip()
            if not size_label: raise Exception("Please select a size (XS-XXL).")
            if not add_stock: raise Exception("Please enter stock quantity to add.")
            add_stock = int(add_stock)
            if add_stock <= 0: raise Exception("Stock quantity must be greater than 0.")

            cursor.execute("SELECT 1 FROM inventory_item_sizes WHERE item_id = %s AND UPPER(size_label) = %s LIMIT 1", (item_id, size_label))
            if not cursor.fetchone(): raise Exception("Selected size row does not exist. Click 'Create default sizes' first.")

            cursor.execute("UPDATE inventory_item_sizes SET stock_total = stock_total + %s WHERE item_id = %s AND UPPER(size_label) = %s", (add_stock, item_id, size_label))
            _recompute_item_totals_from_sizes(cursor, item_id, branch_id)
            db.commit()
            flash(f"✅ Restocked {add_stock} for size {size_label}.", "success")
            return redirect(url_for("registrar.registrar_inventory_restock", item_id=item_id))

        cursor.execute("SELECT size_id, size_label, stock_total, reserved_qty FROM inventory_item_sizes WHERE item_id = %s", (item_id,))
        size_rows = sorted(cursor.fetchall() or [], key=lambda r: _size_sort_key(r[1]))

    except Exception as e:
        db.rollback()
        error = str(e)
        flash(error, "error")
    finally:
        cursor.close(); db.close()

    return render_template("registrar_inventory_restock.html",
        item=item, size_rows=size_rows, size_order=SIZE_ORDER, message=message, error=error)


@registrar_bp.route("/registrar/inventory/<int:item_id>/price", methods=["GET", "POST"])
def registrar_inventory_price(item_id):
    if session.get("role") != "registrar":
        return redirect("/")
    branch_id = session.get("branch_id")
    message = None
    error = None
    item = None

    db = get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute("SELECT item_id, item_name, category, price, stock_total FROM inventory_items WHERE item_id = %s AND branch_id = %s", (item_id, branch_id))
        item = cursor.fetchone()
        if not item:
            return "Item not found", 404
        if request.method == "POST":
            new_price = (request.form.get("new_price") or "").strip()
            if not new_price: raise Exception("Please enter new price")
            new_price = float(new_price)
            if new_price <= 0: raise Exception("Price must be greater than 0")
            cursor.execute("UPDATE inventory_items SET price = %s WHERE item_id = %s AND branch_id = %s", (new_price, item_id, branch_id))
            db.commit()
            flash("Price updated successfully!", "success")
            cursor.execute("SELECT item_id, item_name, category, price, stock_total FROM inventory_items WHERE item_id = %s AND branch_id = %s", (item_id, branch_id))
            item = cursor.fetchone()
    except Exception as e:
        db.rollback()
        error = str(e)
        flash(error, "error")
    finally:
        cursor.close(); db.close()

    return render_template("registrar_inventory_price.html", item=item, message=message, error=error)


@registrar_bp.route("/registrar/inventory/<int:item_id>/toggle", methods=["POST"])
def registrar_inventory_toggle(item_id):
    if session.get("role") != "registrar":
        return redirect("/")
    branch_id = session.get("branch_id")
    db = get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute("UPDATE inventory_items SET is_active = NOT is_active WHERE item_id = %s AND branch_id = %s", (item_id, branch_id))
        db.commit()
        flash("Item status updated.", "success")
    except Exception:
        db.rollback()
        flash("Failed to toggle item.", "error")
    finally:
        cursor.close(); db.close()
    return redirect(request.referrer or "/registrar/inventory?category=UNIFORM")


@registrar_bp.route("/registrar/inventory/<int:item_id>/delete", methods=["POST"])
def registrar_inventory_delete(item_id):
    if session.get("role") != "registrar":
        return redirect("/")
    branch_id = session.get("branch_id")
    db = get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute("DELETE FROM inventory_item_sizes WHERE item_id = %s", (item_id,))
        cursor.execute("DELETE FROM inventory_items WHERE item_id = %s AND branch_id = %s", (item_id, branch_id))
        db.commit()
        flash("Item permanently deleted.", "success")
    except Exception as e:
        db.rollback()
        flash(f"Failed to delete item: {str(e)}", "error")
    finally:
        cursor.close(); db.close()
    return redirect(request.referrer or "/registrar/inventory?category=UNIFORM")

@registrar_bp.route("/registrar/assign-students", methods=["GET", "POST"])
def registrar_assign_students():
    if session.get("role") != "registrar":
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
            return redirect(url_for("registrar.registrar_home"))

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
                return redirect(url_for("registrar.registrar_assign_students", grade=grade_filter))

            if section_id:
                cursor.execute("""
                    SELECT capacity, (SELECT COUNT(*) FROM enrollments WHERE section_id = s.section_id AND status IN ('approved', 'enrolled')) AS current_count
                    FROM sections s JOIN school_years y ON s.year_id = y.year_id
                    WHERE s.section_id=%s AND s.branch_id=%s AND y.is_active = TRUE
                """, (section_id, branch_id))
                sec_info = cursor.fetchone()
                if not sec_info:
                    flash("Section not found.", "error")
                    return redirect(url_for("registrar.registrar_assign_students", grade=grade_filter))
                if sec_info['current_count'] >= sec_info['capacity']:
                    flash("Section is full.", "error")
                    return redirect(url_for("registrar.registrar_assign_students", grade=grade_filter))

            cursor.execute("UPDATE enrollments SET section_id=%s, status = CASE WHEN %s IS NOT NULL AND status = 'approved' THEN 'enrolled' ELSE status END WHERE enrollment_id=%s AND year_id=%s", (section_id, section_id, enrollment_id, active_year_id))
            db.commit()
            flash("Student section updated!", "success")
            return redirect(url_for("registrar.registrar_assign_students", grade=grade_filter))

        cursor.execute("SELECT s.section_id, s.section_name, g.name AS grade_level_name, g.id AS grade_level_id, s.capacity, (SELECT COUNT(*) FROM enrollments e2 WHERE e2.section_id = s.section_id AND e2.status IN ('approved', 'enrolled')) AS current_count FROM sections s JOIN grade_levels g ON s.grade_level_id = g.id JOIN school_years y ON s.year_id = y.year_id WHERE s.branch_id = %s AND y.is_active = TRUE ORDER BY g.display_order, s.section_name", (branch_id,))
        all_sections = cursor.fetchall() or []
        filtered_sections = [s for s in all_sections if str(s['grade_level_id']) == grade_filter]

        grade_name = ""
        if grade_filter:
            cursor.execute("SELECT name FROM grade_levels WHERE id = %s AND branch_id = %s", (grade_filter, branch_id))
            grade_row = cursor.fetchone()
            grade_name = grade_row['name'] if grade_row else ""

        cursor.execute("""
            SELECT e.enrollment_id, e.student_name, e.grade_level, e.branch_enrollment_no, e.section_id, s.section_name
            FROM enrollments e LEFT JOIN sections s ON e.section_id = s.section_id
            WHERE e.branch_id = %s AND e.year_id = %s AND e.status IN ('approved', 'enrolled') AND (e.grade_level ILIKE %s OR e.grade_level ILIKE %s)
            ORDER BY e.student_name
        """, (branch_id, active_year_id, grade_name, grade_name.replace("Grade ", "")))
        students = cursor.fetchall() or []

    except Exception as e:
        db.rollback()
        flash(f"Error: {str(e)}", "error")
        grade_options, filtered_sections, students = [], [], []
    finally:
        cursor.close(); db.close()

    return render_template(
        "registrar_assign_students.html",
        grade_options=grade_options,
        sections=filtered_sections,
        students=students,
        grade_filter=grade_filter
    )

@registrar_bp.route("/registrar/api/assign-student-section", methods=["POST"])
def registrar_api_assign_student_section():
    if session.get("role") != "registrar":
        return {"error": "Unauthorized"}, 403
    branch_id = session.get("branch_id")
    data = request.get_json()
    enrollment_id = data.get("enrollment_id")
    section_id = data.get("section_id")

    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cursor.execute("SELECT year_id FROM school_years WHERE branch_id = %s AND is_active = TRUE LIMIT 1", (branch_id,))
        row = cursor.fetchone()
        active_year_id = row["year_id"] if row else None
        if not active_year_id: return {"success": False, "message": "No active school year"}, 400

        cursor.execute("UPDATE enrollments SET section_id=%s, status = CASE WHEN %s IS NOT NULL AND status = 'approved' THEN 'enrolled' ELSE status END WHERE enrollment_id=%s AND branch_id=%s AND year_id=%s", (section_id, section_id, enrollment_id, branch_id, active_year_id))
        db.commit()
        return {"success": True}
    except Exception as e:
        db.rollback()
        return {"success": False, "message": str(e)}, 500
    finally:
        cursor.close(); db.close()



# ══════════════════════════════════════════════════════
# MANAGE TEACHERS — Registrar Module
# ══════════════════════════════════════════════════════

def _ensure_teacher_tables(cursor):
    cursor.execute("""
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS teacher_type VARCHAR(20) DEFAULT 'advisory',
        ADD COLUMN IF NOT EXISTS specialization_subject VARCHAR(100),
        ADD COLUMN IF NOT EXISTS department VARCHAR(50)
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS teacher_grade_levels (
            id             SERIAL PRIMARY KEY,
            teacher_id     INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
            grade_level_id INTEGER NOT NULL REFERENCES grade_levels(id) ON DELETE CASCADE,
            UNIQUE(teacher_id, grade_level_id)
        )
    """)


@registrar_bp.route("/registrar/manage-teachers", methods=["GET", "POST"])
def registrar_manage_teachers():
    if session.get("role") != "registrar":
        return redirect("/")

    branch_id     = session.get("branch_id")
    created_user  = None
    filter_search = request.args.get("search", "").strip()
    filter_type   = request.args.get("type",   "advisory").strip()
    if filter_type not in ['advisory', 'subject']:
        filter_type = 'advisory'

    db     = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        _ensure_teacher_tables(cursor)
        db.commit()

        cursor.execute(
            "SELECT id, name FROM grade_levels WHERE branch_id = %s ORDER BY display_order",
            (branch_id,)
        )
        grades = cursor.fetchall() or []

        if request.method == "POST":
            full_name      = (request.form.get("full_name")    or "").strip()
            gender         = (request.form.get("gender")       or "").strip().lower()
            user_email     = (request.form.get("email")        or "").strip()
            custom_uname   = (request.form.get("username")     or "").strip()
            teacher_type   = (request.form.get("teacher_type") or "advisory").strip()
            grade_level_id = (request.form.get("grade_level")  or "").strip() or None
            
            # New fields for all teachers
            spec_subject = (request.form.get("specialization_subject") or "").strip()
            department   = (request.form.get("department") or "").strip()

            if not full_name:
                flash("Full name is required.", "error")
                return redirect("/registrar/manage-teachers")
            if gender not in ("male", "female"):
                flash("Please select a gender.", "error")
                return redirect("/registrar/manage-teachers")
            if not user_email:
                flash("Email is required.", "error")
                return redirect("/registrar/manage-teachers")
            if custom_uname and not re.match(r'^[A-Za-z0-9_]+$', custom_uname):
                flash("Username can only contain letters, numbers, and underscores.", "error")
                return redirect("/registrar/manage-teachers")
            
            if teacher_type == "subject":
                if not spec_subject:
                    flash("Specialization subject is required for Subject Teachers.", "error")
                    return redirect("/registrar/manage-teachers")
                if not department:
                    flash("Department is required for Subject Teachers.", "error")
                    return redirect("/registrar/manage-teachers")

            cursor.execute("SELECT branch_code FROM branches WHERE branch_id=%s", (branch_id,))
            b_row = cursor.fetchone()
            branch_code = ((b_row['branch_code'] or "") if b_row else "").strip().upper()
            if not branch_code:
                flash("Branch code not configured.", "error")
                return redirect("/registrar/manage-teachers")

            if custom_uname:
                base_username = custom_uname
            else:
                grade_suffix = ""
                # For base username, we just pick the primary grade if advisory, or no suffix for subject
                ref_grade_id = grade_level_id if teacher_type == "advisory" else None
                if ref_grade_id:
                    cursor.execute("SELECT name FROM grade_levels WHERE id=%s", (ref_grade_id,))
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
                base_username = f"{branch_code}_Teacher{grade_suffix}" if grade_suffix else f"{branch_code}_Teacher"

            username = base_username
            suffix_counter = 2
            while True:
                cursor.execute("SELECT 1 FROM users WHERE username=%s", (username,))
                if not cursor.fetchone():
                    break
                if custom_uname:
                    flash(f"Username '{username}' already exists.", "error")
                    return redirect("/registrar/manage-teachers")
                username = f"{base_username}_{suffix_counter}"
                suffix_counter += 1

            temp_password   = generate_password()
            hashed_password = generate_password_hash(temp_password)
            primary_grade   = grade_level_id if teacher_type == "advisory" else None

            cursor.execute("""
                INSERT INTO users
                    (branch_id, username, password, role, require_password_change,
                     grade_level_id, full_name, gender, email, teacher_type,
                     specialization_subject, department)
                VALUES (%s, %s, %s, 'teacher', TRUE, %s, %s, %s, %s, %s, %s, %s)
                RETURNING user_id
            """, (branch_id, username, hashed_password,
                  primary_grade, full_name, gender, user_email, teacher_type,
                  spec_subject, department))
            new_user_id = cursor.fetchone()['user_id']

            # Map department to grades for both types if department is provided
            if department:
                for g in grades:
                    name = g['name'].lower()
                    num_match = re.search(r'\d+', name)
                    num = int(num_match.group(0)) if num_match else None
                    
                    match = False
                    if department == 'elementary':
                        if num is None and ('nursery' in name or 'kinder' in name): match = True
                        elif num is not None and 1 <= num <= 6: match = True
                    elif department == 'jhs':
                        if num is not None and 7 <= num <= 10: match = True
                    elif department == 'shs':
                        if num is not None and 11 <= num <= 12: match = True
                    
                    if match:
                        try:
                            cursor.execute("""
                                INSERT INTO teacher_grade_levels (teacher_id, grade_level_id)
                                VALUES (%s, %s) ON CONFLICT DO NOTHING
                            """, (new_user_id, g['id']))
                        except Exception:
                            pass

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
                send_email(user_email, subject_line, body)
                flash(f"Teacher account created. Credentials sent to {user_email}.", "success")
            else:
                flash("Teacher account created successfully!", "success")

        query = """
            SELECT
                u.user_id, u.username, u.full_name, u.gender, u.email,
                COALESCE(u.status, 'active') AS status,
                COALESCE(u.teacher_type, 'advisory') AS teacher_type,
                COALESCE(g.name, '') AS primary_grade,
                u.specialization_subject,
                u.department,
                (
                    SELECT STRING_AGG(DISTINCT s.section_name, ', ')
                    FROM section_teachers st
                    JOIN sections s ON st.section_id = s.section_id
                    WHERE st.teacher_id = u.user_id
                ) AS assigned_sections
            FROM users u
            LEFT JOIN grade_levels g ON u.grade_level_id = g.id
            WHERE u.branch_id = %s AND u.role = 'teacher'
        """
        params = [branch_id]
        if filter_search:
            query += " AND (u.full_name ILIKE %s OR u.username ILIKE %s)"
            params.extend([f"%{filter_search}%", f"%{filter_search}%"])
        
        # Always filter by type now that 'All' is removed
        actual_type = filter_type if filter_type in ['advisory', 'subject'] else 'advisory'
        query += " AND COALESCE(u.teacher_type,'advisory') = %s"
        params.append(actual_type)
        
        query += " ORDER BY u.full_name"
        cursor.execute(query, params)
        teachers = cursor.fetchall() or []

        cursor.execute("""
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE COALESCE(teacher_type,'advisory') = 'advisory') AS advisory_count,
                COUNT(*) FILTER (WHERE teacher_type = 'subject') AS subject_count,
                COUNT(*) FILTER (WHERE COALESCE(status,'active') = 'active') AS active_count
            FROM users WHERE branch_id = %s AND role = 'teacher'
        """, (branch_id,))
        stats = cursor.fetchone()

    except Exception as e:
        db.rollback()
        flash(f"An error occurred: {str(e)}", "error")
        teachers, grades, stats = [], [], None
    finally:
        cursor.close()
        db.close()

    return render_template(
        "registrar_manage_teachers.html",
        teachers=teachers,
        grades=grades,
        stats=stats,
        filter_search=filter_search,
        filter_type=filter_type
    )


@registrar_bp.route("/registrar/manage-teachers/<int:user_id>/toggle", methods=["POST"])
def registrar_toggle_teacher(user_id):
    if session.get("role") != "registrar":
        return redirect("/")
    db = get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute("""
            UPDATE users
            SET status = CASE WHEN COALESCE(status,'active') = 'active' THEN 'inactive' ELSE 'active' END
            WHERE user_id = %s AND branch_id = %s AND role = 'teacher'
        """, (user_id, session.get("branch_id")))
        db.commit()
        flash("Teacher status updated.", "success")
    except Exception as e:
        db.rollback()
        flash(f"Failed: {str(e)}", "error")
    finally:
        cursor.close(); db.close()
    return redirect(request.referrer or "/registrar/manage-teachers")


@registrar_bp.route("/registrar/manage-teachers/<int:user_id>/delete", methods=["POST"])
def registrar_delete_teacher(user_id):
    if session.get("role") != "registrar":
        return redirect("/")
    db = get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute("DELETE FROM teacher_grade_levels WHERE teacher_id = %s", (user_id,))
        cursor.execute(
            "DELETE FROM users WHERE user_id = %s AND branch_id = %s AND role = 'teacher'",
            (user_id, session.get("branch_id"))
        )
        db.commit()
        flash("Teacher account permanently deleted.", "success")
    except Exception as e:
        db.rollback()
        flash(f"Failed to delete: {str(e)}", "error")
    finally:
        cursor.close(); db.close()
    return redirect("/registrar/manage-teachers")

