import re

file_path = r"c:\Users\Maris Junterial\OneDrive\Documents\GitHub\LICEO_A\templates\teacher_exam_questions.html"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update Styles
new_styles = """
    .subj-wrap {
        max-width: 1200px;
        margin: 0 auto;
        padding: 24px 20px 64px;
    }
    .subj-hero {
        background: linear-gradient(135deg, #0f2a6b, #1a3a8f, #2250c8);
        border-radius: 20px;
        padding: 28px 32px;
        margin-bottom: 24px;
        position: relative;
        overflow: hidden;
        box-shadow: 0 8px 32px rgba(26, 58, 143, 0.28);
        display: flex;
        justify-content: space-between;
        align-items: center;
        color: white;
    }
    .two-column-layout {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 24px;
        align-items: start;
    }
    @media (max-width: 900px) {
        .two-column-layout {
            grid-template-columns: 1fr;
        }
    }
    .section-divider {
        font-size: 11px;
        font-weight: 800;
        color: #64748b;
        margin: 28px 0 16px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        border-bottom: 2px solid #e2e8f0;
        padding-bottom: 6px;
    }
    .btn-hero {
        background: rgba(255,255,255,0.15);
        color: #fff;
        border: 1px solid rgba(255,255,255,0.3);
    }
    .btn-hero:hover {
        background: rgba(255,255,255,0.25);
    }
"""
content = content.replace("    .container {\n        max-width: 800px;\n        margin: 0 auto;\n        padding: 24px 20px;\n    }", new_styles)

# 2. Replace Header
header_pattern = r'<div class="container">\s*<div\s*style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:10px; margin-bottom:20px;">.*?</div>\s*</div>\s*(?={% with messages)'
new_header = """<div class="subj-wrap">
    <header class="subj-hero">
        <div style="z-index:1; width:100%;">
            <h1 style="font-size:1.7rem; font-weight:900; margin:0 0 6px;">{{ exam.title }} — {{ 'Quiz' if exam.exam_type == 'quiz' else 'Exam' }} Builder</h1>
            <div style="font-size:0.9rem; color:rgba(255,255,255,0.8);">
                {{ exam.subject_name }} • {{ exam.section_name }} • {{ exam.duration_mins }} min •
                <span style="font-weight:700;">● {{ exam.status|capitalize }}</span>
            </div>
            
            <div style="display:flex; gap:10px; margin-top:16px; flex-wrap:wrap;">
                {% if exam.status == 'draft' %}
                <form method="POST" action="{{ url_for('teacher.teacher_exam_publish', exam_id=exam.exam_id) }}" onsubmit="return handleBtnLoad(this, 'Creating...');" style="display:inline;">
                    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                    <button type="submit" class="btn btn-success" style="background:#10b981; border:none;">🛑 Publish Quiz</button>
                </form>
                {% elif exam.status == 'published' %}
                <form method="POST" action="{{ url_for('teacher.teacher_exam_close', exam_id=exam.exam_id) }}" onsubmit="return confirm('Close this {{ 'quiz' if exam.exam_type == 'quiz' else 'exam' }}?');" style="display:inline;">
                    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                    <button type="submit" class="btn btn-danger" style="border:none;">🛑 Close Quiz</button>
                </form>
                {% endif %}
                <a href="{{ url_for('teacher.teacher_exam_edit_settings', exam_id=exam.exam_id) }}" class="btn btn-hero">⚙️ Settings</a>
                <a href="{{ url_for('teacher.teacher_exam_results', exam_id=exam.exam_id) }}" class="btn btn-hero">📊 Results</a>
                <a href="{{ url_for('teacher.teacher_class_view', subject_id=exam.subject_id, active_tab='quizzes' if exam.exam_type == 'quiz' else 'exams') }}" class="btn btn-hero">⬅ Back</a>
            </div>
        </div>
    </header>
"""
content = re.sub(header_pattern, new_header, content, flags=re.DOTALL)

# 3. Create two columns wrapper and replace card headings
content = content.replace('<!-- Question list -->', '<div class="two-column-layout">\n        <div class="col-left">\n    <!-- Question list -->')
content = content.replace('<h2>Questions ({{ questions|length }})</h2>', '<h2>📑 QUESTION LIST ({{ questions|length }} Questions)</h2>')

content = content.replace('<div class="card" id="inline-builder">', '</div> <!-- end col-left -->\n        <div class="col-right">\n            <div class="card">\n                <h2 style="font-size: 18px; margin-bottom: 0;">➕ QUIZ CREATOR & IMPORT TOOL</h2>\n\n                <h3 class="section-divider">--- 🤖 AUTO BUILD (FILL INLINE) ---</h3>\n                <div id="inline-builder">')

content = content.replace('<h2>Auto Build (Fill Inline)</h2>', '')
content = content.replace('<!-- Add question form (only if draft) -->\n    <div class="card">\n        <h2>Add Question</h2>', '<h3 class="section-divider">--- ✍️ MANUAL ADD QUESTION ---</h3>\n        <div id="manual-add-builder">')
content = content.replace('<!-- Add this inside the draft block, alongside the Add Question form -->\n    <div class="card">\n        <h2>Import Questions from File</h2>', '<h3 class="section-divider">--- 📁 IMPORT QUESTIONS FROM FILE ---</h3>\n        <div id="import-builder">')

# 4. Remove extra closing divs from the original cards and add them correctly
# The inline-builder card ended with </div>.
content = content.replace('</form>\n        {% endif %}\n    </div>\n\n    <h3 class="section-divider">--- ✍️ MANUAL ADD QUESTION ---</h3>', '</form>\n        {% endif %}\n    </div>\n\n    <h3 class="section-divider">--- ✍️ MANUAL ADD QUESTION ---</h3>')
# Wait, let's fix the closing tags more robustly via regex.

# We'll write this script, run it, and see the diff.
with open(r"c:\Users\Maris Junterial\OneDrive\Documents\GitHub\LICEO_A\templates\teacher_exam_questions.html", "w", encoding="utf-8") as f:
    f.write(content)

print("Done phase 1")
