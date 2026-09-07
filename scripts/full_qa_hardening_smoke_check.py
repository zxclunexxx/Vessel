from pathlib import Path

root = Path(__file__).resolve().parents[1]
main = (root / 'src' / 'main.js').read_text(encoding='utf-8')
electron = (root / 'electron' / 'main.cjs').read_text(encoding='utf-8')

required_main = [
    "/* VESSEL_FULL_QA_HARDENING_V1 */",
    "if(['offline','не в сети'].includes(key))return 'Не в сети';",
    "stopSpeakingMeters();\n  syncCallUiTicker(false);\n  callStartedAt=0;",
    "overlay.setAttribute('role','dialog');",
    "overlay.setAttribute('aria-modal','true');",
    "document.addEventListener('keydown',onKeyDown,true);",
    "document.removeEventListener('keydown',onKeyDown,true);",
    "if(previousFocus?.isConnected&&typeof previousFocus.focus==='function')previousFocus.focus();",
]
for marker in required_main:
    if marker not in main:
        raise SystemExit(f'Missing Full QA runtime hardening marker: {marker}')

reset_start = main.find('function resetAuthenticatedRuntime()')
reset_end = main.find('async function cleanupAuthenticatedChannels', reset_start)
if reset_start < 0 or reset_end < 0:
    raise SystemExit('Authenticated runtime reset block not found')
reset_block = main[reset_start:reset_end]
for marker in ['stopSpeakingMeters();', 'syncCallUiTicker(false);', 'callStartedAt=0;']:
    if reset_block.count(marker) != 1:
        raise SystemExit(f'Runtime reset must contain exactly one {marker}')

if "if(['offline','не в сети'].includes(key))return 'Не в сети';" not in main:
    raise SystemExit('Offline presence label regression detected')

required_electron = [
    'contextIsolation: true',
    'nodeIntegration: false',
    'sandbox: true',
    "parsed.protocol === 'https:'",
    'setWindowOpenHandler',
    "webContents.on('will-navigate'",
    'setPermissionRequestHandler',
    'setPermissionCheckHandler',
]
for marker in required_electron:
    if marker not in electron:
        raise SystemExit(f'Electron release security invariant missing: {marker}')

for forbidden in ['service_role', 'SUPABASE_SERVICE_ROLE', 'TURN_SHARED_SECRET=']:
    if forbidden in main:
        raise SystemExit(f'Forbidden client-side secret marker detected: {forbidden}')

print('Full QA hardening smoke check passed')
