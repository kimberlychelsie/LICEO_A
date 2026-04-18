from flask import Blueprint, render_template, request, redirect, session, flash, url_for
from db import get_db_connection
from werkzeug.security import check_password_hash, generate_password_hash
import psycopg2.extras
import re
import secrets, hashlib
from datetime import datetime, timedelta, timezone
from utils.send_email import send_email
import os

from extensions import limiter

auth_bp = Blueprint("auth", __name__)
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:5000")

def check_password_change_required(user_data, is_student=False):
    """Check if user needs to change password on first login"""
    return user_data.get("require_password_change", 0) == 1


def validate_password_policy(password):
    """Enforce policy: min 8 chars, at least one letter and one number. Returns (ok, error_message)."""
    if len(password) < 8:
        return False, "Password must be at least 8 characters."
    if not re.search(r"[a-zA-Z]", password):
        return False, "Password must contain at least one letter."
    if not re.search(r"\d", password):
        return False, "Password must contain at least one number."
    return True, None

def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("8 per minute", exempt_when=lambda: request.method != "POST")
def login():
    # If the user is already logged in, redirect them directly to their portal
    if "role" in session:
        role = session["role"]
        if role == "super_admin":
            return redirect("/super-admin")
        elif role == "branch_admin":
            return redirect(url_for("branch_admin.dashboard"))
        elif role == "registrar":
            return redirect(url_for("registrar.registrar_home"))
        elif role == "cashier":
            return redirect(url_for("cashier.dashboard"))
        elif role == "teacher":
            return redirect(url_for("teacher.teacher_dashboard"))
        elif role == "student":
            return redirect(url_for("student_portal.dashboard"))
        elif role == "parent":
            return redirect(url_for("parent.dashboard"))
        elif role == "librarian":
            return redirect(url_for("librarian.dashboard"))

    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        db = get_db_connection()
        cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        try:
            # ✅ 1) Check regular users (super_admin, branch_admin, registrar, cashier, parent, librarian, student if exists)
            cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
            user = cursor.fetchone()

            if user:
                if str(user.get("status") or "active").lower() == "inactive":
                    flash("Account is inactive. Please contact your administrator.", "error")
                    return redirect(url_for("auth.login"))

                stored = user.get("password") or ""

                if stored.startswith(("scrypt:", "pbkdf2:", "$2b$", "$2a$")):
                    password_valid = check_password_hash(stored, password)
                else:
                    password_valid = (stored == password)

                if password_valid:
                    next_url = session.get("next_url")
                    session.clear()

                    session["user_id"]   = user["user_id"]
                    session["role"]      = user["role"]
                    session["branch_id"] = user.get("branch_id")
                    session["username"]  = user.get("username")
                    session["full_name"] = user.get("full_name")  # for display in sidebar

                    # Fetch branch name for sidebar display
                    if user.get("branch_id"):
                        cursor.execute(
                            "SELECT branch_name FROM branches WHERE branch_id = %s",
                            (user["branch_id"],)
                        )
                        brow = cursor.fetchone()
                        session["branch_name"] = brow["branch_name"] if brow else None
                    else:
                        session["branch_name"] = None

                    role = user["role"]

                    # ── For students: load enrollment session FIRST (before any redirects)
                    if role == "student":
                        enrollment_id = user.get("enrollment_id")
                        if enrollment_id:
                            cursor.execute("""
                                SELECT e.enrollment_id, e.student_name, e.grade_level, e.branch_id,
                                       sa.account_id
                                FROM enrollments e
                                LEFT JOIN student_accounts sa ON sa.enrollment_id = e.enrollment_id
                                WHERE e.enrollment_id = %s
                                LIMIT 1
                            """, (enrollment_id,))
                        else:
                            cursor.execute("""
                                SELECT sa.account_id, sa.enrollment_id,
                                       e.student_name, e.grade_level, e.branch_id
                                FROM student_accounts sa
                                JOIN enrollments e ON e.enrollment_id = sa.enrollment_id
                                WHERE sa.username = %s
                                LIMIT 1
                            """, (username,))
                        en = cursor.fetchone()
                        if en:
                            session["student_account_id"]  = en.get("account_id")
                            session["enrollment_id"]       = en.get("enrollment_id")
                            session["student_name"]        = en.get("student_name")
                            session["student_grade_level"] = en.get("grade_level")
                            session["branch_id"]           = en.get("branch_id") or session.get("branch_id")

                            # Make sure sidebar branch label follows the student's actual branch
                            if session.get("branch_id"):
                                cursor.execute(
                                    "SELECT branch_name FROM branches WHERE branch_id = %s",
                                    (session["branch_id"],),
                                )
                                brow = cursor.fetchone()
                                if brow:
                                    session["branch_name"] = brow["branch_name"]

                    # ── Force password change if required (session is already complete)
                    if check_password_change_required(user):
                        return redirect(url_for("auth.change_password"))

                    # ── Route to correct dashboard
                    if role == "super_admin":
                        return redirect("/super-admin")
                    elif role == "branch_admin":
                        return redirect("/branch-admin")
                    elif role == "registrar":
                        return redirect("/registrar")
                    elif role == "cashier":
                        return redirect("/cashier")
                    elif role == "librarian":
                        return redirect("/librarian")
                    elif role == "teacher":
                        return redirect("/teacher")
                    elif role == "parent":
                        return redirect("/parent/dashboard")
                    elif role == "student":
                        if next_url:
                            return redirect(next_url)
                        return redirect("/student/dashboard")
                    else:
                        return redirect("/")


            # ✅ 2) Check student accounts (MAIN student login path)
            cursor.execute("""
                SELECT
                    sa.*,
                    e.branch_id AS enroll_branch_id,
                    e.student_name,
                    e.grade_level,
                    e.email AS enroll_email
                FROM student_accounts sa
                JOIN enrollments e ON sa.enrollment_id = e.enrollment_id
                WHERE sa.username=%s
                LIMIT 1
            """, (username,))
            student = cursor.fetchone()

            if student and student.get("is_active"):
                stored = student.get("password") or ""

                if stored.startswith(("scrypt:", "pbkdf2:", "$2b$", "$2a$")):
                    password_valid = check_password_hash(stored, password)
                else:
                    password_valid = (stored == password)

                if password_valid:
                    branch_id = student.get("enroll_branch_id") or student.get("branch_id")
                    enrollment_id = student.get("enrollment_id")

                    # ✅ ensure student has a matching row in users (reservations.student_user_id NOT NULL)
                    cursor.execute("""
                        SELECT user_id
                        FROM users
                        WHERE username=%s
                        LIMIT 1
                    """, (username,))
                    urow = cursor.fetchone()

                    if urow:
                        student_user_id = urow["user_id"]
                        # Sync require_password_change from student_accounts → users
                        cursor.execute("""
                            UPDATE users
                            SET role='student', branch_id=%s,
                                require_password_change=%s, enrollment_id=%s
                            WHERE user_id=%s
                        """, (branch_id, student.get("require_password_change", False), enrollment_id, student_user_id))
                    else:
                        cursor.execute("""
                            INSERT INTO users (branch_id, username, password, role, require_password_change, enrollment_id, last_password_change, email)
                            VALUES (%s, %s, %s, 'student', %s, %s, NOW(), %s)
                            RETURNING user_id
                        """, (
                            branch_id,
                            username,
                            stored,
                            student.get("require_password_change", 0),
                            enrollment_id,
                            student.get("enroll_email")
                        ))
                        student_user_id = cursor.fetchone()["user_id"]

                    db.commit()

                    next_url = session.get("next_url")
                    # ✅ set sessions properly + enrollment-based references
                    session.clear()
                    session["user_id"] = student_user_id
                    session["student_account_id"] = student["account_id"]
                    session["role"] = "student"
                    session["branch_id"] = branch_id

                    # Sidebar branch label for student logins (student_accounts path)
                    if branch_id:
                        cursor.execute(
                            "SELECT branch_name FROM branches WHERE branch_id = %s",
                            (branch_id,),
                        )
                        brow = cursor.fetchone()
                        session["branch_name"] = brow["branch_name"] if brow else None
                    else:
                        session["branch_name"] = None

                    # ✅ enrollment reference for filters (THIS IS WHAT YOU NEED)
                    session["enrollment_id"] = enrollment_id
                    session["student_name"] = student.get("student_name")
                    session["student_grade_level"] = student.get("grade_level")

                    if check_password_change_required(student, is_student=True):
                        return redirect(url_for("auth.change_password"))

                    if next_url:
                        return redirect(next_url)

                    return redirect("/student/dashboard")

            flash("Invalid username or password", "error")
            return redirect(url_for("auth.login"))

        except Exception as e:
            db.rollback()
            flash(f"Login error: {str(e)}", "error")
            return redirect(url_for("auth.login"))

        finally:
            cursor.close()
            db.close()

    return render_template("login.html")


@auth_bp.route("/change-password", methods=["GET", "POST"])
def change_password():
    if "role" not in session:
        return redirect(url_for("auth.login"))

    db = get_db_connection()
    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        is_required = False

        if session["role"] == "student" and session.get("student_account_id"):
            cursor.execute(
                "SELECT require_password_change FROM student_accounts WHERE account_id=%s",
                (session.get("student_account_id"),)
            )
            account = cursor.fetchone()
            is_required = (account.get("require_password_change", 0) == 1) if account else False
        else:
            # All other roles (registrar, cashier, librarian, branch_admin, etc.) or student without student_account_id
            cursor.execute(
                "SELECT require_password_change FROM users WHERE user_id=%s",
                (session.get("user_id"),)
            )
            user = cursor.fetchone()
            # Treat None or missing column as 0; 1 = force change (same as registrar, cashier, librarian when created by Branch Admin)
            is_required = (user.get("require_password_change", 0) == 1) if user else False

        if request.method == "POST":
            new_password = (request.form.get("new_password") or "").strip()
            confirm_password = (request.form.get("confirm_password") or "").strip()

            if not new_password:
                flash("Please enter a new password.", "error")
                return redirect(url_for("auth.change_password"))

            if not is_required:
                current_password = (request.form.get("current_password") or "").strip()

                if session["role"] == "student" and session.get("student_account_id"):
                    cursor.execute(
                        "SELECT password FROM student_accounts WHERE account_id=%s",
                        (session.get("student_account_id"),)
                    )
                else:
                    cursor.execute(
                        "SELECT password FROM users WHERE user_id=%s",
                        (session.get("user_id"),)
                    )

                account_row = cursor.fetchone()

                if not account_row:
                    flash("Account not found", "error")
                    return redirect(url_for("auth.change_password"))

                stored = account_row.get("password") or ""
                if stored.startswith(("scrypt:", "pbkdf2:", "$2b$", "$2a$")):
                    current_password_valid = check_password_hash(stored, current_password)
                else:
                    current_password_valid = (stored == current_password)

                if not current_password_valid:
                    flash("Current password is incorrect", "error")
                    return redirect(url_for("auth.change_password"))

            ok, err = validate_password_policy(new_password)
            if not ok:
                flash(err, "error")
                return redirect(url_for("auth.change_password"))

            if new_password != confirm_password:
                flash("New passwords do not match", "error")
                return redirect(url_for("auth.change_password"))

            hashed_password = generate_password_hash(new_password)

            try:
                if session["role"] == "student":
                    # Always update BOTH tables so require_password_change is in sync
                    if session.get("student_account_id"):
                        cursor.execute("""
                            UPDATE student_accounts
                            SET password=%s, require_password_change=FALSE
                            WHERE account_id=%s
                        """, (hashed_password, session.get("student_account_id")))
                    # Always update users table too
                    cursor.execute("""
                        UPDATE users
                        SET password=%s, require_password_change=FALSE
                        WHERE user_id=%s
                    """, (hashed_password, session.get("user_id")))

                else:
                    # All other roles: update users only
                    cursor.execute("""
                        UPDATE users
                        SET password=%s, require_password_change=FALSE,
                            last_password_change=NOW()
                        WHERE user_id=%s
                    """, (hashed_password, session.get("user_id")))

                db.commit()
                flash("Password changed successfully!", "success")

                role = session.get("role")
                if role == "super_admin":
                    return redirect("/super-admin")
                elif role == "branch_admin":
                    return redirect("/branch-admin")
                elif role == "registrar":
                    return redirect("/registrar")
                elif role == "cashier":
                    return redirect("/cashier")
                elif role == "librarian":
                    return redirect("/librarian")
                elif role == "teacher":
                    return redirect("/teacher")
                elif role == "parent":
                    return redirect("/parent/dashboard")
                elif role == "student":
                    return redirect("/student/dashboard")
                else:
                    return redirect("/super-admin")

            except Exception as e:
                db.rollback()
                err_msg = str(e).strip()
                if len(err_msg) > 120:
                    err_msg = err_msg[:120] + "..."
                flash(f"Failed to change password. Please try again. ({err_msg})", "error")
                return redirect(url_for("auth.change_password"))

        return render_template("change_password.html", required=is_required)

    finally:
        cursor.close()
        db.close()
@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        email = (request.form.get("email") or "").strip().lower()

        generic_msg = "If the username and email match an account, we sent password reset instructions."

        if not username or not email:
            flash("Username and email are required.", "error")
            return redirect(url_for("auth.forgot_password"))

        cooldown_minutes = 2  # ✅ RESEND TIMER (change this to 5/10 if you want)

        db = get_db_connection()
        cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            expiry = datetime.now(timezone.utc) + timedelta(minutes=30)

            # 1) Try users table
            cur.execute("""
                SELECT user_id, username, role, branch_id, email
                FROM users
                WHERE username=%s
                LIMIT 1
            """, (username,))
            u = cur.fetchone()

            if u and (u.get("email") or "").strip().lower() == email:

                # ✅ RESEND TIMER for users (put it HERE)
                cur.execute("""
                    SELECT 1
                    FROM password_reset_tokens
                    WHERE user_id = %s
                      AND used_at IS NULL
                      AND expires_at > NOW()
                      AND created_at > NOW() - INTERVAL %s
                    LIMIT 1
                """, (u["user_id"], f"{cooldown_minutes} minutes"))
                if cur.fetchone():
                    flash(f"Please wait {cooldown_minutes} minute(s) before requesting another reset link.", "error")
                    return redirect(url_for("auth.forgot_password"))

                raw = secrets.token_urlsafe(32)
                th = _hash_token(raw)

                cur.execute("""
                    INSERT INTO password_reset_tokens (token_hash, user_id, student_account_id, email, expires_at)
                    VALUES (%s, %s, NULL, %s, %s)
                """, (th, u["user_id"], email, expiry))
                db.commit()

                link = f"{BASE_URL}/reset-password/{raw}"
                body = (
                    "We received a request to reset your password.\n\n"
                    f"Account: {u['role']} ({u['username']})\n"
                    f"Reset link: {link}\n\n"
                    "This link expires in 30 minutes. If you did not request this, ignore this email."
                )
                send_email(email, "Password Reset Request", body)

                flash(generic_msg, "success")
                return redirect(url_for("auth.login"))

            # 2) Try student_accounts table
            cur.execute("""
                SELECT
                    sa.account_id, sa.username, sa.branch_id,
                    e.student_name,
                    COALESCE(NULLIF(sa.email,''), NULLIF(e.email,''), NULLIF(e.guardian_email,'')) AS match_email
                FROM student_accounts sa
                LEFT JOIN enrollments e ON e.enrollment_id = sa.enrollment_id
                WHERE sa.username=%s
                LIMIT 1
            """, (username,))
            s = cur.fetchone()

            if s and (s.get("match_email") or "").strip().lower() == email:

                # ✅ RESEND TIMER for student_accounts (put it HERE)
                cur.execute("""
                    SELECT 1
                    FROM password_reset_tokens
                    WHERE student_account_id = %s
                      AND used_at IS NULL
                      AND expires_at > NOW()
                      AND created_at > NOW() - INTERVAL %s
                    LIMIT 1
                """, (s["account_id"], f"{cooldown_minutes} minutes"))
                if cur.fetchone():
                    flash(f"Please wait {cooldown_minutes} minute(s) before requesting another reset link.", "error")
                    return redirect(url_for("auth.forgot_password"))

                raw = secrets.token_urlsafe(32)
                th = _hash_token(raw)

                cur.execute("""
                    INSERT INTO password_reset_tokens (token_hash, user_id, student_account_id, email, expires_at)
                    VALUES (%s, NULL, %s, %s, %s)
                """, (th, s["account_id"], email, expiry))
                db.commit()

                link = f"{BASE_URL}/reset-password/{raw}"
                who = s.get("student_name") or "Student"
                body = (
                    "We received a request to reset your password.\n\n"
                    f"Account: Student ({s['username']}) - {who}\n"
                    f"Reset link: {link}\n\n"
                    "This link expires in 30 minutes. If you did not request this, ignore this email."
                )
                send_email(email, "Password Reset Request", body)

                flash(generic_msg, "success")
                return redirect(url_for("auth.login"))

            flash(generic_msg, "success")
            return redirect(url_for("auth.login"))

        except Exception as e:
            db.rollback()
            print("Forgot password error:", e)
            flash(generic_msg, "success")
            return redirect(url_for("auth.login"))
        finally:
            cur.close()
            db.close()

    return render_template("forgot_password.html")


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    if not token:
        flash("Invalid reset link.", "error")
        return redirect(url_for("auth.login"))

    token_hash = _hash_token(token)

    db = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
            SELECT *
            FROM password_reset_tokens
            WHERE token_hash=%s
            LIMIT 1
        """, (token_hash,))
        row = cur.fetchone()

        if not row or row.get("used_at"):
            flash("Reset link is invalid or already used.", "error")
            return redirect(url_for("auth.login"))

        # Expiry check
        cur.execute("""
    SELECT 1
    FROM password_reset_tokens
    WHERE token_hash=%s
      AND used_at IS NULL
      AND expires_at > NOW()
    LIMIT 1
""", (token_hash,))
        still_valid = cur.fetchone()

        if not still_valid:
            flash("Reset link expired. Please request a new one.", "error")
            return redirect(url_for("auth.forgot_password"))

        if request.method == "POST":
            new_password = request.form.get("password") or ""
            confirm = request.form.get("confirm_password") or ""

            # Use your existing policy function if available:
            ok, err = validate_password_policy(new_password)
            if not ok:
                flash(err, "error")
                return redirect(request.url)

            if new_password != confirm:
                flash("Passwords do not match.", "error")
                return redirect(request.url)

            hashed = generate_password_hash(new_password)

            if row.get("user_id"):
                cur.execute("""
                    UPDATE users
                    SET password=%s, require_password_change=FALSE, last_password_change=NOW()
                    WHERE user_id=%s
                """, (hashed, row["user_id"]))
            else:
                cur.execute("""
                    UPDATE student_accounts
                    SET password=%s, require_password_change=FALSE, last_password_change=NOW()
                    WHERE account_id=%s
                """, (hashed, row["student_account_id"]))

                # Optional: keep users table in sync if student has a users row too
                cur.execute("""
                    UPDATE users
                    SET password=%s, require_password_change=FALSE, last_password_change=NOW()
                    WHERE username = (SELECT username FROM student_accounts WHERE account_id=%s)
                """, (hashed, row["student_account_id"]))

            cur.execute("""
                UPDATE password_reset_tokens
                SET used_at = NOW()
                WHERE id = %s
            """, (row["id"],))

            db.commit()
            flash("Password reset successful. Please log in.", "success")
            return redirect(url_for("auth.login"))

        return render_template("reset_password.html")

    finally:
        cur.close()
        db.close()


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/")