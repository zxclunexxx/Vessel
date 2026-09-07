from pathlib import Path

main = Path('src/main.js').read_text(encoding='utf-8')
markers = [
    'const voicePeerReconnectTimers = new Map();',
    'const voicePeerReconnectAttempts = new Map();',
    'function cancelVoicePeerReconnect(peerId)',
    'function cancelAllVoicePeerReconnects()',
    'function scheduleVoicePeerReconnect(user,peerId)',
    "if(result!=='ok')throw new Error(`VOICE_SIGNAL_",
    "if(pc.connectionState==='connected'){cancelVoicePeerReconnect(peerId);return;}",
    'scheduleVoicePeerReconnect(user,peerId);',
    'voicePeerReconnectTimers.has(peerId)',
    'cancelAllVoicePeerReconnects();',
]
for marker in markers:
    if marker not in main:
        raise SystemExit(f'missing voice peer reconnect marker: {marker}')

if "pc.connectionState==='disconnected')setTimeout(()=>{if(voicePeers.get(peerId)?.pc===pc&&pc.connectionState==='disconnected')removeVoicePeer(peerId);},3000);" in main:
    raise SystemExit('legacy voice disconnect cleanup without reconnect remains')

print('Voice peer reconnect smoke check passed')
