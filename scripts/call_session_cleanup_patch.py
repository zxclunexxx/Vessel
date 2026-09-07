from pathlib import Path

# Session reset must clear all ICE-recovery state so a new login cannot inherit a stale call timer.
path = Path('src/main.js')
text = path.read_text(encoding='utf-8')
changed = False

start = text.find('function resetAuthenticatedRuntime()')
end = text.find('async function', start)
if start < 0:
    raise SystemExit('resetAuthenticatedRuntime not found')
if end < 0:
    end = len(text)
block = text[start:end]
required = [
    'callInitiator=false;',
    'callIceRestartAttempts=0;',
    'callIceRestartInFlight=false;',
    'clearCallDisconnectTimer();',
]
if all(marker in block for marker in required):
    print('Call recovery session cleanup already applied; nothing to change')
    raise SystemExit(0)

old = '''  callVideo=false;
  callAccepted=false;
  pendingIceCandidates=[];
  localIceCandidates=[];'''
new = '''  callVideo=false;
  callAccepted=false;
  callInitiator=false;
  callIceRestartAttempts=0;
  callIceRestartInFlight=false;
  clearCallDisconnectTimer();
  pendingIceCandidates=[];
  localIceCandidates=[];'''
if old not in text:
    raise SystemExit('call recovery session cleanup anchor not found')
text = text.replace(old, new, 1)
changed = True

start = text.find('function resetAuthenticatedRuntime()')
end = text.find('async function', start)
block = text[start:end if end >= 0 else len(text)]
for marker in required:
    if marker not in block:
        raise SystemExit(f'missing call recovery session cleanup marker: {marker}')

if changed:
    path.write_text(text, encoding='utf-8')
    print('Applied call recovery session cleanup')
