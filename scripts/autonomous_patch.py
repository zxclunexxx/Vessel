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

# Consistent user status labels in profile, friends and server roster.
replace_once(
"""function vesselDialog({title,message='',input=false,value='',placeholder='',choices=[]}) {""",
"""function statusLabel(value='online') {
  const key=String(value||'online').toLowerCase();
  if(['dnd','не беспокоить'].includes(key))return 'Не беспокоить';
  if(['away','idle','отошёл'].includes(key))return 'Отошёл';
  return 'В сети';
}
function vesselDialog({title,message='',input=false,value='',placeholder='',choices=[]}) {""",
'status helper')

text = text.replace("member.role==='moderator'?'Модератор':escapeHtml(member.status)", "member.role==='moderator'?'Модератор':escapeHtml(statusLabel(member.status))")
text = text.replace("<span>${friend.status||'в сети'}</span>", "<span>${escapeHtml(statusLabel(friend.status))}</span>")
text = text.replace("<div><b>${user.name}</b><small>в сети</small></div>", "<div><b>${escapeHtml(user.name)}</b><small>${escapeHtml(statusLabel(user.status))}</small></div>")

# Correct profile status values and preserve the selected state.
replace_once(
"""<label>Статус<select name=\"status\"><option>В сети</option><option>Не беспокоить</option><option>Отошёл</option></select></label>""",
"""<label>Статус<select name=\"status\"><option value=\"online\" ${['online','В сети'].includes(user.status)?'selected':''}>В сети</option><option value=\"dnd\" ${['dnd','Не беспокоить'].includes(user.status)?'selected':''}>Не беспокоить</option><option value=\"away\" ${['away','Отошёл'].includes(user.status)?'selected':''}>Отошёл</option></select></label>""",
'profile status select')

replace_once(
"""  document.querySelector('#settings-form').addEventListener('submit', async e => { e.preventDefault(); const data=new FormData(e.currentTarget); const name=data.get('name').trim(); const status=data.get('status'); if(supabase&&user.id){const {error}=await supabase.from('profiles').update({username:name,status}).eq('id',user.id);if(error){alert('Не удалось сохранить профиль.');return;}} localStorage.setItem('vesselUser', JSON.stringify({...user,name,status})); location.reload(); });""",
"""  document.querySelector('#settings-form').addEventListener('submit', async e => {
    e.preventDefault();
    const data=new FormData(e.currentTarget);
    const name=String(data.get('name')||'').trim();
    const status=String(data.get('status')||'online');
    if(!name)return;
    if(!supabase||!user.id){vesselNotice('Сессия Vessel недоступна.','error');return;}
    const {error}=await supabase.from('profiles').update({username:name,status}).eq('id',user.id);
    if(error){vesselNotice('Не удалось сохранить профиль.','error');return;}
    savedUser={...user,name,status};
    localStorage.setItem('vesselUser',JSON.stringify(savedUser));
    modal.classList.add('hidden');
    vesselNotice('Профиль сохранён.','success');
    render();
  });""",
'profile save flow')

# Realtime: reload full channel messages so remote messages have real author data and attachments.
replace_once(
"""    supabase.channel(`vessel-channel-messages-${user.id}`).on('postgres_changes',{event:'INSERT',schema:'public',table:'messages'},payload=>{
      if(payload.new.channel_id===activeChannelId && payload.new.author_id!==user.id){messages.push({name:'Участник',time:'только что',color:'#8b7cff',text:payload.new.body});render();}
    }).subscribe(),""",
"""    supabase.channel(`vessel-channel-messages-${user.id}`).on('postgres_changes',{event:'INSERT',schema:'public',table:'messages'},payload=>{
      if(payload.new.channel_id===activeChannelId && payload.new.author_id!==user.id)loadChannelMessages(activeChannelId).catch(error=>console.warn('Message refresh failed',error));
    }).subscribe(),""",
'channel realtime refresh')

# Realtime membership/channel/roster updates: users see kicks, joins and newly-created channels without reloads.
replace_once(
"""    supabase.channel(`vessel-friendships-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'friendships',filter:`user_id=eq.${user.id}`},()=>{window.__vesselSocialLoaded=false;syncSocial(user);}).subscribe(),
    supabase.channel(`vessel-channel-messages-${user.id}`)""",
"""    supabase.channel(`vessel-friendships-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'friendships',filter:`user_id=eq.${user.id}`},()=>{window.__vesselSocialLoaded=false;syncSocial(user);}).subscribe(),
    supabase.channel(`vessel-memberships-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'server_members'},payload=>{
      const row=payload.new?.server_id?payload.new:payload.old;
      if(!row)return;
      if(row.user_id===user.id){
        window.__vesselServersLoaded=false;
        syncSupabaseServers(user).then(()=>{
          if(activeServerIndex>=Math.max(servers.length-1,1))activeServerIndex=0;
          const active=servers[activeServerIndex];
          serverMembers=[];window.__vesselMembersServerId=null;
          if(active?.dbId){active.__channelsLoaded=false;syncSupabaseChannels(active);syncServerMembers(user,active);}else render();
        });
      }else{
        const active=servers[activeServerIndex];
        if(active?.dbId===row.server_id){window.__vesselMembersServerId=null;serverMembers=[];syncServerMembers(user,active);}
      }
    }).subscribe(),
    supabase.channel(`vessel-channels-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'channels'},payload=>{
      const row=payload.new?.server_id?payload.new:payload.old;
      const active=servers[activeServerIndex];
      if(row?.server_id&&active?.dbId===row.server_id){active.__channelsLoaded=false;syncSupabaseChannels(active);}
    }).subscribe(),
    supabase.channel(`vessel-channel-messages-${user.id}`)""",
'realtime membership subscriptions')

# Show the voice mute control only for the room the user is actually connected to.
text = text.replace("class=\"join-voice ${voiceStream?'':'hidden'}\"", "class=\"join-voice ${voiceStream&&voiceChannelId===activeChannelId?'':'hidden'}\"")

# Outgoing calls now time out instead of leaving a stuck ringing state forever.
replace_once(
"""let callCameraEnabled = true;""",
"""let callCameraEnabled = true;
let callInviteTimer = null;""",
'call timeout state')

replace_once(
"""    if (payload.type === 'accept') {
      callAccepted = true;""",
"""    if (payload.type === 'accept') {
      if(callInviteTimer){clearTimeout(callInviteTimer);callInviteTimer=null;}
      callAccepted = true;""",
'call accept timeout cleanup')

replace_once(
"""    await sendCallInvite(user,activeDmId,{type:'invite',name:user.name,video:callVideo,offer:callOffer});
    render();""",
"""    await sendCallInvite(user,activeDmId,{type:'invite',name:user.name,video:callVideo,offer:callOffer});
    if(callInviteTimer)clearTimeout(callInviteTimer);
    callInviteTimer=setTimeout(()=>{
      if(callConnection&&!callAccepted){vesselNotice('Пользователь не ответил на звонок.');endCall(true);}
    },30000);
    render();""",
'outgoing call timeout')

replace_once(
"""  callAccepted=false;
  callMicEnabled=true;""",
"""  callAccepted=false;
  if(callInviteTimer){clearTimeout(callInviteTimer);callInviteTimer=null;}
  callMicEnabled=true;""",
'end call timeout cleanup')

# Replace common call errors with non-blocking Vessel notifications.
text = text.replace("alert('Открой личный чат с настоящим другом, чтобы начать звонок.');", "vesselNotice('Открой личный чат с настоящим другом, чтобы начать звонок.','error');")
text = text.replace("alert('Не удалось получить доступ к микрофону или камере.');", "vesselNotice('Не удалось получить доступ к микрофону или камере.','error');")
text = text.replace("alert(payload.type === 'busy' ? 'Пользователь уже разговаривает.' : 'Вызов отклонён.');", "vesselNotice(payload.type === 'busy' ? 'Пользователь уже разговаривает.' : 'Вызов отклонён.',payload.type==='busy'?'info':'error');")
text = text.replace("alert('Разреши Vessel доступ к микрофону.');", "vesselNotice('Разреши Vessel доступ к микрофону.','error');")

# Message composer errors and friend request actions should not use blocking browser alerts.
text = text.replace("alert('Нужна активная сессия Vessel.');", "vesselNotice('Нужна активная сессия Vessel.','error');")
text = text.replace("alert('Сначала выбери текстовый канал.');", "vesselNotice('Сначала выбери текстовый канал.','error');")
text = text.replace("alert(`Не удалось отправить личное сообщение: ${error.message}`);", "vesselNotice(`Не удалось отправить личное сообщение: ${error.message}`,'error');")
text = text.replace("alert(`Не удалось отправить сообщение: ${error.message}`);", "vesselNotice(`Не удалось отправить сообщение: ${error.message}`,'error');")
text = text.replace("alert(`Не удалось удалить друга: ${error.message}`);", "vesselNotice(`Не удалось удалить друга: ${error.message}`,'error');")
text = text.replace("if(error){alert('Не удалось принять заявку.');return;}", "if(error){vesselNotice('Не удалось принять заявку.','error');return;}else vesselNotice('Заявка принята.','success');")
text = text.replace("if(error){alert('Не удалось отклонить заявку.');return;}", "if(error){vesselNotice('Не удалось отклонить заявку.','error');return;}else vesselNotice('Заявка отклонена.');")

# Native invite-code dialog with one-click copy.
replace_once(
"""function attachmentMarkup(attachments=[]) {""",
"""function vesselCodeDialog(title,code) {
  const overlay=document.createElement('div');
  overlay.className='modal vessel-dialog';
  overlay.innerHTML=`<div class=\"modal-card dialog-card\"><button class=\"modal-close\" data-code-close>×</button><h2>${escapeHtml(title)}</h2><p>Передай этот код человеку, которого хочешь пригласить.</p><div class=\"invite-code\">${escapeHtml(code)}</div><button class=\"primary\" type=\"button\" data-code-copy>Скопировать код</button></div>`;
  document.body.appendChild(overlay);
  const close=()=>overlay.remove();
  overlay.querySelector('[data-code-close]').addEventListener('click',close);
  overlay.addEventListener('click',event=>{if(event.target===overlay)close();});
  overlay.querySelector('[data-code-copy]').addEventListener('click',async()=>{
    try{await navigator.clipboard.writeText(code);vesselNotice('Код приглашения скопирован.','success');}
    catch{vesselNotice('Не удалось скопировать код. Выдели его вручную.','error');}
  });
}
function attachmentMarkup(attachments=[]) {""",
'invite code dialog helper')

replace_once(
"""        alert(error?`Не удалось создать приглашение: ${error.message}`:`Код приглашения для сервера «${server.name}»:\\n\\n${code}\\n\\nПередай его другу.`);""",
"""        if(error)vesselNotice(`Не удалось создать приглашение: ${error.message}`,'error');else vesselCodeDialog(`Приглашение в ${server.name}`,code);""",
'invite code UI')

# A few remaining frequent server/channel errors become Vessel toasts.
for old,new in [
    ("alert('Сначала выбери сервер.');","vesselNotice('Сначала выбери сервер.','error');"),
    ("alert('Сначала выбери настоящий сервер.');","vesselNotice('Сначала выбери настоящий сервер.','error');"),
    ("alert('Создавать каналы может только владелец сервера.');","vesselNotice('Создавать каналы может только владелец сервера.','error');"),
    ("alert('Нужна активная сессия Vessel.');","vesselNotice('Нужна активная сессия Vessel.','error');"),
]:
    text=text.replace(old,new)

css += r'''
.invite-code{margin:14px 0;background:#10131b;border:1px solid #414960;border-radius:11px;padding:15px;text-align:center;font:800 18px ui-monospace,SFMono-Regular,Consolas,monospace;letter-spacing:.08em;color:#b8b1ff;user-select:all}.settings-saving{opacity:.7;pointer-events:none}
'''

main_path.write_text(text, encoding='utf-8')
css_path.write_text(css, encoding='utf-8')
print('Applied Vessel realtime, profile, invite and call-state patch')
