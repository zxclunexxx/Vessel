from pathlib import Path

path = Path('src/main.js')
text = path.read_text(encoding='utf-8')

old = """  const callInProgress=Boolean(callConnection||callStream);
  const callActions=callInProgress"""
new = """  const callInProgress=Boolean(callConnection||callStream);
  const activeServer=servers[activeServerIndex];
  const canManageChannel=Boolean(!currentDm&&activeChannelId&&activeServer?.dbId&&activeServer.role==='owner');
  const callActions=callInProgress"""
if old not in text:
    raise SystemExit('render call state anchor not found')
text = text.replace(old, new, 1)

old = '<div class="head-actions">${callActions}'
new = '<div class="head-actions">${canManageChannel?`<button id="channel-settings" title="Настройки канала">•••</button>`:\'\'}${callActions}'
if old not in text:
    raise SystemExit('head actions anchor not found')
text = text.replace(old, new, 1)

old = """  document.querySelector('.more').addEventListener('click', async () => { const server=servers[activeServerIndex]; if(!server?.dbId||server.role!=='owner'){alert(`Твоя роль: ${server?.role||'участник'}. Создавать приглашения может только владелец.`);return;} const code=`VSL-${crypto.randomUUID().slice(0,8).toUpperCase()}`; const {error}=await supabase.from('server_invites').insert({server_id:server.dbId,created_by:user.id,code}); alert(error?'Не удалось создать приглашение.':`Код приглашения для сервера «${server.name}»:\n\n${code}\n\nПередай его другу.`); });"""
new = """  document.querySelector('.more').addEventListener('click', async () => {
    const server=servers[activeServerIndex];
    if(!server?.dbId){alert('Сначала выбери сервер.');return;}
    if(server.role==='owner'){
      const action=prompt('Управление сервером:\n1 — создать приглашение\n2 — переименовать сервер\n3 — удалить сервер');
      if(action==='1'){
        const code=`VSL-${crypto.randomUUID().slice(0,8).toUpperCase()}`;
        const {error}=await supabase.from('server_invites').insert({server_id:server.dbId,created_by:user.id,code});
        alert(error?`Не удалось создать приглашение: ${error.message}`:`Код приглашения для сервера «${server.name}»:\n\n${code}\n\nПередай его другу.`);
        return;
      }
      if(action==='2'){
        const name=prompt('Новое название сервера:',server.name);
        if(!name?.trim()||name.trim()===server.name)return;
        const {error}=await supabase.from('servers').update({name:name.trim()}).eq('id',server.dbId).eq('owner_id',user.id);
        if(error){alert(`Не удалось переименовать сервер: ${error.message}`);return;}
        server.name=name.trim(); render(); return;
      }
      if(action==='3'){
        if(!confirm(`Удалить сервер «${server.name}» вместе с каналами и сообщениями?`))return;
        const {error}=await supabase.from('servers').delete().eq('id',server.dbId).eq('owner_id',user.id);
        if(error){alert(`Не удалось удалить сервер: ${error.message}`);return;}
        window.__vesselServersLoaded=false; activeServerIndex=0; activeChannelId=null; currentDm=null; activeDmId=null; messages=[]; serverMembers=[]; window.__vesselMembersServerId=null;
        await syncSupabaseServers(user); const next=servers[activeServerIndex]; if(next?.dbId){next.__channelsLoaded=false;await syncSupabaseChannels(next);await syncServerMembers(user,next);} else render();
        return;
      }
      return;
    }
    if(confirm(`Выйти из сервера «${server.name}»?`)){
      const {error}=await supabase.from('server_members').delete().eq('server_id',server.dbId).eq('user_id',user.id);
      if(error){alert(`Не удалось выйти из сервера: ${error.message}`);return;}
      window.__vesselServersLoaded=false; activeServerIndex=0; activeChannelId=null; currentDm=null; activeDmId=null; messages=[]; serverMembers=[]; window.__vesselMembersServerId=null;
      await syncSupabaseServers(user); const next=servers[activeServerIndex]; if(next?.dbId){next.__channelsLoaded=false;await syncSupabaseChannels(next);await syncServerMembers(user,next);} else render();
    }
  });"""
if old not in text:
    raise SystemExit('server menu listener not found')
text = text.replace(old, new, 1)

anchor = """  document.querySelector('#voice-add').addEventListener('click', () => addChannel('voice'));"""
addition = """  document.querySelector('#voice-add').addEventListener('click', () => addChannel('voice'));
  document.querySelector('#channel-settings')?.addEventListener('click',async()=>{
    const server=servers[activeServerIndex];
    if(!server?.dbId||server.role!=='owner'||!activeChannelId)return;
    const channel=serverChannels().find(item=>item.id===activeChannelId);
    if(!channel)return;
    const action=prompt(`Канал «${channel.name}»:\n1 — переименовать\n2 — удалить`);
    if(action==='1'){
      const name=prompt('Новое название канала:',channel.name);
      if(!name?.trim()||name.trim()===channel.name)return;
      const {error}=await supabase.from('channels').update({name:name.trim()}).eq('id',channel.id).eq('server_id',server.dbId);
      if(error){alert(`Не удалось переименовать канал: ${error.message}`);return;}
      activeChannelName=name.trim(); server.__channelsLoaded=false; await syncSupabaseChannels(server); activeChannelId=channel.id; activeChannelName=name.trim(); render();
      return;
    }
    if(action==='2'){
      if(!confirm(`Удалить канал «${channel.name}»?`))return;
      const {error}=await supabase.from('channels').delete().eq('id',channel.id).eq('server_id',server.dbId);
      if(error){alert(`Не удалось удалить канал: ${error.message}`);return;}
      activeChannelId=null; messages=[]; server.__channelsLoaded=false; await syncSupabaseChannels(server);
    }
  });"""
if anchor not in text:
    raise SystemExit('voice add listener anchor not found')
text = text.replace(anchor, addition, 1)

path.write_text(text, encoding='utf-8')
print('Applied server and channel management patch')
