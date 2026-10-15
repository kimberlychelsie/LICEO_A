from flask import Blueprint, render_template, jsonify, session, redirect, url_for, request, abort
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
        SELECT
            a.announcement_id AS id,
            a.title,
            a.message,
            a.created_at,
            a.image_url,
            a.branch_id,
            b.branch_name
        FROM announcements a
        LEFT JOIN branches b ON b.branch_id = a.branch_id
        WHERE a.is_active = TRUE
            AND a.audience = 'all'
        ORDER BY a.created_at DESC, a.announcement_id DESC
        LIMIT 3
    """)

    branches = query_all("""
        SELECT branch_id, branch_name, location, latitude, longitude
        FROM branches
        WHERE is_active = TRUE
        ORDER BY branch_name ASC
    """)

    return render_template(
        "homepage.html",
        announcements=announcements,
        branches=branches
    )


def _active_public_branches():
    return query_all("""
        SELECT branch_id, branch_name
        FROM branches
        WHERE is_active = TRUE
        ORDER BY branch_name ASC
    """) or []


def _requested_branch_id(active_branches=None):
    raw_branch_id = (request.args.get("branch_id") or "").strip()
    if not raw_branch_id:
        return None, False
    try:
        branch_id = int(raw_branch_id)
    except (TypeError, ValueError):
        return None, True
    if branch_id <= 0:
        return None, True

    if active_branches is not None:
        is_valid = any(branch["branch_id"] == branch_id for branch in active_branches)
    else:
        is_valid = bool(query_one("""
            SELECT 1
            FROM branches
            WHERE branch_id = %s AND is_active = TRUE
        """, (branch_id,)))
    return (branch_id, False) if is_valid else (None, True)


def _get_public_announcements_page(requested_page, branch_id=None, per_page=10):
    page = max(1, requested_page)
    filters = ["a.is_active = TRUE", "a.audience = %s"]
    params = ["all"]
    if branch_id is not None:
        filters.append("(a.branch_id = %s OR a.branch_id IS NULL)")
        params.append(branch_id)
    where_sql = " AND ".join(filters)

    count_row = query_one(f"""
        SELECT COUNT(*) AS total
        FROM announcements a
        WHERE {where_sql}
    """, params) or {}
    total = count_row.get("total", 0)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = min(page, total_pages)
    offset = (page - 1) * per_page

    announcements = query_all(f"""
        SELECT
            a.announcement_id AS id,
            a.title,
            a.message,
            a.created_at,
            a.image_url,
            a.branch_id,
            b.branch_name
        FROM announcements a
        LEFT JOIN branches b ON b.branch_id = a.branch_id
        WHERE {where_sql}
        ORDER BY a.created_at DESC, a.announcement_id DESC
        LIMIT %s OFFSET %s
    """, params + [per_page, offset])
    return announcements, page, total, total_pages


def _requested_page():
    try:
        return max(1, int(request.args.get("page", 1)))
    except (TypeError, ValueError):
        return 1


@public_bp.route("/announcements")
def public_announcements():
    per_page = 10
    branches = _active_public_branches()
    branch_id, invalid_branch = _requested_branch_id(branches)
    if invalid_branch:
        abort(404)
    announcements, page, total, total_pages = _get_public_announcements_page(_requested_page(), branch_id, per_page)
    return render_template(
        "public_announcements.html",
        announcements=announcements,
        branches=branches,
        selected_branch_id=branch_id,
        page=page,
        per_page=per_page,
        total_announcements=total,
        total_pages=total_pages,
    )


@public_bp.route("/api/public-announcements")
def public_announcements_api():
    per_page = 10
    branch_id, invalid_branch = _requested_branch_id()
    if invalid_branch:
        return jsonify({"error": "Invalid or unavailable branch."}), 400
    announcements, page, total, total_pages = _get_public_announcements_page(_requested_page(), branch_id, per_page)
    payload = []
    for announcement in announcements:
        created_at = announcement.get("created_at")
        payload.append({
            "id": announcement.get("id"),
            "title": announcement.get("title"),
            "message": announcement.get("message"),
            "image_url": announcement.get("image_url"),
            "branch_name": announcement.get("branch_name"),
            "source": announcement.get("branch_name") or ("School-wide" if announcement.get("branch_id") is None else None),
            "created_at": created_at.isoformat() if created_at else None,
            "published_at": created_at.strftime("%b %d, %Y") if created_at else None,
        })

    return jsonify({
        "announcements": payload,
        "selected_branch_id": branch_id,
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_previous": page > 1,
    })

@public_bp.route("/branch/<int:branch_id>")
def branch_page(branch_id):
    branch = query_one("""
        SELECT branch_id, branch_name, location, latitude, longitude
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

    # Fetch FAQs for the page (Branch-specific + General)
    faqs = query_all("""
        SELECT question, answer
        FROM chatbot_faqs
        WHERE branch_id = %s OR branch_id IS NULL
        ORDER BY (CASE WHEN branch_id = %s THEN 0 ELSE 1 END), id ASC
    """, (branch_id, branch_id))

    return render_template("branch_page.html", branch=branch, reenrollment_open=reenrollment_open, faqs=faqs)


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
    # Priority: 1. query param, 2. session (for logged in users)
    from flask import request
    branch_id = request.args.get("branch_id", type=int) or session.get("branch_id")

    db = get_db_connection()
    cur = db.cursor()
    try:
        if branch_id:
            # Fetch both branch-specific and general FAQs, branch-specific first
            cur.execute("""
                SELECT question, answer
                FROM chatbot_faqs
                WHERE branch_id = %s OR branch_id IS NULL
                ORDER BY (CASE WHEN branch_id = %s THEN 0 ELSE 1 END), id ASC
            """, (branch_id, branch_id))
        else:
            # Public (no branch context): general FAQs ONLY
            cur.execute("""
                SELECT question, answer
                FROM chatbot_faqs
                WHERE branch_id IS NULL
                ORDER BY id ASC
            """)

        rows = cur.fetchall() or []
        
        parsed_faqs = []
        for r in rows:
            q = r[0]
            ans = r[1]
            if '|' in q:
                cat, actual_q = q.split('|', 1)
            else:
                cat = "General"
                actual_q = q
            parsed_faqs.append({"category": cat, "question": actual_q, "answer": ans})

        return jsonify(parsed_faqs)

    except Exception:
        # wag app.logger dito kasi blueprint file; safe return empty
        return jsonify([]), 200
    finally:
        cur.close()
        db.close()


# =========================
# SECURE EXPIRING & PROTECTED DOCUMENT VIEW ROUTE
# =========================
@public_bp.route("/view-secure-document")
def view_secure_document():
    from flask import request, session, abort, render_template_string
    from itsdangerous import SignatureExpired, BadSignature
    from utils.secure_doc import verify_doc_token

    # 1. Incognito / Unauthenticated Blocking Check
    if not session.get("user_id") and not session.get("student_account_id") and not session.get("parent_id"):
        return render_template_string("""
        <!DOCTYPE html>
        <html><head><title>Access Denied</title></head>
        <body style="font-family:sans-serif; text-align:center; padding:50px;">
            <h2 style="color:#ef4444;">🔒 Access Denied (Bawal sa Incognito)</h2>
            <p>Hindi ma-o-open ang document na ito kung walang naka-login na account sa Liceo Portal.</p>
            <p>Mangyaring mag-login muna sa iyong Registrar / Admin / Student Portal.</p>
        </body></html>
        """), 403

    token = request.args.get("token")
    if not token:
        return "Missing document token", 400

    try:
        doc_url = verify_doc_token(token)
        return redirect(doc_url)
    except SignatureExpired:
        return render_template_string("""
        <!DOCTYPE html>
        <html><head><title>Link Expired</title></head>
        <body style="font-family:sans-serif; text-align:center; padding:50px;">
            <h2 style="color:#ef4444;">⏱️ Document Link Expired</h2>
            <p>Nag-expire na ang 15-minute security token ng document na ito.</p>
            <p>Mangyaring i-refresh ang iyong portal page upang makakuha ng bagong document link.</p>
        </body></html>
        """), 403
    except BadSignature:
        return "Invalid or tampered document link", 403

