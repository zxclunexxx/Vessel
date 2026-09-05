from pathlib import Path

path = Path('src/main.js')
text = path.read_text(encoding='utf-8')

old = """let voiceStream = null;
let voiceRoom = null;"""
new = """let voiceStream = null;
let voiceRoom = null;
let voiceChannelId = null;
let voiceParticipants = [];
const voicePeers = new Map();"""
if old not in text:
    raise SystemExit('voice globals anchor not found')
text = text.replace(old, new, 1)

anchor = """function callRoomName(a,b) { return `vessel-call-${[a,b].sort().join('-')}`; }"""
helpers = r'''function removeVoicePeer(peerId) {
  const state=voicePeers.get(peerId);
  if(!state)return;
  try{state.pc.close();}catch{}
  state.audio?.remove();
  voicePeers.delete(peerId);
}

async function sendVoiceSignal(user,peerId,signal){
  if(!voiceRoom||!user?.id||!peerId)return;
  await voiceRoom.send({type:'broadcast',event:'voice-signal',payload:{from:user.id,to:peerId,signal}});
}

async function ensureVoicePeer(user,peerId,initiator=false){
  if(!user?.id||!peerId||peerId===user.id)return null;
  let state=voicePeers.get(peerId);
  if(state)return state;
  const pc=new RTCPeerConnection({iceServers:[{urls:'stun:stun.l.google.com:19302'}]});
  state={pc,pending:[],audio:null};
  voicePeers.set(peerId,state);
  voiceStream?.getAudioTracks().forEach(track=>pc.addTrack(track,voiceStream));
  pc.onicecandidate=event=>{if(event.candidate)sendVoiceSignal(user,peerId,{type:'ice',candidate:event.candidate}).catch(()=>{});};
  pc.ontrack=event=>{
    let audio=state.audio;
    if(!audio){audio=document.createElement('audio');audio.autoplay=true;audio.playsInline=true;audio.dataset.voicePeer=peerId;audio.style.display='none';document.body.appendChild(audio);state.audio=audio;}
    audio.srcObject=event.streams[0];audio.play().catch(()=>{});
  };
  pc.onconnectionstatechange=()=>{if(['failed','closed'].includes(pc.connectionState))removeVoicePeer(peerId);};
  if(initiator){
    const offer=await pc.createOffer();await pc.setLocalDescription(offer);await sendVoiceSignal(user,peerId,{type:'offer',description:{type:pc.localDescription.type,sdp:pc.localDescription.sdp}});
  }
  return state;
}

async function handleVoiceSignal(user,payload){
  if(!payload||payload.to!==user?.id||payload.from===user.id)return;
  const {from,signal}=payload;
  if(!signal)return;
  const state=await ensureVoicePeer(user,from,false);
  if(!state)return;
  const {pc}=state;
  if(signal.type==='offer'){
    await pc.setRemoteDescription(signal.description);
    for(const candidate of state.pending.splice(0))await pc.addIceCandidate(candidate);
    const answer=await pc.createAnswer();await pc.setLocalDescription(answer);await sendVoiceSignal(user,from,{type:'answer',description:{type:pc.localDescription.type,sdp:pc.localDescription.sdp}});return;
  }
  if(signal.type==='answer'){
    await pc.setRemoteDescription(signal.description);
    for(const candidate of state.pending.splice(0))await pc.addIceCandidate(candidate);
    return;
  }
  if(signal.type==='ice'){
    if(pc.remoteDescription)await pc.addIceCandidate(signal.candidate);else state.pending.push(signal.candidate);
  }
}

async function syncVoicePresence(user){
  if(!voiceRoom||!user?.id)return;
  const entries=Object.values(voiceRoom.presenceState()||{}).flat();
  voiceParticipants=entries.filter(item=>item?.user_id).map(item=>({id:item.user_id,name:item.name||'Участник'}));
  const ids=new Set(voiceParticipants.map(item=>item.id).filter(id=>id!==user.id));
  for(const peerId of ids){
    if(!voicePeers.has(peerId))await ensureVoicePeer(user,peerId,String(user.id)<String(peerId));
  }
  for(const peerId of [...voicePeers.keys()])if(!ids.has(peerId))removeVoicePeer(peerId);
  const status=document.querySelector('.voice-status');
  if(status)status.textContent=`🎙 В голосовой комнате: ${Math.max(1,voiceParticipants.length)}`;
}

async function leaveVoiceRoom(){
  voiceStream?.getTracks().forEach(track=>track.stop());voiceStream=null;
  for(const peerId of [...voicePeers.keys()])removeVoicePeer(peerId);
  voiceParticipants=[];voiceChannelId=null;
  if(voiceRoom&&supabase){try{await supabase.removeChannel(voiceRoom);}catch{}}
  voiceRoom=null;
  render();
}

async function toggleVoiceRoom(user){
  if(voiceStream){await leaveVoiceRoom();return;}
  if(!supabase||!user?.id||!activeChannelId||activeChannelKind!=='voice'){alert('Сначала открой голосовой канал.');return;}
  try{
    voiceStream=await navigator.mediaDevices.getUserMedia({audio:true,video:false});
    voiceChannelId=activeChannelId;
    voiceRoom=supabase.channel(`voice-${voiceChannelId}`,{config:{presence:{key:user.id}}});
    voiceRoom.on('broadcast',{event:'voice-signal'},({payload})=>handleVoiceSignal(user,payload).catch(error=>console.warn('Voice signal failed',error)));
    voiceRoom.on('presence',{event:'sync'},()=>syncVoicePresence(user).catch(error=>console.warn('Voice presence failed',error)));
    voiceRoom.subscribe(async status=>{if(status==='SUBSCRIBED'){await voiceRoom.track({user_id:user.id,name:user.name});await syncVoicePresence(user);}});
    render();
  }catch(error){
    console.warn('Voice join failed',error);voiceStream?.getTracks().forEach(track=>track.stop());voiceStream=null;voiceRoom=null;voiceChannelId=null;alert('Разреши Vessel доступ к микрофону.');
  }
}

function toggleVoiceMicrophone(){
  const track=voiceStream?.getAudioTracks()[0];if(!track)return;track.enabled=!track.enabled;render();
}

function callRoomName(a,b) { return `vessel-call-${[a,b].sort().join('-')}`; }'''
if anchor not in text:
    raise SystemExit('call helper anchor not found')
text = text.replace(anchor, helpers, 1)

# Audio-only voice rooms should not render a blank local video tile.
old = """<video id=\"remote-video\" class=\"remote-video ${remoteCallStream?'':'hidden'}\" autoplay playsinline></video><video id=\"local-video\" class=\"local-video ${voiceStream||callStream?'':'hidden'}\" autoplay muted playsinline></video>"""
new = """<video id=\"remote-video\" class=\"remote-video ${remoteCallStream?'':'hidden'}\" autoplay playsinline></video><video id=\"local-video\" class=\"local-video ${callStream||voiceStream?.getVideoTracks().length?'':'hidden'}\" autoplay muted playsinline></video>"""
if old not in text:
    raise SystemExit('local video visibility anchor not found')
text = text.replace(old, new, 1)

old = """<button id=\"join-voice\" class=\"join-voice ${activeChannelKind==='voice'?'':'hidden'}\">${voiceStream?'Выйти':'Войти'}</button><button id=\"mute-voice\" class=\"join-voice ${voiceStream?'':'hidden'}\">🎙</button><button id=\"camera-voice\" class=\"join-voice ${voiceStream?'':'hidden'}\">📷</button>"""
new = """<button id=\"join-voice\" class=\"join-voice ${activeChannelKind==='voice'?'':'hidden'}\">${voiceStream?'Выйти':'Войти'}</button><button id=\"mute-voice\" class=\"join-voice ${voiceStream?'':'hidden'}\">${voiceStream?.getAudioTracks()[0]?.enabled===false?'🔇':'🎙'}</button>"""
if old not in text:
    raise SystemExit('voice controls markup anchor not found')
text = text.replace(old, new, 1)

old = """${voiceStream?'<div class=\"voice-status\">🎙 Ты в голосовой комнате</div>':''}${membersList}"""
new = """${voiceStream?`<div class=\"voice-status\">🎙 В голосовой комнате: ${Math.max(1,voiceParticipants.length)}</div>`:''}${membersList}"""
if old not in text:
    raise SystemExit('voice status anchor not found')
text = text.replace(old, new, 1)

# Replace the prototype presence-only voice handler with the mesh voice-room controls.
start = """    const voiceButton=document.querySelector('#join-voice'), muteButton=document.querySelector('#mute-voice'), cameraButton=document.querySelector('#camera-voice'); if(channel.textContent.includes('⌁')&&!isDm) {"""
end = """ } else {voiceButton.classList.add('hidden');muteButton.classList.add('hidden');cameraButton.classList.add('hidden');}"""
idx=text.find(start)
if idx<0:raise SystemExit('prototype voice handler start not found')
end_idx=text.find(end,idx)
if end_idx<0:raise SystemExit('prototype voice handler end not found')
end_idx += len(end)
replacement = """    const voiceButton=document.querySelector('#join-voice'), muteButton=document.querySelector('#mute-voice');
    if(channel.textContent.includes('⌁')&&!isDm){
      voiceButton.classList.remove('hidden');voiceButton.textContent=voiceStream?'Выйти':'Подключиться';voiceButton.onclick=()=>toggleVoiceRoom(user);
      if(voiceStream){muteButton.classList.remove('hidden');muteButton.onclick=toggleVoiceMicrophone;}else muteButton.classList.add('hidden');
    }else{voiceButton.classList.add('hidden');muteButton.classList.add('hidden');}"""
text = text[:idx] + replacement + text[end_idx:]

path.write_text(text, encoding='utf-8')
print('Applied functional voice room mesh patch')
