import './style.css';

const SUPABASE_URL = 'https://zqbveciunttbvvxhqvqs.supabase.co';
const SUPABASE_KEY = 'sb_publishable_vjT6aZKGuklvcCmmqcb-Zw_E5zc-434';
const supabase = window.supabase?.createClient(SUPABASE_URL, SUPABASE_KEY);
let activeChannelId = null;
let dbChannels = [];
let voiceStream = null;
let voiceRoom = null;
let voiceChannelId = null;
let voiceServerId = null;
let voiceParticipants = [];
const voicePeers = new Map();
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
let callInviteTimer = null;
let activeServerIndex = 0;
let activeServerId = localStorage.getItem('vesselActiveServerId') || null;
let activeChannelName = 'нет каналов';
let activeChannelKind = 'text';
let currentDm = null;
let activeDmId = null;
let friendsOpen = false;
let friends = [];
let dmThreads = [];
let friendRequests = [];
let outgoingFriendRequests = [];
let dmMessages = [];
let notifications = [];
let serverMembers = [];
function escapeHtml(value='') {
  return String(value).replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
}
function statusLabel(value='online') {
  const key=String(value||'online').toLowerCase();
  if(['dnd','не беспокоить'].includes(key))return 'Не беспокоить';
  if(['away','idle','отошёл'].includes(key))return 'Отошёл';
  return 'В сети';
}
function vesselDialog({title,message='',input=false,value='',placeholder='',choices=[]}) {
  return new Promise(resolve=>{
    const overlay=document.createElement('div');
    overlay.className='modal vessel-dialog';
    const choiceMarkup=choices.map(choice=>`<button type="button" class="dialog-choice ${choice.danger?'dialog-danger':''}" data-dialog-value="${escapeHtml(choice.value)}">${escapeHtml(choice.label)}</button>`).join('');
    overlay.innerHTML=`<div class="modal-card dialog-card"><button class="modal-close" data-dialog-cancel>×</button><h2>${escapeHtml(title)}</h2>${message?`<p>${escapeHtml(message)}</p>`:''}${input?`<input class="dialog-input" value="${escapeHtml(value)}" placeholder="${escapeHtml(placeholder)}" />`:''}<div class="dialog-actions">${choiceMarkup}${input?'<button type="button" class="primary" data-dialog-submit>Готово</button>':''}</div></div>`;
    document.body.appendChild(overlay);
    const finish=result=>{overlay.remove();resolve(result);};
    overlay.querySelector('[data-dialog-cancel]').addEventListener('click',()=>finish(null));
    overlay.addEventListener('click',event=>{if(event.target===overlay)finish(null);});
    overlay.querySelectorAll('[data-dialog-value]').forEach(button=>button.addEventListener('click',()=>finish(button.dataset.dialogValue)));
    if(input){
      const field=overlay.querySelector('.dialog-input');
      const submit=()=>finish(field.value);
      overlay.querySelector('[data-dialog-submit]').addEventListener('click',submit);
      field.addEventListener('keydown',event=>{if(event.key==='Enter')submit();if(event.key==='Escape')finish(null);});
      setTimeout(()=>{field.focus();field.select();},0);
    }
  });
}
function vesselPrompt(title,value='',placeholder='') { return vesselDialog({title,input:true,value,placeholder}); }
function vesselChoice(title,choices,message='') { return vesselDialog({title,message,choices}); }
async function vesselConfirm(title,message='') { return (await vesselChoice(title,[{label:'Отмена',value:'no'},{label:'Подтвердить',value:'yes',danger:true}],message))==='yes'; }
function vesselNotice(message,type='info') {
  const toast=document.createElement('div');
  toast.className=`vessel-toast ${type}`;
  toast.textContent=message;
  document.body.appendChild(toast);
  requestAnimationFrame(()=>toast.classList.add('show'));
  setTimeout(()=>{toast.classList.remove('show');setTimeout(()=>toast.remove(),180);},3200);
}
function vesselListDialog(title,items=[],emptyText='Ничего нет') {
  const overlay=document.createElement('div');
  overlay.className='modal vessel-dialog';
  const content=items.length?items.map(item=>`<div class="dialog-list-item"><div><b>${escapeHtml(item.title||'')}</b>${item.meta?`<time>${escapeHtml(item.meta)}</time>`:''}</div><p>${escapeHtml(item.body||'')}</p></div>`).join(''):`<div class="dialog-empty">${escapeHtml(emptyText)}</div>`;
  overlay.innerHTML=`<div class="modal-card dialog-card dialog-list-card"><button class="modal-close" data-dialog-close>×</button><h2>${escapeHtml(title)}</h2><div class="dialog-list">${content}</div></div>`;
  document.body.appendChild(overlay);
  const close=()=>overlay.remove();
  overlay.querySelector('[data-dialog-close]').addEventListener('click',close);
  overlay.addEventListener('click',event=>{if(event.target===overlay)close();});
}
function vesselCodeDialog(title,code) {
  const overlay=document.createElement('div');
  overlay.className='modal vessel-dialog';
  overlay.innerHTML=`<div class="modal-card dialog-card"><button class="modal-close" data-code-close>×</button><h2>${escapeHtml(title)}</h2><p>Передай этот код человеку, которого хочешь пригласить.</p><div class="invite-code">${escapeHtml(code)}</div><button class="primary" type="button" data-code-copy>Скопировать код</button></div>`;
  document.body.appendChild(overlay);
  const close=()=>overlay.remove();
  overlay.querySelector('[data-code-close]').addEventListener('click',close);
  overlay.addEventListener('click',event=>{if(event.target===overlay)close();});
  overlay.querySelector('[data-code-copy]').addEventListener('click',async()=>{
    try{await navigator.clipboard.writeText(code);vesselNotice('Код приглашения скопирован.','success');}
    catch{vesselNotice('Не удалось скопировать код. Выдели его вручную.','error');}
  });
}
function attachmentMarkup(attachments=[]) {
  return (attachments||[]).map(file=>`<button class="attachment-link" data-attachment-path="${escapeHtml(file.path||'')}">📎 ${escapeHtml(file.name||'Файл')}</button>`).join('');
}
async function openAttachment(path) {
  if(!supabase||!path)return;
  const {data,error}=await supabase.storage.from('vessel-files').createSignedUrl(path,60);
  if(error||!data?.signedUrl){vesselNotice('Не удалось открыть файл.','error');return;}
  window.open(data.signedUrl,'_blank','noopener,noreferrer');
}
async function syncSupabaseMessages() {
  window.__vesselDbLoaded = true;
}
async function loadChannelMessages(channelId) {
  if (!supabase || !channelId) return;
  const {data,error} = await supabase.from('messages').select('body,attachments,created_at,profiles(username,avatar_color)').eq('channel_id',channelId).order('created_at',{ascending:false}).limit(100);
  if(error){vesselNotice('Не удалось загрузить сообщения канала.','error');return;}
  messages = (data||[]).reverse().map(m=>({name:m.profiles?.username||'Участник',time:new Date(m.created_at).toLocaleString('ru-RU'),color:m.profiles?.avatar_color||'#8b7cff',text:m.body,attachments:m.attachments||[]}));
  render();
}
async function syncSupabaseServers(user) {
  if (!supabase || window.__vesselServersLoaded || !user?.id) return;
  const membershipsResult=await supabase.from('server_members').select('server_id,role').eq('user_id',user.id);
  if(membershipsResult.error){vesselNotice('Не удалось загрузить список серверов.','error');return;}
  const memberships=membershipsResult.data||[];
  const memberIds=memberships.map(row=>row.server_id).filter(Boolean);
  const [ownedResult,memberResult]=await Promise.all([
    supabase.from('servers').select('id,name,icon,owner_id').eq('owner_id',user.id).order('created_at'),
    memberIds.length ? supabase.from('servers').select('id,name,icon,owner_id').in('id',memberIds).order('created_at') : Promise.resolve({data:[],error:null})
  ]);
  if(ownedResult.error||memberResult.error){vesselNotice('Не удалось загрузить данные серверов.','error');return;}
  const owned=ownedResult.data||[];
  const all=[...owned,...(memberResult.data||[]).filter(server=>!owned.some(item=>item.id===server.id))];
  servers=[...all.map(server=>({id:server.id,dbId:server.id,icon:server.icon||server.name?.[0]?.toUpperCase()||'V',name:server.name,role:server.owner_id===user.id?'owner':memberships.find(member=>member.server_id===server.id)?.role||'member',channels:[]})),{id:'add-server',icon:'+',name:'Добавить сервер',add:true}];
  window.__vesselServersLoaded=true;
  const selected=setActiveServer(activeServerId && all.some(server=>server.id===activeServerId) ? activeServerId : all[0]?.id||null);
  if(!selected){activeChannelId=null;activeChannelName='нет каналов';activeChannelKind='text';dbChannels=[];messages=[];serverMembers=[];window.__vesselMembersServerId=null;}
  render();
}
async function syncSupabaseChannels(server) {
  if (!supabase || !server?.dbId || server.__channelsLoaded) return;
  const {data,error}=await supabase.from('channels').select('id,name,kind,position').eq('server_id',server.dbId).order('position');
  if(error){console.warn('Channel sync failed',error);vesselNotice('Не удалось загрузить каналы сервера.','error');return;}
  const rows=data||[];
  server.channels=rows;
  server.__channelsLoaded=true;
  if(server.id===getActiveServer()?.id){
    dbChannels=rows;
    let selected=rows.find(channel=>channel.id===activeChannelId)||null;
    if(!selected)selected=rows.find(channel=>channel.kind==='text')||rows[0]||null;
    activeChannelId=selected?.id||null;
    activeChannelName=selected?.name||'нет каналов';
    activeChannelKind=selected?.kind||'text';
    currentDm=null;
    activeDmId=null;
    messages=[];
    if(activeChannelId&&activeChannelKind==='text')await loadChannelMessages(activeChannelId);else render();
  }
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
    if(result.error){console.warn('Member profiles failed',result.error);vesselNotice('Не удалось загрузить профили участников.','error');return;}
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
  const query=await vesselPrompt('Добавить друга','','Точное имя пользователя');
  if(!query?.trim()) return;
  if(!supabase||!user?.id){vesselNotice('Войди через настоящий аккаунт, чтобы добавлять друзей.','error');return;}
  const {data:searchResult,error:searchError}=await supabase.functions.invoke('search-user',{body:{username:query.trim()}});
  if(searchError){vesselNotice('Не удалось выполнить поиск пользователя.','error');return;}
  const target=searchResult?.user;
  if(!target){vesselNotice('Пользователь не найден.','error');return;}
  if(target.self||target.id===user.id){vesselNotice('Нельзя добавить самого себя.','error');return;}
  if(friends.some(friend=>friend.id===target.id)){vesselNotice(`${target.username} уже у тебя в друзьях.`);return;}
  const {data:existing,error:existingError}=await supabase.from('friend_requests').select('id,status,sender_id,receiver_id').or(`and(sender_id.eq.${user.id},receiver_id.eq.${target.id}),and(sender_id.eq.${target.id},receiver_id.eq.${user.id})`).limit(1);
  if(existingError){vesselNotice('Не удалось проверить заявки в друзья.','error');return;}
  const request=existing?.[0];
  if(request?.status==='pending'){
    vesselNotice(request.receiver_id===user.id ? `${target.username} уже отправил тебе заявку. Открой раздел «Друзья».` : 'Заявка уже отправлена.');
    return;
  }
  const {error:sendError}=await supabase.from('friend_requests').upsert({sender_id:user.id,receiver_id:target.id,status:'pending',updated_at:new Date().toISOString()},{onConflict:'sender_id,receiver_id'});
  if(sendError){
    if(sendError.code==='23505'){
      window.__vesselSocialLoaded=false;
      await syncSocial(user);
      vesselNotice('Заявка уже существует или пользователь одновременно отправил заявку тебе. Открой раздел «Друзья».');
      return;
    }
    vesselNotice('Не удалось отправить заявку.','error');return;
  }
  window.__vesselSocialLoaded=false;
  await syncSocial(user);
  vesselNotice(`Заявка пользователю ${target.username} отправлена.`,'success');
}

async function syncSocial(user) {
  if (!supabase || !user?.id || window.__vesselSocialLoaded) return;
  const {data: links, error: linksError} = await supabase.from('friendships').select('friend_id').eq('user_id', user.id);
  if(linksError){vesselNotice('Не удалось загрузить список друзей.','error');return;}
  const ids = (links || []).map(row => row.friend_id).filter(Boolean);
  friends = [];
  if (ids.length) {
    const {data: profiles, error: profilesError} = await supabase.from('profiles').select('id,username,avatar_color,status').in('id', ids);
    if(profilesError){vesselNotice('Не удалось загрузить профили друзей.','error');return;}
    friends = profiles || [];
  }
  const [incomingResult,outgoingResult]=await Promise.all([
    supabase.from('friend_requests').select('id,sender_id,status,created_at,profiles!friend_requests_sender_id_fkey(username,avatar_color)').eq('receiver_id', user.id).eq('status','pending').order('created_at',{ascending:false}),
    supabase.from('friend_requests').select('id,receiver_id,status,created_at,profiles!friend_requests_receiver_id_fkey(username,avatar_color)').eq('sender_id', user.id).eq('status','pending').order('created_at',{ascending:false})
  ]);
  if(incomingResult.error||outgoingResult.error){vesselNotice('Не удалось загрузить заявки в друзья.','error');return;}
  friendRequests = incomingResult.data || [];
  outgoingFriendRequests = outgoingResult.data || [];
  window.__vesselSocialLoaded = true;
  if (document.querySelector('#app')) render();
}
async function syncDmThreads(user) {
  if (!supabase || !user?.id || window.__vesselDmThreadsLoaded) return;
  const {data,error}=await supabase.rpc('vessel_dm_threads');
  if(error){console.warn('DM thread sync failed',error);vesselNotice('Не удалось загрузить список личных чатов.','error');return;}
  dmThreads=(data||[]).map(row=>({id:row.peer_id,username:row.username||'Пользователь',avatar_color:row.avatar_color||'#8b7cff',status:row.status||'online',last_message_at:row.last_message_at}));
  window.__vesselDmThreadsLoaded=true;
  if(document.querySelector('#app'))render();
}
async function syncNotifications(user) {
  if (!supabase || !user?.id || window.__vesselNotificationsLoaded) return;
  const {data}=await supabase.from('notifications').select('id,type,title,body,data,read_at,created_at').eq('user_id',user.id).order('created_at',{ascending:false}).limit(30);
  notifications=data||[]; window.__vesselNotificationsLoaded=true;
  if (document.querySelector('#app')) render();
}
async function loadDirectMessages(user, friendId) {
  if (!supabase || !user?.id || !friendId) return;
  const {data,error} = await supabase.from('direct_messages').select('id,sender_id,receiver_id,body,attachments,created_at,profiles!direct_messages_sender_id_fkey(username,avatar_color)').or(`and(sender_id.eq.${user.id},receiver_id.eq.${friendId}),and(sender_id.eq.${friendId},receiver_id.eq.${user.id})`).order('created_at',{ascending:false}).limit(100);
  if(error){vesselNotice('Не удалось загрузить личные сообщения.','error');return;}
  dmMessages = (data || []).reverse().map(row => ({name:row.profiles?.username || 'Пользователь',time:new Date(row.created_at).toLocaleString('ru-RU'),color:row.profiles?.avatar_color || '#8b7cff',text:row.body,attachments:row.attachments||[]}));
  render();
}
async function uploadVesselFile(file, user) {
  if (!supabase || !user?.id) { vesselNotice('Для загрузки файлов нужен настоящий аккаунт.','error'); return null; }
  if(file.size>25*1024*1024){vesselNotice('Максимальный размер файла — 25 МБ.','error');return null;}
  let context=null;
  if(activeDmId)context=`dm/${activeDmId}`;
  else if(activeChannelId&&activeChannelKind==='text')context=`channel/${activeChannelId}`;
  if(!context){vesselNotice('Открой личный чат или текстовый канал перед загрузкой файла.','error');return null;}
  const safeName=file.name.replace(/[^a-zA-Z0-9._-]/g,'_')||'file';
  const objectPath=`${user.id}/${context}/${crypto.randomUUID()}-${safeName}`;
  const {error}=await supabase.storage.from('vessel-files').upload(objectPath,file,{contentType:file.type||'application/octet-stream',upsert:false});
  if(error){vesselNotice(`Файл не загрузился: ${error.message}`,'error');return null;}
  return {name:file.name,path:objectPath,type:file.type||'application/octet-stream',size:file.size};
}
async function cleanupFailedAttachment(attachment){
  if(!supabase||!attachment?.path)return;
  try{await supabase.storage.from('vessel-files').remove([attachment.path]);}catch(error){console.warn('Attachment cleanup failed',error);}
}

function removeVoicePeer(peerId) {
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
  pc.onconnectionstatechange=()=>{
    if(['failed','closed'].includes(pc.connectionState)){removeVoicePeer(peerId);return;}
    if(pc.connectionState==='disconnected')setTimeout(()=>{if(voicePeers.get(peerId)?.pc===pc&&pc.connectionState==='disconnected')removeVoicePeer(peerId);},3000);
  };
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
  const room=voiceRoom;
  voiceRoom=null;
  voiceStream?.getTracks().forEach(track=>track.stop());voiceStream=null;
  for(const peerId of [...voicePeers.keys()])removeVoicePeer(peerId);
  voiceParticipants=[];voiceChannelId=null;voiceServerId=null;
  if(room&&supabase){try{await supabase.removeChannel(room);}catch{}}
  render();
}

async function toggleVoiceRoom(user){
  if(voiceStream && voiceChannelId===activeChannelId){await leaveVoiceRoom();return;}
  if(!supabase||!user?.id||!activeChannelId||activeChannelKind!=='voice'){vesselNotice('Сначала открой голосовой канал.','error');return;}
  if(callConnection||callStream||incomingCall){vesselNotice('Заверши личный звонок или отклони входящий вызов перед входом в голосовой канал.','error');return;}
  if(voiceStream && voiceChannelId!==activeChannelId){await leaveVoiceRoom();}
  let room=null;
  try{
    const targetChannelId=activeChannelId;
    voiceStream=await navigator.mediaDevices.getUserMedia({audio:true,video:false});
    voiceChannelId=targetChannelId;
    voiceServerId=getActiveServer()?.dbId||null;
    room=supabase.channel(`voice-${targetChannelId}`,{config:{presence:{key:user.id}}});
    voiceRoom=room;
    room.on('broadcast',{event:'voice-signal'},({payload})=>handleVoiceSignal(user,payload).catch(error=>console.warn('Voice signal failed',error)));
    room.on('presence',{event:'sync'},()=>{if(room===voiceRoom)syncVoicePresence(user).catch(error=>console.warn('Voice presence failed',error));});
    await new Promise((resolve,reject)=>{
      let settled=false;
      const timer=setTimeout(()=>{if(!settled){settled=true;reject(new Error('VOICE_REALTIME_TIMEOUT'));}},10000);
      room.subscribe(async status=>{
        if(room!==voiceRoom)return;
        if(status==='SUBSCRIBED'){
          try{
            await room.track({user_id:user.id,name:user.name});
            await syncVoicePresence(user);
            if(!settled){settled=true;clearTimeout(timer);resolve();}
            else render();
          }catch(error){
            if(!settled){settled=true;clearTimeout(timer);reject(error);}
            else console.warn('Voice presence restore failed',error);
          }
          return;
        }
        if(['CHANNEL_ERROR','TIMED_OUT','CLOSED'].includes(status)){
          for(const peerId of [...voicePeers.keys()])removeVoicePeer(peerId);
          voiceParticipants=[];
          render();
          if(!settled){settled=true;clearTimeout(timer);reject(new Error(`VOICE_REALTIME_${status}`));}
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
}

function toggleVoiceMicrophone(){
  const track=voiceStream?.getAudioTracks()[0];if(!track)return;track.enabled=!track.enabled;render();
}

function callRoomName(a,b) { return `vessel-call-${[a,b].sort().join('-')}`; }
function callInboxName(userId) { return `vessel-call-inbox-${userId}`; }
function serialiseDescription(description) { return description ? {type: description.type, sdp: description.sdp} : null; }
function subscribeChannel(channel) {
  if (channel.__subscribed) return Promise.resolve(channel);
  if (channel.__subscribePromise) return channel.__subscribePromise;
  channel.__subscribePromise = new Promise((resolve, reject) => {
    let settled = false;
    const timer = setTimeout(() => {
      if (!settled) { settled = true; channel.__subscribed = false; reject(new Error('Realtime channel timeout')); }
    }, 10000);
    channel.subscribe(status => {
      if (status === 'SUBSCRIBED') {
        channel.__subscribed = true;
        if (!settled) {
          settled = true;
          clearTimeout(timer);
          resolve(channel);
        }
        return;
      }
      if (['CHANNEL_ERROR', 'TIMED_OUT', 'CLOSED'].includes(status)) {
        channel.__subscribed = false;
        if (!settled) {
          settled = true;
          clearTimeout(timer);
          reject(new Error(`Realtime channel ${status}`));
        }
      }
    });
  }).finally(() => { channel.__subscribePromise = null; });
  return channel.__subscribePromise;
}
async function sendCallInvite(user, peerId, payload) {
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
      if (callConnection || callStream || incomingCall) {
        await sendCallInvite(user, payload.from, {type:'busy'});
        return;
      }
      incomingCall = {from:payload.from, name:payload.name || 'Пользователь', video:!!payload.video, offer:payload.offer};
      render();
      return;
    }
    if (payload.type === 'bye') {
      if (incomingCall?.from === payload.from) {
        incomingCall = null;
        render();
        return;
      }
      if (payload.from === callPeer) await endCall(false);
      return;
    }
    if (payload.from !== callPeer) return;
    if (payload.type === 'accept') {
      if(callInviteTimer){clearTimeout(callInviteTimer);callInviteTimer=null;}
      callAccepted = true;
      await ensureCallChannel(user, callPeer);
      if (callOffer) await sendCallSignal(user, callPeer, {type:'offer', description:callOffer}, callVideo);
      await flushLocalIceCandidates(user, callPeer, callVideo);
      render();
      return;
    }
    if (payload.type === 'decline' || payload.type === 'busy') {
      vesselNotice(payload.type === 'busy' ? 'Пользователь уже разговаривает.' : 'Вызов отклонён.',payload.type==='busy'?'info':'error');
      await endCall(false);
      return;
    }
  });
  try {
    await subscribeChannel(callInboxChannel);
  } catch (error) {
    console.warn('Call inbox failed', error);
    const failedChannel=callInboxChannel;
    callInboxChannel=null;
    if(failedChannel&&supabase){try{await supabase.removeChannel(failedChannel);}catch{}}
    setTimeout(()=>{if(savedUser?.id===user.id)ensureCallInbox(savedUser).catch(retryError=>console.warn('Call inbox retry failed',retryError));},3000);
    return null;
  }
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
    await handleCallSignal(user,payload.from,payload.signal,payload.video).catch(error=>{console.warn('Call signal failed',error);endCall(false);});
  });
  await subscribeChannel(callChannel);
  return callChannel;
}
async function sendCallSignal(user,peerId,signal,video) {
  const room=await ensureCallChannel(user,peerId);
  if(!room)throw new Error('CALL_SIGNAL_CHANNEL_UNAVAILABLE');
  const result=await room.send({type:'broadcast',event:'signal',payload:{from:user.id,to:peerId,signal,video:!!video}});
  if(result!=='ok')throw new Error(`CALL_SIGNAL_${String(result||'FAILED').toUpperCase()}`);
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
    if (callAccepted) sendCallSignal(user,peerId,{type:'ice',candidate:e.candidate},video).catch(error=>console.warn('Call ICE send failed',error));
    else localIceCandidates.push(e.candidate);
  };
  callConnection.ontrack=e=>{remoteCallStream=e.streams[0];const el=document.querySelector('#remote-video');if(el){el.srcObject=remoteCallStream;el.play().catch(()=>{});} };
  const connection = callConnection;
  callConnection.onconnectionstatechange=()=>{
    if(connection!==callConnection) return;
    const state=connection.connectionState;
    if(['failed','closed'].includes(state)){endCall(false);return;}
    if(state==='disconnected'){
      setTimeout(()=>{
        if(connection===callConnection && connection.connectionState==='disconnected') endCall(false);
      },3000);
    }
  };
  if(callStream) callStream.getTracks().forEach(track=>callConnection.addTrack(track,callStream));
  return callConnection;
}
async function handleCallSignal(user,peerId,signal,video) {
  if(signal.type==='bye'){await endCall(false);return;}
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
}
async function acceptIncomingCall(user) {
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
}
async function rejectIncomingCall(user) {
  if (!incomingCall) return;
  const invite=incomingCall; incomingCall=null;
  await sendCallInvite(user,invite.from,{type:'decline'});
  render();
}
async function endCall(notify=true) {
  const user=savedUser;
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
  if(callInviteTimer){clearTimeout(callInviteTimer);callInviteTimer=null;}
  callMicEnabled=true;
  callCameraEnabled=true;
  render();
  if(notify&&peer&&user?.id&&room?.__subscribed){
    try {
      await room.send({type:'broadcast',event:'signal',payload:{from:user.id,to:peer,signal:{type:'bye'},video:false}});
    } catch(error) {
      console.warn('Call room hangup signal failed',error);
    }
  }
  if(notify&&peer&&user?.id){
    try { await sendCallInvite(user,peer,{type:'bye'}); } catch(error) { console.warn('Call inbox hangup signal failed',error); }
  }
  if(room&&supabase){ try { await supabase.removeChannel(room); } catch {} }
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

function getActiveServer() {
  const selected=activeServerId ? servers.find(item=>!item.add&&item.id===activeServerId) : null;
  const fallback=selected || servers.find(item=>!item.add) || null;
  activeServerIndex=fallback ? servers.indexOf(fallback) : 0;
  if(fallback?.id!==activeServerId){
    activeServerId=fallback?.id||null;
    if(activeServerId)localStorage.setItem('vesselActiveServerId',activeServerId);else localStorage.removeItem('vesselActiveServerId');
  }
  return fallback;
}
function setActiveServer(serverOrId) {
  const id=typeof serverOrId==='string' ? serverOrId : serverOrId?.id;
  const target=id ? servers.find(item=>!item.add&&item.id===id) : null;
  activeServerId=target?.id||null;
  activeServerIndex=target ? servers.indexOf(target) : 0;
  if(activeServerId)localStorage.setItem('vesselActiveServerId',activeServerId);else localStorage.removeItem('vesselActiveServerId');
  localStorage.removeItem('vesselActiveServer');
  return target;
}
function serverChannels() {
  return getActiveServer()?.channels || [];
}

let messages = [];
function connectSupabaseRealtime(user) {
  if (!supabase || !user?.id || window.__vesselRealtimeChannels) return;
  window.__vesselRealtimeChannels = [
    supabase.channel(`vessel-dm-${user.id}`).on('postgres_changes',{event:'INSERT',schema:'public',table:'direct_messages'},payload=>{
      const row=payload.new;
      window.__vesselDmThreadsLoaded=false;
      syncDmThreads(user).catch(error=>console.warn('DM thread realtime refresh failed',error));
      if(activeDmId && (row.sender_id===activeDmId || row.receiver_id===activeDmId)){ window.__vesselDmLoaded=false; loadDirectMessages(user,activeDmId); }
    }).subscribe(),
    supabase.channel(`vessel-friends-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'friend_requests',filter:`receiver_id=eq.${user.id}`},()=>{window.__vesselSocialLoaded=false;syncSocial(user);}).subscribe(),
    supabase.channel(`vessel-friend-requests-out-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'friend_requests',filter:`sender_id=eq.${user.id}`},()=>{window.__vesselSocialLoaded=false;syncSocial(user);}).subscribe(),
    supabase.channel(`vessel-friendships-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'friendships',filter:`user_id=eq.${user.id}`},()=>{window.__vesselSocialLoaded=false;syncSocial(user);}).subscribe(),
    supabase.channel(`vessel-memberships-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'server_members'},async payload=>{
      const row=payload.new?.server_id?payload.new:payload.old;
      if(!row)return;
      if(row.user_id===user.id){
        if(payload.eventType==='DELETE'&&voiceStream&&voiceServerId===row.server_id)await leaveVoiceRoom();
        window.__vesselServersLoaded=false;
        syncSupabaseServers(user).then(()=>{
          const active=getActiveServer();
          serverMembers=[];window.__vesselMembersServerId=null;
          if(active?.dbId){active.__channelsLoaded=false;syncSupabaseChannels(active);syncServerMembers(user,active);}else render();
        });
      }else{
        const active=getActiveServer();
        if(active?.dbId===row.server_id){window.__vesselMembersServerId=null;serverMembers=[];syncServerMembers(user,active);}
      }
    }).subscribe(),
    supabase.channel(`vessel-channels-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'channels'},async payload=>{
      const row=payload.new?.server_id?payload.new:payload.old;
      if(payload.eventType==='DELETE'&&voiceStream&&row?.id===voiceChannelId)await leaveVoiceRoom();
      const active=getActiveServer();
      if(row?.server_id&&active?.dbId===row.server_id){active.__channelsLoaded=false;syncSupabaseChannels(active);}
    }).subscribe(),
    supabase.channel(`vessel-channel-messages-${user.id}`).on('postgres_changes',{event:'INSERT',schema:'public',table:'messages'},payload=>{
      if(payload.new.channel_id===activeChannelId && payload.new.author_id!==user.id)loadChannelMessages(activeChannelId).catch(error=>console.warn('Message refresh failed',error));
    }).subscribe(),
    supabase.channel(`vessel-profiles-${user.id}`).on('postgres_changes',{event:'UPDATE',schema:'public',table:'profiles'},payload=>{
      const row=payload.new;
      if(!row?.id)return;
      let dirty=false;
      if(savedUser?.id===row.id){savedUser={...savedUser,name:row.username||savedUser.name,status:row.status||savedUser.status,avatarColor:row.avatar_color||savedUser.avatarColor};localStorage.setItem('vesselUser',JSON.stringify(savedUser));dirty=true;}
      const friend=friends.find(item=>item.id===row.id);if(friend){friend.username=row.username||friend.username;friend.status=row.status||friend.status;friend.avatar_color=row.avatar_color||friend.avatar_color;dirty=true;}
      const thread=dmThreads.find(item=>item.id===row.id);if(thread){thread.username=row.username||thread.username;thread.status=row.status||thread.status;thread.avatar_color=row.avatar_color||thread.avatar_color;dirty=true;}
      const member=serverMembers.find(item=>item.id===row.id);if(member){member.username=row.username||member.username;member.status=row.status||member.status;member.avatar_color=row.avatar_color||member.avatar_color;dirty=true;}
      if(activeDmId===row.id&&row.username){currentDm=row.username;dirty=true;}
      if(dirty)render();
    }).subscribe(),
    supabase.channel(`vessel-servers-${user.id}`).on('postgres_changes',{event:'UPDATE',schema:'public',table:'servers'},payload=>{
      const row=payload.new;
      const server=row?.id?servers.find(item=>item.id===row.id):null;
      if(!server)return;
      server.name=row.name||server.name;server.icon=row.icon||server.icon;render();
    }).subscribe(),
    supabase.channel(`vessel-notifications-${user.id}`).on('postgres_changes',{event:'INSERT',schema:'public',table:'notifications',filter:`user_id=eq.${user.id}`},payload=>{notifications=[payload.new,...notifications];render();}).subscribe()
  ];
}

let savedUser = null;
let authStateSyncTimer = null;

function resetAuthenticatedRuntime() {
  const channels=[...(window.__vesselRealtimeChannels||[]),voiceRoom,callChannel,callInboxChannel].filter(Boolean);
  window.__vesselRealtimeChannels=null;
  voiceRoom=null;
  callChannel=null;
  callInboxChannel=null;

  voiceStream?.getTracks().forEach(track=>track.stop());
  callStream?.getTracks().forEach(track=>track.stop());
  remoteCallStream?.getTracks?.().forEach(track=>track.stop?.());
  voiceStream=null;
  callStream=null;
  remoteCallStream=null;
  callConnection?.close();
  callConnection=null;
  for(const peerId of [...voicePeers.keys()])removeVoicePeer(peerId);
  voiceParticipants=[];
  voiceChannelId=null;
  voiceServerId=null;
  incomingCall=null;
  callPeer=null;
  callPeerName='';
  callOffer=null;
  callVideo=false;
  callAccepted=false;
  pendingIceCandidates=[];
  localIceCandidates=[];
  if(callInviteTimer){clearTimeout(callInviteTimer);callInviteTimer=null;}
  callMicEnabled=true;
  callCameraEnabled=true;

  savedUser=null;
  friends=[];
  dmThreads=[];
  friendRequests=[];
  outgoingFriendRequests=[];
  dmMessages=[];
  notifications=[];
  serverMembers=[];
  messages=[];
  dbChannels=[];
  servers=[{id:'add-server',icon:'+',name:'Добавить сервер',add:true}];
  activeServerId=null;
  activeServerIndex=0;
  activeChannelId=null;
  activeChannelName='нет каналов';
  activeChannelKind='text';
  currentDm=null;
  activeDmId=null;
  friendsOpen=false;

  window.__vesselDbLoaded=false;
  window.__vesselServersLoaded=false;
  window.__vesselSocialLoaded=false;
  window.__vesselDmThreadsLoaded=false;
  window.__vesselDmLoaded=false;
  window.__vesselMembersServerId=null;
  localStorage.removeItem('vesselUser');
  localStorage.removeItem('vesselToken');
  localStorage.removeItem('vesselActiveServerId');
  return [...new Set(channels)];
}

async function cleanupAuthenticatedChannels(channels=[]) {
  if(!supabase||!channels.length)return;
  await Promise.allSettled(channels.map(channel=>supabase.removeChannel(channel)));
}

function scheduleAuthStateRefresh(session) {
  const nextUserId=session?.user?.id||null;
  if(!nextUserId)return;
  if(authStateSyncTimer)clearTimeout(authStateSyncTimer);
  authStateSyncTimer=setTimeout(async()=>{
    authStateSyncTimer=null;
    if(savedUser?.id===nextUserId)return;
    try{
      await bootstrapAuth();
      render();
    }catch(error){
      console.error('Auth state refresh failed',error);
      const staleChannels=resetAuthenticatedRuntime();
      render();
      cleanupAuthenticatedChannels(staleChannels).catch(cleanupError=>console.warn('Auth cleanup failed',cleanupError));
    }
  },80);
}

function handleAuthStateChange(event,session) {
  if(event==='INITIAL_SESSION'||event==='TOKEN_REFRESHED')return;
  const nextUserId=session?.user?.id||null;
  if(event==='SIGNED_OUT'||!nextUserId){
    if(authStateSyncTimer){clearTimeout(authStateSyncTimer);authStateSyncTimer=null;}
    const staleChannels=resetAuthenticatedRuntime();
    render();
    setTimeout(()=>cleanupAuthenticatedChannels(staleChannels).catch(error=>console.warn('Auth channel cleanup failed',error)),0);
    return;
  }
  if(event==='SIGNED_IN'){
    if(savedUser?.id===nextUserId)return;
    const staleChannels=savedUser?.id&&savedUser.id!==nextUserId?resetAuthenticatedRuntime():[];
    if(staleChannels.length)setTimeout(()=>cleanupAuthenticatedChannels(staleChannels).catch(error=>console.warn('Auth account-switch cleanup failed',error)),0);
    scheduleAuthStateRefresh(session);
  }
}

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
  if (!supabase || !user?.id) { vesselNotice('Для вступления нужен настоящий аккаунт.','error'); return false; }
  const normalized=code?.trim().toUpperCase();
  if(!normalized)return false;
  const {data,error}=await supabase.functions.invoke('join-server',{body:{code:normalized}});
  if(error){
    let message='Не удалось вступить в сервер.';
    try{
      const payload=await error.context?.json?.();
      if(payload?.error)message=payload.error;
    }catch{}
    vesselNotice(message,'error');
    return false;
  }
  if(!data?.ok){vesselNotice(data?.error||'Не удалось вступить в сервер.','error');return false;}
  window.__vesselServersLoaded=false;
  serverMembers=[];window.__vesselMembersServerId=null;
  await syncSupabaseServers(user);
  setActiveServer(data.server_id);
  const server=getActiveServer();
  if(server?.dbId){server.__channelsLoaded=false;await syncSupabaseChannels(server);await syncServerMembers(user,server);}
  vesselNotice(data.already_member?'Ты уже состоишь в этом сервере.':'Ты вступил в сервер.','success');
  return true;
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
      if (!supabase) { vesselNotice('Сервис авторизации временно недоступен.','error'); return; }
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
          vesselNotice('Аккаунт создан. Если подтверждение почты включено, открой письмо от Vessel, а затем войди.','success');
          setAuthMode('login');
          return;
        }
        await bootstrapAuth();
        render();
      } catch (error) {
        console.error('Authentication failed', error);
        vesselNotice(error?.message || 'Не удалось выполнить авторизацию.','error');
      } finally {
        submit.disabled = false;
      }
    });
    authSwitch.addEventListener('click', () => setAuthMode((authForm.dataset.mode || 'signup') === 'login' ? 'signup' : 'login'));
    return;
  }
  const user = savedUser;
  connectSupabaseRealtime(user); ensureCallInbox(user).catch(()=>{}); syncSupabaseMessages(); syncSupabaseServers(user); const selectedServer=getActiveServer(); if(selectedServer){syncSupabaseChannels(selectedServer);syncServerMembers(user,selectedServer);} syncSocial(user); syncDmThreads(user); syncNotifications(user); if (activeDmId && callConnection) { ensureCallChannel(user,activeDmId).catch(()=>{}); } if (activeDmId && !window.__vesselDmLoaded) { window.__vesselDmLoaded=true; loadDirectMessages(user,activeDmId); }
  const callInProgress=Boolean(callConnection||callStream);
  const activeDmIsFriend=Boolean(activeDmId&&friends.some(friend=>friend.id===activeDmId));
  const activeServer=getActiveServer();
  const canManageChannel=Boolean(!friendsOpen&&!currentDm&&activeChannelId&&activeServer?.dbId&&activeServer.role==='owner');
  const callActions=callInProgress
    ? `<button id="toggle-call-mic" class="call-control" title="${callMicEnabled?'Выключить микрофон':'Включить микрофон'}">${callMicEnabled?'🎙':'🔇'}</button>${callVideo?`<button id="toggle-call-camera" class="call-control" title="${callCameraEnabled?'Выключить камеру':'Включить камеру'}">${callCameraEnabled?'📷':'🚫'}</button>`:''}<button id="end-call" class="hangup" title="Завершить звонок">☎</button>`
    : (!friendsOpen&&activeDmId&&activeDmIsFriend) ? `<button id="audio-call" title="Аудиозвонок">📞</button><button id="video-call" title="Видеозвонок">🎥</button>` : '';
  const dmList=dmThreads.length
    ? dmThreads.map(thread=>`<button class="channel dm ${activeDmId===thread.id?'active':''}" data-dm-id="${thread.id}" data-dm="${escapeHtml(thread.username)}"><div class="mini-avatar" style="background:${thread.avatar_color||'#8b7cff'}">${(thread.username||'?')[0].toUpperCase()}</div> ${escapeHtml(thread.username)} <em></em></button>`).join('')
    : `<div class="dm-empty">Пока нет личных чатов</div>`;
  const membersList=serverMembers.length
    ? `<div class="members-title">УЧАСТНИКИ — ${serverMembers.length}</div>${serverMembers.map(member=>`<div class="member online"><div class="avatar" style="background:${escapeHtml(member.avatar_color||'#8b7cff')}">${escapeHtml(member.username[0]?.toUpperCase()||'?')}</div><span>${escapeHtml(member.username)}<small>${member.role==='owner'?'Создатель':member.role==='moderator'?'Модератор':escapeHtml(statusLabel(member.status))}</small></span>${activeServer?.role==='owner'&&member.role!=='owner'?`<button class="member-manage" data-manage-member="${member.id}" title="Управление участником">•••</button>`:'<i></i>'}</div>`).join('')}`
    : `<div class="members-title">УЧАСТНИКИ</div><div class="dm-empty">${!activeServer?.dbId?'Выбери или создай сервер.':window.__vesselMembersServerId===activeServer.dbId?'На сервере пока нет участников.':'Список загружается…'}</div>`;
  document.querySelector('#app').innerHTML = `
    <main class="shell">
      <aside class="servers"><button class="server home-tab ${friendsOpen?'selected':''}" id="friends-tab" title="Друзья">👥</button>${servers.map((s,i) => `<button class="server ${!friendsOpen&&i===activeServerIndex?'selected':''} ${s.add ? 'add' : ''}" data-server-index="${i}" title="${escapeHtml(s.name)}">${escapeHtml(s.icon)}</button>`).join('')}</aside>
      <aside class="channels">
        <div class="brand"><span class="brand-mark">◈</span><span>${friendsOpen?'Друзья':escapeHtml(activeServer?.name || 'Vessel')}</span><button class="more ${friendsOpen?'hidden':''}">•••</button></div>
        <div class="user-card"><div class="avatar user-avatar">${escapeHtml(user.name?.[0]?.toUpperCase()||'?')}</div><div><b>${escapeHtml(user.name)}</b><small>${escapeHtml(statusLabel(user.status))}</small></div><button class="icon-btn" id="profile-settings" title="Настройки">⚙</button></div>
        <section class="channel-section"><div class="section-title">ЛИЧНЫЕ СООБЩЕНИЯ <button id="dm-add">＋</button></div>
          ${dmList}
        </section>
        <section class="channel-section ${friendsOpen?'hidden':''}"><div class="section-title">ТЕКСТОВЫЕ КАНАЛЫ <button id="channel-add">＋</button></div>
          ${serverChannels().filter(c=>c.kind==='text').map((c,i)=>`<button class="channel ${!currentDm&&activeChannelKind==='text'&&c.name===activeChannelName?'active':''}" data-channel-id="${c.id||''}" data-channel-name="${escapeHtml(c.name)}" data-kind="text"><span>#</span> ${escapeHtml(c.name)}</button>`).join('')}
        </section>
        <section class="channel-section ${friendsOpen?'hidden':''}"><div class="section-title">ГОЛОСОВЫЕ КАНАЛЫ <button id="voice-add">＋</button></div>${serverChannels().filter(c=>c.kind==='voice').map(c=>`<button class="channel ${activeChannelKind==='voice'&&c.name===activeChannelName?'active':''}" data-channel-id="${c.id||''}" data-channel-name="${escapeHtml(c.name)}" data-kind="voice"><span>⌁</span> ${escapeHtml(c.name)}</button>`).join('')}</section>
        <div class="side-footer">Vessel v0.1 <span>●</span></div>
      </aside>
      <section class="chat">
        <header class="chat-head"><div><h1><span>${friendsOpen?'👥':currentDm?'@':activeChannelKind==='voice'?'⌁':'#'}</span> ${friendsOpen?'Друзья':escapeHtml(currentDm || activeChannelName)}</h1><p>${friendsOpen?'Личные контакты и заявки':currentDm?'Личная переписка':activeChannelKind==='voice'?'Голосовая комната':escapeHtml(activeServer?.name || 'Vessel')}</p></div><div class="head-actions"><button id="mobile-nav" title="Каналы">☰</button>${canManageChannel?`<button id="channel-settings" title="Настройки канала">•••</button>`:''}${callActions}<button id="join-voice" class="join-voice ${!friendsOpen&&activeChannelKind==='voice'?'':'hidden'}">${voiceStream?(voiceChannelId===activeChannelId?'Выйти':'Переключиться'):'Войти'}</button><button id="mute-voice" class="join-voice ${!friendsOpen&&voiceStream&&voiceChannelId===activeChannelId?'':'hidden'}">${voiceStream?.getAudioTracks()[0]?.enabled===false?'🔇':'🎙'}</button><button id="search-button" class="${friendsOpen?'hidden':''}">⌕</button><button id="friends-button" title="Друзья" class="${friendsOpen?'hidden':''}">♧</button><button id="notifications" title="Уведомления">🔔${notifications.filter(n=>!n.read_at).length?` <sup>${notifications.filter(n=>!n.read_at).length}</sup>`:''}</button><button id="head-settings">⚙</button></div></header>
        <video id="remote-video" class="remote-video ${remoteCallStream?'':'hidden'}" autoplay playsinline></video><video id="local-video" class="local-video ${callStream||voiceStream?.getVideoTracks().length?'':'hidden'}" autoplay muted playsinline></video><div class="messages">${friendsOpen?`<div class="friends-view"><div class="friends-hero"><h2>Друзья</h2><button id="add-friend" class="primary">Найти пользователя</button></div>${friendRequests.map(request=>`<div class="friend-row request-row"><div class="avatar" style="background:#ffb45e">${(request.profiles?.username||'?')[0].toUpperCase()}</div><b>${escapeHtml(request.profiles?.username||'Пользователь')}</b><span>Заявка</span><button data-accept-request="${request.id}" data-sender="${request.sender_id}">Принять</button><button class="danger compact" data-decline-request="${request.id}">Отклонить</button></div>`).join('')}${outgoingFriendRequests.map(request=>`<div class="friend-row outgoing-request-row"><div class="avatar" style="background:#5a6380">${escapeHtml((request.profiles?.username||'?')[0].toUpperCase())}</div><b>${escapeHtml(request.profiles?.username||'Пользователь')}</b><span class="pending-label">Ожидает подтверждения</span><button class="danger compact" data-cancel-request="${request.id}" title="Отменить заявку">×</button></div>`).join('')}${friends.length ? friends.map(friend=>`<div class="friend-row"><div class="avatar" style="background:${friend.avatar_color||'#8b7cff'}">${friend.username[0].toUpperCase()}</div><b>${escapeHtml(friend.username)}</b><span>${escapeHtml(statusLabel(friend.status))}</span><button data-dm-id="${friend.id}" data-dm="${escapeHtml(friend.username)}">💬</button><button data-call-id="${friend.id}" data-call="${escapeHtml(friend.username)}">📞</button><button class="danger compact" data-remove-friend="${friend.id}" title="Удалить из друзей">×</button></div>`).join('') : `<p class="empty-state">Пока нет добавленных друзей. Нажми «Найти пользователя».</p>`}</div>`:`<div class="welcome"><div class="welcome-icon">${currentDm?'@':activeChannelKind==='voice'?'⌁':'#'}</div><h2>${currentDm?`Переписка с ${escapeHtml(currentDm)}`:`Добро пожаловать в ${activeChannelKind==='voice'?'':'#'}${escapeHtml(activeChannelName)}!`}</h2><p>${activeChannelKind==='voice'?'Подключись к комнате, чтобы общаться голосом.':'Здесь начинается ваше общение.'}</p></div>${(activeDmId?dmMessages:messages).map(m => `<article class="message"><div class="avatar" style="background:${escapeHtml(m.color||'#8b7cff')}">${escapeHtml(m.name?.[0]||'?')}</div><div><div class="message-meta"><b>${escapeHtml(m.name)}</b><time>${escapeHtml(m.time)}</time></div><p>${escapeHtml(m.text)}</p>${attachmentMarkup(m.attachments)}</div></article>`).join('')}`}</div>
        ${activeDmId&&!activeDmIsFriend?'<div class="dm-empty">История доступна только для чтения. Добавь пользователя в друзья, чтобы снова писать и звонить.</div>':''}<form class="composer ${friendsOpen||(!currentDm&&activeChannelKind==='voice')||(activeDmId&&!activeDmIsFriend)?'hidden':''}"><button type="button" class="attach">＋</button><input placeholder="${currentDm?`Написать пользователю ${escapeHtml(currentDm)}`:`Написать в #${escapeHtml(activeChannelName)}`}" /><button type="button" id="emoji-button" title="Эмодзи">☺</button><button type="submit" class="send">➤</button></form>
      </section>
      <aside class="members">${friendsOpen?`<div class="members-title">ДРУЗЬЯ — ${friends.length}</div><div class="dm-empty">${friendRequests.length?`Входящих заявок: ${friendRequests.length}`:outgoingFriendRequests.length?`Исходящих заявок: ${outgoingFriendRequests.length}`:'Выбери друга, чтобы открыть личный чат.'}</div>`:`${voiceStream?`<div class="voice-status">🎙 В голосовой комнате: ${Math.max(1,voiceParticipants.length)}</div>`:''}${membersList}`}</aside>
    </main><div class="modal hidden" id="settings-modal"><div class="modal-card"><button class="modal-close" id="close-settings">×</button><h2>Настройки профиля</h2><p>Измени данные, которые видят другие участники Vessel.</p><form id="settings-form"><label>Имя пользователя<input name="name" value="${escapeHtml(user.name)}" required minlength="2" maxlength="32" /></label><label>Статус<select name="status"><option value="online" ${['online','В сети'].includes(user.status)?'selected':''}>В сети</option><option value="dnd" ${['dnd','Не беспокоить'].includes(user.status)?'selected':''}>Не беспокоить</option><option value="away" ${['away','Отошёл'].includes(user.status)?'selected':''}>Отошёл</option></select></label><button class="primary" type="submit">Сохранить изменения</button></form><button class="danger" id="logout" type="button">Выйти из аккаунта</button></div></div>${incomingCall?`<div class="modal call-modal" id="incoming-call-modal"><div class="modal-card"><div class="call-avatar">${escapeHtml(incomingCall.name?.[0]?.toUpperCase()||'?')}</div><h2>${incomingCall.video?'Видеозвонок':'Аудиозвонок'}</h2><p>${escapeHtml(incomingCall.name)} звонит тебе в Vessel.</p><div class="call-actions"><button class="danger" id="reject-call" type="button">Отклонить</button><button class="primary" id="accept-call" type="button">Принять</button></div></div></div>`:''}`;
  document.querySelector('.composer').addEventListener('submit', async e => { e.preventDefault(); const input=e.currentTarget.querySelector('input'); const text=input.value.trim(); if(!text)return; if(!supabase||!user.id){vesselNotice('Нужна активная сессия Vessel.','error');return;} if(activeDmId){ const peerId=activeDmId; const {error}=await supabase.from('direct_messages').insert({sender_id:user.id,receiver_id:peerId,body:text}); if(error){vesselNotice(`Не удалось отправить личное сообщение: ${error.message}`,'error');return;} window.__vesselDmThreadsLoaded=false; await Promise.all([loadDirectMessages(user,peerId),syncDmThreads(user)]); } else { if(!activeChannelId||activeChannelKind!=='text'){vesselNotice('Сначала выбери текстовый канал.','error');return;} const {error}=await supabase.from('messages').insert({channel_id:activeChannelId,author_id:user.id,body:text}); if(error){vesselNotice(`Не удалось отправить сообщение: ${error.message}`,'error');return;} messages.push({name:user.name,time:'только что',color:user.avatarColor||'#39d9a6',text}); } input.value=''; render(); const list=document.querySelector('.messages'); if(list)list.scrollTop=list.scrollHeight; });
  document.querySelector('#emoji-button')?.addEventListener('click',async()=>{
    const emoji=await vesselChoice('Эмодзи',[{label:'😀',value:'😀'},{label:'😂',value:'😂'},{label:'❤️',value:'❤️'},{label:'👍',value:'👍'},{label:'🔥',value:'🔥'},{label:'🎉',value:'🎉'},{label:'😎',value:'😎'},{label:'🤝',value:'🤝'}]);
    if(!emoji)return;
    const input=document.querySelector('.composer input');
    if(!input)return;
    const start=input.selectionStart??input.value.length;
    const end=input.selectionEnd??start;
    input.value=input.value.slice(0,start)+emoji+input.value.slice(end);
    input.focus();
    input.setSelectionRange(start+emoji.length,start+emoji.length);
  });
  document.querySelector('.attach').addEventListener('click', () => {
    const picker=document.createElement('input'); picker.type='file'; picker.accept='image/*,.pdf,.doc,.docx,.zip';
    picker.onchange=async()=>{
      const file=picker.files[0]; if(!file)return;
      const targetDmId=activeDmId;
      const targetChannelId=!targetDmId&&activeChannelKind==='text'?activeChannelId:null;
      if(!targetDmId&&!targetChannelId){vesselNotice('Открой текстовый канал или личный чат.','error');return;}
      const attachment=await uploadVesselFile(file,user); if(!attachment)return;
      const body=`📎 ${file.name}`;
      if(targetDmId){
        const peerId=targetDmId;
        const {error}=await supabase.from('direct_messages').insert({sender_id:user.id,receiver_id:peerId,body,attachments:[attachment]});
        if(error){await cleanupFailedAttachment(attachment);vesselNotice(`Не удалось отправить файл: ${error.message}`,'error');return;}
        window.__vesselDmThreadsLoaded=false;
        const refreshes=[syncDmThreads(user)];
        if(activeDmId===peerId)refreshes.push(loadDirectMessages(user,peerId));
        await Promise.all(refreshes);
      } else {
        const {error}=await supabase.from('messages').insert({channel_id:targetChannelId,author_id:user.id,body,attachments:[attachment]});
        if(error){await cleanupFailedAttachment(attachment);vesselNotice(`Не удалось отправить файл: ${error.message}`,'error');return;}
        if(!activeDmId&&activeChannelId===targetChannelId&&activeChannelKind==='text'){
          messages.push({name:user.name,time:'только что',color:user.avatarColor||'#39d9a6',text:body,attachments:[attachment]});
        }
      }
      render();
    };
    picker.click();
  });
  document.querySelector('#search-button').addEventListener('click', async () => {
    const query=await vesselPrompt('Поиск по сообщениям','','Что найти?');
    if(!query?.trim())return;
    const source=activeDmId?dmMessages:messages;
    const needle=query.trim().toLowerCase();
    const found=source.filter(message=>(message.text||'').toLowerCase().includes(needle)).slice(-50).reverse();
    vesselListDialog(`Поиск: ${query.trim()}`,found.map(message=>({title:message.name,body:message.text,meta:message.time})), 'Совпадений не найдено');
  });
  document.querySelector('#notifications').addEventListener('click', async () => {
    vesselListDialog('Уведомления',notifications.map(item=>({title:item.title||'Vessel',body:item.body||'',meta:item.created_at?new Date(item.created_at).toLocaleString('ru-RU'):''})), 'Уведомлений пока нет');
    const unread=notifications.filter(item=>!item.read_at);
    if(unread.length&&supabase&&user.id){
      await supabase.from('notifications').update({read_at:new Date().toISOString()}).eq('user_id',user.id).is('read_at',null);
      notifications=notifications.map(item=>({...item,read_at:item.read_at||new Date().toISOString()}));
      render();
    }
  });
  const modal = document.querySelector('#settings-modal');
  document.querySelector('#profile-settings').addEventListener('click', () => modal.classList.remove('hidden'));
  document.querySelector('#mobile-nav')?.addEventListener('click',()=>document.querySelector('.channels')?.classList.toggle('mobile-open'));
  document.querySelector('.more').addEventListener('click', async () => {
    const server=getActiveServer();
    if(!server?.dbId){vesselNotice('Сначала выбери сервер.','error');return;}
    if(server.role==='owner'){
      const action=await vesselChoice('Управление сервером',[{label:'Создать приглашение',value:'1'},{label:'Переименовать сервер',value:'2'},{label:'Удалить сервер',value:'3',danger:true}]);
      if(action==='1'){
        const code=`VSL-${crypto.randomUUID().slice(0,8).toUpperCase()}`;
        const {error}=await supabase.from('server_invites').insert({server_id:server.dbId,created_by:user.id,code});
        if(error)vesselNotice(`Не удалось создать приглашение: ${error.message}`,'error');else vesselCodeDialog(`Приглашение в ${server.name}`,code);
        return;
      }
      if(action==='2'){
        const name=await vesselPrompt('Переименовать сервер',server.name,'Название сервера');
        if(!name?.trim()||name.trim()===server.name)return;
        const {error}=await supabase.from('servers').update({name:name.trim()}).eq('id',server.dbId).eq('owner_id',user.id);
        if(error){vesselNotice(`Не удалось переименовать сервер: ${error.message}`,'error');return;}
        server.name=name.trim(); render(); return;
      }
      if(action==='3'){
        if(!await vesselConfirm(`Удалить сервер «${server.name}»?`,'Каналы и сообщения этого сервера тоже будут удалены.'))return;
        if(voiceStream&&voiceServerId===server.dbId)await leaveVoiceRoom();
        const {error}=await supabase.from('servers').delete().eq('id',server.dbId).eq('owner_id',user.id);
        if(error){vesselNotice(`Не удалось удалить сервер: ${error.message}`,'error');return;}
        window.__vesselServersLoaded=false; activeServerId=null; localStorage.removeItem('vesselActiveServerId'); activeServerIndex=0; activeChannelId=null; currentDm=null; activeDmId=null; dbChannels=[]; messages=[]; serverMembers=[]; window.__vesselMembersServerId=null;
        await syncSupabaseServers(user);
        const next=getActiveServer();
        if(next?.dbId){next.__channelsLoaded=false;await syncSupabaseChannels(next);await syncServerMembers(user,next);} else render();
        return;
      }
      return;
    }
    if(await vesselConfirm(`Выйти из сервера «${server.name}»?`)){
      if(voiceStream&&voiceServerId===server.dbId)await leaveVoiceRoom();
      const {error}=await supabase.from('server_members').delete().eq('server_id',server.dbId).eq('user_id',user.id);
      if(error){vesselNotice(`Не удалось выйти из сервера: ${error.message}`,'error');return;}
      window.__vesselServersLoaded=false; activeServerId=null; localStorage.removeItem('vesselActiveServerId'); activeServerIndex=0; activeChannelId=null; currentDm=null; activeDmId=null; dbChannels=[]; messages=[]; serverMembers=[]; window.__vesselMembersServerId=null;
      await syncSupabaseServers(user);
      const next=getActiveServer();
      if(next?.dbId){next.__channelsLoaded=false;await syncSupabaseChannels(next);await syncServerMembers(user,next);} else render();
    }
  });
  const addChannel = async kind => {
    const name=await vesselPrompt(kind==='voice'?'Новая голосовая комната':'Новый текстовый канал','','Название');
    const channelName=String(name||'').trim().replace(/\s+/g,'-').replace(/-+/g,'-').slice(0,50);
    if(!channelName)return;
    const server=getActiveServer();
    if(!supabase||!user.id||!server?.dbId){vesselNotice('Сначала выбери настоящий сервер.','error');return;}
    if(server.role!=='owner'){vesselNotice('Создавать каналы может только владелец сервера.','error');return;}
    if(serverChannels().some(channel=>channel.name.toLocaleLowerCase('ru-RU')===channelName.toLocaleLowerCase('ru-RU'))){vesselNotice('Канал с таким названием уже существует.','error');return;}
    const position=serverChannels().reduce((max,channel)=>Math.max(max,Number(channel.position)||0),-1)+1;
    const {data,error}=await supabase.from('channels').insert({server_id:server.dbId,name:channelName,kind,position}).select('id,name,kind,position').single();
    if(error){vesselNotice(`Не удалось создать канал: ${error.message}`,'error');return;}
    activeChannelId=data.id; activeChannelName=data.name; activeChannelKind=data.kind; currentDm=null; activeDmId=null; friendsOpen=false; messages=[];
    server.__channelsLoaded=false;
    await syncSupabaseChannels(server);
    vesselNotice(`${kind==='voice'?'Голосовой':'Текстовый'} канал «${data.name}» создан.`,'success');
  };
  document.querySelector('#channel-add').addEventListener('click', () => addChannel('text'));
  document.querySelector('#voice-add').addEventListener('click', () => addChannel('voice'));
  document.querySelector('#channel-settings')?.addEventListener('click',async()=>{
    const server=getActiveServer();
    if(!server?.dbId||server.role!=='owner'||!activeChannelId)return;
    const channel=serverChannels().find(item=>item.id===activeChannelId);
    if(!channel)return;
    const action=await vesselChoice(`Канал «${channel.name}»`,[{label:'Переименовать',value:'1'},{label:'Удалить',value:'2',danger:true}]);
    if(action==='1'){
      const name=await vesselPrompt('Переименовать канал',channel.name,'Название канала');
      const channelName=String(name||'').trim().replace(/\s+/g,'-').replace(/-+/g,'-').slice(0,50);
      if(!channelName||channelName===channel.name)return;
      if(serverChannels().some(item=>item.id!==channel.id&&item.name.toLocaleLowerCase('ru-RU')===channelName.toLocaleLowerCase('ru-RU'))){vesselNotice('Канал с таким названием уже существует.','error');return;}
      const {error}=await supabase.from('channels').update({name:channelName}).eq('id',channel.id).eq('server_id',server.dbId);
      if(error){vesselNotice(`Не удалось переименовать канал: ${error.message}`,'error');return;}
      activeChannelId=channel.id;
      server.__channelsLoaded=false;
      await syncSupabaseChannels(server);
      vesselNotice(`Канал переименован в «${channelName}».`,'success');
      return;
    }
    if(action==='2'){
      if(!await vesselConfirm(`Удалить канал «${channel.name}»?`))return;
      if(voiceChannelId===channel.id&&voiceStream)await leaveVoiceRoom();
      const {error}=await supabase.from('channels').delete().eq('id',channel.id).eq('server_id',server.dbId);
      if(error){vesselNotice(`Не удалось удалить канал: ${error.message}`,'error');return;}
      if(activeChannelId===channel.id){activeChannelId=null;activeChannelName='нет каналов';activeChannelKind='text';messages=[];}
      server.__channelsLoaded=false;
      await syncSupabaseChannels(server);
      vesselNotice(`Канал «${channel.name}» удалён.`,'success');
    }
  });
  document.querySelector('#dm-add').addEventListener('click', () => findAndRequestFriend(user));
  document.querySelector('#close-settings').addEventListener('click', () => modal.classList.add('hidden'));
  document.querySelector('#settings-form').addEventListener('submit', async e => {
    e.preventDefault();
    const data=new FormData(e.currentTarget);
    const name=String(data.get('name')||'').trim();
    const status=String(data.get('status')||'online');
    if(name.length<2||name.length>32){vesselNotice('Имя пользователя должно содержать от 2 до 32 символов.','error');return;}
    if(!supabase||!user.id){vesselNotice('Сессия Vessel недоступна.','error');return;}
    const {data:updated,error}=await supabase.from('profiles').update({username:name,status}).eq('id',user.id).select('username,status,avatar_color').single();
    if(error){
      vesselNotice(error.code==='23505'?'Это имя пользователя уже занято.':'Не удалось сохранить профиль.','error');
      return;
    }
    savedUser={...user,name:updated?.username||name,status:updated?.status||status,avatarColor:updated?.avatar_color||user.avatarColor};
    localStorage.setItem('vesselUser',JSON.stringify(savedUser));
    modal.classList.add('hidden');
    vesselNotice('Профиль сохранён.','success');
    render();
  });
  document.querySelector('#logout').addEventListener('click', async () => { if(supabase) await supabase.auth.signOut().catch(()=>{}); localStorage.removeItem('vesselUser'); localStorage.removeItem('vesselToken'); location.reload(); });
  document.querySelector('#accept-call')?.addEventListener('click', () => acceptIncomingCall(user));
  document.querySelector('#reject-call')?.addEventListener('click', () => rejectIncomingCall(user));
  document.querySelectorAll('.channel:not(.dm)').forEach(channel=>channel.addEventListener('click',async()=>{
    const channelId=channel.dataset.channelId||null;
    if(!channelId)return;
    const kind=channel.dataset.kind||'text';
    const name=channel.dataset.channelName||channel.textContent.replace('#','').replace('⌁','').trim();
    currentDm=null;
    activeDmId=null;
    friendsOpen=false;
    window.__vesselDmLoaded=false;
    activeChannelId=channelId;
    activeChannelName=name;
    activeChannelKind=kind;
    messages=[];
    document.querySelector('.channels')?.classList.remove('mobile-open');
    if(kind==='text')await loadChannelMessages(channelId);else render();
  }));
  const openFriendsHome=()=>{friendsOpen=true;currentDm=null;activeDmId=null;dmMessages=[];window.__vesselDmLoaded=false;render();};
  document.querySelector('#friends-tab').addEventListener('click',openFriendsHome);
  document.querySelector('#friends-button').addEventListener('click',openFriendsHome);
  document.querySelector('#head-settings').addEventListener('click',()=>modal.classList.remove('hidden'));
  document.querySelectorAll('[data-manage-member]').forEach(button=>button.addEventListener('click',async()=>{
    const server=getActiveServer();
    if(!supabase||!user.id||server?.role!=='owner')return;
    const memberId=button.dataset.manageMember;
    const member=serverMembers.find(item=>item.id===memberId);
    if(!member)return;
    const action=await vesselChoice(`Участник ${member.username}`,[{label:'Сделать участником',value:'1'},{label:'Сделать модератором',value:'2'},{label:'Исключить из сервера',value:'3',danger:true}]);
    if(action==='1'||action==='2'){
      const role=action==='2'?'moderator':'member';
      const {error}=await supabase.from('server_members').update({role}).eq('server_id',server.dbId).eq('user_id',memberId);
      if(error){vesselNotice(`Не удалось изменить роль: ${error.message}`,'error');return;}
      window.__vesselMembersServerId=null;serverMembers=[];await syncServerMembers(user,server);render();return;
    }
    if(action==='3'){
      if(!await vesselConfirm(`Исключить ${member.username} из сервера?`))return;
      const {error}=await supabase.from('server_members').delete().eq('server_id',server.dbId).eq('user_id',memberId);
      if(error){vesselNotice(`Не удалось исключить участника: ${error.message}`,'error');return;}
      window.__vesselMembersServerId=null;serverMembers=[];await syncServerMembers(user,server);render();
    }
  }));
  document.querySelectorAll('[data-dm]').forEach(button=>button.addEventListener('click',()=>{currentDm=button.dataset.dm;activeDmId=button.dataset.dmId||null;friendsOpen=false;window.__vesselDmLoaded=false;render();}));
  document.querySelectorAll('[data-attachment-path]').forEach(button=>button.addEventListener('click',()=>openAttachment(button.dataset.attachmentPath)));
  document.querySelectorAll('[data-remove-friend]').forEach(button=>button.addEventListener('click',async()=>{
    if(!supabase||!user.id)return;
    const friendId=button.dataset.removeFriend;
    const friend=friends.find(item=>item.id===friendId);
    if(!await vesselConfirm(`Удалить ${friend?.username||'пользователя'} из друзей?`))return;
    const {error}=await supabase.from('friendships').delete().or(`and(user_id.eq.${user.id},friend_id.eq.${friendId}),and(user_id.eq.${friendId},friend_id.eq.${user.id})`);
    if(error){vesselNotice(`Не удалось удалить друга: ${error.message}`,'error');return;}
    if(activeDmId===friendId){activeDmId=null;currentDm=null;dmMessages=[];window.__vesselDmLoaded=false;}
    window.__vesselSocialLoaded=false;await syncSocial(user);render();
  }));
  document.querySelectorAll('[data-cancel-request]').forEach(button=>button.addEventListener('click',async()=>{
    if(!supabase||!user.id)return;
    const requestId=button.dataset.cancelRequest;
    const {error}=await supabase.from('friend_requests').delete().eq('id',requestId).eq('sender_id',user.id).eq('status','pending');
    if(error){vesselNotice('Не удалось отменить заявку.','error');return;}
    window.__vesselSocialLoaded=false;
    await syncSocial(user);
    vesselNotice('Заявка отменена.','success');
  }));
  document.querySelectorAll('[data-accept-request]').forEach(button=>button.addEventListener('click',async()=>{if(!supabase||!user.id)return;const {error}=await supabase.from('friend_requests').update({status:'accepted',updated_at:new Date().toISOString()}).eq('id',button.dataset.acceptRequest).eq('receiver_id',user.id);if(error){vesselNotice('Не удалось принять заявку.','error');return;}else vesselNotice('Заявка принята.','success');window.__vesselSocialLoaded=false;await syncSocial(user);render();}));
  document.querySelectorAll('[data-decline-request]').forEach(button=>button.addEventListener('click',async()=>{if(!supabase||!user.id)return;const {error}=await supabase.from('friend_requests').update({status:'declined',updated_at:new Date().toISOString()}).eq('id',button.dataset.declineRequest).eq('receiver_id',user.id);if(error){vesselNotice('Не удалось отклонить заявку.','error');return;}else vesselNotice('Заявка отклонена.');window.__vesselSocialLoaded=false;await syncSocial(user);render();}));
  document.querySelector('#add-friend')?.addEventListener('click',()=>findAndRequestFriend(user));
  document.querySelector('#audio-call')?.addEventListener('click',()=>startCall(false,user));
  document.querySelector('#video-call')?.addEventListener('click',()=>startCall(true,user));
  document.querySelector('#end-call')?.addEventListener('click',()=>endCall(true));
  document.querySelector('#toggle-call-mic')?.addEventListener('click',toggleCallMicrophone);
  document.querySelector('#toggle-call-camera')?.addEventListener('click',toggleCallCamera);
  document.querySelectorAll('[data-call-id]').forEach(button=>button.addEventListener('click',()=>{currentDm=button.dataset.call;activeDmId=button.dataset.callId;friendsOpen=false;window.__vesselDmLoaded=false;render();startCall(false,user);}));
  document.querySelectorAll('.server[data-server-index]').forEach(server => server.addEventListener('click', async () => {
    if (server.classList.contains('add')) {
      const addMode=await vesselChoice('Добавить сервер',[{label:'Вступить по приглашению',value:'join'},{label:'Создать свой сервер',value:'create'}]);
      if(addMode==='join'){
        const code=await vesselPrompt('Вступить в сервер','','Код VSL-…');
        if(code?.trim())await joinByInvite(code,user);
        return;
      }
      if(addMode!=='create')return;
      const name=await vesselPrompt('Создать сервер','','Название сервера');
      if(name&&name.trim()){
        if(!supabase||!user.id){vesselNotice('Нужна активная сессия Vessel.','error');return;}
        const icon=name.trim()[0].toUpperCase();
        const {data,error}=await supabase.from('servers').insert({name:name.trim(),icon,owner_id:user.id}).select('id,name,icon').single();
        if(error){vesselNotice(`Не удалось создать сервер: ${error.message}`,'error');return;}
        window.__vesselServersLoaded=false;
        await syncSupabaseServers(user);
        setActiveServer(data.id);
        serverMembers=[]; window.__vesselMembersServerId=null;
        const selected=getActiveServer();
        selected.__channelsLoaded=false;
        await syncSupabaseChannels(selected);
        await syncServerMembers(user,selected);
      }
      return;
    }
    const selected=servers[Number(server.dataset.serverIndex)];
    if(!selected||selected.add)return;
    setActiveServer(selected);
    activeChannelName='загрузка…';activeChannelKind='text';activeChannelId=null;currentDm=null;activeDmId=null;friendsOpen=false;dbChannels=[];messages=[];serverMembers=[];window.__vesselMembersServerId=null;
    selected.__channelsLoaded=false;
    render();
    await syncSupabaseChannels(selected);
    await syncServerMembers(user,selected);
  }));
}
const authStateSubscription=supabase?.auth.onAuthStateChange((event,session)=>handleAuthStateChange(event,session)).data?.subscription||null;
window.addEventListener('beforeunload',()=>authStateSubscription?.unsubscribe());
bootstrapAuth().then(render).catch(error=>{console.error('Vessel bootstrap failed',error);const staleChannels=resetAuthenticatedRuntime();render();cleanupAuthenticatedChannels(staleChannels).catch(()=>{});});
setInterval(()=>{const video=document.querySelector('#local-video');const stream=callStream||voiceStream;if(video&&stream&&video.srcObject!==stream){video.srcObject=stream;video.play().catch(()=>{});}const remote=document.querySelector('#remote-video');if(remote&&remoteCallStream&&remote.srcObject!==remoteCallStream){remote.srcObject=remoteCallStream;remote.play().catch(()=>{});}},500);
