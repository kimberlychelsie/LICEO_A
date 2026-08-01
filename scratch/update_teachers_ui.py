import re

with open('templates/branch_admin_manage_teachers.html', 'r', encoding='utf-8') as f:
    html = f.read()

replacement = '''<div class="ma-container">
    <header class="premium-header">
        <h1>Account <span>Management</span></h1>
        <p>Manage school accounts and user access for {{ session.get('branch_name', 'Liceo LMS') }}</p>
    </header>

    <div class="main-tabs-container" style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 32px;">
        <a href="{{ url_for('branch_admin.branch_admin_manage_accounts', role='all_staff') }}" class="main-tab active" style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 24px; border-radius: 20px; text-decoration: none; border: 2px solid var(--ma-primary); background: rgba(15, 23, 42, 0.05); color: var(--ma-primary); box-shadow: var(--ma-shadow); transition: all 0.2s;">
            <div style="font-weight: 800; font-size: 1.1rem; margin-bottom: 8px; letter-spacing: 0.5px;">STAFF MANAGEMENT TAB</div>
            <div style="font-size: 0.9rem; font-weight: 600; opacity: 0.8;">➕ Create Staff Account</div>
        </a>
        <a href="{{ url_for('branch_admin.branch_admin_manage_accounts', role='student') }}" class="main-tab" style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 24px; border-radius: 20px; text-decoration: none; border: 2px solid transparent; background: var(--ma-card); color: var(--ma-text); box-shadow: var(--ma-shadow); transition: all 0.2s;">
            <div style="font-weight: 800; font-size: 1.1rem; margin-bottom: 8px; letter-spacing: 0.5px;">STUDENT DIRECTORY TAB</div>
            <div style="font-size: 0.9rem; font-weight: 600; opacity: 0.8;">🎓 View Student Records</div>
        </a>
    </div>

    <!-- Create Account Section -->
    {% if not filter_search %}
    <div class="data-card" style="margin-bottom: 32px;">
        <h2 style="font-size: 1.25rem; font-weight: 800; margin-bottom: 24px; color: var(--ma-primary);">Create New Staff Account</h2>
        <form method="post" action="/branch-admin/manage-teachers" id="teacher-form">
            <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
            <input type="hidden" name="role" value="teacher">
            
            <div class="form-group" style="margin-bottom: 24px;">
                <label style="font-weight: 700; margin-bottom: 12px; display: block; color: var(--ma-text);">Select Role:</label>
                <div style="display: flex; gap: 24px; flex-wrap: wrap; background: #f8fafc; padding: 16px; border-radius: 12px; border: 1px solid var(--ma-border);">
                    <label style="display: flex; align-items: center; gap: 8px; cursor: pointer; font-weight: 600;" onchange="window.location.href='/branch-admin/manage-accounts?role=registrar';">
                        <input type="radio" name="role_redirect" value="registrar" style="width: 18px; height: 18px; accent-color: var(--ma-primary);"> Registrar
                    </label>
                    <label style="display: flex; align-items: center; gap: 8px; cursor: pointer; font-weight: 600;" onchange="window.location.href='/branch-admin/manage-accounts?role=cashier';">
                        <input type="radio" name="role_redirect" value="cashier" style="width: 18px; height: 18px; accent-color: var(--ma-primary);"> Cashier
                    </label>
                    <label style="display: flex; align-items: center; gap: 8px; cursor: pointer; font-weight: 600;" onchange="window.location.href='/branch-admin/manage-accounts?role=librarian';">
                        <input type="radio" name="role_redirect" value="librarian" style="width: 18px; height: 18px; accent-color: var(--ma-primary);"> Librarian
                    </label>
                    <label style="display: flex; align-items: center; gap: 8px; cursor: pointer; font-weight: 600;">
                        <input type="radio" name="role_redirect" value="teacher" checked required style="width: 18px; height: 18px; accent-color: var(--ma-primary);"> Teacher
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
                <div class="form-group">
                    <label>Academic Grade Level</label>
                    <select class="form-control" name="grade_level" required>
                        <option value="">Select Level</option>
                        {% for g in grades %}
                        <option value="{{ g.id }}">{{ g.name }}</option>
                        {% endfor %}
                    </select>
                </div>
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
            <div class="form-group" style="flex: 2; min-width: 300px;">
                <label>Find teacher</label>
                <div style="position: relative;">
                    <input type="text" name="search" class="form-control" placeholder="Type part of a name or username..." value="{{ filter_search }}" style="padding-left: 16px;">
                </div>
            </div>
            
            <div class="form-group" style="display: flex; gap: 8px;">
                <button type="submit" class="btn-elegant btn-primary-ma" style="width: 64px; padding: 0;">
                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="11" cy="11" r="8"></circle>
                        <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                    </svg>
                </button>
                <a href="/branch-admin/manage-teachers/archive" class="btn-elegant" style="background: #ffffff; border: 1.5px solid var(--ma-border); color: var(--ma-muted); text-decoration: none; padding: 0 20px;">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 8px;">
                        <rect width="20" height="5" x="2" y="3" rx="1"></rect>
                        <path d="M4 8v11a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8"></path>
                        <path d="M10 12h4"></path>
                    </svg>
                    Archived Teachers
                </a>
            </div>
        </form>

        <div class="nav-tabs-container" style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 0;">
            <div style="font-weight: 700; font-size: 0.95rem; color: var(--ma-muted); align-self: center; margin-right: 12px;">Filter by Role:</div>
            <a href="{{ url_for('branch_admin.branch_admin_manage_accounts', role='all_staff') }}" class="nav-tab">All Staff</a>
            <a href="{{ url_for('branch_admin.branch_admin_manage_accounts', role='registrar') }}" class="nav-tab">Registrars</a>
            <a href="{{ url_for('branch_admin.branch_admin_manage_accounts', role='cashier') }}" class="nav-tab">Cashiers</a>
            <a href="{{ url_for('branch_admin.branch_admin_manage_accounts', role='librarian') }}" class="nav-tab">Librarians</a>
            <a href="/branch-admin/manage-teachers" class="nav-tab active">Teachers</a>
        </div>
    </div>

    <!-- Table -->
    <div class="table-wrap">
'''

# First, replace <div class="wrap"> with <div class="ma-container">
html = html.replace('<div class="wrap">', '<div class="ma-container">')

# Then replace from <!-- Account Role Navigation Tabs --> to <!-- Table -->
import re
new_html = re.sub(r'<!-- Account Role Navigation Tabs -->.*?<!-- Table -->\s*<div class="table-wrap">', replacement, html, flags=re.DOTALL)

with open('templates/branch_admin_manage_teachers.html', 'w', encoding='utf-8') as f:
    f.write(new_html)

print("Updated UI layout for teachers")
