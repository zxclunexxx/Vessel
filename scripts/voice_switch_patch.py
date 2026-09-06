from pathlib import Path

path = Path('src/main.js')
text = path.read_text(encoding='utf-8')
changed = False

old = """async function toggleVoiceRoom(user,reconnecting=false){
  if(!reconnecting)cancelVoiceReconnect();
  if(voiceStream && voiceChannelId===activeChannelId){await leaveVoiceRoom();return;}
  if(!supabase||!user?.id||!activeChannelId||activeChannelKind!=='voice'){vesselNotice('Сначала открой голосовой канал.','error');return;}
"""
new = """async function toggleVoiceRoom(user,reconnecting=false){
  if(!reconnecting)cancelVoiceReconnect();
  if(voiceStream){
    if(voiceChannelId===activeChannelId){await leaveVoiceRoom();return;}
    await leaveVoiceRoom();
  }
  if(!supabase||!user?.id||!activeChannelId||activeChannelKind!=='voice'){vesselNotice('Сначала открой голосовой канал.','error');return;}
"""

if new in text:
    print('Voice channel switch hardening already applied; nothing to change')
elif old in text:
    text = text.replace(old, new, 1)
    changed = True
else:
    raise SystemExit('voice switch anchor not found')

required = [
    'async function toggleVoiceRoom(user,reconnecting=false)',
    'if(voiceStream){',
    'if(voiceChannelId===activeChannelId){await leaveVoiceRoom();return;}',
    'await leaveVoiceRoom();',
]
for marker in required:
    if marker not in text:
        raise SystemExit(f'missing voice switch marker: {marker}')

if changed:
    path.write_text(text, encoding='utf-8')
    print('Applied safe voice-channel switching')
