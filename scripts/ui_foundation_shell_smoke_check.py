from pathlib import Path

style = Path('src/style.css').read_text(encoding='utf-8')
required = [
    '/* VESSEL_UI_FOUNDATION_SHELL_V1 */',
    '--v-bg-0:',
    '--v-cyan:',
    '--v-violet:',
    '--v-radius-panel:',
    '--v-ease-spring:',
    'body::after {',
    '.servers,\n.channels,\n.chat,\n.members {',
    '.server.selected::before { height: 26px; opacity: 1; }',
    '.channel.active::before { height: 22px; opacity: 1; }',
    '.user-card {',
    'order: 20;',
    '.chat-head {',
    '.composer:focus-within {',
    'button:focus-visible,',
    'transition: transform var(--v-normal) var(--v-ease-spring);',
    '.channels.mobile-open { transform: translateX(0); }',
    '@media (prefers-reduced-motion: reduce)',
]
missing = [marker for marker in required if marker not in style]
if missing:
    raise SystemExit('Missing Vessel UI foundation markers: ' + ', '.join(missing))

if style.count('/* VESSEL_UI_FOUNDATION_SHELL_V1 */') != 1:
    raise SystemExit('Vessel UI foundation marker must be unique')

if 'var(--normal, 220ms)' in style:
    raise SystemExit('Legacy mobile motion fallback bypasses the shared --v-normal token')

if 'animation-iteration-count: 1!important;' not in style:
    raise SystemExit('Reduced-motion override must stop repeated animations')

if 'TURN_SHARED_SECRET' in style or 'SUPABASE_SERVICE_ROLE_KEY' in style:
    raise SystemExit('Visual stylesheet must never contain backend secrets')

print('Vessel liquid-glass UI foundation smoke check passed')
