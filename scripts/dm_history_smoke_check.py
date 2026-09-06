from pathlib import Path

main = Path('src/main.js').read_text(encoding='utf-8')

old = "if(activeDmId===friendId){activeDmId=null;currentDm=null;dmMessages=[];window.__vesselDmLoaded=false;}"
if old in main:
    raise SystemExit('Unfriend must not discard an open historical DM')

start = main.find("document.querySelectorAll('[data-remove-friend]')")
if start < 0:
    raise SystemExit('Missing remove-friend lifecycle handler')
block = main[start:start + 1800]

required = [
    'const keepActiveHistory=activeDmId===friendId;',
    'window.__vesselDmThreadsLoaded=false;',
    'await Promise.all([syncSocial(user),syncDmThreads(user)]);',
    'if(keepActiveHistory&&activeDmId===friendId)await loadDirectMessages(user,friendId);else render();',
]
for marker in required:
    if marker not in block:
        raise SystemExit(f'Missing read-only DM history lifecycle marker: {marker}')

if 'activeDmId=null;currentDm=null;dmMessages=[]' in block:
    raise SystemExit('Remove-friend handler still clears the active historical DM')

print('Vessel DM history lifecycle smoke check passed')
