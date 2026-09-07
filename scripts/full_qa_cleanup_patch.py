from pathlib import Path

root = Path(__file__).resolve().parents[1]
main_path = root / 'src' / 'main.js'
text = main_path.read_text(encoding='utf-8')
marker = '/* VESSEL_FULL_QA_CLEANUP_V1 */'
if marker in text:
    print('Full QA cleanup patch already applied')
    raise SystemExit(0)

old = """function render() {\n  document.body.classList.remove('mobile-drawer-open');\n  document.querySelector('.mobile-drawer-scrim')?.remove();\n  document.body.classList.remove('mobile-drawer-open');\n"""
new = """function render() {\n  document.body.classList.remove('mobile-drawer-open');\n  document.querySelector('.mobile-drawer-scrim')?.remove();\n  /* VESSEL_FULL_QA_CLEANUP_V1 */\n"""
if old not in text:
    raise SystemExit('duplicate mobile drawer cleanup anchor not found')
text = text.replace(old, new, 1)
main_path.write_text(text, encoding='utf-8')
print('Removed duplicate Vessel mobile drawer cleanup')
