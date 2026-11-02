src = open('templates/base.html', encoding='utf-8').read()
lines = src.splitlines()
results = []
for i, line in enumerate(lines, 1):
    if ('Student Transfer' in line or 'Enrollment' in line or
        'pending' in line.lower() or 'badge' in line.lower() or
        'transfer' in line.lower() or 'pending_transfer' in line.lower()):
        results.append(f'{i}: {line.strip()[:130]}')
print('\n'.join(results[:60]))
