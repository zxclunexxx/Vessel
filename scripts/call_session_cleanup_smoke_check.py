from pathlib import Path

text = Path('src/main.js').read_text(encoding='utf-8')
start = text.find('function resetAuthenticatedRuntime()')
end = text.find('async function', start)
if start < 0:
    raise SystemExit('resetAuthenticatedRuntime not found')
block = text[start:end if end >= 0 else len(text)]
required = [
    'clearIncomingCallTimer();',
    'callInitiator=false;',
    'callIceRestartAttempts=0;',
    'callIceRestartInFlight=false;',
    'clearCallDisconnectTimer();',
    'if(callInviteTimer){clearTimeout(callInviteTimer);callInviteTimer=null;}',
]
missing = [marker for marker in required if marker not in block]
if missing:
    raise SystemExit('Missing call session cleanup markers: ' + ', '.join(missing))

print('Call recovery session cleanup smoke check passed')
