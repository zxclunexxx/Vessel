from pathlib import Path

path = Path('src/main.js')
text = path.read_text(encoding='utf-8')
changed = False

required = [
    'let callInitiator = false;',
    'let callIceRestartAttempts = 0;',
    'let callIceRestartInFlight = false;',
    'async function attemptCallIceRestart(connection,user,peerId,video)',
    'connection.createOffer({iceRestart:true})',
    "sendCallSignal(user,peerId,{type:'offer',description:callOffer,restart:true},video)",
    'scheduleCallDisconnectCleanup(connection,user,peerId,video)',
    'callInitiator=true;',
    'callInitiator=false;',
]
if all(marker in text for marker in required):
    print('Call ICE restart recovery already applied; nothing to change')
    raise SystemExit(0)

old_globals = '''let callInviteTimer = null;
let incomingCallTimer = null;
let callDisconnectTimer = null;'''
new_globals = '''let callInviteTimer = null;
let incomingCallTimer = null;
let callDisconnectTimer = null;
let callInitiator = false;
let callIceRestartAttempts = 0;
let callIceRestartInFlight = false;'''
if 'let callInitiator = false;' not in text:
    if old_globals not in text:
        raise SystemExit('call ICE state global anchor not found')
    text = text.replace(old_globals, new_globals, 1)
    changed = True

old_helpers = '''function scheduleCallDisconnectCleanup(connection){
  if(connection!==callConnection||callDisconnectTimer)return;
  const state=connection.connectionState;
  const delay=state==='failed'?5000:8000;
  callDisconnectTimer=setTimeout(async()=>{
    callDisconnectTimer=null;
    if(connection!==callConnection)return;
    if(!['failed','disconnected'].includes(connection.connectionState))return;
    vesselNotice('Связь со звонком прервалась. Попробуй позвонить снова.','error');
    await endCall(false);
  },delay);
}'''
new_helpers = '''async function attemptCallIceRestart(connection,user,peerId,video){
  if(connection!==callConnection||!callAccepted||!callInitiator||callIceRestartInFlight)return false;
  if(!['failed','disconnected'].includes(connection.connectionState))return true;
  if(callIceRestartAttempts>=2)return false;
  callIceRestartAttempts+=1;
  callIceRestartInFlight=true;
  try{
    connection.restartIce?.();
    const offer=await connection.createOffer({iceRestart:true});
    if(connection!==callConnection||!callAccepted||!callInitiator)return false;
    await connection.setLocalDescription(offer);
    callOffer=serialiseDescription(connection.localDescription);
    await sendCallSignal(user,peerId,{type:'offer',description:callOffer,restart:true},video);
    console.info(`Call ICE restart attempt ${callIceRestartAttempts} sent`);
    return true;
  }catch(error){
    console.warn('Call ICE restart failed',error);
    return false;
  }finally{
    callIceRestartInFlight=false;
  }
}
function scheduleCallDisconnectCleanup(connection,user,peerId,video){
  if(connection!==callConnection||callDisconnectTimer)return;
  const state=connection.connectionState;
  const canRestart=callInitiator&&callAccepted&&callIceRestartAttempts<2;
  const delay=canRestart?(state==='failed'?1200:2500):(callInitiator?10000:20000);
  callDisconnectTimer=setTimeout(async()=>{
    callDisconnectTimer=null;
    if(connection!==callConnection)return;
    if(!['failed','disconnected'].includes(connection.connectionState))return;
    if(callInitiator&&callAccepted&&callIceRestartAttempts<2){
      await attemptCallIceRestart(connection,user,peerId,video);
      if(connection===callConnection&&['failed','disconnected'].includes(connection.connectionState))scheduleCallDisconnectCleanup(connection,user,peerId,video);
      return;
    }
    vesselNotice('Связь со звонком прервалась. Попробуй позвонить снова.','error');
    await endCall(false);
  },delay);
}'''
if 'async function attemptCallIceRestart(connection,user,peerId,video)' not in text:
    if old_helpers not in text:
        raise SystemExit('call ICE recovery helper anchor not found')
    text = text.replace(old_helpers, new_helpers, 1)
    changed = True

old_state = '''    if(state==='connected'){clearCallDisconnectTimer();return;}
    if(state==='closed'){clearCallDisconnectTimer();return;}
    if(['failed','disconnected'].includes(state))scheduleCallDisconnectCleanup(connection);'''
new_state = '''    if(state==='connected'){clearCallDisconnectTimer();callIceRestartAttempts=0;callIceRestartInFlight=false;return;}
    if(state==='closed'){clearCallDisconnectTimer();return;}
    if(['failed','disconnected'].includes(state))scheduleCallDisconnectCleanup(connection,user,peerId,video);'''
if 'scheduleCallDisconnectCleanup(connection,user,peerId,video)' not in text:
    if old_state not in text:
        raise SystemExit('call ICE connection-state anchor not found')
    text = text.replace(old_state, new_state, 1)
    changed = True

old_outgoing = '''callPeer=peerId; callPeerName=currentDm||'Пользователь'; callVideo=!!video; callAccepted=false; callOffer=null; localIceCandidates=[]; callMicEnabled=true; callCameraEnabled=!!video;'''
new_outgoing = '''callPeer=peerId; callPeerName=currentDm||'Пользователь'; callVideo=!!video; callAccepted=false; callOffer=null; localIceCandidates=[]; callMicEnabled=true; callCameraEnabled=!!video; callInitiator=true; callIceRestartAttempts=0; callIceRestartInFlight=false;'''
if 'callCameraEnabled=!!video; callInitiator=true;' not in text:
    if old_outgoing not in text:
        raise SystemExit('outgoing call ICE role anchor not found')
    text = text.replace(old_outgoing, new_outgoing, 1)
    changed = True

old_incoming = '''incomingCall=null; callPeer=invite.from; callPeerName=invite.name; callVideo=invite.video; callAccepted=true; callMicEnabled=true; callCameraEnabled=invite.video;'''
new_incoming = '''incomingCall=null; callPeer=invite.from; callPeerName=invite.name; callVideo=invite.video; callAccepted=true; callMicEnabled=true; callCameraEnabled=invite.video; callInitiator=false; callIceRestartAttempts=0; callIceRestartInFlight=false;'''
if 'callCameraEnabled=invite.video; callInitiator=false;' not in text:
    if old_incoming not in text:
        raise SystemExit('incoming call ICE role anchor not found')
    text = text.replace(old_incoming, new_incoming, 1)
    changed = True

old_cleanup = '''  callAccepted=false;
  clearCallDisconnectTimer();
  clearIncomingCallTimer();'''
new_cleanup = '''  callAccepted=false;
  callInitiator=false;
  callIceRestartAttempts=0;
  callIceRestartInFlight=false;
  clearCallDisconnectTimer();
  clearIncomingCallTimer();'''
if 'callAccepted=false;\n  callInitiator=false;\n  callIceRestartAttempts=0;' not in text:
    if old_cleanup not in text:
        raise SystemExit('call ICE cleanup anchor not found')
    text = text.replace(old_cleanup, new_cleanup, 1)
    changed = True

for marker in required:
    if marker not in text:
        raise SystemExit(f'missing call ICE restart marker: {marker}')

if changed:
    path.write_text(text, encoding='utf-8')
    print('Applied direct-call ICE restart recovery')
else:
    print('Call ICE restart recovery already applied; nothing to change')
