from flask import Blueprint, render_template, session, redirect, request, flash, url_for
from db import get_db_connection, is_branch_active
from werkzeug.security import generate_password_hash
import secrets
import string
import logging
import psycopg2.extras
import json
from utils.send_email import send_email
from flask import abort

# Setup logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

registrar_bp = Blueprint("registrar", __name__)

def generate_password(length=8):
    characters = string.ascii_letters + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))


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

        # --- YEAR SWITCHER (view context) ---
        selected_year_id = request.args.get("year_id", type=int) or active_year_id

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
            flash(
                f"Enrollment #{display_no} {'approved' if action == 'approved' else 'rejected'}.",
                "success" if action == "approved" else "warning"
            )

        # --- NEW enrollments list (VIEW selected year) ---
        cursor.execute("""
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
            WHERE e.branch_id=%s
              AND e.year_id=%s
              AND e.status IN ('pending', 'rejected')
            GROUP BY e.enrollment_id
            ORDER BY e.branch_enrollment_no ASC NULLS LAST, e.created_at DESC
        """, (branch_id, selected_year_id))
        new_enrollments_raw = cursor.fetchall()

        new_enrollments = []
        for e in new_enrollments_raw:
            e = dict(e)
            if isinstance(e["documents"], str):
                e["documents"] = json.loads(e["documents"])
            new_enrollments.append(e)

        # --- ENROLLED students list (VIEW selected year) ---
        cursor.execute("""
            SELECT e.*,
                   e.branch_enrollment_no AS display_no,
                   s.section_name,
                   CASE WHEN sa.enrollment_id IS NOT NULL THEN TRUE ELSE FALSE END AS has_student_account,
                   CASE WHEN ps.student_id   IS NOT NULL THEN TRUE ELSE FALSE END AS has_parent_account,
                   u.username AS parent_username
            FROM enrollments e
            LEFT JOIN sections s          ON s.section_id    = e.section_id
            LEFT JOIN student_accounts sa ON sa.enrollment_id = e.enrollment_id
            LEFT JOIN parent_student ps   ON ps.student_id   = e.enrollment_id
            LEFT JOIN users u             ON u.user_id        = ps.parent_id
            WHERE e.branch_id=%s
              AND e.year_id=%s
              AND e.status IN ('enrolled', 'open_for_enrollment', 'approved')
            ORDER BY e.grade_level ASC, e.student_name ASC
        """, (branch_id, selected_year_id))
        enrolled_students = cursor.fetchall()

        grade_levels = [
            "Nursery", "Kinder", "Grade 1", "Grade 2", "Grade 3", "Grade 4",
            "Grade 5", "Grade 6", "Grade 7", "Grade 8", "Grade 9", "Grade 10",
            "Grade 11", "Grade 12"
        ]

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
                    # dob needs special handling for empty string
                    if f == "dob" and not val:
                        val = None
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
            return redirect(f"/registrar/enrollment/{enrollment_id}")

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

        return render_template(
            "registrar_enrollment_detail.html",
            enrollment=enrollment,
            documents=documents,
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
                subject = "Your Student Account Credentials"
                body = f"""
Dear {enrollment.get('student_name')},

Your student account has been created.

Username: {username}
Temporary Password: {temp_password}

You can log in at: https://liceolms.up.railway.app/

Please change your password after logging in!

Regards,
Registrar
"""
                send_email(student_email, subject, body)

            return render_template(
                "account_created.html",
                account_type="student",
                student_name=enrollment.get("student_name"),
                enrollment_id=enrollment.get("branch_enrollment_no") or enrollment_id,
                username=username,
                password=temp_password
            )
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
                subject = "Your Parent Account Credentials"
                body = f"""
Dear Parent/Guardian of {enrollment.get('student_name')},

Your parent account has been created.

Username: {username}
Temporary Password: {temp_password}

Student LMS Username: {student_username or '[See Registrar]'}
Temporary Password: {student_temp_password or '[See Registrar or previous email]'}

You can log in at: https://liceolms.up.railway.app/

Please change your password after logging in!

Regards,
Registrar
"""
                send_email(parent_email, subject, body)

            return render_template(
                "account_created.html",
                account_type="parent",
                student_name=enrollment.get("student_name"),
                enrollment_id=enrollment.get("branch_enrollment_no") or enrollment_id,
                username=username,
                password=temp_password
            )
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

    try:
        if request.method == "POST":
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

                    if user_type == 'student':
                        # Update enrollments and if they have user account, update users too
                        cursor.execute("UPDATE enrollments SET profile_image = %s WHERE enrollment_id = %s", (file_url, target_id))
                        
                        # See if student account exists to update users table as well
                        cursor.execute("""
                            SELECT user_id FROM enrollments WHERE enrollment_id = %s
                        """, (target_id,))
                        row = cursor.fetchone()
                        if row and row['user_id']:
                            cursor.execute("UPDATE users SET profile_image = %s WHERE user_id = %s", (file_url, row['user_id']))

                    elif user_type == 'teacher':
                        cursor.execute("UPDATE users SET profile_image = %s WHERE user_id = %s", (file_url, target_id))
                    
                    db.commit()
                    flash("Profile picture uploaded successfully!", "success")
                except Exception as e:
                    db.rollback()
                    flash(f"Error uploading image: {e}", "error")
            else:
                flash("Invalid file type. Allowed: png, jpg, jpeg, gif", "error")

            # redirect back to same tab/filter
            return redirect(request.referrer or url_for('registrar.registrar_profile_pictures'))

        # GET request
        tab = request.args.get("tab", "students")
        grade_filter = request.args.get("grade", "")
        section_filter = request.args.get("section_id", "")

        students = []
        teachers = []
        all_grades = []
        all_sections = []

        if tab == "students":
            # Get grades for filter
            all_grades = [
                "Nursery", "Kinder", "Grade 1", "Grade 2", "Grade 3", "Grade 4", 
                "Grade 5", "Grade 6", "Grade 7", "Grade 8", "Grade 9", "Grade 10", 
                "Grade 11", "Grade 12"
            ]

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
                       s.section_name, e.profile_image, e.status
                FROM enrollments e
                LEFT JOIN sections s ON e.section_id = s.section_id
                WHERE e.branch_id = %s AND e.status IN ('enrolled', 'approved', 'open_for_enrollment')
            """
            params = [branch_id]
            
            if grade_filter:
                query += " AND e.grade_level = %s"
                params.append(grade_filter)
            if section_filter:
                query += " AND e.section_id = %s"
                params.append(section_filter)

            # Sort by Logical Grade Level then by Student Name
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

        all_grades = [
            "Nursery", "Kinder", "Grade 1", "Grade 2", "Grade 3", "Grade 4", 
            "Grade 5", "Grade 6", "Grade 7", "Grade 8", "Grade 9", "Grade 10", 
            "Grade 11", "Grade 12"
        ]

        cursor.execute("""
            SELECT s.section_id, s.section_name, g.name AS grade_level
            FROM sections s
            JOIN grade_levels g ON g.id = s.grade_level_id
            WHERE s.branch_id = %s
            ORDER BY g.id, s.section_name
        """, (branch_id,))
        all_sections = cursor.fetchall()

        query = """
            SELECT e.*, s.section_name,
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
            WHERE e.branch_id = %s 
              AND e.status IN ('enrolled', 'approved', 'open_for_enrollment')
        """
        params = [branch_id]

        if grade_filter:
            query += " AND e.grade_level = %s"
            params.append(grade_filter)
            if section_filter:
                query += " AND e.section_id = %s"
                params.append(section_filter)

        query += """
            GROUP BY e.enrollment_id, s.section_name
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
            section_filter=section_filter
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

    if request.method == "POST":
        combo = request.form["combo"]
        section_id, subject_id, teacher_id = combo.split('|')
        day_of_week = request.form["day_of_week"]
        start_time = request.form["start_time"]
        end_time = request.form["end_time"]
        room = request.form["room"]
        year_id = request.form["year_id"]

        # --- TIME VALIDATION: must be within 07:00 and 23:00, and start < end ---
        start_t = datetime.strptime(start_time, "%H:%M").time()
        end_t = datetime.strptime(end_time, "%H:%M").time()
        if not (time(7,0) <= start_t <= time(23,0)) or not (time(7,0) <= end_t <= time(23,0)):
            flash("Invalid schedule: Times must be between 07:00 and 23:00.", "danger")
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

    # List all schedules for this branch's sections 
    cursor.execute("""
        SELECT s.*, subj.name AS subject_name, sec.section_name AS section_name, 
               u.full_name AS teacher_name, y.label AS year_label
        FROM schedules s
        JOIN subjects subj ON s.subject_id = subj.subject_id
        JOIN sections sec ON s.section_id = sec.section_id
        JOIN users u ON s.teacher_id = u.user_id
        JOIN school_years y ON s.year_id = y.year_id
        WHERE s.branch_id = %s
          AND y.branch_id = %s
          AND y.is_active = TRUE
        ORDER BY y.label DESC, sec.section_name, subj.name, s.day_of_week, s.start_time
    """, (branch_id, branch_id))
    schedules = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "schedules_allinone.html",
        schedules=schedules,
        combinations=combinations,
        school_years=school_years
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

    if request.method == "POST":
        combo = request.form["combo"]
        section_id, subject_id, teacher_id = combo.split('|')
        day_of_week = request.form["day_of_week"]
        start_time = request.form["start_time"]
        end_time = request.form["end_time"]
        room = request.form["room"]
        year_id = request.form["year_id"]

        # --- TIME VALIDATION: must be within 07:00 and 23:00, and start < end ---
        start_t = datetime.strptime(start_time, "%H:%M").time()
        end_t = datetime.strptime(end_time, "%H:%M").time()
        if not (time(7,0) <= start_t <= time(23,0)) or not (time(7,0) <= end_t <= time(23,0)):
            flash("Invalid schedule: Times must be between 07:00 and 23:00.", "danger")
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
        """, (subject_id, section_id, teacher_id, day_of_week, start_time, end_time, room, year_id, schedule_id, branch_id))
        db.commit()
        cursor.close(); db.close()
        flash("Schedule updated!", "success")
        return redirect(url_for("registrar.list_and_add_schedules"))

    cursor.close(); db.close()
    return render_template(
        "schedule_edit.html",
        schedule=schedule,
        combinations=combinations,
        school_years=school_years
    )


@registrar_bp.route("/registrar/schedules/<int:schedule_id>/delete", methods=["POST"])
def delete_schedule(schedule_id):
    db = get_db_connection()
    cursor = db.cursor()
    branch_id = session.get("branch_id")
    cursor.execute("""
        DELETE FROM schedules WHERE schedule_id = %s AND branch_id = %s
    """, (schedule_id, branch_id))
    db.commit()
    cursor.close(); db.close()
    flash("Schedule deleted.", "success")
    return redirect(url_for("registrar.list_and_add_schedules"))
# ══════════════════════════════════════════
# NO CACHE
# ══════════════════════════════════════════

@registrar_bp.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response