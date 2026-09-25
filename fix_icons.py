
with open('templates/registrar_students_by_grade.html', 'r', encoding='utf-8') as f:
    content = f.read()

import re

# Personal & Contact Information (SVG replace with 1)
content = re.sub(
    r'<svg[^>]+xmlns=\x22http://www\.w3\.org/2000/svg\x22[^>]+>.*?</svg>\s*Personal & Contact Information',
    '<div style=\x22width: 32px; height: 32px; background: #eff6ff; color: #1e40af; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 14px;\x22>1</div>\n                                        Personal & Contact Information',
    content,
    flags=re.DOTALL
)

# Academic Records (SVG replace with 2)
content = re.sub(
    r'<svg[^>]+xmlns=\x22http://www\.w3\.org/2000/svg\x22[^>]+>.*?</svg>\s*Academic Records & Documents',
    '<div style=\x22width: 32px; height: 32px; background: #eff6ff; color: #1e40af; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 14px;\x22>2</div>\n                                        Academic Records & Documents',
    content,
    flags=re.DOTALL
)

# Parent & Guardian (SVG replace with 3)
content = re.sub(
    r'<svg[^>]+xmlns=\x22http://www\.w3\.org/2000/svg\x22[^>]+>.*?</svg>\s*Parent & Guardian Information',
    '<div style=\x22width: 32px; height: 32px; background: #eff6ff; color: #1e40af; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 14px;\x22>3</div>\n                                        Parent & Guardian Information',
    content,
    flags=re.DOTALL
)

with open('templates/registrar_students_by_grade.html', 'w', encoding='utf-8') as f:
    f.write(content)

