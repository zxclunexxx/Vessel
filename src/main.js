import './style.css';

const SUPABASE_URL = 'https://zqbveciunttbvvxhqvqs.supabase.co';
const SUPABASE_KEY = 'sb_publishable_vjT6aZKGuklvcCmmqcb-Zw_E5zc-434';
const supabase = window.supabase?.createClient(SUPABASE_URL, SUPABASE_KEY);
let activeChannelId = null;
let dbChannels = [];
let voiceStream = null;
let voiceRoom = null;
async function syncSupabaseMessages() {
  if (!supabase || window.__vesselDbLoaded) return;
  const {data: channels} = await supabase.from('channels').select('id').limit(1);
  if (!channels?.[0]) return;
  activeChannelId = channels[0].id;
  const {data} = await supabase.from('messages').select('body,created_at,profiles(username,avatar_color)').eq('channel_id',activeChannelId).order('created_at',{ascending:true}).limit(100);
  if (data?.length) { messages=data.map(m=>({name:m.profiles?.username||'Участник',time:new Date(m.created_at).toLocaleString('ru-RU'),color:m.profiles?.avatar_color||'#8b7cff',text:m.body})); render(); }
  window.__vesselDbLoaded=true;
}
async function syncSupabaseServers(user) {
  if (!supabase || window.__vesselServersLoaded || !user?.id) return;
  const {data} = await supabase.from('servers').select('id,name,icon').eq('owner_id',user.id).order('created_at');
  if (data?.length) { servers=[...data.map(s=>({icon:s.icon,name:s.name})),{icon:'+',name:'Добавить сервер',add:true}]; render(); }
  window.__vesselServersLoaded=true;
}
async function syncSupabaseChannels() {
  if (!supabase || window.__vesselChannelsLoaded) return;
  const {data} = await supabase.from('channels').select('id,name,kind').order('position');
  if (data?.length) { dbChannels=data; activeChannelId=data[0].id; render(); }
  window.__vesselChannelsLoaded=true;
}

let servers = JSON.parse(localStorage.getItem('vesselServers') || 'null') || [
  { icon: 'V', name: 'Vessel', active: true },
  { icon: '🎮', name: 'Игры' },
  { icon: '🎵', name: 'Музыка' },
  { icon: '+', name: 'Добавить сервер', add: true },
];

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

const savedUser = JSON.parse(localStorage.getItem('vesselUser') || 'null');

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
    document.querySelector('#demo-login').addEventListener('click', () => { localStorage.setItem('vesselUser', JSON.stringify({name:'Артём', email:'demo@vessel.app'})); location.reload(); });
    document.querySelector('#auth-switch').addEventListener('click', () => { const form=document.querySelector('.auth-form'); form.innerHTML='<label>Электронная почта<input name="email" type="email" required placeholder="you@example.com" /></label><label>Пароль<input name="password" type="password" required minlength="4" placeholder="Твой пароль" /></label><button class="primary" type="submit">Войти <span>→</span></button>'; form.onsubmit=async e=>{e.preventDefault();const d=new FormData(form);try{const {data,error}=await supabase.auth.signInWithPassword({email:d.get('email'),password:d.get('password')});if(error)throw error;localStorage.setItem('vesselToken',data.session.access_token);localStorage.setItem('vesselUser',JSON.stringify({name:data.user.user_metadata.username||data.user.email.split('@')[0],email:data.user.email}));location.reload();}catch{alert('Не удалось войти. Проверь почту и пароль.');}}; });
    return;
  }
  const user = JSON.parse(localStorage.getItem('vesselUser'));
  connectRealtime(); syncSupabaseMessages(); syncSupabaseServers(user); syncSupabaseChannels();
  document.querySelector('#app').innerHTML = `
    <main class="shell">
      <aside class="servers">${servers.map(s => `<button class="server ${s.active ? 'selected' : ''} ${s.add ? 'add' : ''}" title="${s.name}">${s.icon}</button>`).join('')}</aside>
      <aside class="channels">
        <div class="brand"><span class="brand-mark">◈</span><span>Vessel</span><button class="more">•••</button></div>
        <div class="user-card"><div class="avatar user-avatar">${user.name[0].toUpperCase()}</div><div><b>${user.name}</b><small>в сети</small></div><button class="icon-btn" id="profile-settings" title="Настройки">⚙</button></div>
        <section class="channel-section"><div class="section-title">ЛИЧНЫЕ СООБЩЕНИЯ <button>＋</button></div>
          <button class="channel dm"><div class="mini-avatar" style="background:#8b7cff">М</div> Марк <em></em></button><button class="channel dm"><div class="mini-avatar" style="background:#ff7294">Л</div> Лиза <em></em></button>
        </section>
        <section class="channel-section"><div class="section-title">ТЕКСТОВЫЕ КАНАЛЫ <button id="channel-add">＋</button></div>
          ${(dbChannels.length ? dbChannels : [{name:'общий',kind:'text'},{name:'идеи-vessel',kind:'text'},{name:'музыка',kind:'text'}]).map((c,i)=>`<button class="channel ${i===0?'active':''}"><span>${c.kind==='voice'?'⌁':'#'}</span> ${c.name}</button>`).join('')}
        </section>
        <section class="channel-section"><div class="section-title">ГОЛОСОВЫЕ КАНАЛЫ <button id="voice-add">＋</button></div><button class="channel"><span>⌁</span> Lounge</button><button class="channel"><span>⌁</span> Игровая</button></section>
        <div class="side-footer">Vessel v0.1 <span>●</span></div>
      </aside>
      <section class="chat">
        <header class="chat-head"><div><h1><span>#</span> общий</h1><p>Главный канал Vessel</p></div><div class="head-actions"><button id="join-voice" class="join-voice hidden">Подключиться</button><button id="mute-voice" class="join-voice hidden">🎙</button><button id="camera-voice" class="join-voice hidden">📷</button><button id="search-button">⌕</button><button>♧</button><button id="notifications">🔔</button><button>⚙</button></div></header>
        <video id="local-video" class="local-video ${voiceStream?'':'hidden'}" autoplay muted playsinline></video><div class="messages"><div class="welcome"><div class="welcome-icon">#</div><h2>Добро пожаловать в #общий!</h2><p>Это начало канала. Здесь начинается ваше общение.</p></div>${messages.map(m => `<article class="message"><div class="avatar" style="background:${m.color}">${m.name[0]}</div><div><div class="message-meta"><b>${m.name}</b><time>${m.time}</time></div><p>${m.text}</p></div></article>`).join('')}</div>
        <form class="composer"><button type="button" class="attach">＋</button><input placeholder="Написать в #общий" /><button type="button">☺</button><button type="submit" class="send">➤</button></form>
      </section>
      <aside class="members">${voiceStream?'<div class="voice-status">🎙 Ты в голосовой комнате</div>':''}<div class="members-title">УЧАСТНИКИ — 3</div><div class="member online"><div class="avatar" style="background:#8b7cff">М</div><span>Марк<small>Создатель</small></span><i></i></div><div class="member online"><div class="avatar" style="background:#ff7294">Л</div><span>Лиза<small>Дизайнер</small></span><i></i></div><div class="member online"><div class="avatar" style="background:#39d9a6">А</div><span>Артём<small>В сети</small></span><i></i></div></aside>
    </main><div class="modal hidden" id="settings-modal"><div class="modal-card"><button class="modal-close" id="close-settings">×</button><h2>Настройки профиля</h2><p>Измени данные, которые видят другие участники Vessel.</p><form id="settings-form"><label>Имя пользователя<input name="name" value="${user.name}" required minlength="2" /></label><label>Статус<select name="status"><option>В сети</option><option>Не беспокоить</option><option>Отошёл</option></select></label><button class="primary" type="submit">Сохранить изменения</button></form><button class="danger" id="logout" type="button">Выйти из аккаунта</button></div></div>`;
  document.querySelector('.composer').addEventListener('submit', e => { e.preventDefault(); const input=e.currentTarget.querySelector('input'); if(input.value.trim()){ const text=input.value.trim(); messages.push({name:user.name,time:'только что',color:'#39d9a6',text}); localStorage.setItem('vesselMessages', JSON.stringify(messages)); if(supabase&&activeChannelId&&user.id) supabase.from('messages').insert({channel_id:activeChannelId,author_id:user.id,body:text}); fetch(`${API_URL}/api/messages`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:user.name,body:text,color:'#39d9a6'})}).catch(()=>{}); input.value=''; render(); document.querySelector('.messages').scrollTop=99999; }});
  document.querySelector('.attach').addEventListener('click', () => {
    const picker = document.createElement('input'); picker.type = 'file'; picker.accept = 'image/*,.pdf,.doc,.docx,.zip';
    picker.onchange = () => { const file = picker.files[0]; if (!file) return; messages.push({name:user.name,time:'только что',color:'#39d9a6',text:`📎 Прикреплён файл: ${file.name}`}); localStorage.setItem('vesselMessages', JSON.stringify(messages)); render(); };
    picker.click();
  });
  document.querySelector('#search-button').addEventListener('click', () => { const query=prompt('Поиск по сообщениям:'); if(query){ const found=messages.filter(m=>m.text.toLowerCase().includes(query.toLowerCase())); alert(found.length ? `Найдено сообщений: ${found.length}\n\n${found.map(m=>m.name+': '+m.text).join('\n')}` : 'Ничего не найдено'); }});
  document.querySelector('#notifications').addEventListener('click', e => { e.currentTarget.textContent = e.currentTarget.textContent === '🔔' ? '🔕' : '🔔'; e.currentTarget.title = e.currentTarget.textContent === '🔕' ? 'Уведомления выключены' : 'Уведомления включены'; });
  const modal = document.querySelector('#settings-modal');
  document.querySelector('#profile-settings').addEventListener('click', () => modal.classList.remove('hidden'));
  document.querySelector('#channel-add').addEventListener('click', async () => { const name=prompt('Название нового канала:'); if(!name?.trim()) return; if(supabase&&user.id){ const {data:owned}=await supabase.from('servers').select('id').eq('owner_id',user.id).limit(1); if(owned?.[0]) await supabase.from('channels').insert({server_id:owned[0].id,name:name.trim(),kind:'text',position:dbChannels.length}); } dbChannels.push({name:name.trim(),kind:'text'}); render(); });
  document.querySelector('#voice-add').addEventListener('click', async () => { const name=prompt('Название голосовой комнаты:'); if(!name?.trim()) return; if(supabase&&user.id){ const {data:owned}=await supabase.from('servers').select('id').eq('owner_id',user.id).limit(1); if(owned?.[0]) await supabase.from('channels').insert({server_id:owned[0].id,name:name.trim(),kind:'voice',position:dbChannels.length}); } dbChannels.push({name:name.trim(),kind:'voice'}); render(); });
  document.querySelector('#close-settings').addEventListener('click', () => modal.classList.add('hidden'));
  document.querySelector('#settings-form').addEventListener('submit', e => { e.preventDefault(); const data=new FormData(e.currentTarget); localStorage.setItem('vesselUser', JSON.stringify({name:data.get('name'),email:user.email,status:data.get('status')})); location.reload(); });
  document.querySelector('#logout').addEventListener('click', () => { localStorage.removeItem('vesselUser'); location.reload(); });
  document.querySelectorAll('.channel').forEach(channel => channel.addEventListener('click', () => {
    document.querySelectorAll('.channel').forEach(item => item.classList.remove('active'));
    channel.classList.add('active');
    const name = channel.textContent.replace('#', '').replace('⌁', '').trim();
    const isDm = channel.classList.contains('dm');
    document.querySelector('.chat-head h1').innerHTML = `<span>${isDm ? '@' : channel.textContent.includes('⌁') ? '⌁' : '#'}</span> ${name}`;
    document.querySelector('.chat-head p').textContent = isDm ? 'Личная переписка' : channel.textContent.includes('⌁') ? 'Голосовая комната' : 'Главный канал Vessel';
    document.querySelector('.composer input').placeholder = isDm ? `Написать пользователю ${name}` : `Написать в ${channel.textContent.includes('⌁') ? '' : '#'}${name}`;
    const voiceButton=document.querySelector('#join-voice'), muteButton=document.querySelector('#mute-voice'), cameraButton=document.querySelector('#camera-voice'); if(channel.textContent.includes('⌁')&&!isDm) { voiceButton.classList.remove('hidden'); voiceButton.textContent=voiceStream?'Выйти':'Подключиться'; voiceButton.onclick=async()=>{ if(voiceStream){voiceStream.getTracks().forEach(t=>t.stop());voiceStream=null;if(voiceRoom)await voiceRoom.unsubscribe();voiceRoom=null;render();return;} try { voiceStream=await navigator.mediaDevices.getUserMedia({audio:true,video:true}); if(supabase&&activeChannelId&&user.id){voiceRoom=supabase.channel('voice-'+activeChannelId);voiceRoom.on('presence',{event:'sync'},()=>{}).subscribe(async status=>{if(status==='SUBSCRIBED')await voiceRoom.track({user_id:user.id,name:user.name});});} render(); } catch { alert('Разреши Vessel доступ к микрофону и камере.'); } }; if(voiceStream){muteButton.classList.remove('hidden');cameraButton.classList.remove('hidden');muteButton.onclick=()=>{const track=voiceStream.getAudioTracks()[0];track.enabled=!track.enabled;muteButton.textContent=track.enabled?'🎙':'🔇';};cameraButton.onclick=()=>{const track=voiceStream.getVideoTracks()[0];track.enabled=!track.enabled;cameraButton.textContent=track.enabled?'📷':'🚫';};} } else {voiceButton.classList.add('hidden');muteButton.classList.add('hidden');cameraButton.classList.add('hidden');}
  }));
  document.querySelectorAll('.server').forEach(server => server.addEventListener('click', () => {
    if (server.classList.contains('add')) {
      const name = prompt('Название нового сервера:');
      if (name && name.trim()) { servers.splice(servers.length - 1, 0, {icon:name.trim()[0].toUpperCase(), name:name.trim()}); localStorage.setItem('vesselServers', JSON.stringify(servers)); render(); }
      return;
    }
    document.querySelectorAll('.server').forEach(item => item.classList.remove('selected'));
    server.classList.add('selected');
  }));
}
render();
setInterval(()=>{const video=document.querySelector('#local-video');if(video&&voiceStream&&video.srcObject!==voiceStream){video.srcObject=voiceStream;video.play().catch(()=>{});}},500);
