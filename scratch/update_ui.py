import re

with open('templates/branch_admin_manage_accounts.html', 'r', encoding='utf-8') as f:
    html = f.read()

new_ma_container = '''<div class="ma-container">
    <header class="premium-header">
        <h1>Account <span>Management</span></h1>
        <p>Manage school accounts and user access for {{ session.get('branch_name', 'Liceo LMS') }}</p>
    </header>

    <div class="main-tabs-container" style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 32px;">
        <a href="?role=all_staff" class="main-tab {% if role_filter != 'student' %}active{% endif %}" style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 24px; border-radius: 20px; text-decoration: none; border: 2px solid {% if role_filter != 'student' %}var(--ma-primary){% else %}transparent{% endif %}; background: {% if role_filter != 'student' %}rgba(15, 23, 42, 0.05){% else %}var(--ma-card){% endif %}; color: {% if role_filter != 'student' %}var(--ma-primary){% else %}var(--ma-text){% endif %}; box-shadow: var(--ma-shadow); transition: all 0.2s;">
            <div style="font-weight: 800; font-size: 1.1rem; margin-bottom: 8px; letter-spacing: 0.5px;">STAFF MANAGEMENT TAB</div>
            <div style="font-size: 0.9rem; font-weight: 600; opacity: 0.8;">➕ Create Staff Account</div>
        </a>
        <a href="?role=student" class="main-tab {% if role_filter == 'student' %}active{% endif %}" style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 24px; border-radius: 20px; text-decoration: none; border: 2px solid {% if role_filter == 'student' %}var(--ma-primary){% else %}transparent{% endif %}; background: {% if role_filter == 'student' %}rgba(15, 23, 42, 0.05){% else %}var(--ma-card){% endif %}; color: {% if role_filter == 'student' %}var(--ma-primary){% else %}var(--ma-text){% endif %}; box-shadow: var(--ma-shadow); transition: all 0.2s;">
            <div style="font-weight: 800; font-size: 1.1rem; margin-bottom: 8px; letter-spacing: 0.5px;">STUDENT DIRECTORY TAB</div>
            <div style="font-size: 0.9rem; font-weight: 600; opacity: 0.8;">🎓 View Student Records</div>
        </a>
    </div>

    <!-- Create Account Section -->
    {% if is_branch_active_status and role_filter != 'student' %}
    <div class="data-card" style="margin-bottom: 32px;">
        <h2 style="font-size: 1.25rem; font-weight: 800; margin-bottom: 24px; color: var(--ma-primary);">Create New Staff Account</h2>
        <form method="post" action="{{ url_for('branch_admin.branch_admin_manage_accounts') }}">
            <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
            
            <div class="form-group" style="margin-bottom: 24px;">
                <label style="font-weight: 700; margin-bottom: 12px; display: block; color: var(--ma-text);">Select Role:</label>
                <div style="display: flex; gap: 24px; flex-wrap: wrap; background: #f8fafc; padding: 16px; border-radius: 12px; border: 1px solid var(--ma-border);">
                    <label style="display: flex; align-items: center; gap: 8px; cursor: pointer; font-weight: 600;">
                        <input type="radio" name="role" value="registrar" {% if role_filter=='registrar' or role_filter=='all_staff' %}checked{% endif %} required style="width: 18px; height: 18px; accent-color: var(--ma-primary);"> Registrar
                    </label>
                    <label style="display: flex; align-items: center; gap: 8px; cursor: pointer; font-weight: 600;">
                        <input type="radio" name="role" value="cashier" {% if role_filter=='cashier' %}checked{% endif %} style="width: 18px; height: 18px; accent-color: var(--ma-primary);"> Cashier
                    </label>
                    <label style="display: flex; align-items: center; gap: 8px; cursor: pointer; font-weight: 600;">
                        <input type="radio" name="role" value="librarian" {% if role_filter=='librarian' %}checked{% endif %} style="width: 18px; height: 18px; accent-color: var(--ma-primary);"> Librarian
                    </label>
                    <label style="display: flex; align-items: center; gap: 8px; cursor: pointer; font-weight: 600;" onchange="window.location.href='/branch-admin/manage-teachers';">
                        <input type="radio" name="role" value="teacher" {% if role_filter=='teacher' %}checked{% endif %} style="width: 18px; height: 18px; accent-color: var(--ma-primary);"> Teacher
                    </label>
                </div>
            </div>

            <div class="form-row">
                <div class="form-group">
                    <label>First Name</label>
                    <input type="text" class="form-control" name="first_name" placeholder="E.g. Alexander" required oninput="this.value = this.value.replace(/[0-9]/g, '')">
                </div>
                <div class="form-group">
                    <label>Middle Name (Optional)</label>
                    <input type="text" class="form-control" name="middle_name" placeholder="E.g. Pierce" oninput="this.value = this.value.replace(/[0-9]/g, '')">
                </div>
                <div class="form-group">
                    <label>Last Name</label>
                    <input type="text" class="form-control" name="last_name" placeholder="E.g. Mercer" required oninput="this.value = this.value.replace(/[0-9]/g, '')">
                </div>
                <div class="form-group">
                    <label>Gender Profile</label>
                    <select class="form-control" name="gender" required>
                        <option value="">Select Gender</option>
                        <option value="female">Female</option>
                        <option value="male">Male</option>
                    </select>
                </div>
            </div>

            <div class="form-row">
                <div class="form-group" style="flex: 2;">
                    <label>Email Address</label>
                    <input class="form-control" name="email" type="email" placeholder="example@domain.com" required>
                </div>
                
                <div class="form-group" style="align-self: flex-end;">
                    <button class="btn-elegant btn-primary-ma" type="submit" style="width: 100%; height: 46px; font-weight: 700;">
                        <span>➕ Create Account</span>
                    </button>
                </div>
            </div>
        </form>
    </div>
    {% endif %}

    <!-- Controls Wrapper: Navigation & Search -->
    <div class="controls-wrapper">
        <h2 style="font-size: 1.25rem; font-weight: 800; margin-bottom: 24px; color: var(--ma-primary);">USER DIRECTORY</h2>
        
        <form method="get" class="search-registry-bar" id="filter-form" style="margin-bottom: 24px;">
            <input type="hidden" name="role" value="{{ role_filter }}">
            <div class="form-group" style="flex: 2; min-width: 300px;">
                <label>Search Accounts</label>
                <div style="position: relative;">
                    <input type="text" name="search" class="form-control" placeholder="Filter by name, ID or username..." value="{{ filter_search }}" style="padding-left: 16px;">
                </div>
            </div>
            {% if role_filter in ['student', 'teacher'] %}
            <div class="form-group">
                <label>Grade Level</label>
                <select name="grade" class="form-control" onchange="this.form.submit()">
                    <option value="">All Levels</option>
                    {% if role_filter == 'student' %}
                    {% set unique_grades = [] %}
                    {% for s in section_options %}{% if s.grade_level_name not in unique_grades %}{% set _ = unique_grades.append(s.grade_level_name) %}{% endif %}{% endfor %}
                    {% for gname in unique_grades|sort %}
                    <option value="{{ gname }}" {% if filter_grade==gname %}selected{% endif %}>{{ gname }}</option>
                    {% endfor %}
                    {% else %}
                    {% for g in grades %}
                    <option value="{{ g.id }}" {% if filter_grade==g.id|string %}selected{% endif %}>{{ g.name }}</option>
                    {% endfor %}
                    {% endif %}
                </select>
            </div>
            <div class="form-group">
                <label>Section</label>
                <select name="section" class="form-control" onchange="this.form.submit()">
                    <option value="">All Sections</option>
                    {% for s in section_options %}
                    <option value="{{ s.section_id }}" {% if filter_section==s.section_id|string %}selected{% endif %}>
                        {{ s.grade_level_name }} - {{ s.section_name }}
                    </option>
                    {% endfor %}
                </select>
            </div>
            {% endif %}
            <div class="form-group" style="display: flex; gap: 8px;">
                <button type="submit" class="btn-elegant btn-primary-ma" style="width: 64px; padding: 0;">
                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="11" cy="11" r="8"></circle>
                        <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                    </svg>
                </button>
                {% if role_filter in ['student', 'teacher'] %}
                {% if view_mode == 'grouped' %}
                <a href="?role={{ role_filter }}" class="btn-elegant" style="background: #ffffff; border: 1.5px solid var(--ma-border); color: var(--ma-muted); text-decoration: none; padding: 0 20px;">Default View</a>
                {% else %}
                <a href="?role={{ role_filter }}&view=grouped" class="btn-elegant" style="background: #f1f5f9; color: var(--ma-primary); text-decoration: none; padding: 0 20px;">Group View</a>
                {% endif %}
                {% endif %}
            </div>
        </form>

        <div class="nav-tabs-container" style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 0;">
            <div style="font-weight: 700; font-size: 0.95rem; color: var(--ma-muted); align-self: center; margin-right: 12px;">Filter by Role:</div>
            {% if role_filter != 'student' %}
            <a href="?role=all_staff" class="nav-tab {% if role_filter == 'all_staff' %}active{% endif %}">All Staff</a>
            <a href="?role=registrar" class="nav-tab {% if role_filter == 'registrar' %}active{% endif %}">Registrars</a>
            <a href="?role=cashier" class="nav-tab {% if role_filter == 'cashier' %}active{% endif %}">Cashiers</a>
            <a href="?role=librarian" class="nav-tab {% if role_filter == 'librarian' %}active{% endif %}">Librarians</a>
            <a href="/branch-admin/manage-teachers" class="nav-tab {% if role_filter == 'teacher' %}active{% endif %}">Teachers</a>
            {% else %}
            <a href="?role=student" class="nav-tab active">Students</a>
            {% endif %}
        </div>
    </div>

    <!-- Results Table -->
    <div class="table-mount">
        {% if accounts %}
        <div style="overflow-x: auto;">
            {% if view_mode == 'grouped' %}
            {# --- GROUPED VIEW --- #}
            {% if role_filter == 'student' %}
            {% for grade, students in accounts|groupby('grade_level') %}
            <div class="group-header">
                {{ grade or 'Unassigned Grade' }} <span>{{ students|length }} Students</span>
            </div>
            {{ render_account_table(students, role_filter, is_branch_active_status) }}
            {% endfor %}
            {% elif role_filter == 'teacher' %}
            {% for section, teachers in accounts|groupby('section_name') %}
            <div class="group-header">
                {{ section or 'Unassigned Section' }} <span>{{ teachers|length }} Teachers</span>
            </div>
            {{ render_account_table(teachers, role_filter, is_branch_active_status) }}
            {% endfor %}
            {% endif %}
            {% else %}
            {# --- FLAT VIEW --- #}
            {{ render_account_table(accounts, role_filter, is_branch_active_status) }}
            {% endif %}
        </div>
        {% else %}
        <div style="text-align: center; padding: 100px 48px; color: var(--ma-muted);">
            <div style="font-size: 5rem; margin-bottom: 32px; opacity: 0.2; display: flex; justify-content: center;">
                <svg xmlns="http://www.w3.org/2000/svg" width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
                </svg>
            </div>
            <h3 style="font-weight: 900; color: var(--ma-primary); font-size: 1.5rem; margin-bottom: 12px;">No Accounts Found</h3>
            <p style="font-weight: 600; font-size: 1.1rem;">The registry contains no records matching your current selected filters.</p>
        </div>
        {% endif %}
    </div>
</div>'''

new_html = re.sub(r'<div class="ma-container">.*{% endblock %}', new_ma_container + '\n\n{% endblock %}', html, flags=re.DOTALL)

with open('templates/branch_admin_manage_accounts.html', 'w', encoding='utf-8') as f:
    f.write(new_html)

print('Updated UI layout')
