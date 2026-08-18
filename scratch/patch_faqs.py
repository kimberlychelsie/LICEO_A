import os
import re

routes_path = r"C:\Users\Maris Junterial\OneDrive\Documents\GitHub\LICEO_A\routes\branch_admin.py"
template_path = r"C:\Users\Maris Junterial\OneDrive\Documents\GitHub\LICEO_A\templates\branch_admin_faqs.html"

# 1. Update routes
with open(routes_path, "r", encoding="utf-8") as f:
    content = f.read()

# branch_admin_faq_add
add_old = """    branch_id = session.get("branch_id")
    question = request.form.get("question", "").strip()
    answer = request.form.get("answer", "").strip()

    if not question or not answer:
        flash("Question and Answer are required.", "error")
        return redirect("/branch-admin/faqs")"""
        
add_new = """    branch_id = session.get("branch_id")
    category = request.form.get("category", "General").strip()
    question = request.form.get("question", "").strip()
    answer = request.form.get("answer", "").strip()

    if not question or not answer:
        flash("Question and Answer are required.", "error")
        return redirect("/branch-admin/faqs")
        
    formatted_question = f"{category}|{question}" """

content = content.replace(add_old, add_new)

# branch_admin_faq_add insert
insert_old = """        cursor.execute(\"\"\"
            INSERT INTO chatbot_faqs (question, answer, branch_id)
            VALUES (%s, %s, %s)
        \"\"\", (question, answer, branch_id))"""
insert_new = """        cursor.execute(\"\"\"
            INSERT INTO chatbot_faqs (question, answer, branch_id)
            VALUES (%s, %s, %s)
        \"\"\", (formatted_question, answer, branch_id))"""
content = content.replace(insert_old, insert_new)

# branch_admin_faq_edit
edit_old = """    branch_id = session.get("branch_id")
    question = request.form.get("question", "").strip()
    answer = request.form.get("answer", "").strip()

    if not question or not answer:
        flash("Question and Answer are required.", "error")
        return redirect("/branch-admin/faqs")"""
edit_new = """    branch_id = session.get("branch_id")
    category = request.form.get("category", "General").strip()
    question = request.form.get("question", "").strip()
    answer = request.form.get("answer", "").strip()

    if not question or not answer:
        flash("Question and Answer are required.", "error")
        return redirect("/branch-admin/faqs")
        
    formatted_question = f"{category}|{question}" """
content = content.replace(edit_old, edit_new)

# branch_admin_faq_edit update
update_old = """        cursor.execute(\"\"\"
            UPDATE chatbot_faqs
            SET question=%s, answer=%s
            WHERE id=%s AND branch_id=%s
        \"\"\", (question, answer, faq_id, branch_id))"""
update_new = """        cursor.execute(\"\"\"
            UPDATE chatbot_faqs
            SET question=%s, answer=%s
            WHERE id=%s AND branch_id=%s
        \"\"\", (formatted_question, answer, faq_id, branch_id))"""
content = content.replace(update_old, update_new)

with open(routes_path, "w", encoding="utf-8") as f:
    f.write(content)

# 2. Update Template
with open(template_path, "r", encoding="utf-8") as f:
    html = f.read()

# Add Category to Add Form
add_form_old = """                <div class="entry-grid">
                    <div class="form-node">
                        <label>Question</label>
                        <input type="text" name="question" placeholder="e.g. How do student enroll?" required>
                    </div>"""
add_form_new = """                <div class="entry-grid">
                    <div class="form-node">
                        <label>Category</label>
                        <select name="category" required style="width: 100%; padding: 12px 16px; border: 1.5px solid var(--ma-border); border-radius: 12px; font-size: 0.95rem; font-family: inherit; margin-bottom: 16px; background-color: white;">
                            <option value="General">General</option>
                            <option value="Enrollment">Enrollment</option>
                            <option value="Tuition & Fees">Tuition & Fees</option>
                            <option value="Campus Life">Campus Life</option>
                            <option value="Grades & Documents">Grades & Documents</option>
                        </select>
                    </div>
                    <div class="form-node">
                        <label>Question</label>
                        <input type="text" name="question" placeholder="e.g. How do student enroll?" required>
                    </div>"""
html = html.replace(add_form_old, add_form_new)

# Add Filter and Sort
filter_old = """            <h2 style="margin:0; display:flex; align-items:center; gap: 10px;">
                FAQ List
            </h2>
            <span
                style="background: #f1f5f9; color: var(--ma-muted); padding: 4px 12px; border-radius: 8px; font-weight: 800; font-size: 0.8rem; text-transform: uppercase;">
                {{ faqs|length }} FAQs
            </span>
        </div>"""
filter_new = """            <h2 style="margin:0; display:flex; align-items:center; gap: 10px;">
                FAQ List
            </h2>
            <div style="display: flex; align-items: center; gap: 16px; flex-wrap: wrap;">
                <select id="categoryFilter" onchange="filterFaqs()" style="padding: 8px 16px; border: 1.5px solid var(--ma-border); border-radius: 12px; font-size: 0.9rem; font-family: inherit; font-weight: 700; color: var(--ma-text); outline: none;">
                    <option value="All">All Categories</option>
                    <option value="General">General</option>
                    <option value="Enrollment">Enrollment</option>
                    <option value="Tuition & Fees">Tuition & Fees</option>
                    <option value="Campus Life">Campus Life</option>
                    <option value="Grades & Documents">Grades & Documents</option>
                </select>
                <span
                    style="background: #f1f5f9; color: var(--ma-muted); padding: 4px 12px; border-radius: 8px; font-weight: 800; font-size: 0.8rem; text-transform: uppercase;">
                    <span id="faqCount">{{ faqs|length }}</span> FAQs
                </span>
            </div>
        </div>"""
html = html.replace(filter_old, filter_new)

# Add Badge and Category parse
loop_old = """            {% for faq in faqs %}
            <div class="faq-item">
                <div class="faq-question">
                    <div style="display: flex; align-items: flex-start; gap: 12px;">
                        <span style="color: var(--ma-gold); margin-top: 2px;"><i
                                class="fas fa-question-circle"></i></span>
                        <span>{{ faq[1] }}</span>
                    </div>"""
loop_new = """            {% for faq in faqs %}
            {% set parts = faq[1].split('|', 1) %}
            {% set cat = parts[0] if parts|length > 1 else 'General' %}
            {% set act_q = parts[1] if parts|length > 1 else faq[1] %}
            <div class="faq-item" data-category="{{ cat }}">
                <div class="faq-question">
                    <div style="display: flex; align-items: flex-start; gap: 12px; flex-direction: column;">
                        <span style="font-size: 0.8rem; background: #e0e7ff; color: var(--ma-primary); padding: 4px 10px; border-radius: 8px;">{{ cat }}</span>
                        <div style="display: flex; align-items: flex-start; gap: 12px;">
                            <span style="color: var(--ma-gold); margin-top: 2px;"><i class="fas fa-question-circle"></i></span>
                            <span>{{ act_q }}</span>
                        </div>
                    </div>"""
html = html.replace(loop_old, loop_new)

# Edit form updates
edit_old = """                        <div class="entry-grid">
                            <div class="form-node">
                                <label>Question</label>
                                <input type="text" class="edit-input" name="question" data-initial="{{ faq[1] }}"
                                    value="{{ faq[1] }}" oninput="checkChanges({{ faq[0] }})" required>
                            </div>"""
edit_new = """                        <div class="entry-grid">
                            <div class="form-node">
                                <label>Category</label>
                                <select name="category" class="edit-input" data-initial="{{ cat }}" onchange="checkChanges({{ faq[0] }})" required style="width: 100%; padding: 12px 16px; border: 1.5px solid var(--ma-border); border-radius: 12px; font-size: 0.95rem; font-family: inherit; margin-bottom: 16px; background-color: white;">
                                    <option value="General" {% if cat == 'General' %}selected{% endif %}>General</option>
                                    <option value="Enrollment" {% if cat == 'Enrollment' %}selected{% endif %}>Enrollment</option>
                                    <option value="Tuition & Fees" {% if cat == 'Tuition & Fees' %}selected{% endif %}>Tuition & Fees</option>
                                    <option value="Campus Life" {% if cat == 'Campus Life' %}selected{% endif %}>Campus Life</option>
                                    <option value="Grades & Documents" {% if cat == 'Grades & Documents' %}selected{% endif %}>Grades & Documents</option>
                                </select>
                            </div>
                            <div class="form-node">
                                <label>Question</label>
                                <input type="text" class="edit-input" name="question" data-initial="{{ act_q }}"
                                    value="{{ act_q }}" oninput="checkChanges({{ faq[0] }})" required>
                            </div>"""
html = html.replace(edit_old, edit_new)

# Add Javascript for Filter
js_old = """</script>
{% endblock %}"""
js_new = """    function filterFaqs() {
        const filter = document.getElementById('categoryFilter').value;
        const items = document.querySelectorAll('.faq-item');
        let count = 0;
        
        items.forEach(item => {
            if (filter === 'All' || item.dataset.category === filter) {
                item.style.display = 'block';
                count++;
            } else {
                item.style.display = 'none';
            }
        });
        
        document.getElementById('faqCount').innerText = count;
    }
</script>
{% endblock %}"""
html = html.replace(js_old, js_new)

with open(template_path, "w", encoding="utf-8") as f:
    f.write(html)
print("done")
