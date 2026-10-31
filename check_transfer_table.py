import ast

files = [
    'routes/registrar.py',
    'routes/branch_admin.py',
    'routes/teacher.py',
    'routes/student_portal.py',
]

bad_patterns = ['registrar_dashboard', 'branch_admin_dashboard', 'student_dashboard', 'teacher_dashboard_home']

all_ok = True
for f in files:
    src = open(f, encoding='utf-8').read()
    try:
        ast.parse(src)
        print(f'{f}: syntax OK')
    except SyntaxError as e:
        print(f'{f}: SYNTAX ERROR - {e}')
        all_ok = False

    lines = src.splitlines()
    for pat in bad_patterns:
        found = [i+1 for i, l in enumerate(lines) if pat in l and 'url_for' in l]
        if found:
            print(f'  WARNING: bad url_for ref "{pat}" at lines {found}')
            all_ok = False

print()
print('All clear!' if all_ok else 'Issues found above.')
