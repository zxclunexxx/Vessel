from pathlib import Path

path = Path('src/main.js')
text = path.read_text(encoding='utf-8')
changed = False

MEDIA_MARKERS = [
    'const targetServerId=getActiveServer()?.dbId||null;',
    "const stream=await navigator.mediaDevices.getUserMedia({audio:true,video:false});",
    "activeChannelId!==targetChannelId||activeChannelKind!=='voice'",
    'const mediaStream=await navigator.mediaDevices.getUserMedia({audio:true,video:!!video});',
    'const accessAfterMedia=await verifyDirectMessageAccess(user,peerId,{notify:false});',
    'const acceptedStream=await navigator.mediaDevices.getUserMedia({audio:true,video:callVideo});',
    'const acceptedAccess=await verifyDirectMessageAccess(user,invite.from,{notify:false});',
]

if all(marker in text for marker in MEDIA_MARKERS):
    print('Media permission context hardening already applied; nothing to change')
    raise SystemExit(0)


def replace_once(old, new, label):
    global text, changed
    if new in text:
        print(f'{label}: already applied')
        return
    if old not in text:
        raise SystemExit(f'{label}: expected source or patched form not found')
    text = text.replace(old, new, 1)
    changed = True


replace_once(
    """    const targetChannelId=activeChannelId;
    voiceStream=await navigator.mediaDevices.getUserMedia({audio:true,video:false});
    voiceChannelId=targetChannelId;
    voiceServerId=getActiveServer()?.dbId||null;
""",
    """    const targetChannelId=activeChannelId;
    const targetServerId=getActiveServer()?.dbId||null;
    const stream=await navigator.mediaDevices.getUserMedia({audio:true,video:false});
    if(savedUser?.id!==user.id||activeChannelId!==targetChannelId||activeChannelKind!=='voice'||getActiveServer()?.dbId!==targetServerId||callConnection||callStream||incomingCall){
      stream.getTracks().forEach(track=>track.stop());
      if(reconnecting)cancelVoiceReconnect();
      return;
    }
    voiceStream=stream;
    voiceChannelId=targetChannelId;
    voiceServerId=targetServerId;
""",
    'voice media context guard',
)

replace_once(
    """  if(signal.type==='offer'){
    callPeer=peerId; callPeerName=callPeerName||'Пользователь';
    if(!callStream) callStream=await navigator.mediaDevices.getUserMedia({audio:true,video:!!video});
    callVideo=!!video; prepareCallConnection(user,peerId,!!video); await callConnection.setRemoteDescription(signal.description);
""",
    """  if(signal.type==='offer'){
    callPeer=peerId; callPeerName=callPeerName||'Пользователь';
    if(!callStream){
      const signalStream=await navigator.mediaDevices.getUserMedia({audio:true,video:!!video});
      const signalAccess=await verifyDirectMessageAccess(user,peerId,{notify:false});
      if(savedUser?.id!==user.id||callPeer!==peerId||signalAccess!==true){
        signalStream.getTracks().forEach(track=>track.stop());
        if(savedUser?.id===user.id&&callPeer===peerId)await endCall(false);
        return;
      }
      callStream=signalStream;
    }
    callVideo=!!video; prepareCallConnection(user,peerId,!!video); await callConnection.setRemoteDescription(signal.description);
""",
    'call signal media context guard',
)

replace_once(
    """    callPeer=peerId; callPeerName=currentDm||'Пользователь'; callVideo=!!video; callAccepted=false; callOffer=null; localIceCandidates=[]; callMicEnabled=true; callCameraEnabled=!!video;
    callStream=await navigator.mediaDevices.getUserMedia({audio:true,video:!!video});
    prepareCallConnection(user,peerId,!!video);
""",
    """    callPeer=peerId; callPeerName=currentDm||'Пользователь'; callVideo=!!video; callAccepted=false; callOffer=null; localIceCandidates=[]; callMicEnabled=true; callCameraEnabled=!!video;
    const mediaStream=await navigator.mediaDevices.getUserMedia({audio:true,video:!!video});
    const accessAfterMedia=await verifyDirectMessageAccess(user,peerId,{notify:false});
    if(savedUser?.id!==user.id||activeDmId!==peerId||callPeer!==peerId||incomingCall||accessAfterMedia!==true){
      mediaStream.getTracks().forEach(track=>track.stop());
      if(savedUser?.id===user.id&&callPeer===peerId)await endCall(false);
      return;
    }
    callStream=mediaStream;
    prepareCallConnection(user,peerId,!!video);
""",
    'outgoing call media context guard',
)

replace_once(
    """  try {
    if(voiceStream)await leaveVoiceRoom();
    callStream=await navigator.mediaDevices.getUserMedia({audio:true,video:callVideo});
    await ensureCallChannel(user,callPeer);
""",
    """  try {
    if(voiceStream)await leaveVoiceRoom();
    if(savedUser?.id!==user.id||callPeer!==invite.from||!callAccepted)return;
    const acceptedStream=await navigator.mediaDevices.getUserMedia({audio:true,video:callVideo});
    const acceptedAccess=await verifyDirectMessageAccess(user,invite.from,{notify:false});
    if(savedUser?.id!==user.id||callPeer!==invite.from||!callAccepted||acceptedAccess!==true){
      acceptedStream.getTracks().forEach(track=>track.stop());
      if(savedUser?.id===user.id&&callPeer===invite.from)await endCall(false);
      return;
    }
    callStream=acceptedStream;
    await ensureCallChannel(user,callPeer);
""",
    'incoming call media context guard',
)

for marker in MEDIA_MARKERS:
    if marker not in text:
        raise SystemExit(f'missing media context hardening marker: {marker}')

if changed:
    path.write_text(text, encoding='utf-8')
    print('Applied media permission session/context hardening')
else:
    print('Media permission context hardening already applied; nothing to change')
