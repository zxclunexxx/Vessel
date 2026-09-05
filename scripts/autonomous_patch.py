from pathlib import Path

path = Path('src/main.js')
text = path.read_text(encoding='utf-8')

# The callee must see the caller's name, not their own name from currentDm.
old = "await sendCallInvite(user,activeDmId,{type:'invite',name:callPeerName,video:callVideo,offer:callOffer});"
new = "await sendCallInvite(user,activeDmId,{type:'invite',name:user.name,video:callVideo,offer:callOffer});"
if old not in text:
    raise SystemExit('call invite name anchor not found')
text = text.replace(old,new,1)

# Allow a user to switch directly between voice rooms instead of first having to disconnect manually.
old = """async function toggleVoiceRoom(user){
  if(voiceStream){await leaveVoiceRoom();return;}
  if(!supabase||!user?.id||!activeChannelId||activeChannelKind!=='voice'){alert('Сначала открой голосовой канал.');return;}"""
new = """async function toggleVoiceRoom(user){
  if(voiceStream && voiceChannelId===activeChannelId){await leaveVoiceRoom();return;}
  if(!supabase||!user?.id||!activeChannelId||activeChannelKind!=='voice'){vesselNotice('Сначала открой голосовой канал.','error');return;}
  if(voiceStream && voiceChannelId!==activeChannelId){await leaveVoiceRoom();}
"""
if old not in text:
    raise SystemExit('toggleVoiceRoom anchor not found')
text = text.replace(old,new,1)

# Render the voice action according to the actual room connection, not merely whether any voice stream exists.
old = """<button id=\"join-voice\" class=\"join-voice ${activeChannelKind==='voice'?'':'hidden'}\">${voiceStream?'Выйти':'Войти'}</button>"""
new = """<button id=\"join-voice\" class=\"join-voice ${activeChannelKind==='voice'?'':'hidden'}\">${voiceStream?(voiceChannelId===activeChannelId?'Выйти':'Переключиться'):'Войти'}</button>"""
if old not in text:
    raise SystemExit('voice header button anchor not found')
text = text.replace(old,new,1)

old = "voiceButton.classList.remove('hidden');voiceButton.textContent=voiceStream?'Выйти':'Подключиться';voiceButton.onclick=()=>toggleVoiceRoom(user);"
new = "voiceButton.classList.remove('hidden');voiceButton.textContent=voiceStream?(voiceChannelId===activeChannelId?'Выйти':'Переключиться'):'Подключиться';voiceButton.onclick=()=>toggleVoiceRoom(user);"
if old not in text:
    raise SystemExit('voice channel button text anchor not found')
text = text.replace(old,new,1)

# Do not expose the voice mute button while viewing a different room than the connected one.
old = "if(voiceStream){muteButton.classList.remove('hidden');muteButton.onclick=toggleVoiceMicrophone;}else muteButton.classList.add('hidden');"
new = "if(voiceStream&&voiceChannelId===activeChannelId){muteButton.classList.remove('hidden');muteButton.onclick=toggleVoiceMicrophone;}else muteButton.classList.add('hidden');"
if old not in text:
    raise SystemExit('voice mute visibility anchor not found')
text = text.replace(old,new,1)

path.write_text(text,encoding='utf-8')
print('Applied call identity and voice switching patch')
