from pathlib import Path

main = Path('src/main.js').read_text(encoding='utf-8')
markers = [
    'const requests=existing||[];',
    "const pending=requests.find(request=>request.status==='pending');",
    'const outgoing=requests.find(request=>request.sender_id===user.id&&request.receiver_id===target.id);',
    "['accepted','declined','cancelled'].includes(outgoing.status)",
    ".in('status',['accepted','declined','cancelled'])",
]
for marker in markers:
    if marker not in main:
        raise SystemExit(f'missing friend request retry marker: {marker}')

legacy = ".or(`and(sender_id.eq.${user.id},receiver_id.eq.${target.id}),and(sender_id.eq.${target.id},receiver_id.eq.${user.id})`).limit(1)"
if legacy in main:
    raise SystemExit('friend request lookup still picks an arbitrary single historical direction')
if "['declined','cancelled'].includes(request.status)" in main:
    raise SystemExit('legacy retry path still excludes accepted requests')

print('Friend request retry client smoke check passed')
