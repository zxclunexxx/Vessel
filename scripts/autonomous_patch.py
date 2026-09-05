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

# No fake-looking default channel while real server data is loading or absent.
text = text.replace("let activeChannelName = 'общий';", "let activeChannelName = 'нет каналов';", 1)
text = text.replace("activeChannelName='общий';activeChannelKind='text';activeChannelId=null;", "activeChannelName='загрузка…';activeChannelKind='text';activeChannelId=null;", 1)

# When there are no servers, explicitly clear channel state instead of leaving stale labels/data.
replace_once(
"""  servers=[...all.map(s=>({id:s.id,dbId:s.id,icon:s.icon,name:s.name,role:s.owner_id===user.id?'owner':(memberships||[]).find(m=>m.server_id===s.id)?.role||'member'})),{id:'add-server',icon:'+',name:'Добавить сервер',add:true}];
  if(activeServerIndex>=Math.max(servers.length-1,1)) activeServerIndex=0;
  render();""",
"""  servers=[...all.map(s=>({id:s.id,dbId:s.id,icon:s.icon,name:s.name,role:s.owner_id===user.id?'owner':(memberships||[]).find(m=>m.server_id===s.id)?.role||'member'})),{id:'add-server',icon:'+',name:'Добавить сервер',add:true}];
  if(activeServerIndex>=Math.max(servers.length-1,1)) activeServerIndex=0;
  if(!all.length){activeChannelId=null;activeChannelName='нет каналов';activeChannelKind='text';messages=[];serverMembers=[];}
  render();""",
'empty server state')

# Load newest messages, not the oldest first 100; present them chronologically.
replace_once(
"""  const {data} = await supabase.from('messages').select('body,attachments,created_at,profiles(username,avatar_color)').eq('channel_id',channelId).order('created_at',{ascending:true}).limit(100);
  messages = data?.length ? data.map(m=>({name:m.profiles?.username||'Участник',time:new Date(m.created_at).toLocaleString('ru-RU'),color:m.profiles?.avatar_color||'#8b7cff',text:m.body,attachments:m.attachments||[]})) : [];""",
"""  const {data,error} = await supabase.from('messages').select('body,attachments,created_at,profiles(username,avatar_color)').eq('channel_id',channelId).order('created_at',{ascending:false}).limit(100);
  if(error){vesselNotice('Не удалось загрузить сообщения канала.','error');return;}
  messages = (data||[]).reverse().map(m=>({name:m.profiles?.username||'Участник',time:new Date(m.created_at).toLocaleString('ru-RU'),color:m.profiles?.avatar_color||'#8b7cff',text:m.body,attachments:m.attachments||[]}));""",
'channel message pagination')

replace_once(
"""  const {data} = await supabase.from('direct_messages').select('id,sender_id,receiver_id,body,attachments,created_at,profiles!direct_messages_sender_id_fkey(username,avatar_color)').or(`and(sender_id.eq.${user.id},receiver_id.eq.${friendId}),and(sender_id.eq.${friendId},receiver_id.eq.${user.id})`).order('created_at',{ascending:true});
  dmMessages = (data || []).map(row => ({name:row.profiles?.username || 'Пользователь',time:new Date(row.created_at).toLocaleString('ru-RU'),color:row.profiles?.avatar_color || '#8b7cff',text:row.body,attachments:row.attachments||[]}));""",
"""  const {data,error} = await supabase.from('direct_messages').select('id,sender_id,receiver_id,body,attachments,created_at,profiles!direct_messages_sender_id_fkey(username,avatar_color)').or(`and(sender_id.eq.${user.id},receiver_id.eq.${friendId}),and(sender_id.eq.${friendId},receiver_id.eq.${user.id})`).order('created_at',{ascending:false}).limit(100);
  if(error){vesselNotice('Не удалось загрузить личные сообщения.','error');return;}
  dmMessages = (data || []).reverse().map(row => ({name:row.profiles?.username || 'Пользователь',time:new Date(row.created_at).toLocaleString('ru-RU'),color:row.profiles?.avatar_color || '#8b7cff',text:row.body,attachments:row.attachments||[]}));""",
'dm pagination')

# Avoid optimistic/realtime race duplicates in DMs: after DB success reload authoritative history.
replace_once(
"""if(activeDmId){ const {error}=await supabase.from('direct_messages').insert({sender_id:user.id,receiver_id:activeDmId,body:text}); if(error){vesselNotice(`Не удалось отправить личное сообщение: ${error.message}`,'error');return;} dmMessages.push({name:user.name,time:'только что',color:user.avatarColor||'#39d9a6',text}); }""",
"""if(activeDmId){ const peerId=activeDmId; const {error}=await supabase.from('direct_messages').insert({sender_id:user.id,receiver_id:peerId,body:text}); if(error){vesselNotice(`Не удалось отправить личное сообщение: ${error.message}`,'error');return;} await loadDirectMessages(user,peerId); }""",
'dm send authoritative reload')

replace_once(
"""        const {error}=await supabase.from('direct_messages').insert({sender_id:user.id,receiver_id:activeDmId,body,attachments:[attachment]});
        if(error){alert(`Не удалось отправить файл: ${error.message}`);return;}
        dmMessages.push({name:user.name,time:'только что',color:user.avatarColor||'#39d9a6',text:body,attachments:[attachment]});""",
"""        const peerId=activeDmId;
        const {error}=await supabase.from('direct_messages').insert({sender_id:user.id,receiver_id:peerId,body,attachments:[attachment]});
        if(error){vesselNotice(`Не удалось отправить файл: ${error.message}`,'error');return;}
        await loadDirectMessages(user,peerId);""",
'dm attachment authoritative reload')

# Remove all remaining blocking prototype browser alerts from normal flows.
replacements = {
"if (!supabase || !user?.id) { alert('Для вступления нужен настоящий аккаунт.'); return false; }":"if (!supabase || !user?.id) { vesselNotice('Для вступления нужен настоящий аккаунт.','error'); return false; }",
"    alert(message);":"    vesselNotice(message,'error');",
"  if(!data?.ok){alert(data?.error||'Не удалось вступить в сервер.');return false;}":"  if(!data?.ok){vesselNotice(data?.error||'Не удалось вступить в сервер.','error');return false;}",
"      if (!supabase) { alert('Сервис авторизации временно недоступен.'); return; }":"      if (!supabase) { vesselNotice('Сервис авторизации временно недоступен.','error'); return; }",
"          alert('Аккаунт создан. Если подтверждение почты включено, открой письмо от Vessel, а затем войди.');":"          vesselNotice('Аккаунт создан. Если подтверждение почты включено, открой письмо от Vessel, а затем войди.','success');",
"        alert(error?.message || 'Не удалось выполнить авторизацию.');":"        vesselNotice(error?.message || 'Не удалось выполнить авторизацию.','error');",
"        if(!activeChannelId||activeChannelKind!=='text'){alert('Открой текстовый канал или личный чат.');return;}":"        if(!activeChannelId||activeChannelKind!=='text'){vesselNotice('Открой текстовый канал или личный чат.','error');return;}",
"        if(error){alert(`Не удалось отправить файл: ${error.message}`);return;}":"        if(error){vesselNotice(`Не удалось отправить файл: ${error.message}`,'error');return;}",
"        if(error){alert(`Не удалось переименовать сервер: ${error.message}`);return;}":"        if(error){vesselNotice(`Не удалось переименовать сервер: ${error.message}`,'error');return;}",
"        if(error){alert(`Не удалось удалить сервер: ${error.message}`);return;}":"        if(error){vesselNotice(`Не удалось удалить сервер: ${error.message}`,'error');return;}",
"      if(error){alert(`Не удалось выйти из сервера: ${error.message}`);return;}":"      if(error){vesselNotice(`Не удалось выйти из сервера: ${error.message}`,'error');return;}",
"    if(error){alert(`Не удалось создать канал: ${error.message}`);return;}":"    if(error){vesselNotice(`Не удалось создать канал: ${error.message}`,'error');return;}",
"      if(error){alert(`Не удалось переименовать канал: ${error.message}`);return;}":"      if(error){vesselNotice(`Не удалось переименовать канал: ${error.message}`,'error');return;}",
"      if(error){alert(`Не удалось удалить канал: ${error.message}`);return;}":"      if(error){vesselNotice(`Не удалось удалить канал: ${error.message}`,'error');return;}",
"      if(error){alert(`Не удалось изменить роль: ${error.message}`);return;}":"      if(error){vesselNotice(`Не удалось изменить роль: ${error.message}`,'error');return;}",
"      if(error){alert(`Не удалось исключить участника: ${error.message}`);return;}":"      if(error){vesselNotice(`Не удалось исключить участника: ${error.message}`,'error');return;}",
"        if(error){alert(`Не удалось создать сервер: ${error.message}`);return;}":"        if(error){vesselNotice(`Не удалось создать сервер: ${error.message}`,'error');return;}",
}
for old,new in replacements.items():
    if old in text:text=text.replace(old,new)

# Member management was the final direct prompt() left in the app.
replace_once(
"""    const action=prompt(`Участник ${member.username}:\n1 — сделать участником\n2 — сделать модератором\n3 — исключить из сервера`);""",
"""    const action=await vesselChoice(`Участник ${member.username}`,[{label:'Сделать участником',value:'1'},{label:'Сделать модератором',value:'2'},{label:'Исключить из сервера',value:'3',danger:true}]);""",
'member management dialog')

# Escape user-controlled values that still reached the big HTML template directly.
text = text.replace('title="${s.name}">${s.icon}</button>', 'title="${escapeHtml(s.name)}">${escapeHtml(s.icon)}</button>')
text = text.replace("${friendsOpen?'Друзья':servers[activeServerIndex]?.name || 'Vessel'}</span>", "${friendsOpen?'Друзья':escapeHtml(servers[activeServerIndex]?.name || 'Vessel')}</span>")
text = text.replace('${user.name[0].toUpperCase()}</div><div><b>${escapeHtml(user.name)}</b>', "${escapeHtml(user.name?.[0]?.toUpperCase()||'?')}</div><div><b>${escapeHtml(user.name)}</b>")
text = text.replace("${currentDm || activeChannelName}</h1>", "${escapeHtml(currentDm || activeChannelName)}</h1>")
text = text.replace("${currentDm?'Личная переписка':activeChannelKind==='voice'?'Голосовая комната':servers[activeServerIndex]?.name || 'Vessel'}</p>", "${currentDm?'Личная переписка':activeChannelKind==='voice'?'Голосовая комната':escapeHtml(servers[activeServerIndex]?.name || 'Vessel')}</p>")
text = text.replace("value=\"${user.name}\" required", "value=\"${escapeHtml(user.name)}\" required")
text = text.replace("${incomingCall.name[0]?.toUpperCase()||'?'}</div>", "${escapeHtml(incomingCall.name?.[0]?.toUpperCase()||'?')}</div>")
text = text.replace("<p>${incomingCall.name} звонит тебе в Vessel.</p>", "<p>${escapeHtml(incomingCall.name)} звонит тебе в Vessel.</p>")
text = text.replace("`Переписка с ${currentDm}`", "`Переписка с ${escapeHtml(currentDm)}`")
text = text.replace("`Добро пожаловать в ${activeChannelKind==='voice'?'':'#'}${activeChannelName}!`", "`Добро пожаловать в ${activeChannelKind==='voice'?'':'#'}${escapeHtml(activeChannelName)}!`")
text = text.replace("placeholder=\"${currentDm?`Написать пользователю ${currentDm}`:`Написать в #${activeChannelName}`}\"", "placeholder=\"${currentDm?`Написать пользователю ${escapeHtml(currentDm)}`:`Написать в #${escapeHtml(activeChannelName)}`}\"")

# If the last real server disappeared, don't leave the add-server tile selected as if it were a server.
text = text.replace("const activeServer=servers[activeServerIndex];", "const activeServer=servers[activeServerIndex]?.add?null:servers[activeServerIndex];", 1)

css += r'''
.empty-state{color:#7f879b;line-height:1.6}.channel-section:has(.dm-empty){min-height:54px}
'''

# Guardrails: this patch intentionally removes the rough native browser dialogs.
if 'prompt(' in text:
    raise SystemExit('A browser prompt() remains after UX cleanup')
if 'confirm(' in text:
    raise SystemExit('A browser confirm() remains after UX cleanup')

main_path.write_text(text, encoding='utf-8')
css_path.write_text(css, encoding='utf-8')
print('Applied Vessel data-flow, escaping and remaining UX cleanup')
