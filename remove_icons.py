import re

filepath = r"c:\Users\Maris Junterial\OneDrive\Documents\GitHub\LICEO_A\templates\branch_admin_dashboard.html"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# Replace <i class="fas ..."></i> with empty string
new_content = re.sub(r'<i class="fas [^"]+"[^>]*></i>\s*', '', content)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(new_content)

print("Replaced!")
