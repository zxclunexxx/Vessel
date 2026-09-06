from pathlib import Path

# Patch revision: validates call access at the last safe moment before media acquisition.
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


replace_once(
    """    if (payload.type === 'invite') {
      const caller=await resolveCallableFriend(user,payload.from);
      if(!caller){console.warn('Ignored call invite from non-friend');return;}
""",
    """    if (payload.type === 'invite') {
      const caller=await resolveCallableFriend(user,payload.from);
      if(callInboxChannel!==inbox||savedUser?.id!==user.id)return;
      if(!caller){console.warn('Ignored call invite from non-friend');return;}
""",
    'incoming call session guard',
)

replace_once(
    """  try {
    if(voiceStream)await leaveVoiceRoom();
    const peerId=activeDmId;
    callPeer=peerId; callPeerName=currentDm||'Пользователь'; callVideo=!!video; callAccepted=false; callOffer=null; localIceCandidates=[]; callMicEnabled=true; callCameraEnabled=!!video;
""",
    """  const peerId=activeDmId;
  try {
    if((await verifyDirectMessageAccess(user,peerId))!==true)return;
    if(savedUser?.id!==user.id||activeDmId!==peerId)return;
    if(voiceStream)await leaveVoiceRoom();
    if(savedUser?.id!==user.id||activeDmId!==peerId)return;
    callPeer=peerId; callPeerName=currentDm||'Пользователь'; callVideo=!!video; callAccepted=false; callOffer=null; localIceCandidates=[]; callMicEnabled=true; callCameraEnabled=!!video;
""",
    'outgoing call friendship/context guard',
)

replace_once(
    """async function acceptIncomingCall(user) {
  if (!incomingCall || !user?.id) return;
  const invite=incomingCall; incomingCall=null; callPeer=invite.from; callPeerName=invite.name; callVideo=invite.video; callAccepted=true; callMicEnabled=true; callCameraEnabled=invite.video;
  activeDmId=invite.from; currentDm=invite.name; friendsOpen=false; window.__vesselDmLoaded=false;
  try {
""",
    """async function acceptIncomingCall(user) {
  if (!incomingCall || !user?.id) return;
  const invite=incomingCall;
  const access=await verifyDirectMessageAccess(user,invite.from);
  if(incomingCall!==invite||savedUser?.id!==user.id)return;
  if(access!==true){
    incomingCall=null;
    await sendCallInvite(user,invite.from,{type:'decline'});
    render();
    return;
  }
  incomingCall=null; callPeer=invite.from; callPeerName=invite.name; callVideo=invite.video; callAccepted=true; callMicEnabled=true; callCameraEnabled=invite.video;
  activeDmId=invite.from; currentDm=invite.name; friendsOpen=false; window.__vesselDmLoaded=false;
  try {
""",
    'incoming call acceptance friendship guard',
)

for marker in [
    'if(callInboxChannel!==inbox||savedUser?.id!==user.id)return;',
    'if((await verifyDirectMessageAccess(user,peerId))!==true)return;',
    'if(savedUser?.id!==user.id||activeDmId!==peerId)return;',
    'const access=await verifyDirectMessageAccess(user,invite.from);',
    'if(incomingCall!==invite||savedUser?.id!==user.id)return;',
]:
    if marker not in text:
        raise SystemExit(f'missing call access race hardening marker: {marker}')

if changed:
    path.write_text(text, encoding='utf-8')
    print('Applied call friendship and async context hardening')
else:
    print('Call friendship and async context hardening already applied; nothing to change')
