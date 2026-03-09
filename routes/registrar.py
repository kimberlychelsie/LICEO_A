from flask import Blueprint, render_template, session, redirect, request, flash
from db import get_db_connection
from werkzeug.security import generate_password_hash
import secrets
import string
import logging
import psycopg2.extras

# Setup logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

registrar_bp = Blueprint("registrar", __name__)

def generate_password(length=8):
    """Generate a cryptographically secure random password"""
    characters = string.ascii_letters + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))


@registrar_bp.route("/registrar", methods=["GET", "POST"])
def registrar_dashboard():
    if session.get("role") != "registrar":
        return redirect("/")

    branch_id = session.get("branch_id")
    if not branch_id:
        flash("Missing branch in session. Please login again.", "error")
        return redirect("/logout")

    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        # Handle Approve/Reject actions for NEW enrollments
        if request.method == "POST":
            enrollment_id = request.form.get("enrollment_id")
            action = request.form.get("action")  # 'approved' or 'rejected'

            if not enrollment_id:
                flash("Missing enrollment ID", "error")
                return redirect("/registrar")

            if action not in ("approved", "rejected"):
                flash("Invalid action", "error")
                return redirect("/registrar")

            cursor.execute("""
                UPDATE enrollments
                SET status=%s
                WHERE enrollment_id=%s AND branch_id=%s
            """, (action, enrollment_id, branch_id))

            if cursor.rowcount == 0:
                db.rollback()
                flash("Enrollment not found for your branch.", "error")
                return redirect("/registrar")

            db.commit()

            cursor.execute("""
                SELECT branch_enrollment_no AS display_no
                FROM enrollments WHERE enrollment_id=%s
            """, (enrollment_id,))
            disp_row = cursor.fetchone()
            display_no = disp_row["display_no"] if disp_row else "???"

            if action == "approved":
                flash(f"Enrollment #{display_no} approved successfully", "success")
            else:
                flash(f"Enrollment #{display_no} rejected", "warning")

        # ── NEW enrollments (pending / approved / rejected — not yet fully enrolled)
        cursor.execute("""
            SELECT *,
                   branch_enrollment_no AS display_no
            FROM enrollments
            WHERE branch_id=%s AND status IN ('pending', 'approved', 'rejected')
            ORDER BY branch_enrollment_no ASC NULLS LAST, created_at DESC
        """, (branch_id,))
        new_enrollments = cursor.fetchall()

        for enrollment in new_enrollments:
            eid = enrollment["enrollment_id"]
            cursor.execute("SELECT * FROM enrollment_documents WHERE enrollment_id=%s", (eid,))
            enrollment["documents"] = cursor.fetchall()

            cursor.execute("SELECT 1 FROM student_accounts WHERE enrollment_id=%s", (eid,))
            enrollment["has_student_account"] = cursor.fetchone() is not None

            cursor.execute("""
                SELECT ps.*, u.username FROM parent_student ps
                JOIN users u ON ps.parent_id = u.user_id
                WHERE ps.student_id = %s
            """, (eid,))
            parent_link = cursor.fetchone()
            enrollment["has_parent_account"] = parent_link is not None
            enrollment["parent_username"] = parent_link["username"] if parent_link else None

        # ── ENROLLED students (enrolled + open_for_enrollment)
        cursor.execute("""
            SELECT e.*,
                   e.branch_enrollment_no AS display_no,
                   s.section_name
            FROM enrollments e
            LEFT JOIN sections s ON s.section_id = e.section_id
            WHERE e.branch_id=%s AND e.status IN ('enrolled', 'open_for_enrollment')
            ORDER BY e.grade_level ASC, e.student_name ASC
        """, (branch_id,))
        enrolled_students = cursor.fetchall()

        # Grade list for filter dropdown
        grade_levels = sorted(set(
            e["grade_level"] for e in enrolled_students if e.get("grade_level")
        ))

        # Is re-enrollment currently open?
        reenrollment_open = any(
            e["status"] == "open_for_enrollment" for e in enrolled_students
        )

        # ── Sections for the assign-section modal
        cursor.execute("""
            SELECT s.section_id,
           s.section_name,
           g.name AS grade_level_name,
           CONCAT(g.name, ' — ', s.section_name) AS section_display
    FROM sections s
    JOIN grade_levels g ON g.id = s.grade_level_id
    WHERE s.branch_id = %s
    ORDER BY g.name, s.section_name
        """, (branch_id,))
        section_options = cursor.fetchall()

        return render_template(
            "registrar_dashboard.html",
            new_enrollments=new_enrollments,
            enrolled_students=enrolled_students,
            grade_levels=grade_levels,
            reenrollment_open=reenrollment_open,
            section_options=section_options,
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Registrar dashboard error: {str(e)}")
        flash("Something went wrong in registrar dashboard. Please try again.", "error")
        return redirect("/registrar")

    finally:
        cursor.close()
        db.close()


@registrar_bp.route("/registrar/toggle-reenrollment", methods=["POST"])
def toggle_reenrollment():
    if session.get("role") != "registrar":
        return redirect("/")

    branch_id = session.get("branch_id")
    if not branch_id:
        flash("Missing branch in session.", "error")
        return redirect("/logout")

    action = request.form.get("action")  # 'open' or 'close'
    if action not in ("open", "close"):
        flash("Invalid action.", "error")
        return redirect("/registrar")

    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        if action == "open":
            cursor.execute("""
                UPDATE enrollments
                SET status = 'open_for_enrollment'
                WHERE branch_id = %s AND status = 'enrolled'
            """, (branch_id,))
            count = cursor.rowcount
            db.commit()
            flash(f"Re-enrollment opened for {count} student(s). They can now re-enroll online.", "success")
        else:
            cursor.execute("""
                UPDATE enrollments
                SET status = 'enrolled'
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

    return redirect("/registrar#enrolled")

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
            SELECT *
            FROM enrollments
            WHERE enrollment_id=%s AND branch_id=%s AND status='approved'
        """, (enrollment_id, branch_id))
        enrollment = cursor.fetchone()

        if not enrollment:
            flash("Enrollment not found or not approved", "error")
            return redirect("/registrar")

        cursor.execute("""
            SELECT 1 FROM student_accounts WHERE enrollment_id=%s
        """, (enrollment_id,))
        if cursor.fetchone():
            flash("Student account already exists for this enrollment", "warning")
            return redirect("/registrar")

        cursor.execute("SELECT branch_code FROM branches WHERE branch_id=%s", (branch_id,))
        brow = cursor.fetchone()
        branch_code = (brow["branch_code"] if brow and brow.get("branch_code") else "").strip().upper()
        if not branch_code:
            branch_code = f"B{branch_id}"

        branch_no = enrollment.get("branch_enrollment_no") or enrollment_id
        try:
            num = int(branch_no)
            branch_no_str = f"{num:04d}"
        except Exception:
            branch_no_str = str(branch_no)

        username = f"{branch_code}_{branch_no_str}"
        temp_password = generate_password()
        hashed_password = generate_password_hash(temp_password)

        try:
            cursor.execute("""
                INSERT INTO student_accounts
                  (enrollment_id, branch_id, username, password, is_active, require_password_change)
                VALUES
                  (%s, %s, %s, %s, TRUE, TRUE)
            """, (enrollment_id, enrollment["branch_id"], username, hashed_password))
            db.commit()

            # ── Optional: assign section if registrar selected one ──
            section_id = request.form.get("section_id", "").strip()
            if section_id and section_id.isdigit():
                try:
                    # ✅ Verify section belongs to this branch AND matches student's grade level
                    cursor.execute("""
                        SELECT s.section_id
                        FROM sections s
                        JOIN grade_levels g ON s.grade_level_id = g.id
                        WHERE s.section_id = %s
                          AND s.branch_id = %s
                          AND g.name ILIKE %s
                    """, (int(section_id), branch_id, enrollment.get("grade_level", "")))

                    if cursor.fetchone():
                        cursor.execute("""
                            UPDATE enrollments SET section_id = %s
                            WHERE enrollment_id = %s AND branch_id = %s
                        """, (int(section_id), enrollment_id, branch_id))
                        db.commit()
                    else:
                        logger.warning(
                            f"Section {section_id} does not match grade level "
                            f"'{enrollment.get('grade_level')}' — section not assigned."
                        )
                except Exception as e:
                    db.rollback()
                    logger.warning(f"Section assign failed (non-fatal): {str(e)}")

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
            return redirect("/registrar")

    except Exception as e:
        db.rollback()
        logger.error(f"Create student account error: {str(e)}")
        flash("Something went wrong while creating student account.", "error")
        return redirect("/registrar")

    finally:
        cursor.close()
        db.close()


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
            SELECT *
            FROM enrollments
            WHERE enrollment_id=%s AND branch_id=%s AND status='approved'
        """, (enrollment_id, branch_id))
        enrollment = cursor.fetchone()

        if not enrollment:
            flash("Enrollment not found or not approved", "error")
            return redirect("/registrar")

        cursor.execute("""
            SELECT ps.*, u.username
            FROM parent_student ps
            JOIN users u ON ps.parent_id = u.user_id
            WHERE ps.student_id = %s
        """, (enrollment_id,))
        existing_parent = cursor.fetchone()

        if existing_parent:
            flash(
                f"Parent account already exists for this enrollment (Username: {existing_parent['username']})",
                "warning"
            )
            return redirect("/registrar")

        cursor.execute("SELECT branch_code FROM branches WHERE branch_id=%s", (branch_id,))
        brow = cursor.fetchone()
        branch_code = (brow["branch_code"] if brow and brow.get("branch_code") else "").strip().upper()
        if not branch_code:
            branch_code = f"B{branch_id}"

        cursor.execute("""
            SELECT COUNT(*) AS cnt
            FROM users
            WHERE role='parent' AND branch_id=%s AND username ILIKE %s
        """, (branch_id, f"{branch_code}_Parent%"))
        prow = cursor.fetchone() or {}
        next_no = (prow.get("cnt") or 0) + 1

        username = f"{branch_code}_Parent{next_no}"
        temp_password = generate_password()
        hashed_password = generate_password_hash(temp_password)

        try:
            cursor.execute("""
                INSERT INTO users
                  (username, password, role, branch_id, require_password_change)
                VALUES
                  (%s, %s, 'parent', %s, TRUE)
                RETURNING user_id
            """, (username, hashed_password, branch_id))

            parent_id = cursor.fetchone()["user_id"]

            cursor.execute("""
                INSERT INTO parent_student (parent_id, student_id, relationship)
                VALUES (%s, %s, 'guardian')
            """, (parent_id, enrollment_id))

            db.commit()

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
            return redirect("/registrar")

    except Exception as e:
        db.rollback()
        logger.error(f"Create parent account error: {str(e)}")
        flash("Something went wrong while creating parent account.", "error")
        return redirect("/registrar")

    finally:
        cursor.close()
        db.close()


@registrar_bp.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response