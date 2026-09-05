from pathlib import Path

path=Path('src/main.js')
text=path.read_text(encoding='utf-8')

def replace_once(old,new,label):
    global text
    if old not in text:
        raise SystemExit(f'{label} anchor not found')
    text=text.replace(old,new,1)

# Voice peer connections should not linger indefinitely after a network disconnect.
replace_once(
"  pc.onconnectionstatechange=()=>{if(['failed','closed'].includes(pc.connectionState))removeVoicePeer(peerId);};",
"""  pc.onconnectionstatechange=()=>{
    if(['failed','closed'].includes(pc.connectionState)){removeVoicePeer(peerId);return;}
    if(pc.connectionState==='disconnected')setTimeout(()=>{if(voicePeers.get(peerId)?.pc===pc&&pc.connectionState==='disconnected')removeVoicePeer(peerId);},3000);
  };""",
'voice peer disconnect cleanup')

# Voice room joining is mutually exclusive with a direct call and only becomes active after
# the Realtime presence channel really subscribes. Errors/timeouts clean every local resource.
old="""async function toggleVoiceRoom(user){
  if(voiceStream && voiceChannelId===activeChannelId){await leaveVoiceRoom();return;}
  if(!supabase||!user?.id||!activeChannelId||activeChannelKind!=='voice'){vesselNotice('Сначала открой голосовой канал.','error');return;}
  if(voiceStream && voiceChannelId!==activeChannelId){await leaveVoiceRoom();}
  try{
    voiceStream=await navigator.mediaDevices.getUserMedia({audio:true,video:false});
    voiceChannelId=activeChannelId;
    voiceRoom=supabase.channel(`voice-${voiceChannelId}`,{config:{presence:{key:user.id}}});
    voiceRoom.on('broadcast',{event:'voice-signal'},({payload})=>handleVoiceSignal(user,payload).catch(error=>console.warn('Voice signal failed',error)));
    voiceRoom.on('presence',{event:'sync'},()=>syncVoicePresence(user).catch(error=>console.warn('Voice presence failed',error)));
    voiceRoom.subscribe(async status=>{if(status==='SUBSCRIBED'){await voiceRoom.track({user_id:user.id,name:user.name});await syncVoicePresence(user);}});
    render();
  }catch(error){
    console.warn('Voice join failed',error);voiceStream?.getTracks().forEach(track=>track.stop());voiceStream=null;voiceRoom=null;voiceChannelId=null;vesselNotice('Разреши Vessel доступ к микрофону.','error');
  }
}"""
new="""async function toggleVoiceRoom(user){
  if(voiceStream && voiceChannelId===activeChannelId){await leaveVoiceRoom();return;}
  if(!supabase||!user?.id||!activeChannelId||activeChannelKind!=='voice'){vesselNotice('Сначала открой голосовой канал.','error');return;}
  if(callConnection||callStream||incomingCall){vesselNotice('Заверши личный звонок или отклони входящий вызов перед входом в голосовой канал.','error');return;}
  if(voiceStream && voiceChannelId!==activeChannelId){await leaveVoiceRoom();}
  let room=null;
  try{
    const targetChannelId=activeChannelId;
    voiceStream=await navigator.mediaDevices.getUserMedia({audio:true,video:false});
    voiceChannelId=targetChannelId;
    room=supabase.channel(`voice-${targetChannelId}`,{config:{presence:{key:user.id}}});
    voiceRoom=room;
    room.on('broadcast',{event:'voice-signal'},({payload})=>handleVoiceSignal(user,payload).catch(error=>console.warn('Voice signal failed',error)));
    room.on('presence',{event:'sync'},()=>{if(room===voiceRoom)syncVoicePresence(user).catch(error=>console.warn('Voice presence failed',error));});
    await new Promise((resolve,reject)=>{
      let settled=false;
      const timer=setTimeout(()=>{if(!settled){settled=true;reject(new Error('VOICE_REALTIME_TIMEOUT'));}},10000);
      room.subscribe(async status=>{
        if(settled||room!==voiceRoom)return;
        if(status==='SUBSCRIBED'){
          settled=true;clearTimeout(timer);
          try{await room.track({user_id:user.id,name:user.name});await syncVoicePresence(user);resolve();}
          catch(error){reject(error);}
          return;
        }
        if(['CHANNEL_ERROR','TIMED_OUT','CLOSED'].includes(status)){
          settled=true;clearTimeout(timer);reject(new Error(`VOICE_REALTIME_${status}`));
        }
      });
    });
    render();
  }catch(error){
    console.warn('Voice join failed',error);
    voiceStream?.getTracks().forEach(track=>track.stop());voiceStream=null;
    for(const peerId of [...voicePeers.keys()])removeVoicePeer(peerId);
    voiceParticipants=[];voiceChannelId=null;
    if(room&&supabase){try{await supabase.removeChannel(room);}catch{}}
    if(voiceRoom===room)voiceRoom=null;
    vesselNotice(error?.message?.startsWith('VOICE_REALTIME_')?'Не удалось подключиться к голосовой комнате. Попробуй ещё раз.':'Разреши Vessel доступ к микрофону.','error');
    render();
  }
}"""
replace_once(old,new,'voice room lifecycle')

# Friends home keeps DM controls, but server-specific management/channel sections are visually absent.
replace_once(
"<div class=\"brand\"><span class=\"brand-mark\">◈</span><span>${friendsOpen?'Друзья':escapeHtml(activeServer?.name || 'Vessel')}</span><button class=\"more\">•••</button></div>",
"<div class=\"brand\"><span class=\"brand-mark\">◈</span><span>${friendsOpen?'Друзья':escapeHtml(activeServer?.name || 'Vessel')}</span><button class=\"more ${friendsOpen?'hidden':''}\">•••</button></div>",
'friends server menu visibility')
replace_once(
"<section class=\"channel-section\"><div class=\"section-title\">ТЕКСТОВЫЕ КАНАЛЫ <button id=\"channel-add\">＋</button></div>",
"<section class=\"channel-section ${friendsOpen?'hidden':''}\"><div class=\"section-title\">ТЕКСТОВЫЕ КАНАЛЫ <button id=\"channel-add\">＋</button></div>",
'text channel friends visibility')
replace_once(
"<section class=\"channel-section\"><div class=\"section-title\">ГОЛОСОВЫЕ КАНАЛЫ <button id=\"voice-add\">＋</button></div>",
"<section class=\"channel-section ${friendsOpen?'hidden':''}\"><div class=\"section-title\">ГОЛОСОВЫЕ КАНАЛЫ <button id=\"voice-add\">＋</button></div>",
'voice channel friends visibility')
replace_once(
"<button id=\"search-button\">⌕</button><button id=\"friends-button\" title=\"Друзья\">♧</button>",
"<button id=\"search-button\" class=\"${friendsOpen?'hidden':''}\">⌕</button><button id=\"friends-button\" title=\"Друзья\" class=\"${friendsOpen?'hidden':''}\">♧</button>",
'friends header utility visibility')

# Prevent any programmatic/stale composer event from writing to a voice channel.
replace_once(
"} else { if(!activeChannelId){vesselNotice('Сначала выбери текстовый канал.','error');return;} const {error}=await supabase.from('messages').insert({channel_id:activeChannelId,author_id:user.id,body:text});",
"} else { if(!activeChannelId||activeChannelKind!=='text'){vesselNotice('Сначала выбери текстовый канал.','error');return;} const {error}=await supabase.from('messages').insert({channel_id:activeChannelId,author_id:user.id,body:text});",
'composer text channel guard')

# Match profile UI validation with database constraints and give a useful client-side error.
replace_once(
"<label>Имя пользователя<input name=\"name\" value=\"${escapeHtml(user.name)}\" required minlength=\"2\" /></label>",
"<label>Имя пользователя<input name=\"name\" value=\"${escapeHtml(user.name)}\" required minlength=\"2\" maxlength=\"32\" /></label>",
'profile maxlength')
replace_once(
"    const status=String(data.get('status')||'online');\n    if(!name)return;",
"    const status=String(data.get('status')||'online');\n    if(name.length<2||name.length>32){vesselNotice('Имя пользователя должно содержать от 2 до 32 символов.','error');return;}",
'profile length validation')

# Stable server helper everywhere, including immediately after server creation.
replace_once("        const selected=servers[activeServerIndex];","        const selected=getActiveServer();",'created server selection')

# Voice header button listener should remain safe even if the UI is re-rendered during errors.
for required in [
    "if(callConnection||callStream||incomingCall){vesselNotice('Заверши личный звонок",
    "VOICE_REALTIME_TIMEOUT",
    "activeChannelKind!=='text'",
    "maxlength=\"32\"",
    "const selected=getActiveServer();",
    "document.querySelector('#end-call')?.addEventListener('click',()=>endCall(true));",
]:
    if required not in text:
        raise SystemExit(f'missing final runtime hardening: {required}')
for forbidden in [
    "const selected=servers[activeServerIndex];",
    "if(!activeChannelId){vesselNotice('Сначала выбери текстовый канал.'",
]:
    if forbidden in text:
        raise SystemExit(f'stale runtime behavior remains: {forbidden}')

path.write_text(text,encoding='utf-8')
print('Applied final voice and navigation hardening')
