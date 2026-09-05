from pathlib import Path

main_path = Path('src/main.js')
css_path = Path('src/style.css')
text = main_path.read_text(encoding='utf-8')
css = css_path.read_text(encoding='utf-8')

def replace_once(old, new, label):
    global text
    if old not in text:
        raise SystemExit(f'{label} anchor not found')
    text = text.replace(old, new, 1)

# Voice rooms: disconnect only when pressing the button for the room we are actually in;
# otherwise switch directly to the newly selected voice room.
replace_once(
"""async function toggleVoiceRoom(user){
  if(voiceStream){await leaveVoiceRoom();return;}
  if(!supabase||!user?.id||!activeChannelId||activeChannelKind!=='voice'){alert('Сначала открой голосовой канал.');return;}""",
"""async function toggleVoiceRoom(user){
  if(voiceStream && voiceChannelId===activeChannelId){await leaveVoiceRoom();return;}
  if(!supabase||!user?.id||!activeChannelId||activeChannelKind!=='voice'){vesselNotice('Сначала открой голосовой канал.','error');return;}
  if(voiceStream && voiceChannelId!==activeChannelId){await leaveVoiceRoom();}""",
'voice room switching')

replace_once(
"""<button id=\"join-voice\" class=\"join-voice ${activeChannelKind==='voice'?'':'hidden'}\">${voiceStream?'Выйти':'Войти'}</button>""",
"""<button id=\"join-voice\" class=\"join-voice ${activeChannelKind==='voice'?'':'hidden'}\">${voiceStream?(voiceChannelId===activeChannelId?'Выйти':'Переключиться'):'Войти'}</button>""",
'voice header action')

replace_once(
"voiceButton.classList.remove('hidden');voiceButton.textContent=voiceStream?'Выйти':'Подключиться';voiceButton.onclick=()=>toggleVoiceRoom(user);",
"voiceButton.classList.remove('hidden');voiceButton.textContent=voiceStream?(voiceChannelId===activeChannelId?'Выйти':'Переключиться'):'Подключиться';voiceButton.onclick=()=>toggleVoiceRoom(user);",
'voice channel action')

replace_once(
"if(voiceStream){muteButton.classList.remove('hidden');muteButton.onclick=toggleVoiceMicrophone;}else muteButton.classList.add('hidden');",
"if(voiceStream&&voiceChannelId===activeChannelId){muteButton.classList.remove('hidden');muteButton.onclick=toggleVoiceMicrophone;}else muteButton.classList.add('hidden');",
'voice mute visibility')

# Calls should only be offered inside a real direct message. During a call the hangup controls stay visible.
replace_once(
"""  const callActions=callInProgress
    ? `<button id=\"toggle-call-mic\" class=\"call-control\" title=\"${callMicEnabled?'Выключить микрофон':'Включить микрофон'}\">${callMicEnabled?'🎙':'🔇'}</button>${callVideo?`<button id=\"toggle-call-camera\" class=\"call-control\" title=\"${callCameraEnabled?'Выключить камеру':'Включить камеру'}\">${callCameraEnabled?'📷':'🚫'}</button>`:''}<button id=\"end-call\" class=\"hangup\" title=\"Завершить звонок\">☎</button>`
    : `<button id=\"audio-call\" title=\"Аудиозвонок\">📞</button><button id=\"video-call\" title=\"Видеозвонок\">🎥</button>`;""",
"""  const callActions=callInProgress
    ? `<button id=\"toggle-call-mic\" class=\"call-control\" title=\"${callMicEnabled?'Выключить микрофон':'Включить микрофон'}\">${callMicEnabled?'🎙':'🔇'}</button>${callVideo?`<button id=\"toggle-call-camera\" class=\"call-control\" title=\"${callCameraEnabled?'Выключить камеру':'Включить камеру'}\">${callCameraEnabled?'📷':'🚫'}</button>`:''}<button id=\"end-call\" class=\"hangup\" title=\"Завершить звонок\">☎</button>`
    : activeDmId ? `<button id=\"audio-call\" title=\"Аудиозвонок\">📞</button><button id=\"video-call\" title=\"Видеозвонок\">🎥</button>` : '';""",
'call action visibility')

# Add a reusable in-app list panel for message search and notifications.
replace_once(
"""function attachmentMarkup(attachments=[]) {""",
"""function vesselListDialog(title,items=[],emptyText='Ничего нет') {
  const overlay=document.createElement('div');
  overlay.className='modal vessel-dialog';
  const content=items.length?items.map(item=>`<div class=\"dialog-list-item\"><div><b>${escapeHtml(item.title||'')}</b>${item.meta?`<time>${escapeHtml(item.meta)}</time>`:''}</div><p>${escapeHtml(item.body||'')}</p></div>`).join(''):`<div class=\"dialog-empty\">${escapeHtml(emptyText)}</div>`;
  overlay.innerHTML=`<div class=\"modal-card dialog-card dialog-list-card\"><button class=\"modal-close\" data-dialog-close>×</button><h2>${escapeHtml(title)}</h2><div class=\"dialog-list\">${content}</div></div>`;
  document.body.appendChild(overlay);
  const close=()=>overlay.remove();
  overlay.querySelector('[data-dialog-close]').addEventListener('click',close);
  overlay.addEventListener('click',event=>{if(event.target===overlay)close();});
}
function attachmentMarkup(attachments=[]) {""",
'list dialog helper')

# Replace browser prompt/alert search with native Vessel UI and make it work for both channels and DMs.
replace_once(
"""  document.querySelector('#search-button').addEventListener('click', () => { const query=prompt('Поиск по сообщениям:'); if(query){ const found=messages.filter(m=>m.text.toLowerCase().includes(query.toLowerCase())); alert(found.length ? `Найдено сообщений: ${found.length}\\n\\n${found.map(m=>m.name+': '+m.text).join('\\n')}` : 'Ничего не найдено'); }});""",
"""  document.querySelector('#search-button').addEventListener('click', async () => {
    const query=await vesselPrompt('Поиск по сообщениям','','Что найти?');
    if(!query?.trim())return;
    const source=activeDmId?dmMessages:messages;
    const needle=query.trim().toLowerCase();
    const found=source.filter(message=>(message.text||'').toLowerCase().includes(needle)).slice(-50).reverse();
    vesselListDialog(`Поиск: ${query.trim()}`,found.map(message=>({title:message.name,body:message.text,meta:message.time})), 'Совпадений не найдено');
  });""",
'message search UI')

replace_once(
"""  document.querySelector('#notifications').addEventListener('click', async () => { const unread=notifications.filter(n=>!n.read_at); if(!unread.length){alert('Новых уведомлений нет.');return;} alert(unread.map(n=>`${n.title}\\n${n.body}`).join('\\n\\n')); if(supabase&&user.id) await supabase.from('notifications').update({read_at:new Date().toISOString()}).eq('user_id',user.id).is('read_at',null); notifications=notifications.map(n=>({...n,read_at:n.read_at||new Date().toISOString()})); render(); });""",
"""  document.querySelector('#notifications').addEventListener('click', async () => {
    vesselListDialog('Уведомления',notifications.map(item=>({title:item.title||'Vessel',body:item.body||'',meta:item.created_at?new Date(item.created_at).toLocaleString('ru-RU'):''})), 'Уведомлений пока нет');
    const unread=notifications.filter(item=>!item.read_at);
    if(unread.length&&supabase&&user.id){
      await supabase.from('notifications').update({read_at:new Date().toISOString()}).eq('user_id',user.id).is('read_at',null);
      notifications=notifications.map(item=>({...item,read_at:item.read_at||new Date().toISOString()}));
      render();
    }
  });""",
'notifications UI')

# Turn the previously dead smile button into a small native emoji picker.
replace_once(
"""<button type=\"button\">☺</button><button type=\"submit\" class=\"send\">➤</button>""",
"""<button type=\"button\" id=\"emoji-button\" title=\"Эмодзи\">☺</button><button type=\"submit\" class=\"send\">➤</button>""",
'emoji button id')

replace_once(
"""  document.querySelector('.attach').addEventListener('click', () => {""",
"""  document.querySelector('#emoji-button')?.addEventListener('click',async()=>{
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
  document.querySelector('.attach').addEventListener('click', () => {""",
'emoji handler')

# Improve common file/attachment errors without browser alerts.
text = text.replace("if(error||!data?.signedUrl){alert('Не удалось открыть файл.');return;}", "if(error||!data?.signedUrl){vesselNotice('Не удалось открыть файл.','error');return;}")
text = text.replace("if (!supabase || !user?.id) { alert('Для загрузки файлов нужен настоящий аккаунт.'); return null; }", "if (!supabase || !user?.id) { vesselNotice('Для загрузки файлов нужен настоящий аккаунт.','error'); return null; }")
text = text.replace("if(error){alert(`Файл не загрузился: ${error.message}`);return null;}", "if(error){vesselNotice(`Файл не загрузился: ${error.message}`,'error');return null;}")

# Do not show an endless loading state when there is no selected server or the roster loaded empty.
replace_once(
"""    : `<div class=\"members-title\">УЧАСТНИКИ</div><div class=\"dm-empty\">Список загружается…</div>`;""",
"""    : `<div class=\"members-title\">УЧАСТНИКИ</div><div class=\"dm-empty\">${!activeServer?.dbId?'Выбери или создай сервер.':window.__vesselMembersServerId===activeServer.dbId?'На сервере пока нет участников.':'Список загружается…'}</div>`;""",
'member empty state')

# Mobile navigation: channels become a slide-out drawer instead of disappearing completely.
replace_once(
"""<div class=\"head-actions\">${canManageChannel?""",
"""<div class=\"head-actions\"><button id=\"mobile-nav\" title=\"Каналы\">☰</button>${canManageChannel?""",
'mobile nav button')

replace_once(
"""  document.querySelector('#profile-settings').addEventListener('click', () => modal.classList.remove('hidden'));""",
"""  document.querySelector('#profile-settings').addEventListener('click', () => modal.classList.remove('hidden'));
  document.querySelector('#mobile-nav')?.addEventListener('click',()=>document.querySelector('.channels')?.classList.toggle('mobile-open'));""",
'mobile nav handler')

replace_once(
"""    if (!isDm && channel.dataset.channelId) loadChannelMessages(channel.dataset.channelId);""",
"""    document.querySelector('.channels')?.classList.remove('mobile-open');
    if (!isDm && channel.dataset.channelId) loadChannelMessages(channel.dataset.channelId);""",
'close mobile drawer after channel select')

# A little polish for the new native panels and the mobile channel drawer.
css += r'''
.dialog-list-card{width:min(560px,100%);max-height:min(76vh,680px);display:flex;flex-direction:column}.dialog-list{overflow:auto;margin-top:14px;display:grid;gap:8px}.dialog-list-item{background:#232837;border:1px solid #353c50;border-radius:11px;padding:11px 12px}.dialog-list-item>div{display:flex;align-items:baseline;justify-content:space-between;gap:12px}.dialog-list-item b{color:#eef0f7}.dialog-list-item time{color:#747c91;font-size:10px;white-space:nowrap}.dialog-list-item p{margin:6px 0 0;color:#b8bed0;white-space:pre-wrap;overflow-wrap:anywhere}.dialog-empty{padding:24px 10px;text-align:center;color:#777f93}#mobile-nav{display:none!important}
@media(max-width:600px){.channels{display:block!important;position:fixed;left:56px;top:0;bottom:0;width:min(290px,calc(100vw - 56px));z-index:30;transform:translateX(-110%);transition:transform .2s ease;box-shadow:18px 0 55px #0009}.channels.mobile-open{transform:translateX(0)}#mobile-nav{display:inline-grid!important;place-items:center}.dialog-list-item>div{align-items:flex-start;flex-direction:column;gap:3px}.dialog-list-item time{white-space:normal}}
'''

main_path.write_text(text, encoding='utf-8')
css_path.write_text(css, encoding='utf-8')
print('Applied Vessel voice, search, notifications, emoji and mobile UX patch')
