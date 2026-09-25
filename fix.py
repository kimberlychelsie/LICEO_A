
with open('templates/registrar_students_by_grade.html', 'r', encoding='utf-8') as f:
    content = f.read()

import re
target = r'(</div>\s*</div>\s*</div>\s*<div style=\x22grid-column: 1 / -1; margin-top: 10px;\x22>)'
match = re.search(target, content)
if match:
    replacement = '</div>\n                                        </div>\n                                    </div>\n                                </div>\n                            </div>\n                            <div style=\x22grid-column: 1 / -1; margin-top: 10px;\x22>'
    content = content[:match.start()] + replacement + content[match.end():]
    with open('templates/registrar_students_by_grade.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Replaced')
else:
    print('Not found')

