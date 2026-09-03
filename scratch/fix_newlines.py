import glob
import os

files = glob.glob('templates/*shs*.html')
for file in files:
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace literal `n with actual newline
    content = content.replace('`n    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">', '\n    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">')
    
    with open(file, 'w', encoding='utf-8') as f:
        f.write(content)
