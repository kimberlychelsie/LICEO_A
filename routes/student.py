from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.utils import secure_filename
import os
import uuid
import re
import psycopg2.extras
from db import get_db_connection, is_branch_active
from cloudinary_helper import upload_enrollment_document
from rapidfuzz import fuzz
import logging
from utils.send_email import send_email

logger = logging.getLogger(__name__)

student_bp = Blueprint("student", __name__)

ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def is_valid_email(email):
    # Strict email validation: username@domain.com
    # Username: a-z, 0-9, ., _, -
    # Explicitly block #, %, &, spaces
    if not email:
        return False
    import re
    email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(email_regex, email))

def save_doc_file(cursor, enrollment_id, fileobj, doc_type):
    if fileobj and fileobj.filename:
        if not allowed_file(fileobj.filename):
            logger.warning(f"File type not allowed: {fileobj.filename}")
            return False, "Invalid file type. Only PDF, JPG, JPEG, and PNG are allowed."
            
        # Check size
        fileobj.seek(0, os.SEEK_END)
        size = fileobj.tell()
        fileobj.seek(0)
        
        if size > MAX_FILE_SIZE:
            logger.warning(f"File too large: {fileobj.filename} ({size} bytes)")
            return False, f"File '{doc_type}' is too large. Maximum limit is 10MB."

        original = secure_filename(fileobj.filename)
        try:
            url_path = upload_enrollment_document(fileobj)
            cursor.execute("""
                INSERT INTO enrollment_documents (enrollment_id, file_name, file_path, doc_type)
                VALUES (%s, %s, %s, %s)
            """, (enrollment_id, original, url_path, doc_type))
            return True, None
        except Exception as e:
            logger.error(f"Failed to upload document {original}: {e}")
            return False, "Upload failed. Please try again."
    return True, None

# =======================
# GRADE RANGE MAPPINGS
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

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def normalize_grade_level(raw):
    """
    enrollments.grade_level could be '7' (number) or 'Grade 7'
    Convert to 'Grade 7' so it matches GRADE_MAPPINGS.
    """
    raw = str(raw or "").strip()
    if not raw:
        return None

    if raw.isdigit():
        return f"Grade {int(raw)}"

    low = raw.lower()
    if "grade" in low:
        nums = "".join([c for c in raw if c.isdigit()])
        return f"Grade {nums}" if nums else raw

    if "kinder" in low:
        return "Kinder"

    if "nursery" in low:
        return "Nursery"

    return raw


def get_logged_student_grade_level():
    """
    Returns enrollments.grade_level for the logged-in student using enrollment_id
    (NOT students table).
    """
    enrollment_id = session.get("enrollment_id")
    if not enrollment_id:
        return None

    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cursor.execute("""
            SELECT grade_level
            FROM enrollments
            WHERE enrollment_id = %s
            LIMIT 1
        """, (enrollment_id,))
        row = cursor.fetchone()
        return normalize_grade_level(row["grade_level"]) if row else None
    finally:
        cursor.close()
        db.close()


def template_exists(template_name):
    try:
        from flask import current_app
        return template_name in current_app.jinja_loader.list_templates()
    except Exception:
        return False


def render_template_safe(template_name, **context):
    if template_exists(template_name):
        return render_template(template_name, **context)
    else:
        return render_template("template_missing.html", missing=template_name, **context)

def get_active_school_year_id(cursor, branch_id):
    cursor.execute("""
        SELECT year_id
        FROM school_years
        WHERE is_active = TRUE
        AND branch_id = %s
        LIMIT 1
    """, (branch_id,))
    row = cursor.fetchone()
    return row["year_id"] if row else None
# =======================
# DUPLICATE CHECK HELPER
# =======================
def compute_duplicate_score(new_name, new_dob, new_lrn, existing):
    """
    Returns (score, reasons) for a single existing enrollment row.
    Score thresholds: >= 50 → block, 30-49 → (not used currently, reserved)
    """
    score = 0
    reasons = []

    # LRN exact match — strongest signal
    if new_lrn and existing.get("lrn") and new_lrn.strip() == existing["lrn"].strip():
        score += 60
        reasons.append("LRN matches")

    # Birthday exact match
    dob_match = False
    if new_dob and existing.get("dob"):
        existing_dob = str(existing["dob"]).split(" ")[0]  # strip time if any
        if new_dob.strip() == existing_dob.strip():
            dob_match = True
            score += 20
            reasons.append("birthday matches")

    # Fuzzy name match
    if new_name and existing.get("student_name"):
        similarity = fuzz.token_sort_ratio(new_name.lower(), existing["student_name"].lower())
        if similarity >= 90:
            score += 25
            reasons.append(f"name is {similarity}% similar")
        elif similarity >= 75:
            score += 15
            reasons.append(f"name is {similarity}% similar")

    return score, reasons


# =======================
# DUPLICATE CHECK API
# =======================
@student_bp.route("/api/check-duplicate", methods=["POST"])
def check_duplicate():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    dob  = (data.get("dob") or "").strip()
    lrn  = (data.get("lrn") or "").strip()
    branch_id = data.get("branch_id")

    if not name and not lrn:
        return jsonify({"status": "ok"})

    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        # Fetch existing enrollments from the DB (exclude rejected ones)
        cursor.execute("""
            SELECT student_name, dob, lrn, enrollment_id, grade_level
            FROM enrollments
            WHERE status NOT IN ('rejected')
        """)
        existing_records = cursor.fetchall()

        best_score = 0
        best_reasons = []
        best_match = None

        for rec in existing_records:
            score, reasons = compute_duplicate_score(name, dob, lrn, rec)
            if score > best_score:
                best_score = score
                best_reasons = reasons
                best_match = rec

        if best_score >= 50:
            return jsonify({
                "status": "blocked",
                "score": best_score,
                "reasons": best_reasons,
                "match_name": best_match["student_name"] if best_match else None,
                "match_grade": best_match["grade_level"] if best_match else None,
            })

        return jsonify({"status": "ok", "score": best_score})

    except Exception as e:
        logger.error(f"Duplicate check error: {e}")
        return jsonify({"status": "ok"})  # fail open — don't block on error
    finally:
        cursor.close()
        db.close()


def trigger_enrollment_email(student_email, student_name, display_no, branch_name):
    """Sends a professional HTML enrollment confirmation email."""
    if not student_email:
        return

    subject = f"Enrollment Submitted - {branch_name}"
    
    # Plain text version as fallback
    body = (
        f"Enrollment Submitted!\n\n"
        f"Hello {student_name},\n"
        f"Your application has been received by {branch_name}.\n\n"
        f"YOUR BRANCH ENROLLMENT ID: {display_no}\n\n"
        f"Important: Save this ID! You will need it to track your enrollment status."
    )

    # Professional HTML version
    html_body = f"""
    <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 600px; margin: 20px auto; border: 1px solid #e0e0e0; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.05);">
        <div style="background-color: #1a2a4e; padding: 30px; text-align: center; color: white;">
            <h1 style="margin: 0; font-size: 24px; font-weight: 700;">Enrollment Submitted!</h1>
        </div>
        <div style="padding: 40px; color: #334155; line-height: 1.6;">
            <p style="font-size: 16px;">Hello <strong>{student_name}</strong>,</p>
            <p style="font-size: 16px;">Your application has been successfully received by <strong>{branch_name}</strong> and is now pending review.</p>
            
            <div style="background-color: #f8fafc; border: 1px dashed #cbd5e1; border-radius: 8px; padding: 25px; margin: 30px 0; text-align: center;">
                <p style="margin: 0 0 10px 0; font-size: 14px; color: #64748b; text-transform: uppercase; letter-spacing: 1px;">Your Branch Enrollment ID</p>
                <p style="margin: 0; font-size: 42px; font-weight: 800; color: #1a2a4e;">{display_no}</p>
            </div>

            <p style="font-size: 14px; color: #e11d48; font-weight: 600; text-align: center;">Important: Save this ID! You will need it to track your enrollment status.</p>
        </div>
        <div style="background-color: #f1f5f9; padding: 20px; text-align: center; font-size: 12px; color: #94a3b8;">
            &copy; 2026 LiceoLMS - Liceo de Majayjay System
        </div>
    </div>
    """
    
    send_email(student_email, subject, body, html_body=html_body)


# ---------------- Step 1: Student Enrollment ----------------
@student_bp.route("/branch/<int:branch_id>/enroll", methods=["GET", "POST"])
def enroll(branch_id):
    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        # ── Fetch branch ──
        cursor.execute("SELECT branch_id, branch_name FROM branches WHERE branch_id=%s", (branch_id,))
        branch = cursor.fetchone()
        if not branch:
            return "Branch not found", 404

        # ── Fetch grade levels ──
        cursor.execute("""
            SELECT id, name FROM grade_levels
            WHERE branch_id = %s
            ORDER BY display_order
        """, (branch_id,))
        grade_levels = cursor.fetchall() or []

        # ── Fetch school years ──
        cursor.execute("""
            SELECT year_id, label, is_active
            FROM school_years
            WHERE branch_id = %s
            ORDER BY label DESC
        """, (branch_id,))
        school_years = cursor.fetchall() or []

        # ── POST: Handle enrollment ──
        if request.method == "POST":
            # Selected school year from form, fallback to active
            selected_sy_id = request.form.get("year_id")
            if selected_sy_id:
                selected_sy_id = int(selected_sy_id)
            else:
                selected_sy_id = get_active_school_year_id(cursor, branch_id)

            if not selected_sy_id:
                flash("No active school year found. Please contact admin.", "error")
                return redirect(url_for("public.homepage"))
            if not is_branch_active(branch_id):
                flash("This branch is currently deactivated. New enrollments are not allowed.", "error")
                return redirect(url_for("public.homepage"))

            # ── Student Details ──
            student_name      = request.form.get("student_name", "").strip()
            grade_level       = normalize_grade_level(request.form.get("grade_level", "").strip())
            gender            = request.form.get("gender", "").strip()
            dob               = request.form.get("dob", "").strip() or None
            lrn               = request.form.get("lrn", "").strip() or None
            address           = request.form.get("address", "").strip()
            contact_number    = request.form.get("contact_number", "").strip()
            email             = request.form.get("email", "").strip() or None
            birthplace        = request.form.get("birthplace", "").strip() or None

            # ── Guardian ──
            guardian_name     = request.form.get("guardian_name", "").strip()
            guardian_contact  = request.form.get("guardian_contact", "").strip()
            guardian_email    = request.form.get("guardian_email", "").strip() or None

            # ── Parents ──
            father_name       = request.form.get("father_name", "").strip() or None
            father_contact    = request.form.get("father_contact", "").strip() or None
            father_occupation = request.form.get("father_occupation", "").strip() or None
            mother_name       = request.form.get("mother_name", "").strip() or None
            mother_contact    = request.form.get("mother_contact", "").strip() or None
            mother_occupation = request.form.get("mother_occupation", "").strip() or None

            # ── Previous School ──
            previous_school   = request.form.get("previous_school", "").strip() or None
            enroll_type_raw   = request.form.get("enroll_type", "").strip() or None
            enroll_semester   = request.form.get("enroll_semester", "").strip() or None
            # Combine Transferee + semester into a single stored value
            if enroll_type_raw == "Transferee" and enroll_semester:
                enroll_type = f"Transferee - {enroll_semester}"
            else:
                enroll_type = enroll_type_raw
            enroll_date       = request.form.get("enroll_date", "").strip() or None
            remarks           = request.form.get("remarks", "").strip() or None

            if not student_name or ',' not in student_name or len(student_name) < 5:
                flash("Please enter the full name in 'Last Name, First Name, M.I.' format.", "error")
                return redirect(request.url)
            if not grade_level:
                flash("Grade level is required.", "error")
                return redirect(request.url)
            if not dob:
                flash("Birthday is required.", "error")
                return redirect(request.url)
            if lrn and (not lrn.isdigit() or len(lrn) != 12):
                flash("LRN must be a 12-digit number.", "error")
                return redirect(request.url)
            if not guardian_name:
                flash("Guardian name is required.", "error")
                return redirect(request.url)
            if not guardian_contact:
                flash("Guardian contact is required.", "error")
                return redirect(request.url)
            if not request.form.get("privacy_consent"):
                flash("You must agree to the Data Privacy Consent.", "error")
                return redirect(request.url)

            # ── EMAIL VALIDATION ──
            if email and not is_valid_email(email):
                flash(f"The student email '{email}' is invalid. Please follow the correct format (e.g., name@domain.com) and avoid special characters like # % &.", "error")
                return redirect(request.url)
            
            if guardian_email and not is_valid_email(guardian_email):
                flash(f"The guardian email '{guardian_email}' is invalid. Please follow the correct format (e.g., name@domain.com) and avoid special characters like # % &.", "error")
                return redirect(request.url)

            # ── SERVER-SIDE DUPLICATE CHECK ──
            cursor.execute("""
                SELECT student_name, dob, lrn, grade_level
                FROM enrollments
                WHERE status NOT IN ('rejected')
                AND branch_id = %s
                AND year_id = %s
            """, (branch_id, selected_sy_id))
            existing_records = cursor.fetchall()
            best_score = 0
            best_reasons = []
            for rec in existing_records:
                score, reasons = compute_duplicate_score(student_name, dob or "", lrn or "", rec)
                if score > best_score:
                    best_score = score
                    best_reasons = reasons

            if best_score >= 50:
                reason_text = ", ".join(best_reasons)
                return render_template(
                    "student_enroll.html",
                    branch=branch,
                    grade_levels=grade_levels,
                    school_years=school_years,
                    message=None,
                    duplicate_blocked=True,
                    duplicate_reason=reason_text,
                )

            # ── Enrollment number ──
            cursor.execute("SELECT COALESCE(MAX(branch_enrollment_no), 0) + 1 AS next_no FROM enrollments WHERE branch_id = %s", (branch_id,))
            next_no = cursor.fetchone()["next_no"]

            # ── Insert enrollment ──
            cursor.execute("""
                INSERT INTO enrollments
                  (student_name, grade_level, gender, dob, address, contact_number,
                   guardian_name, guardian_contact, previous_school, branch_id, status,
                   branch_enrollment_no, lrn, email, guardian_email,
                   birthplace, father_name, father_contact, father_occupation,
                   mother_name, mother_contact, mother_occupation,
                   enroll_type, enroll_date, remarks, year_id)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'pending',%s,%s,%s,%s, %s,%s,%s,%s, %s,%s,%s, %s,%s,%s,%s)
                RETURNING enrollment_id
            """, (
                student_name, grade_level, gender, dob, address, contact_number,
                guardian_name, guardian_contact, previous_school, branch_id,
                next_no, lrn, email, guardian_email,
                birthplace, father_name, father_contact, father_occupation,
                mother_name, mother_contact, mother_occupation,
                enroll_type, enroll_date, remarks, selected_sy_id
            ))
            enrollment_id = cursor.fetchone()["enrollment_id"]

            # ── Process & Save Documents ──
            document_fields = [
                ("psa_birth_cert", "PSA Birth Certificate"),
                ("baptismal_cert", "Baptismal Certificate"),
                ("form_138", "Form 138"),
                ("good_moral", "Good Moral Certificate"),
                ("form_137", "Form 137")
            ]

            for file_field, doc_name in document_fields:
                fileobj = request.files.get(file_field)
                if fileobj and fileobj.filename:
                    # Save each doc file
                    save_doc_file(cursor, enrollment_id, fileobj, doc_name)

            db.commit()

            # ── Trigger Email Notification ──
            if email:
                # Format the display ID: BRANCH-NO (e.g., MAIN-0005)
                display_id = f"{branch['branch_name'][:4].upper()}-{next_no:04d}"
                trigger_enrollment_email(email, student_name, display_id, branch["branch_name"])

            flash("Enrollment submitted successfully! Please wait for registrar approval.", "success")
            return redirect(url_for("student.enrollment_success", branch_id=branch_id, enrollment_id=enrollment_id))

        # ── GET: Render form ──
        return render_template(
            "student_enroll.html",
            branch=branch,
            grade_levels=grade_levels,
            school_years=school_years,  # ✅ pass school years to template
            message=None,
            duplicate_blocked=False,
            duplicate_reason=None
        )

    finally:
        cursor.close()
        db.close()


# ---------------- Enrollment success (direct after form submit; no books/uniform) ----------------
@student_bp.route("/branch/<int:branch_id>/enroll/success/<int:enrollment_id>", methods=["GET"])
def enrollment_success(branch_id, enrollment_id):
    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cursor.execute(
            "SELECT branch_enrollment_no, student_name FROM enrollments WHERE enrollment_id=%s",
            (enrollment_id,),
        )
        row = cursor.fetchone()
        if not row:
            return "Enrollment not found", 404
        display_no = row.get("branch_enrollment_no") or "???"
        student_name = (row.get("student_name") or "").strip()
        return render_template(
            "enrollment_success.html",
            enrollment_id=display_no,
            student_name=student_name,
        )
    finally:
        cursor.close()
        db.close()

def compute_next_grade(current_grade):
    cg = str(current_grade).strip()
    if cg == "Nursery": return "Kinder"
    if cg == "Kinder": return "Grade 1"
    
    import re
    match = re.match(r"^Grade\s+(\d+)", cg, re.IGNORECASE)
    if match:
        num = int(match.group(1))
        if num < 10:
            return f"Grade {num + 1}"
        elif num == 10:
            return "Grade 11" 
        elif num == 11:
            # For Grade 11, we want to progress to the corresponding Grade 12 strand
            strand = ""
            if "-" in cg:
                strand = cg.split("-", 1)[1].strip()
            elif "–" in cg:
                strand = cg.split("–", 1)[1].strip()
            
            if strand:
                return f"Grade 12-{strand}"
            return "Grade 12"
        elif num == 12:
            return "Graduated"
    
    return None

@student_bp.route("/branch/<int:branch_id>/continuing/login")
def continuing_login(branch_id):
    if session.get("role") == "student":
        if session.get("branch_id") != branch_id:
            flash("You are logged into a different branch. Please login again.", "error")
            session.clear()
        else:
            return redirect(url_for("student.continuing_enrollment", branch_id=branch_id))
    session["next_url"] = url_for("student.continuing_enrollment", branch_id=branch_id)
    flash("Please login with your student account to continue your enrollment.", "info")
    return redirect(url_for("auth.login"))

@student_bp.route("/branch/<int:branch_id>/continuing/enroll", methods=["GET", "POST"])
def continuing_enrollment(branch_id):
    if session.get("role") != "student" or session.get("branch_id") != branch_id:
        session["next_url"] = url_for("student.continuing_enrollment", branch_id=branch_id)
        return redirect(url_for("auth.login"))
        
    enrollment_id = session.get("enrollment_id")
    if not enrollment_id:
        flash("Enrollment record not found.", "error")
        return redirect(url_for("public.homepage"))
        
    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cursor.execute("SELECT * FROM enrollments WHERE enrollment_id=%s AND branch_id=%s", (enrollment_id, branch_id))
        enrollment = cursor.fetchone()
        
        if not enrollment:
            flash("Enrollment record not found for this branch.", "error")
            return redirect(url_for("public.homepage"))
        active_sy_id = get_active_school_year_id(cursor, branch_id)
        if not active_sy_id:
            flash("No active school year found. Please contact admin.", "error")
            return redirect(url_for("student.dashboard"))
        

        if enrollment.get("status") != "open_for_enrollment":
            flash("Continuing enrollment is currently not open for your account. Please wait for the registrar to open it.", "error")
            return redirect("/student/dashboard")
            
        current_grade = enrollment.get("grade_level", "")
        next_grade = compute_next_grade(current_grade)
        
        if not next_grade or next_grade == "Graduated":
            flash("Congratulations! You have completed your studies here.", "info")
            return redirect("/student/dashboard")

        needs_strand = (next_grade == "Grade 11")

        if request.method == "POST":
            chosen_grade = request.form.get("grade_level") or next_grade
            section_id_raw = request.form.get("section_id")
            section_id = int(section_id_raw) if section_id_raw and section_id_raw.isdigit() else None

            cursor.execute("""
                SELECT COALESCE(MAX(branch_enrollment_no), 0) + 1 AS next_no
                FROM enrollments WHERE branch_id = %s
            """, (branch_id,))
            next_no = cursor.fetchone()["next_no"]

            cursor.execute("""
                INSERT INTO enrollments
                  (student_name, grade_level, gender, dob, address, contact_number,
                   guardian_name, guardian_contact, previous_school, branch_id, status,
                   branch_enrollment_no, lrn, email, guardian_email, user_id, section_id, year_id)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'enrolled',%s,%s,%s,%s,%s,%s,%s)
                RETURNING enrollment_id
            """, (
                enrollment["student_name"], chosen_grade, enrollment["gender"], 
                enrollment["dob"], enrollment["address"], 
                enrollment["contact_number"], enrollment["guardian_name"], 
                enrollment["guardian_contact"], enrollment["previous_school"], 
                branch_id, next_no, enrollment["lrn"], enrollment.get("email"), 
                enrollment.get("guardian_email"), enrollment.get("user_id"), 
                section_id, active_sy_id
            ))
            new_enrollment_id = cursor.fetchone()["enrollment_id"]

            cursor.execute("""
                UPDATE enrollments 
                SET status = 'completed'
                WHERE enrollment_id = %s
            """, (enrollment_id,))

            if enrollment.get("user_id"):
                cursor.execute("UPDATE users SET enrollment_id = %s, grade_level = %s WHERE user_id = %s", 
                               (new_enrollment_id, chosen_grade, enrollment["user_id"]))
                               
            cursor.execute("UPDATE student_accounts SET enrollment_id = %s WHERE enrollment_id = %s",
                           (new_enrollment_id, enrollment_id))
                           
            cursor.execute("UPDATE parent_student SET student_id = %s WHERE student_id = %s",
                           (new_enrollment_id, enrollment_id))

            db.commit()

            session["enrollment_id"] = new_enrollment_id
            session["student_grade_level"] = chosen_grade
            # Redirect to confirmation/subjects preview page
            return redirect(url_for("student.continuing_enrolled_confirmation",
                                    branch_id=branch_id, section_id=section_id or 0,
                                    grade=chosen_grade))

        cursor.execute("""
            SELECT s.section_id, s.section_name, g.name as grade_name
            FROM sections s
            JOIN grade_levels g ON s.grade_level_id = g.id
            WHERE s.branch_id = %s 
             AND s.year_id = %s
            ORDER BY s.section_name
        """, (branch_id, active_sy_id))
        # fetch all sections, filter in JS based on chosen grade
        raw_sections = cursor.fetchall() or []
        sections = [dict(s) for s in raw_sections]

        shs_strands = []
        if needs_strand:
            cursor.execute("""
                SELECT name FROM grade_levels 
                WHERE branch_id = %s AND name ILIKE 'Grade 11-%%'
                ORDER BY display_order
            """, (branch_id,))
            shs_strands = [row["name"] for row in cursor.fetchall()]

        return render_template(
            "student_continuing_enroll.html", 
            branch_id=branch_id, 
            current_grade=current_grade, 
            next_grade=next_grade,
            needs_strand=needs_strand,
            shs_strands=shs_strands,
            sections=sections,
            student_name=enrollment.get("student_name")
        )
    finally:
        cursor.close()
        db.close()


# ---------------- Continuing Enrollment: Confirmation + Subjects Preview ----------------
@student_bp.route("/branch/<int:branch_id>/continuing/confirmed", methods=["GET"])
def continuing_enrolled_confirmation(branch_id):
    """Show the student their new grade, section, and assigned subjects after continuing enrollment."""
    if session.get("role") != "student" or session.get("branch_id") != branch_id:
        return redirect(url_for("auth.login"))

    section_id = request.args.get("section_id", type=int)
    grade = request.args.get("grade", "")

    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        # Fetch section name
        section_name = None
        grade_level_name = None
        if section_id:
            cursor.execute("""
                SELECT s.section_name, g.name AS grade_level_name
                FROM sections s
                JOIN grade_levels g ON s.grade_level_id = g.id
                WHERE s.section_id = %s AND s.branch_id = %s
                LIMIT 1
            """, (section_id, branch_id))
            row = cursor.fetchone()
            if row:
                section_name = row["section_name"]
                grade_level_name = row["grade_level_name"]

        # Fetch subjects assigned to this section
        subjects = []
        if section_id:
            cursor.execute("""
                SELECT
                    sub.name        AS subject_name,
                    u.full_name     AS teacher_full_name,
                    u.username      AS teacher_username,
                    u.gender        AS teacher_gender
                FROM section_teachers st
                JOIN subjects sub   ON st.subject_id  = sub.subject_id
                LEFT JOIN users u   ON st.teacher_id  = u.user_id
                WHERE st.section_id = %s
                ORDER BY sub.name
            """, (section_id,))
            subjects = cursor.fetchall() or []

        enrollment_id = session.get("enrollment_id")
        student_name = ""
        if enrollment_id:
            cursor.execute("SELECT student_name FROM enrollments WHERE enrollment_id=%s", (enrollment_id,))
            row = cursor.fetchone()
            if row:
                student_name = row["student_name"]

        return render_template(
            "student_continuing_enrolled.html",
            branch_id=branch_id,
            grade=grade,
            section_id=section_id,
            section_name=section_name,
            grade_level_name=grade_level_name,
            subjects=subjects,
            student_name=student_name,
        )
    finally:
        cursor.close()
        db.close()


# ---------------- API: Section Subjects (student-accessible, for live preview) ----------------
@student_bp.route("/api/student/section/<int:section_id>/subjects", methods=["GET"])
def api_section_subjects_student(section_id):
    """Return subjects for a given section as JSON. Requires student session."""
    if session.get("role") != "student":
        return {"error": "Unauthorized"}, 403

    branch_id = session.get("branch_id")
    if not branch_id:
        return {"error": "No branch in session"}, 400

    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        # Ensure the section belongs to this branch
        cursor.execute(
            "SELECT section_name FROM sections WHERE section_id=%s AND branch_id=%s",
            (section_id, branch_id)
        )
        sec = cursor.fetchone()
        if not sec:
            return {"error": "Section not found"}, 404

        cursor.execute("""
            SELECT
                sub.name        AS subject_name,
                u.full_name     AS teacher_full_name,
                u.username      AS teacher_username,
                u.gender        AS teacher_gender
            FROM section_teachers st
            JOIN subjects sub   ON st.subject_id  = sub.subject_id
            LEFT JOIN users u   ON st.teacher_id  = u.user_id
            WHERE st.section_id = %s
            ORDER BY sub.name
        """, (section_id,))
        rows = cursor.fetchall() or []

        return {
            "section_name": sec["section_name"],
            "subjects": [dict(r) for r in rows]
        }
    finally:
        cursor.close()
        db.close()


# ---------------- Step 2: Book Reservation (legacy; not used in main flow) ----------------
@student_bp.route("/branch/<int:branch_id>/enroll/books/<int:enrollment_id>", methods=["GET", "POST"])
def enroll_books(branch_id, enrollment_id):
    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        books_available = ["Math Book", "Science Book", "English Book"]

        if request.method == "POST":
            selected_books = request.form.getlist("books")
            for book in selected_books:
                cursor.execute("""
                    INSERT INTO enrollment_books (enrollment_id, book_name, quantity)
                    VALUES (%s, %s, 1)
                """, (enrollment_id, book))

            db.commit()
            return redirect(url_for("student.enroll_uniform", branch_id=branch_id, enrollment_id=enrollment_id))

        return render_template("enroll_books.html", books=books_available, enrollment_id=enrollment_id)

    finally:
        cursor.close()
        db.close()


# ---------------- Step 3: Uniform Selection ----------------
@student_bp.route("/branch/<int:branch_id>/enroll/uniform/<int:enrollment_id>", methods=["GET", "POST"])
def enroll_uniform(branch_id, enrollment_id):
    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    uniforms = [
        {"type": "Shirt", "sizes": ["S", "M", "L", "XL"]},
        {"type": "Pants", "sizes": ["S", "M", "L", "XL"]},
        {"type": "Jacket", "sizes": ["S", "M", "L", "XL"]},
    ]

    try:
        if request.method == "POST":
            for uniform in uniforms:
                uniform_type = uniform["type"]
                size = request.form.get(f"{uniform_type}_size")
                quantity = int(request.form.get(f"{uniform_type}_qty", 0) or 0)

                if quantity > 0:
                    cursor.execute("""
                        INSERT INTO enrollment_uniforms (enrollment_id, uniform_type, size, quantity)
                        VALUES (%s, %s, %s, %s)
                    """, (enrollment_id, uniform_type, size, quantity))

            db.commit()
            return redirect(url_for("student.enroll_summary", branch_id=branch_id, enrollment_id=enrollment_id))

        return render_template("enroll_uniform.html", uniforms=uniforms, enrollment_id=enrollment_id)

    finally:
        cursor.close()
        db.close()


# ---------------- Step 4: Summary & Submit ----------------
@student_bp.route("/branch/<int:branch_id>/enroll/summary/<int:enrollment_id>", methods=["GET", "POST"])
def enroll_summary(branch_id, enrollment_id):
    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        cursor.execute("SELECT * FROM enrollments WHERE enrollment_id=%s", (enrollment_id,))
        enrollment = cursor.fetchone()

        cursor.execute("SELECT * FROM enrollment_documents WHERE enrollment_id=%s", (enrollment_id,))
        documents = cursor.fetchall()

        cursor.execute("SELECT * FROM enrollment_books WHERE enrollment_id=%s", (enrollment_id,))
        books = cursor.fetchall()

        cursor.execute("SELECT * FROM enrollment_uniforms WHERE enrollment_id=%s", (enrollment_id,))
        uniforms = cursor.fetchall()

        if request.method == "POST":
            cursor.execute("UPDATE enrollments SET status='pending' WHERE enrollment_id=%s", (enrollment_id,))
            db.commit()

            # Use branch_enrollment_no (per-branch #1, #2...) for display
            display_no = enrollment["branch_enrollment_no"] if enrollment else "???"

            return render_template(
                "enrollment_success.html",
                enrollment_id=display_no,
                student_name=enrollment["student_name"] if enrollment else ""
            )

        return render_template(
            "enroll_summary.html",
            enrollment=enrollment,
            documents=documents,
            books=books,
            uniforms=uniforms
        )

    finally:
        cursor.close()
        db.close()


@student_bp.route("/track", methods=["GET", "POST"])
def track_enrollment():
    enrollment = None
    documents = []
    branches = []
    requirements = {}

    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    REQUIRED_DOCS = {
        "PSA Birth Certificate": "PSA Birth Certificate",
        "Baptismal Certificate": "Baptismal Certificate",
        "Form 138": "Form 138",
        "Good Moral Certificate": "Good Moral Certificate",
        "Form 137": "Form 137",
    }

    try:
        cursor.execute("SELECT branch_id, branch_name FROM branches WHERE is_active = TRUE ORDER BY branch_name")
        branches = cursor.fetchall()

        if request.method == "POST":
            enrollment_id = request.form.get("enrollment_id", "").strip()
            branch_id = request.form.get("branch_id")

            if enrollment_id.isdigit() and branch_id:
                enrollment_no_int = int(enrollment_id)
                branch_id_int = int(branch_id)

                cursor.execute("""
                    SELECT e.*, b.branch_name
                    FROM enrollments e
                    JOIN branches b ON e.branch_id = b.branch_id
                    WHERE e.branch_enrollment_no = %s AND e.branch_id = %s
                    ORDER BY e.created_at DESC
                    LIMIT 1
                """, (enrollment_no_int, branch_id_int))
                enrollment = cursor.fetchone()

                if enrollment:
                    session["tracked_enrollment_id"] = enrollment["enrollment_id"]
                    session["tracked_branch_id"]     = enrollment["branch_id"]

                    cursor.execute("SELECT * FROM enrollment_documents WHERE enrollment_id=%s", (enrollment["enrollment_id"],))
                    documents = cursor.fetchall()
                    submitted_types = set(d["doc_type"] for d in documents)
                    requirements = {label: key in submitted_types for key, label in REQUIRED_DOCS.items()}
                else:
                    flash("No enrollment found with that ID in the selected branch.", "error")
    finally:
        cursor.close()
        db.close()

    return render_template(
        "track_enrollment.html",
        enrollment=enrollment,
        documents=documents,
        branches=branches,
        requirements=requirements
    )

# ---------------- Correction / Edit Enrollment ----------------
@student_bp.route("/enroll/edit/<int:enrollment_id>", methods=["GET", "POST"])
def enroll_edit(enrollment_id):
    # Security check: Must have tracked this enrollment in the current session
    if session.get("tracked_enrollment_id") != enrollment_id:
        flash("Unauthorized access. Please track your enrollment first.", "error")
        return redirect(url_for("student.track_enrollment"))

    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        # Fetch existing enrollment
        cursor.execute("SELECT * FROM enrollments WHERE enrollment_id = %s", (enrollment_id,))
        enrollment = cursor.fetchone()
        if not enrollment:
            flash("Enrollment not found.", "error")
            return redirect(url_for("student.track_enrollment"))

        branch_id = enrollment["branch_id"]

        # Fetch branch & grade levels
        cursor.execute("SELECT branch_id, branch_name FROM branches WHERE branch_id=%s", (branch_id,))
        branch = cursor.fetchone()
        
        cursor.execute("SELECT id, name FROM grade_levels WHERE branch_id = %s ORDER BY display_order", (branch_id,))
        grade_levels = cursor.fetchall() or []

        # Fetch school years
        cursor.execute("SELECT year_id, label FROM school_years WHERE branch_id = %s ORDER BY label DESC", (branch_id,))
        school_years = cursor.fetchall() or []

        # Fetch existing documents
        cursor.execute("SELECT * FROM enrollment_documents WHERE enrollment_id = %s", (enrollment_id,))
        existing_docs = cursor.fetchall()

        if request.method == "POST":
            # ── Selective Update Logic ──
            # Only update fields that were actually in the form
            possible_fields = [
                "student_name", "grade_level", "gender", "dob", "lrn", "address", 
                "contact_number", "email", "birthplace", "guardian_name", 
                "guardian_contact", "guardian_email", "father_name", "father_contact", 
                "father_occupation", "mother_name", "mother_contact", "mother_occupation", 
                "previous_school", "enroll_type", "remarks", "year_id"
            ]
            
            update_fields = []
            update_values = []
            
            for field in possible_fields:
                if field in request.form:
                    val = request.form.get(field, "").strip()
                    
                    # ── EMAIL VALIDATION ──
                    if field in ["email", "guardian_email"] and val:
                        if not is_valid_email(val):
                            flash(f"The email address '{val}' is invalid. Please follow the correct format (e.g., name@domain.com) and avoid special characters like # % &.", "error")
                            return redirect(request.url)

                    if field == "grade_level":
                        val = normalize_grade_level(val)
                    
                    update_fields.append(f"{field} = %s")
                    update_values.append(val or None)
            
            # Always reset status to pending
            update_fields.append("status = %s")
            update_values.append("pending")
            
            if update_fields:
                final_query = f"UPDATE enrollments SET {', '.join(update_fields)} WHERE enrollment_id = %s"
                update_values.append(enrollment_id)
                cursor.execute(final_query, update_values)

            # ── Handle Document Re-uploads ──
            document_fields = [
                ("psa_birth_cert", "PSA Birth Certificate"),
                ("baptismal_cert", "Baptismal Certificate"),
                ("form_138", "Form 138"),
                ("good_moral", "Good Moral Certificate"),
                ("form_137", "Form 137")
            ]
            
            # Pre-validate re-uploads
            for file_field, doc_name in document_fields:
                f = request.files.get(file_field)
                if f and f.filename:
                    if not allowed_file(f.filename):
                        flash(f"Invalid file type for {doc_name}. Only PDF, JPG, JPEG, and PNG are allowed.", "error")
                        return redirect(request.url)
                    f.seek(0, os.SEEK_END)
                    if f.tell() > MAX_FILE_SIZE:
                        flash(f"File {doc_name} is too large. Maximum limit is 10MB.", "error")
                        return redirect(request.url)
                    f.seek(0)

            for file_field, doc_name in document_fields:
                fileobj = request.files.get(file_field)
                if fileobj and fileobj.filename:
                    # Delete old record if it exists
                    cursor.execute("DELETE FROM enrollment_documents WHERE enrollment_id=%s AND doc_type=%s", (enrollment_id, doc_name))
                    save_doc_file(cursor, enrollment_id, fileobj, doc_name)

            db.commit()
            flash("Your application has been updated and re-submitted for review.", "success")
            return redirect(url_for("student.track_enrollment"))

        return render_template(
            "student_enroll_edit.html",
            enrollment=enrollment,
            branch=branch,
            grade_levels=grade_levels,
            school_years=school_years,
            existing_docs=existing_docs
        )

    finally:
        cursor.close()
        db.close()


# =======================
# STUDENT/PARENT RESERVATION ROUTES
# =======================

@student_bp.route("/reservation", methods=["GET", "POST"])
def student_reservation():
    role = session.get("role")
    if role not in ("student", "parent"):
        return redirect(url_for("auth.login"))

    message = None
    error = None
    items = []

    search = request.args.get('search', '').strip()
    category_filter = request.args.get('category', '').strip()
    success_id = request.args.get('success_id', type=int)
    success_data = None

    branch_id = None
    student_grade = None
    student_user_id = None  # student only
    reserved_by_user_id = session.get("user_id")

    if not reserved_by_user_id:
        session.clear()
        return redirect(url_for("auth.login"))

    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        if role == "student":
            branch_id = session.get("branch_id")
            student_user_id = session.get("user_id")
            enrollment_id = session.get("enrollment_id")

            if not branch_id or not student_user_id or not enrollment_id:
                session.clear()
                return redirect(url_for("auth.login"))

            student_grade = get_logged_student_grade_level()

        else:
            # role == parent
            enrollment_id = request.args.get("enrollment_id", type=int)
            if not enrollment_id:
                flash("Please select a child first.", "error")
                return redirect(url_for("parent.dashboard"))

            cursor.execute("""
                SELECT e.branch_id, e.grade_level
                FROM parent_student ps
                JOIN enrollments e ON e.enrollment_id = ps.student_id
                WHERE ps.parent_id = %s AND ps.student_id = %s
                LIMIT 1
            """, (reserved_by_user_id, enrollment_id))
            row = cursor.fetchone()

            if not row:
                flash("Child not found or access denied.", "error")
                return redirect(url_for("parent.dashboard"))

            branch_id = row["branch_id"]
            student_grade = normalize_grade_level(row["grade_level"])

            # Resolve student's user_id so cashier can show this reservation and link parent_student
            cursor.execute("""
                SELECT u.user_id
                FROM student_accounts sa
                JOIN users u ON u.username = sa.username
                WHERE sa.enrollment_id = %s
                LIMIT 1
            """, (enrollment_id,))
            urow = cursor.fetchone()
            if urow:
                student_user_id = urow["user_id"]

        # Block new reservations when branch is inactive
        if not is_branch_active(branch_id):
            flash("This branch is currently deactivated. New reservations are not allowed.", "error")
            if role == "parent":
                return redirect(url_for("parent.dashboard"))
            else:
                return redirect("/student/dashboard")

        def is_item_visible_for_student(item_name: str, item_grade_level, student_grade_level: str) -> bool:
            if not student_grade_level:
                return True

            if item_name in GRADE_MAPPINGS:
                return student_grade_level in GRADE_MAPPINGS[item_name]

            if not item_grade_level:
                return False

            return str(item_grade_level).strip().lower() == str(student_grade_level).strip().lower()

        query = """
            SELECT item_id, category, item_name, grade_level, is_common, size_label,
                   price, stock_total, reserved_qty, image_url
            FROM inventory_items
            WHERE branch_id = %s AND is_active = TRUE
        """
        params = [branch_id]

        if search:
            query += " AND item_name ILIKE %s"
            params.append(f"%{search}%")

        if category_filter:
            query += " AND category = %s"
            params.append(category_filter)

        query += " ORDER BY category, item_name"

        cursor.execute(query, tuple(params))
        rows = cursor.fetchall() or []

        for r in rows:
            if bool(r['is_common']) or is_item_visible_for_student(r['item_name'], r['grade_level'], student_grade):
                available = int(r['stock_total'] or 0) - int(r['reserved_qty'] or 0)
                
                cursor.execute("""
                    SELECT size_id, size_label, stock_total, reserved_qty 
                    FROM inventory_item_sizes 
                    WHERE item_id = %s
                """, (r['item_id'],))
                sizes_rows = cursor.fetchall() or []
                
                # Sort standard clothing sizes logically
                def get_size_rank(lbl):
                    lbl_up = str(lbl).upper().strip()
                    mapping = {"XXS":1, "XS":2, "S":3, "M":4, "L":5, "XL":6, "XXL":7, "2XL":7, "3XL":8, "4XL":9}
                    return mapping.get(lbl_up, 99)

                sizes_rows = sorted(sizes_rows, key=lambda x: (get_size_rank(x['size_label']), x['size_label']))
                
                sizes = []
                for s in sizes_rows:
                    s_available = int(s['stock_total'] or 0) - int(s['reserved_qty'] or 0)
                    sizes.append({
                        "size_id": s['size_id'],
                        "size_label": s['size_label'],
                        "available": s_available
                    })

                items.append({
                    "item_id": r['item_id'],
                    "category": r['category'],
                    "item_name": r['item_name'],
                    "grade_level": r['grade_level'],
                    "is_common": bool(r['is_common']),
                    "size_label": r['size_label'],
                    "price": float(r['price'] or 0),
                    "available": available,
                    "image_url": r['image_url'],
                    "sizes": sizes
                })

        if request.method == "POST":
            selected = []
            for it in items:
                key = f"qty_{it['item_id']}"
                qty_str = (request.form.get(key) or "0").strip()
                try:
                    qty = int(qty_str)
                except Exception:
                    qty = 0

                if qty > 0:
                    size_key = f"size_{it['item_id']}"
                    size_val = (request.form.get(size_key) or "").strip()
                    selected.append({"item_id": it["item_id"], "qty": qty, "size": size_val or None, "category": it["category"]})

            if not selected:
                error = "No items selected."
                return render_template_safe(
                    "student_reservation.html",
                    items=items,
                    student_grade=student_grade,
                    branch_id=branch_id,
                    search=search,
                    category=category_filter,
                    message=message,
                    error=error
                )

            db_tx = get_db_connection()
            cursor_tx = db_tx.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            try:
                # Resolve enrollment_id for the reservation
                target_enrollment_id = enrollment_id if role == "parent" else session.get("enrollment_id")

                # Create one reservation ID per transaction
                cursor_tx.execute("""
                    INSERT INTO reservations (student_user_id, branch_id, student_grade_level, status, reserved_by_user_id, enrollment_id)
                    VALUES (%s, %s, %s, 'RESERVED', %s, %s)
                    RETURNING reservation_id
                """, (student_user_id, branch_id, student_grade, reserved_by_user_id, target_enrollment_id))
                reservation_id = cursor_tx.fetchone()['reservation_id']

                for sel in selected:
                    item_id = sel["item_id"]
                    qty = sel["qty"]
                    size = sel["size"]

                    cursor_tx.execute("""
                        SELECT stock_total, reserved_qty, price, size_label, item_name
                        FROM inventory_items
                        WHERE item_id = %s AND branch_id = %s AND is_active = TRUE
                        FOR UPDATE
                    """, (item_id, branch_id))
                    r = cursor_tx.fetchone()
                    if not r:
                        raise Exception("Item not found.")

                    available = int(r['stock_total'] or 0) - int(r['reserved_qty'] or 0)
                    if qty > available:
                        raise Exception(f"Not enough overall stock for: {r['item_name']}")

                    stored_size = size if size else r['size_label']

                    if stored_size:
                        cursor_tx.execute("""
                            SELECT size_id, stock_total, reserved_qty
                            FROM inventory_item_sizes
                            WHERE item_id = %s AND size_label = %s
                            FOR UPDATE
                        """, (item_id, stored_size))
                        s_row = cursor_tx.fetchone()
                        if s_row:
                            s_available = int(s_row['stock_total'] or 0) - int(s_row['reserved_qty'] or 0)
                            if qty > s_available:
                                raise Exception(f"Not enough stock for {r['item_name']} (Size: {stored_size})")
                            
                            cursor_tx.execute("""
                                UPDATE inventory_item_sizes
                                SET reserved_qty = reserved_qty + %s
                                WHERE size_id = %s
                            """, (qty, s_row['size_id']))

                    cursor_tx.execute("""
                        UPDATE inventory_items
                        SET reserved_qty = reserved_qty + %s
                        WHERE item_id = %s AND branch_id = %s
                    """, (qty, item_id, branch_id))

                    unit_price = float(r['price'] or 0)
                    line_total = unit_price * qty

                    cursor_tx.execute("""
                        INSERT INTO reservation_items (reservation_id, item_id, qty, size_label, unit_price, line_total)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (reservation_id, item_id, qty, stored_size, unit_price, line_total))

                db_tx.commit()
                
                # Redirect back to the same page with success_id to avoid form re-submission
                success_url = url_for("student.student_reservation", enrollment_id=target_enrollment_id)
                if "?" in success_url:
                    success_url += f"&success_id={reservation_id}"
                else:
                    success_url += f"?success_id={reservation_id}"
                
                return redirect(success_url)

            except Exception as e:
                db_tx.rollback()
                error = str(e)
            finally:
                cursor_tx.close()
                db_tx.close()

        # If success_id was provided, fetch the details to show the success message on the same page
        if success_id:
            try:
                cursor.execute("""
                    SELECT r.reservation_id, r.status, r.created_at
                    FROM reservations r
                    WHERE r.reservation_id = %s 
                      AND (r.student_user_id = %s OR r.reserved_by_user_id = %s)
                    LIMIT 1
                """, (success_id, student_user_id, reserved_by_user_id))
                res_row = cursor.fetchone()
                if res_row:
                    cursor.execute("""
                        SELECT ii.item_name, ri.qty, ri.size_label, ri.unit_price, ri.line_total
                        FROM reservation_items ri
                        JOIN inventory_items ii ON ii.item_id = ri.item_id
                        WHERE ri.reservation_id = %s
                    """, (success_id,))
                    res_items = cursor.fetchall()
                    success_data = {
                        "reservation": res_row,
                        "reserved_items": res_items,
                        "total": sum(float(x['line_total'] or 0) for x in res_items)
                    }
            except Exception as e:
                logger.error(f"Error fetching success data: {e}")

    except Exception as e:
        error = str(e)
    finally:
        cursor.close()
        db.close()

    return render_template_safe(
        "student_reservation.html",
        items=items,
        student_grade=student_grade,
        branch_id=branch_id,
        search=search,
        category=category_filter,
        message=message,
        error=error,
        success_data=success_data
    )

@student_bp.route("/student/reservations", methods=["GET"])
def student_reservations_list():
    if session.get("role") != "student":
        return redirect(url_for("auth.login"))

    branch_id = session.get("branch_id")
    student_user_id = session.get("user_id")

    if not branch_id or not student_user_id:
        session.clear()
        return redirect(url_for("auth.login"))

    conn = get_db_connection()
    cur = None
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cur.execute("""
            SELECT
                r.reservation_id,
                r.status,
                r.created_at,
                COALESCE(SUM(ri.line_total), 0) AS total_amount,
                COALESCE(SUM(ri.qty), 0) AS total_qty,
                STRING_AGG(DISTINCT ii.item_name, ', ' ORDER BY ii.item_name) AS items
            FROM reservations r
            LEFT JOIN reservation_items ri ON ri.reservation_id = r.reservation_id
            LEFT JOIN inventory_items ii ON ii.item_id = ri.item_id
            WHERE r.student_user_id = %s AND r.branch_id = %s
            GROUP BY r.reservation_id, r.status, r.created_at
            ORDER BY r.created_at DESC
        """, (student_user_id, branch_id))

        rows = cur.fetchall() or []

    finally:
        if cur:
            try:
                cur.close()
            except Exception:
                pass
        conn.close()

    return render_template("student_reservations_list.html", rows=rows)

@student_bp.route("/reservation/success/<int:reservation_id>")
def student_reservation_success(reservation_id):
    """Legacy route: Redirect to the new in-page confirmation flow."""
    role = session.get("role")
    if role not in ("student", "parent"):
        return redirect(url_for("auth.login"))

    # Try to find the enrollment_id to redirect properly
    enrollment_id = session.get("enrollment_id")
    if role == "parent":
        # We might not have it in session, but student_reservation will handle it if missing
        pass

    return redirect(url_for("student.student_reservation", enrollment_id=enrollment_id, success_id=reservation_id))