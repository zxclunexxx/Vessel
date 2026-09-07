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
let voiceDeafened = false;
const voicePeers = new Map();
const voicePeerReconnectTimers = new Map();
const voicePeerReconnectAttempts = new Map();
let voiceReconnectTimer = null;
let voiceReconnectAttempt = 0;
let voiceReconnectContext = null;
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
let incomingCallTimer = null;
let callDisconnectTimer = null;
let callInitiator = false;
let callIceRestartAttempts = 0;
let callIceRestartInFlight = false;
let rtcConfigCache = null;
let rtcConfigUserId = null;
let rtcConfigExpiresAt = 0;
let rtcConfigPromise = null;
let callInboxReconnectTimer = null;
let callInboxReconnectAttempt = 0;
let callSignalReconnectTimer = null;
let callSignalReconnectAttempt = 0;
let activeServerIndex = 0;
let activeServerId = localStorage.getItem('vesselActiveServerId') || null;
let serversSyncRevision = 0;
let activeChannelName = 'нет каналов';
let activeChannelKind = 'text';
let currentDm = null;
let activeDmId = null;
let friendsOpen = false;
let friends = [];
let socialSyncRevision = 0;
let dmThreads = [];
let dmThreadsSyncRevision = 0;
let friendRequests = [];
let outgoingFriendRequests = [];
let dmMessages = [];
let dmMessagesSyncRevision = 0;
let notifications = [];
let notificationsSyncRevision = 0;
let dataRealtimeReconnectTimer = null;
let dataRealtimeReconnectAttempt = 0;
let dataRealtimeRecoveryInFlight = false;
let serverMembers = [];
let lastRenderedMessageContext = null;
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
function vesselListDialog(title,items=[],emptyText='Ничего нет',onSelect=null) {
  const overlay=document.createElement('div');
  overlay.className='modal vessel-dialog';
  const content=items.length?items.map((item,index)=>{
    const inner=`<div><b>${escapeHtml(item.title||'')}</b>${item.meta?`<time>${escapeHtml(item.meta)}</time>`:''}</div><p>${escapeHtml(item.body||'')}</p>`;
    return onSelect&&item.value?`<button type="button" class="dialog-list-item dialog-list-button" data-list-index="${index}">${inner}</button>`:`<div class="dialog-list-item">${inner}</div>`;
  }).join(''):`<div class="dialog-empty">${escapeHtml(emptyText)}</div>`;
  overlay.innerHTML=`<div class="modal-card dialog-card dialog-list-card"><button class="modal-close" data-dialog-close>×</button><h2>${escapeHtml(title)}</h2><div class="dialog-list">${content}</div></div>`;
  document.body.appendChild(overlay);
  const close=()=>overlay.remove();
  overlay.querySelector('[data-dialog-close]').addEventListener('click',close);
  overlay.addEventListener('click',event=>{if(event.target===overlay)close();});
  overlay.querySelectorAll('[data-list-index]').forEach(button=>button.addEventListener('click',async()=>{
    const item=items[Number(button.dataset.listIndex)];
    close();
    try{await onSelect?.(item);}catch(error){console.warn('Dialog list action failed',error);vesselNotice('Не удалось открыть уведомление.','error');}
  }));
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
function messageMarkup(message,user,canMutate=true) {
  const own=Boolean(canMutate&&message?.id&&message.authorId===user?.id);
  const edited=message?.editedAt?' · изменено':'';
  const actions=own?`<span class="message-actions"><button type="button" data-edit-message="${escapeHtml(message.id)}" title="Редактировать сообщение">✎</button><button type="button" data-delete-message="${escapeHtml(message.id)}" title="Удалить сообщение">×</button></span>`:'';
  return `<article class="message" data-message-id="${escapeHtml(message?.id||'')}"><div class="avatar" style="background:${escapeHtml(message?.color||'#8b7cff')}">${escapeHtml(message?.name?.[0]||'?')}</div><div class="message-content"><div class="message-meta"><b>${escapeHtml(message?.name||'Пользователь')}</b><time>${escapeHtml(message?.time||'')}${edited}</time>${actions}</div><p>${escapeHtml(message?.text||'')}</p>${attachmentMarkup(message?.attachments)}</div></article>`;
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
  const sessionUserId=savedUser?.id||null;
  if(!sessionUserId)return;
  const {data,error} = await supabase.from('messages').select('id,author_id,body,attachments,created_at,edited_at,profiles(username,avatar_color)').eq('channel_id',channelId).order('created_at',{ascending:false}).limit(100);
  if(savedUser?.id!==sessionUserId||activeDmId||activeChannelId!==channelId||activeChannelKind!=='text')return;
  if(activeDmId||activeChannelId!==channelId||activeChannelKind!=='text')return;
  if(error){vesselNotice('Не удалось загрузить сообщения канала.','error');return;}
  messages = (data||[]).reverse().map(m=>({id:m.id,authorId:m.author_id,name:m.profiles?.username||'Участник',time:new Date(m.created_at).toLocaleString('ru-RU'),editedAt:m.edited_at||null,color:m.profiles?.avatar_color||'#8b7cff',text:m.body,attachments:m.attachments||[]}));
  render();
}
async function syncSupabaseServers(user) {
  if (!supabase || window.__vesselServersLoaded || !user?.id) return;
  const revision=++serversSyncRevision;
  const membershipsResult=await supabase.from('server_members').select('server_id,role').eq('user_id',user.id);
  if(savedUser?.id!==user.id||revision!==serversSyncRevision)return;
  if(membershipsResult.error){vesselNotice('Не удалось загрузить список серверов.','error');return;}
  const memberships=membershipsResult.data||[];
  const memberIds=memberships.map(row=>row.server_id).filter(Boolean);
  const [ownedResult,memberResult]=await Promise.all([
    supabase.from('servers').select('id,name,icon,owner_id').eq('owner_id',user.id).order('created_at'),
    memberIds.length ? supabase.from('servers').select('id,name,icon,owner_id').in('id',memberIds).order('created_at') : Promise.resolve({data:[],error:null})
  ]);
  if(savedUser?.id!==user.id||revision!==serversSyncRevision)return;
  if(ownedResult.error||memberResult.error){vesselNotice('Не удалось загрузить данные серверов.','error');return;}
  const owned=ownedResult.data||[];
  const all=[...owned,...(memberResult.data||[]).filter(server=>!owned.some(item=>item.id===server.id))];
  const nextServers=[...all.map(server=>({id:server.id,dbId:server.id,icon:server.icon||server.name?.[0]?.toUpperCase()||'V',name:server.name,role:server.owner_id===user.id?'owner':memberships.find(member=>member.server_id===server.id)?.role||'member',channels:[]})),{id:'add-server',icon:'+',name:'Добавить сервер',add:true}];
  servers=nextServers;
  window.__vesselServersLoaded=true;
  const selected=setActiveServer(activeServerId && all.some(server=>server.id===activeServerId) ? activeServerId : all[0]?.id||null);
  if(!selected){activeChannelId=null;activeChannelName='нет каналов';activeChannelKind='text';dbChannels=[];messages=[];serverMembers=[];window.__vesselMembersServerId=null;}
  render();
}
async function syncSupabaseChannels(server) {
  if (!supabase || !server?.dbId || server.__channelsLoaded) return;
  const sessionUserId=savedUser?.id||null;
  const serverId=server.dbId;
  if(!sessionUserId)return;
  const {data,error}=await supabase.from('channels').select('id,name,kind,position').eq('server_id',serverId).order('position');
  const activeServer=getActiveServer();
  const serverStillActive=Boolean(savedUser?.id===sessionUserId&&server===activeServer&&serverId===activeServer?.dbId);
  if(savedUser?.id!==sessionUserId||!servers.includes(server))return;
  if(error){console.warn('Channel sync failed',error);if(serverStillActive)vesselNotice('Не удалось загрузить каналы сервера.','error');return;}
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
  if(savedUser?.id!==user.id||server.dbId!==getActiveServer()?.dbId)return;
  if (error) { console.warn('Server members failed', error); serverMembers=[]; return; }
  const ids=(memberships||[]).map(row=>row.user_id).filter(Boolean);
  let profiles=[];
  if(ids.length){
    const result=await supabase.from('profiles').select('id,username,avatar_color,status').in('id',ids);
    if(savedUser?.id!==user.id||server.dbId!==getActiveServer()?.dbId)return;
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
  const {data:existing,error:existingError}=await supabase.from('friend_requests').select('id,status,sender_id,receiver_id').or(`and(sender_id.eq.${user.id},receiver_id.eq.${target.id}),and(sender_id.eq.${target.id},receiver_id.eq.${user.id})`);
  if(existingError){vesselNotice('Не удалось проверить заявки в друзья.','error');return;}
  const requests=existing||[];
  const pending=requests.find(request=>request.status==='pending');
  if(pending){
    vesselNotice(pending.receiver_id===user.id ? `${target.username} уже отправил тебе заявку. Открой раздел «Друзья».` : 'Заявка уже отправлена.');
    return;
  }
  const outgoing=requests.find(request=>request.sender_id===user.id&&request.receiver_id===target.id);
  let sendError=null;
  let sentRequest=null;
  if(outgoing&&['accepted','declined','cancelled'].includes(outgoing.status)){
    const result=await supabase.from('friend_requests').update({status:'pending',updated_at:new Date().toISOString()}).eq('id',outgoing.id).eq('sender_id',user.id).in('status',['accepted','declined','cancelled']).select('id,status').maybeSingle();
    sendError=result.error;
    sentRequest=result.data;
    if(!sendError&&!sentRequest){
      window.__vesselSocialLoaded=false;
      await syncSocial(user);
      vesselNotice('Состояние заявки уже изменилось. Список друзей обновлён.');
      return;
    }
  }else{
    const result=await supabase.from('friend_requests').insert({sender_id:user.id,receiver_id:target.id,status:'pending'}).select('id,status').single();
    sendError=result.error;
    sentRequest=result.data;
  }
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
  const revision=++socialSyncRevision;
  const {data: links, error: linksError} = await supabase.from('friendships').select('friend_id').eq('user_id', user.id);
  if(savedUser?.id!==user.id||revision!==socialSyncRevision)return;
  if(linksError){vesselNotice('Не удалось загрузить список друзей.','error');return;}
  const ids = (links || []).map(row => row.friend_id).filter(Boolean);
  let nextFriends = [];
  if (ids.length) {
    const {data: profiles, error: profilesError} = await supabase.from('profiles').select('id,username,avatar_color,status').in('id', ids);
    if(savedUser?.id!==user.id||revision!==socialSyncRevision)return;
    if(profilesError){vesselNotice('Не удалось загрузить профили друзей.','error');return;}
    nextFriends = profiles || [];
  }
  const [incomingResult,outgoingResult]=await Promise.all([
    supabase.from('friend_requests').select('id,sender_id,status,created_at,profiles!friend_requests_sender_id_fkey(username,avatar_color)').eq('receiver_id', user.id).eq('status','pending').order('created_at',{ascending:false}),
    supabase.from('friend_requests').select('id,receiver_id,status,created_at,profiles!friend_requests_receiver_id_fkey(username,avatar_color)').eq('sender_id', user.id).eq('status','pending').order('created_at',{ascending:false})
  ]);
  if(savedUser?.id!==user.id||revision!==socialSyncRevision)return;
  if(incomingResult.error||outgoingResult.error){vesselNotice('Не удалось загрузить заявки в друзья.','error');return;}
  friends = nextFriends;
  friendRequests = incomingResult.data || [];
  outgoingFriendRequests = outgoingResult.data || [];
  window.__vesselSocialLoaded = true;
  if (document.querySelector('#app')) render();
}
async function syncDmThreads(user) {
  if (!supabase || !user?.id || window.__vesselDmThreadsLoaded) return;
  const revision=++dmThreadsSyncRevision;
  const {data,error}=await supabase.rpc('vessel_dm_threads');
  if(savedUser?.id!==user.id||revision!==dmThreadsSyncRevision)return;
  if(error){console.warn('DM thread sync failed',error);vesselNotice('Не удалось загрузить список личных чатов.','error');return;}
  dmThreads=(data||[]).map(row=>({id:row.peer_id,username:row.username||'Пользователь',avatar_color:row.avatar_color||'#8b7cff',status:row.status||'online',last_message_at:row.last_message_at}));
  window.__vesselDmThreadsLoaded=true;
  if(document.querySelector('#app'))render();
}
async function syncNotifications(user) {
  if (!supabase || !user?.id || window.__vesselNotificationsLoaded) return;
  const revision=++notificationsSyncRevision;
  const {data,error}=await supabase.from('notifications').select('id,type,title,body,data,read_at,created_at').eq('user_id',user.id).order('created_at',{ascending:false}).limit(100);
  if(savedUser?.id!==user.id||revision!==notificationsSyncRevision)return;
  if(error){console.warn('Notification sync failed',error);vesselNotice('Не удалось загрузить уведомления.','error');return;}
  notifications=data||[]; window.__vesselNotificationsLoaded=true;
  if (document.querySelector('#app')) render();
}
function unreadDirectMessageCount(peerId) {
  if(!peerId)return 0;
  return notifications.filter(item=>!item.read_at&&item.type==='direct_message'&&item.data?.sender_id===peerId).length;
}
async function markDirectMessageNotificationsRead(user,peerId,notificationId=null) {
  if(!supabase||!user?.id||!peerId)return;
  const sessionUserId=user.id;
  if(savedUser?.id!==sessionUserId)return;
  const localUnread=notifications.filter(item=>!item.read_at&&item.type==='direct_message'&&item.data?.sender_id===peerId&&(!notificationId||item.id===notificationId));
  if(notificationId&&!localUnread.length)return;
  const readAt=new Date().toISOString();
  let query=supabase.from('notifications').update({read_at:readAt}).eq('user_id',sessionUserId).eq('type','direct_message').is('read_at',null);
  const result=notificationId
    ? await query.eq('id',notificationId).select('id')
    : await query.contains('data',{sender_id:peerId}).select('id');
  if(savedUser?.id!==sessionUserId)return;
  if(result.error){console.warn('DM notification read update failed',result.error);return;}
  const updatedIds=new Set((result.data||[]).map(row=>row.id));
  if(!updatedIds.size)return;
  notifications=notifications.map(item=>updatedIds.has(item.id)&&!item.read_at?{...item,read_at:readAt}:item);
  render();
}
async function loadDirectMessages(user, friendId) {
  if (!supabase || !user?.id || !friendId) return;
  const dmLoadUserId=user.id;
  const revision=++dmMessagesSyncRevision;
  if(savedUser?.id!==dmLoadUserId)return;
  const {data,error} = await supabase.from('direct_messages').select('id,sender_id,receiver_id,body,attachments,created_at,edited_at,deleted_at,profiles!direct_messages_sender_id_fkey(username,avatar_color)').or(`and(sender_id.eq.${dmLoadUserId},receiver_id.eq.${friendId}),and(sender_id.eq.${friendId},receiver_id.eq.${dmLoadUserId})`).is('deleted_at',null).order('created_at',{ascending:false}).limit(100);
  if(savedUser?.id!==dmLoadUserId||revision!==dmMessagesSyncRevision||activeDmId!==friendId)return;
  if(error){window.__vesselDmLoaded=false;vesselNotice('Не удалось загрузить личные сообщения.','error');return;}
  dmMessages = (data || []).reverse().map(row => ({id:row.id,authorId:row.sender_id,name:row.profiles?.username || 'Пользователь',time:new Date(row.created_at).toLocaleString('ru-RU'),editedAt:row.edited_at||null,color:row.profiles?.avatar_color || '#8b7cff',text:row.body,attachments:row.attachments||[]}));
  render();
}
async function uploadVesselFile(file, user, context) {
  if (!supabase || !user?.id) { vesselNotice('Для загрузки файлов нужен настоящий аккаунт.','error'); return null; }
  if(file.size>25*1024*1024){vesselNotice('Максимальный размер файла — 25 МБ.','error');return null;}
  const storageContext=String(context||'');
  if(!/^(dm|channel)\/[^/]+$/.test(storageContext)){vesselNotice('Контекст загрузки файла устарел. Выбери чат или канал ещё раз.','error');return null;}
  const safeName=file.name.replace(/[^a-zA-Z0-9._-]/g,'_')||'file';
  const objectPath=`${user.id}/${storageContext}/${crypto.randomUUID()}-${safeName}`;
  const {error}=await supabase.storage.from('vessel-files').upload(objectPath,file,{contentType:file.type||'application/octet-stream',upsert:false});
  if(error){vesselNotice(`Файл не загрузился: ${error.message}`,'error');return null;}
  return {name:file.name,path:objectPath,type:file.type||'application/octet-stream',size:file.size};
}
async function cleanupFailedAttachment(attachment){
  if(!supabase||!attachment?.path)return;
  try{await supabase.storage.from('vessel-files').remove([attachment.path]);}catch(error){console.warn('Attachment cleanup failed',error);}
}
async function editOwnMessage(user,messageId){
  if(!supabase||!user?.id||!messageId)return;
  const sessionUserId=user.id;
  const peerId=activeDmId||null;
  const channelId=!peerId&&activeChannelKind==='text'?activeChannelId:null;
  const source=peerId?dmMessages:messages;
  const message=source.find(item=>item.id===messageId);
  if(!message||message.authorId!==sessionUserId)return;
  if(peerId&&(await verifyDirectMessageAccess(user,peerId))!==true)return;
  if(channelId&&(await verifyChannelAccess(user,channelId))!==true)return;
  if(savedUser?.id!==sessionUserId||activeDmId!==peerId||(!peerId&&activeChannelId!==channelId))return;
  const value=await vesselPrompt('Редактировать сообщение',message.text||'','Текст сообщения');
  const body=String(value||'').trim();
  if(!body||body===message.text)return;
  if(body.length>4000){vesselNotice('Сообщение не может быть длиннее 4000 символов.','error');return;}
  if(savedUser?.id!==sessionUserId||activeDmId!==peerId||(!peerId&&activeChannelId!==channelId))return;
  const editedAt=new Date().toISOString();
  let result;
  if(peerId){
    if((await verifyDirectMessageAccess(user,peerId,{notify:false}))!==true)return;
    result=await supabase.from('direct_messages').update({body,edited_at:editedAt}).eq('id',messageId).eq('sender_id',sessionUserId).is('deleted_at',null).select('id,body,edited_at').maybeSingle();
  }else{
    if(!channelId||(await verifyChannelAccess(user,channelId,{notify:false}))!==true)return;
    result=await supabase.from('messages').update({body,edited_at:editedAt}).eq('id',messageId).eq('author_id',sessionUserId).eq('channel_id',channelId).select('id,body,edited_at').maybeSingle();
  }
  if(savedUser?.id!==sessionUserId)return;
  if(result.error||!result.data){vesselNotice('Не удалось отредактировать сообщение.','error');return;}
  const liveSource=peerId?dmMessages:messages;
  const live=liveSource.find(item=>item.id===messageId);
  if(live){live.text=result.data.body;live.editedAt=result.data.edited_at||editedAt;}
  render();
}
async function deleteOwnMessage(user,messageId){
  if(!supabase||!user?.id||!messageId)return;
  const sessionUserId=user.id;
  const peerId=activeDmId||null;
  const channelId=!peerId&&activeChannelKind==='text'?activeChannelId:null;
  const source=peerId?dmMessages:messages;
  const message=source.find(item=>item.id===messageId);
  if(!message||message.authorId!==sessionUserId)return;
  if(peerId&&(await verifyDirectMessageAccess(user,peerId))!==true)return;
  if(channelId&&(await verifyChannelAccess(user,channelId))!==true)return;
  if(!await vesselConfirm('Удалить сообщение?','Это действие нельзя отменить.'))return;
  if(savedUser?.id!==sessionUserId||activeDmId!==peerId||(!peerId&&activeChannelId!==channelId))return;
  let result;
  if(peerId){
    result=await supabase.from('direct_messages').delete().eq('id',messageId).eq('sender_id',sessionUserId).select('id');
  }else{
    if(!channelId)return;
    result=await supabase.from('messages').delete().eq('id',messageId).eq('author_id',sessionUserId).eq('channel_id',channelId).select('id');
  }
  if(savedUser?.id!==sessionUserId)return;
  if(result.error||!result.data?.some(row=>row.id===messageId)){vesselNotice('Не удалось удалить сообщение.','error');return;}
  if(peerId&&activeDmId===peerId)dmMessages=dmMessages.filter(item=>item.id!==messageId);
  if(!peerId&&activeChannelId===channelId)messages=messages.filter(item=>item.id!==messageId);
  Promise.allSettled((message.attachments||[]).map(cleanupFailedAttachment)).catch(()=>{});
  if(peerId){window.__vesselDmThreadsLoaded=false;syncDmThreads(user).catch(error=>console.warn('DM thread refresh after delete failed',error));}
  render();
}

const RTC_FALLBACK_ICE_SERVERS = [
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
}

async function ensureVoicePeer(user,peerId,initiator=false){
  if(!user?.id||!peerId||peerId===user.id)return null;
  let state=voicePeers.get(peerId);
  if(state)return state;
  const rtcConfiguration=await resolveRtcConfiguration(user);
  if(savedUser?.id!==user.id||!voiceRoom||!voiceStream)return null;
  const pc=new RTCPeerConnection(rtcConfiguration);
  state={pc,pending:[],audio:null,initiator:!!initiator,iceRestartAttempts:0,iceRestartInFlight:false,disconnectTimer:null};
  voicePeers.set(peerId,state);
  voiceStream?.getAudioTracks().forEach(track=>pc.addTrack(track,voiceStream));
  pc.onicecandidate=event=>{if(event.candidate)sendVoiceSignal(user,peerId,{type:'ice',candidate:event.candidate}).catch(()=>{});};
  pc.ontrack=event=>{
    let audio=state.audio;
    if(!audio){audio=document.createElement('audio');audio.autoplay=true;audio.playsInline=true;audio.dataset.voicePeer=peerId;audio.style.display='none';document.body.appendChild(audio);state.audio=audio;}
    audio.muted=voiceDeafened;
    audio.srcObject=event.streams[0];audio.play().catch(()=>{});
  };
  pc.onconnectionstatechange=()=>{
    if(pc.connectionState==='connected'){clearVoicePeerDisconnectTimer(state);state.iceRestartAttempts=0;state.iceRestartInFlight=false;}
    if(pc.connectionState==='connected'){cancelVoicePeerReconnect(peerId);return;}
    if(pc.connectionState==='closed'){
      if(voicePeers.get(peerId)===state){removeVoicePeer(peerId);scheduleVoicePeerReconnect(user,peerId);}
      return;
    }
    if(['failed','disconnected'].includes(pc.connectionState))scheduleVoicePeerRecovery(user,peerId,state);
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
  const uniqueParticipants=new Map();
  for(const item of entries)if(item?.user_id&&!uniqueParticipants.has(item.user_id))uniqueParticipants.set(item.user_id,{id:item.user_id,name:item.name||'Участник'});
  voiceParticipants=[...uniqueParticipants.values()];
  const ids=new Set(voiceParticipants.map(item=>item.id).filter(id=>id!==user.id));
  for(const peerId of ids){
    if(!voicePeers.has(peerId)&&!voicePeerReconnectTimers.has(peerId)){
      try{await ensureVoicePeer(user,peerId,String(user.id)<String(peerId));}
      catch(error){console.warn('Voice peer connect failed',error);scheduleVoicePeerReconnect(user,peerId);}
    }
  }
  for(const peerId of [...voicePeers.keys()])if(!ids.has(peerId)){removeVoicePeer(peerId);cancelVoicePeerReconnect(peerId);}
  for(const peerId of [...voicePeerReconnectTimers.keys()])if(!ids.has(peerId))cancelVoicePeerReconnect(peerId);
  const status=document.querySelector('.voice-status');
  if(status)status.textContent=`🎙 В голосовой комнате: ${Math.max(1,voiceParticipants.length)}`;
}

function cancelVoiceReconnect(){
  if(voiceReconnectTimer){clearTimeout(voiceReconnectTimer);voiceReconnectTimer=null;}
  voiceReconnectAttempt=0;
  voiceReconnectContext=null;
}

function scheduleVoiceReconnect(user,channelId,serverId){
  if(!user?.id||!channelId||!serverId)return;
  if(voiceReconnectContext&&(voiceReconnectContext.channelId!==channelId||voiceReconnectContext.serverId!==serverId))cancelVoiceReconnect();
  if(voiceReconnectTimer)return;
  voiceReconnectContext={channelId,serverId};
  voiceReconnectAttempt=Math.min(voiceReconnectAttempt+1,4);
  const attempt=voiceReconnectAttempt;
  const delay=Math.min(1000*(2**(attempt-1)),8000);
  voiceReconnectTimer=setTimeout(async()=>{
    voiceReconnectTimer=null;
    if(!voiceReconnectContext||voiceReconnectContext.channelId!==channelId||voiceReconnectContext.serverId!==serverId)return;
    if(activeChannelId!==channelId||activeChannelKind!=='voice'||getActiveServer()?.dbId!==serverId){cancelVoiceReconnect();return;}
    if(callConnection||callStream||incomingCall){cancelVoiceReconnect();return;}
    await toggleVoiceRoom(user,true);
    if(voiceStream&&voiceRoom&&voiceChannelId===channelId){
      cancelVoiceReconnect();
      vesselNotice('Голосовая связь восстановлена.','success');
      return;
    }
    if(attempt<4){scheduleVoiceReconnect(user,channelId,serverId);return;}
    cancelVoiceReconnect();
    vesselNotice('Голосовая связь потеряна. Нажми «Войти», чтобы попробовать снова.','error');
  },delay);
}

async function leaveVoiceRoom(){
  cancelVoiceReconnect();
  const room=voiceRoom;
  voiceRoom=null;
  voiceStream?.getTracks().forEach(track=>track.stop());voiceStream=null;
  for(const peerId of [...voicePeers.keys()])removeVoicePeer(peerId);
  cancelAllVoicePeerReconnects();
  voiceParticipants=[];voiceChannelId=null;voiceServerId=null;voiceDeafened=false;
  if(room&&supabase){try{await supabase.removeChannel(room);}catch{}}
  render();
}

async function toggleVoiceRoom(user,reconnecting=false){
  if(!reconnecting)cancelVoiceReconnect();
  if(voiceStream){
    if(voiceChannelId===activeChannelId){await leaveVoiceRoom();return;}
    await leaveVoiceRoom();
  }
  if(!supabase||!user?.id||!activeChannelId||activeChannelKind!=='voice'){vesselNotice('Сначала открой голосовой канал.','error');return;}
  if(callConnection||callStream||incomingCall){vesselNotice('Заверши личный звонок или отклони входящий вызов перед входом в голосовой канал.','error');return;}
  let room=null;
  try{
    const targetChannelId=activeChannelId;
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
    room=supabase.channel(`voice-${targetChannelId}`,{config:{private:true,presence:{key:user.id}}});
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
          if(!settled){
            for(const peerId of [...voicePeers.keys()])removeVoicePeer(peerId);
            voiceParticipants=[];
            render();
            settled=true;clearTimeout(timer);reject(new Error(`VOICE_REALTIME_${status}`));
            return;
          }
          const failedChannelId=voiceChannelId;
          const failedServerId=voiceServerId;
          voiceRoom=null;
          voiceStream?.getTracks().forEach(track=>track.stop());voiceStream=null;
          for(const peerId of [...voicePeers.keys()])removeVoicePeer(peerId);
          voiceParticipants=[];voiceChannelId=null;voiceServerId=null;
          if(supabase)void supabase.removeChannel(room).catch(error=>console.warn('Voice channel cleanup failed',error));
          render();
          scheduleVoiceReconnect(user,failedChannelId,failedServerId);
        }
      });
    });
    render();
  }catch(error){
    console.warn('Voice join failed',error);
    voiceStream?.getTracks().forEach(track=>track.stop());voiceStream=null;
    for(const peerId of [...voicePeers.keys()])removeVoicePeer(peerId);
    voiceParticipants=[];voiceChannelId=null;voiceServerId=null;
    if(room&&supabase){try{await supabase.removeChannel(room);}catch{}}
    if(voiceRoom===room)voiceRoom=null;
    if(!reconnecting)vesselNotice(error?.message?.startsWith('VOICE_REALTIME_')?'Не удалось подключиться к голосовой комнате. Попробуй ещё раз.':'Разреши Vessel доступ к микрофону.','error');
    render();
  }
}

function toggleVoiceMicrophone(){
  const track=voiceStream?.getAudioTracks()[0];if(!track)return;track.enabled=!track.enabled;render();
}
function toggleVoiceDeafen(){
  if(!voiceStream)return;
  voiceDeafened=!voiceDeafened;
  for(const state of voicePeers.values())if(state.audio)state.audio.muted=voiceDeafened;
  render();
}

function callRoomName(a,b) { return `vessel-call-${[a,b].sort().join('-')}`; }
function callInboxName(userId) { return `vessel-call-inbox-${userId}`; }
function serialiseDescription(description) { return description ? {type: description.type, sdp: description.sdp} : null; }
function subscribeChannel(channel,onDisconnect=null) {
  if (channel.__subscribed) return Promise.resolve(channel);
  if (channel.__subscribePromise) return channel.__subscribePromise;
  channel.__subscribePromise = new Promise((resolve, reject) => {
    let settled = false;
    let everSubscribed = false;
    let disconnectNotified = false;
    const timer = setTimeout(() => {
      if (!settled) { settled = true; channel.__subscribed = false; reject(new Error('Realtime channel timeout')); }
    }, 10000);
    channel.subscribe(status => {
      if (status === 'SUBSCRIBED') {
        channel.__subscribed = true;
        everSubscribed = true;
        disconnectNotified = false;
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
          return;
        }
        if (everSubscribed && !disconnectNotified && typeof onDisconnect === 'function') {
          disconnectNotified = true;
          Promise.resolve().then(() => onDisconnect(status)).catch(error => console.warn('Realtime disconnect handler failed', error));
        }
      }
    });
  }).finally(() => { channel.__subscribePromise = null; });
  return channel.__subscribePromise;
}
async function sendCallInvite(user, peerId, payload) {
  if (!supabase || !user?.id || !peerId) return false;
  const channel = supabase.channel(callInboxName(peerId),{config:{private:true}});
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
async function resolveCallableFriend(user, peerId) {
  if(!supabase||!user?.id||!peerId||peerId===user.id)return null;
  const {data:link,error:linkError}=await supabase.from('friendships').select('friend_id').eq('user_id',user.id).eq('friend_id',peerId).maybeSingle();
  if(linkError||!link)return null;
  const {data:profile,error:profileError}=await supabase.from('profiles').select('id,username,avatar_color,status').eq('id',peerId).maybeSingle();
  if(profileError)return null;
  return profile||{id:peerId,username:'Пользователь'};
}
async function ensureCallInbox(user) {
  if (!supabase || !user?.id) return null;
  const name = callInboxName(user.id);
  if (callInboxChannel?.__roomName === name && callInboxChannel.__subscribed) return callInboxChannel;
  const previousInbox=callInboxChannel;
  callInboxChannel=null;
  if (previousInbox) await supabase.removeChannel(previousInbox).catch(()=>{});
  const inbox=supabase.channel(name,{config:{private:true}});
  callInboxChannel=inbox;
  inbox.__roomName = name;
  inbox.on('broadcast', {event:'call'}, async ({payload}) => {
    if (!payload || payload.to !== user.id) return;
    if (payload.type === 'invite') {
      const caller=await resolveCallableFriend(user,payload.from);
      if(callInboxChannel!==inbox||savedUser?.id!==user.id)return;
      if(!caller){console.warn('Ignored call invite from non-friend');return;}
      if (callConnection || callStream || incomingCall) {
        await sendCallInvite(user, payload.from, {type:'busy'});
        return;
      }
      incomingCall = {from:payload.from, name:caller.username || 'Пользователь', video:!!payload.video, offer:payload.offer};
      clearIncomingCallTimer();
      const incomingFrom=payload.from;
      incomingCallTimer=setTimeout(()=>{
        incomingCallTimer=null;
        if(savedUser?.id!==user.id||incomingCall?.from!==incomingFrom)return;
        incomingCall=null;
        render();
      },32000);
      render();
      return;
    }
    if (payload.type === 'bye') {
      if (incomingCall?.from === payload.from) {
        clearIncomingCallTimer();
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
    await subscribeChannel(inbox,status=>{
      if(callInboxChannel!==inbox||savedUser?.id!==user.id)return;
      console.warn(`Call inbox ${status}; reconnecting`);
      callInboxChannel=null;
      if(supabase)void supabase.removeChannel(inbox).catch(error=>console.warn('Call inbox cleanup failed',error));
      if(savedUser?.id===user.id&&!callInboxChannel)scheduleCallInboxReconnect(savedUser);
    });
  } catch (error) {
    console.warn('Call inbox failed', error);
    if(callInboxChannel===inbox)callInboxChannel=null;
    if(supabase){try{await supabase.removeChannel(inbox);}catch{}}
    if(savedUser?.id===user.id&&!callInboxChannel)scheduleCallInboxReconnect(user);
    return null;
  }
  if(callInboxChannel===inbox)cancelCallInboxReconnect();
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
async function ensureCallChannel(user, peerId) {
  if (!supabase || !user?.id || !peerId) return null;
  const name=callRoomName(user.id,peerId);
  if(callChannel?.__roomName===name && callChannel.__subscribed) return callChannel;
  const previousCallChannel=callChannel;
  callChannel=null;
  if(previousCallChannel)await supabase.removeChannel(previousCallChannel).catch(()=>{});
  const room=supabase.channel(name,{config:{private:true}});
  callChannel=room;
  room.__roomName=name;
  room.on('broadcast',{event:'signal'},async({payload})=>{
    if(!payload || payload.to!==user.id || payload.from!==callPeer) return;
    await handleCallSignal(user,payload.from,payload.signal,payload.video).catch(error=>{console.warn('Call signal failed',error);endCall(false);});
  });
  try{
    await subscribeChannel(room,status=>{
      if(callChannel!==room||savedUser?.id!==user.id||callPeer!==peerId)return;
      console.warn(`Call signaling ${status}; reconnecting`);
      callChannel=null;
      if(supabase)void supabase.removeChannel(room).catch(error=>console.warn('Call signaling cleanup failed',error));
      if(savedUser?.id===user.id&&callPeer===peerId&&callConnection&&!callChannel)scheduleCallSignalReconnect(savedUser,peerId);
    });
  }catch(error){
    if(callChannel===room)callChannel=null;
    if(supabase)await supabase.removeChannel(room).catch(()=>{});
    throw error;
  }
  if(callChannel===room)cancelCallSignalReconnect();
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
function clearIncomingCallTimer(){
  if(incomingCallTimer){clearTimeout(incomingCallTimer);incomingCallTimer=null;}
}
function clearCallDisconnectTimer(){
  if(callDisconnectTimer){clearTimeout(callDisconnectTimer);callDisconnectTimer=null;}
}
async function attemptCallIceRestart(connection,user,peerId,video){
  if(connection!==callConnection||!callAccepted||!callInitiator||callIceRestartInFlight)return false;
  if(!['failed','disconnected'].includes(connection.connectionState))return true;
  if(callIceRestartAttempts>=2)return false;
  callIceRestartAttempts+=1;
  callIceRestartInFlight=true;
  try{
    const rtcConfiguration=await resolveRtcConfiguration(user,{force:true});
    if(connection!==callConnection||!callAccepted||!callInitiator)return false;
    connection.setConfiguration?.(rtcConfiguration);
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
}
async function prepareCallConnection(user,peerId,video) {
  if (callConnection) return callConnection;
  const sessionUserId=user?.id||null;
  if(!sessionUserId||savedUser?.id!==sessionUserId||callPeer!==peerId)return null;
  const rtcConfiguration=await resolveRtcConfiguration(user);
  if(savedUser?.id!==sessionUserId||callPeer!==peerId)return null;
  if(callConnection)return callConnection;
  callConnection=new RTCPeerConnection(rtcConfiguration);
  callConnection.onicecandidate=e=>{
    if (!e.candidate) return;
    if (callAccepted) sendCallSignal(user,peerId,{type:'ice',candidate:e.candidate},video).catch(error=>console.warn('Call ICE send failed',error));
    else localIceCandidates.push(e.candidate);
  };
  callConnection.ontrack=e=>{remoteCallStream=e.streams[0];const el=document.querySelector('#remote-video');if(el){el.srcObject=remoteCallStream;el.play().catch(()=>{});} };
  const connection = callConnection;
  callConnection.onconnectionstatechange=()=>{
    if(connection!==callConnection)return;
    const state=connection.connectionState;
    if(state==='connected'){clearCallDisconnectTimer();callIceRestartAttempts=0;callIceRestartInFlight=false;return;}
    if(state==='closed'){clearCallDisconnectTimer();return;}
    if(['failed','disconnected'].includes(state))scheduleCallDisconnectCleanup(connection,user,peerId,video);
  };
  if(callStream) callStream.getTracks().forEach(track=>callConnection.addTrack(track,callStream));
  return callConnection;
}
async function handleCallSignal(user,peerId,signal,video) {
  if(signal.type==='bye'){await endCall(false);return;}
  if(signal.type==='ice'){if(callConnection?.remoteDescription) await callConnection.addIceCandidate(signal.candidate); else pendingIceCandidates.push(signal.candidate);return;}
  if(signal.type==='offer'){
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
    callVideo=!!video; if(!await prepareCallConnection(user,peerId,!!video))return; await callConnection.setRemoteDescription(signal.description);
    for(const candidate of pendingIceCandidates) await callConnection.addIceCandidate(candidate); pendingIceCandidates=[];
    const answer=await callConnection.createAnswer(); await callConnection.setLocalDescription(answer); await sendCallSignal(user,peerId,{type:'answer',description:answer},video); render(); return;
  }
  if(signal.type==='answer'&&callConnection){await callConnection.setRemoteDescription(signal.description);for(const candidate of pendingIceCandidates)await callConnection.addIceCandidate(candidate);pendingIceCandidates=[];render();}
}
async function startCall(video,user) {
  if(!activeDmId||!supabase||!user?.id){vesselNotice('Открой личный чат с настоящим другом, чтобы начать звонок.','error');return;}
  if(incomingCall){vesselNotice('Сначала ответь на входящий вызов или отклони его.','error');return;}
  if(callConnection || callStream){await endCall(true);return;}
  const peerId=activeDmId;
  try {
    if((await verifyDirectMessageAccess(user,peerId))!==true)return;
    if(savedUser?.id!==user.id||activeDmId!==peerId)return;
    if(voiceStream)await leaveVoiceRoom();
    if(savedUser?.id!==user.id||activeDmId!==peerId)return;
    callPeer=peerId; callPeerName=currentDm||'Пользователь'; callVideo=!!video; callAccepted=false; callOffer=null; localIceCandidates=[]; callMicEnabled=true; callCameraEnabled=!!video; callInitiator=true; callIceRestartAttempts=0; callIceRestartInFlight=false;
    const mediaStream=await navigator.mediaDevices.getUserMedia({audio:true,video:!!video});
    const accessAfterMedia=await verifyDirectMessageAccess(user,peerId,{notify:false});
    if(savedUser?.id!==user.id||activeDmId!==peerId||callPeer!==peerId||incomingCall||accessAfterMedia!==true){
      mediaStream.getTracks().forEach(track=>track.stop());
      if(savedUser?.id===user.id&&callPeer===peerId)await endCall(false);
      return;
    }
    callStream=mediaStream;
    if(!await prepareCallConnection(user,peerId,!!video))throw new Error('CALL_RTC_CONFIGURATION_STALE');
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
  const invite=incomingCall;
  clearIncomingCallTimer();
  const access=await verifyDirectMessageAccess(user,invite.from);
  if(incomingCall!==invite||savedUser?.id!==user.id)return;
  if(access!==true){
    incomingCall=null;
    await sendCallInvite(user,invite.from,{type:'decline'});
    render();
    return;
  }
  incomingCall=null; callPeer=invite.from; callPeerName=invite.name; callVideo=invite.video; callAccepted=true; callMicEnabled=true; callCameraEnabled=invite.video; callInitiator=false; callIceRestartAttempts=0; callIceRestartInFlight=false;
  activeDmId=invite.from; currentDm=invite.name; friendsOpen=false; window.__vesselDmLoaded=false;
  try {
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
  const invite=incomingCall; clearIncomingCallTimer(); incomingCall=null;
  await sendCallInvite(user,invite.from,{type:'decline'});
  render();
}
async function endCall(notify=true) {
  cancelCallSignalReconnect();
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
  callInitiator=false;
  callIceRestartAttempts=0;
  callIceRestartInFlight=false;
  clearCallDisconnectTimer();
  clearIncomingCallTimer();
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
function clearDataRealtimeRecovery(){
  if(dataRealtimeReconnectTimer){clearTimeout(dataRealtimeReconnectTimer);dataRealtimeReconnectTimer=null;}
  dataRealtimeReconnectAttempt=0;
  dataRealtimeRecoveryInFlight=false;
}
function handleDataRealtimeStatus(user,status){
  if(savedUser?.id!==user?.id||dataRealtimeRecoveryInFlight)return;
  if(['CHANNEL_ERROR','TIMED_OUT','CLOSED'].includes(status))scheduleDataRealtimeRecovery(user,status);
}
function scheduleDataRealtimeRecovery(user,status='CHANNEL_ERROR'){
  if(!supabase||!user?.id||savedUser?.id!==user.id||dataRealtimeReconnectTimer||dataRealtimeRecoveryInFlight)return;
  const sessionUserId=user.id;
  dataRealtimeReconnectAttempt=Math.min(dataRealtimeReconnectAttempt+1,5);
  const attempt=dataRealtimeReconnectAttempt;
  const delay=Math.min(1000*(2**(attempt-1)),10000);
  console.warn(`Data Realtime ${status}; recovery attempt ${attempt} scheduled`);
  dataRealtimeReconnectTimer=setTimeout(async()=>{
    dataRealtimeReconnectTimer=null;
    if(savedUser?.id!==sessionUserId)return;
    dataRealtimeRecoveryInFlight=true;
    const stale=window.__vesselRealtimeChannels||[];
    window.__vesselRealtimeChannels=null;
    try{
      if(stale.length)await Promise.allSettled(stale.map(channel=>supabase.removeChannel(channel)));
    }finally{
      dataRealtimeRecoveryInFlight=false;
    }
    if(savedUser?.id!==sessionUserId)return;
    window.__vesselSocialLoaded=false;
    window.__vesselDmThreadsLoaded=false;
    window.__vesselNotificationsLoaded=false;
    if(activeDmId)window.__vesselDmLoaded=false;
    connectSupabaseRealtime(user);
    const refreshes=[syncSocial(user),syncDmThreads(user),syncNotifications(user)];
    if(activeDmId)refreshes.push(loadDirectMessages(user,activeDmId));
    await Promise.allSettled(refreshes);
    if(savedUser?.id===sessionUserId)dataRealtimeReconnectAttempt=0;
  },delay);
}
function connectSupabaseRealtime(user) {
  if (!supabase || !user?.id || window.__vesselRealtimeChannels) return;
  window.__vesselRealtimeChannels = [
    supabase.channel(`vessel-dm-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'direct_messages'},payload=>{
      if(savedUser?.id!==user.id)return;
      if(payload.eventType==='DELETE'){
        const deletedId=payload.old?.id;
        if(deletedId&&dmMessages.some(item=>item.id===deletedId)){
          dmMessages=dmMessages.filter(item=>item.id!==deletedId);
          window.__vesselDmThreadsLoaded=false;
          syncDmThreads(user).catch(error=>console.warn('DM thread delete refresh failed',error));
          render();
        }
        return;
      }
      const row=payload.new;
      if(!row?.id||![row.sender_id,row.receiver_id].includes(user.id))return;
      window.__vesselDmThreadsLoaded=false;
      syncDmThreads(user).catch(error=>console.warn('DM thread realtime refresh failed',error));
      if(activeDmId && (row.sender_id===activeDmId || row.receiver_id===activeDmId)){ window.__vesselDmLoaded=false; loadDirectMessages(user,activeDmId); }
    }).subscribe(status=>handleDataRealtimeStatus(user,status)),
    supabase.channel(`vessel-friends-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'friend_requests',filter:`receiver_id=eq.${user.id}`},()=>{if(savedUser?.id!==user.id)return;window.__vesselSocialLoaded=false;syncSocial(user);}).subscribe(status=>handleDataRealtimeStatus(user,status)),
    supabase.channel(`vessel-friend-requests-out-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'friend_requests',filter:`sender_id=eq.${user.id}`},()=>{if(savedUser?.id!==user.id)return;window.__vesselSocialLoaded=false;syncSocial(user);}).subscribe(status=>handleDataRealtimeStatus(user,status)),
    supabase.channel(`vessel-friendships-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'friendships',filter:`user_id=eq.${user.id}`},async payload=>{
      if(savedUser?.id!==user.id)return;
      const row=payload.new?.friend_id?payload.new:payload.old;
      if(payload.eventType==='DELETE'&&row?.friend_id){
        if(incomingCall?.from===row.friend_id){clearIncomingCallTimer();incomingCall=null;render();}
        if(callPeer===row.friend_id)await endCall(false);
      }
      window.__vesselSocialLoaded=false;
      syncSocial(user);
    }).subscribe(status=>handleDataRealtimeStatus(user,status)),
    supabase.channel(`vessel-memberships-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'server_members'},async payload=>{
      if(savedUser?.id!==user.id)return;
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
    }).subscribe(status=>handleDataRealtimeStatus(user,status)),
    supabase.channel(`vessel-channels-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'channels'},async payload=>{
      if(savedUser?.id!==user.id)return;
      const row=payload.new?.server_id?payload.new:payload.old;
      if(payload.eventType==='DELETE'&&voiceStream&&row?.id===voiceChannelId)await leaveVoiceRoom();
      const active=getActiveServer();
      if(row?.server_id&&active?.dbId===row.server_id){active.__channelsLoaded=false;syncSupabaseChannels(active);}
    }).subscribe(status=>handleDataRealtimeStatus(user,status)),
    supabase.channel(`vessel-channel-messages-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'messages'},payload=>{
      if(savedUser?.id!==user.id)return;
      if(payload.eventType==='DELETE'){
        const deletedId=payload.old?.id;
        if(deletedId&&messages.some(item=>item.id===deletedId)){messages=messages.filter(item=>item.id!==deletedId);render();}
        return;
      }
      const row=payload.new;
      if(row?.channel_id===activeChannelId)loadChannelMessages(activeChannelId).catch(error=>console.warn('Message refresh failed',error));
    }).subscribe(status=>handleDataRealtimeStatus(user,status)),
    supabase.channel(`vessel-profiles-${user.id}`).on('postgres_changes',{event:'UPDATE',schema:'public',table:'profiles'},payload=>{
      if(savedUser?.id!==user.id)return;
      const row=payload.new;
      if(!row?.id)return;
      let dirty=false;
      if(savedUser?.id===row.id){savedUser={...savedUser,name:row.username||savedUser.name,status:row.status||savedUser.status,avatarColor:row.avatar_color||savedUser.avatarColor};localStorage.setItem('vesselUser',JSON.stringify(savedUser));dirty=true;}
      const friend=friends.find(item=>item.id===row.id);if(friend){friend.username=row.username||friend.username;friend.status=row.status||friend.status;friend.avatar_color=row.avatar_color||friend.avatar_color;dirty=true;}
      const thread=dmThreads.find(item=>item.id===row.id);if(thread){thread.username=row.username||thread.username;thread.status=row.status||thread.status;thread.avatar_color=row.avatar_color||thread.avatar_color;dirty=true;}
      const member=serverMembers.find(item=>item.id===row.id);if(member){member.username=row.username||member.username;member.status=row.status||member.status;member.avatar_color=row.avatar_color||member.avatar_color;dirty=true;}
      if(activeDmId===row.id&&row.username){currentDm=row.username;dirty=true;}
      if(dirty)render();
    }).subscribe(status=>handleDataRealtimeStatus(user,status)),
    supabase.channel(`vessel-servers-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'servers'},async payload=>{
      if(savedUser?.id!==user.id)return;
      const row=payload.new?.id?payload.new:payload.old;
      if(!row?.id)return;
      if(payload.eventType==='DELETE'){
        if(voiceStream&&voiceServerId===row.id)await leaveVoiceRoom();
        if(savedUser?.id!==user.id)return;
        window.__vesselServersLoaded=false;
        serversSyncRevision++;
        await syncSupabaseServers(user);
        return;
      }
      const server=servers.find(item=>item.id===row.id);
      if(!server)return;
      server.name=row.name||server.name;
      server.icon=row.icon||server.icon;
      render();
    }).subscribe(status=>handleDataRealtimeStatus(user,status)),
    supabase.channel(`vessel-notifications-${user.id}`)
      .on('postgres_changes',{event:'INSERT',schema:'public',table:'notifications',filter:`user_id=eq.${user.id}`},async payload=>{
        if(savedUser?.id!==user.id)return;
        const row=payload.new;
        notificationsSyncRevision++;
        window.__vesselNotificationsLoaded=true;
        notifications=[row,...notifications.filter(item=>item.id!==row.id)];
        if(row?.type==='direct_message'&&row.data?.sender_id===activeDmId&&!friendsOpen){
          await markDirectMessageNotificationsRead(user,activeDmId,row.id);
          return;
        }
        render();
      })
      .on('postgres_changes',{event:'UPDATE',schema:'public',table:'notifications',filter:`user_id=eq.${user.id}`},payload=>{
        if(savedUser?.id!==user.id)return;
        const row=payload.new;
        if(!row?.id)return;
        notificationsSyncRevision++;
        window.__vesselNotificationsLoaded=true;
        notifications=notifications.map(item=>item.id===row.id?{...item,...row}:item);
        render();
      })
      .subscribe(status=>handleDataRealtimeStatus(user,status))
  ];
}

let savedUser = null;
let authStateSyncTimer = null;

function resetAuthenticatedRuntime() {
  clearDataRealtimeRecovery();
  cancelVoiceReconnect();
  cancelAllVoicePeerReconnects();
  cancelCallInboxReconnect();
  cancelCallSignalReconnect();
  resetRtcConfiguration();
  dmMessagesSyncRevision++;
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
  voiceDeafened=false;
  clearIncomingCallTimer();
  incomingCall=null;
  callPeer=null;
  callPeerName='';
  callOffer=null;
  callVideo=false;
  callAccepted=false;
  callInitiator=false;
  callIceRestartAttempts=0;
  callIceRestartInFlight=false;
  clearCallDisconnectTimer();
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
  serversSyncRevision++;
  window.__vesselSocialLoaded=false;
  socialSyncRevision++;
  window.__vesselDmThreadsLoaded=false;
  dmThreadsSyncRevision++;
  window.__vesselDmLoaded=false;
  window.__vesselNotificationsLoaded=false;
  notificationsSyncRevision++;
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
  const {data: profile, error: profileError} = await supabase.from('profiles').select('id,username,status,avatar_color').eq('id', authUser.id).maybeSingle();
  if (profileError) console.warn('Profile load failed', profileError);

  savedUser = {
    id: authUser.id,
    name: profile?.username || authUser.user_metadata?.username || authUser.email?.split('@')[0] || 'Пользователь',
    email: authUser.email || '',
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

async function manageServerInvites(user,server){
  if(!supabase||!user?.id||!server?.dbId||server.role!=='owner'){vesselNotice('Управлять приглашениями может только владелец сервера.','error');return;}
  const userId=user.id;
  const serverId=server.dbId;
  const {data,error}=await supabase.from('server_invites').select('id,code,created_at,expires_at,max_uses,uses').eq('server_id',serverId).eq('created_by',userId).order('created_at',{ascending:false}).limit(100);
  if(savedUser?.id!==userId||getActiveServer()?.dbId!==serverId)return;
  if(error){vesselNotice('Не удалось загрузить приглашения сервера.','error');return;}
  const invites=data||[];
  const items=invites.map(invite=>{
    const expired=invite.expires_at&&new Date(invite.expires_at).getTime()<=Date.now();
    const exhausted=Number(invite.max_uses)>0&&Number(invite.uses)>=Number(invite.max_uses);
    const status=expired?'Истекло':exhausted?'Использовано':'Активно';
    const uses=Number(invite.max_uses)>0?`${Number(invite.uses)||0}/${Number(invite.max_uses)}`:`${Number(invite.uses)||0}/∞`;
    const expires=invite.expires_at?new Date(invite.expires_at).toLocaleString('ru-RU'):'без срока';
    return {title:invite.code,meta:status,body:`Использований: ${uses} · Срок: ${expires}`,value:invite.id,invite};
  });
  vesselListDialog(`Приглашения · ${server.name}`,items,'Активных или старых приглашений пока нет.',async item=>{
    const invite=item?.invite;
    if(!invite||savedUser?.id!==userId)return;
    const action=await vesselChoice(`Приглашение ${invite.code}`,[{label:'Показать и скопировать код',value:'copy'},{label:'Отозвать приглашение',value:'revoke',danger:true}]);
    if(action==='copy'){vesselCodeDialog(`Приглашение в ${server.name}`,invite.code);return;}
    if(action!=='revoke')return;
    if(!await vesselConfirm(`Отозвать приглашение ${invite.code}?`,'После этого по этому коду больше нельзя будет вступить в сервер.'))return;
    if(savedUser?.id!==userId)return;
    const {data:deleted,error:deleteError}=await supabase.from('server_invites').delete().eq('id',invite.id).eq('server_id',serverId).eq('created_by',userId).select('id');
    if(savedUser?.id!==userId)return;
    if(deleteError||!deleted?.some(row=>row.id===invite.id)){vesselNotice('Не удалось отозвать приглашение.','error');return;}
    vesselNotice('Приглашение отозвано.','success');
  });
}

async function refreshReadOnlyDirectMessage(user,peerId){
  const refreshUserId=user?.id||null;
  if(!refreshUserId||savedUser?.id!==refreshUserId)return;
  window.__vesselSocialLoaded=false;
  window.__vesselDmThreadsLoaded=false;
  await Promise.all([syncSocial(user),syncDmThreads(user)]);
  if(savedUser?.id!==refreshUserId)return;
  if(activeDmId===peerId){
    window.__vesselDmLoaded=false;
    await loadDirectMessages(user,peerId);
  }else render();
}
async function verifyDirectMessageAccess(user,peerId,{notify=true}={}){
  if(!supabase||!user?.id||!peerId)return false;
  const accessUserId=user.id;
  if(savedUser?.id!==accessUserId)return null;
  const {data,error}=await supabase.from('friendships').select('friend_id').eq('user_id',accessUserId).eq('friend_id',peerId).maybeSingle();
  if(savedUser?.id!==accessUserId)return null;
  if(error){
    console.warn('DM friendship verification failed',error);
    if(notify)vesselNotice('Не удалось проверить доступ к переписке. Попробуй ещё раз.','error');
    return null;
  }
  if(data)return true;
  await refreshReadOnlyDirectMessage(user,peerId);
  if(savedUser?.id!==accessUserId)return null;
  if(notify)vesselNotice('Пользователь больше не в друзьях. История оставлена только для чтения.','error');
  return false;
}
async function refreshAfterChannelAccessLoss(user,channelId){
  const refreshUserId=user?.id||null;
  if(!refreshUserId||savedUser?.id!==refreshUserId)return;
  const lostServerId=getActiveServer()?.dbId||null;
  if(voiceStream&&lostServerId&&voiceServerId===lostServerId)await leaveVoiceRoom();
  activeChannelId=null;
  activeChannelName='нет каналов';
  activeChannelKind='text';
  dbChannels=[];
  messages=[];
  serverMembers=[];
  window.__vesselMembersServerId=null;
  window.__vesselServersLoaded=false;
  await syncSupabaseServers(user);
  if(savedUser?.id!==refreshUserId)return;
  const next=getActiveServer();
  if(next?.dbId){
    next.__channelsLoaded=false;
    await syncSupabaseChannels(next);
    await syncServerMembers(user,next);
  }else render();
}
async function verifyChannelAccess(user,channelId,{notify=true}={}){
  if(!supabase||!user?.id||!channelId)return false;
  const accessUserId=user.id;
  if(savedUser?.id!==accessUserId)return null;
  const {data,error}=await supabase.from('channels').select('id').eq('id',channelId).maybeSingle();
  if(savedUser?.id!==accessUserId)return null;
  if(error){
    console.warn('Channel access verification failed',error);
    if(notify)vesselNotice('Не удалось проверить доступ к каналу. Попробуй ещё раз.','error');
    return null;
  }
  if(data)return true;
  await refreshAfterChannelAccessLoss(user,channelId);
  if(savedUser?.id!==accessUserId)return null;
  if(notify)vesselNotice('Доступ к каналу потерян. Список серверов обновлён.','error');
  return false;
}
function render() {
  const previousMessagesPane=document.querySelector('.messages');
  const previousMessageContext=lastRenderedMessageContext;
  const previousMessageScroll=previousMessagesPane?{
    top:previousMessagesPane.scrollTop,
    atBottom:(previousMessagesPane.scrollHeight-previousMessagesPane.scrollTop-previousMessagesPane.clientHeight)<80
  }:null;
  if (!savedUser) {
    lastRenderedMessageContext=null;
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
  const currentMessageContext=friendsOpen
    ? `user:${user.id}:friends`
    : activeDmId
      ? `user:${user.id}:dm:${activeDmId}`
      : `user:${user.id}:channel:${activeChannelId||'none'}:${activeChannelKind}`;
  connectSupabaseRealtime(user); ensureCallInbox(user).catch(()=>{}); syncSupabaseMessages(); syncSupabaseServers(user); const selectedServer=getActiveServer(); if(selectedServer){syncSupabaseChannels(selectedServer);syncServerMembers(user,selectedServer);} syncSocial(user); syncDmThreads(user); syncNotifications(user); if (activeDmId && callConnection) { ensureCallChannel(user,activeDmId).catch(()=>{}); } if (activeDmId && !window.__vesselDmLoaded) { window.__vesselDmLoaded=true; loadDirectMessages(user,activeDmId); }
  const callInProgress=Boolean(callConnection||callStream);
  const activeDmIsFriend=Boolean(activeDmId&&friends.some(friend=>friend.id===activeDmId));
  const activeServer=getActiveServer();
  const canManageChannel=Boolean(!friendsOpen&&!currentDm&&activeChannelId&&activeServer?.dbId&&['owner','moderator'].includes(activeServer.role));
  const callActions=callInProgress
    ? `<button id="toggle-call-mic" class="call-control" title="${callMicEnabled?'Выключить микрофон':'Включить микрофон'}">${callMicEnabled?'🎙':'🔇'}</button>${callVideo?`<button id="toggle-call-camera" class="call-control" title="${callCameraEnabled?'Выключить камеру':'Включить камеру'}">${callCameraEnabled?'📷':'🚫'}</button>`:''}<button id="end-call" class="hangup" title="Завершить звонок">☎</button>`
    : (!friendsOpen&&activeDmId&&activeDmIsFriend) ? `<button id="audio-call" title="Аудиозвонок">📞</button><button id="video-call" title="Видеозвонок">🎥</button>` : '';
  const dmList=dmThreads.length
    ? dmThreads.map(thread=>{const unread=unreadDirectMessageCount(thread.id);return `<button class="channel dm ${activeDmId===thread.id?'active':''}" data-dm-id="${thread.id}" data-dm="${escapeHtml(thread.username)}"><div class="mini-avatar" style="background:${thread.avatar_color||'#8b7cff'}">${(thread.username||'?')[0].toUpperCase()}</div> ${escapeHtml(thread.username)} ${unread?`<em class="dm-unread" title="Непрочитанных: ${unread}">${unread>99?'99+':unread}</em>`:''}</button>`;}).join('')
    : `<div class="dm-empty">Пока нет личных чатов</div>`;
  const membersList=serverMembers.length
    ? `<div class="members-title">УЧАСТНИКИ — ${serverMembers.length}</div>${serverMembers.map(member=>`<div class="member online"><div class="avatar" style="background:${escapeHtml(member.avatar_color||'#8b7cff')}">${escapeHtml(member.username[0]?.toUpperCase()||'?')}</div><span>${escapeHtml(member.username)}<small>${member.role==='owner'?'Создатель':member.role==='moderator'?'Модератор':escapeHtml(statusLabel(member.status))}</small></span>${activeServer?.role==='owner'&&member.role!=='owner'?`<button class="member-manage" data-manage-member="${member.id}" title="Управление участником">•••</button>`:'<i></i>'}</div>`).join('')}`
    : `<div class="members-title">УЧАСТНИКИ</div><div class="dm-empty">${!activeServer?.dbId?'Выбери или создай сервер.':window.__vesselMembersServerId===activeServer.dbId?'На сервере пока нет участников.':'Список загружается…'}</div>`;
  document.querySelector('#app').innerHTML = `
    <main class="shell">
      <aside class="servers"><button class="server home-tab ${friendsOpen?'selected':''}" id="friends-tab" title="Друзья">👥</button>${servers.map((s,i) => `<button class="server ${!friendsOpen&&i===activeServerIndex?'selected':''} ${s.add ? 'add' : ''}" data-server-index="${i}" title="${escapeHtml(s.name)}">${escapeHtml(s.icon)}</button>`).join('')}</aside>
      <aside class="channels">
        <div class="brand"><span class="brand-mark">◈</span><span>${friendsOpen?'Друзья':escapeHtml(activeServer?.name || 'Vessel')}</span><button class="more ${friendsOpen?'hidden':''}">•••</button><button class="mobile-drawer-close" id="mobile-nav-close" type="button" title="Закрыть каналы" aria-label="Закрыть каналы">×</button></div>
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
        <header class="chat-head"><div><h1><span>${friendsOpen?'👥':currentDm?'@':activeChannelKind==='voice'?'⌁':'#'}</span> ${friendsOpen?'Друзья':escapeHtml(currentDm || activeChannelName)}</h1><p>${friendsOpen?'Личные контакты и заявки':currentDm?'Личная переписка':activeChannelKind==='voice'?'Голосовая комната':escapeHtml(activeServer?.name || 'Vessel')}</p></div><div class="head-actions"><button id="mobile-nav" title="Каналы">☰</button>${canManageChannel?`<button id="channel-settings" title="Настройки канала">•••</button>`:''}${callActions}<button id="join-voice" class="join-voice ${!friendsOpen&&activeChannelKind==='voice'?'':'hidden'}">${voiceStream?(voiceChannelId===activeChannelId?'Выйти':'Переключиться'):'Войти'}</button><button id="mute-voice" class="join-voice ${!friendsOpen&&voiceStream&&voiceChannelId===activeChannelId?'':'hidden'}" title="${voiceStream?.getAudioTracks()[0]?.enabled===false?'Включить микрофон':'Выключить микрофон'}">${voiceStream?.getAudioTracks()[0]?.enabled===false?'🔇':'🎙'}</button><button id="deafen-voice" class="join-voice ${!friendsOpen&&voiceStream&&voiceChannelId===activeChannelId?'':'hidden'}" title="${voiceDeafened?'Включить звук участников':'Отключить звук участников'}">${voiceDeafened?'🙉':'🎧'}</button><button id="search-button" class="${friendsOpen?'hidden':''}">⌕</button><button id="friends-button" title="Друзья" class="${friendsOpen?'hidden':''}">♧</button><button id="notifications" title="Уведомления">🔔${notifications.filter(n=>!n.read_at).length?` <sup>${notifications.filter(n=>!n.read_at).length}</sup>`:''}</button><button id="head-settings">⚙</button></div></header>
        <video id="remote-video" class="remote-video ${remoteCallStream?'':'hidden'}" autoplay playsinline></video><video id="local-video" class="local-video ${callStream||voiceStream?.getVideoTracks().length?'':'hidden'}" autoplay muted playsinline></video><div class="messages">${friendsOpen?`<div class="friends-view"><div class="friends-hero"><h2>Друзья</h2><button id="add-friend" class="primary">Найти пользователя</button></div>${friendRequests.map(request=>`<div class="friend-row request-row"><div class="avatar" style="background:#ffb45e">${(request.profiles?.username||'?')[0].toUpperCase()}</div><b>${escapeHtml(request.profiles?.username||'Пользователь')}</b><span>Заявка</span><button data-accept-request="${request.id}" data-sender="${request.sender_id}">Принять</button><button class="danger compact" data-decline-request="${request.id}">Отклонить</button></div>`).join('')}${outgoingFriendRequests.map(request=>`<div class="friend-row outgoing-request-row"><div class="avatar" style="background:#5a6380">${escapeHtml((request.profiles?.username||'?')[0].toUpperCase())}</div><b>${escapeHtml(request.profiles?.username||'Пользователь')}</b><span class="pending-label">Ожидает подтверждения</span><button class="danger compact" data-cancel-request="${request.id}" title="Отменить заявку">×</button></div>`).join('')}${friends.length ? friends.map(friend=>`<div class="friend-row"><div class="avatar" style="background:${friend.avatar_color||'#8b7cff'}">${friend.username[0].toUpperCase()}</div><b>${escapeHtml(friend.username)}</b><span>${escapeHtml(statusLabel(friend.status))}</span><button data-dm-id="${friend.id}" data-dm="${escapeHtml(friend.username)}">💬</button><button data-call-id="${friend.id}" data-call="${escapeHtml(friend.username)}">📞</button><button class="danger compact" data-remove-friend="${friend.id}" title="Удалить из друзей">×</button></div>`).join('') : `<p class="empty-state">Пока нет добавленных друзей. Нажми «Найти пользователя».</p>`}</div>`:`<div class="welcome"><div class="welcome-icon">${currentDm?'@':activeChannelKind==='voice'?'⌁':'#'}</div><h2>${currentDm?`Переписка с ${escapeHtml(currentDm)}`:`Добро пожаловать в ${activeChannelKind==='voice'?'':'#'}${escapeHtml(activeChannelName)}!`}</h2><p>${activeChannelKind==='voice'?'Подключись к комнате, чтобы общаться голосом.':'Здесь начинается ваше общение.'}</p></div>${(activeDmId?dmMessages:messages).map(m=>messageMarkup(m,user,!activeDmId||activeDmIsFriend)).join('')}`}</div>
        ${activeDmId&&!activeDmIsFriend?'<div class="dm-empty">История доступна только для чтения. Добавь пользователя в друзья, чтобы снова писать и звонить.</div>':''}<form class="composer ${friendsOpen||(!currentDm&&activeChannelKind==='voice')||(activeDmId&&!activeDmIsFriend)?'hidden':''}"><button type="button" class="attach">＋</button><input placeholder="${currentDm?`Написать пользователю ${escapeHtml(currentDm)}`:`Написать в #${escapeHtml(activeChannelName)}`}" /><button type="button" id="emoji-button" title="Эмодзи">☺</button><button type="submit" class="send">➤</button></form>
      </section>
      <aside class="members">${friendsOpen?`<div class="members-title">ДРУЗЬЯ — ${friends.length}</div><div class="dm-empty">${friendRequests.length?`Входящих заявок: ${friendRequests.length}`:outgoingFriendRequests.length?`Исходящих заявок: ${outgoingFriendRequests.length}`:'Выбери друга, чтобы открыть личный чат.'}</div>`:`${voiceStream?`<div class="voice-status">🎙 В голосовой комнате: ${Math.max(1,voiceParticipants.length)}</div>`:''}${membersList}`}</aside>
    </main><div class="modal hidden" id="settings-modal"><div class="modal-card"><button class="modal-close" id="close-settings">×</button><h2>Настройки профиля</h2><p>Измени данные, которые видят другие участники Vessel.</p><form id="settings-form"><label>Имя пользователя<input name="name" value="${escapeHtml(user.name)}" required minlength="2" maxlength="32" /></label><label>Статус<select name="status"><option value="online" ${['online','В сети'].includes(user.status)?'selected':''}>В сети</option><option value="dnd" ${['dnd','Не беспокоить'].includes(user.status)?'selected':''}>Не беспокоить</option><option value="away" ${['away','Отошёл'].includes(user.status)?'selected':''}>Отошёл</option></select></label><button class="primary" type="submit">Сохранить изменения</button></form><button class="danger" id="logout" type="button">Выйти из аккаунта</button></div></div>${incomingCall?`<div class="modal call-modal" id="incoming-call-modal"><div class="modal-card"><div class="call-avatar">${escapeHtml(incomingCall.name?.[0]?.toUpperCase()||'?')}</div><h2>${incomingCall.video?'Видеозвонок':'Аудиозвонок'}</h2><p>${escapeHtml(incomingCall.name)} звонит тебе в Vessel.</p><div class="call-actions"><button class="danger" id="reject-call" type="button">Отклонить</button><button class="primary" id="accept-call" type="button">Принять</button></div></div></div>`:''}`;
  const nextMessagesPane=document.querySelector('.messages');
  if(nextMessagesPane){
    const contextChanged=previousMessageContext!==currentMessageContext;
    if(contextChanged||!previousMessageScroll||previousMessageScroll.atBottom){
      requestAnimationFrame(()=>{
        if(nextMessagesPane.isConnected)nextMessagesPane.scrollTop=nextMessagesPane.scrollHeight;
      });
    }else{
      const maxTop=Math.max(0,nextMessagesPane.scrollHeight-nextMessagesPane.clientHeight);
      nextMessagesPane.scrollTop=Math.min(previousMessageScroll.top,maxTop);
    }
  }
  lastRenderedMessageContext=currentMessageContext;
  document.querySelector('.composer').addEventListener('submit', async e => {
    e.preventDefault();
    const input=e.currentTarget.querySelector('input');
    const text=input.value.trim();
    if(!text)return;
    if(!supabase||!user.id){vesselNotice('Нужна активная сессия Vessel.','error');return;}
    const sendSessionUserId=user.id;
    if(activeDmId){
      const peerId=activeDmId;
      if((await verifyDirectMessageAccess(user,peerId))!==true)return;
      const {error}=await supabase.from('direct_messages').insert({sender_id:sendSessionUserId,receiver_id:peerId,body:text});
      if(savedUser?.id!==sendSessionUserId)return;
      if(error){
        const access=await verifyDirectMessageAccess(user,peerId,{notify:false});
        if(access===false){vesselNotice('Пользователь больше не в друзьях. История оставлена только для чтения.','error');return;}
        vesselNotice(`Не удалось отправить личное сообщение: ${error.message}`,'error');
        return;
      }
      window.__vesselDmThreadsLoaded=false;
      const refreshes=[syncDmThreads(user)];
      if(activeDmId===peerId)refreshes.push(loadDirectMessages(user,peerId));
      await Promise.all(refreshes);
    } else {
      if(!activeChannelId||activeChannelKind!=='text'){vesselNotice('Сначала выбери текстовый канал.','error');return;}
      const channelId=activeChannelId;
      if((await verifyChannelAccess(user,channelId))!==true)return;
      if(savedUser?.id!==sendSessionUserId)return;
      const {error}=await supabase.from('messages').insert({channel_id:channelId,author_id:sendSessionUserId,body:text});
      if(savedUser?.id!==sendSessionUserId)return;
      if(error){
        const access=await verifyChannelAccess(user,channelId,{notify:false});
        if(access===false){vesselNotice('Доступ к каналу потерян. Список серверов обновлён.','error');return;}
        vesselNotice(`Не удалось отправить сообщение: ${error.message}`,'error');
        return;
      }
      if(!activeDmId&&activeChannelId===channelId&&activeChannelKind==='text')await loadChannelMessages(channelId);
    }
    if(savedUser?.id!==sendSessionUserId)return;
    input.value='';
    render();
    const list=document.querySelector('.messages');
    if(list)list.scrollTop=list.scrollHeight;
  });
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
      const attachmentSessionUserId=user.id;
      if(savedUser?.id!==attachmentSessionUserId)return;
      const targetDmId=activeDmId;
      const targetChannelId=!targetDmId&&activeChannelKind==='text'?activeChannelId:null;
      if(!targetDmId&&!targetChannelId){vesselNotice('Открой текстовый канал или личный чат.','error');return;}
      if(targetDmId&&(await verifyDirectMessageAccess(user,targetDmId))!==true)return;
      if(targetChannelId&&(await verifyChannelAccess(user,targetChannelId))!==true)return;
      if(savedUser?.id!==attachmentSessionUserId)return;
      const attachmentContext=targetDmId?`dm/${targetDmId}`:`channel/${targetChannelId}`;
      const attachment=await uploadVesselFile(file,user,attachmentContext); if(!attachment)return;
      if(savedUser?.id!==attachmentSessionUserId){await cleanupFailedAttachment(attachment);return;}
      if(targetDmId&&(await verifyDirectMessageAccess(user,targetDmId))!==true){await cleanupFailedAttachment(attachment);return;}
      if(targetChannelId&&(await verifyChannelAccess(user,targetChannelId))!==true){await cleanupFailedAttachment(attachment);return;}
      if(savedUser?.id!==attachmentSessionUserId){await cleanupFailedAttachment(attachment);return;}
      const body=`📎 ${file.name}`;
      if(targetDmId){
        const peerId=targetDmId;
        const {error}=await supabase.from('direct_messages').insert({sender_id:attachmentSessionUserId,receiver_id:peerId,body,attachments:[attachment]});
        if(savedUser?.id!==attachmentSessionUserId){if(error)await cleanupFailedAttachment(attachment);return;}
        if(error){
          await cleanupFailedAttachment(attachment);
          const access=await verifyDirectMessageAccess(user,peerId,{notify:false});
          if(access===false){vesselNotice('Пользователь больше не в друзьях. История оставлена только для чтения.','error');return;}
          vesselNotice(`Не удалось отправить файл: ${error.message}`,'error');
          return;
        }
        window.__vesselDmThreadsLoaded=false;
        const refreshes=[syncDmThreads(user)];
        if(activeDmId===peerId)refreshes.push(loadDirectMessages(user,peerId));
        await Promise.all(refreshes);
      } else {
        const {error}=await supabase.from('messages').insert({channel_id:targetChannelId,author_id:attachmentSessionUserId,body,attachments:[attachment]});
        if(savedUser?.id!==attachmentSessionUserId){if(error)await cleanupFailedAttachment(attachment);return;}
        if(error){
          await cleanupFailedAttachment(attachment);
          const access=await verifyChannelAccess(user,targetChannelId,{notify:false});
          if(access===false){vesselNotice('Доступ к каналу потерян. Список серверов обновлён.','error');return;}
          vesselNotice(`Не удалось отправить файл: ${error.message}`,'error');
          return;
        }
        if(!activeDmId&&activeChannelId===targetChannelId&&activeChannelKind==='text'){
          await loadChannelMessages(targetChannelId);
        }
      }
      if(savedUser?.id!==attachmentSessionUserId)return;
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
    const openNotification=async selected=>{
      const notification=notifications.find(item=>item.id===selected?.value);
      if(!notification)return;
      if(notification.type==='direct_message'&&notification.data?.sender_id){
        const peerId=notification.data.sender_id;
        let peer=dmThreads.find(item=>item.id===peerId)||friends.find(item=>item.id===peerId)||null;
        if(!peer&&supabase){
          const {data:profile,error}=await supabase.from('profiles').select('id,username,avatar_color,status').eq('id',peerId).maybeSingle();
          if(error)console.warn('Notification peer profile load failed',error);else peer=profile;
        }
        currentDm=peer?.username||'Пользователь';
        activeDmId=peerId;
        friendsOpen=false;
        window.__vesselDmLoaded=false;
        document.querySelector('.channels')?.classList.remove('mobile-open');
        render();
        await markDirectMessageNotificationsRead(user,peerId);
        return;
      }
      if(notification.type==='friend_request'){
        friendsOpen=true;
        currentDm=null;
        activeDmId=null;
        dmMessages=[];
        window.__vesselDmLoaded=false;
        document.querySelector('.channels')?.classList.remove('mobile-open');
        render();
      }
    };
    vesselListDialog('Уведомления',notifications.map(item=>({title:item.title||'Vessel',body:item.body||'',meta:item.created_at?new Date(item.created_at).toLocaleString('ru-RU'):'',value:['direct_message','friend_request'].includes(item.type)?item.id:null})), 'Уведомлений пока нет',openNotification);
    const sessionUserId=user.id;
    const unreadIds=notifications.filter(item=>!item.read_at&&item.type!=='direct_message').map(item=>item.id).filter(Boolean);
    if(unreadIds.length&&supabase&&sessionUserId){
      const readAt=new Date().toISOString();
      const {data:updated,error}=await supabase.from('notifications').update({read_at:readAt}).eq('user_id',sessionUserId).in('id',unreadIds).is('read_at',null).select('id');
      if(savedUser?.id!==sessionUserId)return;
      if(error){console.warn('Notification read update failed',error);vesselNotice('Не удалось отметить уведомления прочитанными.','error');return;}
      const updatedIds=new Set((updated||[]).map(row=>row.id));
      notifications=notifications.map(item=>updatedIds.has(item.id)&&!item.read_at?{...item,read_at:readAt}:item);
      render();
    }
  });
  const modal = document.querySelector('#settings-modal');
  document.querySelector('#profile-settings').addEventListener('click', () => modal.classList.remove('hidden'));
  const setMobileDrawerOpen=open=>document.querySelector('.channels')?.classList.toggle('mobile-open',Boolean(open));
  document.querySelector('#mobile-nav')?.addEventListener('click',()=>setMobileDrawerOpen(!document.querySelector('.channels')?.classList.contains('mobile-open')));
  document.querySelector('#mobile-nav-close')?.addEventListener('click',()=>setMobileDrawerOpen(false));
  document.querySelector('.more').addEventListener('click', async () => {
    const server=getActiveServer();
    if(!server?.dbId){vesselNotice('Сначала выбери сервер.','error');return;}
    if(server.role==='owner'){
      const action=await vesselChoice('Управление сервером',[{label:'Создать приглашение',value:'1'},{label:'Управление приглашениями',value:'4'},{label:'Переименовать сервер',value:'2'},{label:'Удалить сервер',value:'3',danger:true}]);
      if(action==='1'){
        const code=`VSL-${crypto.randomUUID().slice(0,8).toUpperCase()}`;
        const {error}=await supabase.from('server_invites').insert({server_id:server.dbId,created_by:user.id,code});
        if(error)vesselNotice(`Не удалось создать приглашение: ${error.message}`,'error');else vesselCodeDialog(`Приглашение в ${server.name}`,code);
        return;
      }
      if(action==='4'){await manageServerInvites(user,server);return;}
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
    if(!['owner','moderator'].includes(server.role)){vesselNotice('Создавать каналы могут владелец и модераторы сервера.','error');return;}
    if(serverChannels().some(channel=>channel.name.toLocaleLowerCase('ru-RU')===channelName.toLocaleLowerCase('ru-RU'))){vesselNotice('Канал с таким названием уже существует.','error');return;}
    const position=serverChannels().reduce((max,channel)=>Math.max(max,Number(channel.position)||0),-1)+1;
    const {data,error}=await supabase.from('channels').insert({server_id:server.dbId,name:channelName,kind,position}).select('id,name,kind,position').single();
    if(error){vesselNotice(error.code==='23505'?'Канал с таким названием уже существует.':`Не удалось создать канал: ${error.message}`,'error');if(error.code==='23505'){server.__channelsLoaded=false;await syncSupabaseChannels(server);}return;}
    activeChannelId=data.id; activeChannelName=data.name; activeChannelKind=data.kind; currentDm=null; activeDmId=null; friendsOpen=false; messages=[];
    server.__channelsLoaded=false;
    await syncSupabaseChannels(server);
    vesselNotice(`${kind==='voice'?'Голосовой':'Текстовый'} канал «${data.name}» создан.`,'success');
  };
  document.querySelector('#channel-add').addEventListener('click', () => addChannel('text'));
  document.querySelector('#voice-add').addEventListener('click', () => addChannel('voice'));
  document.querySelector('#channel-settings')?.addEventListener('click',async()=>{
    const server=getActiveServer();
    if(!server?.dbId||!['owner','moderator'].includes(server.role)||!activeChannelId)return;
    const channel=serverChannels().find(item=>item.id===activeChannelId);
    if(!channel)return;
    const action=await vesselChoice(`Канал «${channel.name}»`,[{label:'Переименовать',value:'1'},{label:'Удалить',value:'2',danger:true}]);
    if(action==='1'){
      const name=await vesselPrompt('Переименовать канал',channel.name,'Название канала');
      const channelName=String(name||'').trim().replace(/\s+/g,'-').replace(/-+/g,'-').slice(0,50);
      if(!channelName||channelName===channel.name)return;
      if(serverChannels().some(item=>item.id!==channel.id&&item.name.toLocaleLowerCase('ru-RU')===channelName.toLocaleLowerCase('ru-RU'))){vesselNotice('Канал с таким названием уже существует.','error');return;}
      const {error}=await supabase.from('channels').update({name:channelName}).eq('id',channel.id).eq('server_id',server.dbId);
      if(error){vesselNotice(error.code==='23505'?'Канал с таким названием уже существует.':`Не удалось переименовать канал: ${error.message}`,'error');if(error.code==='23505'){server.__channelsLoaded=false;await syncSupabaseChannels(server);}return;}
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
  const logoutButton=document.querySelector('#logout');
  logoutButton.addEventListener('click', async () => {
    if(!supabase){vesselNotice('Сервис авторизации временно недоступен.','error');return;}
    logoutButton.disabled=true;
    try{
      const {error}=await supabase.auth.signOut();
      if(error){vesselNotice('Не удалось выйти из аккаунта. Попробуй ещё раз.','error');return;}
      if(savedUser){
        const staleChannels=resetAuthenticatedRuntime();
        render();
        cleanupAuthenticatedChannels(staleChannels).catch(cleanupError=>console.warn('Logout cleanup failed',cleanupError));
      }
    }catch(error){
      console.warn('Logout failed',error);
      vesselNotice('Не удалось выйти из аккаунта. Попробуй ещё раз.','error');
    }finally{
      if(logoutButton.isConnected)logoutButton.disabled=false;
    }
  });
  document.querySelector('#join-voice')?.addEventListener('click',async event=>{
    const button=event.currentTarget;
    button.disabled=true;
    try{await toggleVoiceRoom(user);}finally{if(button.isConnected)button.disabled=false;}
  });
  document.querySelector('#mute-voice')?.addEventListener('click',toggleVoiceMicrophone);
  document.querySelector('#deafen-voice')?.addEventListener('click',toggleVoiceDeafen);
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
    const action=await vesselChoice(`Участник ${member.username}`,[{label:'Сделать участником',value:'1'},{label:'Сделать модератором',value:'2'},{label:'Передать владение сервером',value:'4',danger:true},{label:'Исключить из сервера',value:'3',danger:true}]);
    if(action==='4'){
      if(!await vesselConfirm(`Передать сервер пользователю ${member.username}?`,'Ты перестанешь быть владельцем и станешь обычным участником.'))return;
      const serverId=server.dbId;
      const {data,error}=await supabase.functions.invoke('transfer-server-ownership',{body:{server_id:serverId,target_owner:memberId}});
      if(error||data?.ok!==true){vesselNotice(`Не удалось передать сервер: ${error?.message||'неизвестная ошибка'}`,'error');return;}
      window.__vesselServersLoaded=false;
      window.__vesselMembersServerId=null;
      serverMembers=[];
      await syncSupabaseServers(user);
      const refreshedServer=getActiveServer();
      if(refreshedServer?.dbId===serverId){
        refreshedServer.__channelsLoaded=false;
        await Promise.all([syncSupabaseChannels(refreshedServer),syncServerMembers(user,refreshedServer)]);
      }
      vesselNotice(`Сервер передан пользователю ${member.username}.`,'success');
      render();
      return;
    }
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
  document.querySelectorAll('[data-dm]').forEach(button=>button.addEventListener('click',async()=>{currentDm=button.dataset.dm;activeDmId=button.dataset.dmId||null;friendsOpen=false;window.__vesselDmLoaded=false;render();if(activeDmId)await markDirectMessageNotificationsRead(user,activeDmId);}));
  document.querySelectorAll('[data-attachment-path]').forEach(button=>button.addEventListener('click',()=>openAttachment(button.dataset.attachmentPath)));
  document.querySelectorAll('[data-edit-message]').forEach(button=>button.addEventListener('click',()=>editOwnMessage(user,button.dataset.editMessage)));
  document.querySelectorAll('[data-delete-message]').forEach(button=>button.addEventListener('click',()=>deleteOwnMessage(user,button.dataset.deleteMessage)));
  document.querySelectorAll('[data-remove-friend]').forEach(button=>button.addEventListener('click',async()=>{
    if(!supabase||!user.id)return;
    const friendId=button.dataset.removeFriend;
    const friend=friends.find(item=>item.id===friendId);
    if(!await vesselConfirm(`Удалить ${friend?.username||'пользователя'} из друзей?`))return;
    if(incomingCall?.from===friendId){incomingCall=null;render();}
    if(callPeer===friendId)await endCall(false);
    const {data:removed,error}=await supabase.from('friendships').delete().or(`and(user_id.eq.${user.id},friend_id.eq.${friendId}),and(user_id.eq.${friendId},friend_id.eq.${user.id})`).select('user_id,friend_id');
    if(error){vesselNotice(`Не удалось удалить друга: ${error.message}`,'error');return;}
    if(!removed?.length){
      window.__vesselSocialLoaded=false;
      await syncSocial(user);
      vesselNotice('Пользователь уже удалён из друзей. Список обновлён.');
      return;
    }
    const keepActiveHistory=activeDmId===friendId;
    if(keepActiveHistory)window.__vesselDmLoaded=false;
    window.__vesselSocialLoaded=false;
    window.__vesselDmThreadsLoaded=false;
    await Promise.all([syncSocial(user),syncDmThreads(user)]);
    if(keepActiveHistory&&activeDmId===friendId)await loadDirectMessages(user,friendId);else render();
  }));
  document.querySelectorAll('[data-cancel-request]').forEach(button=>button.addEventListener('click',async()=>{
    if(!supabase||!user.id)return;
    const requestId=button.dataset.cancelRequest;
    const {data:cancelled,error}=await supabase.from('friend_requests').delete().eq('id',requestId).eq('sender_id',user.id).eq('status','pending').select('id');
    if(error){vesselNotice('Не удалось отменить заявку.','error');return;}
    window.__vesselSocialLoaded=false;
    await syncSocial(user);
    if(!cancelled?.some(row=>row.id===requestId)){vesselNotice('Заявка уже была обработана. Список обновлён.');return;}
    vesselNotice('Заявка отменена.','success');
  }));
  document.querySelectorAll('[data-accept-request]').forEach(button=>button.addEventListener('click',async()=>{
    if(!supabase||!user.id)return;
    const requestId=button.dataset.acceptRequest;
    const {data:accepted,error}=await supabase.from('friend_requests').update({status:'accepted',updated_at:new Date().toISOString()}).eq('id',requestId).eq('receiver_id',user.id).eq('status','pending').select('id,status').maybeSingle();
    if(error){vesselNotice('Не удалось принять заявку.','error');return;}
    window.__vesselSocialLoaded=false;
    await syncSocial(user);
    if(!accepted){vesselNotice('Заявка уже была обработана. Список обновлён.');return;}
    vesselNotice('Заявка принята.','success');
    render();
  }));
  document.querySelectorAll('[data-decline-request]').forEach(button=>button.addEventListener('click',async()=>{
    if(!supabase||!user.id)return;
    const requestId=button.dataset.declineRequest;
    const {data:declined,error}=await supabase.from('friend_requests').update({status:'declined',updated_at:new Date().toISOString()}).eq('id',requestId).eq('receiver_id',user.id).eq('status','pending').select('id,status').maybeSingle();
    if(error){vesselNotice('Не удалось отклонить заявку.','error');return;}
    window.__vesselSocialLoaded=false;
    await syncSocial(user);
    if(!declined){vesselNotice('Заявка уже была обработана. Список обновлён.');return;}
    vesselNotice('Заявка отклонена.');
    render();
  }));
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
