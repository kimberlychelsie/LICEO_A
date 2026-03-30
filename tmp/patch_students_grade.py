"""
Patch registrar_students_by_grade.html:
1. Simplify the header to iPhone-style (minimal)
2. Add export buttons ONLY when grade is selected (Jinja condition), placed below filter card
"""
import re

filepath = r"c:\LICEO_A\templates\registrar_students_by_grade.html"

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# ── Step 1: Replace the entire header-bar div (including the old export buttons) ──
old_header_start = '<div class="header-bar">'
# Find the closing </div> of the header-bar
header_start_idx = content.find(old_header_start + "\n")
if header_start_idx == -1:
    header_start_idx = content.find(old_header_start)

# Find the end of the header-bar block (closing tag after buttons div)
# The header-bar is followed by a blank line then filter-card
header_end_marker = "\n\n<div class=\"filter-card\">"
header_end_idx = content.find(header_end_marker, header_start_idx)

if header_start_idx == -1 or header_end_idx == -1:
    print("ERROR: Could not find header-bar markers")
    print(f"header_start_idx={header_start_idx}, header_end_idx={header_end_idx}")
    exit(1)

old_header = content[header_start_idx:header_end_idx]
print("OLD HEADER FOUND:")
print(repr(old_header[:200]))

NEW_HEADER = """<div style="padding: 16px 20px 12px; background: #fff; border-bottom: 1px solid #e2e8f0;">
    <h2 style="margin: 0; font-size: 1.15rem; font-weight: 900; color: #1e293b;">Students by Grade &amp; Section</h2>
    <p style="margin: 2px 0 0; color: #94a3b8; font-size: 0.8rem;">Select a grade to filter, view, and export student data</p>
</div>"""

content = content[:header_start_idx] + NEW_HEADER + content[header_end_idx:]

# ── Step 2: Find where filter-card ends and insert conditional export buttons ──
# Look for the closing of the filter-card div
filter_end = "</div>\n\n{% if students %}"
if filter_end not in content:
    filter_end = "</div>\n{% if students %}"

if filter_end in content:
    EXPORT_BUTTONS = """</div>

{% if grade_filter %}
<div style="padding: 12px 20px; background: #f8fafc; border-bottom: 1px solid #e2e8f0; display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
    <span style="font-size: 0.8rem; color: #64748b; font-weight: 600;">Export {{ grade_filter }}{% if section_filter %} &mdash; {{ all_sections | selectattr('section_id', 'equalto', section_filter|int) | map(attribute='section_name') | first }}{% endif %}:</span>
    <button onclick="exportToExcel()" style="
        display: inline-flex; align-items: center; gap: 7px;
        padding: 8px 16px; border-radius: 10px; border: none; cursor: pointer;
        background: linear-gradient(135deg, #16a34a, #15803d);
        color: #fff; font-weight: 700; font-size: 0.83rem;
        box-shadow: 0 2px 6px rgba(22,163,74,0.3); transition: all 0.2s;
    " onmouseover="this.style.transform='translateY(-1px)';" onmouseout="this.style.transform='';">
        &#128202; Excel <span style="font-size:0.7rem; opacity:0.8;">per section</span>
    </button>
    <button onclick="exportToPDF()" style="
        display: inline-flex; align-items: center; gap: 7px;
        padding: 8px 16px; border-radius: 10px; border: none; cursor: pointer;
        background: linear-gradient(135deg, #dc2626, #b91c1c);
        color: #fff; font-weight: 700; font-size: 0.83rem;
        box-shadow: 0 2px 6px rgba(220,38,38,0.3); transition: all 0.2s;
    " onmouseover="this.style.transform='translateY(-1px)';" onmouseout="this.style.transform='';">
        &#128196; PDF
    </button>
</div>
{% endif %}

{% if students %}"""
    content = content.replace(filter_end, EXPORT_BUTTONS)
    print("Export buttons injected successfully.")
else:
    print(f"ERROR: Could not find filter_end marker. Trying alternatives...")
    # Try to find the end of filter-card differently
    idx = content.find("</div>\n\n{%")
    if idx != -1:
        print(f"Found at idx {idx}: " + repr(content[idx:idx+50]))

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print("Done! File updated successfully.")
