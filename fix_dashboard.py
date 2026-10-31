"""
Inserts safe-default variable declarations before the `try:` block in dashboard()
so that announcements_list / grades / recent_grade_requests are always defined
even when the DB block raises early (preventing NameError → "Something went wrong").
"""
import re

path = 'routes/branch_admin.py'
src = open(path, encoding='utf-8').read()

# The exact anchor we're looking for inside dashboard()
OLD = (
    "    db = get_db_connection()\n"
    "    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)\n"
    "\n"
    "    try:\n"
)

NEW = (
    "    db = get_db_connection()\n"
    "    cursor = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)\n"
    "\n"
    "    # Safe defaults — always defined even if the DB block raises early\n"
    "    announcements_list = []\n"
    "    grades = []\n"
    "    recent_grade_requests = []\n"
    "\n"
    "    try:\n"
)

# Normalise the source to LF just for the search, then work on bytes
src_lf = src.replace('\r\n', '\n')

if OLD not in src_lf:
    print("ERROR: anchor not found — file may have already been patched or changed.")
else:
    count = src_lf.count(OLD)
    print(f"Found {count} occurrence(s) of anchor.")
    patched_lf = src_lf.replace(OLD, NEW, 1)  # only first occurrence (in dashboard)
    # Write back preserving original line endings style (keep \n, Railway doesn't care)
    open(path, 'w', encoding='utf-8', newline='\n').write(patched_lf)
    print("Patch applied successfully.")

    # Verify syntax
    import ast
    ast.parse(patched_lf)
    print("Syntax OK.")
