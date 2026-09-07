from pathlib import Path

path = Path('src/main.js')
text = path.read_text(encoding='utf-8')
changed = False

def replace_once(old, new, label):
    global text, changed
    if new in text:
        print(f'{label}: already applied')
        return
    if old not in text:
        raise SystemExit(f'{label}: expected source or patched form not found')
    text = text.replace(old, new, 1)
    changed = True
    print(f'{label}: applied')

replace_once(
"""let callIceRestartAttempts = 0;
let callIceRestartInFlight = false;
let activeServerIndex = 0;""",
"""let callIceRestartAttempts = 0;
let callIceRestartInFlight = false;
let rtcConfigCache = null;
let rtcConfigUserId = null;
let rtcConfigExpiresAt = 0;
let rtcConfigPromise = null;
let callInboxReconnectTimer = null;
let callInboxReconnectAttempt = 0;
let callSignalReconnectTimer = null;
let callSignalReconnectAttempt = 0;
let activeServerIndex = 0;""",
'RTC and call reconnect state',
)

old_voice_remove = """function removeVoicePeer(peerId) {
  const state=voicePeers.get(peerId);
  if(!state)return;
  try{state.pc.close();}catch{}
  state.audio?.remove();
  voicePeers.delete(peerId);
}
"""
new_voice_remove = """const RTC_FALLBACK_ICE_SERVERS = [
  {urls:['stun:stun.l.google.com:19302','stun:stun1.l.google.com:19302']}
];
function resetRtcConfiguration(){
  rtcConfigCache=null;
  rtcConfigUserId=null;
  rtcConfigExpiresAt=0;
  rtcConfigPromise=null;
}
function normaliseRtcIceServers(rows){
  if(!Array.isArray(rows))return [];
  const output=[];
  for(const row of rows.slice(0,8)){
    if(!row||typeof row!=='object')continue;
    const rawUrls=Array.isArray(row.urls)?row.urls:[row.urls];
    const urls=rawUrls.map(value=>String(value||'').trim()).filter(value=>/^(stun|turn|turns):/i.test(value));
    if(!urls.length)continue;
    const hasRelay=urls.some(value=>/^turns?:/i.test(value));
    if(hasRelay&&(!row.username||!row.credential))continue;
    const entry={urls:urls.length===1?urls[0]:urls};
    if(hasRelay){entry.username=String(row.username);entry.credential=String(row.credential);}
    output.push(entry);
  }
  return output;
}
async function resolveRtcConfiguration(user,{force=false}={}){
  const userId=user?.id||null;
  const fallback={iceServers:RTC_FALLBACK_ICE_SERVERS,iceCandidatePoolSize:2};
  if(!supabase||!userId||savedUser?.id!==userId)return fallback;
  const now=Date.now();
  if(!force&&rtcConfigCache&&rtcConfigUserId===userId&&rtcConfigExpiresAt>now+60000)return rtcConfigCache;
  if(rtcConfigPromise&&rtcConfigUserId===userId)return rtcConfigPromise;
  rtcConfigUserId=userId;
  rtcConfigPromise=(async()=>{
    try{
      const {data,error}=await supabase.functions.invoke('rtc-config');
      if(savedUser?.id!==userId)return fallback;
      if(error)throw error;
      const iceServers=normaliseRtcIceServers(data?.iceServers);
      if(!iceServers.length)throw new Error('RTC_CONFIG_EMPTY');
      const parsedExpiry=Date.parse(String(data?.expires_at||''));
      rtcConfigCache={iceServers,iceCandidatePoolSize:2};
      rtcConfigExpiresAt=Number.isFinite(parsedExpiry)?parsedExpiry:Date.now()+5*60*1000;
      return rtcConfigCache;
    }catch(error){
      console.warn('RTC configuration fallback active',error);
      rtcConfigCache=fallback;
      rtcConfigExpiresAt=Date.now()+60*1000;
      return fallback;
    }finally{
      rtcConfigPromise=null;
    }
  })();
  return rtcConfigPromise;
}
function clearVoicePeerDisconnectTimer(state){
  if(state?.disconnectTimer){clearTimeout(state.disconnectTimer);state.disconnectTimer=null;}
}
async function attemptVoicePeerIceRestart(user,peerId,state){
  if(!user?.id||!state||voicePeers.get(peerId)!==state||!state.initiator||state.iceRestartInFlight)return false;
  const pc=state.pc;
  if(!['failed','disconnected'].includes(pc.connectionState)||state.iceRestartAttempts>=2)return false;
  state.iceRestartAttempts+=1;
  state.iceRestartInFlight=true;
  try{
    const rtcConfiguration=await resolveRtcConfiguration(user,{force:true});
    if(savedUser?.id!==user.id||voicePeers.get(peerId)!==state||!voiceRoom||!voiceStream)return false;
    pc.setConfiguration?.(rtcConfiguration);
    pc.restartIce?.();
    const offer=await pc.createOffer({iceRestart:true});
    if(savedUser?.id!==user.id||voicePeers.get(peerId)!==state||!voiceRoom||!voiceStream)return false;
    await pc.setLocalDescription(offer);
    await sendVoiceSignal(user,peerId,{type:'offer',description:{type:pc.localDescription.type,sdp:pc.localDescription.sdp},restart:true});
    console.info(`Voice ICE restart attempt ${state.iceRestartAttempts} sent for ${peerId}`);
    return true;
  }catch(error){
    console.warn('Voice ICE restart failed',error);
    return false;
  }finally{
    state.iceRestartInFlight=false;
  }
}
function scheduleVoicePeerRecovery(user,peerId,state){
  if(!user?.id||!state||voicePeers.get(peerId)!==state||state.disconnectTimer)return;
  if(!['failed','disconnected'].includes(state.pc.connectionState))return;
  const canRestart=state.initiator&&state.iceRestartAttempts<2;
  const delay=canRestart?(state.pc.connectionState==='failed'?750:2200):(state.initiator?8000:12000);
  state.disconnectTimer=setTimeout(async()=>{
    state.disconnectTimer=null;
    if(savedUser?.id!==user.id||voicePeers.get(peerId)!==state||!voiceRoom||!voiceStream)return;
    if(!['failed','disconnected'].includes(state.pc.connectionState))return;
    if(state.initiator&&state.iceRestartAttempts<2){
      await attemptVoicePeerIceRestart(user,peerId,state);
      if(voicePeers.get(peerId)===state&&['failed','disconnected'].includes(state.pc.connectionState))scheduleVoicePeerRecovery(user,peerId,state);
      return;
    }
    removeVoicePeer(peerId);
    scheduleVoicePeerReconnect(user,peerId);
  },delay);
}
function removeVoicePeer(peerId) {
  const state=voicePeers.get(peerId);
  if(!state)return;
  voicePeers.delete(peerId);
  clearVoicePeerDisconnectTimer(state);
  try{state.pc.close();}catch{}
  state.audio?.remove();
}
"""
replace_once(old_voice_remove, new_voice_remove, 'RTC config and voice ICE recovery helpers')

replace_once(
"""  const pc=new RTCPeerConnection({iceServers:[{urls:'stun:stun.l.google.com:19302'}]});
  state={pc,pending:[],audio:null};
  voicePeers.set(peerId,state);""",
"""  const rtcConfiguration=await resolveRtcConfiguration(user);
  if(savedUser?.id!==user.id||!voiceRoom||!voiceStream)return null;
  const pc=new RTCPeerConnection(rtcConfiguration);
  state={pc,pending:[],audio:null,initiator:!!initiator,iceRestartAttempts:0,iceRestartInFlight:false,disconnectTimer:null};
  voicePeers.set(peerId,state);""",
'Voice peer TURN-aware connection',
)

replace_once(
"""  pc.onconnectionstatechange=()=>{
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
  };""",
"""  pc.onconnectionstatechange=()=>{
    if(pc.connectionState==='connected'){clearVoicePeerDisconnectTimer(state);state.iceRestartAttempts=0;state.iceRestartInFlight=false;}
    if(pc.connectionState==='connected'){cancelVoicePeerReconnect(peerId);return;}
    if(pc.connectionState==='closed'){
      if(voicePeers.get(peerId)===state){removeVoicePeer(peerId);scheduleVoicePeerReconnect(user,peerId);}
      return;
    }
    if(['failed','disconnected'].includes(pc.connectionState))scheduleVoicePeerRecovery(user,peerId,state);
  };""",
'Voice connection recovery strategy',
)

replace_once(
"""      setTimeout(()=>{
        if(savedUser?.id===user.id&&!callInboxChannel)ensureCallInbox(savedUser).catch(retryError=>console.warn('Call inbox reconnect failed',retryError));
      },1000);""",
"""      if(savedUser?.id===user.id&&!callInboxChannel)scheduleCallInboxReconnect(savedUser);""",
'Call inbox established reconnect backoff',
)
replace_once(
"""    setTimeout(()=>{if(savedUser?.id===user.id&&!callInboxChannel)ensureCallInbox(savedUser).catch(retryError=>console.warn('Call inbox retry failed',retryError));},3000);
    return null;""",
"""    if(savedUser?.id===user.id&&!callInboxChannel)scheduleCallInboxReconnect(user);
    return null;""",
'Call inbox initial reconnect backoff',
)
replace_once(
"""  return callInboxChannel===inbox?inbox:callInboxChannel;
}
async function ensureCallChannel(user, peerId) {""",
"""  if(callInboxChannel===inbox)cancelCallInboxReconnect();
  return callInboxChannel===inbox?inbox:callInboxChannel;
}
function cancelCallInboxReconnect(){
  if(callInboxReconnectTimer){clearTimeout(callInboxReconnectTimer);callInboxReconnectTimer=null;}
  callInboxReconnectAttempt=0;
}
function scheduleCallInboxReconnect(user,immediate=false){
  if(!user?.id||savedUser?.id!==user.id||callInboxReconnectTimer)return;
  callInboxReconnectAttempt=Math.min(callInboxReconnectAttempt+1,6);
  const delay=immediate?0:Math.min(1000*(2**(callInboxReconnectAttempt-1)),15000);
  const sessionUserId=user.id;
  callInboxReconnectTimer=setTimeout(()=>{
    callInboxReconnectTimer=null;
    if(savedUser?.id!==sessionUserId||callInboxChannel)return;
    ensureCallInbox(savedUser).catch(retryError=>{
      console.warn('Call inbox reconnect failed',retryError);
      if(savedUser?.id===sessionUserId&&!callInboxChannel)scheduleCallInboxReconnect(savedUser);
    });
  },delay);
}
async function ensureCallChannel(user, peerId) {""",
'Call inbox reconnect scheduler',
)

replace_once(
"""      setTimeout(()=>{
        if(savedUser?.id===user.id&&callPeer===peerId&&callConnection&&!callChannel){
          ensureCallChannel(savedUser,peerId).catch(error=>console.warn('Call signaling reconnect failed',error));
        }
      },1000);""",
"""      if(savedUser?.id===user.id&&callPeer===peerId&&callConnection&&!callChannel)scheduleCallSignalReconnect(savedUser,peerId);""",
'Call signaling established reconnect backoff',
)
replace_once(
"""  return room;
}
async function sendCallSignal(user,peerId,signal,video) {""",
"""  if(callChannel===room)cancelCallSignalReconnect();
  return room;
}
function cancelCallSignalReconnect(){
  if(callSignalReconnectTimer){clearTimeout(callSignalReconnectTimer);callSignalReconnectTimer=null;}
  callSignalReconnectAttempt=0;
}
function scheduleCallSignalReconnect(user,peerId,immediate=false){
  if(!user?.id||!peerId||savedUser?.id!==user.id||callPeer!==peerId||!callConnection||callSignalReconnectTimer)return;
  callSignalReconnectAttempt=Math.min(callSignalReconnectAttempt+1,6);
  const delay=immediate?0:Math.min(750*(2**(callSignalReconnectAttempt-1)),12000);
  const sessionUserId=user.id;
  callSignalReconnectTimer=setTimeout(()=>{
    callSignalReconnectTimer=null;
    if(savedUser?.id!==sessionUserId||callPeer!==peerId||!callConnection||callChannel)return;
    ensureCallChannel(savedUser,peerId).then(async room=>{
      if(!room||savedUser?.id!==sessionUserId||callPeer!==peerId||!callConnection)return;
      cancelCallSignalReconnect();
      if(callInitiator&&callAccepted&&['failed','disconnected'].includes(callConnection.connectionState)){
        await attemptCallIceRestart(callConnection,savedUser,peerId,callVideo);
      }
    }).catch(error=>{
      console.warn('Call signaling reconnect failed',error);
      if(savedUser?.id===sessionUserId&&callPeer===peerId&&callConnection&&!callChannel)scheduleCallSignalReconnect(savedUser,peerId);
    });
  },delay);
}
async function sendCallSignal(user,peerId,signal,video) {""",
'Call signaling reconnect scheduler',
)

replace_once(
"""  try{
    connection.restartIce?.();
    const offer=await connection.createOffer({iceRestart:true});""",
"""  try{
    const rtcConfiguration=await resolveRtcConfiguration(user,{force:true});
    if(connection!==callConnection||!callAccepted||!callInitiator)return false;
    connection.setConfiguration?.(rtcConfiguration);
    connection.restartIce?.();
    const offer=await connection.createOffer({iceRestart:true});""",
'Call ICE restart TURN credential refresh',
)

replace_once(
"""function prepareCallConnection(user,peerId,video) {
  if (callConnection) return callConnection;
  callConnection=new RTCPeerConnection({iceServers:[{urls:'stun:stun.l.google.com:19302'}]});""",
"""async function prepareCallConnection(user,peerId,video) {
  if (callConnection) return callConnection;
  const sessionUserId=user?.id||null;
  if(!sessionUserId||savedUser?.id!==sessionUserId||callPeer!==peerId)return null;
  const rtcConfiguration=await resolveRtcConfiguration(user);
  if(savedUser?.id!==sessionUserId||callPeer!==peerId)return null;
  if(callConnection)return callConnection;
  callConnection=new RTCPeerConnection(rtcConfiguration);""",
'Call TURN-aware connection',
)

replace_once(
"""    callVideo=!!video; prepareCallConnection(user,peerId,!!video); await callConnection.setRemoteDescription(signal.description);""",
"""    callVideo=!!video; if(!await prepareCallConnection(user,peerId,!!video))return; await callConnection.setRemoteDescription(signal.description);""",
'Incoming call async RTC configuration',
)
replace_once(
"""    prepareCallConnection(user,peerId,!!video);
    const offer=await callConnection.createOffer();""",
"""    if(!await prepareCallConnection(user,peerId,!!video))throw new Error('CALL_RTC_CONFIGURATION_STALE');
    const offer=await callConnection.createOffer();""",
'Outgoing call async RTC configuration',
)

replace_once(
"""async function endCall(notify=true) {
  const user=savedUser;""",
"""async function endCall(notify=true) {
  cancelCallSignalReconnect();
  const user=savedUser;""",
'Call reconnect cleanup on hangup',
)

replace_once(
"""function toggleCallCamera() {
  const track=callStream?.getVideoTracks()[0];
  if(!track) return;
  track.enabled=!track.enabled;
  callCameraEnabled=track.enabled;
  render();
}

let servers = [{ id: 'add-server', icon: '+', name: 'Добавить сервер', add: true }];""",
"""function toggleCallCamera() {
  const track=callStream?.getVideoTracks()[0];
  if(!track) return;
  track.enabled=!track.enabled;
  callCameraEnabled=track.enabled;
  render();
}
async function recoverRtcAfterNetworkReturn(){
  const user=savedUser;
  if(!user?.id)return;
  scheduleCallInboxReconnect(user,true);
  if(callPeer&&callConnection)scheduleCallSignalReconnect(user,callPeer,true);
  for(const [peerId,state] of voicePeers){
    if(['failed','disconnected'].includes(state.pc.connectionState)){
      clearVoicePeerDisconnectTimer(state);
      scheduleVoicePeerRecovery(user,peerId,state);
    }
  }
  if(voiceReconnectContext&&!voiceRoom&&!voiceStream){
    const {channelId,serverId}=voiceReconnectContext;
    if(voiceReconnectTimer){clearTimeout(voiceReconnectTimer);voiceReconnectTimer=null;}
    scheduleVoiceReconnect(user,channelId,serverId);
  }
}
window.addEventListener('online',()=>{recoverRtcAfterNetworkReturn().catch(error=>console.warn('RTC network recovery failed',error));});

let servers = [{ id: 'add-server', icon: '+', name: 'Добавить сервер', add: true }];""",
'Online RTC recovery hook',
)

replace_once(
"""function resetAuthenticatedRuntime() {
  clearDataRealtimeRecovery();
  dmMessagesSyncRevision++;""",
"""function resetAuthenticatedRuntime() {
  clearDataRealtimeRecovery();
  cancelVoiceReconnect();
  cancelAllVoicePeerReconnects();
  cancelCallInboxReconnect();
  cancelCallSignalReconnect();
  resetRtcConfiguration();
  dmMessagesSyncRevision++;""",
'RTC session reset cleanup',
)

required = [
    "supabase.functions.invoke('rtc-config')",
    'async function attemptVoicePeerIceRestart(user,peerId,state)',
    'pc.createOffer({iceRestart:true})',
    'pc.setConfiguration?.(rtcConfiguration);',
    'async function prepareCallConnection(user,peerId,video)',
    'callConnection=new RTCPeerConnection(rtcConfiguration);',
    'connection.setConfiguration?.(rtcConfiguration);',
    'function scheduleCallInboxReconnect(user,immediate=false)',
    'function scheduleCallSignalReconnect(user,peerId,immediate=false)',
    "window.addEventListener('online'",
    'resetRtcConfiguration();',
]
missing=[marker for marker in required if marker not in text]
if missing:
    raise SystemExit('Missing voice/TURN-ready markers: ' + ', '.join(missing))
if "new RTCPeerConnection({iceServers:[{urls:'stun:stun.l.google.com:19302'}]})" in text:
    raise SystemExit('Hard-coded STUN-only RTCPeerConnection remains')
if text.count('new RTCPeerConnection(rtcConfiguration)') != 2:
    raise SystemExit('Expected exactly two TURN-aware RTCPeerConnection constructors')

if changed:
    path.write_text(text, encoding='utf-8')
    print('Applied Vessel voice/calls/reconnect/TURN-ready hardening')
else:
    print('Vessel voice/calls/reconnect/TURN-ready hardening already applied; nothing to change')
