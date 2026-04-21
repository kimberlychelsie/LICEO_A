from flask import Blueprint, render_template, jsonify, session, redirect, url_for
from db import get_db_connection
import psycopg2.extras

public_bp = Blueprint("public", __name__)

def query_all(sql, params=None):
    """Helper: return list of rows (RealDictCursor)"""
    db = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(sql, params or ())
        return cur.fetchall()
    finally:
        cur.close()
        db.close()

def query_one(sql, params=None):
    """Helper: return single row (RealDictCursor)"""
    db = get_db_connection()
    cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(sql, params or ())
        return cur.fetchone()
    finally:
        cur.close()
        db.close()


# =========================
# PUBLIC PAGES
# =========================
@public_bp.route("/")
def homepage():
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

    announcements = query_all("""
        SELECT announcement_id AS id, title, message, created_at, image_url
        FROM announcements
        WHERE is_active = TRUE
            AND audience = 'all'
        ORDER BY created_at DESC
    """)

    branches = query_all("""
        SELECT branch_id, branch_name, location
        FROM branches
        WHERE is_active = TRUE
        ORDER BY branch_name ASC
    """)

    return render_template(
        "homepage.html",
        announcements=announcements,
        branches=branches
    )


@public_bp.route("/branch/<int:branch_id>")
def branch_page(branch_id):
    branch = query_one("""
        SELECT branch_id, branch_name, location
        FROM branches
        WHERE branch_id = %s AND is_active = TRUE
    """, (branch_id,))

    if not branch:
        return "Branch not found", 404

    # Check if re-enrollment is open for this branch
    reenrollment_open = bool(query_one("""
        SELECT 1 FROM enrollments
        WHERE branch_id = %s AND status = 'open_for_enrollment'
        LIMIT 1
    """, (branch_id,)))

    return render_template("branch_page.html", branch=branch, reenrollment_open=reenrollment_open)


# =========================
# IN-APP FAQ VIEW (logged-in users: registrar, cashier, teacher, etc.)
# =========================
@public_bp.route("/faq")
def faq_view():
    if not session.get("role"):
        return redirect(url_for("auth.login"))
    branch_id = session.get("branch_id")
    db = get_db_connection()
    cur = db.cursor()
    try:
        cur.execute("""
            SELECT question, answer
            FROM chatbot_faqs
            WHERE branch_id IS NULL
            ORDER BY id ASC
        """)
        general_faqs = cur.fetchall() or []
        branch_faqs = []
        if branch_id:
            cur.execute("""
                SELECT question, answer
                FROM chatbot_faqs
                WHERE branch_id = %s
                ORDER BY id ASC
            """, (branch_id,))
            branch_faqs = cur.fetchall() or []
    finally:
        cur.close()
        db.close()
    return render_template(
        "faq_view.html",
        general_faqs=general_faqs,
        branch_faqs=branch_faqs,
    )


# =========================
# PUBLIC API (Chatbot FAQs)
# =========================
@public_bp.route("/api/faqs")
def api_faqs():
    role = session.get("role")
    branch_id = session.get("branch_id")

    db = get_db_connection()
    cur = db.cursor()
    try:
        # Logged in users: branch FAQs ONLY
        if role and branch_id:
            cur.execute("""
                SELECT question, answer
                FROM chatbot_faqs
                WHERE branch_id = %s
                ORDER BY id ASC
            """, (branch_id,))
        else:
            # Public (not logged in): general FAQs ONLY
            cur.execute("""
                SELECT question, answer
                FROM chatbot_faqs
                WHERE branch_id IS NULL
                ORDER BY id ASC
            """)

        rows = cur.fetchall() or []
        return jsonify([{"question": r[0], "answer": r[1]} for r in rows])

    except Exception:
        # wag app.logger dito kasi blueprint file; safe return empty
        return jsonify([]), 200
    finally:
        cur.close()
        db.close()
