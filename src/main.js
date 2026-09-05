import './style.css';

const SUPABASE_URL = 'https://zqbveciunttbvvxhqvqs.supabase.co';
const SUPABASE_KEY = 'sb_publishable_vjT6aZKGuklvcCmmqcb-Zw_E5zc-434';
const supabase = window.supabase?.createClient(SUPABASE_URL, SUPABASE_KEY);
let activeChannelId = null;
let dbChannels = [];
let voiceStream = null;
let voiceRoom = null;
let callStream = null;
let remoteCallStream = null;
let callPeer = null;
let callPeerName = '';
let callConnection = null;
let callChannel = null;
let callInboxChannel = null;
let pendingIceCandidates = [];
let localIceCandidates = [];
let callOffer = null;
let callVideo = false;
let callAccepted = false;
let incomingCall = null;
let callMicEnabled = true;
let callCameraEnabled = true;
let activeServerIndex = Number(localStorage.getItem('vesselActiveServer') || 0);
let activeChannelName = 'общий';
let activeChannelKind = 'text';
let currentDm = null;
let activeDmId = null;
let friendsOpen = false;
let friends = [];
let friendRequests = [];
let dmMessages = [];
let notifications = [];
let serverMembers = [];
const savedChannelMap = JSON.parse(localStorage.getItem('vesselChannelMap') || '{}');
async function syncSupabaseMessages() {
  if (!supabase || window.__vesselDbLoaded) return;
  const {data: channels} = await supabase.from('channels').select('id').limit(1);
  if (!channels?.[0]) return;
  activeChannelId = channels[0].id;
  const {data} = await supabase.from('messages').select('body,created_at,profiles(username,avatar_color)').eq('channel_id',activeChannelId).order('created_at',{ascending:true}).limit(100);
  if (data?.length) { messages=data.map(m=>({name:m.profiles?.username||'Участник',time:new Date(m.created_at).toLocaleString('ru-RU'),color:m.profiles?.avatar_color||'#8b7cff',text:m.body})); render(); }
  window.__vesselDbLoaded=true;
}
async function loadChannelMessages(channelId) {
  if (!supabase || !channelId) return;
  const {data} = await supabase.from('messages').select('body,created_at,profiles(username,avatar_color)').eq('channel_id',channelId).order('created_at',{ascending:true}).limit(100);
  messages = data?.length ? data.map(m=>({name:m.profiles?.username||'Участник',time:new Date(m.created_at).toLocaleString('ru-RU'),color:m.profiles?.avatar_color||'#8b7cff',text:m.body})) : [];
  render();
}
async function syncSupabaseServers(user) {
  if (!supabase || window.__vesselServersLoaded || !user?.id) return;
  const {data:memberships} = await supabase.from('server_members').select('server_id,role').eq('user_id',user.id);
  const memberIds=(memberships||[]).map(row=>row.server_id);
  const [ownedResult,memberResult]=await Promise.all([
    supabase.from('servers').select('id,name,icon,owner_id').eq('owner_id',user.id).order('created_at'),
    memberIds.length ? supabase.from('servers').select('id,name,icon,owner_id').in('id',memberIds).order('created_at') : Promise.resolve({data:[]})
  ]);
  const all=[...(ownedResult.data||[]),...(memberResult.data||[]).filter(s=>!(ownedResult.data||[]).some(o=>o.id===s.id))];
  window.__vesselServersLoaded=true;
  if (all.length) { servers=[...all.map(s=>({id:s.id,dbId:s.id,icon:s.icon,name:s.name,role:s.owner_id===user.id?'owner':(memberships||[]).find(m=>m.server_id===s.id)?.role||'member'})),{icon:'+',name:'Добавить сервер',add:true}]; if(activeServerIndex>=servers.length-1) activeServerIndex=0; render(); }
}
async function syncSupabaseChannels(server) {
  if (!supabase || !server?.dbId || server.__channelsLoaded) return;
  const {data} = await supabase.from('channels').select('id,name,kind,position').eq('server_id',server.dbId).order('position');
  if (data?.length) { dbChannels=data; savedChannelMap[server.id]=data; saveChannelMap(); if (server.id===servers[activeServerIndex]?.id) { activeChannelId=data[0].id; activeChannelName=data[0].name; activeChannelKind=data[0].kind; } render(); if(server.id===servers[activeServerIndex]?.id) loadChannelMessages(activeChannelId); }
  server.__channelsLoaded=true;
}
async function syncServerMembers(user, server) {
  if (!supabase || !user?.id || !server?.dbId) { serverMembers=[]; return; }
  if (window.__vesselMembersServerId === server.dbId) return;
  const {data: memberships, error} = await supabase.from('server_members').select('user_id,role').eq('server_id',server.dbId);
  if (error) { console.warn('Server members failed', error); serverMembers=[]; return; }
  const ids=(memberships||[]).map(row=>row.user_id).filter(Boolean);
  let profiles=[];
  if(ids.length){
    const result=await supabase.from('profiles').select('id,username,avatar_color,status').in('id',ids);
    profiles=result.data||[];
  }
  serverMembers=(memberships||[]).map(member=>{
    const profile=profiles.find(item=>item.id===member.user_id);
    return {id:member.user_id,role:member.role,username:profile?.username||'Участник',avatar_color:profile?.avatar_color||'#8b7cff',status:profile?.status||'в сети'};
  });
  window.__vesselMembersServerId=server.dbId;
  if(document.querySelector('#app')) render();
}

async function findAndRequestFriend(user) {
  const query=prompt('Введи точное имя пользователя:');
  if(!query?.trim()) return;
  if(!supabase||!user?.id){alert('Войди через настоящий аккаунт, чтобы добавлять друзей.');return;}
  const {data:found,error}=await supabase.from('profiles').select('id,username,avatar_color,status').ilike('username',query.trim()).limit(1);
  if(error||!found?.[0]){alert('Пользователь не найден.');return;}
  const target=found[0];
  if(target.id===user.id){alert('Нельзя добавить самого себя.');return;}
  if(friends.some(friend=>friend.id===target.id)){alert(`${target.username} уже у тебя в друзьях.`);return;}
  const {data:existing}=await supabase.from('friend_requests').select('id,status,sender_id,receiver_id').or(`and(sender_id.eq.${user.id},receiver_id.eq.${target.id}),and(sender_id.eq.${target.id},receiver_id.eq.${user.id})`).limit(1);
  const request=existing?.[0];
  if(request?.status==='pending'){
    alert(request.receiver_id===user.id ? `${target.username} уже отправил тебе заявку. Открой раздел «Друзья».` : 'Заявка уже отправлена.');
    return;
  }
  const {error:sendError}=await supabase.from('friend_requests').upsert({sender_id:user.id,receiver_id:target.id,status:'pending',updated_at:new Date().toISOString()},{onConflict:'sender_id,receiver_id'});
  alert(sendError?'Не удалось отправить заявку.':`Заявка пользователю ${target.username} отправлена.`);
}

async function syncSocial(user) {
  if (!supabase || !user?.id || window.__vesselSocialLoaded) return;
  const {data: links} = await supabase.from('friendships').select('friend_id').eq('user_id', user.id);
  const ids = (links || []).map(row => row.friend_id).filter(Boolean);
  friends = [];
  if (ids.length) {
    const {data: profiles} = await supabase.from('profiles').select('id,username,avatar_color,status').in('id', ids);
    friends = profiles || [];
  }
  const {data: requests} = await supabase.from('friend_requests').select('id,sender_id,status,profiles!friend_requests_sender_id_fkey(username,avatar_color)').eq('receiver_id', user.id).eq('status','pending');
  friendRequests = requests || [];
  window.__vesselSocialLoaded = true;
  if (document.querySelector('#app')) render();
}
async function syncNotifications(user) {
  if (!supabase || !user?.id || window.__vesselNotificationsLoaded) return;
  const {data}=await supabase.from('notifications').select('id,type,title,body,data,read_at,created_at').eq('user_id',user.id).order('created_at',{ascending:false}).limit(30);
  notifications=data||[]; window.__vesselNotificationsLoaded=true;
  if (document.querySelector('#app')) render();
}
async function loadDirectMessages(user, friendId) {
  if (!supabase || !user?.id || !friendId) return;
  const {data} = await supabase.from('direct_messages').select('id,sender_id,receiver_id,body,created_at,profiles!direct_messages_sender_id_fkey(username,avatar_color)').or(`and(sender_id.eq.${user.id},receiver_id.eq.${friendId}),and(sender_id.eq.${friendId},receiver_id.eq.${user.id})`).order('created_at',{ascending:true});
  dmMessages = (data || []).map(row => ({name:row.profiles?.username || 'Пользователь',time:new Date(row.created_at).toLocaleString('ru-RU'),color:row.profiles?.avatar_color || '#8b7cff',text:row.body}));
  render();
}
async function uploadVesselFile(file, user) {
  if (!supabase || !user?.id) { alert('Для загрузки файлов нужен настоящий аккаунт.'); return null; }
  const safeName=file.name.replace(/[^a-zA-Z0-9._-]/g,'_');
  const path=`${user.id}/${crypto.randomUUID()}-${safeName}`;
  const {error}=await supabase.storage.from('vessel-files').upload(path,file,{contentType:file.type||'application/octet-stream',upsert:false});
  if(error){alert(`Файл не загрузился: ${error.message}`);return null;}
  return {name:file.name,path,type:file.type||'application/octet-stream',size:file.size};
}

function callRoomName(a,b) { return `vessel-call-${[a,b].sort().join('-')}`; }
function callInboxName(userId) { return `vessel-call-inbox-${userId}`; }
function serialiseDescription(description) { return description ? {type: description.type, sdp: description.sdp} : null; }
function subscribeChannel(channel) {
  if (channel.__subscribed) return Promise.resolve(channel);
  return new Promise((resolve, reject) => {
    let settled = false;
    const timer = setTimeout(() => {
      if (!settled) { settled = true; reject(new Error('Realtime channel timeout')); }
    }, 10000);
    channel.subscribe(status => {
      if (settled) return;
      if (status === 'SUBSCRIBED') {
        settled = true;
        clearTimeout(timer);
        channel.__subscribed = true;
        resolve(channel);
      } else if (['CHANNEL_ERROR', 'TIMED_OUT', 'CLOSED'].includes(status)) {
        settled = true;
        clearTimeout(timer);
        reject(new Error(`Realtime channel ${status}`));
      }
    });
  });
}
async function sendCallInvite(user, peerId, payload) {
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
}
async function ensureCallInbox(user) {
  if (!supabase || !user?.id) return null;
  const name = callInboxName(user.id);
  if (callInboxChannel?.__roomName === name && callInboxChannel.__subscribed) return callInboxChannel;
  if (callInboxChannel) await supabase.removeChannel(callInboxChannel);
  callInboxChannel = supabase.channel(name);
  callInboxChannel.__roomName = name;
  callInboxChannel.on('broadcast', {event:'call'}, async ({payload}) => {
    if (!payload || payload.to !== user.id) return;
    if (payload.type === 'invite') {
      if (callConnection || incomingCall) {
        await sendCallInvite(user, payload.from, {type:'busy'});
        return;
      }
      incomingCall = {from:payload.from, name:payload.name || 'Пользователь', video:!!payload.video, offer:payload.offer};
      render();
      return;
    }
    if (payload.from !== callPeer) return;
    if (payload.type === 'accept') {
      callAccepted = true;
      await ensureCallChannel(user, callPeer);
      if (callOffer) await sendCallSignal(user, callPeer, {type:'offer', description:callOffer}, callVideo);
      await flushLocalIceCandidates(user, callPeer, callVideo);
      render();
      return;
    }
    if (payload.type === 'decline' || payload.type === 'busy') {
      alert(payload.type === 'busy' ? 'Пользователь уже разговаривает.' : 'Вызов отклонён.');
      await endCall(false);
      return;
    }
    if (payload.type === 'bye') await endCall(false);
  });
  try { await subscribeChannel(callInboxChannel); } catch (error) { console.warn('Call inbox failed', error); }
  return callInboxChannel;
}
async function ensureCallChannel(user, peerId) {
  if (!supabase || !user?.id || !peerId) return null;
  const name=callRoomName(user.id,peerId);
  if(callChannel?.__roomName===name && callChannel.__subscribed) return callChannel;
  if(callChannel) await supabase.removeChannel(callChannel);
  callChannel=supabase.channel(name);
  callChannel.__roomName=name;
  callChannel.on('broadcast',{event:'signal'},async({payload})=>{
    if(!payload || payload.to!==user.id) return;
    await handleCallSignal(user,payload.from,payload.signal,payload.video);
  });
  await subscribeChannel(callChannel);
  return callChannel;
}
async function sendCallSignal(user,peerId,signal,video) {
  const room=await ensureCallChannel(user,peerId); if(!room)return;
  await room.send({type:'broadcast',event:'signal',payload:{from:user.id,to:peerId,signal,video:!!video}});
}
async function flushLocalIceCandidates(user, peerId, video) {
  if (!callAccepted || !localIceCandidates.length) return;
  const candidates = localIceCandidates.splice(0);
  for (const candidate of candidates) await sendCallSignal(user, peerId, {type:'ice', candidate}, video);
}
function prepareCallConnection(user,peerId,video) {
  if (callConnection) return callConnection;
  callConnection=new RTCPeerConnection({iceServers:[{urls:'stun:stun.l.google.com:19302'}]});
  callConnection.onicecandidate=e=>{
    if (!e.candidate) return;
    if (callAccepted) sendCallSignal(user,peerId,{type:'ice',candidate:e.candidate},video);
    else localIceCandidates.push(e.candidate);
  };
  callConnection.ontrack=e=>{remoteCallStream=e.streams[0];const el=document.querySelector('#remote-video');if(el){el.srcObject=remoteCallStream;el.play().catch(()=>{});} };
  const connection = callConnection;
  callConnection.onconnectionstatechange=()=>{if(connection===callConnection&&['failed','closed'].includes(connection.connectionState)){endCall(false);}};
  if(callStream) callStream.getTracks().forEach(track=>callConnection.addTrack(track,callStream));
  return callConnection;
}
async function handleCallSignal(user,peerId,signal,video) {
  if(signal.type==='bye'){endCall(false);return;}
  if(signal.type==='ice'){if(callConnection?.remoteDescription) await callConnection.addIceCandidate(signal.candidate); else pendingIceCandidates.push(signal.candidate);return;}
  if(signal.type==='offer'){
    callPeer=peerId; callPeerName=callPeerName||'Пользователь';
    if(!callStream) callStream=await navigator.mediaDevices.getUserMedia({audio:true,video:!!video});
    callVideo=!!video; prepareCallConnection(user,peerId,!!video); await callConnection.setRemoteDescription(signal.description);
    for(const candidate of pendingIceCandidates) await callConnection.addIceCandidate(candidate); pendingIceCandidates=[];
    const answer=await callConnection.createAnswer(); await callConnection.setLocalDescription(answer); await sendCallSignal(user,peerId,{type:'answer',description:answer},video); render(); return;
  }
  if(signal.type==='answer'&&callConnection){await callConnection.setRemoteDescription(signal.description);for(const candidate of pendingIceCandidates)await callConnection.addIceCandidate(candidate);pendingIceCandidates=[];render();}
}
async function startCall(video,user) {
  if(!activeDmId||!supabase||!user?.id){alert('Открой личный чат с настоящим другом, чтобы начать звонок.');return;}
  if(callConnection || callStream){endCall(true);return;}
  try {
    callPeer=activeDmId; callPeerName=currentDm||'Пользователь'; callVideo=!!video; callAccepted=false; callOffer=null; localIceCandidates=[]; callMicEnabled=true; callCameraEnabled=!!video;
    callStream=await navigator.mediaDevices.getUserMedia({audio:true,video:!!video});
    prepareCallConnection(user,activeDmId,!!video);
    const offer=await callConnection.createOffer();
    await callConnection.setLocalDescription(offer);
    callOffer=serialiseDescription(callConnection.localDescription);
    await sendCallInvite(user,activeDmId,{type:'invite',name:user.name,video:callVideo,offer:callOffer});
    render();
  } catch { await endCall(false); alert('Не удалось получить доступ к микрофону или камере.'); }
}
async function acceptIncomingCall(user) {
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
    alert('Не удалось получить доступ к микрофону или камере.');
  }
}
async function rejectIncomingCall(user) {
  if (!incomingCall) return;
  const invite=incomingCall; incomingCall=null;
  await sendCallInvite(user,invite.from,{type:'decline'});
  render();
}
async function endCall(notify=true) {
  const user=savedUser || JSON.parse(localStorage.getItem('vesselUser')||'null');
  const peer=callPeer;
  const room=callChannel;
  const connection=callConnection;
  callConnection=null;
  callChannel=null;
  connection?.close();
  callStream?.getTracks().forEach(track=>track.stop());
  remoteCallStream?.getTracks?.().forEach(track=>track.stop?.());
  callStream=null;
  remoteCallStream=null;
  callPeer=null;
  callPeerName='';
  pendingIceCandidates=[];
  localIceCandidates=[];
  callOffer=null;
  callVideo=false;
  callAccepted=false;
  callMicEnabled=true;
  callCameraEnabled=true;
  render();
  if(room&&supabase) supabase.removeChannel(room).catch(()=>{});
  if(notify&&peer&&user?.id) sendCallInvite(user,peer,{type:'bye'}).catch(()=>{});
}

function toggleCallMicrophone() {
  const track=callStream?.getAudioTracks()[0];
  if(!track) return;
  track.enabled=!track.enabled;
  callMicEnabled=track.enabled;
  render();
}

function toggleCallCamera() {
  const track=callStream?.getVideoTracks()[0];
  if(!track) return;
  track.enabled=!track.enabled;
  callCameraEnabled=track.enabled;
  render();
}

let servers = [{ id: 'add-server', icon: '+', name: 'Добавить сервер', add: true }];
if (activeServerIndex < 0) activeServerIndex = 0;

function serverChannels() {
  const server = servers[activeServerIndex];
  return savedChannelMap[server?.id] || [];
}

function saveChannelMap() {
  localStorage.setItem('vesselChannelMap', JSON.stringify(savedChannelMap));
}

let messages = [];
function connectSupabaseRealtime(user) {
  if (!supabase || !user?.id || window.__vesselRealtimeChannels) return;
  window.__vesselRealtimeChannels = [
    supabase.channel(`vessel-dm-${user.id}`).on('postgres_changes',{event:'INSERT',schema:'public',table:'direct_messages'},payload=>{
      const row=payload.new;
      if(activeDmId && (row.sender_id===activeDmId || row.receiver_id===activeDmId)){ window.__vesselDmLoaded=false; loadDirectMessages(user,activeDmId); }
    }).subscribe(),
    supabase.channel(`vessel-friends-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'friend_requests',filter:`receiver_id=eq.${user.id}`},()=>{window.__vesselSocialLoaded=false;syncSocial(user).then(()=>{if(friendsOpen)render();});}).subscribe(),
    supabase.channel(`vessel-friendships-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'friendships',filter:`user_id=eq.${user.id}`},()=>{window.__vesselSocialLoaded=false;syncSocial(user);}).subscribe(),
    supabase.channel(`vessel-channel-messages-${user.id}`).on('postgres_changes',{event:'INSERT',schema:'public',table:'messages'},payload=>{
      if(payload.new.channel_id===activeChannelId && payload.new.author_id!==user.id){messages.push({name:'Участник',time:'только что',color:'#8b7cff',text:payload.new.body});render();}
    }).subscribe(),
    supabase.channel(`vessel-notifications-${user.id}`).on('postgres_changes',{event:'INSERT',schema:'public',table:'notifications',filter:`user_id=eq.${user.id}`},payload=>{notifications=[payload.new,...notifications];render();}).subscribe()
  ];
}

let savedUser = null;

async function bootstrapAuth() {
  if (!supabase) {
    console.error('Supabase client is unavailable.');
    savedUser = null;
    return;
  }

  // One-time cleanup of the old prototype runtime. These keys previously allowed
  // an unauthenticated local user and fake servers/messages to masquerade as real data.
  if (localStorage.getItem('vesselRuntimeV2') !== '1') {
    ['vesselUser','vesselToken','vesselServers','vesselMessages','vesselChannelMap','vesselActiveServer'].forEach(key => localStorage.removeItem(key));
    localStorage.setItem('vesselRuntimeV2', '1');
    activeServerIndex = 0;
    Object.keys(savedChannelMap).forEach(key => delete savedChannelMap[key]);
  }

  const {data, error} = await supabase.auth.getSession();
  if (error) {
    console.error('Unable to restore Supabase session', error);
    savedUser = null;
    return;
  }

  const session = data?.session;
  if (!session?.user) {
    localStorage.removeItem('vesselUser');
    localStorage.removeItem('vesselToken');
    savedUser = null;
    return;
  }

  const authUser = session.user;
  const {data: profile, error: profileError} = await supabase.from('profiles').select('id,username,email,status,avatar_color').eq('id', authUser.id).maybeSingle();
  if (profileError) console.warn('Profile load failed', profileError);

  savedUser = {
    id: authUser.id,
    name: profile?.username || authUser.user_metadata?.username || authUser.email?.split('@')[0] || 'Пользователь',
    email: profile?.email || authUser.email || '',
    status: profile?.status || 'online',
    avatarColor: profile?.avatar_color || '#8b7cff'
  };
  // Cache only. render() never trusts this value until getSession() succeeded.
  localStorage.setItem('vesselUser', JSON.stringify(savedUser));
}


async function joinByInvite(code, user) {
  if (!supabase || !user?.id) { alert('Для вступления нужен настоящий аккаунт.'); return false; }
  const {data:invite,error}=await supabase.from('server_invites').select('id,server_id,role,max_uses,uses,expires_at').eq('code',code.trim().toUpperCase()).maybeSingle();
  if(error || !invite){alert('Код приглашения не найден.');return false;}
  if(invite.expires_at && new Date(invite.expires_at)<new Date()){alert('Срок действия приглашения истёк.');return false;}
  if(invite.max_uses>0 && invite.uses>=invite.max_uses){alert('Приглашение больше недействительно.');return false;}
  const {error:joinError}=await supabase.from('server_members').upsert({server_id:invite.server_id,user_id:user.id,role:invite.role});
  if(joinError){alert('Не удалось вступить в сервер.');return false;}
  window.__vesselServersLoaded=false; alert('Ты вступил в сервер.'); render(); return true;
}

function render() {
  if (!savedUser) {
    document.querySelector('#app').innerHTML = `
      <main class="auth-page"><div class="auth-glow"></div><section class="auth-card">
        <div class="auth-logo">◈</div><h1>Добро пожаловать<br><span>в Vessel</span></h1>
        <p class="auth-subtitle">Твоё пространство для общения,<br>команд и идей.</p>
        <form class="auth-form"><label>Имя пользователя<input name="name" required minlength="2" placeholder="Например, Артём" /></label><label>Электронная почта<input name="email" type="email" required placeholder="you@example.com" /></label><label>Пароль<input name="password" type="password" required minlength="6" placeholder="Минимум 6 символов" /></label><button class="primary" type="submit">Создать аккаунт <span>→</span></button></form>
        <button class="auth-switch" type="button" id="auth-switch">У меня уже есть аккаунт</button><small>Продолжая, ты принимаешь правила Vessel</small>
      </section></main>`;
    const authForm = document.querySelector('.auth-form');
    const authSwitch = document.querySelector('#auth-switch');
    const setAuthMode = mode => {
      authForm.dataset.mode = mode;
      if (mode === 'login') {
        authForm.innerHTML = '<label>Электронная почта<input name="email" type="email" required placeholder="you@example.com" /></label><label>Пароль<input name="password" type="password" required minlength="6" placeholder="Твой пароль" /></label><button class="primary" type="submit">Войти <span>→</span></button>';
        authSwitch.textContent = 'Создать новый аккаунт';
      } else {
        authForm.innerHTML = '<label>Имя пользователя<input name="name" required minlength="2" placeholder="Например, Артём" /></label><label>Электронная почта<input name="email" type="email" required placeholder="you@example.com" /></label><label>Пароль<input name="password" type="password" required minlength="6" placeholder="Минимум 6 символов" /></label><button class="primary" type="submit">Создать аккаунт <span>→</span></button>';
        authSwitch.textContent = 'У меня уже есть аккаунт';
      }
    };
    authForm.addEventListener('submit', async e => {
      e.preventDefault();
      if (!supabase) { alert('Сервис авторизации временно недоступен.'); return; }
      const form = e.currentTarget;
      const data = new FormData(form);
      const mode = form.dataset.mode || 'signup';
      const submit = form.querySelector('button[type="submit"]');
      submit.disabled = true;
      try {
        if (mode === 'login') {
          const {error} = await supabase.auth.signInWithPassword({email:data.get('email'), password:data.get('password')});
          if (error) throw error;
          await bootstrapAuth();
          render();
          return;
        }
        const payload = {name:String(data.get('name') || '').trim(), email:String(data.get('email') || '').trim(), password:String(data.get('password') || '')};
        const {data: result, error} = await supabase.auth.signUp({email:payload.email,password:payload.password,options:{data:{username:payload.name}}});
        if (error) throw error;
        if (!result.session) {
          alert('Аккаунт создан. Если подтверждение почты включено, открой письмо от Vessel, а затем войди.');
          setAuthMode('login');
          return;
        }
        await bootstrapAuth();
        render();
      } catch (error) {
        console.error('Authentication failed', error);
        alert(error?.message || 'Не удалось выполнить авторизацию.');
      } finally {
        submit.disabled = false;
      }
    });
    authSwitch.addEventListener('click', () => setAuthMode((authForm.dataset.mode || 'signup') === 'login' ? 'signup' : 'login'));
    return;
  }
  const user = savedUser;
  connectSupabaseRealtime(user); ensureCallInbox(user).catch(()=>{}); syncSupabaseMessages(); syncSupabaseServers(user); syncSupabaseChannels(servers[activeServerIndex]); syncServerMembers(user,servers[activeServerIndex]); syncSocial(user); syncNotifications(user); if (activeDmId && callConnection) { ensureCallChannel(user,activeDmId).catch(()=>{}); } if (activeDmId && !window.__vesselDmLoaded) { window.__vesselDmLoaded=true; loadDirectMessages(user,activeDmId); }
  const callInProgress=Boolean(callConnection||callStream);
  const callActions=callInProgress
    ? `<button id="toggle-call-mic" class="call-control" title="${callMicEnabled?'Выключить микрофон':'Включить микрофон'}">${callMicEnabled?'🎙':'🔇'}</button>${callVideo?`<button id="toggle-call-camera" class="call-control" title="${callCameraEnabled?'Выключить камеру':'Включить камеру'}">${callCameraEnabled?'📷':'🚫'}</button>`:''}<button id="end-call" class="hangup" title="Завершить звонок">☎</button>`
    : `<button id="audio-call" title="Аудиозвонок">📞</button><button id="video-call" title="Видеозвонок">🎥</button>`;
  const dmList=friends.length
    ? friends.map(friend=>`<button class="channel dm ${activeDmId===friend.id?'active':''}" data-dm-id="${friend.id}" data-dm="${friend.username}"><div class="mini-avatar" style="background:${friend.avatar_color||'#8b7cff'}">${(friend.username||'?')[0].toUpperCase()}</div> ${friend.username} <em></em></button>`).join('')
    : `<div class="dm-empty">Пока нет личных чатов</div>`;
  const membersList=serverMembers.length
    ? `<div class="members-title">УЧАСТНИКИ — ${serverMembers.length}</div>${serverMembers.map(member=>`<div class="member online"><div class="avatar" style="background:${member.avatar_color}">${member.username[0]?.toUpperCase()||'?'}</div><span>${member.username}<small>${member.role==='owner'?'Создатель':member.status}</small></span><i></i></div>`).join('')}`
    : `<div class="members-title">УЧАСТНИКИ</div><div class="dm-empty">Список загружается…</div>`;
  document.querySelector('#app').innerHTML = `
    <main class="shell">
      <aside class="servers"><button class="server home-tab ${friendsOpen?'selected':''}" id="friends-tab" title="Друзья">👥</button>${servers.map((s,i) => `<button class="server ${!friendsOpen&&i===activeServerIndex?'selected':''} ${s.add ? 'add' : ''}" data-server-index="${i}" title="${s.name}">${s.icon}</button>`).join('')}</aside>
      <aside class="channels">
        <div class="brand"><span class="brand-mark">◈</span><span>${friendsOpen?'Друзья':servers[activeServerIndex]?.name || 'Vessel'}</span><button class="more">•••</button></div>
        <div class="user-card"><div class="avatar user-avatar">${user.name[0].toUpperCase()}</div><div><b>${user.name}</b><small>в сети</small></div><button class="icon-btn" id="profile-settings" title="Настройки">⚙</button></div>
        <section class="channel-section"><div class="section-title">ЛИЧНЫЕ СООБЩЕНИЯ <button id="dm-add">＋</button></div>
          ${dmList}
        </section>
        <section class="channel-section"><div class="section-title">ТЕКСТОВЫЕ КАНАЛЫ <button id="channel-add">＋</button></div>
          ${serverChannels().filter(c=>c.kind==='text').map((c,i)=>`<button class="channel ${!currentDm&&activeChannelKind==='text'&&c.name===activeChannelName?'active':''}" data-channel-id="${c.id||''}" data-channel-name="${c.name}" data-kind="text"><span>#</span> ${c.name}</button>`).join('')}
        </section>
        <section class="channel-section"><div class="section-title">ГОЛОСОВЫЕ КАНАЛЫ <button id="voice-add">＋</button></div>${serverChannels().filter(c=>c.kind==='voice').map(c=>`<button class="channel ${activeChannelKind==='voice'&&c.name===activeChannelName?'active':''}" data-channel-id="${c.id||''}" data-channel-name="${c.name}" data-kind="voice"><span>⌁</span> ${c.name}</button>`).join('')}</section>
        <div class="side-footer">Vessel v0.1 <span>●</span></div>
      </aside>
      <section class="chat">
        <header class="chat-head"><div><h1><span>${currentDm?'@':activeChannelKind==='voice'?'⌁':'#'}</span> ${currentDm || activeChannelName}</h1><p>${currentDm?'Личная переписка':activeChannelKind==='voice'?'Голосовая комната':servers[activeServerIndex]?.name || 'Vessel'}</p></div><div class="head-actions">${callActions}<button id="join-voice" class="join-voice ${activeChannelKind==='voice'?'':'hidden'}">${voiceStream?'Выйти':'Войти'}</button><button id="mute-voice" class="join-voice ${voiceStream?'':'hidden'}">🎙</button><button id="camera-voice" class="join-voice ${voiceStream?'':'hidden'}">📷</button><button id="search-button">⌕</button><button id="friends-button" title="Друзья">♧</button><button id="notifications" title="Уведомления">🔔${notifications.filter(n=>!n.read_at).length?` <sup>${notifications.filter(n=>!n.read_at).length}</sup>`:''}</button><button id="head-settings">⚙</button></div></header>
        <video id="remote-video" class="remote-video ${remoteCallStream?'':'hidden'}" autoplay playsinline></video><video id="local-video" class="local-video ${voiceStream||callStream?'':'hidden'}" autoplay muted playsinline></video><div class="messages">${friendsOpen?`<div class="friends-view"><div class="friends-hero"><h2>Друзья</h2><button id="add-friend" class="primary">Найти пользователя</button></div>${friendRequests.map(request=>`<div class="friend-row request-row"><div class="avatar" style="background:#ffb45e">${(request.profiles?.username||'?')[0].toUpperCase()}</div><b>${request.profiles?.username||'Пользователь'}</b><span>Заявка</span><button data-accept-request="${request.id}" data-sender="${request.sender_id}">Принять</button></div>`).join('')}${friends.length ? friends.map(friend=>`<div class="friend-row"><div class="avatar" style="background:${friend.avatar_color||'#8b7cff'}">${friend.username[0].toUpperCase()}</div><b>${friend.username}</b><span>${friend.status||'в сети'}</span><button data-dm-id="${friend.id}" data-dm="${friend.username}">💬</button><button data-call-id="${friend.id}" data-call="${friend.username}">📞</button></div>`).join('') : `<p class="empty-state">Пока нет добавленных друзей. Нажми «Найти пользователя».</p>`}</div>`:`<div class="welcome"><div class="welcome-icon">${currentDm?'@':activeChannelKind==='voice'?'⌁':'#'}</div><h2>${currentDm?`Переписка с ${currentDm}`:`Добро пожаловать в ${activeChannelKind==='voice'?'':'#'}${activeChannelName}!`}</h2><p>${activeChannelKind==='voice'?'Подключись к комнате, чтобы общаться голосом.':'Здесь начинается ваше общение.'}</p></div>${(activeDmId?dmMessages:messages).map(m => `<article class="message"><div class="avatar" style="background:${m.color}">${m.name[0]}</div><div><div class="message-meta"><b>${m.name}</b><time>${m.time}</time></div><p>${m.text}</p></div></article>`).join('')}`}</div>
        <form class="composer ${friendsOpen?'hidden':''}"><button type="button" class="attach">＋</button><input placeholder="${currentDm?`Написать пользователю ${currentDm}`:`Написать в #${activeChannelName}`}" /><button type="button">☺</button><button type="submit" class="send">➤</button></form>
      </section>
      <aside class="members">${voiceStream?'<div class="voice-status">🎙 Ты в голосовой комнате</div>':''}${membersList}</aside>
    </main><div class="modal hidden" id="settings-modal"><div class="modal-card"><button class="modal-close" id="close-settings">×</button><h2>Настройки профиля</h2><p>Измени данные, которые видят другие участники Vessel.</p><form id="settings-form"><label>Имя пользователя<input name="name" value="${user.name}" required minlength="2" /></label><label>Статус<select name="status"><option>В сети</option><option>Не беспокоить</option><option>Отошёл</option></select></label><button class="primary" type="submit">Сохранить изменения</button></form><button class="danger" id="logout" type="button">Выйти из аккаунта</button></div></div>${incomingCall?`<div class="modal call-modal" id="incoming-call-modal"><div class="modal-card"><div class="call-avatar">${incomingCall.name[0]?.toUpperCase()||'?'}</div><h2>${incomingCall.video?'Видеозвонок':'Аудиозвонок'}</h2><p>${incomingCall.name} звонит тебе в Vessel.</p><div class="call-actions"><button class="danger" id="reject-call" type="button">Отклонить</button><button class="primary" id="accept-call" type="button">Принять</button></div></div></div>`:''}`;
  document.querySelector('.composer').addEventListener('submit', async e => { e.preventDefault(); const input=e.currentTarget.querySelector('input'); const text=input.value.trim(); if(!text)return; if(!supabase||!user.id){alert('Нужна активная сессия Vessel.');return;} if(activeDmId){ const {error}=await supabase.from('direct_messages').insert({sender_id:user.id,receiver_id:activeDmId,body:text}); if(error){alert(`Не удалось отправить личное сообщение: ${error.message}`);return;} dmMessages.push({name:user.name,time:'только что',color:user.avatarColor||'#39d9a6',text}); } else { if(!activeChannelId){alert('Сначала выбери текстовый канал.');return;} const {error}=await supabase.from('messages').insert({channel_id:activeChannelId,author_id:user.id,body:text}); if(error){alert(`Не удалось отправить сообщение: ${error.message}`);return;} messages.push({name:user.name,time:'только что',color:user.avatarColor||'#39d9a6',text}); } input.value=''; render(); const list=document.querySelector('.messages'); if(list)list.scrollTop=list.scrollHeight; });
  document.querySelector('.attach').addEventListener('click', () => {
    const picker = document.createElement('input'); picker.type = 'file'; picker.accept = 'image/*,.pdf,.doc,.docx,.zip';
    picker.onchange = async () => { const file = picker.files[0]; if (!file) return; const attachment=await uploadVesselFile(file,user); if(!attachment)return; const body=`📎 ${file.name}`; if(activeChannelId&&user.id){const {error}=await supabase.from('messages').insert({channel_id:activeChannelId,author_id:user.id,body,attachments:[attachment]});if(error){alert('Файл загрузился, но сообщение не отправилось.');return;}} messages.push({name:user.name,time:'только что',color:'#39d9a6',text:body}); localStorage.setItem('vesselMessages', JSON.stringify(messages)); render(); };
    picker.click();
  });
  document.querySelector('#search-button').addEventListener('click', () => { const query=prompt('Поиск по сообщениям:'); if(query){ const found=messages.filter(m=>m.text.toLowerCase().includes(query.toLowerCase())); alert(found.length ? `Найдено сообщений: ${found.length}\n\n${found.map(m=>m.name+': '+m.text).join('\n')}` : 'Ничего не найдено'); }});
  document.querySelector('#notifications').addEventListener('click', async () => { const unread=notifications.filter(n=>!n.read_at); if(!unread.length){alert('Новых уведомлений нет.');return;} alert(unread.map(n=>`${n.title}\n${n.body}`).join('\n\n')); if(supabase&&user.id) await supabase.from('notifications').update({read_at:new Date().toISOString()}).eq('user_id',user.id).is('read_at',null); notifications=notifications.map(n=>({...n,read_at:n.read_at||new Date().toISOString()})); render(); });
  const modal = document.querySelector('#settings-modal');
  document.querySelector('#profile-settings').addEventListener('click', () => modal.classList.remove('hidden'));
  document.querySelector('.more').addEventListener('click', async () => { const server=servers[activeServerIndex]; if(!server?.dbId||server.role!=='owner'){alert(`Твоя роль: ${server?.role||'участник'}. Создавать приглашения может только владелец.`);return;} const code=`VSL-${crypto.randomUUID().slice(0,8).toUpperCase()}`; const {error}=await supabase.from('server_invites').insert({server_id:server.dbId,created_by:user.id,code}); alert(error?'Не удалось создать приглашение.':`Код приглашения для сервера «${server.name}»:\n\n${code}\n\nПередай его другу.`); });
  const addChannel = async kind => { const name=prompt(kind==='voice'?'Название голосовой комнаты:':'Название нового канала:'); if(!name?.trim()) return; const server=servers[activeServerIndex]; const channels=serverChannels(); const created={name:name.trim(),kind}; if(supabase&&user.id&&server.dbId){ const {data,error}=await supabase.from('channels').insert({server_id:server.dbId,name:created.name,kind,position:channels.length}).select('id,name,kind,position').single(); if(error){alert('Не удалось создать канал. Проверь права доступа.');return;} created.id=data.id; activeChannelId=data.id; } savedChannelMap[server.id]=[...channels,created]; saveChannelMap(); activeChannelName=created.name; activeChannelKind=kind; currentDm=null; render(); };
  document.querySelector('#channel-add').addEventListener('click', () => addChannel('text'));
  document.querySelector('#voice-add').addEventListener('click', () => addChannel('voice'));
  document.querySelector('#dm-add').addEventListener('click', () => findAndRequestFriend(user));
  document.querySelector('#close-settings').addEventListener('click', () => modal.classList.add('hidden'));
  document.querySelector('#settings-form').addEventListener('submit', async e => { e.preventDefault(); const data=new FormData(e.currentTarget); const name=data.get('name').trim(); const status=data.get('status'); if(supabase&&user.id){const {error}=await supabase.from('profiles').update({username:name,status}).eq('id',user.id);if(error){alert('Не удалось сохранить профиль.');return;}} localStorage.setItem('vesselUser', JSON.stringify({...user,name,status})); location.reload(); });
  document.querySelector('#logout').addEventListener('click', async () => { if(supabase) await supabase.auth.signOut().catch(()=>{}); localStorage.removeItem('vesselUser'); localStorage.removeItem('vesselToken'); location.reload(); });
  document.querySelector('#accept-call')?.addEventListener('click', () => acceptIncomingCall(user));
  document.querySelector('#reject-call')?.addEventListener('click', () => rejectIncomingCall(user));
  document.querySelectorAll('.channel:not(.dm)').forEach(channel => channel.addEventListener('click', () => {
    document.querySelectorAll('.channel').forEach(item => item.classList.remove('active'));
    channel.classList.add('active');
    const name = channel.dataset.channelName || channel.textContent.replace('#', '').replace('⌁', '').trim();
    const isDm = channel.classList.contains('dm');
    currentDm=isDm?name:null; activeDmId=isDm?null:activeDmId; activeChannelId=channel.dataset.channelId||activeChannelId; activeChannelName=name; activeChannelKind=channel.dataset.kind || (channel.textContent.includes('⌁')?'voice':'text'); friendsOpen=false;
    document.querySelector('.chat-head h1').innerHTML = `<span>${isDm ? '@' : channel.textContent.includes('⌁') ? '⌁' : '#'}</span> ${name}`;
    document.querySelector('.chat-head p').textContent = isDm ? 'Личная переписка' : channel.textContent.includes('⌁') ? 'Голосовая комната' : 'Главный канал Vessel';
    document.querySelector('.composer input').placeholder = isDm ? `Написать пользователю ${name}` : `Написать в ${channel.textContent.includes('⌁') ? '' : '#'}${name}`;
    if (!isDm && channel.dataset.channelId) loadChannelMessages(channel.dataset.channelId);
    const voiceButton=document.querySelector('#join-voice'), muteButton=document.querySelector('#mute-voice'), cameraButton=document.querySelector('#camera-voice'); if(channel.textContent.includes('⌁')&&!isDm) { voiceButton.classList.remove('hidden'); voiceButton.textContent=voiceStream?'Выйти':'Подключиться'; voiceButton.onclick=async()=>{ if(voiceStream){voiceStream.getTracks().forEach(t=>t.stop());voiceStream=null;if(voiceRoom)await voiceRoom.unsubscribe();voiceRoom=null;render();return;} try { voiceStream=await navigator.mediaDevices.getUserMedia({audio:true,video:true}); if(supabase&&activeChannelId&&user.id){voiceRoom=supabase.channel('voice-'+activeChannelId);voiceRoom.on('presence',{event:'sync'},()=>{}).subscribe(async status=>{if(status==='SUBSCRIBED')await voiceRoom.track({user_id:user.id,name:user.name});});} render(); } catch { alert('Разреши Vessel доступ к микрофону и камере.'); } }; if(voiceStream){muteButton.classList.remove('hidden');cameraButton.classList.remove('hidden');muteButton.onclick=()=>{const track=voiceStream.getAudioTracks()[0];track.enabled=!track.enabled;muteButton.textContent=track.enabled?'🎙':'🔇';};cameraButton.onclick=()=>{const track=voiceStream.getVideoTracks()[0];track.enabled=!track.enabled;cameraButton.textContent=track.enabled?'📷':'🚫';};} } else {voiceButton.classList.add('hidden');muteButton.classList.add('hidden');cameraButton.classList.add('hidden');}
  }));
  document.querySelector('#friends-tab').addEventListener('click',()=>{friendsOpen=true;currentDm=null;render();});
  document.querySelector('#friends-button').addEventListener('click',()=>{friendsOpen=true;currentDm=null;render();});
  document.querySelector('#head-settings').addEventListener('click',()=>modal.classList.remove('hidden'));
  document.querySelectorAll('[data-dm]').forEach(button=>button.addEventListener('click',()=>{currentDm=button.dataset.dm;activeDmId=button.dataset.dmId||null;friendsOpen=false;window.__vesselDmLoaded=false;render();}));
  document.querySelectorAll('[data-accept-request]').forEach(button=>button.addEventListener('click',async()=>{if(!supabase||!user.id)return;const {error}=await supabase.from('friend_requests').update({status:'accepted',updated_at:new Date().toISOString()}).eq('id',button.dataset.acceptRequest).eq('receiver_id',user.id);if(error){alert('Не удалось принять заявку.');return;}window.__vesselSocialLoaded=false;await syncSocial(user);render();}));
  document.querySelector('#add-friend')?.addEventListener('click',()=>findAndRequestFriend(user));
  document.querySelector('#audio-call')?.addEventListener('click',()=>startCall(false,user));
  document.querySelector('#video-call')?.addEventListener('click',()=>startCall(true,user));
  document.querySelector('#end-call')?.addEventListener('click',()=>endCall(true));
  document.querySelector('#toggle-call-mic')?.addEventListener('click',toggleCallMicrophone);
  document.querySelector('#toggle-call-camera')?.addEventListener('click',toggleCallCamera);
  document.querySelectorAll('[data-call-id]').forEach(button=>button.addEventListener('click',()=>{currentDm=button.dataset.call;activeDmId=button.dataset.callId;friendsOpen=false;window.__vesselDmLoaded=false;render();startCall(false,user);}));
  document.querySelectorAll('.server[data-server-index]').forEach(server => server.addEventListener('click', async () => {
    if (server.classList.contains('add')) {
      if(supabase&&user.id&&confirm('У тебя есть код приглашения? Нажми «ОК», чтобы вступить в сервер.')){const code=prompt('Введи код приглашения:');if(code?.trim()){await joinByInvite(code,user);return;}}
      const name = prompt('Название нового сервера:');
      if (name && name.trim()) { let created={id:`local-${Date.now()}`,icon:name.trim()[0].toUpperCase(),name:name.trim()}; if(supabase&&user.id){ const {data,error}=await supabase.from('servers').insert({name:name.trim(),icon:created.icon,owner_id:user.id}).select('id,name,icon').single(); if(error){alert('Не удалось создать сервер. Проверь права доступа.');return;} created={...created,id:data.id,dbId:data.id}; } servers.splice(servers.length - 1, 0, created); activeServerIndex=servers.length-2; savedChannelMap[created.id]=[{name:'общий',kind:'text'}]; saveChannelMap(); localStorage.setItem('vesselServers', JSON.stringify(servers)); localStorage.setItem('vesselActiveServer',activeServerIndex); activeChannelName='общий';activeChannelKind='text';currentDm=null;friendsOpen=false;render(); }
      return;
    }
    activeServerIndex=Number(server.dataset.serverIndex);localStorage.setItem('vesselActiveServer',activeServerIndex);activeChannelName='общий';activeChannelKind='text';activeChannelId=null;currentDm=null;activeDmId=null;friendsOpen=false;serverMembers=[];window.__vesselMembersServerId=null;render();syncSupabaseChannels(servers[activeServerIndex]);syncServerMembers(user,servers[activeServerIndex]);
  }));
}
bootstrapAuth().then(render).catch(error=>{console.error('Vessel bootstrap failed',error);savedUser=null;render();});
setInterval(()=>{const video=document.querySelector('#local-video');const stream=callStream||voiceStream;if(video&&stream&&video.srcObject!==stream){video.srcObject=stream;video.play().catch(()=>{});}const remote=document.querySelector('#remote-video');if(remote&&remoteCallStream&&remote.srcObject!==remoteCallStream){remote.srcObject=remoteCallStream;remote.play().catch(()=>{});}},500);
