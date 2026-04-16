import codecs
import re

try:
    with codecs.open('registrar_theirs.html', 'r', 'utf-16le') as f:
        theirs = f.read()
except Exception:
    # Handle if git show wrote utf-8 initially
    with codecs.open('registrar_theirs.html', 'r', 'utf-8') as f:
        theirs = f.read()

with codecs.open('templates/registrar_dashboard.html', 'r', 'utf-8') as f:
    ours = f.read()

# EXTRACT logic from theirs
reject_modal_match = re.search(r'<!-- Reject Reason Modal -->.*?</form>\s*</div>\s*</div>\s*</div>', theirs, re.DOTALL)
reject_modal = reject_modal_match.group(0) if reject_modal_match else ''

inline_form_match = re.search(r'(<tr id=\"new-details-\{\{ enrollment\.enrollment_id \}\}\".*?</tr>)', theirs, re.DOTALL)
if inline_form_match:
    inline_form_html = inline_form_match.group(1).replace('enrollment.enrollment_id', 'e.enrollment_id').replace('enrollment.gender', 'e.gender').replace('enrollment.', 'e.')
else:
    inline_form_html = ''

# Also extract inline save button script
save_btn_script_match = re.search(r'// Enable inline save button only when changes exist \(per expanded form\).*?\}\);', theirs, re.DOTALL)
save_btn_script = save_btn_script_match.group(0) if save_btn_script_match else ''

# Replace action buttons in ours with the ones that trigger toggleNewDetails
ours = ours.replace(
    '<a href="/registrar/enrollment/{{ e.enrollment_id }}"\n                                        class="btn-elegant btn-view-modern">\n                                        <i class="fas fa-id-card"></i> Profile\n                                    </a>',
    '<button type="button" class="btn-elegant btn-view-modern" onclick="toggleNewDetails(\'{{ e.enrollment_id }}\', this)"><i class="fas fa-id-card"></i> Profile / Edit</button>\n<a href="/registrar/enrollment/{{ e.enrollment_id }}" class="btn-elegant btn-view-modern" style="margin-top:5px;"><i class="fas fa-external-link-alt"></i></a>'
)

ours = ours.replace(
    '''<form method="post" action="/registrar/enrollments" style="display:inline;">
                                        <input type="hidden" name="enrollment_id" value="{{ e.enrollment_id }}">
                                        <button name="action" value="rejected" class="btn-elegant btn-cross-modern"
                                            onclick="return confirm(\'Strictly reject this enrollment?\')"><i
                                                class="fas fa-ban"></i> Deny</button>
                                    </form>''',
    '''<button type="button" class="btn-elegant btn-cross-modern" onclick="openRejectModal(\'{{ e.enrollment_id }}\', \'{{ e.student_name|e }}\')"><i class="fas fa-ban"></i> Deny</button>'''
)

# Insert inline form directly after the row ending inside the loop. The loop is {% for e in new_enrollments %}
# We split the file around `{% else %}` for the new_enrollments loop, and insert the row right before `{% else %}`.
# Wait, safer way:
# Let's just find the `</tr>` before `{% else %}` block in the first table
new_table_part = ours.split('{% else %}')
new_table_part[0] = new_table_part[0] + inline_form_html + '\n                        '

ours = '{% else %}'.join(new_table_part)

# Add rejectModal before Scripts block
ours = ours.replace('{% block scripts %}', reject_modal + '\n{% block scripts %}')

# Add ToggleNewDetails script
js_funcs = '''
function toggleNewDetails(enrollmentId, btn) {
    const row = document.getElementById('new-details-' + enrollmentId);
    if (!row) return;
    const isOpen = row.style.display !== 'none';
    row.style.display = isOpen ? 'none' : '';
    if (btn) btn.innerHTML = isOpen ? '<i class=\"fas fa-id-card\"></i> Profile / Edit' : '<i class=\"fas fa-times\"></i> Set Form';
}

function openRejectModal(enrollmentId, studentName) {
    const modal = document.getElementById('rejectModal');
    document.getElementById('rejectEnrollmentId').value = enrollmentId;
    document.getElementById('rejectStudentName').textContent = studentName || '';
    const reason = document.getElementById('rejectReason');
    reason.value = '';
    modal.style.display = 'block';
    setTimeout(() => reason.focus(), 0);
}
function closeRejectModal() {
    document.getElementById('rejectModal').style.display = 'none';
}

''' + save_btn_script + '''
'''

ours = ours.replace('// Roster Filtering', js_funcs + '\n    // Roster Filtering')

# Modify the tab logic to also use `newSearch` and `newGradeFilter` if possible, but the python code is injecting correctly so the DOM exists. Wait, I didn't inject newSearch and newGradeFilter into the DOM itself yet. 
# We'll do that manually later.

with codecs.open('templates/registrar_dashboard.html', 'w', 'utf-8') as f:
    f.write(ours)

print('Success merge')
