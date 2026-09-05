from pathlib import Path

path = Path('src/main.js')
text = path.read_text(encoding='utf-8')


def replace(old, new, label):
    global text
    if old not in text:
        raise SystemExit(f'Missing patch target: {label}')
    text = text.replace(old, new, 1)

replace(
"let notifications = [];\nconst savedChannelMap",
"let notifications = [];\nlet serverMembers = [];\nconst savedChannelMap",
"server members state",
)

replace(
"async function syncSocial(user) {",
"""async function syncServerMembers(user, server) {
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

async function syncSocial(user) {""",
"social helpers",
)

replace(
"""  const {data: links} = await supabase.from('friendships').select('friend_id').eq('user_id', user.id);
  const ids = (links || []).map(row => row.friend_id).filter(Boolean);
  if (ids.length) {
    const {data: profiles} = await supabase.from('profiles').select('id,username,avatar_color,status').in('id', ids);
    friends = profiles || [];
  }""",
"""  const {data: links} = await supabase.from('friendships').select('friend_id').eq('user_id', user.id);
  const ids = (links || []).map(row => row.friend_id).filter(Boolean);
  friends = [];
  if (ids.length) {
    const {data: profiles} = await supabase.from('profiles').select('id,username,avatar_color,status').in('id', ids);
    friends = profiles || [];
  }""",
"reset friends",
)

replace(
"connectRealtime(); connectSupabaseRealtime(user); ensureCallInbox(user).catch(()=>{}); syncSupabaseMessages(); syncSupabaseServers(user); syncSupabaseChannels(servers[activeServerIndex]); syncSocial(user); syncNotifications(user);",
"connectRealtime(); connectSupabaseRealtime(user); ensureCallInbox(user).catch(()=>{}); syncSupabaseMessages(); syncSupabaseServers(user); syncSupabaseChannels(servers[activeServerIndex]); syncServerMembers(user,servers[activeServerIndex]); syncSocial(user); syncNotifications(user);",
"sync server members during render",
)

replace(
"""  const dmList=friends.length
    ? friends.map(friend=>`<button class=\"channel dm ${activeDmId===friend.id?'active':''}\" data-dm-id=\"${friend.id}\" data-dm=\"${friend.username}\"><div class=\"mini-avatar\" style=\"background:${friend.avatar_color||'#8b7cff'}\">${(friend.username||'?')[0].toUpperCase()}</div> ${friend.username} <em></em></button>`).join('')
    : `<button class=\"channel dm\" data-dm=\"Марк\"><div class=\"mini-avatar\" style=\"background:#8b7cff\">М</div> Марк <em></em></button><button class=\"channel dm\" data-dm=\"Лиза\"><div class=\"mini-avatar\" style=\"background:#ff7294\">Л</div> Лиза <em></em></button>`;""",
"""  const dmList=friends.length
    ? friends.map(friend=>`<button class=\"channel dm ${activeDmId===friend.id?'active':''}\" data-dm-id=\"${friend.id}\" data-dm=\"${friend.username}\"><div class=\"mini-avatar\" style=\"background:${friend.avatar_color||'#8b7cff'}\">${(friend.username||'?')[0].toUpperCase()}</div> ${friend.username} <em></em></button>`).join('')
    : `<div class=\"dm-empty\">Пока нет личных чатов</div>`;
  const membersList=serverMembers.length
    ? `<div class=\"members-title\">УЧАСТНИКИ — ${serverMembers.length}</div>${serverMembers.map(member=>`<div class=\"member online\"><div class=\"avatar\" style=\"background:${member.avatar_color}\">${member.username[0]?.toUpperCase()||'?'}</div><span>${member.username}<small>${member.role==='owner'?'Создатель':member.status}</small></span><i></i></div>`).join('')}`
    : `<div class=\"members-title\">УЧАСТНИКИ</div><div class=\"dm-empty\">Список загружается…</div>`;""",
"dm and members lists",
)

replace(
"""      <aside class=\"members\">${voiceStream?'<div class=\"voice-status\">🎙 Ты в голосовой комнате</div>':''}<div class=\"members-title\">УЧАСТНИКИ — 3</div><div class=\"member online\"><div class=\"avatar\" style=\"background:#8b7cff\">М</div><span>Марк<small>Создатель</small></span><i></i></div><div class=\"member online\"><div class=\"avatar\" style=\"background:#ff7294\">Л</div><span>Лиза<small>Дизайнер</small></span><i></i></div><div class=\"member online\"><div class=\"avatar\" style=\"background:#39d9a6\">А</div><span>Артём<small>В сети</small></span><i></i></div></aside>""",
"""      <aside class=\"members\">${voiceStream?'<div class=\"voice-status\">🎙 Ты в голосовой комнате</div>':''}${membersList}</aside>""",
"real member sidebar",
)

replace(
"document.querySelector('#dm-add').addEventListener('click', () => { const name=prompt('Имя пользователя:'); if(name?.trim()){currentDm=name.trim();activeDmId=null;friendsOpen=false;render();} });",
"document.querySelector('#dm-add').addEventListener('click', () => findAndRequestFriend(user));",
"dm add",
)

replace(
"document.querySelectorAll('.channel').forEach(channel => channel.addEventListener('click', () => {",
"document.querySelectorAll('.channel:not(.dm)').forEach(channel => channel.addEventListener('click', () => {",
"separate dm channel clicks",
)

replace(
"""  document.querySelectorAll('[data-accept-request]').forEach(button=>button.addEventListener('click',async()=>{if(!supabase||!user.id)return;const sender=button.dataset.sender;await supabase.from('friend_requests').update({status:'accepted',updated_at:new Date().toISOString()}).eq('id',button.dataset.acceptRequest);await supabase.from('friendships').upsert([{user_id:user.id,friend_id:sender},{user_id:sender,friend_id:user.id}]);window.__vesselSocialLoaded=false;render();}));
  document.querySelector('#add-friend')?.addEventListener('click',async()=>{const query=prompt('Введи точное имя пользователя:');if(!query?.trim())return;if(!supabase||!user.id){alert('Войди через настоящий аккаунт, чтобы добавлять друзей.');return;}const {data:found}=await supabase.from('profiles').select('id,username').ilike('username',query.trim()).limit(1);if(!found?.[0]){alert('Пользователь не найден.');return;}if(found[0].id===user.id){alert('Нельзя добавить самого себя.');return;}const {error}=await supabase.from('friend_requests').upsert({sender_id:user.id,receiver_id:found[0].id,status:'pending'},{onConflict:'sender_id,receiver_id'});alert(error?'Не удалось отправить заявку.':`Заявка пользователю ${found[0].username} отправлена.`);});""",
"""  document.querySelectorAll('[data-accept-request]').forEach(button=>button.addEventListener('click',async()=>{if(!supabase||!user.id)return;const {error}=await supabase.from('friend_requests').update({status:'accepted',updated_at:new Date().toISOString()}).eq('id',button.dataset.acceptRequest).eq('receiver_id',user.id);if(error){alert('Не удалось принять заявку.');return;}window.__vesselSocialLoaded=false;await syncSocial(user);render();}));
  document.querySelector('#add-friend')?.addEventListener('click',()=>findAndRequestFriend(user));""",
"friend actions",
)

replace(
"""  document.querySelector('#settings-form').addEventListener('submit', e => { e.preventDefault(); const data=new FormData(e.currentTarget); localStorage.setItem('vesselUser', JSON.stringify({name:data.get('name'),email:user.email,status:data.get('status')})); location.reload(); });
  document.querySelector('#logout').addEventListener('click', () => { localStorage.removeItem('vesselUser'); location.reload(); });""",
"""  document.querySelector('#settings-form').addEventListener('submit', async e => { e.preventDefault(); const data=new FormData(e.currentTarget); const name=data.get('name').trim(); const status=data.get('status'); if(supabase&&user.id){const {error}=await supabase.from('profiles').update({username:name,status}).eq('id',user.id);if(error){alert('Не удалось сохранить профиль.');return;}} localStorage.setItem('vesselUser', JSON.stringify({...user,name,status})); location.reload(); });
  document.querySelector('#logout').addEventListener('click', async () => { if(supabase) await supabase.auth.signOut().catch(()=>{}); localStorage.removeItem('vesselUser'); localStorage.removeItem('vesselToken'); location.reload(); });""",
"profile save and logout",
)

replace(
"activeServerIndex=Number(server.dataset.serverIndex);localStorage.setItem('vesselActiveServer',activeServerIndex);activeChannelName='общий';activeChannelKind='text';activeChannelId=null;currentDm=null;friendsOpen=false;render();syncSupabaseChannels(servers[activeServerIndex]);",
"activeServerIndex=Number(server.dataset.serverIndex);localStorage.setItem('vesselActiveServer',activeServerIndex);activeChannelName='общий';activeChannelKind='text';activeChannelId=null;currentDm=null;activeDmId=null;friendsOpen=false;serverMembers=[];window.__vesselMembersServerId=null;render();syncSupabaseChannels(servers[activeServerIndex]);syncServerMembers(user,servers[activeServerIndex]);",
"server switching",
)

path.write_text(text, encoding='utf-8')
print('Vessel social upgrade applied')
