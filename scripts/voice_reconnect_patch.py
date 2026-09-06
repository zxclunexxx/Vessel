from pathlib import Path

# Voice reconnect recovery is already committed to main. Keep this script as an
# idempotent state verifier so later edits to toggleVoiceRoom do not invalidate old anchors.
text = Path('src/main.js').read_text(encoding='utf-8')

required = [
    'let voiceReconnectTimer = null;',
    'let voiceReconnectAttempt = 0;',
    'let voiceReconnectContext = null;',
    'function cancelVoiceReconnect()',
    'function scheduleVoiceReconnect(user,channelId,serverId)',
    'async function toggleVoiceRoom(user,reconnecting=false)',
    'scheduleVoiceReconnect(user,failedChannelId,failedServerId);',
    "if(!reconnecting)vesselNotice(error?.message?.startsWith('VOICE_REALTIME_')",
    "vesselNotice('Голосовая связь восстановлена.','success');",
    "vesselNotice('Голосовая связь потеряна. Нажми «Войти», чтобы попробовать снова.','error');",
]
missing = [marker for marker in required if marker not in text]
if missing:
    raise SystemExit('Voice reconnect marker missing: ' + ', '.join(missing))

print('Voice Realtime reconnect recovery already applied; nothing to change')
