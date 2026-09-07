from pathlib import Path

text = Path('src/main.js').read_text(encoding='utf-8')
connected_state = "if(state==='connected'){clearCallDisconnectTimer();callIceRestartAttempts=0;callIceRestartInFlight=false;return;}"
reconnect_callsite = "if(['failed','disconnected'].includes(state))scheduleCallDisconnectCleanup(connection,user,peerId,video);"
required = [
    'let callInitiator = false;',
    'let callIceRestartAttempts = 0;',
    'let callIceRestartInFlight = false;',
    'async function attemptCallIceRestart(connection,user,peerId,video)',
    'connection.restartIce?.();',
    'connection.createOffer({iceRestart:true})',
    "sendCallSignal(user,peerId,{type:'offer',description:callOffer,restart:true},video)",
    connected_state,
    reconnect_callsite,
    'callInitiator=true;',
    'callInitiator=false;',
    'callIceRestartAttempts>=2',
]
missing = [marker for marker in required if marker not in text]
if missing:
    raise SystemExit('Missing call ICE restart markers: ' + ', '.join(missing))

if text.count('connection.createOffer({iceRestart:true})') != 1:
    raise SystemExit('Unexpected number of ICE restart offer paths')
if text.count(reconnect_callsite) != 1:
    raise SystemExit('Direct-call reconnect callsite is missing or duplicated')
if "scheduleCallDisconnectCleanup(connection);" in text:
    raise SystemExit('Legacy reconnect callsite still drops user/peer/video context')
if "const delay=canRestart?(state==='failed'?1200:2500):(callInitiator?10000:20000);" not in text:
    raise SystemExit('Call recovery grace periods are missing')

print('Call ICE restart recovery smoke check passed')
