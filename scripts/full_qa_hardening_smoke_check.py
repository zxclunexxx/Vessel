from pathlib import Path

root = Path(__file__).resolve().parents[1]
main = (root / 'src' / 'main.js').read_text(encoding='utf-8')
electron = (root / 'electron' / 'main.cjs').read_text(encoding='utf-8')

required_main = [
    "/* VESSEL_FULL_QA_HARDENING_V1 */",
    "/* VESSEL_FULL_QA_INTERACTION_PERF_V1 */",
    "/* VESSEL_FULL_QA_CLEANUP_V1 */",
    "if(['offline','не в сети'].includes(key))return 'Не в сети';",
    "overlay.setAttribute('role','dialog');",
    "overlay.setAttribute('aria-modal','true');",
    "document.addEventListener('keydown',onKeyDown,true);",
    "document.removeEventListener('keydown',onKeyDown,true);",
    "if(previousFocus?.isConnected&&typeof previousFocus.focus==='function')previousFocus.focus();",
    "let rtcVisualRuntimeTicker = null;",
    "function rtcVisualRuntimeActive()",
    "function syncRtcVisualRuntimeTicker(active=rtcVisualRuntimeActive())",
    "modal.setAttribute('role','dialog');",
    "modal.setAttribute('aria-modal','true');",
]
for marker in required_main:
    if marker not in main:
        raise SystemExit(f'Missing Full QA runtime hardening marker: {marker}')

reset_start = main.find('function resetAuthenticatedRuntime()')
reset_end = main.find('async function cleanupAuthenticatedChannels', reset_start)
if reset_start < 0 or reset_end < 0:
    raise SystemExit('Authenticated runtime reset block not found')
reset_block = main[reset_start:reset_end]
for marker in ['stopSpeakingMeters();', 'syncCallUiTicker(false);', 'syncRtcVisualRuntimeTicker(false);', 'callStartedAt=0;']:
    if reset_block.count(marker) != 1:
        raise SystemExit(f'Runtime reset must contain exactly one {marker}')

render_start = main.find('function render() {')
render_end = main.find('  const previousMessagesPane=', render_start)
if render_start < 0 or render_end < 0:
    raise SystemExit('Render cleanup block not found')
render_prefix = main[render_start:render_end]
if render_prefix.count("document.body.classList.remove('mobile-drawer-open');") != 1:
    raise SystemExit('Render must clear mobile drawer body state exactly once')
if render_prefix.count("document.querySelector('.mobile-drawer-scrim')?.remove();") != 1:
    raise SystemExit('Render must clear mobile drawer scrim exactly once')

if "document.querySelector('.channels')?.classList.remove('mobile-open');" in main:
    raise SystemExit('Legacy mobile drawer close bypass still exists')
if main.count('setMobileDrawerOpen(false);') < 3:
    raise SystemExit('Unified mobile drawer close lifecycle is not used by all navigation paths')

legacy_global_rtc_poll = "setInterval(()=>{\n  const callStage=document.querySelector('[data-call-stage]');"
if legacy_global_rtc_poll in main:
    raise SystemExit('Legacy always-on 500ms RTC polling loop still exists')

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
