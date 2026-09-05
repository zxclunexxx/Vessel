from pathlib import Path

path=Path('src/main.js')
text=path.read_text(encoding='utf-8')

def replace_once(old,new,label):
    global text
    if old not in text:
        raise SystemExit(f'{label} anchor not found')
    text=text.replace(old,new,1)

# Realtime updates must refresh outgoing requests too (accept/decline by the other user).
old="""    supabase.channel(`vessel-friends-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'friend_requests',filter:`receiver_id=eq.${user.id}`},()=>{window.__vesselSocialLoaded=false;syncSocial(user).then(()=>{if(friendsOpen)render();});}).subscribe(),
    supabase.channel(`vessel-friendships-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'friendships',filter:`user_id=eq.${user.id}`},()=>{window.__vesselSocialLoaded=false;syncSocial(user);}).subscribe(),"""
new="""    supabase.channel(`vessel-friends-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'friend_requests',filter:`receiver_id=eq.${user.id}`},()=>{window.__vesselSocialLoaded=false;syncSocial(user);}).subscribe(),
    supabase.channel(`vessel-friend-requests-out-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'friend_requests',filter:`sender_id=eq.${user.id}`},()=>{window.__vesselSocialLoaded=false;syncSocial(user);}).subscribe(),
    supabase.channel(`vessel-friendships-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'friendships',filter:`user_id=eq.${user.id}`},()=>{window.__vesselSocialLoaded=false;syncSocial(user);}).subscribe(),"""
replace_once(old,new,'outgoing friend request realtime')

# Call invite delivery should be observable by callers instead of silently timing out on a transport error.
old="""async function sendCallInvite(user, peerId, payload) {
  if (!supabase || !user?.id || !peerId) return;
  const channel = supabase.channel(callInboxName(peerId));
  try {
    await subscribeChannel(channel);
    await channel.send({type:'broadcast', event:'call', payload:{from:user.id,to:peerId,...payload}});
  } catch (error) {
    console.warn('Call invite failed', error);
  } finally {
    await supabase.removeChannel(channel);
  }
}"""
new="""async function sendCallInvite(user, peerId, payload) {
  if (!supabase || !user?.id || !peerId) return false;
  const channel = supabase.channel(callInboxName(peerId));
  try {
    await subscribeChannel(channel);
    const result=await channel.send({type:'broadcast', event:'call', payload:{from:user.id,to:peerId,...payload}});
    return result==='ok';
  } catch (error) {
    console.warn('Call invite failed', error);
    return false;
  } finally {
    await supabase.removeChannel(channel).catch(()=>{});
  }
}"""
replace_once(old,new,'call invite delivery')

# A call-in-progress includes a local media stream during setup; do not accept a second invite then.
replace_once("      if (callConnection || incomingCall) {","      if (callConnection || callStream || incomingCall) {",'incoming busy guard')

# Avoid unhandled async signaling errors from WebRTC callbacks.
replace_once("    if (callAccepted) sendCallSignal(user,peerId,{type:'ice',candidate:e.candidate},video);","    if (callAccepted) sendCallSignal(user,peerId,{type:'ice',candidate:e.candidate},video).catch(error=>console.warn('Call ICE send failed',error));",'call ICE error handling')
replace_once("    await handleCallSignal(user,payload.from,payload.signal,payload.video);","    await handleCallSignal(user,payload.from,payload.signal,payload.video).catch(error=>{console.warn('Call signal failed',error);endCall(false);});",'call signal error handling')

# Starting a DM call while an incoming call is waiting is ambiguous. Voice-room audio is released first.
old="""async function startCall(video,user) {
  if(!activeDmId||!supabase||!user?.id){vesselNotice('Открой личный чат с настоящим другом, чтобы начать звонок.','error');return;}
  if(callConnection || callStream){await endCall(true);return;}
  try {
    callPeer=activeDmId; callPeerName=currentDm||'Пользователь'; callVideo=!!video; callAccepted=false; callOffer=null; localIceCandidates=[]; callMicEnabled=true; callCameraEnabled=!!video;
    callStream=await navigator.mediaDevices.getUserMedia({audio:true,video:!!video});
    prepareCallConnection(user,activeDmId,!!video);
    const offer=await callConnection.createOffer();
    await callConnection.setLocalDescription(offer);
    callOffer=serialiseDescription(callConnection.localDescription);
    await sendCallInvite(user,activeDmId,{type:'invite',name:user.name,video:callVideo,offer:callOffer});
    if(callInviteTimer)clearTimeout(callInviteTimer);
    callInviteTimer=setTimeout(()=>{
      if(callConnection&&!callAccepted){vesselNotice('Пользователь не ответил на звонок.');endCall(true);}
    },30000);
    render();
  } catch { await endCall(false); vesselNotice('Не удалось получить доступ к микрофону или камере.','error'); }
}"""
new="""async function startCall(video,user) {
  if(!activeDmId||!supabase||!user?.id){vesselNotice('Открой личный чат с настоящим другом, чтобы начать звонок.','error');return;}
  if(incomingCall){vesselNotice('Сначала ответь на входящий вызов или отклони его.','error');return;}
  if(callConnection || callStream){await endCall(true);return;}
  try {
    if(voiceStream)await leaveVoiceRoom();
    const peerId=activeDmId;
    callPeer=peerId; callPeerName=currentDm||'Пользователь'; callVideo=!!video; callAccepted=false; callOffer=null; localIceCandidates=[]; callMicEnabled=true; callCameraEnabled=!!video;
    callStream=await navigator.mediaDevices.getUserMedia({audio:true,video:!!video});
    prepareCallConnection(user,peerId,!!video);
    const offer=await callConnection.createOffer();
    await callConnection.setLocalDescription(offer);
    callOffer=serialiseDescription(callConnection.localDescription);
    render();
    const delivered=await sendCallInvite(user,peerId,{type:'invite',name:user.name,video:callVideo,offer:callOffer});
    if(!delivered)throw new Error('CALL_INVITE_DELIVERY_FAILED');
    if(callInviteTimer)clearTimeout(callInviteTimer);
    callInviteTimer=setTimeout(()=>{
      if(callConnection&&!callAccepted){vesselNotice('Пользователь не ответил на звонок.');endCall(true);}
    },30000);
  } catch(error) {
    console.warn('Call start failed',error);
    await endCall(false);
    vesselNotice(error?.message==='CALL_INVITE_DELIVERY_FAILED'?'Не удалось доставить вызов. Попробуй ещё раз.':'Не удалось получить доступ к микрофону или камере.','error');
  }
}"""
replace_once(old,new,'outgoing call lifecycle')

# Accepting a DM call leaves an active voice room first and verifies the accept signal was delivered.
old="""async function acceptIncomingCall(user) {
  if (!incomingCall || !user?.id) return;
  const invite=incomingCall; incomingCall=null; callPeer=invite.from; callPeerName=invite.name; callVideo=invite.video; callAccepted=true; callMicEnabled=true; callCameraEnabled=invite.video;
  activeDmId=invite.from; currentDm=invite.name; friendsOpen=false;
  try {
    callStream=await navigator.mediaDevices.getUserMedia({audio:true,video:callVideo});
    await ensureCallChannel(user,callPeer);
    await sendCallInvite(user,callPeer,{type:'accept',video:callVideo});
    render();
  } catch {
    await sendCallInvite(user,callPeer,{type:'decline'});
    await endCall(false);
    vesselNotice('Не удалось получить доступ к микрофону или камере.','error');
  }
}"""
new="""async function acceptIncomingCall(user) {
  if (!incomingCall || !user?.id) return;
  const invite=incomingCall; incomingCall=null; callPeer=invite.from; callPeerName=invite.name; callVideo=invite.video; callAccepted=true; callMicEnabled=true; callCameraEnabled=invite.video;
  activeDmId=invite.from; currentDm=invite.name; friendsOpen=false; window.__vesselDmLoaded=false;
  try {
    if(voiceStream)await leaveVoiceRoom();
    callStream=await navigator.mediaDevices.getUserMedia({audio:true,video:callVideo});
    await ensureCallChannel(user,callPeer);
    const delivered=await sendCallInvite(user,callPeer,{type:'accept',video:callVideo});
    if(!delivered)throw new Error('CALL_ACCEPT_DELIVERY_FAILED');
    render();
  } catch(error) {
    console.warn('Call accept failed',error);
    await sendCallInvite(user,callPeer,{type:'decline'});
    await endCall(false);
    vesselNotice(error?.message==='CALL_ACCEPT_DELIVERY_FAILED'?'Не удалось подтвердить вызов. Попробуйте снова.':'Не удалось получить доступ к микрофону или камере.','error');
  }
}"""
replace_once(old,new,'incoming call lifecycle')

# Never fall back to a cached localStorage identity when sending a hangup signal.
replace_once("  const user=savedUser || JSON.parse(localStorage.getItem('vesselUser')||'null');","  const user=savedUser;",'hangup authenticated identity')

# Friends home is its own navigation state, not a stale DM layered over a server channel.
replace_once("  const canManageChannel=Boolean(!currentDm&&activeChannelId&&activeServer?.dbId&&activeServer.role==='owner');","  const canManageChannel=Boolean(!friendsOpen&&!currentDm&&activeChannelId&&activeServer?.dbId&&activeServer.role==='owner');",'friends channel settings isolation')
replace_once("    : activeDmId ? `<button id=\"audio-call\" title=\"Аудиозвонок\">📞</button><button id=\"video-call\" title=\"Видеозвонок\">🎥</button>` : '';","    : (!friendsOpen&&activeDmId) ? `<button id=\"audio-call\" title=\"Аудиозвонок\">📞</button><button id=\"video-call\" title=\"Видеозвонок\">🎥</button>` : '';",'friends call isolation')

old="""<header class="chat-head"><div><h1><span>${currentDm?'@':activeChannelKind==='voice'?'⌁':'#'}</span> ${escapeHtml(currentDm || activeChannelName)}</h1><p>${currentDm?'Личная переписка':activeChannelKind==='voice'?'Голосовая комната':escapeHtml(activeServer?.name || 'Vessel')}</p></div><div class="head-actions"><button id="mobile-nav" title="Каналы">☰</button>${canManageChannel?`<button id="channel-settings" title="Настройки канала">•••</button>`:''}${callActions}<button id="join-voice" class="join-voice ${activeChannelKind==='voice'?'':'hidden'}">${voiceStream?(voiceChannelId===activeChannelId?'Выйти':'Переключиться'):'Войти'}</button><button id="mute-voice" class="join-voice ${voiceStream&&voiceChannelId===activeChannelId?'':'hidden'}">${voiceStream?.getAudioTracks()[0]?.enabled===false?'🔇':'🎙'}</button>"""
new="""<header class="chat-head"><div><h1><span>${friendsOpen?'👥':currentDm?'@':activeChannelKind==='voice'?'⌁':'#'}</span> ${friendsOpen?'Друзья':escapeHtml(currentDm || activeChannelName)}</h1><p>${friendsOpen?'Личные контакты и заявки':currentDm?'Личная переписка':activeChannelKind==='voice'?'Голосовая комната':escapeHtml(activeServer?.name || 'Vessel')}</p></div><div class="head-actions"><button id="mobile-nav" title="Каналы">☰</button>${canManageChannel?`<button id="channel-settings" title="Настройки канала">•••</button>`:''}${callActions}<button id="join-voice" class="join-voice ${!friendsOpen&&activeChannelKind==='voice'?'':'hidden'}">${voiceStream?(voiceChannelId===activeChannelId?'Выйти':'Переключиться'):'Войти'}</button><button id="mute-voice" class="join-voice ${!friendsOpen&&voiceStream&&voiceChannelId===activeChannelId?'':'hidden'}">${voiceStream?.getAudioTracks()[0]?.enabled===false?'🔇':'🎙'}</button>"""
replace_once(old,new,'friends header isolation')

# In friends home, right sidebar should summarize friends instead of showing unrelated server members.
replace_once("      <aside class=\"members\">${voiceStream?`<div class=\"voice-status\">🎙 В голосовой комнате: ${Math.max(1,voiceParticipants.length)}</div>`:''}${membersList}</aside>","      <aside class=\"members\">${friendsOpen?`<div class=\"members-title\">ДРУЗЬЯ — ${friends.length}</div><div class=\"dm-empty\">${friendRequests.length?`Входящих заявок: ${friendRequests.length}`:outgoingFriendRequests.length?`Исходящих заявок: ${outgoingFriendRequests.length}`:'Выбери друга, чтобы открыть личный чат.'}</div>`:`${voiceStream?`<div class=\"voice-status\">🎙 В голосовой комнате: ${Math.max(1,voiceParticipants.length)}</div>`:''}${membersList}`}</aside>",'friends sidebar isolation')

old="""  document.querySelector('#friends-tab').addEventListener('click',()=>{friendsOpen=true;currentDm=null;render();});
  document.querySelector('#friends-button').addEventListener('click',()=>{friendsOpen=true;currentDm=null;render();});"""
new="""  const openFriendsHome=()=>{friendsOpen=true;currentDm=null;activeDmId=null;dmMessages=[];window.__vesselDmLoaded=false;render();};
  document.querySelector('#friends-tab').addEventListener('click',openFriendsHome);
  document.querySelector('#friends-button').addEventListener('click',openFriendsHome);"""
replace_once(old,new,'friends navigation cleanup')

# Guardrails: all high-risk regressions in this patch must be absent/present as expected.
for forbidden in [
    "savedUser || JSON.parse(localStorage.getItem('vesselUser')",
    "if (callConnection || incomingCall)",
    "#friends-tab').addEventListener('click',()=>{friendsOpen=true;currentDm=null;render();",
]:
    if forbidden in text:
        raise SystemExit(f'call/friends regression remains: {forbidden}')
for required in [
    'vessel-friend-requests-out-',
    "if(voiceStream)await leaveVoiceRoom();",
    "if(incomingCall){vesselNotice('Сначала ответь на входящий вызов или отклони его.'",
    "document.querySelector('#end-call')?.addEventListener('click',()=>endCall(true));",
    'const openFriendsHome=()=>{friendsOpen=true;currentDm=null;activeDmId=null;',
]:
    if required not in text:
        raise SystemExit(f'missing call/friends hardening: {required}')

path.write_text(text,encoding='utf-8')
print('Applied friends home and call lifecycle hardening')
