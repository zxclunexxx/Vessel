from pathlib import Path

path = Path('src/style.css')
text = path.read_text(encoding='utf-8')
old = 'transition: transform var(--normal, 220ms) var(--v-ease-spring);'
new = 'transition: transform var(--v-normal) var(--v-ease-spring);'

if new in text:
    print('Vessel mobile motion token already normalized')
    raise SystemExit(0)
if text.count(old) != 1:
    raise SystemExit(f'Expected exactly one legacy mobile motion token, found {text.count(old)}')

path.write_text(text.replace(old, new, 1), encoding='utf-8')
print('Normalized Vessel mobile drawer transition to --v-normal')
