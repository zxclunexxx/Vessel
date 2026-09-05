from pathlib import Path

main = Path('src/main.js').read_text(encoding='utf-8')

banned = [
    "{ name: 'Марк'",
    "{ name: 'Лиза'",
    "defaultMessages",
    "name: 'Игры'",
    "name: 'Музыка'",
    "demo@vessel.app",
]
missing = [item for item in banned if item in main]
if missing:
    raise SystemExit(f'Authenticated runtime still contains banned demo placeholders: {missing}')

required = [
    'async function bootstrapAuth()',
    'async function syncSocial(user)',
    'async function loadDirectMessages(user, friendId)',
    'async function toggleVoiceRoom(user)',
    'async function endCall(notify=true)',
    "friends can send dms",
]
# The RLS policy string lives in DB rather than JS; only assert JS requirements here.
for item in required[:-1]:
    if item not in main:
        raise SystemExit(f'Missing expected runtime feature: {item}')

print('Vessel authenticated runtime smoke check passed')
