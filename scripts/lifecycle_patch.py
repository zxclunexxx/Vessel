from pathlib import Path

path = Path('src/main.js')
text = path.read_text(encoding='utf-8')
changed = False


def replace_once(old, new, label):
    global text, changed
    if new in text:
        return
    if old not in text:
        raise SystemExit(f'{label} anchor not found')
    text = text.replace(old, new, 1)
    changed = True


def replace_all_expected(old, new, label, minimum=1):
    global text, changed
    if old not in text:
        if new in text:
            return
        raise SystemExit(f'{label} anchor not found')
    count = text.count(old)
    if count < minimum:
        raise SystemExit(f'{label} expected at least {minimum} anchors, found {count}')
    text = text.replace(old, new)
    changed = True


# Bind uploads to the conversation/channel selected before the asynchronous upload begins.
upload_old = """async function uploadVesselFile(file, user) {
  if (!supabase || !user?.id) { vesselNotice('Для загрузки файлов нужен настоящий аккаунт.','error'); return null; }
  if(file.size>25*1024*1024){vesselNotice('Максимальный размер файла — 25 МБ.','error');return null;}
  let context=null;
  if(activeDmId)context=`dm/${activeDmId}`;
  else if(activeChannelId&&activeChannelKind==='text')context=`channel/${activeChannelId}`;
  if(!context){vesselNotice('Открой личный чат или текстовый канал перед загрузкой файла.','error');return null;}
"""
upload_new = """async function uploadVesselFile(file, user, context) {
  if (!supabase || !user?.id) { vesselNotice('Для загрузки файлов нужен настоящий аккаунт.','error'); return null; }
  if(file.size>25*1024*1024){vesselNotice('Максимальный размер файла — 25 МБ.','error');return null;}
  if(!context){vesselNotice('Открой личный чат или текстовый канал перед загрузкой файла.','error');return null;}
"""
replace_once(upload_old, upload_new, 'attachment target capture')


# A DM send that finishes after the user navigates away must not overwrite the currently shown DM.
dm_refresh_old = """window.__vesselDmThreadsLoaded=false; await Promise.all([loadDirectMessages(user,peerId),syncDmThreads(user)]);"""
dm_refresh_new = """window.__vesselDmThreadsLoaded=false; if(activeDmId===peerId)await Promise.all([loadDirectMessages(user,peerId),syncDmThreads(user)]);else await syncDmThreads(user);"""
replace_all_expected(dm_refresh_old, dm_refresh_new, 'DM navigation-safe refresh', minimum=1)

# The attachment branch is formatted across multiple lines; harden it separately.
attachment_refresh_old = """        window.__vesselDmThreadsLoaded=false;
        await Promise.all([loadDirectMessages(user,peerId),syncDmThreads(user)]);
"""
attachment_refresh_new = """        window.__vesselDmThreadsLoaded=false;
        if(activeDmId===peerId)await Promise.all([loadDirectMessages(user,peerId),syncDmThreads(user)]);else await syncDmThreads(user);
"""
replace_once(attachment_refresh_old, attachment_refresh_new, 'attachment DM navigation-safe refresh')


attach_old = """  document.querySelector('.attach').addEventListener('click', () => {
    const picker=document.createElement('input'); picker.type='file'; picker.accept='image/*,.pdf,.doc,.docx,.zip';
    picker.onchange=async()=>{
      const file=picker.files[0]; if(!file)return;
      const attachment=await uploadVesselFile(file,user); if(!attachment)return;
      const body=`📎 ${file.name}`;
      if(activeDmId){
        const peerId=activeDmId;
        const {error}=await supabase.from('direct_messages').insert({sender_id:user.id,receiver_id:peerId,body,attachments:[attachment]});
        if(error){await cleanupFailedAttachment(attachment);vesselNotice(`Не удалось отправить файл: ${error.message}`,'error');return;}
        window.__vesselDmThreadsLoaded=false;
        if(activeDmId===peerId)await Promise.all([loadDirectMessages(user,peerId),syncDmThreads(user)]);else await syncDmThreads(user);
      } else {
        if(!activeChannelId||activeChannelKind!=='text'){vesselNotice('Открой текстовый канал или личный чат.','error');return;}
        const {error}=await supabase.from('messages').insert({channel_id:activeChannelId,author_id:user.id,body,attachments:[attachment]});
        if(error){await cleanupFailedAttachment(attachment);vesselNotice(`Не удалось отправить файл: ${error.message}`,'error');return;}
        messages.push({name:user.name,time:'только что',color:user.avatarColor||'#39d9a6',text:body,attachments:[attachment]});
      }
      render();
    };
    picker.click();
  });
"""
attach_new = """  document.querySelector('.attach').addEventListener('click', () => {
    const targetDmId=activeDmId;
    const targetChannelId=!targetDmId&&activeChannelKind==='text'?activeChannelId:null;
    const uploadContext=targetDmId?`dm/${targetDmId}`:targetChannelId?`channel/${targetChannelId}`:null;
    if(!uploadContext){vesselNotice('Открой текстовый канал или личный чат.','error');return;}
    const picker=document.createElement('input'); picker.type='file'; picker.accept='image/*,.pdf,.doc,.docx,.zip';
    picker.onchange=async()=>{
      const file=picker.files[0]; if(!file)return;
      const attachment=await uploadVesselFile(file,user,uploadContext); if(!attachment)return;
      const body=`📎 ${file.name}`;
      if(targetDmId){
        const peerId=targetDmId;
        const {error}=await supabase.from('direct_messages').insert({sender_id:user.id,receiver_id:peerId,body,attachments:[attachment]});
        if(error){await cleanupFailedAttachment(attachment);vesselNotice(`Не удалось отправить файл: ${error.message}`,'error');return;}
        window.__vesselDmThreadsLoaded=false;
        if(activeDmId===peerId)await Promise.all([loadDirectMessages(user,peerId),syncDmThreads(user)]);else await syncDmThreads(user);
      } else {
        const {error}=await supabase.from('messages').insert({channel_id:targetChannelId,author_id:user.id,body,attachments:[attachment]});
        if(error){await cleanupFailedAttachment(attachment);vesselNotice(`Не удалось отправить файл: ${error.message}`,'error');return;}
        if(activeChannelId===targetChannelId&&!activeDmId)messages.push({name:user.name,time:'только что',color:user.avatarColor||'#39d9a6',text:body,attachments:[attachment]});
      }
      render();
    };
    picker.click();
  });
"""
replace_once(attach_old, attach_new, 'attachment conversation race')


# Capture the selected text channel before awaiting the DB insert so a navigation event cannot
# append the sent message to a different channel UI.
composer_channel_old = """} else { if(!activeChannelId||activeChannelKind!=='text'){vesselNotice('Сначала выбери текстовый канал.','error');return;} const {error}=await supabase.from('messages').insert({channel_id:activeChannelId,author_id:user.id,body:text}); if(error){vesselNotice(`Не удалось отправить сообщение: ${error.message}`,'error');return;} messages.push({name:user.name,time:'только что',color:user.avatarColor||'#39d9a6',text}); } input.value=''; render();"""
composer_channel_new = """} else { if(!activeChannelId||activeChannelKind!=='text'){vesselNotice('Сначала выбери текстовый канал.','error');return;} const channelId=activeChannelId; const {error}=await supabase.from('messages').insert({channel_id:channelId,author_id:user.id,body:text}); if(error){vesselNotice(`Не удалось отправить сообщение: ${error.message}`,'error');return;} if(activeChannelId===channelId&&!activeDmId)messages.push({name:user.name,time:'только что',color:user.avatarColor||'#39d9a6',text}); } input.value=''; render();"""
replace_once(composer_channel_old, composer_channel_new, 'channel send navigation race')


# Leaving or deleting the server that owns the active voice room must stop microphone/media
# before membership/channel rows disappear.
server_delete_old = """      if(action==='3'){
        if(!await vesselConfirm(`Удалить сервер «${server.name}»?`,'Каналы и сообщения этого сервера тоже будут удалены.'))return;
        const {error}=await supabase.from('servers').delete().eq('id',server.dbId).eq('owner_id',user.id);
"""
server_delete_new = """      if(action==='3'){
        if(!await vesselConfirm(`Удалить сервер «${server.name}»?`,'Каналы и сообщения этого сервера тоже будут удалены.'))return;
        if(voiceStream&&voiceChannelId&&serverChannels().some(channel=>channel.id===voiceChannelId))await leaveVoiceRoom();
        const {error}=await supabase.from('servers').delete().eq('id',server.dbId).eq('owner_id',user.id);
"""
replace_once(server_delete_old, server_delete_new, 'server delete voice cleanup')

server_leave_old = """    if(await vesselConfirm(`Выйти из сервера «${server.name}»?`)){
      const {error}=await supabase.from('server_members').delete().eq('server_id',server.dbId).eq('user_id',user.id);
"""
server_leave_new = """    if(await vesselConfirm(`Выйти из сервера «${server.name}»?`)){
      if(voiceStream&&voiceChannelId&&serverChannels().some(channel=>channel.id===voiceChannelId))await leaveVoiceRoom();
      const {error}=await supabase.from('server_members').delete().eq('server_id',server.dbId).eq('user_id',user.id);
"""
replace_once(server_leave_old, server_leave_new, 'server leave voice cleanup')


for marker in [
    'async function uploadVesselFile(file, user, context)',
    'const targetDmId=activeDmId;',
    'const uploadContext=targetDmId?',
    'channel_id:targetChannelId',
    'const channelId=activeChannelId;',
    'serverChannels().some(channel=>channel.id===voiceChannelId)',
]:
    if marker not in text:
        raise SystemExit(f'missing lifecycle hardening marker: {marker}')

if changed:
    path.write_text(text,encoding='utf-8')
    print('Applied Vessel attachment and server/voice lifecycle hardening')
else:
    print('Vessel attachment and server/voice lifecycle hardening already applied; nothing to change')
