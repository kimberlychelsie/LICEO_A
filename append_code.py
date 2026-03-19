import os

new_code = """

@teacher_bp.route("/teacher/reschedule", methods=["POST"])
def teacher_reschedule():
    if not _require_teacher():
        return jsonify({"error": "Unauthorized"}), 403

    user_id = session.get("user_id")
    branch_id = session.get("branch_id")

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

    db = get_db_connection()
    cur = db.cursor()
    try:
        # 1. Verify ownership of the item
        if item_type == 'activity':
            cur.execute("SELECT 1 FROM activities WHERE activity_id = %s AND teacher_id = %s", (item_id, user_id))
        else:
            cur.execute("SELECT 1 FROM exams WHERE exam_id = %s AND teacher_id = %s", (item_id, user_id))

        if not cur.fetchone():
            return jsonify({"error": "Unauthorized item access or item not found."}), 403

        # 2. Verify student enrollment in the same branch
        cur.execute("SELECT 1 FROM enrollments WHERE enrollment_id = %s AND branch_id = %s", (enrollment_id, branch_id))
        if not cur.fetchone():
            return jsonify({"error": "Invalid student or branch mismatch."}), 403

        # 3. Upsert into individual_extensions
        cur.execute(\"\"\"
            INSERT INTO individual_extensions (enrollment_id, item_type, item_id, new_due_date)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT ON CONSTRAINT uq_extension
            DO UPDATE SET new_due_date = EXCLUDED.new_due_date
        \"\"\", (enrollment_id, item_type, item_id, new_due_date))

        db.commit()
        return jsonify({"ok": True, "message": "Rescheduled successfully!"})
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        db.close()
"""

target_file = r"c:\LICEO_A\routes\teacher.py"
with open(target_file, "a") as f:
    f.write(new_code)

print(f"Successfully appended code to {target_file}")
