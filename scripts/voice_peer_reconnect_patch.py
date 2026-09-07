from pathlib import Path

path = Path('src/main.js')
text = path.read_text(encoding='utf-8')
changed = False

old_state = "const voicePeers = new Map();\nlet voiceReconnectTimer = null;"
new_state = "const voicePeers = new Map();\nconst voicePeerReconnectTimers = new Map();\nconst voicePeerReconnectAttempts = new Map();\nlet voiceReconnectTimer = null;"
if new_state not in text:
    if old_state not in text:
        raise SystemExit('voice peer state anchor not found')
    text = text.replace(old_state, new_state, 1)
    changed = True

old_remove = '''function removeVoicePeer(peerId) {
  const state=voicePeers.get(peerId);
  if(!state)return;
  try{state.pc.close();}catch{}
  state.audio?.remove();
  voicePeers.delete(peerId);
}

async function sendVoiceSignal(user,peerId,signal){
  if(!voiceRoom||!user?.id||!peerId)return;
  await voiceRoom.send({type:'broadcast',event:'voice-signal',payload:{from:user.id,to:peerId,signal}});
}'''
new_remove = '''function removeVoicePeer(peerId) {
  const state=voicePeers.get(peerId);
  if(!state)return;
  try{state.pc.close();}catch{}
  state.audio?.remove();
  voicePeers.delete(peerId);
}
function cancelVoicePeerReconnect(peerId){
  const timer=voicePeerReconnectTimers.get(peerId);
  if(timer)clearTimeout(timer);
  voicePeerReconnectTimers.delete(peerId);
  voicePeerReconnectAttempts.delete(peerId);
}
function cancelAllVoicePeerReconnects(){
  for(const peerId of [...voicePeerReconnectTimers.keys()])cancelVoicePeerReconnect(peerId);
  voicePeerReconnectAttempts.clear();
}
function scheduleVoicePeerReconnect(user,peerId){
  if(!user?.id||!peerId||peerId===user.id||voicePeerReconnectTimers.has(peerId))return;
  if(!voiceRoom||!voiceStream||!voiceParticipants.some(item=>item.id===peerId))return;
  const attempt=Math.min((voicePeerReconnectAttempts.get(peerId)||0)+1,4);
  voicePeerReconnectAttempts.set(peerId,attempt);
  const delay=Math.min(750*(2**(attempt-1)),6000);
  const timer=setTimeout(async()=>{
    voicePeerReconnectTimers.delete(peerId);
    if(savedUser?.id!==user.id||!voiceRoom||!voiceStream||!voiceParticipants.some(item=>item.id===peerId)){cancelVoicePeerReconnect(peerId);return;}
    if(voicePeers.has(peerId))return;
    try{
      await ensureVoicePeer(user,peerId,String(user.id)<String(peerId));
    }catch(error){
      console.warn('Voice peer reconnect failed',error);
      if(attempt<4)scheduleVoicePeerReconnect(user,peerId);
    }
  },delay);
  voicePeerReconnectTimers.set(peerId,timer);
}

async function sendVoiceSignal(user,peerId,signal){
  if(!voiceRoom||!user?.id||!peerId)throw new Error('VOICE_SIGNAL_ROOM_UNAVAILABLE');
  const result=await voiceRoom.send({type:'broadcast',event:'voice-signal',payload:{from:user.id,to:peerId,signal}});
  if(result!=='ok')throw new Error(`VOICE_SIGNAL_${String(result||'FAILED').toUpperCase()}`);
}'''
if new_remove not in text:
    if old_remove not in text:
        raise SystemExit('voice peer remove/signal anchor not found')
    text = text.replace(old_remove, new_remove, 1)
    changed = True

old_statechange = '''  pc.onconnectionstatechange=()=>{
    if(['failed','closed'].includes(pc.connectionState)){removeVoicePeer(peerId);return;}
    if(pc.connectionState==='disconnected')setTimeout(()=>{if(voicePeers.get(peerId)?.pc===pc&&pc.connectionState==='disconnected')removeVoicePeer(peerId);},3000);
  };
  if(initiator){
    const offer=await pc.createOffer();await pc.setLocalDescription(offer);await sendVoiceSignal(user,peerId,{type:'offer',description:{type:pc.localDescription.type,sdp:pc.localDescription.sdp}});
  }
  return state;'''
new_statechange = '''  pc.onconnectionstatechange=()=>{
    if(pc.connectionState==='connected'){cancelVoicePeerReconnect(peerId);return;}
    if(['failed','closed'].includes(pc.connectionState)){
      removeVoicePeer(peerId);
      scheduleVoicePeerReconnect(user,peerId);
      return;
    }
    if(pc.connectionState==='disconnected')setTimeout(()=>{
      if(voicePeers.get(peerId)?.pc===pc&&pc.connectionState==='disconnected'){
        removeVoicePeer(peerId);
        scheduleVoicePeerReconnect(user,peerId);
      }
    },5000);
  };
  if(initiator){
    try{
      const offer=await pc.createOffer();await pc.setLocalDescription(offer);await sendVoiceSignal(user,peerId,{type:'offer',description:{type:pc.localDescription.type,sdp:pc.localDescription.sdp}});
    }catch(error){
      if(voicePeers.get(peerId)?.pc===pc)removeVoicePeer(peerId);
      scheduleVoicePeerReconnect(user,peerId);
      throw error;
    }
  }
  return state;'''
if new_statechange not in text:
    if old_statechange not in text:
        raise SystemExit('voice peer connection-state anchor not found')
    text = text.replace(old_statechange, new_statechange, 1)
    changed = True

old_presence = '''  for(const peerId of ids){
    if(!voicePeers.has(peerId))await ensureVoicePeer(user,peerId,String(user.id)<String(peerId));
  }
  for(const peerId of [...voicePeers.keys()])if(!ids.has(peerId))removeVoicePeer(peerId);'''
new_presence = '''  for(const peerId of ids){
    if(!voicePeers.has(peerId)&&!voicePeerReconnectTimers.has(peerId)){
      try{await ensureVoicePeer(user,peerId,String(user.id)<String(peerId));}
      catch(error){console.warn('Voice peer connect failed',error);scheduleVoicePeerReconnect(user,peerId);}
    }
  }
  for(const peerId of [...voicePeers.keys()])if(!ids.has(peerId)){removeVoicePeer(peerId);cancelVoicePeerReconnect(peerId);}
  for(const peerId of [...voicePeerReconnectTimers.keys()])if(!ids.has(peerId))cancelVoicePeerReconnect(peerId);'''
if new_presence not in text:
    if old_presence not in text:
        raise SystemExit('voice presence anchor not found')
    text = text.replace(old_presence, new_presence, 1)
    changed = True

old_leave = '''  voiceStream?.getTracks().forEach(track=>track.stop());voiceStream=null;
  for(const peerId of [...voicePeers.keys()])removeVoicePeer(peerId);
  voiceParticipants=[];voiceChannelId=null;voiceServerId=null;'''
new_leave = '''  voiceStream?.getTracks().forEach(track=>track.stop());voiceStream=null;
  for(const peerId of [...voicePeers.keys()])removeVoicePeer(peerId);
  cancelAllVoicePeerReconnects();
  voiceParticipants=[];voiceChannelId=null;voiceServerId=null;'''
if new_leave not in text:
    if old_leave not in text:
        raise SystemExit('voice leave anchor not found')
    text = text.replace(old_leave, new_leave, 1)
    changed = True

for marker in [
    'const voicePeerReconnectTimers = new Map();',
    'function scheduleVoicePeerReconnect(user,peerId)',
    "if(result!=='ok')throw new Error(`VOICE_SIGNAL_",
    "if(pc.connectionState==='connected'){cancelVoicePeerReconnect(peerId);return;}",
    'scheduleVoicePeerReconnect(user,peerId);',
    'cancelAllVoicePeerReconnects();',
]:
    if marker not in text:
        raise SystemExit(f'missing voice reconnect marker: {marker}')

if changed:
    path.write_text(text, encoding='utf-8')
    print('Voice peer reconnect hardening applied')
else:
    print('Voice peer reconnect hardening already applied; nothing to change')
