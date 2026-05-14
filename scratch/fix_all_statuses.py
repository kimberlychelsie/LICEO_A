import re

file_path = r"c:\Users\Maris Junterial\OneDrive\Documents\GitHub\LICEO_A\routes\registrar.py"
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Pattern to find status IN filters that only have approved/enrolled
# It matches both ('approved', 'enrolled') and ('approved','enrolled')
pattern = r"status\s+IN\s*\(\s*'approved'\s*,\s*'enrolled'\s*\)"

# The replacement
replacement = "status IN ('approved', 'enrolled', 'open_for_enrollment', 'completed')"

new_content, count = re.subn(pattern, replacement, content, flags=re.IGNORECASE)

if count > 0:
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"Replaced {count} occurrences.")
else:
    print("No occurrences found.")
