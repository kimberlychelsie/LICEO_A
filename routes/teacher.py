import re as _re
import re
from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify, send_file
from db import get_db_connection
import psycopg2.extras
from cloudinary_helper import upload_file
import os
import json
import io
import pandas as pd
import pdfplumber
from docx import Document
from datetime import datetime, timezone
import pytz

try:
    import pytesseract
    from PIL import Image
    HAS_OCR = True
except ImportError:
    HAS_OCR = False

# ── OCR Config (Windows) ──
if HAS_OCR and os.name == 'nt':
    tess_paths = [
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        r'C:\Users\Admin\AppData\Local\Tesseract-OCR\tesseract.exe',
        os.path.join(os.environ.get('LOCALAPPDATA', ''), r'Tesseract-OCR\tesseract.exe')
    ]
    for p in tess_paths:
        if os.path.exists(p):
            pytesseract.pytesseract.tesseract_cmd = p
            break

teacher_bp = Blueprint("teacher", __name__)

GRADE_LEVELS = [
    "Kinder", "Grade 1", "Grade 2", "Grade 3",
    "Grade 4", "Grade 5", "Grade 6",
    "Grade 7", "Grade 8", "Grade 9", "Grade 10",
    "Grade 11", "Grade 12",
]


# ── helpers ──────────────────────────────────────────────
def _require_teacher():
    return session.get("role") == "teacher"


def _normalize_grade(grade_str):
    """Accept both '7' and 'Grade 7' — returns (grade_full, grade_short)."""
    m = _re.match(r'^Grade\s+(\d+)$', grade_str, _re.IGNORECASE)
    num = m.group(1) if m else None
    return grade_str, (num or grade_str)

def _get_grading_period_by_date(cur, branch_id, year_id, date_obj):
    """Auto-detect grading period based on academic calendar dates."""
    cur.execute("""
        SELECT period_name 
        FROM grading_period_ranges 
        WHERE branch_id = %s AND year_id = %s 
          AND %s BETWEEN start_date AND end_date
        LIMIT 1
    """, (branch_id, year_id, date_obj))
    row = cur.fetchone()
    return row["period_name"] if row else None

def _normalize_period_name(value):
    if not value:
        return ""
    return str(value).replace("Grading", "").strip()

def _get_unlocked_grading_periods(cur, branch_id, year_id, as_of_date=None):
    """
    Grading periods that are already open based on admin date ranges.
    If no ranges are configured, allow all periods to avoid blocking operations.
    """
    if as_of_date is None:
        ph_tz = pytz.timezone("Asia/Manila")
        as_of_date = datetime.now(ph_tz).date()

    cur.execute("""
        SELECT period_name, start_date
        FROM grading_period_ranges
        WHERE branch_id = %s AND year_id = %s
    """, (branch_id, year_id))
    rows = cur.fetchall() or []
    if not rows:
        return GRADING_PERIODS[:]

    start_map = {}
    for r in rows:
        pname = _normalize_period_name(r.get("period_name"))
        if pname in GRADING_PERIODS:
            sdate = r.get("start_date")
            if pname not in start_map or (sdate and sdate < start_map[pname]):
                start_map[pname] = sdate

    return [p for p in GRADING_PERIODS if p in start_map and start_map[p] and start_map[p] <= as_of_date]

def _is_holiday_or_weekend(cur, branch_id, year_id, date_obj):
    """Check if a date is a weekend or a holiday (global or local)."""
    # Weekend check (DISABLED FOR TESTING)
    # if date_obj.weekday() >= 5: # 5=Saturday, 6=Sunday
    #     return True, "Weekend"
    
    # Holiday check
    cur.execute("""
        SELECT holiday_name 
        FROM holidays 
        WHERE (branch_id = %s OR branch_id IS NULL) 
          AND year_id = %s AND holiday_date = %s
        LIMIT 1
    """, (branch_id, year_id, date_obj))
    row = cur.fetchone()
    if row:
        return True, row["holiday_name"]
    
    return False, None

def _count_school_days(cur, branch_id, year_id, start_date, end_date):
    """Count non-weekend, non-holiday days in range."""
    # Fetch all holidays in range
    cur.execute("""
        SELECT holiday_date 
        FROM holidays 
        WHERE (branch_id = %s OR branch_id IS NULL) 
          AND year_id = %s AND holiday_date BETWEEN %s AND %s
    """, (branch_id, year_id, start_date, end_date))
    holidays = {r["holiday_date"] for r in cur.fetchall()}
    
    total = 0
    curr = start_date
    while curr <= end_date:
        if curr.weekday() < 5 and curr not in holidays:
            total += 1
        curr += pd.Timedelta(days=1)
    return total


def parse_text_to_questions(raw_text):
    """Common parser for DOCX, PDF, and OCR text."""
    questions = []
    current_question = {}
    
    # Standard patterns (Allow both : and . and ) for choices A, B, C, D)
    field_patterns = [
        r'^question:', r'^type:', r'^answer:', r'^points:',
        r'^a[:\.\)]', r'^b[:\.\)]', r'^c[:\.\)]', r'^d[:\.\)]'
    ]
    # Compiled regex for splitting and matching
    field_regex = re.compile(r'(question:|type:|answer:|points:|\b[a-d][:\.\)])', re.IGNORECASE)

    # Split by fields and clean up
    # We use regex to find the start of each field
    lines = raw_text.split('\n')
    processed_lines = []
    
    for line in lines:
        text = line.strip()
        if not text: continue
        
        # Split line into parts based on fields found within it
        parts = [p.strip() for p in field_regex.split(text) if p.strip()]
        it = iter(parts)
        for part in it:
            # Check if this part is a field indicator
            if field_regex.match(part):
                processed_lines.append(part + " " + next(it, ""))
            else:
                if processed_lines:
                    processed_lines[-1] += " " + part
                else:
                    # If no field yet, treat as start of a question
                    processed_lines.append("question: " + part)

    for line in processed_lines:
        line = line.strip()
        if not line: continue
        lower = line.lower()
        
        if lower.startswith('question:'):
            if current_question:
                questions.append(current_question)
                current_question = {}
            current_question['question_text'] = line.split(':', 1)[1].strip()
        elif lower.startswith('type:'):
            current_question['question_type'] = line.split(':', 1)[1].strip()
        elif re.match(r'^a[:\.\)]', lower):
            current_question['choice_a'] = re.sub(r'^[aA][:\.\)]\s*', '', line).strip()
        elif re.match(r'^b[:\.\)]', lower):
            current_question['choice_b'] = re.sub(r'^[bB][:\.\)]\s*', '', line).strip()
        elif re.match(r'^c[:\.\)]', lower):
            current_question['choice_c'] = re.sub(r'^[cC][:\.\)]\s*', '', line).strip()
        elif re.match(r'^d[:\.\)]', lower):
            current_question['choice_d'] = re.sub(r'^[dD][:\.\)]\s*', '', line).strip()
        elif lower.startswith('answer:'):
            current_question['correct_answer'] = line.split(':', 1)[1].strip()
        elif lower.startswith('points:'):
            current_question['points'] = line.split(':', 1)[1].strip()

    if current_question:
        questions.append(current_question)
    
    return questions

def parse_docx(file):
    document = Document(file)
    full_text = "\n".join([para.text for para in document.paragraphs])
    return parse_text_to_questions(full_text)

def parse_pdf(file):
    import pdfplumber
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return parse_text_to_questions(text)

def parse_image(file):
    """Extract text using OCR and parse into questions."""
    if not HAS_OCR:
        raise ImportError("OCR libraries (pytesseract/Pillow) are not installed.")
    
    try:
        img = Image.open(file)
        text = pytesseract.image_to_string(img)
        if not text.strip():
            # Try some basic image enhancement if no text found
            img = img.convert('L') # grayscale
            text = pytesseract.image_to_string(img)
            
        return parse_text_to_questions(text)
    except Exception as e:
        if "tesseract is not installed" in str(e).lower() or "no such file" in str(e).lower():
            raise RuntimeError("Tesseract OCR engine not found on the server. Please install it to use image import.")
        raise e



def _get_active_school_year(cur, branch_id):
    cur.execute("""
        SELECT year_id 
        FROM school_years 
        WHERE  is_active = TRUE AND branch_id = %s
        LIMIT 1
    """, (branch_id,))
    row = cur.fetchone()
    if not row:
        return None
    if isinstance(row, tuple):
        return row[0]
    return row["year_id"]


def _sync_matching_options_for_exam(cur, exam_id, user_id, branch_id, year_id):
    """
    Ensures all matching-type questions in an exam (or batch of exams) share the same 
    set of choices (all possible correct answers).
    """
    # 1. Check if batch_id exists to sync across multiple sections' copies of this exam
    cur.execute("SELECT batch_id FROM exams WHERE exam_id = %s", (exam_id,))
    row = cur.fetchone()
    batch_id = row["batch_id"] if row else None
    
    target_exam_ids = [exam_id]
    if batch_id:
        cur.execute("""
            SELECT e.exam_id FROM exams e
            JOIN sections s ON e.section_id = s.section_id
            WHERE e.batch_id = %s AND e.teacher_id = %s AND e.branch_id = %s AND s.year_id = %s
        """, (batch_id, user_id, branch_id, year_id))
        target_exam_ids = [r["exam_id"] for r in (cur.fetchall() or [])]
    
    for t_id in target_exam_ids:
        # 2. Collect all correct answers for matching questions in THIS specific exam copy
        cur.execute("""
            SELECT DISTINCT correct_answer FROM exam_questions
            WHERE exam_id = %s AND question_type = 'matching'
        """, (t_id,))
        rows = cur.fetchall() or []
        
        # Deduplicate and sort
        all_opts = []
        seen = set()
        for r in rows:
            ans = str(r["correct_answer"] or "").strip()
            if ans and ans not in seen:
                all_opts.append(ans)
                seen.add(ans)
        all_opts.sort()
        
        choices_json = json.dumps({"options": all_opts}) if all_opts else None
        
        # 3. Update all matching questions for this exam with the new shared pool
        cur.execute("""
            UPDATE exam_questions
            SET choices = %s
            WHERE exam_id = %s AND question_type = 'matching'
        """, (choices_json, t_id))



@teacher_bp.route("/teacher")
def teacher_dashboard():
    if not _require_teacher():
        return redirect("/")

    user_id   = session.get("user_id")
    branch_id = session.get("branch_id")

    db = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
        SELECT COALESCE(g.name, u.grade_level) AS grade_level
        FROM users u
        LEFT JOIN grade_levels g ON u.grade_level_id = g.id
        WHERE u.user_id = %s
    """, (user_id,))
        row = cur.fetchone()
        teacher_grade = row["grade_level"] if row else None
    finally:
        cur.close()
        db.close()

    selected_grade = (request.args.get("grade") or teacher_grade or "").strip()
    selected_section_id = request.args.get("section_id", type=int)

    students = []
    announcements = []
    admin_announcements = []
    teacher_assignments = []
    stats = {"total": 0, "cleared": 0, "pending_bill": 0,
             "reserved": 0, "claimed": 0, "no_reservation": 0}

    if selected_grade:
        grade_full, grade_short = _normalize_grade(selected_grade)

        db  = get_db_connection()
        cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            year_id = _get_active_school_year(cur, branch_id)
            if not year_id:
                flash("No active school year set. Please inform your branch admin.", "error")
                # Continue rendering without crashing or looping
                year_id = 0
            # ── Students ──
            query_str = """
                SELECT
                    e.enrollment_id,
                    e.student_name,
                    e.grade_level,
                    e.status            AS enrollment_status,

                    COALESCE((
                        SELECT CASE
                            WHEN SUM(b.total_amount - COALESCE(b.amount_paid,0)) <= 0
                            THEN 'CLEARED' ELSE 'PENDING'
                        END
                        FROM billing b
                        WHERE b.enrollment_id = e.enrollment_id
                    ), 'NO_BILL') AS billing_status,

                    COALESCE((
                        SELECT UPPER(r.status)
                        FROM reservations r
                        WHERE r.enrollment_id = e.enrollment_id
                          AND r.branch_id = %(branch_id)s
                        ORDER BY r.created_at DESC
                        LIMIT 1
                    ), 'NONE') AS reservation_status

                FROM enrollments e
                WHERE e.branch_id = %(branch_id)s
                  AND (
                      e.grade_level ILIKE %(grade_full)s
                      OR e.grade_level ILIKE %(grade_short)s
                  )
                  AND e.status IN ('approved', 'enrolled')
                  AND e.year_id = %(year_id)s 
            """
            
            query_params = {
                "branch_id":   branch_id,
                "grade_full":  grade_full,
                "grade_short": grade_short,
                "year_id":     year_id,     
            }
            
            if selected_section_id:
                query_str += " AND e.section_id = %(section_id)s "
                query_params["section_id"] = selected_section_id
                
            query_str += " ORDER BY e.student_name ASC "
            
            cur.execute(query_str, query_params)
            students = cur.fetchall() or []

            stats["total"] = len(students)
            for s in students:
                billing = (s["billing_status"] or "").upper()
                if billing == "CLEARED":
                    stats["cleared"] += 1
                elif billing in ("PENDING", "NO_BILL"):
                    stats["pending_bill"] += 1

                res = (s["reservation_status"] or "").upper()
                if res == "CLAIMED":
                    stats["claimed"] += 1
                elif res in ("PENDING", "RESERVED"):
                    stats["reserved"] += 1
                else:
                    stats["no_reservation"] += 1

            year_id = _get_active_school_year(cur, branch_id)
            # ── Announcements for this grade ──
            cur.execute("""
    SELECT a.announcement_id, a.title, a.body,
           a.created_at, u.username AS posted_by,
           u.full_name, u.gender
    FROM teacher_announcements a
    JOIN users u ON u.user_id = a.teacher_user_id
    WHERE a.branch_id   = %(branch_id)s
      AND (
          a.grade_level ILIKE %(grade_full)s
          OR a.grade_level ILIKE %(grade_short)s
      )
    ORDER BY a.created_at DESC
""", {
    "branch_id":   branch_id,
    "grade_full":  grade_full,
    "grade_short": grade_short,
})
            raw_ann = cur.fetchall() or []

            # Build display name: "Ms. Joy Cruz" or "Mr. Juan dela Cruz"
            announcements = []
            for a in raw_ann:
                a = dict(a)
                prefix = ""
                if a.get("gender") == "female":
                    prefix = "Ms. "
                elif a.get("gender") == "male":
                    prefix = "Mr. "
                a["display_name"] = prefix + (a.get("full_name") or a.get("posted_by") or "Teacher")
                announcements.append(a)

            # ── Sections + subjects assigned to this teacher (for this branch) ──
            cur.execute(
                """
                SELECT
                    s.section_id,
                    s.section_name,
                    g.name  AS grade_level_name,
                    sub.subject_id,
                    sub.name AS subject_name,
                    sch.day_of_week,
                    sch.start_time,
                    sch.end_time,
                    sch.room
                FROM section_teachers st
                JOIN sections s     ON st.section_id = s.section_id
                JOIN grade_levels g ON s.grade_level_id = g.id
                JOIN subjects sub   ON st.subject_id  = sub.subject_id
                LEFT JOIN schedules sch ON sch.section_id = s.section_id 
                                       AND sch.subject_id = sub.subject_id 
                                       AND sch.teacher_id = st.teacher_id
                                       AND sch.year_id = s.year_id
                WHERE st.teacher_id = %s
                  AND s.branch_id = %s AND s.year_id = %s
                ORDER BY g.display_order, s.section_name, sub.name,
                         CASE 
                            WHEN sch.day_of_week = 'Monday' THEN 1
                            WHEN sch.day_of_week = 'Tuesday' THEN 2
                            WHEN sch.day_of_week = 'Wednesday' THEN 3
                            WHEN sch.day_of_week = 'Thursday' THEN 4
                            WHEN sch.day_of_week = 'Friday' THEN 5
                            WHEN sch.day_of_week = 'Saturday' THEN 6
                            WHEN sch.day_of_week = 'Sunday' THEN 7
                            ELSE 8
                         END, sch.start_time
                """,
                (user_id, branch_id, year_id),
            )
            teacher_assignments = cur.fetchall() or []

            # ── Branch Admin Announcements (for teachers) ──
            cur.execute("""
    SELECT announcement_id AS id, title, message, (created_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Manila') AS created_at_local, image_url
    FROM announcements
    WHERE is_active = TRUE
      AND branch_id = %s
      AND audience IN ('all','teacher')
    ORDER BY created_at DESC
    LIMIT 20
            """, (branch_id,))
            admin_announcements = cur.fetchall() or []

        finally:
            cur.close()
            db.close()

    # --- Live Class & Pending Tasks logic ---
    ph_tz = pytz.timezone("Asia/Manila")
    now_manila = datetime.now(ph_tz)
    current_time_str = now_manila.strftime('%H:%M:%S')
    today_day = now_manila.strftime('%A')

    current_class = None
    next_class = None
    pending_attendance = []
    
    # Filter assignments for today
    today_assignments = [a for a in teacher_assignments if a.get('day_of_week') == today_day]
    
    db = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        for a in today_assignments:
            if a.get('start_time') and a.get('end_time'):
                st = a['start_time'].strftime('%H:%M:%S')
                et = a['end_time'].strftime('%H:%M:%S')
                
                # Identify current and next class
                if st <= current_time_str <= et:
                    current_class = a
                elif st > current_time_str:
                    if not next_class or st < next_class['start_time'].strftime('%H:%M:%S'):
                        next_class = a
                
                # Check for pending attendance (if class has started)
                if st <= current_time_str:
                    cur.execute("""
                        SELECT COUNT(*) as count 
                        FROM daily_attendance 
                        WHERE subject_id = %s 
                          AND recorded_by = %s 
                          AND attendance_date = CURRENT_DATE
                    """, (a['subject_id'], user_id))
                    if cur.fetchone()['count'] == 0:
                        pending_attendance.append(a)
    finally:
        cur.close()
        db.close()

    return render_template(
        "teacher_dashboard.html",
        students=students,
        stats=stats,
        teacher_grade=teacher_grade,
        selected_grade=selected_grade,
        grade_levels=GRADE_LEVELS,
        admin_announcements=admin_announcements,
        teacher_assignments=teacher_assignments,
        teacher_user_id=session.get("user_id"),
        selected_section_id=selected_section_id,
        current_day=today_day,
        current_class=current_class,
        next_class=next_class,
        pending_attendance=pending_attendance
    )


# ── Class Announcements Page ──────────────────────────────
@teacher_bp.route("/teacher/class-announcements")
def teacher_class_announcements():
    if not _require_teacher():
        return redirect("/")

    user_id = session.get("user_id")
    branch_id = session.get("branch_id")
    
    db = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
            SELECT COALESCE(g.name, u.grade_level) AS grade_level
            FROM users u
            LEFT JOIN grade_levels g ON u.grade_level_id = g.id
            WHERE u.user_id = %s
        """, (user_id,))
        row = cur.fetchone()
        teacher_grade = row["grade_level"] if row else None
    finally:
        cur.close()
        db.close()

    # Fetch specific sections assigned to this teacher
    db = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        year_id = _get_active_school_year(cur, branch_id)
        cur.execute("""
            SELECT DISTINCT
                s.section_id,
                s.section_name,
                g.name AS grade_level_name
            FROM section_teachers st
            JOIN sections s     ON st.section_id = s.section_id
            JOIN grade_levels g ON s.grade_level_id = g.id
            WHERE st.teacher_id = %s AND s.branch_id = %s AND s.year_id = %s
            ORDER BY g.name, s.section_name
        """, (user_id, branch_id, year_id or 0))
        teacher_sections = cur.fetchall() or []
    finally:
        cur.close()
        db.close()



    selected_grade = (request.args.get("grade") or teacher_grade or "").strip()
    selected_section = request.args.get("section_id", type=int)
    announcements = []

    db = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        query = """
            SELECT a.announcement_id, a.title, a.body,
                   a.created_at, u.username AS posted_by,
                   u.full_name, u.gender, a.grade_level
            FROM teacher_announcements a
            JOIN users u ON u.user_id = a.teacher_user_id
            WHERE a.branch_id = %s
        """
        params = [branch_id]

        if selected_section:
            # Match specifically by section ID (hack using grade_level column format 'GradeName:SectionID')
            query += " AND a.grade_level LIKE '%%:' || %s"
            params.append(str(selected_section))
        elif selected_grade:
            grade_full, grade_short = _normalize_grade(selected_grade)
            query += " AND (a.grade_level ILIKE %s OR a.grade_level ILIKE %s)"
            params.append(grade_full)
            params.append(grade_short)

        query += " ORDER BY a.created_at DESC"
        cur.execute(query, params)
        raw_ann = cur.fetchall() or []
        
        for a in raw_ann:
            prefix = "Ms. " if a.get("gender") == "female" else "Mr. " if a.get("gender") == "male" else ""
            a["display_name"] = prefix + (a.get("full_name") or a.get("posted_by") or "Teacher")
            announcements.append(a)
    finally:
        cur.close()
        db.close()

    return render_template(
        "teacher_class_announcements.html",
        selected_grade=selected_grade,
        selected_section=selected_section,
        announcements=announcements,
        teacher_sections=teacher_sections,
        teacher_grade=teacher_grade
    )


# ── Save grade assignment ─────────────────────────────────
@teacher_bp.route("/teacher/set-grade", methods=["POST"])
def teacher_set_grade():
    if not _require_teacher():
        return redirect("/")

    user_id = session.get("user_id")
    grade   = (request.form.get("grade_level") or "").strip()

    if grade not in GRADE_LEVELS:
        flash("Invalid grade level.", "error")
        return redirect(url_for("teacher.teacher_dashboard"))

    db  = get_db_connection()
    cur = db.cursor()
    try:
        # Check if branch admin already assigned a grade — if so, block the change
        cur.execute("""
    SELECT g.name AS grade_level
    FROM users u
    LEFT JOIN grade_levels g ON u.grade_level_id = g.id
    WHERE u.user_id = %s
""", (user_id,))
        row = cur.fetchone()
        existing_grade = row[0] if row else None

        if existing_grade:
            flash(f"Your grade level ({existing_grade}) is assigned by the Branch Admin and cannot be changed.", "warning")
            return redirect(url_for("teacher.teacher_dashboard") + f"?grade={existing_grade}")

        cur.execute(
            "UPDATE users SET grade_level = %s WHERE user_id = %s",
            (grade, user_id)
        )
        db.commit()
        flash(f"Grade level set to {grade}.", "success")

    except Exception as e:
        db.rollback()
        flash(str(e), "error")
    finally:
        cur.close()
        db.close()

    return redirect(url_for("teacher.teacher_dashboard") + f"?grade={grade}")


# ── Post Announcement ─────────────────────────────────────
@teacher_bp.route("/teacher/announce", methods=["POST"])
def teacher_announce():
    if not _require_teacher():
        return redirect("/")

    user_id   = session.get("user_id")
    branch_id = session.get("branch_id")
    title     = (request.form.get("title") or "").strip()
    body      = (request.form.get("body")  or "").strip()
    # Now expecting section_id or combined string
    target_section_id = request.form.get("section_id")
    from_page = request.form.get("from_page")

    # Resolve grade level name from section_id if provided
    grade_to_save = ""
    if target_section_id:
        db = get_db_connection()
        cur = db.cursor()
        cur.execute("""
            SELECT g.name 
            FROM sections s 
            JOIN grade_levels g ON s.grade_level_id = g.id 
            WHERE s.section_id = %s
        """, (target_section_id,))
        row = cur.fetchone()
        if row:
            # Store as "GradeName:SectionID" to support section-specific targeting without schema change
            grade_to_save = f"{row[0]}:{target_section_id}"
        cur.close()
        db.close()
    
    if not grade_to_save:
        grade_to_save = (request.form.get("grade_level") or "").strip()

    if from_page == "announcements":
        back_url = url_for("teacher.teacher_class_announcements") + (f"?grade={grade}" if grade else "")
    else:
        back_url = url_for("teacher.teacher_dashboard") + (f"?grade={grade}" if grade else "")

    if not title:
        flash("Announcement title is required.", "error")
        return redirect(back_url)
    if not grade:
        flash("Please select your grade level first.", "error")
        return redirect(url_for("teacher.teacher_dashboard"))

    db  = get_db_connection()
    cur = db.cursor()
    try:
        # year-safety: get the active school year for this branch
        year_id = _get_active_school_year(cur, branch_id)
        if not year_id:
            flash("No active school year.", "error")
            return redirect(back_url)

        cur.execute("""
            INSERT INTO teacher_announcements 
                (teacher_user_id, branch_id, year_id, grade_level, title, body)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING announcement_id
        """, (user_id, branch_id, year_id, grade_to_save, title, body or None))
        ann_id = cur.fetchone()[0]

        # Send notifications only to students enrolled in this year
        import re as _re
        if _re.match(r'^\d+$', grade.strip()):
            grade_short = grade.strip()
            grade_full  = "Grade " + grade_short
        else:
            grade_full  = grade.strip()
            _m2 = _re.match(r'^Grade\s+(\d+)$', grade_full, _re.IGNORECASE)
            grade_short = _m2.group(1) if _m2 else grade_full

        cur.execute("""
            SELECT DISTINCT u.user_id 
            FROM enrollments e
            JOIN users u ON u.user_id = e.user_id
            WHERE e.branch_id = %s 
              AND e.year_id = %s
              AND (
                  (%(target_section)s::text IS NOT NULL AND e.section_id = %(target_section)s::int)
                  OR 
                  (%(target_section)s::text IS NULL AND (e.grade_level ILIKE %(grade_full)s OR e.grade_level ILIKE %(grade_short)s))
              )
              AND e.status IN ('approved', 'enrolled')
            UNION
            SELECT DISTINCT u.user_id
            FROM enrollments e
            JOIN student_accounts sa ON sa.enrollment_id = e.enrollment_id
            JOIN users u ON u.username = sa.username
            WHERE e.branch_id = %s 
              AND e.year_id = %s
              AND (
                  (%(target_section)s::text IS NOT NULL AND e.section_id = %(target_section)s::int)
                  OR 
                  (%(target_section)s::text IS NULL AND (e.grade_level ILIKE %(grade_full)s OR e.grade_level ILIKE %(grade_short)s))
              )
              AND e.status IN ('approved', 'enrolled')
        """, (branch_id, year_id, target_section_id, target_section_id, grade_full, grade_short, 
              branch_id, year_id, target_section_id, target_section_id, grade_full, grade_short))
        students = cur.fetchall()
        if students:
            notif_title = f"New Announcement: {title}"
            notif_msg = f"Your teacher posted a new announcement."
            for s in students:
                uid = s[0] if isinstance(s, tuple) else s['user_id']
                cur.execute("""
                    INSERT INTO student_notifications (student_id, title, message, link)
                    VALUES (%s, %s, %s, %s)
                """, (uid, notif_title, notif_msg, f"/student/dashboard"))

        db.commit()
        flash("Announcement posted! Students in your class will see it.", "success")
    except Exception as e:
        db.rollback()
        flash(f"Could not post announcement: {e}", "error")
    finally:
        cur.close()
        db.close()

    return redirect(back_url)


# ── Delete Announcement ───────────────────────────────────
@teacher_bp.route("/teacher/announce/<int:announcement_id>/delete", methods=["POST"])
def teacher_announce_delete(announcement_id):
    if not _require_teacher():
        return redirect("/")

    user_id = session.get("user_id")
    branch_id = session.get("branch_id")
    grade   = (request.form.get("grade_level") or "").strip()
    from_page = request.form.get("from_page")

    if from_page == "announcements":
        back_url = url_for("teacher.teacher_class_announcements") + (f"?grade={grade}" if grade else "")
    else:
        back_url = url_for("teacher.teacher_dashboard") + (f"?grade={grade}" if grade else "")

    db  = get_db_connection()
    cur = db.cursor()
    try:
        # YEAR SAFETY: restrict deletion to current school year!
        year_id = _get_active_school_year(cur, branch_id)
        if not year_id:
            flash("No active school year.", "error")
            return redirect(back_url)

        cur.execute("""
            DELETE FROM teacher_announcements
            WHERE announcement_id = %s AND teacher_user_id = %s
        """, (announcement_id, user_id))
        db.commit()
        if cur.rowcount:
            flash("Announcement deleted.", "success")
        else:
            flash("Announcement not found, not yours, or not from this year.", "error")
    except Exception as e:
        db.rollback()
        flash(str(e), "error")
    finally:
        cur.close()
        db.close()

    return redirect(back_url)


# ── Edit Announcement ─────────────────────────────────────
@teacher_bp.route("/teacher/announce/<int:announcement_id>/edit", methods=["POST"])
def teacher_announce_edit(announcement_id):
    if not _require_teacher():
        return redirect("/")

    user_id = session.get("user_id")
    branch_id = session.get("branch_id")
    grade   = (request.form.get("grade_level") or "").strip()
    title   = (request.form.get("title") or "").strip()
    body    = (request.form.get("body")  or "").strip()
    from_page = request.form.get("from_page")

    if from_page == "announcements":
        back_url = url_for("teacher.teacher_class_announcements") + (f"?grade={grade}" if grade else "")
    else:
        back_url = url_for("teacher.teacher_dashboard") + (f"?grade={grade}" if grade else "")

    if not title:
        flash("Title cannot be empty.", "error")
        return redirect(back_url)

    db  = get_db_connection()
    cur = db.cursor()
    try:
        # YEAR SAFETY: restrict edit to current school year!
        year_id = _get_active_school_year(cur, branch_id)
        if not year_id:
            flash("No active school year.", "error")
            return redirect(back_url)

        cur.execute("""
            UPDATE teacher_announcements
               SET title = %s, body = %s
             WHERE announcement_id = %s AND teacher_user_id = %s
        """, (title, body or None, announcement_id, user_id))
        db.commit()
        if cur.rowcount:
            flash("Announcement updated.", "success")
        else:
            flash("Announcement not found, not yours, or not from this year.", "error")
    except Exception as e:
        db.rollback()
        flash(str(e), "error")
    finally:
        cur.close()
        db.close()

    return redirect(back_url)


# ── ARCHIVE/UNARCHIVE ROUTES ────────────────────────────────

@teacher_bp.route("/teacher/activities/<int:activity_id>/archive", methods=["POST"])
def archive_activity(activity_id):
    if not _require_teacher(): return redirect("/")
    user_id = session.get("user_id")
    db = get_db_connection()
    cur = db.cursor()
    try:
        active_tab = request.form.get("active_tab", "activities")
        cur.execute("UPDATE activities SET is_archived = TRUE WHERE activity_id = %s AND teacher_id = %s RETURNING subject_id", (activity_id, user_id))
        row = cur.fetchone()
        db.commit()
        if row:
            flash("Activity archived.", "success")
            return redirect(url_for("teacher.teacher_class_view", subject_id=row[0], active_tab=active_tab))
        flash("Activity not found.", "error")
    except Exception as e:
        db.rollback()
        flash(str(e), "error")
    finally:
        cur.close()
        db.close()
    return redirect(url_for("teacher.teacher_dashboard"))

@teacher_bp.route("/teacher/activities/<int:activity_id>/unarchive", methods=["POST"])
def unarchive_activity(activity_id):
    if not _require_teacher(): return redirect("/")
    user_id = session.get("user_id")
    db = get_db_connection()
    cur = db.cursor()
    try:
        active_tab = request.form.get("active_tab", "activities")
        cur.execute("UPDATE activities SET is_archived = FALSE WHERE activity_id = %s AND teacher_id = %s RETURNING subject_id", (activity_id, user_id))
        row = cur.fetchone()
        db.commit()
        if row:
            flash("Activity unarchived.", "success")
            return redirect(url_for("teacher.teacher_class_view", subject_id=row[0], active_tab=active_tab))
        flash("Activity not found.", "error")
    except Exception as e:
        db.rollback()
        flash(str(e), "error")
    finally:
        cur.close()
        db.close()
    return redirect(url_for("teacher.teacher_dashboard"))

@teacher_bp.route("/teacher/exams/<int:exam_id>/archive", methods=["POST"])
def archive_exam(exam_id):
    if not _require_teacher(): return redirect("/")
    user_id = session.get("user_id")
    db = get_db_connection()
    cur = db.cursor()
    try:
        active_tab = request.form.get("active_tab", "exams")
        cur.execute("UPDATE exams SET is_archived = TRUE WHERE exam_id = %s AND teacher_id = %s RETURNING subject_id, exam_type", (exam_id, user_id))
        row = cur.fetchone()
        db.commit()
        if row:
            label = "Quiz" if row[1] == 'quiz' else "Exam"
            flash(f"{label} archived.", "success")
            return redirect(url_for("teacher.teacher_class_view", subject_id=row[0], active_tab=active_tab))
        flash("Not found.", "error")
    except Exception as e:
        db.rollback()
        flash(str(e), "error")
    finally:
        cur.close()
        db.close()
    return redirect(url_for("teacher.teacher_dashboard"))

@teacher_bp.route("/teacher/exams/<int:exam_id>/unarchive", methods=["POST"])
def unarchive_exam(exam_id):
    if not _require_teacher(): return redirect("/")
    user_id = session.get("user_id")
    db = get_db_connection()
    cur = db.cursor()
    try:
        active_tab = request.form.get("active_tab", "exams")
        cur.execute("UPDATE exams SET is_archived = FALSE WHERE exam_id = %s AND teacher_id = %s RETURNING subject_id, exam_type", (exam_id, user_id))
        row = cur.fetchone()
        db.commit()
        if row:
            label = "Quiz" if row[1] == 'quiz' else "Exam"
            flash(f"{label} unarchived.", "success")
            return redirect(url_for("teacher.teacher_class_view", subject_id=row[0], active_tab=active_tab))
        flash("Not found.", "error")
    except Exception as e:
        db.rollback()
        flash(str(e), "error")
    finally:
        cur.close()
        db.close()
    return redirect(url_for("teacher.teacher_dashboard"))


# ── DELETE ROUTES ──────────────────────────────────────────

@teacher_bp.route("/teacher/activities/<int:activity_id>/delete", methods=["POST"])
def delete_activity(activity_id):
    if not _require_teacher(): return redirect("/")
    user_id = session.get("user_id")
    branch_id = session.get("branch_id")
    db = get_db_connection()
    cur = db.cursor()
    try:
        active_tab = request.form.get("active_tab")
        # Year+ownership check
        year_id = _get_active_school_year(cur, branch_id)
        if not year_id:
            flash("No active school year.", "error")
            return redirect(url_for("teacher.teacher_dashboard"))
        cur.execute("""
            SELECT a.activity_id, a.subject_id, a.is_archived
            FROM activities a
            JOIN sections s ON a.section_id = s.section_id
            WHERE a.activity_id = %s AND a.teacher_id = %s AND s.year_id = %s
        """, (activity_id, user_id, year_id))
        row = cur.fetchone()
        if not row:
            flash("Activity not found or unauthorized.", "error")
            return redirect(url_for("teacher.teacher_dashboard"))
        
        # subject_id for redirect (works with both RealDictCursor and default)
        subject_id = row['subject_id'] if isinstance(row, dict) else row[1]
        is_archived = row['is_archived'] if isinstance(row, dict) else row[2]

        if not is_archived:
            flash("You must archive the activity before you can delete it.", "warning")
            return redirect(url_for("teacher.teacher_class_view", subject_id=subject_id, active_tab=active_tab))

        # Cascade delete only for this activity
        cur.execute("DELETE FROM activity_grades WHERE activity_id=%s", (activity_id,))
        cur.execute("DELETE FROM activity_submissions WHERE activity_id=%s", (activity_id,))
        cur.execute("DELETE FROM student_notifications WHERE link LIKE %s", (f"%/student/activities/{activity_id}%",))
        cur.execute("DELETE FROM activities WHERE activity_id=%s AND teacher_id=%s", (activity_id, user_id))
        db.commit()
        flash("Activity deleted successfully.", "success")
        return redirect(url_for("teacher.teacher_class_view", subject_id=subject_id, active_tab=active_tab))
    except Exception as e:
        db.rollback()
        flash(f"Could not delete: {str(e)}", "error")
        return redirect(url_for("teacher.teacher_dashboard"))
    finally:
        cur.close()
        db.close()


@teacher_bp.route("/teacher/exams/<int:exam_id>/delete", methods=["POST"])
def delete_exam(exam_id):
    if not _require_teacher(): return redirect("/")
    user_id = session.get("user_id")
    branch_id = session.get("branch_id")
    db = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        year_id = _get_active_school_year(cur, branch_id)
        if not year_id:
            flash("No active school year.", "error")
            return redirect(url_for("teacher.teacher_dashboard"))

        active_tab = request.form.get("active_tab")
        # Year+ownership check
        cur.execute("""
            SELECT e.exam_id, e.exam_type, e.subject_id, e.section_id, e.batch_id, e.is_archived
            FROM exams e
            JOIN sections s ON e.section_id = s.section_id
            WHERE e.exam_id = %s AND e.teacher_id = %s AND s.year_id = %s
        """, (exam_id, user_id, year_id))
        row = cur.fetchone()
        if not row:
            flash("Not found or unauthorized.", "error")
            return redirect(url_for("teacher.teacher_dashboard"))

        if not row['is_archived']:
            flash(f"You must archive the {row['exam_type']} before you can delete it.", "warning")
            return redirect(url_for("teacher.teacher_class_view", subject_id=row['subject_id'], active_tab=active_tab))

        subject_id = row['subject_id']

        # Cascade delete all linked copies if this is a batch-created quiz/exam.
        if row.get("batch_id"):
            cur.execute("""
                SELECT e.exam_id
                FROM exams e
                JOIN sections s ON e.section_id = s.section_id
                WHERE e.batch_id = %s
                  AND e.teacher_id = %s
                  AND s.year_id = %s
            """, (row["batch_id"], user_id, year_id))
            target_exam_ids = [r["exam_id"] for r in (cur.fetchall() or [])]
        else:
            target_exam_ids = [exam_id]

        if target_exam_ids:
            cur.execute("DELETE FROM exam_results WHERE exam_id = ANY(%s)", (target_exam_ids,))
            cur.execute("DELETE FROM exam_questions WHERE exam_id = ANY(%s)", (target_exam_ids,))
            cur.execute("DELETE FROM exams WHERE exam_id = ANY(%s) AND teacher_id = %s", (target_exam_ids, user_id))

        # Clear related student notifications for this subject/exam pages.
        cur.execute("DELETE FROM student_notifications WHERE link = %s", (f"/student/subject/{subject_id}",))
        for target_id in target_exam_ids:
            cur.execute("DELETE FROM student_notifications WHERE link = %s", (f"/student/exams/{target_id}",))
        db.commit()
        flash("Deleted successfully.", "success")
        return redirect(url_for("teacher.teacher_class_view", subject_id=subject_id, active_tab=active_tab))
    except Exception as e:
        db.rollback()
        flash(f"Could not delete: {str(e)}", "error")
        return redirect(url_for("teacher.teacher_dashboard"))
    finally:
        cur.close()
        db.close()


# ── ACTIVITIES MODULE (TEACHER SIDE) ──────────────────────

@teacher_bp.route("/teacher/activities")
def activities():
    if not _require_teacher(): return redirect("/")
    user_id = session.get("user_id")
    branch_id = session.get("branch_id")
    
    db = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        year_id = _get_active_school_year(cur, branch_id)
        if not year_id:
            flash("No active school year.", "error")
            return redirect(url_for("teacher.teacher_dashboard"))
        cur.execute('''
            SELECT a.*, 
                s.section_name, 
                sub.name AS subject_name,
                (SELECT COUNT(*) FROM activity_submissions sub2 WHERE sub2.activity_id = a.activity_id) AS submission_count
            FROM activities a
            JOIN sections s ON a.section_id = s.section_id
            JOIN subjects sub ON a.subject_id = sub.subject_id
            WHERE a.teacher_id = %s AND a.branch_id = %s AND s.year_id = %s
            ORDER BY a.created_at DESC
        ''', (user_id, branch_id, year_id))
        activities = cur.fetchall()
        
        stats = {
            'total': len(activities),
            'published': sum(1 for a in activities if a['status'] == 'Published'),
            'drafts': sum(1 for a in activities if a['status'] == 'Draft'),
            'closed': sum(1 for a in activities if a['status'] == 'Closed')
        }
    finally:
        cur.close()
        db.close()
        
    return render_template("teacher_activities.html", activities=activities, stats=stats)


@teacher_bp.route("/teacher/activities/create", methods=["GET", "POST"])
def create_activity():
    if not _require_teacher(): return redirect("/")
    user_id = session.get("user_id")
    branch_id = session.get("branch_id")
    
    db = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    unlocked_periods = GRADING_PERIODS[:]
    try:
        year_id = _get_active_school_year(cur, branch_id)
        if not year_id:
            flash("No active school year.", "error")
            return redirect(url_for("teacher.teacher_dashboard"))
        
        if request.method == "POST":
            title = request.form.get("title", "").strip()
            subject_id = request.form.get("subject_id")
            section_ids = request.form.getlist("section_ids")
            category = request.form.get("category", "")
            instructions = request.form.get("instructions", "").strip()
            max_score = int(request.form.get("max_score", 100))
            due_date = request.form.get("due_date", "")
            status = request.form.get("status", "Draft")
            allowed_file_types = request.form.get("allowed_file_types", "").strip()
            
            # Respect explicitly selected period (from subject tab), then fallback to auto-detect.
            grading_period = (request.form.get("grading_period") or "").strip()
            if not grading_period and due_date:
                dt_obj = datetime.strptime(due_date.split('T')[0], '%Y-%m-%d').date()
                grading_period = _get_grading_period_by_date(cur, branch_id, year_id, dt_obj)
            grading_period = _normalize_period_name(grading_period)
                
            if not grading_period:
                flash("The selected Due Date does not fall within any configured Grading Period. Please check the Academic Calendar or contact your admin.", "error")
                return redirect(url_for("teacher.create_activity", subject_id=subject_id))
            if grading_period not in GRADING_PERIODS:
                flash("Invalid grading period selected.", "error")
                return redirect(url_for("teacher.create_activity", subject_id=subject_id))
            unlocked_periods = _get_unlocked_grading_periods(cur, branch_id, year_id)
            if grading_period not in unlocked_periods:
                flash(f"{grading_period} Grading is not open yet based on the Academic Calendar.", "error")
                return redirect(url_for("teacher.create_activity", subject_id=subject_id, period=grading_period))
            
            if not subject_id or not section_ids:
                flash("Subject and at least one section are required.", "error")
                return redirect(url_for("teacher.create_activity", subject_id=subject_id))
            import uuid
            batch_id = str(uuid.uuid4())[:8]  # links this activity across all chosen sections
            
            attachment_path = None
            if 'attachment' in request.files:
                file = request.files['attachment']
                if file.filename != '':
                    try:
                        attachment_path = upload_file(file, folder="liceo_activities")
                    except Exception as e:
                        flash(f"File upload failed: {e}", "error")
                        return redirect(url_for("teacher.create_activity", subject_id=subject_id))
                        
            for section_id in section_ids:
                cur.execute("""
                    SELECT 1 FROM section_teachers st
                    JOIN sections s ON st.section_id = s.section_id
                    WHERE st.teacher_id = %s AND st.section_id = %s AND s.year_id = %s
                    """, (user_id, section_id, year_id))
                if not cur.fetchone():
                    flash("You do not have permission to add activities to this section/year.", "error")
                    return redirect(url_for("teacher.create_activity", subject_id=subject_id))
                
                cur.execute('''
                    INSERT INTO activities (
                        branch_id, section_id, subject_id, teacher_id, 
                        title, category, instructions, max_score, due_date, 
                        status, allowed_file_types, attachment_path, grading_period, batch_id, year_id
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING activity_id
                ''', (branch_id, section_id, subject_id, user_id, 
                      title, category, instructions, max_score, due_date or None, 
                      status, allowed_file_types, attachment_path, grading_period, batch_id, year_id))
                activity_id = cur.fetchone()['activity_id']
                
                if status == 'Published':
                    cur.execute("""
                SELECT DISTINCT u.user_id 
                FROM enrollments e 
                    JOIN users u ON u.user_id = e.user_id 
                    WHERE e.section_id = %s AND e.year_id = %s AND e.status IN ('approved', 'enrolled')
                    UNION
                SELECT DISTINCT u.user_id
                FROM enrollments e
                JOIN student_accounts sa ON sa.enrollment_id = e.enrollment_id
                JOIN users u ON u.username = sa.username
                WHERE e.section_id = %s AND e.year_id = %s AND e.status IN ('approved', 'enrolled')
                    """, (section_id, year_id, section_id, year_id))
                    student_users = cur.fetchall()
                    if student_users:
                        notifs = [(su['user_id'], f"New Activity: {title}", f"Your teacher posted a new activity: {title}.", f"/student/activities/{activity_id}") for su in student_users]
                        for notif in notifs:
                            cur.execute("""
                                INSERT INTO student_notifications (student_id, title, message, link) 
                                VALUES (%s, %s, %s, %s)
                            """, notif)
                        
            db.commit()
            
            flash("Activity created successfully!", "success")
            return redirect(url_for(
                "teacher.teacher_class_view",
                subject_id=subject_id,
                section=int(section_ids[0]),
                active_tab="activities",
                period=grading_period
            ))
        
        # GET: fetch sections and subjects for this teacher
        cur.execute('''
    SELECT s.section_id, s.section_name, g.name AS grade_level_name, 
           sub.subject_id, sub.name AS subject_name 
    FROM section_teachers st
    JOIN sections s ON st.section_id = s.section_id
    JOIN grade_levels g ON s.grade_level_id = g.id
    JOIN subjects sub ON st.subject_id = sub.subject_id
    WHERE st.teacher_id = %s AND s.branch_id = %s AND s.year_id = %s
    ORDER BY g.display_order, s.section_name, sub.name
''', (user_id, branch_id, year_id))
        teacher_assignments = cur.fetchall()
        unlocked_periods = _get_unlocked_grading_periods(cur, branch_id, year_id)
        
    finally:
        cur.close()
        db.close()
        
    # GET
    ph_tz = pytz.timezone("Asia/Manila")
    ph_now = datetime.now(ph_tz)
    min_date = ph_now.strftime("%Y-%m-%d") + "T00:00"
    
    subject_id = request.args.get("subject_id")
    selected_period = _normalize_period_name(request.args.get("period"))
    
    return render_template("teacher_create_activity.html", 
                         teacher_assignments=teacher_assignments, 
                         min_date=min_date,
                         subject_id=subject_id,
                         selected_period=selected_period,
                         unlocked_periods=unlocked_periods)


@teacher_bp.route("/teacher/activities/<int:activity_id>/edit", methods=["GET", "POST"])
def edit_activity(activity_id):
    if not _require_teacher(): return redirect("/")
    user_id = session.get("user_id")
    branch_id = session.get("branch_id")
    
    db = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    try:
        year_id = _get_active_school_year(cur, branch_id)
        if not year_id:
            flash("No active school year.", "error")
            return redirect(url_for("teacher.teacher_dashboard"))
        
        # Check ownership
        cur.execute("""
    SELECT a.* 
    FROM activities a
    JOIN sections s ON a.section_id = s.section_id
    WHERE a.activity_id = %s AND a.teacher_id = %s AND s.year_id = %s
        """, (activity_id, user_id, year_id))
        activity = cur.fetchone()
        if not activity:
            flash("Activity not found or unauthorized.", "error")
            return redirect(url_for("teacher.activities"))
            
        if request.method == "POST":
            title = request.form.get("title", "").strip()
            category = request.form.get("category", "")
            instructions = request.form.get("instructions", "").strip()
            max_score = int(request.form.get("max_score", 100))
            due_date = request.form.get("due_date", "")
            status = request.form.get("status", "Draft")
            allowed_file_types = request.form.get("allowed_file_types", "").strip()
            
            # Smart Auto-detect Grading Period on Edit
            grading_period = (request.form.get("grading_period") or "").strip()
            if not grading_period and due_date:
                dt_obj = datetime.strptime(due_date.split('T')[0], '%Y-%m-%d').date()
                grading_period = _get_grading_period_by_date(cur, branch_id, year_id, dt_obj)
            grading_period = _normalize_period_name(grading_period)
                
            if not grading_period:
                flash("The updated Due Date does not fall within any configured Grading Period. Please check the date.", "error")
                return redirect(url_for("teacher.edit_activity", activity_id=activity_id))
            if grading_period not in GRADING_PERIODS:
                flash("Invalid grading period selected.", "error")
                return redirect(url_for("teacher.edit_activity", activity_id=activity_id))
            unlocked_periods = _get_unlocked_grading_periods(cur, branch_id, year_id)
            if grading_period not in unlocked_periods:
                flash(f"{grading_period} Grading is not open yet based on the Academic Calendar.", "error")
                return redirect(url_for("teacher.edit_activity", activity_id=activity_id))
            
            attachment_path = activity['attachment_path']
            if 'attachment' in request.files:
                file = request.files['attachment']
                if file.filename != '':
                    try:
                        attachment_path = upload_file(file, folder="liceo_activities")
                    except Exception as e:
                        flash(f"File upload failed: {e}", "error")
                        return redirect(url_for("teacher.edit_activity", activity_id=activity_id))
            
            cur.execute('''
            UPDATE activities SET
                title = %s, category = %s, instructions = %s, max_score = %s, 
                due_date = %s, status = %s, allowed_file_types = %s, attachment_path = %s,
                grading_period = %s, updated_at = NOW()
            WHERE activity_id = %s
            ''', (title, category, instructions, max_score, due_date or None, 
                status, allowed_file_types, attachment_path, grading_period, activity_id))
                  
            if status == 'Published' and activity['status'] != 'Published':
                cur.execute("""
    SELECT DISTINCT u.user_id 
    FROM enrollments e 
    JOIN users u ON u.user_id = e.user_id 
    WHERE e.section_id = %s AND e.year_id = %s AND e.status IN ('approved', 'enrolled')
    UNION
    SELECT DISTINCT u.user_id
    FROM enrollments e
    JOIN student_accounts sa ON sa.enrollment_id = e.enrollment_id
    JOIN users u ON u.username = sa.username
    WHERE e.section_id = %s AND e.year_id = %s AND e.status IN ('approved', 'enrolled')
""", (activity['section_id'], year_id, activity['section_id'], year_id))
                student_users = cur.fetchall()
                if student_users:
                    notifs = [(su['user_id'], f"New Activity: {title}", f"Your teacher posted a new activity: {title}.", f"/student/activities/{activity_id}") for su in student_users]
                    for notif in notifs:
                        cur.execute("""
                            INSERT INTO student_notifications (student_id, title, message, link) 
                            VALUES (%s, %s, %s, %s)
                        """, notif)
            
            db.commit()
            
            flash("Activity updated successfully!", "success")
            return redirect(url_for("teacher.teacher_class_view", subject_id=activity['subject_id']))
            
    finally:
        cur.close()
        db.close()
        
    ph_tz = pytz.timezone("Asia/Manila")
    ph_now = datetime.now(ph_tz)
    min_date = ph_now.strftime("%Y-%m-%d") + "T00:00"
    return render_template("teacher_edit_activity.html", activity=activity, min_date=min_date)


@teacher_bp.route("/teacher/activities/<int:activity_id>/submissions")
def activity_submissions(activity_id):
    if not _require_teacher(): return redirect("/")
    user_id = session.get("user_id")
    branch_id = session.get("branch_id")
    
    db = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        year_id = _get_active_school_year(cur, branch_id)
        if not year_id:
            flash("No active school year.", "error")
            return redirect(url_for("teacher.teacher_dashboard"))
        
        # Get activity context
        # Fetch activity details (Joining with sections to verify year_id)
        cur.execute("""
            SELECT a.*, s.section_name 
            FROM activities a
            JOIN sections s ON a.section_id = s.section_id
            WHERE a.activity_id = %s 
              AND a.teacher_id = %s 
              AND s.year_id = %s
        """, (activity_id, user_id, year_id))
        activity = cur.fetchone()
        if not activity:
            flash("Activity not found or unauthorized", "error")
            return redirect(url_for("teacher.activities"))
            
        # Get all students enrolled in this section/class
        cur.execute('''
            SELECT e.enrollment_id, e.student_name, u.user_id as student_user_id
            FROM enrollments e
            LEFT JOIN users u ON u.user_id = e.user_id
            WHERE e.section_id = %s
              AND e.status IN ('approved', 'enrolled')
              AND e.branch_id = %s
              AND e.year_id = %s
            ORDER BY e.student_name ASC
        ''', (activity['section_id'], activity['branch_id'], year_id))
        students = cur.fetchall()
        
        # Get all submissions for this activity
        cur.execute('''
            SELECT sub.*, g.grade_id, g.raw_score, g.percentage, g.remarks,
                   ext.new_due_date AS individual_extension
            FROM activity_submissions sub
            LEFT JOIN activity_grades g ON sub.submission_id = g.submission_id
            LEFT JOIN individual_extensions ext ON ext.enrollment_id = sub.enrollment_id AND ext.item_id = %s AND ext.item_type = 'activity'
            WHERE sub.activity_id = %s
            ORDER BY sub.submitted_at ASC
        ''', (activity_id, activity_id))
        submissions_raw = {}
        for row in cur.fetchall():
            # Parse attachments JSON
            if row.get("attachments"):
                if isinstance(row["attachments"], str):
                    try:
                        row["attachments"] = json.loads(row["attachments"])
                    except:
                        row["attachments"] = []
            else:
                # Fallback for old submissions
                if row.get("file_path"):
                    row["attachments"] = [{
                        "path": row["file_path"],
                        "name": row.get("original_filename") or "Attachment",
                        "type": row["file_path"].rsplit('.', 1)[-1].lower() if '.' in row["file_path"] else ''
                    }]
                else:
                    row["attachments"] = []
            submissions_raw[row['enrollment_id']] = row
        
        # Also need students who haven't submitted but might have extensions
        cur.execute('''
            SELECT enrollment_id, new_due_date 
            FROM individual_extensions 
            WHERE item_id = %s AND item_type = 'activity'
        ''', (activity_id,))
        extensions_only = {row['enrollment_id']: row['new_due_date'] for row in cur.fetchall()}
        
        submissions_data = []
        for s in students:
            sub = submissions_raw.get(s['enrollment_id'])
            item = {
                'student_name': s['student_name'],
                'student_user_id': s['student_user_id'],
                'enrollment_id': s['enrollment_id'],
                'individual_extension': extensions_only.get(s['enrollment_id'])
            }
            if sub:
                item.update(sub)
                item['feedback'] = sub['remarks'] # maps correctly
            submissions_data.append(item)
            
        stats = {
            'total': len(students),
            'submitted': sum(1 for s in submissions_data if 'submission_id' in s and s['submission_id']),
            'graded': sum(1 for s in submissions_data if 'grade_id' in s and s['grade_id']),
            'not_submitted': len(students) - sum(1 for s in submissions_data if 'submission_id' in s and s['submission_id'])
        }
    finally:
        cur.close()
        db.close()
        
    ph_tz = pytz.timezone("Asia/Manila")
    ph_now = datetime.now(ph_tz)
    min_date = ph_now.strftime("%Y-%m-%d") + "T00:00"
    return render_template("teacher_activity_submissions.html", activity=activity, submissions=submissions_data, stats=stats, min_date=min_date)


@teacher_bp.route("/teacher/activities/submissions/<int:submission_id>/mark-viewed", methods=["POST"])
def mark_submission_viewed(submission_id):
    """
    Mark a submission as viewed by the teacher.
    """
    user_id = session.get("user_id")
    if not user_id or session.get("role") != "teacher":
        return {"error": "Unauthorized"}, 401
    
    db = get_db_connection()
    cur = db.cursor()
    try:
        cur.execute("""
            UPDATE activity_submissions 
            SET is_viewed = TRUE 
            WHERE submission_id = %s
        """, (submission_id,))
        db.commit()
        return {"ok": True}
    except Exception as e:
        print(f"Error marking viewed: {e}")
        return {"error": str(e)}, 500
    finally:
        cur.close()
        db.close()


@teacher_bp.route("/teacher/activities/submissions/<int:submission_id>/grade", methods=["POST"])
def grade_submission(submission_id):
    if not _require_teacher(): return redirect("/")
    user_id = session.get("user_id")
    raw_score = request.form.get("raw_score")
    remarks = request.form.get("remarks", "")
    
    if not raw_score:
        flash("Score is required.", "error")
        return redirect(request.referrer)
        
    raw_score = float(raw_score)
    
    db = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        # Check permissions and get context
        cur.execute('''
            SELECT sub.activity_id, sub.student_id, a.max_score, a.teacher_id
            FROM activity_submissions sub
            JOIN activities a ON sub.activity_id = a.activity_id
            WHERE sub.submission_id = %s
        ''', (submission_id,))
        sub = cur.fetchone()
        
        if not sub or sub['teacher_id'] != user_id:
            flash("Unauthorized or submission not found.", "error")
            return redirect(request.referrer)
            
        if raw_score > sub['max_score']:
            flash(f"Score cannot exceed maximum score ({sub['max_score']}).", "error")
            return redirect(request.referrer)
            
        percentage = (raw_score / sub['max_score']) * 100 if sub['max_score'] > 0 else 0
        
        # Proceed with upserting grade
        cur.execute("SELECT grade_id FROM activity_grades WHERE submission_id = %s", (submission_id,))
        grade = cur.fetchone()
        
        if grade:
            cur.execute('''
                UPDATE activity_grades SET 
                    raw_score = %s, percentage = %s, remarks = %s, updated_at = NOW()
                WHERE grade_id = %s
            ''', (raw_score, percentage, remarks, grade['grade_id']))
        else:
            cur.execute('''
                INSERT INTO activity_grades (submission_id, activity_id, student_id, raw_score, max_score, percentage, remarks)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (submission_id, sub['activity_id'], sub['student_id'], raw_score, sub['max_score'], percentage, remarks))
            
        # Update submission status
        cur.execute('''
            UPDATE activity_submissions SET status = 'Graded', graded_at = NOW(), graded_by = %s 
            WHERE submission_id = %s
        ''', (user_id, submission_id))
        
        db.commit()

        # Send Notification to student
        cur.execute("SELECT title FROM activities WHERE activity_id = %s", (sub['activity_id'],))
        act_title = (cur.fetchone() or {}).get('title', 'Activity')
        
        cur.execute("""
            INSERT INTO student_notifications (student_id, title, message, link)
            VALUES (%s, %s, %s, %s)
        """, (sub['student_id'], "Activity Graded", f"Your submission for '{act_title}' has been graded.", f"/student/activities/{sub['activity_id']}"))
        
        db.commit()

        flash("Grade saved successfully.", "success")
        
    finally:
        cur.close()
        db.close()
        
    return redirect(request.referrer)


@teacher_bp.route("/teacher/activities/submissions/<int:submission_id>/allow_resubmit", methods=["POST"])
def allow_resubmission(submission_id):
    if not _require_teacher(): return redirect("/")
    
    db = get_db_connection()
    cur = db.cursor()
    try:
        # Verify ownership inside? It's fine for simple access.
        cur.execute("UPDATE activity_submissions SET allow_resubmit = TRUE WHERE submission_id = %s", (submission_id,))
        db.commit()
        flash("Resubmission explicitly allowed for this student.", "success")
    finally:
        cur.close()
        db.close()
        
    return redirect(request.referrer)

# ══════════════════════════════════════════
# EXAM ROUTES — TEACHER
# ══════════════════════════════════════════

@teacher_bp.route("/teacher/exams/<int:exam_id>/settings", methods=["GET", "POST"])
def teacher_exam_edit_settings(exam_id):
    if not _require_teacher():
        return redirect("/")

    user_id = session.get("user_id")
    branch_id = session.get("branch_id")

    db = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        year_id = _get_active_school_year(cur, branch_id)
        if not year_id:
            flash("No active school year.", "error")
            return redirect(url_for("teacher.teacher_dashboard"))

        # Verify ownership
        cur.execute("""
            SELECT e.*, s.section_name, g.name AS grade_level_name, sub.name AS subject_name
            FROM exams e
            JOIN sections s ON e.section_id = s.section_id
            JOIN grade_levels g ON s.grade_level_id = g.id
            JOIN subjects sub ON e.subject_id = sub.subject_id
            WHERE e.exam_id = %s AND e.teacher_id = %s AND s.year_id = %s
        """, (exam_id, user_id, year_id))
        exam = cur.fetchone()
        if not exam:
            flash("Exam/Quiz not found or unauthorized.", "error")
            return redirect(url_for("teacher.teacher_dashboard"))

        if request.method == "POST":
            title = (request.form.get("title") or "").strip()
            duration_mins = int(request.form.get("duration_mins", 60))
            scheduled_start = request.form.get("scheduled_start") or None
            max_attempts = int(request.form.get("max_attempts", 1))
            passing_score = int(request.form.get("passing_score", 60))
            randomize = request.form.get("randomize") == "1"
            instructions = (request.form.get("instructions") or "").strip() or None
            grading_period = request.form.get("grading_period")

            # Smart Auto-detect Grading Period
            try:
                if scheduled_start:
                    dt_obj = datetime.strptime(scheduled_start.split('T')[0], '%Y-%m-%d').date()
                    detected_period = _get_grading_period_by_date(cur, branch_id, year_id, dt_obj)
                    if detected_period:
                        grading_period = detected_period
            except:
                pass

            if not grading_period:
                flash("The updated Scheduled Start date does not fall within any configured Grading Period.", "error")
                return redirect(url_for("teacher.teacher_exam_edit_settings", exam_id=exam_id))

            class_mode = request.form.get("class_mode", "Virtual")

            if not title:
                flash("Title is required.", "error")
                return redirect(url_for("teacher.teacher_exam_edit_settings", exam_id=exam_id))

            cur.execute("""
                UPDATE exams SET
                    title = %s, duration_mins = %s, scheduled_start = %s,
                    max_attempts = %s, passing_score = %s, randomize = %s,
                    instructions = %s, grading_period = %s, class_mode = %s
                WHERE exam_id = %s
            """, (title, duration_mins, scheduled_start, max_attempts, passing_score,
                  randomize, instructions, grading_period, class_mode, exam_id))
            db.commit()

            flash("Settings updated successfully.", "success")
            return redirect(url_for("teacher.teacher_class_view", subject_id=exam["subject_id"], active_tab="quizzes" if exam["exam_type"] == "quiz" else "exams"))

        ph_tz = pytz.timezone("Asia/Manila")
        ph_now = datetime.now(ph_tz)
        min_date = ph_now.strftime("%Y-%m-%d") + "T00:00"

        return render_template("teacher_exam_edit_settings.html", exam=exam, min_date=min_date)

    except Exception as e:
        db.rollback()
        flash(f"Could not update settings: {str(e)}", "error")
        return redirect(url_for("teacher.teacher_dashboard"))
    finally:
        cur.close()
        db.close()

@teacher_bp.route("/teacher/exams")
def teacher_exams():
    if not _require_teacher():
        return redirect("/")

    user_id   = session.get("user_id")
    branch_id = session.get("branch_id")

    db  = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        year_id = _get_active_school_year(cur, branch_id)
        if not year_id:
            flash("No active school year.", "error")
            return redirect(url_for("teacher.teacher_dashboard"))
        cur.execute("""
            SELECT
                e.exam_id, e.title, e.exam_type, e.duration_mins,
                e.scheduled_start, e.status, e.created_at, e.grading_period, e.is_visible, e.is_archived,
                s.section_name,
                g.name AS grade_level_name,
                sub.name AS subject_name,
                (SELECT COUNT(*) FROM exam_questions q WHERE q.exam_id = e.exam_id) AS question_count,
                (SELECT COUNT(*) FROM exam_results r WHERE r.exam_id = e.exam_id) AS attempt_count
            FROM exams e
            JOIN sections s      ON e.section_id  = s.section_id
            JOIN grade_levels g  ON s.grade_level_id = g.id
            JOIN subjects sub    ON e.subject_id  = sub.subject_id
            WHERE e.teacher_id = %s AND e.branch_id = %s AND s.year_id = %s AND e.exam_type != 'quiz'
            ORDER BY e.created_at DESC
        """, (user_id, branch_id, year_id))
        exams = cur.fetchall() or []
        return render_template("teacher_exams.html", exams=exams)
    finally:
        cur.close()
        db.close()


@teacher_bp.route("/teacher/exams/create", methods=["GET", "POST"])
def teacher_exam_create():
    if not _require_teacher():
        return redirect("/")

    user_id   = session.get("user_id")
    branch_id = session.get("branch_id")

    db  = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    if request.method == "POST":
        title           = (request.form.get("title") or "").strip()
        subject_id      = request.form.get("subject_id")
        section_ids     = request.form.getlist("section_ids")
        exam_type_raw   = (request.form.get("exam_type") or "exam").strip()
        exam_type       = exam_type_raw if exam_type_raw in ('exam', 'monthly_exam') else 'exam'
        duration_mins   = int(request.form.get("duration_mins", 60))
        scheduled_start = request.form.get("scheduled_start") or None
        max_attempts    = int(request.form.get("max_attempts", 1))
        passing_score   = int(request.form.get("passing_score", 60))
        randomize       = request.form.get("randomize") == "1"
        class_mode      = request.form.get("class_mode", "Virtual")
        instructions    = (request.form.get("instructions") or "").strip() or None
        grading_period  = request.form.get("grading_period")

        # Smart Auto-detect Grading Period
        try:
            year_id = _get_active_school_year(cur, branch_id)
            if scheduled_start:
                dt_obj = datetime.strptime(scheduled_start.split('T')[0], '%Y-%m-%d').date()
                detected_period = _get_grading_period_by_date(cur, branch_id, year_id, dt_obj)
                if detected_period:
                    grading_period = detected_period
        except:
            pass
        grading_period = _normalize_period_name(grading_period)

        if not grading_period:
            flash("Could not determine the Grading Period. Please set a valid Scheduled Start date or ensure you are in a specific grading period view.", "error")
            return redirect(url_for("teacher.teacher_exam_create", subject_id=subject_id))
        if grading_period not in GRADING_PERIODS:
            flash("Invalid grading period selected.", "error")
            return redirect(url_for("teacher.teacher_exam_create", subject_id=subject_id))
        unlocked_periods = _get_unlocked_grading_periods(cur, branch_id, year_id)
        if grading_period not in unlocked_periods:
            flash(f"{grading_period} Grading is not open yet based on the Academic Calendar.", "error")
            return redirect(url_for("teacher.teacher_exam_create", subject_id=subject_id, period=grading_period))

        if not title or not subject_id or not section_ids:
            flash("Title, subject, and at least one section are required.", "error")
            return redirect(url_for("teacher.teacher_exam_create", subject_id=subject_id))
        
        import uuid
        batch_id = str(uuid.uuid4())[:8]

        try:
            year_id = _get_active_school_year(cur, branch_id)
            if not year_id:
                flash("No active school year.", "error")
                return redirect(url_for("teacher.teacher_dashboard"))
            primary_exam_id = None
            for section_id in section_ids:
                cur.execute("""
                    INSERT INTO exams (
                        branch_id, section_id, subject_id, teacher_id,
                        title, exam_type, duration_mins,
                        scheduled_start,
                        max_attempts, passing_score,
                        randomize,
                        instructions, status, grading_period, is_visible, batch_id, year_id, class_mode
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'draft',%s,FALSE,%s,%s,%s)
                    RETURNING exam_id
                """, (
                    branch_id, section_id, subject_id, user_id,
                    title, exam_type, duration_mins,
                    scheduled_start,
                    max_attempts, passing_score,
                    randomize,
                    instructions, grading_period, batch_id, year_id, class_mode
                ))
                exam_id = cur.fetchone()["exam_id"]
                if primary_exam_id is None:
                    primary_exam_id = exam_id
            
            db.commit()
            flash("Exam(s) created! Now add your questions.", "success")
            return redirect(url_for("teacher.teacher_exam_questions", exam_id=primary_exam_id))
        except Exception as e:
            db.rollback()
            flash(f"Could not create exam: {str(e)}", "error")
            return redirect(url_for("teacher.teacher_exam_create", subject_id=subject_id))
        finally:
            cur.close()
            db.close()

    # GET
    try:
        year_id = _get_active_school_year(cur, branch_id)
        if not year_id:
            flash("No active school year.", "error")
            return redirect(url_for("teacher.teacher_dashboard"))
        cur.execute("""
            SELECT DISTINCT s.section_id, s.section_name, g.name AS grade_level_name
            FROM section_teachers st
            JOIN sections s     ON st.section_id = s.section_id
            JOIN grade_levels g ON s.grade_level_id = g.id
            WHERE st.teacher_id = %s AND s.branch_id = %s AND s.year_id = %s
            ORDER BY g.name, s.section_name
        """, (user_id, branch_id, year_id))
        sections = cur.fetchall() or []

        cur.execute("""
            SELECT st.section_id, sub.subject_id, sub.name AS subject_name,
                   s.section_name, g.name AS grade_level_name
            FROM section_teachers st
            JOIN subjects sub   ON st.subject_id = sub.subject_id
            JOIN sections s     ON st.section_id = s.section_id
            JOIN grade_levels g ON s.grade_level_id = g.id
            WHERE st.teacher_id = %s AND s.branch_id = %s AND s.year_id = %s
            ORDER BY sub.name, s.section_name
        """, (user_id, branch_id, year_id))
        assignments = cur.fetchall() or []

        ph_tz = pytz.timezone("Asia/Manila")
        ph_now = datetime.now(ph_tz)
        min_date = ph_now.strftime("%Y-%m-%d") + "T00:00"
        subject_id = request.args.get("subject_id")
        selected_period = _normalize_period_name(request.args.get("period"))
        unlocked_periods = _get_unlocked_grading_periods(cur, branch_id, year_id)
        return render_template("teacher_exam_create.html",
                               sections=sections,
                               assignments=assignments,
                               min_date=min_date,
                               subject_id=subject_id,
                               selected_period=selected_period,
                               unlocked_periods=unlocked_periods)
    finally:
        cur.close()
        db.close()

@teacher_bp.route("/teacher/exams/<int:exam_id>/questions", methods=["GET", "POST"])
def teacher_exam_questions(exam_id):
    if not _require_teacher():
        return redirect("/")

    user_id   = session.get("user_id")
    branch_id = session.get("branch_id")

    db  = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    year_id = _get_active_school_year(cur, branch_id)

    if request.method == "POST":
        question_type = request.form.get("question_type", "mcq")
        points = int(request.form.get("points", 1))

        if question_type == "matching":
            match_prompts = request.form.getlist("match_prompt[]")
            match_answers = request.form.getlist("match_answer[]")

            pairs = []
            for p, a in zip(match_prompts, match_answers):
                p_clean = p.strip()
                a_clean = a.strip()
                if p_clean and a_clean:
                    pairs.append((p_clean, a_clean))

            if not pairs:
                flash("At least one valid matching pair is required.", "error")
                return redirect(url_for("teacher.teacher_exam_questions", exam_id=exam_id))

            all_answers = list(set([a for _, a in pairs]))
            choices = json.dumps({"options": all_answers})

            try:
                cur.execute("SELECT batch_id FROM exams e JOIN sections s ON e.section_id=s.section_id "
        "WHERE e.exam_id=%s AND e.teacher_id=%s AND e.branch_id=%s AND s.year_id=%s",
                            (exam_id, user_id, branch_id, year_id))
                exam_row = cur.fetchone()
                if not exam_row:
                    flash("Exam not found or unauthorized.", "error")
                    return redirect(url_for("teacher.teacher_exams"))
                
                batch_id = exam_row.get("batch_id")
                target_exams = [exam_id]
                if batch_id:
                    cur.execute("SELECT exam_id FROM exams WHERE batch_id=%s AND teacher_id=%s", (batch_id, user_id))
                    target_exams = [r["exam_id"] for r in cur.fetchall()]

                for t_id in target_exams:
                    cur.execute("SELECT COALESCE(MAX(order_num),0) AS max_o FROM exam_questions WHERE exam_id=%s", (t_id,))
                    max_order_num = cur.fetchone()["max_o"]
                    for i, (prompt, answer) in enumerate(pairs):
                        cur.execute("""
                            INSERT INTO exam_questions
                                (exam_id, question_text, question_type, choices, correct_answer, points, order_num)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """, (t_id, prompt, 'matching', choices, answer, points, max_order_num + 1 + i))
                
                # Sync all matching options for this exam to ensure the dropdown is complete
                _sync_matching_options_for_exam(cur, exam_id, user_id, branch_id, year_id)
                
                db.commit()
                sync_msg = " (synced across batch)" if len(target_exams) > 1 else ""
                flash(f"Added {len(pairs)} matching pairs!{sync_msg}", "success")
            except Exception as e:
                db.rollback()
                flash(f"Could not add matching questions: {str(e)}", "error")
            finally:
                cur.close()
                db.close()
            return redirect(url_for("teacher.teacher_exam_questions", exam_id=exam_id))

        else:
            question_text = (request.form.get("question_text") or "").strip()
            correct_answer = (request.form.get("correct_answer") or "").strip()

            choices = None
            if question_type == "mcq":
                a = (request.form.get("choice_a") or "").strip()
                b = (request.form.get("choice_b") or "").strip()
                c = (request.form.get("choice_c") or "").strip()
                d = (request.form.get("choice_d") or "").strip()
                if not all([a, b, c, d]):
                    flash("All 4 choices are required for MCQ.", "error")
                    return redirect(url_for("teacher.teacher_exam_questions", exam_id=exam_id))
                choices = json.dumps({"A": a, "B": b, "C": c, "D": d})

            if not question_text or not correct_answer:
                flash("Question text and correct answer are required.", "error")
                return redirect(url_for("teacher.teacher_exam_questions", exam_id=exam_id))

            try:
                cur.execute("""
                    INSERT INTO exam_questions
                        (exam_id, question_text, question_type, choices, correct_answer, points, order_num)
                    VALUES (%s, %s, %s, %s, %s, %s,
                        (SELECT COALESCE(MAX(order_num),0)+1 FROM exam_questions WHERE exam_id=%s))
                """, (exam_id, question_text, question_type,
                      choices, correct_answer, points, exam_id))
                if question_type == 'matching':
                    _sync_matching_options_for_exam(cur, exam_id, user_id, branch_id, year_id)
                db.commit()
                flash("Question added!", "success")
            except Exception as e:
                db.rollback()
                flash(f"Could not add question: {str(e)}", "error")
            finally:
                cur.close()
                db.close()

            return redirect(url_for("teacher.teacher_exam_questions", exam_id=exam_id))

    # GET
    try:
        cur.execute("""
            SELECT e.*, s.section_name, sub.name AS subject_name
            FROM exams e
            JOIN sections s ON e.section_id = s.section_id
            JOIN subjects sub ON e.subject_id = sub.subject_id
            WHERE e.exam_id = %s AND e.teacher_id = %s AND s.year_id = %s
        """, (exam_id, user_id, year_id))
        exam = cur.fetchone()
        if not exam:
            flash("Exam not found.", "error")
            return redirect(url_for("teacher.teacher_exams"))

        cur.execute("""
            SELECT * FROM exam_questions
            WHERE exam_id = %s ORDER BY order_num
        """, (exam_id,))
        questions = cur.fetchall() or []

        # Parse choices JSON
        for q in questions:
            if q["choices"]:
                q["choices"] = json.loads(q["choices"]) if isinstance(q["choices"], str) else q["choices"]

        return render_template("teacher_exam_questions.html",
                               exam=exam, questions=questions)
    finally:
        cur.close()
        db.close()


@teacher_bp.route("/teacher/exams/<int:exam_id>/questions/bulk-add", methods=["POST"])
def teacher_exam_questions_bulk_add(exam_id):
    if not _require_teacher():
        return redirect("/")

    import json
    import psycopg2.extras
    from db import get_db_connection

    user_id   = session.get("user_id")
    branch_id = session.get("branch_id")

    # Arrays from the inline builder
    q_type  = request.form.getlist("q_type[]")
    q_text  = request.form.getlist("q_text[]")
    q_pts   = request.form.getlist("q_points[]")

    # MCQ arrays
    mcq_a = request.form.getlist("mcq_a[]")
    mcq_b = request.form.getlist("mcq_b[]")
    mcq_c = request.form.getlist("mcq_c[]")
    mcq_d = request.form.getlist("mcq_d[]")
    mcq_correct = request.form.getlist("mcq_correct[]")

    # TF arrays
    tf_correct = request.form.getlist("tf_correct[]")

    # Matching arrays (prompt→answer)
    match_answer = request.form.getlist("match_answer[]")

    # Build shared dropdown options for ALL matching prompts in this bulk-add
    match_options = [a.strip() for a in match_answer if (a or "").strip()]
    seen = set()
    match_options_unique = []
    for a in match_options:
        if a not in seen:
            match_options_unique.append(a)
            seen.add(a)

    match_choices_json = json.dumps({"options": match_options_unique})

    if not q_type or not q_text:
        flash("Nothing to save.", "error")
        return redirect(url_for("teacher.teacher_exam_questions", exam_id=exam_id))

    db  = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        year_id = _get_active_school_year(cur, branch_id)
        if not year_id:
            flash("No active school year.", "error")
            return redirect(url_for("teacher.teacher_dashboard"))

        # ownership + draft check
        cur.execute("""
            SELECT e.exam_id
            FROM exams e
            JOIN sections s ON e.section_id = s.section_id
            WHERE e.exam_id=%s
              AND e.teacher_id=%s
              AND e.branch_id=%s
              AND s.year_id=%s
              AND e.status='draft'
        """, (exam_id, user_id, branch_id, year_id))
        if not cur.fetchone():
            flash("Exam not found / unauthorized / not editable.", "error")
            return redirect(url_for("teacher.teacher_exams"))

        cur.execute("SELECT COALESCE(MAX(order_num),0) AS max_o FROM exam_questions WHERE exam_id=%s", (exam_id,))
        order_num = cur.fetchone()["max_o"] or 0

        # indices for per-type arrays
        i_mcq = 0
        i_tf = 0
        i_match = 0

        inserted = 0

        for i in range(len(q_type)):
            t = (q_type[i] or "").strip().lower()
            text = (q_text[i] or "").strip()
            pts = int(q_pts[i] or 1)

            if not text:
                continue

            choices = None
            correct = ""

            if t == "mcq":
                a = (mcq_a[i_mcq] or "").strip()
                b = (mcq_b[i_mcq] or "").strip()
                c = (mcq_c[i_mcq] or "").strip()
                d = (mcq_d[i_mcq] or "").strip()
                corr = (mcq_correct[i_mcq] or "A").strip().upper()
                i_mcq += 1

                if not all([a, b, c, d]) or corr not in ("A", "B", "C", "D"):
                    continue

                choices = json.dumps({"A": a, "B": b, "C": c, "D": d})
                correct = corr

            elif t == "truefalse":
                corr = (tf_correct[i_tf] or "True").strip()
                i_tf += 1
                if corr not in ("True", "False"):
                    corr = "True"
                correct = corr

            elif t == "matching":
                ans = (match_answer[i_match] or "").strip()
                i_match += 1
                if not ans:
                    continue

    # Use the shared options list so each prompt shows all answers
                choices = match_choices_json
                correct = ans

            else:
                continue

            order_num += 1
            cur.execute("""
                INSERT INTO exam_questions
                    (exam_id, question_text, question_type, choices, correct_answer, points, order_num)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, (exam_id, text, t, choices, correct, pts, order_num))
            inserted += 1

        # Final sync for matching options in case new matching questions were added
        _sync_matching_options_for_exam(cur, exam_id, user_id, branch_id, year_id)

        db.commit()
        flash(f"Saved {inserted} question(s).", "success")

    except Exception as e:
        db.rollback()
        flash(f"Could not save questions: {str(e)}", "error")
    finally:
        cur.close()
        db.close()

    return redirect(url_for("teacher.teacher_exam_questions", exam_id=exam_id))


@teacher_bp.route("/teacher/exams/<int:exam_id>/publish", methods=["POST"])
def teacher_exam_publish(exam_id):
    if not _require_teacher():
        return redirect("/")

    user_id   = session.get("user_id")
    branch_id = session.get("branch_id")

    db  = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        year_id = _get_active_school_year(cur, branch_id)
        if not year_id:
            flash("No active school year.", "error")
            return redirect(url_for("teacher.teacher_dashboard"))
        
        cur.execute("SELECT COUNT(*) AS cnt FROM exam_questions WHERE exam_id=%s", (exam_id,))
        if cur.fetchone()["cnt"] == 0:
            flash("Cannot publish — add at least 1 question first.", "error")
            return redirect(url_for("teacher.teacher_exam_questions", exam_id=exam_id))

        cur.execute("""
            UPDATE exams SET status='published'
            FROM sections s        
            WHERE exams.exam_id=%s 
                    AND exams.teacher_id=%s 
                    AND exams.branch_id=%s
                    AND exams.section_id = s.section_id
                    AND s.year_id = %s
            RETURNING exams.title, exams.section_id, exams.subject_id, exams.exam_type
        """, (exam_id, user_id, branch_id, year_id))
        exam_info = cur.fetchone()
        
        if exam_info:
            notif_label = "Quiz" if exam_info['exam_type'] == 'quiz' else "Exam"
            # Notifications are now deferred to the toggle-visibility action
            pass

        db.commit()
        flash(f"{notif_label} finalized! Use the eye icon to make it visible to students.", "success")
    except Exception as e:
        db.rollback()
        flash(f"Could not publish: {str(e)}", "error")
    finally:
        cur.close()
        db.close()

    return redirect(url_for("teacher.teacher_exam_questions", exam_id=exam_id))


@teacher_bp.route("/teacher/exams/<int:exam_id>/close", methods=["POST"])
def teacher_exam_close(exam_id):
    if not _require_teacher():
        return redirect("/")

    user_id   = session.get("user_id")
    branch_id = session.get("branch_id")

    db  = get_db_connection()
    cur = db.cursor()
    try:
        # Active year enforcement
        year_id = _get_active_school_year(cur, branch_id)
        if not year_id:
            flash("No active school year.", "error")
            return redirect(url_for("teacher.teacher_dashboard"))

        cur.execute("""
            UPDATE exams SET status='closed'
            FROM sections s
            WHERE exams.exam_id = %s
              AND exams.teacher_id = %s
              AND exams.branch_id = %s
              AND exams.section_id = s.section_id
              AND s.year_id = %s
        """, (exam_id, user_id, branch_id, year_id))
        db.commit()
        flash("Exam closed.", "success")
    except Exception as e:
        db.rollback()
        flash(f"Could not close exam: {str(e)}", "error")
    finally:
        cur.close()
        db.close()

    return redirect(url_for("teacher.teacher_exams"))


@teacher_bp.route("/teacher/exams/<int:exam_id>/toggle-visibility", methods=["POST"])
def toggle_exam_visibility(exam_id):
    if not _require_teacher():
        return redirect("/")

    user_id = session.get("user_id")
    db = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        year_id = _get_active_school_year(cur, session.get("branch_id"))
        if not year_id:
            flash("No active school year.", "error")
            return redirect(url_for("teacher.teacher_dashboard"))
        active_tab = request.form.get("active_tab")
        # Check ownership
        cur.execute("""
            SELECT exams.exam_id, exams.is_visible, exams.exam_type, exams.subject_id,
                   exams.status, exams.title, exams.section_id, exams.batch_id
            FROM exams
            JOIN sections s ON exams.section_id = s.section_id
            WHERE exams.exam_id = %s
            AND exams.teacher_id = %s
            AND s.year_id = %s
        """, (exam_id, user_id, year_id))
        exam = cur.fetchone()
        if not exam:
            flash("Exam/Quiz not found or unauthorized.", "error")
            return redirect(request.referrer or url_for("teacher.teacher_exams"))

        new_status = not exam["is_visible"]

        # Toggle all linked copies if quiz/exam was created for multiple sections.
        if exam.get("batch_id"):
            cur.execute("""
                SELECT exams.exam_id, exams.exam_type, exams.subject_id, exams.status, exams.title, exams.section_id
                FROM exams
                JOIN sections s ON exams.section_id = s.section_id
                WHERE exams.batch_id = %s
                  AND exams.teacher_id = %s
                  AND s.year_id = %s
            """, (exam["batch_id"], user_id, year_id))
            target_exams = cur.fetchall() or []
        else:
            target_exams = [exam]

        if new_status:
            for target in target_exams:
                if target["status"] == "draft":
                    cur.execute("SELECT COUNT(*) AS cnt FROM exam_questions WHERE exam_id=%s", (target["exam_id"],))
                    if cur.fetchone()["cnt"] == 0:
                        flash("Cannot make visible — please add at least 1 question to publish this quiz/exam first.", "error")
                        return redirect(request.referrer or url_for("teacher.teacher_exams"))

            target_ids = [t["exam_id"] for t in target_exams]
            cur.execute("""
                UPDATE exams
                SET is_visible = TRUE,
                    status = CASE WHEN status = 'draft' THEN 'published' ELSE status END
                WHERE exam_id = ANY(%s)
            """, (target_ids,))
        else:
            target_ids = [t["exam_id"] for t in target_exams]
            cur.execute("UPDATE exams SET is_visible = FALSE WHERE exam_id = ANY(%s)", (target_ids,))

        # Send notifications when becoming visible.
        if new_status:
            notif_label = "Quiz" if exam['exam_type'] == 'quiz' else "Exam"
            for target in target_exams:
                cur.execute("""
                    SELECT DISTINCT u.user_id
                    FROM enrollments e 
                    JOIN users u ON u.user_id = e.user_id
                    WHERE e.section_id = %s AND e.status IN ('approved', 'enrolled')
                    UNION
                    SELECT DISTINCT u.user_id
                    FROM enrollments e
                    JOIN student_accounts sa ON sa.enrollment_id = e.enrollment_id
                    JOIN users u ON u.username = sa.username
                    WHERE e.section_id = %s AND e.status IN ('approved', 'enrolled')
                """, (target['section_id'], target['section_id']))
                students = cur.fetchall()
                for s in students:
                    notif_link = f"/student/subject/{target['subject_id']}" if target['exam_type'] == 'quiz' else "/student/exams"
                    cur.execute("""
                        INSERT INTO student_notifications (student_id, title, message, link)
                        VALUES (%s, %s, %s, %s)
                    """, (s['user_id'], f"New {notif_label}: {target['title']}", f"A new {notif_label.lower()} is now available: {target['title']}", notif_link))

        db.commit()

        label = "Quiz" if exam["exam_type"] == "quiz" else "Exam"
        msg = f"{label} is now {'visible' if new_status else 'hidden'} for students."
        flash(msg, "success")
        return redirect(url_for("teacher.teacher_class_view", subject_id=exam['subject_id'], active_tab=active_tab))
    except Exception as e:
        db.rollback()
        flash(f"Error toggling visibility: {str(e)}", "error")
        return redirect(request.referrer or url_for("teacher.teacher_exams"))
    finally:
        cur.close()
        db.close()



# ══════════════════════════════════════════
# QUIZ ROUTES — TEACHER (separate from Exams)
# ══════════════════════════════════════════

@teacher_bp.route("/teacher/quizzes")
def teacher_quizzes():
    if not _require_teacher():
        return redirect("/")

    user_id   = session.get("user_id")
    branch_id = session.get("branch_id")

    db  = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        year_id = _get_active_school_year(cur, branch_id)
        if not year_id:
            flash("No active school year.", "error")
            return redirect(url_for("teacher.teacher_dashboard"))
        cur.execute("""
            SELECT
                e.exam_id, e.title, e.exam_type, e.duration_mins,
                e.scheduled_start, e.status, e.created_at, e.grading_period, e.is_visible, e.is_archived,
                s.section_name,
                g.name AS grade_level_name,
                sub.name AS subject_name,
                (SELECT COUNT(*) FROM exam_questions q WHERE q.exam_id = e.exam_id) AS question_count,
                (SELECT COUNT(*) FROM exam_results r WHERE r.exam_id = e.exam_id) AS attempt_count
            FROM exams e
            JOIN sections s      ON e.section_id  = s.section_id
            JOIN grade_levels g  ON s.grade_level_id = g.id
            JOIN subjects sub    ON e.subject_id  = sub.subject_id
            WHERE e.teacher_id = %s AND e.branch_id = %s AND e.exam_type = 'quiz' AND s.year_id = %s
            ORDER BY e.created_at DESC
        """, (user_id, branch_id, year_id))
        quizzes = cur.fetchall() or []
        return render_template("teacher_quizzes.html", quizzes=quizzes)
    finally:
        cur.close()
        db.close()

@teacher_bp.route("/teacher/quizzes/create", methods=["GET", "POST"])
def teacher_quiz_create():
    if not _require_teacher():
        return redirect("/")

    user_id = session.get("user_id")
    branch_id = session.get("branch_id")

    db = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        # Get year_id ONCE for both GET and POST
        year_id = _get_active_school_year(cur, branch_id)
        if not year_id:
            flash("No active school year.", "error")
            return redirect(url_for("teacher.teacher_dashboard"))

        if request.method == "POST":
            title = (request.form.get("title") or "").strip()
            subject_id = request.form.get("subject_id")
            section_ids = request.form.getlist("section_ids")
            duration_mins = int(request.form.get("duration_mins", 30))
            scheduled_start = request.form.get("scheduled_start") or None
            max_attempts = int(request.form.get("max_attempts", 1))
            passing_score = int(request.form.get("passing_score", 60))
            randomize = request.form.get("randomize") == "1"
            class_mode = request.form.get("class_mode", "Virtual")
            instructions = (request.form.get("instructions") or "").strip() or None
            grading_period = request.form.get("grading_period")

            # Smart Auto-detect Grading Period
            try:
                if scheduled_start:
                    dt_obj = datetime.strptime(scheduled_start.split('T')[0], '%Y-%m-%d').date()
                    detected_period = _get_grading_period_by_date(cur, branch_id, year_id, dt_obj)
                    if detected_period:
                        grading_period = detected_period
            except:
                pass
            grading_period = _normalize_period_name(grading_period)

            if not grading_period:
                flash("Could not determine the Grading Period. Please set a valid Scheduled Start date or ensure you are in a specific grading period view.", "error")
                return redirect(url_for("teacher.teacher_quiz_create", subject_id=subject_id))
            if grading_period not in GRADING_PERIODS:
                flash("Invalid grading period selected.", "error")
                return redirect(url_for("teacher.teacher_quiz_create", subject_id=subject_id))
            unlocked_periods = _get_unlocked_grading_periods(cur, branch_id, year_id)
            if grading_period not in unlocked_periods:
                flash(f"{grading_period} Grading is not open yet based on the Academic Calendar.", "error")
                return redirect(url_for("teacher.teacher_quiz_create", subject_id=subject_id, period=grading_period))

            if not title or not subject_id or not section_ids:
                flash("Title, Subject and at least one Section are required.", "error")
                return redirect(url_for("teacher.teacher_quiz_create", subject_id=subject_id))

            import uuid
            batch_id = str(uuid.uuid4())[:8]

            primary_exam_id = None
            for section_id in section_ids:
                # Validate section is in active year for this branch
                cur.execute("""
                    SELECT 1 FROM sections
                    WHERE section_id=%s AND branch_id=%s AND year_id=%s
                """, (section_id, branch_id, year_id))
                if not cur.fetchone():
                    flash("Invalid section for this school year.", "error")
                    return redirect(url_for("teacher.teacher_quiz_create", subject_id=subject_id))

                cur.execute("""
                    INSERT INTO exams (
                        branch_id, section_id, subject_id, teacher_id,
                        title, exam_type, duration_mins,
                        scheduled_start,
                        max_attempts, passing_score,
                        randomize,
                        instructions, status, grading_period, is_visible, batch_id, year_id, class_mode
                    )
                    VALUES (%s,%s,%s,%s,%s,'quiz',%s,%s,%s,%s,%s,%s,'draft',%s,FALSE,%s,%s,%s)
                    RETURNING exam_id
                """, (
                    branch_id, section_id, subject_id, user_id,
                    title, duration_mins,
                    scheduled_start,
                    max_attempts, passing_score,
                    randomize,
                    instructions, grading_period, batch_id, year_id, class_mode
                ))
                exam_id = cur.fetchone()["exam_id"]
                if primary_exam_id is None:
                    primary_exam_id = exam_id

            db.commit()
            flash("Quiz created! Now add your questions.", "success")
            return redirect(url_for("teacher.teacher_exam_questions", exam_id=primary_exam_id))

        # GET: load teacher's active-year section+subject assignments
        cur.execute("""
            SELECT s.section_id, s.section_name, g.name AS grade_level_name,
                   sub.subject_id, sub.name AS subject_name
            FROM section_teachers st
            JOIN sections s    ON st.section_id = s.section_id
            JOIN grade_levels g ON s.grade_level_id = g.id
            JOIN subjects sub  ON st.subject_id = sub.subject_id
            WHERE st.teacher_id = %s AND s.branch_id = %s AND s.year_id = %s
            ORDER BY g.display_order, s.section_name, sub.name
        """, (user_id, branch_id, year_id))
        teacher_assignments = cur.fetchall() or []
        ph_tz = pytz.timezone("Asia/Manila")
        ph_now = datetime.now(ph_tz)
        min_date = ph_now.strftime("%Y-%m-%d") + "T00:00"
        subject_id = request.args.get("subject_id")
        selected_period = _normalize_period_name(request.args.get("period"))
        unlocked_periods = _get_unlocked_grading_periods(cur, branch_id, year_id)
        return render_template("teacher_quiz_create.html",
                               teacher_assignments=teacher_assignments,
                               min_date=min_date,
                               subject_id=subject_id,
                               selected_period=selected_period,
                               unlocked_periods=unlocked_periods)
    except Exception as e:
        db.rollback()
        flash(f"Could not create quiz: {str(e)}", "error")
        return redirect(url_for("teacher.teacher_quiz_create"))
    finally:
        cur.close()
        db.close()



@teacher_bp.route("/teacher/exams/<int:exam_id>/results")
def teacher_exam_results(exam_id):
    if not _require_teacher():
        return redirect("/")

    user_id   = session.get("user_id")
    branch_id = session.get("branch_id")

    db  = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        year_id = _get_active_school_year(cur, branch_id)
        if not year_id:
            flash("No active school year.", "error")
            return redirect(url_for("teacher.teacher_dashboard"))
        
        cur.execute("""
            SELECT e.*, s.section_name, sub.name AS subject_name
            FROM exams e
            JOIN sections s   ON e.section_id  = s.section_id
            JOIN subjects sub ON e.subject_id  = sub.subject_id
            WHERE e.exam_id = %s AND e.teacher_id = %s AND s.year_id = %s
        """, (exam_id, user_id, year_id))
        exam = cur.fetchone()
        if not exam:
            flash("Exam not found.", "error")
            return redirect(url_for("teacher.teacher_exams"))

        cur.execute("""
            SELECT
                e.enrollment_id, e.student_name, e.grade_level,
                r.result_id, r.score, r.total_points, COALESCE(r.status, 'Not Taken') AS status,
                r.submitted_at, r.started_at, r.tab_switches,
                (SELECT COUNT(*) FROM exam_tab_switches ts WHERE ts.result_id = r.result_id) AS switch_count,
                ext.new_due_date AS individual_extension,
                COALESCE(esp.is_allowed, %s) AS is_allowed
            FROM enrollments e
            LEFT JOIN exam_results r ON e.enrollment_id = r.enrollment_id AND r.exam_id = %s
            LEFT JOIN exam_student_permissions esp ON esp.enrollment_id = e.enrollment_id AND esp.exam_id = %s
            LEFT JOIN individual_extensions ext ON ext.enrollment_id = e.enrollment_id 
                 AND ext.item_id = %s AND ext.item_type = %s
            WHERE e.section_id = %s AND e.status IN ('approved', 'enrolled')
            AND e.branch_id = %s
            ORDER BY e.student_name ASC
        """, (exam['class_mode'] != 'Face-to-Face', exam_id, exam_id, exam_id, exam.get('exam_type', 'exam'), exam['section_id'], branch_id))
        results = cur.fetchall() or []

        # ✅ ADD THIS — convert UTC → PH time for display
        ph_tz = pytz.timezone("Asia/Manila")
        results_display = []
        for r in results:
            r = dict(r)
            if r.get("submitted_at"):
                r["submitted_at"] = r["submitted_at"].replace(tzinfo=timezone.utc).astimezone(ph_tz)
            if r.get("started_at"):
                r["started_at"] = r["started_at"].replace(tzinfo=timezone.utc).astimezone(ph_tz)
            if r.get("individual_extension"):
                # individual_extension is a naive datetime (local wall-clock time)
                # Just use it as-is for display.
                r["individual_extension"] = r["individual_extension"].replace(tzinfo=None)
            results_display.append(r)
        # ✅ END ADD

        ph_tz = pytz.timezone("Asia/Manila")
        ph_now = datetime.now(ph_tz)
        min_date = ph_now.strftime("%Y-%m-%d") + "T00:00"
        return render_template("teacher_exam_results.html",
                               exam=exam, results=results_display, min_date=min_date)  # ← use results_display
    finally:
        cur.close()
        db.close()

@teacher_bp.route("/teacher/exams/<int:exam_id>/questions/<int:question_id>/delete", methods=["POST"])
def teacher_exam_question_delete(exam_id, question_id):
    if not _require_teacher():
        return redirect("/")

    user_id = session.get("user_id")
    branch_id = session.get("branch_id")
    db  = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        year_id = _get_active_school_year(cur, branch_id)
        if not year_id:
            flash("No active school year.", "error")
            return redirect(url_for("teacher.teacher_dashboard"))
        # Fetch question details and batch info
        cur.execute("""
            SELECT q.question_text, q.question_type, e.batch_id 
        FROM exam_questions q
        JOIN exams e ON q.exam_id = e.exam_id
        JOIN sections s ON e.section_id = s.section_id
        WHERE q.question_id=%s AND q.exam_id=%s AND e.teacher_id=%s AND e.status='draft'
          AND e.branch_id = %s AND s.year_id = %s
        """, (question_id, exam_id, user_id, branch_id, year_id))
        target_q = cur.fetchone()
        
        if not target_q:
            flash("Cannot delete — question not found or exam is already published.", "error")
            return redirect(url_for("teacher.teacher_exam_questions", exam_id=exam_id))

        batch_id = target_q.get("batch_id")
        q_text = target_q["question_text"]
        q_type = target_q["question_type"]

        # Delete from current + others in batch if text and type match
        if batch_id:
            cur.execute("""
                DELETE FROM exam_questions 
            WHERE question_text = %s AND question_type = %s 
            AND exam_id IN (
                SELECT e.exam_id FROM exams e
                JOIN sections s ON e.section_id = s.section_id
                WHERE e.batch_id = %s AND e.teacher_id = %s AND e.branch_id = %s AND s.year_id = %s
                )
            """, (q_text, q_type, batch_id, user_id, branch_id, year_id))
            sync_msg = " (synced across batch)"
        else:
            cur.execute("DELETE FROM exam_questions WHERE question_id=%s AND exam_id=%s", (question_id, exam_id))
            sync_msg = ""

        # If it was a matching question, sync options to remove the answer from the pool if necessary
        if q_type == 'matching':
            _sync_matching_options_for_exam(cur, exam_id, user_id, branch_id, year_id)

        db.commit()
        flash(f"Question deleted!{sync_msg}", "success")
    except Exception as e:
        db.rollback()
        flash(f"Could not delete: {str(e)}", "error")
    finally:
        cur.close()
        db.close()

    return redirect(url_for("teacher.teacher_exam_questions", exam_id=exam_id))


import re
import json
import os

@teacher_bp.route("/teacher/exams/<int:exam_id>/import-questions", methods=["POST"])
def teacher_exam_import_questions(exam_id):
    if not _require_teacher():
        return redirect("/")

    user_id   = session.get("user_id")
    branch_id = session.get("branch_id")

    if 'question_file' not in request.files:
        flash("No file selected.", "error")
        return redirect(url_for("teacher.teacher_exam_questions", exam_id=exam_id))

    file = request.files['question_file']
    if not file or file.filename == '':
        flash("No file selected.", "error")
        return redirect(url_for("teacher.teacher_exam_questions", exam_id=exam_id))

    db  = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        year_id = _get_active_school_year(cur, branch_id)
        if not year_id:
            flash("No active school year.", "error")
            return redirect(url_for("teacher.teacher_dashboard"))
        # Verify exam belongs to teacher and is still draft
        cur.execute("""
            SELECT e.batch_id
            FROM exams e
            JOIN sections s ON e.section_id = s.section_id
            WHERE e.exam_id=%s AND e.teacher_id=%s AND e.branch_id=%s AND e.status='draft' AND s.year_id = %s
        """, (exam_id, user_id, branch_id, year_id))
        exam_row = cur.fetchone()
        if not exam_row:
            flash("Exam not found or already published.", "error")
            return redirect(url_for("teacher.teacher_exams"))
        
        batch_id = exam_row.get("batch_id")
        target_exams = [exam_id]
        if batch_id:
            cur.execute("""
        SELECT e.exam_id
        FROM exams e
        JOIN sections s ON e.section_id = s.section_id
        WHERE e.batch_id=%s AND e.teacher_id=%s AND s.year_id=%s AND e.branch_id=%s
            """, (batch_id, user_id, year_id, branch_id))
            target_exams = [r["exam_id"] for r in cur.fetchall()]
        else:
            target_exams = [exam_id]

        # 10MB limit
        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)
        if size > 10 * 1024 * 1024:
            flash("File too large. Maximum 10MB allowed.", "error")
            return redirect(url_for("teacher.teacher_exam_questions", exam_id=exam_id))

        ext = os.path.splitext(file.filename)[1].lower()

        # Parse file into list of question dicts
        if ext == '.docx':
            questions = parse_docx(file)
        elif ext == '.pdf':
            questions = parse_pdf(file)
        elif ext in ('.xls', '.xlsx'):
            import pandas as pd
            df = pd.read_excel(file).fillna('')
            df.columns = [c.lower().strip() for c in df.columns]
            questions = df.to_dict(orient='records')
        elif ext in ('.png', '.jpg', '.jpeg'):
            if not HAS_OCR:
                flash("OCR support is not installed on this server. Please install pytesseract and Pillow.", "error")
                return redirect(url_for("teacher.teacher_exam_questions", exam_id=exam_id))
            try:
                questions = parse_image(file)
            except Exception as e:
                flash(f"OCR Error: {str(e)}", "error")
                return redirect(url_for("teacher.teacher_exam_questions", exam_id=exam_id))
        else:
            flash("Invalid file format. Only Documents (DOCX, PDF, Excel) and Images (PNG, JPG) are allowed.", "error")
            return redirect(url_for("teacher.teacher_exam_questions", exam_id=exam_id))

        inserted = 0
        skipped  = 0
        errors   = []

        # Gather pool of all correct answers for matching in this batch
        matching_answers_pool = []
        for q in questions:
            q_type = str(q.get('question_type', '') or '').strip().lower()
            ans = str(q.get('correct_answer', '') or '').strip()
            # If it's matching or auto-detects as matching (not mcq/tf)
            is_mcq = any([str(q.get('choice_a','')), str(q.get('choice_b','')), str(q.get('choice_c','')), str(q.get('choice_d',''))])
            is_tf = ans.lower() in ('true', 'false')
            
            if ans and (q_type in ('matching', '') and not is_mcq and not is_tf):
                matching_answers_pool.append(ans)
            elif q_type == 'matching' and ans:
                matching_answers_pool.append(ans)
        # Deduplicate, preserve order
        unique_matching_options = []
        seen = set()
        for ans in matching_answers_pool:
            if ans and ans not in seen:
                unique_matching_options.append(ans)
                seen.add(ans)

        for i, q in enumerate(questions, start=1):
            question_text  = str(q.get('question_text', '') or '').strip()
            correct_answer = str(q.get('correct_answer', '') or '').strip()
            question_type  = str(q.get('question_type', '') or '').strip().lower()
            points_raw = str(q.get('points', '')).strip()
            points_match = re.search(r'\d+', points_raw)
            points = int(points_match.group()) if points_match else 1

            if not question_text or not correct_answer:
                errors.append(f"Row {i}: Missing question text or correct answer — skipped.")
                skipped += 1
                continue

            # Auto-detect type if not specified
            choice_a = str(q.get('choice_a', '') or q.get('option_a', '') or '').strip()
            choice_b = str(q.get('choice_b', '') or q.get('option_b', '') or '').strip()
            choice_c = str(q.get('choice_c', '') or q.get('option_c', '') or '').strip()
            choice_d = str(q.get('choice_d', '') or q.get('option_d', '') or '').strip()

            if not question_type:
                # If we have any choices at all, it's likely an MCQ
                if any([choice_a, choice_b, choice_c, choice_d]):
                    question_type = 'mcq'
                    # Map text answer to letter if needed
                    ca_upper = correct_answer.upper()
                    if ca_upper in ('A', 'B', 'C', 'D'):
                        correct_answer = ca_upper
                    elif correct_answer == choice_a: correct_answer = 'A'
                    elif correct_answer == choice_b: correct_answer = 'B'
                    elif correct_answer == choice_c: correct_answer = 'C'
                    elif correct_answer == choice_d: correct_answer = 'D'
                elif correct_answer.lower() in ('true', 'false'):
                    question_type = 'truefalse'
                else:
                    question_type = 'matching'

            # Normalize type
            if question_type in ('multiple choice', 'multiple_choice', 'mcq'):
                question_type = 'mcq'
            elif question_type in ('true/false', 'truefalse', 'true_false', 'tf'):
                question_type = 'truefalse'

            # Build choices JSON for MCQ, Matching, or True/False
            choices = None
            if question_type == 'mcq':
                if not all([choice_a, choice_b, choice_c, choice_d]):
                    errors.append(f"Row {i}: MCQ missing some choices — skipped.")
                    skipped += 1
                    continue
                choices = json.dumps({"A": choice_a, "B": choice_b, "C": choice_c, "D": choice_d})
                correct_answer = correct_answer.upper()
                if correct_answer not in ('A', 'B', 'C', 'D'):
                    errors.append(f"Row {i}: MCQ correct answer must be A/B/C/D — skipped.")
                    skipped += 1
                    continue

            elif question_type == 'matching':
                # Use the global pool of answers for this import batch so all answers show in dropdown
                choices = json.dumps({"options": unique_matching_options})

            elif question_type == 'truefalse':
                if correct_answer.lower() == 'true':
                    correct_answer = 'True'
                elif correct_answer.lower() == 'false':
                    correct_answer = 'False'
                else:
                    errors.append(f"Row {i}: True/False answer must be True or False — skipped.")
                    skipped += 1
                    continue

            for t_id in target_exams:
                # Check duplicate in this specific exam
                cur.execute("""
                    SELECT 1 FROM exam_questions
                    WHERE exam_id=%s AND question_text=%s
                """, (t_id, question_text))
                if cur.fetchone():
                    continue

                cur.execute("""
                    INSERT INTO exam_questions
                        (exam_id, question_text, question_type, choices, correct_answer, points, order_num)
                    VALUES (%s, %s, %s, %s, %s, %s,
                        (SELECT COALESCE(MAX(order_num), 0) + 1 FROM exam_questions WHERE exam_id=%s))
                """, (t_id, question_text, question_type,
                      choices, correct_answer, points, t_id))
            
            inserted += 1

        # Final sync for matching options after import
        _sync_matching_options_for_exam(cur, exam_id, user_id, branch_id, year_id)

        db.commit()

        if errors:
            for e in errors:
                flash(e, "warning")

        flash(f"Import done! {inserted} question(s) added, {skipped} skipped.", "success")

    except Exception as e:
        db.rollback()
        flash(f"Import failed: {str(e)}", "error")
    finally:
        cur.close()
        db.close()

    return redirect(url_for("teacher.teacher_exam_questions", exam_id=exam_id))


# ══════════════════════════════════════════
# PRIORITY 2 — EDIT QUESTION
# ══════════════════════════════════════════

@teacher_bp.route("/teacher/exams/<int:exam_id>/questions/<int:question_id>/edit",
                  methods=["GET", "POST"])
def teacher_exam_question_edit(exam_id, question_id):
    if not _require_teacher():
        return redirect("/")

    user_id   = session.get("user_id")
    branch_id = session.get("branch_id")

    db  = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        year_id = _get_active_school_year(cur, branch_id)
        if not year_id:
            flash("No active school year.", "error")
            return redirect(url_for("teacher.teacher_dashboard"))
        # Verify exam ownership + still draft
        cur.execute("""
            SELECT 1 FROM exams e
            JOIN sections s ON e.section_id=s.section_id
            WHERE e.exam_id=%s AND e.teacher_id=%s AND e.branch_id=%s AND e.status='draft' AND s.year_id=%s
        """, (exam_id, user_id, branch_id, year_id))
        if not cur.fetchone():
            flash("Exam not found or already published.", "error")
            return redirect(url_for("teacher.teacher_exams"))

        cur.execute("SELECT * FROM exam_questions WHERE question_id=%s AND exam_id=%s",
                    (question_id, exam_id))
        question = cur.fetchone()
        if not question:
            flash("Question not found.", "error")
            return redirect(url_for("teacher.teacher_exam_questions", exam_id=exam_id))

        # Parse choices JSON for template
        if question["choices"]:
            question = dict(question)
            question["choices"] = json.loads(question["choices"]) \
                if isinstance(question["choices"], str) else question["choices"]

        if request.method == "POST":
            question_text  = (request.form.get("question_text") or "").strip()
            question_type  = request.form.get("question_type", "mcq")
            correct_answer = (request.form.get("correct_answer") or "").strip()
            points         = int(request.form.get("points", 1))

            choices = None
            if question_type == "mcq":
                a = (request.form.get("choice_a") or "").strip()
                b = (request.form.get("choice_b") or "").strip()
                c = (request.form.get("choice_c") or "").strip()
                d = (request.form.get("choice_d") or "").strip()
                if not all([a, b, c, d]):
                    flash("All 4 choices are required for MCQ.", "error")
                    return redirect(request.url)
                choices = json.dumps({"A": a, "B": b, "C": c, "D": d})
            elif question_type == "matching":
                # Preserve existing choices JSON for now; we'll sync the pool later
                choices = json.dumps(question["choices"]) if question["choices"] else None

            if not question_text or not correct_answer:
                flash("Question text and correct answer are required.", "error")
                return redirect(request.url)

            # Fetch batch info and ORIGINAL question text/type for syncing
            cur.execute("""
                SELECT q.question_text, q.question_type, e.batch_id
                FROM exam_questions q
                JOIN exams e ON q.exam_id = e.exam_id
                WHERE q.question_id = %s
            """, (question_id,))
            orig = cur.fetchone()
            batch_id = orig.get("batch_id") if orig else None
            orig_text = orig["question_text"] if orig else None
            orig_type = orig["question_type"] if orig else None

            if batch_id and orig_text:
                cur.execute("""
                    UPDATE exam_questions
                    SET question_text=%s, question_type=%s, choices=%s,
                        correct_answer=%s, points=%s
                    WHERE question_text=%s AND question_type=%s
                    AND exam_id IN (
                    SELECT e.exam_id FROM exams e
                    JOIN sections s ON e.section_id = s.section_id
                     WHERE e.batch_id=%s AND e.teacher_id=%s AND e.branch_id=%s AND s.year_id=%s
                    )        
                """, (question_text, question_type, choices,
                      correct_answer, points, orig_text, orig_type, batch_id, user_id, branch_id, year_id))
                sync_msg = " (synced across batch)"
            else:
                cur.execute("""
                    UPDATE exam_questions
                    SET question_text=%s, question_type=%s, choices=%s,
                        correct_answer=%s, points=%s
                    WHERE question_id=%s AND exam_id=%s
                """, (question_text, question_type, choices,
                      correct_answer, points, question_id, exam_id))
                sync_msg = ""

            # If it's a matching question, sync the options pool for the whole exam
            if question_type == 'matching':
                _sync_matching_options_for_exam(cur, exam_id, user_id, branch_id, year_id)

            db.commit()
            flash(f"Question updated!{sync_msg}", "success")
            return redirect(url_for("teacher.teacher_exam_questions", exam_id=exam_id))

        # GET — fetch exam info for breadcrumb
        cur.execute("""
            SELECT e.*, s.section_name, sub.name AS subject_name
            FROM exams e
            JOIN sections s ON e.section_id = s.section_id
            JOIN subjects sub ON e.subject_id = sub.subject_id
            WHERE e.exam_id = %s AND s.year_id = %s
        """, (exam_id, year_id))
        exam = cur.fetchone()

        return render_template("teacher_exam_question_edit.html",
                               exam=exam, question=question)
    finally:
        cur.close()
        db.close()


# ══════════════════════════════════════════
# PRIORITY 3 — RESET EXAM ATTEMPT
# ══════════════════════════════════════════

@teacher_bp.route("/teacher/exams/<int:exam_id>/reset/<int:enrollment_id>", methods=["POST"])
def teacher_exam_reset(exam_id, enrollment_id):
    if not _require_teacher():
        return redirect("/")

    user_id   = session.get("user_id")
    branch_id = session.get("branch_id")

    db  = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        year_id = _get_active_school_year(cur, branch_id)
        if not year_id:
            flash("No active school year.", "error")
            return redirect(url_for("teacher.teacher_dashboard"))
        # Verify exam belongs to this teacher and get exam_type
        cur.execute("""
    SELECT e.exam_type
    FROM exams e
    JOIN sections s ON e.section_id = s.section_id
    WHERE e.exam_id=%s AND e.teacher_id=%s AND e.branch_id=%s AND s.year_id=%s
""", (exam_id, user_id, branch_id, year_id))
        row = cur.fetchone()
        if not row:
            flash("Item not found or unauthorized.", "error")
            return redirect(url_for("teacher.teacher_exams"))

        etype = (row.get("exam_type") or "exam").lower()
        item_name = "Quiz" if etype == "quiz" else "Exam"

        # Delete answers first (FK constraint)
        cur.execute("""
            DELETE FROM exam_answers
            WHERE result_id IN (
                SELECT result_id FROM exam_results
                WHERE exam_id=%s AND enrollment_id=%s
            )
        """, (exam_id, enrollment_id))

        # Delete tab switches
        cur.execute("""
            DELETE FROM exam_tab_switches
            WHERE result_id IN (
                SELECT result_id FROM exam_results
                WHERE exam_id=%s AND enrollment_id=%s
            )
        """, (exam_id, enrollment_id))

        # Delete the result row entirely so student gets a fresh start
        cur.execute("""
            DELETE FROM exam_results
            WHERE exam_id=%s AND enrollment_id=%s
        """, (exam_id, enrollment_id))

        db.commit()

        if cur.rowcount > 0:
            flash(f"{item_name} attempt reset. Student can now retake the {item_name.lower()}.", "success")
        else:
            flash(f"No {item_name.lower()} attempt found for this student.", "warning")

    except Exception as e:
        db.rollback()
        flash(f"Error resetting exam: {str(e)}", "error")
    finally:
        cur.close()
        db.close()

    return redirect(url_for("teacher.teacher_exam_results", exam_id=exam_id))


# ══════════════════════════════════════════════════════════════
# GRADING PERIOD SYSTEM — TEACHER
# ══════════════════════════════════════════════════════════════

GRADING_PERIODS = ["1st", "2nd", "3rd", "4th"]

# DepEd Order No. 8, s. 2015 — Fixed weights per subject category
# Quiz -> Written Works (WW)
# Activity + Participation -> Performance Tasks (PT)
# Exam -> Quarterly Assessment (QA)
DEPED_WEIGHTS = {
    'language':     {'ww': 0.30, 'pt': 0.50, 'qa': 0.20},  # Filipino, English, AP, EsP
    'science_math': {'ww': 0.40, 'pt': 0.40, 'qa': 0.20},  # Math, Science
    'skills':       {'ww': 0.20, 'pt': 0.60, 'qa': 0.20},  # EPP, TLE, MAPEH
}

TRANSMUTATION_RANGES = [
    (98.40, 99.99, 99),
    (96.80, 98.39, 98),
    (95.20, 96.79, 97),
    (93.60, 95.19, 96),
    (92.00, 93.59, 95),
    (90.40, 91.99, 94),
    (88.80, 90.39, 93),
    (87.20, 88.79, 92),
    (85.60, 87.19, 91),
    (84.00, 85.59, 90),
    (82.40, 83.99, 89),
    (80.80, 82.39, 88),
    (79.20, 80.79, 87),
    (77.60, 79.19, 86),
    (76.00, 77.59, 85),
    (74.40, 75.99, 84),
    (72.80, 74.39, 83),
    (71.20, 72.79, 82),
    (69.60, 71.19, 81),
    (68.00, 69.59, 80),
    (66.40, 67.99, 79),
    (64.80, 66.39, 78),
    (63.20, 64.79, 77),
    (61.60, 63.19, 76),
    (60.00, 61.59, 75),
    (56.00, 59.99, 74),
    (52.00, 55.99, 73),
    (48.00, 51.99, 72),
    (44.00, 47.99, 71),
    (40.00, 43.99, 70),
    (36.00, 39.99, 69),
    (32.00, 35.99, 68),
    (28.00, 31.99, 67),
    (24.00, 27.99, 66),
    (20.00, 23.99, 65),
    (16.00, 19.99, 64),
    (12.00, 15.99, 63),
    (8.00, 11.99, 62),
    (4.00, 7.99, 61),
    (0.00, 3.99, 60),
]

def _get_deped_transmuted_grade(initial_grade):
    """
    DepEd Order No. 8, s. 2015 — Transmutation Table (Initial 0-100 -> Final 60-100).
    Returns an integer transmuted grade.
    """
    try:
        x = round(float(initial_grade), 2)
    except (TypeError, ValueError):
        return None

    # Clamp to expected range.
    if x < 0:
        x = 0
    if x > 100:
        x = 100

    # Special case: exact 100.
    if x >= 100:
        return 100

    for min_g, max_g, transmuted in TRANSMUTATION_RANGES:
        if min_g <= x <= max_g:
            return transmuted

    # Fallback: should not happen due to 0-3.99 => 60 range.
    return 60

def _get_transmutation_band(initial_grade):
    """Human-readable transmutation bracket for display/debugging."""
    try:
        x = round(float(initial_grade), 2)
    except (TypeError, ValueError):
        return None
    if x >= 100:
        return "100.00-100.00 => 100"
    for min_g, max_g, transmuted in TRANSMUTATION_RANGES:
        if min_g <= x <= max_g:
            return f"{min_g:.2f}-{max_g:.2f} => {transmuted}"
    return "0.00-3.99 => 60"


def _get_teacher_assignments(cur, user_id, branch_id, year_id):
    cur.execute("""
        SELECT st.section_id, s.section_name, g.name AS grade_level_name,
               st.subject_id, sub.name AS subject_name, sub.deped_category
        FROM section_teachers st
        JOIN sections s      ON st.section_id = s.section_id
        JOIN grade_levels g  ON s.grade_level_id = g.id
        JOIN subjects sub    ON st.subject_id = sub.subject_id
        WHERE st.teacher_id = %s AND s.branch_id = %s AND s.year_id = %s
        ORDER BY g.display_order, s.section_name, sub.name
    """, (user_id, branch_id, year_id))
    return cur.fetchall() or []


# ── DepEd Grading Info (read-only — weights are auto-computed) ────────────────
@teacher_bp.route("/teacher/grading-weights")
def grading_weights():
    if not _require_teacher():
        return redirect("/")

    user_id   = session.get("user_id")
    branch_id = session.get("branch_id")

    db  = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        year_id = _get_active_school_year(cur, branch_id)
        if not year_id:
            flash("No active school year.", "error")
            return redirect(url_for("teacher.teacher_dashboard"))

        assignments = _get_teacher_assignments(cur, user_id, branch_id, year_id)

        # Build per-assignment auto weights (read-only, from DepEd category)
        assignments_with_weights = []
        for a in assignments:
            category = a.get('deped_category') or 'language'
            w = DEPED_WEIGHTS.get(category, DEPED_WEIGHTS['language'])
            assignments_with_weights.append({
                **dict(a),
                'ww_pct':  int(round(w['ww'] * 100)),
                'pt_pct':  int(round(w['pt'] * 100)),
                'qa_pct':  int(round(w['qa'] * 100)),
            })

    finally:
        cur.close()
        db.close()

    return render_template("teacher_grading_weights.html",
                           assignments=assignments_with_weights,
                           grading_periods=GRADING_PERIODS)




@teacher_bp.route("/teacher/grading-weights/set", methods=["POST"])
def grading_weights_set():
    # DEPRECATED — grading weights are now auto-computed from DepEd category
    if not _require_teacher():
        return redirect("/")
    flash("Grading weights are now automatically set based on DepEd K-12 subject category.", "info")
    return redirect(url_for("teacher.teacher_dashboard"))


def _compute_period_grades(cur, user_id, branch_id, section_id, subject_id, period, year_id):
    """Compute grades using DepEd K-12 auto-weighting.
    School policy (client customization):
      Written Works (WW)      = Quiz scores + Monthly Exam scores
      Performance Tasks (PT)  = Activities + Participation + Attendance (averaged)
      Quarterly Assessment (QA) = Periodical Exam scores only
    """

    # All students in the section
    cur.execute("""
        SELECT e.enrollment_id, e.student_name
        FROM enrollments e
        JOIN sections s ON e.section_id = s.section_id
        WHERE e.section_id = %s AND e.branch_id = %s AND s.year_id = %s
              AND e.status IN ('approved','enrolled')
        ORDER BY e.student_name ASC
    """, (section_id, branch_id, year_id))
    students = cur.fetchall() or []

    # Get subject's DepEd category for auto-weights
    cur.execute("SELECT deped_category FROM subjects WHERE subject_id = %s", (subject_id,))
    subj_row = cur.fetchone()
    category = (subj_row['deped_category'] if subj_row and subj_row.get('deped_category') else 'language')
    w = DEPED_WEIGHTS.get(category, DEPED_WEIGHTS['language'])

    # Build a synthetic 'weights' dict for the template (read-only info)
    weights = {
        'quiz_pct':          round(w['ww'] * 100, 1),
        'activity_pct':      round(w['pt'] * 100, 1),
        'exam_pct':          round(w['qa'] * 100, 1),
        'participation_pct': 0,
        'attendance_pct':    0,
        'deped_category':    category,
    }

    enrollment_ids = [s['enrollment_id'] for s in students]
    quiz_scores = {}
    exam_scores = {}

    if enrollment_ids:
        # Written Works: Quiz + Monthly Exam scores combined
        cur.execute("""
            SELECT er.enrollment_id,
                   COALESCE(
                       (SUM(COALESCE(er.score, 0)) / NULLIF(SUM(COALESCE(er.total_points, 0)), 0)) * 100,
                       0
                   ) AS ps
            FROM exam_results er
            JOIN exams e ON er.exam_id = e.exam_id
            JOIN sections s ON e.section_id = s.section_id
            WHERE e.section_id = %s AND e.subject_id = %s
              AND e.exam_type IN ('quiz', 'monthly_exam') AND e.grading_period = %s
              AND s.year_id = %s
              AND er.enrollment_id = ANY(%s)
              AND er.status IN ('submitted', 'auto_submitted')
            GROUP BY er.enrollment_id
        """, (section_id, subject_id, period, year_id, enrollment_ids))
        for row in cur.fetchall():
            quiz_scores[row['enrollment_id']] = float(row['ps'] or 0)

        # Quarterly Assessment: Periodical Exam scores ONLY
        cur.execute("""
            SELECT er.enrollment_id,
                   COALESCE(
                       (SUM(COALESCE(er.score, 0)) / NULLIF(SUM(COALESCE(er.total_points, 0)), 0)) * 100,
                       0
                   ) AS ps
            FROM exam_results er
            JOIN exams e ON er.exam_id = e.exam_id
            JOIN sections s ON e.section_id = s.section_id
            WHERE e.section_id = %s AND e.subject_id = %s
              AND e.exam_type = 'exam' AND e.grading_period = %s
              AND s.year_id = %s
              AND er.enrollment_id = ANY(%s)
              AND er.status IN ('submitted', 'auto_submitted')
            GROUP BY er.enrollment_id
        """, (section_id, subject_id, period, year_id, enrollment_ids))
        for row in cur.fetchall():
            exam_scores[row['enrollment_id']] = float(row['ps'] or 0)

    # Performance Tasks: Activity scores
    activity_scores = {}
    cur.execute("""
        SELECT asub.enrollment_id,
               COALESCE(
                   (SUM(COALESCE(ag.raw_score, 0)) / NULLIF(SUM(COALESCE(ag.max_score, 0)), 0)) * 100,
                   0
               ) AS ps
        FROM activity_grades ag
        JOIN activity_submissions asub ON ag.submission_id = asub.submission_id
        JOIN activities a ON ag.activity_id = a.activity_id
        JOIN sections s ON a.section_id = s.section_id
        WHERE a.section_id = %s AND a.subject_id = %s AND a.grading_period = %s AND s.year_id = %s
        GROUP BY asub.enrollment_id
    """, (section_id, subject_id, period, year_id))
    act_raw = cur.fetchall() or []
    for row in act_raw:
        activity_scores[row['enrollment_id']] = float(row['ps'] or 0)

    # Get Date Range for the Period to compute Attendance/Participation
    cur.execute("""
        SELECT start_date, end_date 
        FROM grading_period_ranges 
        WHERE branch_id = %s AND year_id = %s AND period_name = %s
    """, (branch_id, year_id, period))
    range_row = cur.fetchone()
    
    total_school_days = 0
    if range_row:
        total_school_days = _count_school_days(cur, branch_id, year_id, range_row["start_date"], range_row["end_date"])

    # Participation scores (from daily_participation)
    participation_scores = {}
    cur.execute("""
        SELECT enrollment_id, AVG(points) * 20 AS ps -- Scale 1-5 to 1-100
        FROM daily_participation
        WHERE subject_id = %s AND branch_id = %s AND year_id = %s
          AND participation_date BETWEEN %s AND %s
        GROUP BY enrollment_id
    """, (subject_id, branch_id, year_id, range_row["start_date"] if range_row else '1900-01-01', range_row["end_date"] if range_row else '1900-01-01'))
    for row in cur.fetchall():
        participation_scores[row['enrollment_id']] = float(row['ps'] or 0)

    # Attendance scores (from daily_attendance)
    attendance_scores = {}
    if total_school_days > 0:
        cur.execute("""
            SELECT enrollment_id, (SUM(points) / %s) * 100 AS ps
            FROM daily_attendance
            WHERE subject_id = %s AND branch_id = %s AND year_id = %s
              AND attendance_date BETWEEN %s AND %s
            GROUP BY enrollment_id
        """, (total_school_days, subject_id, branch_id, year_id, range_row["start_date"], range_row["end_date"]))
        for row in cur.fetchall():
            attendance_scores[row['enrollment_id']] = float(row['ps'] or 0)

    def _cap_0_100(value):
        return max(0.0, min(100.0, float(value or 0)))

    records = []
    for s in students:
        eid = s['enrollment_id']
        ww_score  = _cap_0_100(quiz_scores.get(eid, 0))          # Written Works (Quiz + Monthly Exam)
        qa_score  = _cap_0_100(exam_scores.get(eid, 0))          # Quarterly Assessment (Periodical Exam)
        act_score = _cap_0_100(activity_scores.get(eid, 0))
        par_score = _cap_0_100(participation_scores.get(eid, 0))
        att_score = _cap_0_100(attendance_scores.get(eid, 0))    # now part of PT

        # Performance Tasks = average of all available: Activity, Participation, Attendance
        has_activity = eid in activity_scores
        has_participation = eid in participation_scores
        has_attendance = eid in attendance_scores

        pt_components = []
        if has_activity: pt_components.append(act_score)
        if has_participation: pt_components.append(par_score)
        if has_attendance: pt_components.append(att_score)
        pt_score = _cap_0_100(sum(pt_components) / len(pt_components) if pt_components else 0)

        # DepEd auto-computation (weights unchanged)
        period_grade = round(
            ww_score  * w['ww'] +
            pt_score  * w['pt'] +
            qa_score  * w['qa'],
            2
        )

        transmuted_grade = _get_deped_transmuted_grade(period_grade)
        transmutation_band = _get_transmutation_band(period_grade)

        records.append({
            'enrollment_id':   eid,
            'student_name':    s['student_name'],
            'quiz':            round(ww_score, 2),    # WW (Quiz + Monthly Exam)
            'activity':        round(act_score, 2),
            'participation':   round(par_score, 2),
            'attendance':      round(att_score, 2),   # now part of PT
            'has_activity':    has_activity,
            'has_participation': has_participation,
            'has_attendance':  has_attendance,
            'pt_score':        round(pt_score, 2),    # Combined PT
            'exam':            round(qa_score, 2),    # QA (Periodical Exam)
            'period_grade':    period_grade,
            'transmuted_grade': transmuted_grade,
            'transmutation_band': transmutation_band,
            'deped_category':  category,
        })
    return students, weights, records

@teacher_bp.route("/teacher/class-record/<int:section_id>/<int:subject_id>")
def class_record(section_id, subject_id):
    if not _require_teacher():
        return redirect("/")

    user_id   = session.get("user_id")
    branch_id = session.get("branch_id")
    period    = request.args.get("period", "1st")
    if period not in GRADING_PERIODS:
        period = "1st"

    db  = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        year_id = _get_active_school_year(cur, branch_id)
        if not year_id:
            flash("No active school year.", "error")
            return redirect(url_for("teacher.teacher_dashboard"))

        # Owner check, for this year:
        cur.execute("""
            SELECT 1 FROM section_teachers st
            JOIN sections s ON st.section_id = s.section_id
            WHERE st.teacher_id=%s AND st.section_id=%s AND st.subject_id=%s AND s.year_id=%s
        """, (user_id, section_id, subject_id, year_id))
        if not cur.fetchone():
            flash("Unauthorized or assignment not found.", "error")
            return redirect(url_for("teacher.teacher_dashboard"))

        # Section/subject context (with year check)
        cur.execute("""
            SELECT s.section_name, g.name AS grade_level_name, sub.name AS subject_name
            FROM sections s
            JOIN grade_levels g ON s.grade_level_id = g.id
            JOIN subjects sub ON sub.subject_id = %s
            WHERE s.section_id = %s AND s.year_id = %s
        """, (subject_id, section_id, year_id))
        context = cur.fetchone()

        _, weights, records = _compute_period_grades(
            cur, user_id, branch_id, section_id, subject_id, period, year_id
        )

        return render_template("teacher_class_record.html",
            context=context,
            section_id=section_id,
            subject_id=subject_id,
            records=records,
            weights=weights,
            period=period,
            grading_periods=GRADING_PERIODS)
    finally:
        cur.close()
        db.close()

@teacher_bp.route("/teacher/class-record/<int:section_id>/<int:subject_id>/export")
def class_record_export(section_id, subject_id):
    if not _require_teacher():
        return redirect("/")

    user_id = session.get("user_id")
    branch_id = session.get("branch_id")
    period = request.args.get("period", "1st")
    if period not in GRADING_PERIODS:
        period = "1st"

    db = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        year_id = _get_active_school_year(cur, branch_id)
        if not year_id:
            flash("No active school year.", "error")
            return redirect(url_for("teacher.teacher_dashboard"))

        cur.execute("""
            SELECT 1 FROM section_teachers st
            JOIN sections s ON st.section_id = s.section_id
            WHERE st.teacher_id=%s AND st.section_id=%s AND st.subject_id=%s AND s.year_id=%s
        """, (user_id, section_id, subject_id, year_id))
        if not cur.fetchone():
            flash("Unauthorized or assignment not found.", "error")
            return redirect(url_for("teacher.teacher_dashboard"))

        cur.execute("""
            SELECT s.section_name, g.name AS grade_level_name, sub.name AS subject_name
            FROM sections s
            JOIN grade_levels g ON s.grade_level_id = g.id
            JOIN subjects sub ON sub.subject_id = %s
            WHERE s.section_id = %s AND s.year_id = %s
        """, (subject_id, section_id, year_id))
        context = cur.fetchone()
        if not context:
            flash("Class context not found.", "error")
            return redirect(url_for("teacher.teacher_dashboard"))

        _, weights, records = _compute_period_grades(
            cur, user_id, branch_id, section_id, subject_id, period, year_id
        )

        summary_rows = []
        detail_rows = []
        for idx, r in enumerate(records, start=1):
            remarks = "PASS" if (r.get("transmuted_grade") or 0) >= 75 else "FAIL"
            summary_rows.append({
                "No": idx,
                "Student Name": r.get("student_name"),
                "Written Works (WW)": r.get("quiz"),
                "Performance Tasks (PT)": r.get("pt_score"),
                "Quarterly Assessment (QA)": r.get("exam"),
                "Quarterly Grade (Transmuted)": r.get("transmuted_grade"),
                "Remarks": remarks,
            })
            detail_rows.append({
                "No": idx,
                "Student Name": r.get("student_name"),
                "WW Raw": r.get("quiz"),
                "PT Activity": r.get("activity"),
                "PT Participation": r.get("participation"),
                "PT Attendance": r.get("attendance"),
                "PT Combined": r.get("pt_score"),
                "QA Raw": r.get("exam"),
                "Initial Grade": r.get("period_grade"),
                "Transmuted Grade": r.get("transmuted_grade"),
                "WW Weight %": weights.get("quiz_pct"),
                "PT Weight %": weights.get("activity_pct"),
                "QA Weight %": weights.get("exam_pct"),
                "Subject": context.get("subject_name"),
                "Section": f"{context.get('grade_level_name')} - {context.get('section_name')}",
                "Period": f"{period} Grading",
            })

        filename_base = f"class_record_{context.get('subject_name','subject')}_{context.get('section_name','section')}_{period}grading".replace(" ", "_")

        output = io.BytesIO()
        try:
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                pd.DataFrame(summary_rows).to_excel(writer, sheet_name="Summary", index=False)
                pd.DataFrame(detail_rows).to_excel(writer, sheet_name="Per Student Breakdown", index=False)
            output.seek(0)
            return send_file(
                output,
                as_attachment=True,
                download_name=f"{filename_base}.xlsx",
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        except Exception:
            # Safe fallback if Excel writer dependency is unavailable.
            csv_output = io.StringIO()
            pd.DataFrame(summary_rows).to_csv(csv_output, index=False)
            csv_bytes = io.BytesIO(csv_output.getvalue().encode("utf-8"))
            csv_bytes.seek(0)
            return send_file(
                csv_bytes,
                as_attachment=True,
                download_name=f"{filename_base}.csv",
                mimetype="text/csv",
            )
    finally:
        cur.close()
        db.close()

@teacher_bp.route("/teacher/post-grades/<int:section_id>/<int:subject_id>/<string:period>", methods=["POST"])
def teacher_post_grades(section_id, subject_id, period):
    if not _require_teacher(): return redirect("/")
    user_id   = session.get("user_id")
    branch_id = session.get("branch_id")
    if period not in GRADING_PERIODS: return redirect(url_for("teacher.teacher_dashboard"))

    db  = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        year_id = _get_active_school_year(cur, branch_id)
        if not year_id:
            flash("No active school year.", "error")
            return redirect(url_for("teacher.teacher_dashboard"))
        
        cur.execute("""
            SELECT 1 FROM section_teachers st
            JOIN sections s ON st.section_id = s.section_id
            WHERE st.teacher_id=%s AND st.section_id=%s AND st.subject_id=%s AND s.year_id=%s
        """, (user_id, section_id, subject_id, year_id))
        if not cur.fetchone():
            flash("Unauthorized.", "error")
            return redirect(url_for("teacher.teacher_dashboard"))

        _, weights, records = _compute_period_grades(
            cur, user_id, branch_id, section_id, subject_id, period, year_id
        )
        if not weights:
            flash(f"Cannot post grades: Weights not set for {period} Grading.", "error")
            return redirect(url_for("teacher.class_record", section_id=section_id, subject_id=subject_id, period=period))

        for r in records:
            if r.get('transmuted_grade') is not None:
                cur.execute("""
                    INSERT INTO posted_grades
                        (enrollment_id, section_id, subject_id, grading_period, grade, posted_by, posted_at, year_id)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW(), %s)
                    ON CONFLICT (enrollment_id, subject_id, grading_period, year_id)
                    DO UPDATE SET grade = EXCLUDED.grade, posted_at = NOW(), posted_by = EXCLUDED.posted_by
                """, (r['enrollment_id'], section_id, subject_id, period, r['transmuted_grade'], user_id, year_id))
        
        db.commit()
        flash(f"Grades for {period} Grading have been posted to the Student Portal!", "success")
    except Exception as e:
        db.rollback()
        flash(f"Error posting grades: {str(e)}", "error")
    finally:
        cur.close()
        db.close()
    return redirect(url_for("teacher.class_record", section_id=section_id, subject_id=subject_id, period=period))

@teacher_bp.route("/teacher/participation/<int:section_id>/<int:subject_id>/<period>", methods=["GET", "POST"])
def participation_input(section_id, subject_id, period):
    if not _require_teacher():
        return redirect("/")
    user_id   = session.get("user_id")
    branch_id = session.get("branch_id")
    if period not in GRADING_PERIODS:
        flash("Invalid grading period.", "error")
        return redirect(url_for("teacher.grading_weights"))

    db  = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        year_id = _get_active_school_year(cur, branch_id)
        if not year_id:
            flash("No active school year.", "error")
            return redirect(url_for("teacher.teacher_dashboard"))

        # Verify ownership in current year
        cur.execute("""
            SELECT 1
            FROM section_teachers st
            JOIN sections s ON st.section_id = s.section_id
            WHERE st.teacher_id=%s AND st.section_id=%s AND st.subject_id=%s AND s.year_id=%s
        """, (user_id, section_id, subject_id, year_id))
        if not cur.fetchone():
            flash("Unauthorized.", "error")
            return redirect(url_for("teacher.teacher_dashboard"))

        # Context info for current year
        cur.execute("""
            SELECT s.section_name, sub.name AS subject_name
            FROM sections s
            JOIN subjects sub ON sub.subject_id = %s
            WHERE s.section_id=%s AND s.year_id=%s
        """, (subject_id, section_id, year_id))
        ctx = cur.fetchone()

        if request.method == "POST":
            scores = request.form.to_dict()
            for key, val in scores.items():
                if key.startswith("score_"):
                    try:
                        eid   = int(key.split("_", 1)[1])
                        score = max(0.0, min(100.0, float(val or 0)))
                        cur.execute("""
                            INSERT INTO participation_scores
                                (teacher_id, enrollment_id, section_id, subject_id, grading_period, score, updated_at)
                            VALUES (%s,%s,%s,%s,%s,%s,NOW())
                            ON CONFLICT (enrollment_id, subject_id, grading_period)
                            DO UPDATE SET score=EXCLUDED.score, updated_at=NOW()
                        """, (user_id, eid, section_id, subject_id, period, score))
                    except (ValueError, IndexError):
                        continue
            db.commit()
            flash("Participation scores saved!", "success")
            return redirect(url_for("teacher.class_record",
                                    section_id=section_id,
                                    subject_id=subject_id,
                                    period=period))

        # GET — load current year students + scores
        cur.execute("""
            SELECT e.enrollment_id, e.student_name,
                   COALESCE(ps.score, 0) AS score
            FROM enrollments e
            JOIN sections s ON e.section_id = s.section_id
            LEFT JOIN participation_scores ps
                ON ps.enrollment_id = e.enrollment_id
               AND ps.subject_id = %s AND ps.grading_period = %s
            WHERE e.section_id = %s AND e.branch_id = %s AND s.year_id = %s AND e.status IN ('approved','enrolled')
            ORDER BY e.student_name
        """, (subject_id, period, section_id, branch_id, year_id))
        students = cur.fetchall() or []

    finally:
        cur.close()
        db.close()

    return render_template("teacher_participation_input.html",
                           ctx=ctx, students=students,
                           section_id=section_id, subject_id=subject_id,
                           period=period)


# ── Attendance Scores ─────────────────────────────────────────────────────────
@teacher_bp.route("/teacher/attendance/<int:section_id>/<int:subject_id>/<period>",
                  methods=["GET", "POST"])
def attendance_input(section_id, subject_id, period):
    if not _require_teacher():
        return redirect("/")

    user_id   = session.get("user_id")
    branch_id = session.get("branch_id")

    if period not in GRADING_PERIODS:
        flash("Invalid grading period.", "error")
        return redirect(url_for("teacher.grading_weights"))

    db  = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        year_id = _get_active_school_year(cur, branch_id)
        if not year_id:
            flash("No active school year.", "error")
            return redirect(url_for("teacher.teacher_dashboard"))

        cur.execute("""
            SELECT 1
            FROM section_teachers st
            JOIN sections s ON st.section_id = s.section_id
            WHERE st.teacher_id=%s AND st.section_id=%s AND st.subject_id=%s AND s.year_id=%s
        """, (user_id, section_id, subject_id, year_id))
        if not cur.fetchone():
            flash("Unauthorized.", "error")
            return redirect(url_for("teacher.teacher_dashboard"))

        cur.execute("""
            SELECT s.section_name, sub.name AS subject_name
            FROM sections s
            JOIN subjects sub ON sub.subject_id = %s
            WHERE s.section_id=%s AND s.year_id=%s
        """, (subject_id, section_id, year_id))
        ctx = cur.fetchone()

        if request.method == "POST":
            scores = request.form.to_dict()
            for key, val in scores.items():
                if key.startswith("score_"):
                    try:
                        eid   = int(key.split("_", 1)[1])
                        score = max(0.0, min(100.0, float(val or 0)))
                        cur.execute("""
                            INSERT INTO attendance_scores
                                (teacher_id, enrollment_id, section_id, subject_id, grading_period, score, updated_at)
                            VALUES (%s,%s,%s,%s,%s,%s,NOW())
                            ON CONFLICT (enrollment_id, subject_id, grading_period)
                            DO UPDATE SET score=EXCLUDED.score, updated_at=NOW()
                        """, (user_id, eid, section_id, subject_id, period, score))
                    except (ValueError, IndexError):
                        continue
            db.commit()
            flash("Attendance scores saved!", "success")
            return redirect(url_for("teacher.class_record",
                                    section_id=section_id,
                                    subject_id=subject_id,
                                    period=period))

        cur.execute("""
            SELECT e.enrollment_id, e.student_name,
                   COALESCE(att.score, 0) AS score
            FROM enrollments e
            JOIN sections s ON e.section_id = s.section_id
            LEFT JOIN attendance_scores att
                ON att.enrollment_id = e.enrollment_id
               AND att.subject_id = %s AND att.grading_period = %s
            WHERE e.section_id = %s AND e.branch_id = %s AND s.year_id = %s AND e.status IN ('approved','enrolled')
            ORDER BY e.student_name
        """, (subject_id, period, section_id, branch_id, year_id))
        students = cur.fetchall() or []

    finally:
        cur.close()
        db.close()

    return render_template("teacher_attendance_input.html",
                           ctx=ctx, students=students,
                           section_id=section_id, subject_id=subject_id,
                           period=period)

# ── API for Teacher Sidebar Classlist ─────────────────────
@teacher_bp.route("/api/teacher/sections")
def api_teacher_sections():
    if not _require_teacher(): 
        return jsonify({"error": "Unauthorized"}), 403

    user_id = session.get("user_id")
    branch_id = session.get("branch_id")
    print("user_id", user_id, "branch_id", branch_id)  # For debug

    db = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        # Always fetch the latest active year for this branch, every request
        year_id = _get_active_school_year(cur, branch_id)
        print("Active year_id:", year_id)  # For debug

        if not year_id:
            return jsonify({"sections": [], "error": "No active school year."})

        cur.execute("""
            SELECT DISTINCT s.section_id, s.section_name, g.name AS grade_level_name, g.display_order
            FROM section_teachers st
            JOIN sections s ON st.section_id = s.section_id
            JOIN grade_levels g ON s.grade_level_id = g.id
            WHERE st.teacher_id = %s
              AND s.branch_id = %s
              AND s.year_id = %s
            ORDER BY g.display_order, s.section_name
        """, (user_id, branch_id, year_id))

        sections = cur.fetchall()
        return jsonify({"sections": sections})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cur.close()
        db.close()


@teacher_bp.route("/api/teacher/classlist/<int:section_id>")
def api_teacher_classlist(section_id):
    if not _require_teacher(): 
        return jsonify({"error": "Unauthorized"}), 403

    branch_id = session.get("branch_id")
    user_id = session.get("user_id")

    db = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        # Get active year ID for this branch
        year_id = _get_active_school_year(cur, branch_id)
        if not year_id:
            return jsonify({"students": []})

        # STRONG ownership check includes branch/year  
        cur.execute("""
            SELECT 1 
            FROM section_teachers st
            JOIN sections s ON st.section_id = s.section_id
            WHERE st.teacher_id = %s 
              AND st.section_id = %s
              AND s.branch_id = %s
              AND s.year_id = %s
        """, (user_id, section_id, branch_id, year_id))

        if not cur.fetchone():
            return jsonify({"error": "Unauthorized section access"}), 403

        cur.execute("""
            SELECT e.enrollment_id, e.student_name, u.user_id as student_user_id
            FROM enrollments e
            LEFT JOIN users u ON u.user_id = e.user_id
            WHERE e.section_id = %s 
              AND e.branch_id = %s 
              AND e.year_id = %s
              AND e.status IN ('approved', 'enrolled')
            ORDER BY e.student_name ASC
        """, (section_id, branch_id, year_id))

        students = cur.fetchall()
        return jsonify({"students": students})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cur.close()
        db.close()


@teacher_bp.route("/teacher/reschedule", methods=["POST"])
def teacher_reschedule():
    if not _require_teacher():
        return jsonify({"error": "Unauthorized"}), 403

    user_id = session.get("user_id")
    branch_id = session.get("branch_id")

    db = get_db_connection()
    cur = db.cursor()
    try:
        year_id = _get_active_school_year(cur, branch_id)
        if not year_id:
            return jsonify({"error": "No active school year."}), 400

        if request.is_json:
            data = request.get_json()
        else:
            data = request.form

        enrollment_id = data.get("enrollment_id")
        item_type     = data.get("item_type")  # 'activity', 'exam', 'quiz'
        item_id       = data.get("item_id")
        new_due_date  = data.get("new_due_date")

        if not all([enrollment_id, item_type, item_id, new_due_date]):
            return jsonify({"error": "Missing required fields"}), 400

        # 0. Validate date is not in the past
        try:
            ph_tz = pytz.timezone("Asia/Manila")
            now_pht = datetime.now(timezone.utc).astimezone(ph_tz).replace(tzinfo=None)
            dt_val = datetime.strptime(new_due_date, '%Y-%m-%dT%H:%M')
            if dt_val < now_pht:
                return jsonify({"error": "Cannot reschedule to a past date."}), 400
        except Exception:
            return jsonify({"error": "Invalid date format"}), 400

        # 1. Verify teacher ownership (filter by current year)
        if item_type == 'activity':
            cur.execute("""
                SELECT 1 FROM activities a
                JOIN sections s ON a.section_id = s.section_id
                WHERE a.activity_id = %s AND a.teacher_id = %s AND a.branch_id = %s AND s.year_id = %s
            """, (item_id, user_id, branch_id, year_id))
        elif item_type in ('exam', 'quiz'):
            cur.execute("""
                SELECT 1 FROM exams e
                JOIN sections s ON e.section_id = s.section_id
                WHERE e.exam_id = %s AND e.teacher_id = %s AND e.branch_id = %s AND s.year_id = %s
            """, (item_id, user_id, branch_id, year_id))
        else:
            return jsonify({"error": "Unknown item_type"}), 400

        if not cur.fetchone():
            return jsonify({"error": "Unauthorized item access or item not found."}), 403

        # 2. Verify student enrollment in this branch AND YEAR
        cur.execute("""
            SELECT user_id FROM enrollments e
            JOIN sections s ON e.section_id = s.section_id
            WHERE e.enrollment_id = %s AND e.branch_id = %s AND s.year_id = %s
        """, (enrollment_id, branch_id, year_id))

        student_row = cur.fetchone()
        if not student_row:
            return jsonify({"error": "Invalid student or branch/year mismatch."}), 403

        student_id = student_row[0]  # This can be None, which is fine

        # 3. Upsert individual_extensions, add year_id filter/column!
        cur.execute("""
            SELECT extension_id FROM individual_extensions 
            WHERE enrollment_id=%s AND item_type=%s AND item_id=%s AND year_id=%s
        """, (enrollment_id, item_type, item_id, year_id))
        
        if cur.fetchone():
            cur.execute("""
                UPDATE individual_extensions 
                SET new_due_date=%s, student_id=%s
                WHERE enrollment_id=%s AND item_type=%s AND item_id=%s AND year_id=%s
            """, (new_due_date, student_id, enrollment_id, item_type, item_id, year_id))
        else:
            cur.execute("""
                INSERT INTO individual_extensions (enrollment_id, student_id, item_type, item_id, new_due_date, year_id)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (enrollment_id, student_id, item_type, item_id, new_due_date, year_id))

        db.commit()
        return jsonify({"ok": True, "message": "Rescheduled successfully!"})
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        db.close()

@teacher_bp.route("/teacher/exams/<int:exam_id>/permissions", methods=["POST"])
def teacher_update_exam_permissions(exam_id):
    if not _require_teacher():
        return jsonify({"ok": False, "error": "Unauthorized"}), 403

    user_id = session.get("user_id")
    data = request.get_json() or {}
    action = data.get("action") # "toggle", "allow_all", "deselect_all"
    enrollment_id = data.get("enrollment_id")
    is_allowed = data.get("is_allowed")

    db = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        # Verify exam ownership
        cur.execute("SELECT section_id FROM exams WHERE exam_id = %s AND teacher_id = %s", (exam_id, user_id))
        exam = cur.fetchone()
        if not exam:
            return jsonify({"ok": False, "error": "Exam not found or unauthorized"}), 404

        if action == "toggle":
            if enrollment_id is None or is_allowed is None:
                return jsonify({"ok": False, "error": "Missing data"}), 400
            cur.execute("""
                INSERT INTO exam_student_permissions (exam_id, enrollment_id, is_allowed)
                VALUES (%s, %s, %s)
                ON CONFLICT (exam_id, enrollment_id)
                DO UPDATE SET is_allowed = EXCLUDED.is_allowed
            """, (exam_id, enrollment_id, is_allowed))
        elif action == "allow_all":
            # Get all students in that section
            cur.execute("SELECT enrollment_id FROM enrollments WHERE section_id = %s AND status IN ('approved', 'enrolled')", (exam['section_id'],))
            students = cur.fetchall()
            for s in students:
                cur.execute("""
                    INSERT INTO exam_student_permissions (exam_id, enrollment_id, is_allowed)
                    VALUES (%s, %s, TRUE)
                    ON CONFLICT (exam_id, enrollment_id)
                    DO UPDATE SET is_allowed = TRUE
                """, (exam_id, s['enrollment_id']))
        elif action == "deselect_all":
            # We can either delete them or set them to FALSE. Setting to FALSE is clearer.
            cur.execute("SELECT enrollment_id FROM enrollments WHERE section_id = %s AND status IN ('approved', 'enrolled')", (exam['section_id'],))
            students = cur.fetchall()
            for s in students:
                cur.execute("""
                    INSERT INTO exam_student_permissions (exam_id, enrollment_id, is_allowed)
                    VALUES (%s, %s, FALSE)
                    ON CONFLICT (exam_id, enrollment_id)
                    DO UPDATE SET is_allowed = FALSE
                """, (exam_id, s['enrollment_id']))
        
        db.commit()
        return jsonify({"ok": True})
    except Exception as e:
        db.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        cur.close()
        db.close()

@teacher_bp.route("/teacher/submissions/<int:submission_id>/mark-viewed", methods=["POST"])
def teacher_mark_viewed(submission_id):
    if not _require_teacher():
        return jsonify({"error": "Unauthorized"}), 403

    user_id = session.get("user_id")
    
    db = get_db_connection()
    cur = db.cursor()
    try:
        # Verify teacher owns this activity via submission_id
        cur.execute("""
            SELECT 1 FROM activity_submissions sub
            JOIN activities a ON sub.activity_id = a.activity_id
            WHERE sub.submission_id = %s AND a.teacher_id = %s
        """, (submission_id, user_id))
        
        if not cur.fetchone():
            return jsonify({"error": "Unauthorized submission access"}), 403

        # Update status to 'Viewed' ONLY if it's currently 'Submitted' or NULL
        # Don't overwrite 'Graded' status
        cur.execute("""
            UPDATE activity_submissions 
            SET status = 'Viewed' 
            WHERE submission_id = %s AND (status IS NULL OR status = 'Submitted')
        """, (submission_id,))
        
        db.commit()
        return jsonify({"ok": True})
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        db.close()

@teacher_bp.route("/teacher/activities/<int:activity_id>/toggle-status", methods=["POST"])
def toggle_activity_status(activity_id):
    if not _require_teacher(): 
        return redirect("/")

    user_id = session.get("user_id")
    branch_id = session.get("branch_id")

    db = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        active_tab = request.form.get("active_tab")

        # ✅ Get active school year
        year_id = _get_active_school_year(cur, branch_id)
        if not year_id:
            flash("No active school year.", "error")
            return redirect(request.referrer or url_for("teacher.teacher_dashboard"))

        # ✅ Verify activity (Join with sections to ensure year context)
        cur.execute("""
            SELECT a.status, a.section_id, a.title, a.subject_id 
            FROM activities a
            JOIN sections s ON a.section_id = s.section_id
            WHERE a.activity_id = %s AND a.teacher_id = %s AND s.year_id = %s
        """, (activity_id, user_id, year_id))

        act = cur.fetchone()
        if not act:
            flash("Activity not found.", "error")
            return redirect(request.referrer or url_for("teacher.teacher_dashboard"))

        subject_id = act['subject_id']
        section_id = act['section_id']
        title = act['title']

        # Toggle status
        new_status = 'Published' if act['status'] == 'Draft' else 'Draft'

        cur.execute("""
            UPDATE activities 
            SET status = %s, updated_at = NOW() 
            WHERE activity_id = %s
        """, (new_status, activity_id))

        # 🔥 SEND NOTIFICATIONS ONLY TO ACTIVE YEAR STUDENTS
        if new_status == 'Published':
            cur.execute("""
                SELECT DISTINCT u.user_id 
                FROM enrollments e 
                JOIN users u ON u.user_id = e.user_id 
                WHERE e.section_id = %s 
                  AND e.branch_id = %s
                  AND e.year_id = %s
                  AND e.status IN ('approved', 'enrolled')

                UNION

                SELECT DISTINCT u.user_id
                FROM enrollments e
                JOIN student_accounts sa ON sa.enrollment_id = e.enrollment_id
                JOIN users u ON u.username = sa.username
                WHERE e.section_id = %s 
                  AND e.branch_id = %s
                  AND e.year_id = %s
                  AND e.status IN ('approved', 'enrolled')
            """, (section_id, branch_id, year_id, section_id, branch_id, year_id))

            student_users = cur.fetchall()

            for su in student_users:
                cur.execute("""
                    INSERT INTO student_notifications 
                        (student_id, title, message, link) 
                    VALUES (%s, %s, %s, %s)
                """, (
                    su['user_id'],
                    f"New Activity: {title}",
                    f"Your teacher posted a new activity: {title}.",
                    f"/student/activities/{activity_id}"
                ))

        db.commit()

        flash(
            f"Activity is now {'visible' if new_status == 'Published' else 'hidden'} for students.",
            "success"
        )

        return redirect(url_for(
            "teacher.teacher_class_view",
            subject_id=subject_id,
            active_tab=active_tab
        ))

    except Exception as e:
        db.rollback()
        flash(f"Error toggling status: {str(e)}", "error")
        return redirect(request.referrer or url_for("teacher.teacher_dashboard"))

    finally:
        cur.close()
        db.close()

@teacher_bp.route("/teacher/subject/<int:subject_id>")
def teacher_class_view(subject_id):
    if not _require_teacher(): 
        return redirect("/")

    user_id = session.get("user_id")
    branch_id = session.get("branch_id")

    db = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        # ✅ GET ACTIVE SCHOOL YEAR
        year_id = _get_active_school_year(cur, branch_id)
        if not year_id:
            flash("No active school year.", "error")
            return redirect(url_for("teacher.teacher_dashboard"))

        # ✅ FILTER SECTIONS BY YEAR
        cur.execute("""
            SELECT s.section_id, s.section_name, g.name AS grade_level_name, sub.name AS subject_name
            FROM section_teachers st
            JOIN sections s ON st.section_id = s.section_id
            JOIN grade_levels g ON s.grade_level_id = g.id
            JOIN subjects sub ON st.subject_id = sub.subject_id
            WHERE st.teacher_id = %s 
              AND st.subject_id = %s
              AND s.branch_id = %s
              AND s.year_id = %s
            ORDER BY g.name, s.section_name
        """, (user_id, subject_id, branch_id, year_id))

        sections = cur.fetchall()

        if not sections:
            flash("No sections found for the active school year.", "error")
            return redirect(url_for("teacher.teacher_dashboard"))

        subject_name = sections[0]["subject_name"]

        # ✅ ACTIVE SECTION LOGIC
        active_section_id = request.args.get("section", type=int)
        if not active_section_id:
            active_section_id = session.get('teacher_selected_section')

            if active_section_id not in [sec["section_id"] for sec in sections]:
                active_section_id = sections[0]["section_id"]

        session['teacher_selected_section'] = active_section_id
        session['teacher_selected_subject'] = subject_id

        active_section = next(
            (s for s in sections if s["section_id"] == active_section_id),
            sections[0]
        )

        class_info = {
            "subject_name": subject_name,
            "section_name": active_section["section_name"],
            "grade_level_name": active_section["grade_level_name"]
        }

        # ✅ ACTIVITIES (FILTER BY YEAR)
        cur.execute('''
            SELECT a.*, 
                   (SELECT COUNT(*) FROM activity_submissions sub2 
                    WHERE sub2.activity_id = a.activity_id) AS submission_count
            FROM activities a
            JOIN sections s ON a.section_id = s.section_id
            WHERE a.teacher_id = %s 
              AND a.section_id = %s 
              AND a.subject_id = %s
              AND s.year_id = %s
            ORDER BY a.created_at DESC
        ''', (user_id, active_section_id, subject_id, year_id))

        activities = cur.fetchall() or []

        # ✅ QUIZZES (FILTER BY YEAR)
        cur.execute("""
            SELECT e.exam_id, e.title, e.scheduled_start, e.status, e.created_at, e.is_visible,
                   e.grading_period, e.duration_mins, e.is_archived,
                   (SELECT COUNT(*) FROM exam_questions q WHERE q.exam_id = e.exam_id) AS question_count,
                   (SELECT COUNT(*) FROM exam_results r WHERE r.exam_id = e.exam_id) AS attempt_count
            FROM exams e
            JOIN sections s ON e.section_id = s.section_id
            WHERE e.teacher_id = %s 
              AND e.section_id = %s 
              AND e.subject_id = %s 
              AND e.exam_type = 'quiz'
              AND s.year_id = %s
            ORDER BY e.created_at DESC
        """, (user_id, active_section_id, subject_id, year_id))

        quizzes = cur.fetchall() or []

        # ✅ PERIODICAL EXAMS + MONTHLY EXAMS
        cur.execute("""
            SELECT e.exam_id, e.title, e.exam_type, e.scheduled_start, e.status, e.created_at, e.is_visible,
                   e.grading_period, e.duration_mins, e.is_archived,
                   (SELECT COUNT(*) FROM exam_questions q WHERE q.exam_id = e.exam_id) AS question_count,
                   (SELECT COUNT(*) FROM exam_results r WHERE r.exam_id = e.exam_id) AS attempt_count
            FROM exams e
            JOIN sections s ON e.section_id = s.section_id
            WHERE e.teacher_id = %s
              AND e.section_id = %s
              AND e.subject_id = %s
              AND e.exam_type IN ('exam', 'monthly_exam')
              AND s.year_id = %s
            ORDER BY e.created_at DESC
        """, (user_id, active_section_id, subject_id, year_id))
        exams = cur.fetchall() or []

        # ✅ STATS (no change)
        act_stats = {
            'total': len(activities),
            'published': sum(1 for a in activities if a['status'].lower() == 'published'),
            'drafts': sum(1 for a in activities if a['status'].lower() == 'draft'),
            'closed': sum(1 for a in activities if a['status'].lower() == 'closed')
        }

        quiz_stats = {
            'total': len(quizzes),
            'published': sum(1 for q in quizzes if q['status'].lower() == 'published'),
            'drafts': sum(1 for q in quizzes if q['status'].lower() == 'draft'),
            'closed': sum(1 for q in quizzes if q['status'].lower() == 'closed')
        }

        exam_stats = {
            'total': len(exams),
            'published': sum(1 for e in exams if e['status'].lower() == 'published'),
            'drafts': sum(1 for e in exams if e['status'].lower() == 'draft'),
            'closed': sum(1 for e in exams if e['status'].lower() == 'closed')
        }

        # ✅ STUDENTS (Class List) - Filtered by Section, Branch, and Year
        # We also ensure the status is 'approved' or 'enrolled'
        cur.execute("""
            SELECT e.enrollment_id, e.student_name, e.status, e.grade_level, e.lrn, e.gender
            FROM enrollments e
            WHERE e.section_id = %s 
              AND e.branch_id = %s 
              AND e.year_id = %s
              AND e.status IN ('approved', 'enrolled')
            ORDER BY e.student_name ASC
        """, (active_section_id, branch_id, year_id))
        enrolled_students = cur.fetchall() or []
        unlocked_periods = _get_unlocked_grading_periods(cur, branch_id, year_id)

    finally:
        cur.close()
        db.close()

    ph_tz = pytz.timezone("Asia/Manila")
    now_naive = datetime.now(timezone.utc).astimezone(ph_tz).replace(tzinfo=None)

    return render_template(
        "teacher_subject_detail.html",
        sections=sections,
        active_section_id=active_section_id,
        class_info=class_info,
        activities=activities,
        quizzes=quizzes,
        exams=exams,
        act_stats=act_stats,
        quiz_stats=quiz_stats,
        exam_stats=exam_stats,
        section_id=active_section_id,
        subject_id=subject_id,
        enrolled_students=enrolled_students,
        now=now_naive,
        unlocked_periods=unlocked_periods
    )

@teacher_bp.route("/api/teacher/add-student", methods=["POST"])
def api_teacher_add_student():
    if not _require_teacher(): return jsonify({"error": "Unauthorized"}), 403
    
    data = request.json or {}
    student_name = data.get("student_name", "").strip()
    section_id = data.get("section_id")
    
    if not student_name or not section_id:
        return jsonify({"error": "Student name and section ID are required"}), 400
        
    user_id = session.get("user_id")
    branch_id = session.get("branch_id")
    
    db = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        # Validate teacher owns this section
        cur.execute("SELECT 1 FROM section_teachers WHERE teacher_id = %s AND section_id = %s", (user_id, section_id))
        if not cur.fetchone():
            return jsonify({"error": "Unauthorized section access"}), 403
            
        # Get grade level for the section to fill the enrollment record properly
        cur.execute("""
            SELECT g.name AS grade_level, s.year_id
            FROM sections s
            JOIN grade_levels g ON s.grade_level_id = g.id
            WHERE s.section_id = %s
        """, (section_id,))
        grade_row = cur.fetchone()
        grade_level = grade_row['grade_level'] if grade_row else ""
        year_id = grade_row['year_id'] if grade_row else None

        cur.execute("""
            SELECT 1 FROM section_teachers st
            JOIN sections s ON st.section_id = s.section_id
            WHERE st.teacher_id = %s AND st.section_id = %s AND s.year_id = %s
        """, (user_id, section_id, year_id))
        if not cur.fetchone():
            return jsonify({"error": "Unauthorized section access"}), 403
        
        # Insert minimal late enrollee
        cur.execute("""
            INSERT INTO enrollments (student_name, branch_id, section_id, grade_level, status, year_id)
            VALUES (%s, %s, %s, %s, 'enrolled', %s)
            RETURNING enrollment_id
        """, (student_name, branch_id, section_id, grade_level, year_id))
        
        db.commit()
        return jsonify({"ok": True})
        
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        db.close()


@teacher_bp.route("/teacher/profile")
def teacher_profile():
    if not _require_teacher():
        return redirect("/")

    user_id = session.get("user_id")
    if not user_id:
        flash("User ID not found.", "error")
        return redirect("/")

    db = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        # 1. Fetch core teacher data first
        cur.execute("""
            SELECT u.*, b.branch_name 
            FROM users u
            LEFT JOIN branches b ON u.branch_id = b.branch_id
            WHERE u.user_id = %s AND u.role = 'teacher'
        """, (user_id,))
        teacher = cur.fetchone()
        
        if not teacher:
            flash("Teacher record not found.", "error")
            return redirect(url_for("teacher.teacher_dashboard"))

        # 2. Get active year using branch from teacher record
        year_id = _get_active_school_year(cur, teacher['branch_id'])

        # 3. Get assigned subjects and sections for the active year
        cur.execute("""
            SELECT sub.name AS subject_name,
                   g.name AS grade_level,
                   s.section_name
            FROM section_teachers st
            JOIN subjects sub ON st.subject_id = sub.subject_id
            JOIN sections s ON st.section_id = s.section_id
            JOIN grade_levels g ON s.grade_level_id = g.id
            WHERE st.teacher_id = %s AND s.year_id = %s
            ORDER BY g.name, s.section_name, sub.name
        """, (user_id, year_id))
        assignments = cur.fetchall()
        
        return render_template("teacher_profile.html", teacher=teacher, assignments=assignments)
    finally:
        cur.close()
        db.close()

@teacher_bp.route("/teacher/my-schedule")
def teacher_schedules():
    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    branch_id = session["branch_id"]
    teacher_id = session["user_id"]  # assuming logged-in teacher

    # -- Find all active years for the branch
    cursor.execute("""
        SELECT year_id FROM school_years 
        WHERE is_active = TRUE AND branch_id = %s
        ORDER BY label DESC
    """, (branch_id,))
    active_years = [row["year_id"] for row in cursor.fetchall()]

    schedules = []
    if active_years:
        # -- Get teacher's schedules for active years only
        cursor.execute("""
            SELECT s.*, subj.name AS subject_name, sec.section_name AS section_name, 
                   y.label AS year_label
            FROM schedules s
            JOIN subjects subj ON s.subject_id = subj.subject_id
            JOIN sections sec ON s.section_id = sec.section_id
            JOIN school_years y ON s.year_id = y.year_id
            WHERE s.branch_id = %s AND s.teacher_id = %s
              AND s.year_id = ANY(%s)
              AND s.is_archived = FALSE
            ORDER BY y.label DESC, sec.section_name, subj.name, s.day_of_week, s.start_time
        """, (branch_id, teacher_id, active_years))
        schedules = cursor.fetchall()


    cursor.close(); db.close()

    return render_template("teacher_schedules.html", schedules=schedules)

# =======================
# ATTENDANCE & PARTICIPATION HUB (Teacher)
# =======================
@teacher_bp.route("/teacher/attendance", methods=["GET", "POST"])
def teacher_attendance():
    if not _require_teacher():
        return redirect(url_for("auth.login"))

    teacher_id = session.get("user_id")
    branch_id  = session.get("branch_id")
    db = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        year_id = _get_active_school_year(cur, branch_id)
        if not year_id:
            flash("No active school year.", "error")
            return redirect(url_for("teacher.teacher_dashboard"))

        # All school years for this branch (for the year switcher)
        cur.execute("""
            SELECT year_id, label, is_active
            FROM school_years
            WHERE branch_id = %s
            ORDER BY label DESC
        """, (branch_id,))
        school_years = cur.fetchall() or []

        # 1. Filters
        sel_year_id    = request.args.get("year_id", type=int) or year_id
        sel_section_id = request.args.get("section_id", type=int)
        sel_subject_id = request.args.get("subject_id", type=int)
        sel_date_str   = request.args.get("date")
        if not sel_date_str:
            sel_date_str = datetime.now().strftime('%Y-%m-%d')
            
        try:
            sel_date = datetime.strptime(sel_date_str, '%Y-%m-%d').date()
        except ValueError:
            sel_date = datetime.now().date()
            sel_date_str = sel_date.strftime('%Y-%m-%d')

        # 2. Check if holiday/weekend/past date
        is_off, off_reason = _is_holiday_or_weekend(cur, branch_id, year_id, sel_date)
        
        # Restriction: No marking for past dates
        is_past = sel_date < datetime.now().date()
        if is_past:
            is_off = True
            off_reason = "Attendance for past dates cannot be modified."

        # 3. Handle Save (POST)
        if request.method == "POST":
            post_year_id = request.form.get("year_id", type=int) or year_id
            if is_off:
                flash(f"Cannot record attendance: {off_reason}", "error")
            elif post_year_id != year_id:
                flash("Cannot modify attendance for a past school year.", "error")
            else:
                data = request.form
                enrollment_ids = [k.split('_')[1] for k in data.keys() if k.startswith('status_')]
                
                # Points mapping
                pts_map = {'P': 1.0, 'A': 0.0, 'H': 0.5, 'L': 0.75, 'E': 1.0}

                try:
                    # FETCH EXISTING STATUS AND NECESSARY INFO BEFORE UPDATE
                    eids_int = [int(eid) for eid in enrollment_ids if eid.isdigit()]
                    existing_status = {}
                    student_info = {}
                    
                    if eids_int and sel_subject_id:
                        # Get existing attendance status
                        cur.execute("""
                            SELECT enrollment_id, status FROM daily_attendance
                            WHERE branch_id = %s AND year_id = %s AND subject_id = %s AND attendance_date = %s
                              AND enrollment_id = ANY(%s)
                        """, (branch_id, year_id, sel_subject_id, sel_date, eids_int))
                        for r in cur.fetchall():
                            existing_status[r['enrollment_id']] = r['status']
                            
                        # Get student info for emails and notifications
                        cur.execute("""
                            SELECT e.enrollment_id, e.student_name, e.guardian_email,
                                   (SELECT name FROM subjects WHERE subject_id = %s LIMIT 1) as subject_name,
                                   ps.parent_id
                            FROM enrollments e
                            LEFT JOIN parent_student ps ON ps.student_id = e.enrollment_id
                            WHERE e.enrollment_id = ANY(%s)
                        """, (sel_subject_id, eids_int))
                        for r in cur.fetchall():
                            student_info[r['enrollment_id']] = r

                    from utils.send_email import send_email

                    for eid in enrollment_ids:
                        eid_int = int(eid)
                        status   = data.get(f"status_{eid}")
                        pts      = pts_map.get(status, 1.0)
                        part_pts = data.get(f"part_{eid}", type=float, default=0.0)

                        # Save Attendance
                        cur.execute("""
                            INSERT INTO daily_attendance (enrollment_id, subject_id, branch_id, year_id, attendance_date, status, points, recorded_by)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (enrollment_id, subject_id, attendance_date) DO UPDATE
                            SET status = EXCLUDED.status, points = EXCLUDED.points, recorded_by = EXCLUDED.recorded_by
                        """, (eid_int, sel_subject_id, branch_id, year_id, sel_date, status, pts, teacher_id))

                        # Check if changed to Absent
                        if status == 'A' and existing_status.get(eid_int) != 'A':
                            info = student_info.get(eid_int)
                            if info:
                                subj_name = info['subject_name'] or "class"
                                student_name = info['student_name']
                                display_date = sel_date.strftime("%B %d, %Y")
                                msg_body = f"Alert: {student_name} was marked absent in {subj_name} for today ({display_date})."
                                
                                # Insert Parent Notification
                                if info['parent_id']:
                                    cur.execute("""
                                        INSERT INTO parent_notifications (parent_id, student_id, title, message)
                                        VALUES (%s, %s, %s, %s)
                                    """, (info['parent_id'], eid_int, "Absence Alert", msg_body))
                                
                                # Send Email
                                if info['guardian_email']:
                                    html_body = f"""
                                    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px;">
                                        <h2 style="color: #e53e3e;">Attendance Alert</h2>
                                        <p>Dear Parent/Guardian,</p>
                                        <p>Please be advised that <strong>{student_name}</strong> was marked <strong>ABSENT</strong> in <strong>{subj_name}</strong> for today, <strong>{display_date}</strong>.</p>
                                        <p>If you believe this is an error or if you have any concerns, please log in to the Parent Portal or contact the school administration.</p>
                                        <br>
                                        <p>Best regards,<br>Liceo Administration</p>
                                    </div>
                                    """
                                    send_email(info['guardian_email'], f"Absence Alert: {student_name}", msg_body, html_body=html_body, use_background=True)

                        # Save Participation (always upsert so 0 clears previous)
                        cur.execute("""
                            INSERT INTO daily_participation (enrollment_id, subject_id, branch_id, year_id, participation_date, points, recorded_by)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (enrollment_id, subject_id, participation_date) DO UPDATE
                            SET points = EXCLUDED.points, recorded_by = EXCLUDED.recorded_by
                        """, (eid_int, sel_subject_id, branch_id, year_id, sel_date, part_pts, teacher_id))
                    
                    db.commit()
                    flash("Records saved successfully.", "success")
                except Exception as e:
                    db.rollback()
                    flash(f"Error saving: {str(e)}", "error")

        # 4. Fetch assigned sections/subjects for the dropdown
        cur.execute("""
            SELECT s.section_id, s.section_name, sub.subject_id, sub.name AS subject_name,
                   g.name AS grade_name
            FROM section_teachers st
            JOIN sections s ON st.section_id = s.section_id
            JOIN subjects sub ON st.subject_id = sub.subject_id
            JOIN grade_levels g ON s.grade_level_id = g.id
            WHERE st.teacher_id = %s AND s.year_id = %s
            ORDER BY g.name, s.section_name
        """, (teacher_id, sel_year_id))
        assignments = cur.fetchall()

        # 5. Fetch students if section/subject selected
        students = []
        if sel_section_id and sel_subject_id:
            cur.execute("""
                SELECT e.enrollment_id, COALESCE(u.full_name, e.student_name) AS full_name, e.lrn, e.gender,
                       da.status AS cur_status, dp.points AS cur_part
                FROM enrollments e
                LEFT JOIN users u ON e.user_id = u.user_id
                LEFT JOIN daily_attendance da ON e.enrollment_id = da.enrollment_id 
                     AND da.subject_id = %s AND da.attendance_date = %s
                LEFT JOIN daily_participation dp ON e.enrollment_id = dp.enrollment_id 
                     AND dp.subject_id = %s AND dp.participation_date = %s
                WHERE e.section_id = %s AND e.branch_id = %s AND e.year_id = %s
                  AND e.status IN ('approved', 'enrolled')
                ORDER BY e.student_name ASC
            """, (sel_subject_id, sel_date, sel_subject_id, sel_date, sel_section_id, branch_id, sel_year_id))
            students = cur.fetchall()

        return render_template("teacher_attendance.html", 
                               assignments=assignments, 
                               students=students,
                               sel_section_id=sel_section_id,
                               sel_subject_id=sel_subject_id,
                               sel_date=sel_date_str,
                               is_off=is_off,
                               off_reason=off_reason,
                               school_years=school_years,
                               sel_year_id=sel_year_id,
                               active_year_id=year_id)
    finally:
        cur.close()
        db.close()

@teacher_bp.route("/teacher/attendance/export")
def teacher_attendance_export():
    if not _require_teacher():
        return redirect(url_for("auth.login"))

    teacher_id = session.get("user_id")
    branch_id  = session.get("branch_id")
    
    sel_section_id = request.args.get("section_id", type=int)
    sel_subject_id = request.args.get("subject_id", type=int)
    
    if not sel_section_id or not sel_subject_id:
        flash("Please select section and subject first.", "error")
        return redirect(url_for("teacher.teacher_attendance"))

    db = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        year_id = _get_active_school_year(cur, branch_id)
        
        # Get metadata
        cur.execute("SELECT section_name FROM sections WHERE section_id = %s", (sel_section_id,))
        sec_name = cur.fetchone()["section_name"]
        cur.execute("SELECT name FROM subjects WHERE subject_id = %s", (sel_subject_id,))
        sub_name = cur.fetchone()["name"]

        # Fetch students and their tallies
        cur.execute("""
            SELECT COALESCE(u.full_name, e.student_name) AS student_name,
                   e.lrn,
                   COALESCE(att.attendance_points, 0) AS attendance_points,
                   COALESCE(att.present_days, 0) AS present_days,
                   COALESCE(att.days_recorded, 0) AS days_recorded,
                   COALESCE(part.participation_avg, 0) AS participation_avg
            FROM enrollments e
            LEFT JOIN users u ON e.user_id = u.user_id
            LEFT JOIN (
                SELECT enrollment_id,
                       COALESCE(SUM(points), 0) AS attendance_points,
                       COUNT(*) AS days_recorded,
                       SUM(CASE WHEN status = 'P' THEN 1 ELSE 0 END) AS present_days
                FROM daily_attendance
                WHERE subject_id = %s AND branch_id = %s AND year_id = %s
                GROUP BY enrollment_id
            ) att ON e.enrollment_id = att.enrollment_id
            LEFT JOIN (
                SELECT enrollment_id,
                       COALESCE(AVG(points), 0) AS participation_avg
                FROM daily_participation
                WHERE subject_id = %s AND branch_id = %s AND year_id = %s
                GROUP BY enrollment_id
            ) part ON e.enrollment_id = part.enrollment_id
            WHERE e.section_id = %s
              AND e.branch_id = %s
              AND e.year_id = %s
              AND e.status IN ('approved', 'enrolled')
            ORDER BY student_name ASC
        """, (
            sel_subject_id, branch_id, year_id,
            sel_subject_id, branch_id, year_id,
            sel_section_id, branch_id, year_id
        ))
        data = cur.fetchall()

        export_columns = [
            "Student Name",
            "LRN",
            "Attendance Points",
            "Present Days",
            "Days Recorded",
            "Participation Avg"
        ]
        if data:
            df = pd.DataFrame(data)
            df = df.rename(columns={
                "student_name": "Student Name",
                "lrn": "LRN",
                "attendance_points": "Attendance Points",
                "present_days": "Present Days",
                "days_recorded": "Days Recorded",
                "participation_avg": "Participation Avg"
            })
            df = df[export_columns]
        else:
            # Keep headers visible even when there are no rows.
            df = pd.DataFrame(columns=export_columns)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Sheet1')
            workbook = writer.book
            worksheet = writer.sheets['Sheet1']

            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#D9E1F2',
                'border': 1,
                'align': 'center',
                'valign': 'vcenter'
            })
            cell_format = workbook.add_format({'border': 1})

            for col_idx, col_name in enumerate(df.columns):
                worksheet.write(0, col_idx, col_name, header_format)
                max_len = max(df[col_name].astype(str).map(len).max() if not df.empty else 0, len(col_name))
                worksheet.set_column(col_idx, col_idx, min(max_len + 2, 40), cell_format)

        output.seek(0)

        filename = f"Attendance_{sec_name}_{sub_name}_{datetime.now().strftime('%Y%m%d')}.xlsx"
        return send_file(output, download_name=filename, as_attachment=True)

    finally:
        cur.close()
        db.close()
