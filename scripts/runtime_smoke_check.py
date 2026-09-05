from pathlib import Path

main = Path('src/main.js').read_text(encoding='utf-8')

banned = [
    "Марк",
    "Лиза",
    "defaultMessages",
    "name: 'Игры'",
    "name: 'Музыка'",
    "demo@vessel.app",
    "prompt(",
    "confirm(",
    "alert(",
]
found = [item for item in banned if item in main]
if found:
    raise SystemExit(f'Authenticated runtime contains banned prototype behavior: {found}')

required = [
    'async function bootstrapAuth()',
    'async function syncSocial(user)',
    'async function loadDirectMessages(user, friendId)',
    'async function toggleVoiceRoom(user)',
    'async function endCall(notify=true)',
    "supabase.functions.invoke('search-user'",
    "supabase.functions.invoke('join-server'",
    'function vesselDialog(',
    'function vesselListDialog(',
    'function vesselCodeDialog(',
    'function escapeHtml(',
    'callInviteTimer',
    'vessel-memberships-',
    'vessel-channels-',
    'data-remove-friend',
    'id="mobile-nav"',
    "createSignedUrl(path,60)",
    "activeChannelName = 'нет каналов'",
]
for item in required:
    if item not in main:
        raise SystemExit(f'Missing expected runtime feature: {item}')

# Keep the authenticated UI backed by database identities, not fake fallback people.
if "savedUser = JSON.parse(localStorage.getItem('vesselUser')" in main:
    raise SystemExit('Runtime must not trust a cached localStorage user as an authenticated session')

print('Vessel authenticated runtime smoke check passed')
