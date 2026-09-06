from pathlib import Path

path = Path('src/main.js')
text = path.read_text(encoding='utf-8')
changed = False

old = """    if(activeDmId===friendId){activeDmId=null;currentDm=null;dmMessages=[];window.__vesselDmLoaded=false;}
    window.__vesselSocialLoaded=false;await syncSocial(user);render();
"""
new = """    const keepActiveHistory=activeDmId===friendId;
    if(keepActiveHistory)window.__vesselDmLoaded=false;
    window.__vesselSocialLoaded=false;
    window.__vesselDmThreadsLoaded=false;
    await Promise.all([syncSocial(user),syncDmThreads(user)]);
    if(keepActiveHistory&&activeDmId===friendId)await loadDirectMessages(user,friendId);else render();
"""

if new in text:
    print('Read-only DM history after unfriend already preserved; nothing to change')
elif old in text:
    text = text.replace(old, new, 1)
    changed = True
else:
    raise SystemExit('unfriend DM history anchor not found')

for marker in [
    'const keepActiveHistory=activeDmId===friendId;',
    'window.__vesselDmThreadsLoaded=false;',
    'await Promise.all([syncSocial(user),syncDmThreads(user)]);',
    'if(keepActiveHistory&&activeDmId===friendId)await loadDirectMessages(user,friendId);else render();',
]:
    if marker not in text:
        raise SystemExit(f'missing DM unfriend history marker: {marker}')

if 'if(activeDmId===friendId){activeDmId=null;currentDm=null;dmMessages=[];window.__vesselDmLoaded=false;}' in text:
    raise SystemExit('active DM is still discarded after unfriend')

if changed:
    path.write_text(text, encoding='utf-8')
    print('Applied read-only DM history lifecycle after unfriend')
