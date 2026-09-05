from pathlib import Path

path=Path('src/main.js')
text=path.read_text(encoding='utf-8')

def replace_once(old,new,label):
    global text
    if old not in text:
        raise SystemExit(f'{label} anchor not found')
    text=text.replace(old,new,1)

# Realtime channel changes must resolve the active server by stable id.
text=text.replace("const active=servers[activeServerIndex];", "const active=getActiveServer();")

# Channel creation: normalize names, reject duplicates, and select the new channel BEFORE
# reloading the list so syncSupabaseChannels preserves the newly-created selection.
old="""    if(!name?.trim())return;
    const server=getActiveServer();
    if(!supabase||!user.id||!server?.dbId){vesselNotice('Сначала выбери настоящий сервер.','error');return;}
    if(server.role!=='owner'){vesselNotice('Создавать каналы может только владелец сервера.','error');return;}
    const position=serverChannels().length;
    const {data,error}=await supabase.from('channels').insert({server_id:server.dbId,name:name.trim(),kind,position}).select('id,name,kind,position').single();
    if(error){vesselNotice(`Не удалось создать канал: ${error.message}`,'error');return;}
    server.__channelsLoaded=false;
    await syncSupabaseChannels(server);
    activeChannelId=data.id; activeChannelName=data.name; activeChannelKind=data.kind; currentDm=null; activeDmId=null;
    if(kind==='text') await loadChannelMessages(data.id); else render();"""
new="""    const channelName=String(name||'').trim().replace(/\\s+/g,'-').replace(/-+/g,'-').slice(0,50);
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
    vesselNotice(`${kind==='voice'?'Голосовой':'Текстовый'} канал «${data.name}» создан.`,'success');"""
replace_once(old,new,'channel create lifecycle')

# Rename: same normalization and duplicate protection; preserve active selection by id.
old="""      const name=await vesselPrompt('Переименовать канал',channel.name,'Название канала');
      if(!name?.trim()||name.trim()===channel.name)return;
      const {error}=await supabase.from('channels').update({name:name.trim()}).eq('id',channel.id).eq('server_id',server.dbId);
      if(error){vesselNotice(`Не удалось переименовать канал: ${error.message}`,'error');return;}
      server.__channelsLoaded=false;
      await syncSupabaseChannels(server);
      activeChannelId=channel.id; activeChannelName=name.trim(); render();
      return;"""
new="""      const name=await vesselPrompt('Переименовать канал',channel.name,'Название канала');
      const channelName=String(name||'').trim().replace(/\\s+/g,'-').replace(/-+/g,'-').slice(0,50);
      if(!channelName||channelName===channel.name)return;
      if(serverChannels().some(item=>item.id!==channel.id&&item.name.toLocaleLowerCase('ru-RU')===channelName.toLocaleLowerCase('ru-RU'))){vesselNotice('Канал с таким названием уже существует.','error');return;}
      const {error}=await supabase.from('channels').update({name:channelName}).eq('id',channel.id).eq('server_id',server.dbId);
      if(error){vesselNotice(`Не удалось переименовать канал: ${error.message}`,'error');return;}
      activeChannelId=channel.id;
      server.__channelsLoaded=false;
      await syncSupabaseChannels(server);
      vesselNotice(`Канал переименован в «${channelName}».`,'success');
      return;"""
replace_once(old,new,'channel rename lifecycle')

# Delete: leave a deleted voice room first, clear the selected id, then let DB order choose the next channel.
old="""      if(!await vesselConfirm(`Удалить канал «${channel.name}»?`))return;
      const {error}=await supabase.from('channels').delete().eq('id',channel.id).eq('server_id',server.dbId);
      if(error){vesselNotice(`Не удалось удалить канал: ${error.message}`,'error');return;}
      activeChannelId=null; messages=[]; server.__channelsLoaded=false; await syncSupabaseChannels(server);"""
new="""      if(!await vesselConfirm(`Удалить канал «${channel.name}»?`))return;
      if(voiceChannelId===channel.id&&voiceStream)await leaveVoiceRoom();
      const {error}=await supabase.from('channels').delete().eq('id',channel.id).eq('server_id',server.dbId);
      if(error){vesselNotice(`Не удалось удалить канал: ${error.message}`,'error');return;}
      if(activeChannelId===channel.id){activeChannelId=null;activeChannelName='нет каналов';activeChannelKind='text';messages=[];}
      server.__channelsLoaded=false;
      await syncSupabaseChannels(server);
      vesselNotice(`Канал «${channel.name}» удалён.`,'success');"""
replace_once(old,new,'channel delete lifecycle')

# Guard against accidental reintroduction of stale state or wrong ordering.
if "const active=servers[activeServerIndex];" in text:
    raise SystemExit('realtime still trusts active server array index')
create_marker="activeChannelId=data.id; activeChannelName=data.name; activeChannelKind=data.kind;"
sync_marker="server.__channelsLoaded=false;\n    await syncSupabaseChannels(server);"
create_at=text.find(create_marker)
sync_at=text.find(sync_marker, create_at)
if create_at<0 or sync_at<0 or create_at>sync_at:
    raise SystemExit('new channel must be selected before channel resync')

path.write_text(text,encoding='utf-8')
print('Applied robust channel lifecycle patch')
