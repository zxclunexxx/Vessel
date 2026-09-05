import './style.css';

const SUPABASE_URL = 'https://zqbveciunttbvvxhqvqs.supabase.co';
const SUPABASE_KEY = 'sb_publishable_vjT6aZKGuklvcCmmqcb-Zw_E5zc-434';
const supabase = window.supabase?.createClient(SUPABASE_URL, SUPABASE_KEY);
let activeChannelId = null;
let dbChannels = [];
let voiceStream = null;
let voiceRoom = null;
let activeServerIndex = Number(localStorage.getItem('vesselActiveServer') || 0);
let activeChannelName = 'общий';
let activeChannelKind = 'text';
let currentDm = null;
let activeDmId = null;
let friendsOpen = false;
let friends = [];
let friendRequests = [];
let dmMessages = [];
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
async function syncSocial(user) {
  if (!supabase || !user?.id || window.__vesselSocialLoaded) return;
  const {data: links} = await supabase.from('friendships').select('friend_id').eq('user_id', user.id);
  const ids = (links || []).map(row => row.friend_id).filter(Boolean);
  if (ids.length) {
    const {data: profiles} = await supabase.from('profiles').select('id,username,avatar_color,status').in('id', ids);
    friends = profiles || [];
  }
  const {data: requests} = await supabase.from('friend_requests').select('id,sender_id,status,profiles!friend_requests_sender_id_fkey(username,avatar_color)').eq('receiver_id', user.id).eq('status','pending');
  friendRequests = requests || [];
  window.__vesselSocialLoaded = true;
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

let servers = JSON.parse(localStorage.getItem('vesselServers') || 'null') || [
  { icon: 'V', name: 'Vessel', active: true },
  { icon: '🎮', name: 'Игры' },
  { icon: '🎵', name: 'Музыка' },
  { icon: '+', name: 'Добавить сервер', add: true },
];
servers = servers.map((server, index) => ({...server, id: server.id || `local-${index}`}));
if (activeServerIndex >= servers.length - 1) activeServerIndex = 0;

function serverChannels() {
  const server = servers[activeServerIndex];
  const fallback = server?.name === 'Vessel'
    ? [{name:'общий',kind:'text'},{name:'идеи-vessel',kind:'text'},{name:'музыка',kind:'text'},{name:'Lounge',kind:'voice'},{name:'Игровая',kind:'voice'}]
    : [{name:'общий',kind:'text'}];
  return savedChannelMap[server?.id] || fallback;
}

function saveChannelMap() {
  localStorage.setItem('vesselChannelMap', JSON.stringify(savedChannelMap));
}

const defaultMessages = [
  { name: 'Марк', time: 'Сегодня в 11:42', color: '#8b7cff', text: 'Добро пожаловать в Vessel! Здесь можно общаться, создавать свои серверы и собирать команды.' },
  { name: 'Лиза', time: 'Сегодня в 11:44', color: '#ff7294', text: 'Интерфейс выглядит очень круто 🔥' },
  { name: 'Ты', time: 'Сегодня в 11:45', color: '#39d9a6', text: 'Это только начало. Скоро добавим голосовые комнаты и личные сообщения.' },
];
let messages = JSON.parse(localStorage.getItem('vesselMessages') || 'null') || defaultMessages;
const API_URL = 'http://localhost:8080';

function connectRealtime() {
  if (window.__vesselRealtime || !window.EventSource) return;
  window.__vesselRealtime = new EventSource(`${API_URL}/api/events`);
  window.__vesselRealtime.onmessage = event => { try { const item=JSON.parse(event.data); messages.push({name:item.name||'Участник',time:'только что',color:item.color||'#8b7cff',text:item.body||item.text}); localStorage.setItem('vesselMessages',JSON.stringify(messages)); render(); } catch {} };
}
function connectSupabaseRealtime(user) {
  if (!supabase || !user?.id || window.__vesselRealtimeChannels) return;
  window.__vesselRealtimeChannels = [
    supabase.channel(`vessel-dm-${user.id}`).on('postgres_changes',{event:'INSERT',schema:'public',table:'direct_messages'},payload=>{
      const row=payload.new;
      if(activeDmId && (row.sender_id===activeDmId || row.receiver_id===activeDmId)){ window.__vesselDmLoaded=false; loadDirectMessages(user,activeDmId); }
    }).subscribe(),
    supabase.channel(`vessel-friends-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'friend_requests',filter:`receiver_id=eq.${user.id}`},()=>{window.__vesselSocialLoaded=false;syncSocial(user).then(()=>{if(friendsOpen)render();});}).subscribe(),
    supabase.channel(`vessel-channel-messages-${user.id}`).on('postgres_changes',{event:'INSERT',schema:'public',table:'messages'},payload=>{
      if(payload.new.channel_id===activeChannelId && payload.new.author_id!==user.id){messages.push({name:'Участник',time:'только что',color:'#8b7cff',text:payload.new.body});render();}
    }).subscribe()
  ];
}

const savedUser = JSON.parse(localStorage.getItem('vesselUser') || 'null');

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
  if (!savedUser && !localStorage.getItem('vesselUser')) {
    document.querySelector('#app').innerHTML = `
      <main class="auth-page"><div class="auth-glow"></div><section class="auth-card">
        <div class="auth-logo">◈</div><h1>Добро пожаловать<br><span>в Vessel</span></h1>
        <p class="auth-subtitle">Твоё пространство для общения,<br>команд и идей.</p>
        <form class="auth-form"><label>Имя пользователя<input name="name" required minlength="2" placeholder="Например, Артём" /></label><label>Электронная почта<input name="email" type="email" required placeholder="you@example.com" /></label><label>Пароль<input name="password" type="password" required minlength="4" placeholder="Минимум 4 символа" /></label><button class="primary" type="submit">Создать аккаунт <span>→</span></button></form>
        <div class="auth-divider"><span>или</span></div><button class="ghost" type="button" id="demo-login">Войти в демо-режим</button><button class="auth-switch" type="button" id="auth-switch">У меня уже есть аккаунт</button><small>Продолжая, ты принимаешь правила Vessel</small>
      </section></main>`;
    document.querySelector('.auth-form').addEventListener('submit', async e => { e.preventDefault(); const data = new FormData(e.currentTarget); const payload={name:data.get('name'),email:data.get('email'),password:data.get('password')}; try { if (!supabase) throw new Error(); const {data:result,error}=await supabase.auth.signUp({email:payload.email,password:payload.password,data:{username:payload.name}}); if(error) throw error; localStorage.setItem('vesselToken',result.session?.access_token||'pending'); localStorage.setItem('vesselUser', JSON.stringify({id:result.user?.id,name:payload.name,email:payload.email})); location.reload(); } catch { localStorage.setItem('vesselUser', JSON.stringify({name:payload.name,email:payload.email})); location.reload(); } });
    document.querySelector('#demo-login').addEventListener('click', () => { localStorage.setItem('vesselUser', JSON.stringify({id:null,name:'Артём', email:'demo@vessel.app'})); location.reload(); });
    document.querySelector('#auth-switch').addEventListener('click', () => { const form=document.querySelector('.auth-form'); form.innerHTML='<label>Электронная почта<input name="email" type="email" required placeholder="you@example.com" /></label><label>Пароль<input name="password" type="password" required minlength="4" placeholder="Твой пароль" /></label><button class="primary" type="submit">Войти <span>→</span></button>'; form.onsubmit=async e=>{e.preventDefault();const d=new FormData(form);try{const {data,error}=await supabase.auth.signInWithPassword({email:d.get('email'),password:d.get('password')});if(error)throw error;localStorage.setItem('vesselToken',data.session.access_token);localStorage.setItem('vesselUser',JSON.stringify({id:data.user.id,name:data.user.user_metadata.username||data.user.email.split('@')[0],email:data.user.email}));location.reload();}catch{alert('Не удалось войти. Проверь почту и пароль.');}}; });
    return;
  }
  const user = JSON.parse(localStorage.getItem('vesselUser'));
  connectRealtime(); connectSupabaseRealtime(user); syncSupabaseMessages(); syncSupabaseServers(user); syncSupabaseChannels(servers[activeServerIndex]); syncSocial(user); if (activeDmId && !window.__vesselDmLoaded) { window.__vesselDmLoaded=true; loadDirectMessages(user,activeDmId); }
  document.querySelector('#app').innerHTML = `
    <main class="shell">
      <aside class="servers"><button class="server home-tab ${friendsOpen?'selected':''}" id="friends-tab" title="Друзья">👥</button>${servers.map((s,i) => `<button class="server ${!friendsOpen&&i===activeServerIndex?'selected':''} ${s.add ? 'add' : ''}" data-server-index="${i}" title="${s.name}">${s.icon}</button>`).join('')}</aside>
      <aside class="channels">
        <div class="brand"><span class="brand-mark">◈</span><span>${friendsOpen?'Друзья':servers[activeServerIndex]?.name || 'Vessel'}</span><button class="more">•••</button></div>
        <div class="user-card"><div class="avatar user-avatar">${user.name[0].toUpperCase()}</div><div><b>${user.name}</b><small>в сети</small></div><button class="icon-btn" id="profile-settings" title="Настройки">⚙</button></div>
        <section class="channel-section"><div class="section-title">ЛИЧНЫЕ СООБЩЕНИЯ <button id="dm-add">＋</button></div>
          <button class="channel dm"><div class="mini-avatar" style="background:#8b7cff">М</div> Марк <em></em></button><button class="channel dm"><div class="mini-avatar" style="background:#ff7294">Л</div> Лиза <em></em></button>
        </section>
        <section class="channel-section"><div class="section-title">ТЕКСТОВЫЕ КАНАЛЫ <button id="channel-add">＋</button></div>
          ${serverChannels().filter(c=>c.kind==='text').map((c,i)=>`<button class="channel ${!currentDm&&activeChannelKind==='text'&&c.name===activeChannelName?'active':''}" data-channel-id="${c.id||''}" data-channel-name="${c.name}" data-kind="text"><span>#</span> ${c.name}</button>`).join('')}
        </section>
        <section class="channel-section"><div class="section-title">ГОЛОСОВЫЕ КАНАЛЫ <button id="voice-add">＋</button></div>${serverChannels().filter(c=>c.kind==='voice').map(c=>`<button class="channel ${activeChannelKind==='voice'&&c.name===activeChannelName?'active':''}" data-channel-id="${c.id||''}" data-channel-name="${c.name}" data-kind="voice"><span>⌁</span> ${c.name}</button>`).join('')}</section>
        <div class="side-footer">Vessel v0.1 <span>●</span></div>
      </aside>
      <section class="chat">
        <header class="chat-head"><div><h1><span>${currentDm?'@':activeChannelKind==='voice'?'⌁':'#'}</span> ${currentDm || activeChannelName}</h1><p>${currentDm?'Личная переписка':activeChannelKind==='voice'?'Голосовая комната':servers[activeServerIndex]?.name || 'Vessel'}</p></div><div class="head-actions"><button id="audio-call" title="Аудиозвонок">📞</button><button id="video-call" title="Видеозвонок">🎥</button><button id="join-voice" class="join-voice ${activeChannelKind==='voice'?'':'hidden'}">${voiceStream?'Выйти':'Войти'}</button><button id="mute-voice" class="join-voice ${voiceStream?'':'hidden'}">🎙</button><button id="camera-voice" class="join-voice ${voiceStream?'':'hidden'}">📷</button><button id="search-button">⌕</button><button id="friends-button" title="Друзья">♧</button><button id="notifications">🔔</button><button id="head-settings">⚙</button></div></header>
        <video id="local-video" class="local-video ${voiceStream?'':'hidden'}" autoplay muted playsinline></video><div class="messages">${friendsOpen?`<div class="friends-view"><div class="friends-hero"><h2>Друзья</h2><button id="add-friend" class="primary">Найти пользователя</button></div>${friendRequests.map(request=>`<div class="friend-row request-row"><div class="avatar" style="background:#ffb45e">${(request.profiles?.username||'?')[0].toUpperCase()}</div><b>${request.profiles?.username||'Пользователь'}</b><span>Заявка</span><button data-accept-request="${request.id}" data-sender="${request.sender_id}">Принять</button></div>`).join('')}${friends.length ? friends.map(friend=>`<div class="friend-row"><div class="avatar" style="background:${friend.avatar_color||'#8b7cff'}">${friend.username[0].toUpperCase()}</div><b>${friend.username}</b><span>${friend.status||'в сети'}</span><button data-dm-id="${friend.id}" data-dm="${friend.username}">💬</button><button data-call="${friend.username}">📞</button></div>`).join('') : `<p class="empty-state">Пока нет добавленных друзей. Нажми «Найти пользователя».</p>`}</div>`:`<div class="welcome"><div class="welcome-icon">${currentDm?'@':activeChannelKind==='voice'?'⌁':'#'}</div><h2>${currentDm?`Переписка с ${currentDm}`:`Добро пожаловать в ${activeChannelKind==='voice'?'':'#'}${activeChannelName}!`}</h2><p>${activeChannelKind==='voice'?'Подключись к комнате, чтобы общаться голосом.':'Здесь начинается ваше общение.'}</p></div>${(activeDmId?dmMessages:messages).map(m => `<article class="message"><div class="avatar" style="background:${m.color}">${m.name[0]}</div><div><div class="message-meta"><b>${m.name}</b><time>${m.time}</time></div><p>${m.text}</p></div></article>`).join('')}`}</div>
        <form class="composer ${friendsOpen?'hidden':''}"><button type="button" class="attach">＋</button><input placeholder="${currentDm?`Написать пользователю ${currentDm}`:`Написать в #${activeChannelName}`}" /><button type="button">☺</button><button type="submit" class="send">➤</button></form>
      </section>
      <aside class="members">${voiceStream?'<div class="voice-status">🎙 Ты в голосовой комнате</div>':''}<div class="members-title">УЧАСТНИКИ — 3</div><div class="member online"><div class="avatar" style="background:#8b7cff">М</div><span>Марк<small>Создатель</small></span><i></i></div><div class="member online"><div class="avatar" style="background:#ff7294">Л</div><span>Лиза<small>Дизайнер</small></span><i></i></div><div class="member online"><div class="avatar" style="background:#39d9a6">А</div><span>Артём<small>В сети</small></span><i></i></div></aside>
    </main><div class="modal hidden" id="settings-modal"><div class="modal-card"><button class="modal-close" id="close-settings">×</button><h2>Настройки профиля</h2><p>Измени данные, которые видят другие участники Vessel.</p><form id="settings-form"><label>Имя пользователя<input name="name" value="${user.name}" required minlength="2" /></label><label>Статус<select name="status"><option>В сети</option><option>Не беспокоить</option><option>Отошёл</option></select></label><button class="primary" type="submit">Сохранить изменения</button></form><button class="danger" id="logout" type="button">Выйти из аккаунта</button></div></div>`;
  document.querySelector('.composer').addEventListener('submit', async e => { e.preventDefault(); const input=e.currentTarget.querySelector('input'); if(input.value.trim()){ const text=input.value.trim(); if(activeDmId&&supabase&&user.id){ const {error}=await supabase.from('direct_messages').insert({sender_id:user.id,receiver_id:activeDmId,body:text}); if(error){alert('Не удалось отправить личное сообщение.');return;} dmMessages.push({name:user.name,time:'только что',color:'#39d9a6',text}); } else { messages.push({name:user.name,time:'только что',color:'#39d9a6',text}); localStorage.setItem('vesselMessages', JSON.stringify(messages)); if(supabase&&activeChannelId&&user.id) supabase.from('messages').insert({channel_id:activeChannelId,author_id:user.id,body:text}); fetch(`${API_URL}/api/messages`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:user.name,body:text,color:'#39d9a6'})}).catch(()=>{}); } input.value=''; render(); document.querySelector('.messages').scrollTop=99999; }});
  document.querySelector('.attach').addEventListener('click', () => {
    const picker = document.createElement('input'); picker.type = 'file'; picker.accept = 'image/*,.pdf,.doc,.docx,.zip';
    picker.onchange = async () => { const file = picker.files[0]; if (!file) return; const attachment=await uploadVesselFile(file,user); if(!attachment)return; const body=`📎 ${file.name}`; if(activeChannelId&&user.id){const {error}=await supabase.from('messages').insert({channel_id:activeChannelId,author_id:user.id,body,attachments:[attachment]});if(error){alert('Файл загрузился, но сообщение не отправилось.');return;}} messages.push({name:user.name,time:'только что',color:'#39d9a6',text:body}); localStorage.setItem('vesselMessages', JSON.stringify(messages)); render(); };
    picker.click();
  });
  document.querySelector('#search-button').addEventListener('click', () => { const query=prompt('Поиск по сообщениям:'); if(query){ const found=messages.filter(m=>m.text.toLowerCase().includes(query.toLowerCase())); alert(found.length ? `Найдено сообщений: ${found.length}\n\n${found.map(m=>m.name+': '+m.text).join('\n')}` : 'Ничего не найдено'); }});
  document.querySelector('#notifications').addEventListener('click', e => { e.currentTarget.textContent = e.currentTarget.textContent === '🔔' ? '🔕' : '🔔'; e.currentTarget.title = e.currentTarget.textContent === '🔕' ? 'Уведомления выключены' : 'Уведомления включены'; });
  const modal = document.querySelector('#settings-modal');
  document.querySelector('#profile-settings').addEventListener('click', () => modal.classList.remove('hidden'));
  document.querySelector('.more').addEventListener('click', async () => { const server=servers[activeServerIndex]; if(!server?.dbId||server.role!=='owner'){alert(`Твоя роль: ${server?.role||'участник'}. Создавать приглашения может только владелец.`);return;} const code=`VSL-${crypto.randomUUID().slice(0,8).toUpperCase()}`; const {error}=await supabase.from('server_invites').insert({server_id:server.dbId,created_by:user.id,code}); alert(error?'Не удалось создать приглашение.':`Код приглашения для сервера «${server.name}»:\n\n${code}\n\nПередай его другу.`); });
  const addChannel = async kind => { const name=prompt(kind==='voice'?'Название голосовой комнаты:':'Название нового канала:'); if(!name?.trim()) return; const server=servers[activeServerIndex]; const channels=serverChannels(); const created={name:name.trim(),kind}; if(supabase&&user.id&&server.dbId){ const {data,error}=await supabase.from('channels').insert({server_id:server.dbId,name:created.name,kind,position:channels.length}).select('id,name,kind,position').single(); if(error){alert('Не удалось создать канал. Проверь права доступа.');return;} created.id=data.id; activeChannelId=data.id; } savedChannelMap[server.id]=[...channels,created]; saveChannelMap(); activeChannelName=created.name; activeChannelKind=kind; currentDm=null; render(); };
  document.querySelector('#channel-add').addEventListener('click', () => addChannel('text'));
  document.querySelector('#voice-add').addEventListener('click', () => addChannel('voice'));
  document.querySelector('#dm-add').addEventListener('click', () => { const name=prompt('Имя пользователя:'); if(name?.trim()){currentDm=name.trim();activeDmId=null;friendsOpen=false;render();} });
  document.querySelector('#close-settings').addEventListener('click', () => modal.classList.add('hidden'));
  document.querySelector('#settings-form').addEventListener('submit', e => { e.preventDefault(); const data=new FormData(e.currentTarget); localStorage.setItem('vesselUser', JSON.stringify({name:data.get('name'),email:user.email,status:data.get('status')})); location.reload(); });
  document.querySelector('#logout').addEventListener('click', () => { localStorage.removeItem('vesselUser'); location.reload(); });
  document.querySelectorAll('.channel').forEach(channel => channel.addEventListener('click', () => {
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
  document.querySelectorAll('[data-accept-request]').forEach(button=>button.addEventListener('click',async()=>{if(!supabase||!user.id)return;const sender=button.dataset.sender;await supabase.from('friend_requests').update({status:'accepted',updated_at:new Date().toISOString()}).eq('id',button.dataset.acceptRequest);await supabase.from('friendships').upsert([{user_id:user.id,friend_id:sender},{user_id:sender,friend_id:user.id}]);window.__vesselSocialLoaded=false;render();}));
  document.querySelector('#add-friend')?.addEventListener('click',async()=>{const query=prompt('Введи точное имя пользователя:');if(!query?.trim())return;if(!supabase||!user.id){alert('Войди через настоящий аккаунт, чтобы добавлять друзей.');return;}const {data:found}=await supabase.from('profiles').select('id,username').ilike('username',query.trim()).limit(1);if(!found?.[0]){alert('Пользователь не найден.');return;}if(found[0].id===user.id){alert('Нельзя добавить самого себя.');return;}const {error}=await supabase.from('friend_requests').upsert({sender_id:user.id,receiver_id:found[0].id,status:'pending'},{onConflict:'sender_id,receiver_id'});alert(error?'Не удалось отправить заявку.':`Заявка пользователю ${found[0].username} отправлена.`);});
  async function startCall(video) { try { if(voiceStream){voiceStream.getTracks().forEach(t=>t.stop());voiceStream=null;render();return;} voiceStream=await navigator.mediaDevices.getUserMedia({audio:true,video}); render(); alert(`${video?'Видеозвонок':'Аудиозвонок'} начат. Для разговора с другим телефоном собеседник должен войти в эту же комнату.`); } catch { alert('Разреши Vessel доступ к микрофону и камере.'); } }
  document.querySelector('#audio-call').addEventListener('click',()=>startCall(false));
  document.querySelector('#video-call').addEventListener('click',()=>startCall(true));
  document.querySelectorAll('[data-call]').forEach(button=>button.addEventListener('click',()=>{currentDm=button.dataset.call;friendsOpen=false;startCall(false);}));
  document.querySelectorAll('.server[data-server-index]').forEach(server => server.addEventListener('click', async () => {
    if (server.classList.contains('add')) {
      if(supabase&&user.id&&confirm('У тебя есть код приглашения? Нажми «ОК», чтобы вступить в сервер.')){const code=prompt('Введи код приглашения:');if(code?.trim()){await joinByInvite(code,user);return;}}
      const name = prompt('Название нового сервера:');
      if (name && name.trim()) { let created={id:`local-${Date.now()}`,icon:name.trim()[0].toUpperCase(),name:name.trim()}; if(supabase&&user.id){ const {data,error}=await supabase.from('servers').insert({name:name.trim(),icon:created.icon,owner_id:user.id}).select('id,name,icon').single(); if(error){alert('Не удалось создать сервер. Проверь права доступа.');return;} created={...created,id:data.id,dbId:data.id}; } servers.splice(servers.length - 1, 0, created); activeServerIndex=servers.length-2; savedChannelMap[created.id]=[{name:'общий',kind:'text'}]; saveChannelMap(); localStorage.setItem('vesselServers', JSON.stringify(servers)); localStorage.setItem('vesselActiveServer',activeServerIndex); activeChannelName='общий';activeChannelKind='text';currentDm=null;friendsOpen=false;render(); }
      return;
    }
    activeServerIndex=Number(server.dataset.serverIndex);localStorage.setItem('vesselActiveServer',activeServerIndex);activeChannelName='общий';activeChannelKind='text';activeChannelId=null;currentDm=null;friendsOpen=false;render();syncSupabaseChannels(servers[activeServerIndex]);
  }));
}
render();
setInterval(()=>{const video=document.querySelector('#local-video');if(video&&voiceStream&&video.srcObject!==voiceStream){video.srcObject=voiceStream;video.play().catch(()=>{});}},500);
