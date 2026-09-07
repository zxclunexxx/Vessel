from pathlib import Path

path = Path('src/main.js')
text = path.read_text(encoding='utf-8')
changed = False


def replace_once(old, new, label):
    global text, changed
    if new in text:
        print(f'{label} already applied')
        return
    if old not in text:
        raise SystemExit(f'{label} anchor not found')
    text = text.replace(old, new, 1)
    changed = True


replace_once(
    """let voiceServerId = null;\nlet voiceParticipants = [];\n""",
    """let voiceServerId = null;\nlet voiceParticipants = [];\nlet voiceDeafened = false;\n""",
    'voice deafen state',
)

replace_once(
    """    if(!audio){audio=document.createElement('audio');audio.autoplay=true;audio.playsInline=true;audio.dataset.voicePeer=peerId;audio.style.display='none';document.body.appendChild(audio);state.audio=audio;}\n    audio.srcObject=event.streams[0];audio.play().catch(()=>{});\n""",
    """    if(!audio){audio=document.createElement('audio');audio.autoplay=true;audio.playsInline=true;audio.dataset.voicePeer=peerId;audio.style.display='none';document.body.appendChild(audio);state.audio=audio;}\n    audio.muted=voiceDeafened;\n    audio.srcObject=event.streams[0];audio.play().catch(()=>{});\n""",
    'remote voice deafen propagation',
)

replace_once(
    """  const entries=Object.values(voiceRoom.presenceState()||{}).flat();\n  voiceParticipants=entries.filter(item=>item?.user_id).map(item=>({id:item.user_id,name:item.name||'Участник'}));\n""",
    """  const entries=Object.values(voiceRoom.presenceState()||{}).flat();\n  const uniqueParticipants=new Map();\n  for(const item of entries)if(item?.user_id&&!uniqueParticipants.has(item.user_id))uniqueParticipants.set(item.user_id,{id:item.user_id,name:item.name||'Участник'});\n  voiceParticipants=[...uniqueParticipants.values()];\n""",
    'voice presence dedupe',
)

replace_once(
    """  voiceParticipants=[];voiceChannelId=null;voiceServerId=null;\n  if(room&&supabase){try{await supabase.removeChannel(room);}catch{}}\n""",
    """  voiceParticipants=[];voiceChannelId=null;voiceServerId=null;voiceDeafened=false;\n  if(room&&supabase){try{await supabase.removeChannel(room);}catch{}}\n""",
    'voice leave state reset',
)

replace_once(
    """function toggleVoiceMicrophone(){\n  const track=voiceStream?.getAudioTracks()[0];if(!track)return;track.enabled=!track.enabled;render();\n}\n\nfunction callRoomName(a,b) { return `vessel-call-${[a,b].sort().join('-')}`; }\n""",
    """function toggleVoiceMicrophone(){\n  const track=voiceStream?.getAudioTracks()[0];if(!track)return;track.enabled=!track.enabled;render();\n}\nfunction toggleVoiceDeafen(){\n  if(!voiceStream)return;\n  voiceDeafened=!voiceDeafened;\n  for(const state of voicePeers.values())if(state.audio)state.audio.muted=voiceDeafened;\n  render();\n}\n\nfunction callRoomName(a,b) { return `vessel-call-${[a,b].sort().join('-')}`; }\n""",
    'voice deafen action',
)

replace_once(
    """  voiceParticipants=[];\n  voiceChannelId=null;\n  voiceServerId=null;\n  incomingCall=null;\n""",
    """  voiceParticipants=[];\n  voiceChannelId=null;\n  voiceServerId=null;\n  voiceDeafened=false;\n  incomingCall=null;\n""",
    'voice auth reset',
)

replace_once(
    """<button id=\"mute-voice\" class=\"join-voice ${!friendsOpen&&voiceStream&&voiceChannelId===activeChannelId?'':'hidden'}\">${voiceStream?.getAudioTracks()[0]?.enabled===false?'🔇':'🎙'}</button><button id=\"search-button\"""",
    """<button id=\"mute-voice\" class=\"join-voice ${!friendsOpen&&voiceStream&&voiceChannelId===activeChannelId?'':'hidden'}\" title=\"${voiceStream?.getAudioTracks()[0]?.enabled===false?'Включить микрофон':'Выключить микрофон'}\">${voiceStream?.getAudioTracks()[0]?.enabled===false?'🔇':'🎙'}</button><button id=\"deafen-voice\" class=\"join-voice ${!friendsOpen&&voiceStream&&voiceChannelId===activeChannelId?'':'hidden'}\" title=\"${voiceDeafened?'Включить звук участников':'Отключить звук участников'}\">${voiceDeafened?'🙉':'🎧'}</button><button id=\"search-button\"""",
    'voice deafen control',
)

replace_once(
    """  document.querySelector('#accept-call')?.addEventListener('click', () => acceptIncomingCall(user));\n  document.querySelector('#reject-call')?.addEventListener('click', () => rejectIncomingCall(user));\n""",
    """  document.querySelector('#join-voice')?.addEventListener('click',async event=>{\n    const button=event.currentTarget;\n    button.disabled=true;\n    try{await toggleVoiceRoom(user);}finally{if(button.isConnected)button.disabled=false;}\n  });\n  document.querySelector('#mute-voice')?.addEventListener('click',toggleVoiceMicrophone);\n  document.querySelector('#deafen-voice')?.addEventListener('click',toggleVoiceDeafen);\n  document.querySelector('#accept-call')?.addEventListener('click', () => acceptIncomingCall(user));\n  document.querySelector('#reject-call')?.addEventListener('click', () => rejectIncomingCall(user));\n""",
    'voice control event wiring',
)

required = [
    "document.querySelector('#join-voice')?.addEventListener('click'",
    "document.querySelector('#mute-voice')?.addEventListener('click',toggleVoiceMicrophone)",
    "document.querySelector('#deafen-voice')?.addEventListener('click',toggleVoiceDeafen)",
    'function toggleVoiceDeafen()',
    'const uniqueParticipants=new Map();',
    'audio.muted=voiceDeafened;',
]
for marker in required:
    if marker not in text:
        raise SystemExit(f'missing voice controls marker: {marker}')

if changed:
    path.write_text(text, encoding='utf-8')
    print('Applied voice controls, deafen, and presence dedupe hardening')
else:
    print('Voice controls hardening already applied; nothing to change')
