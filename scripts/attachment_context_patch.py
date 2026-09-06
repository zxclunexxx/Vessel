from pathlib import Path

# Keep asynchronous sends bound to the conversation/channel that initiated them.
path = Path('src/main.js')
text = path.read_text(encoding='utf-8')
changed = False

attachment_old = """    picker.onchange=async()=>{
      const file=picker.files[0]; if(!file)return;
      const attachment=await uploadVesselFile(file,user); if(!attachment)return;
      const body=`📎 ${file.name}`;
      if(activeDmId){
        const peerId=activeDmId;
        const {error}=await supabase.from('direct_messages').insert({sender_id:user.id,receiver_id:peerId,body,attachments:[attachment]});
        if(error){await cleanupFailedAttachment(attachment);vesselNotice(`Не удалось отправить файл: ${error.message}`,'error');return;}
        window.__vesselDmThreadsLoaded=false;
        await Promise.all([loadDirectMessages(user,peerId),syncDmThreads(user)]);
      } else {
        if(!activeChannelId||activeChannelKind!=='text'){vesselNotice('Открой текстовый канал или личный чат.','error');return;}
        const {error}=await supabase.from('messages').insert({channel_id:activeChannelId,author_id:user.id,body,attachments:[attachment]});
        if(error){await cleanupFailedAttachment(attachment);vesselNotice(`Не удалось отправить файл: ${error.message}`,'error');return;}
        messages.push({name:user.name,time:'только что',color:user.avatarColor||'#39d9a6',text:body,attachments:[attachment]});
      }
      render();
    };"""

attachment_new = """    picker.onchange=async()=>{
      const file=picker.files[0]; if(!file)return;
      const targetDmId=activeDmId;
      const targetChannelId=!targetDmId&&activeChannelKind==='text'?activeChannelId:null;
      if(!targetDmId&&!targetChannelId){vesselNotice('Открой текстовый канал или личный чат.','error');return;}
      const attachment=await uploadVesselFile(file,user); if(!attachment)return;
      const body=`📎 ${file.name}`;
      if(targetDmId){
        const peerId=targetDmId;
        const {error}=await supabase.from('direct_messages').insert({sender_id:user.id,receiver_id:peerId,body,attachments:[attachment]});
        if(error){await cleanupFailedAttachment(attachment);vesselNotice(`Не удалось отправить файл: ${error.message}`,'error');return;}
        window.__vesselDmThreadsLoaded=false;
        const refreshes=[syncDmThreads(user)];
        if(activeDmId===peerId)refreshes.push(loadDirectMessages(user,peerId));
        await Promise.all(refreshes);
      } else {
        const {error}=await supabase.from('messages').insert({channel_id:targetChannelId,author_id:user.id,body,attachments:[attachment]});
        if(error){await cleanupFailedAttachment(attachment);vesselNotice(`Не удалось отправить файл: ${error.message}`,'error');return;}
        if(!activeDmId&&activeChannelId===targetChannelId&&activeChannelKind==='text'){
          messages.push({name:user.name,time:'только что',color:user.avatarColor||'#39d9a6',text:body,attachments:[attachment]});
        }
      }
      render();
    };"""

if attachment_new not in text:
    if attachment_old not in text:
        raise SystemExit('attachment upload anchor not found')
    text = text.replace(attachment_old, attachment_new, 1)
    changed = True

composer_old = """  document.querySelector('.composer').addEventListener('submit', async e => { e.preventDefault(); const input=e.currentTarget.querySelector('input'); const text=input.value.trim(); if(!text)return; if(!supabase||!user.id){vesselNotice('Нужна активная сессия Vessel.','error');return;} if(activeDmId){ const peerId=activeDmId; const {error}=await supabase.from('direct_messages').insert({sender_id:user.id,receiver_id:peerId,body:text}); if(error){vesselNotice(`Не удалось отправить личное сообщение: ${error.message}`,'error');return;} window.__vesselDmThreadsLoaded=false; await Promise.all([loadDirectMessages(user,peerId),syncDmThreads(user)]); } else { if(!activeChannelId||activeChannelKind!=='text'){vesselNotice('Сначала выбери текстовый канал.','error');return;} const {error}=await supabase.from('messages').insert({channel_id:activeChannelId,author_id:user.id,body:text}); if(error){vesselNotice(`Не удалось отправить сообщение: ${error.message}`,'error');return;} messages.push({name:user.name,time:'только что',color:user.avatarColor||'#39d9a6',text}); } input.value=''; render(); const list=document.querySelector('.messages'); if(list)list.scrollTop=list.scrollHeight; });"""
composer_new = """  document.querySelector('.composer').addEventListener('submit', async e => { e.preventDefault(); const input=e.currentTarget.querySelector('input'); const text=input.value.trim(); if(!text)return; if(!supabase||!user.id){vesselNotice('Нужна активная сессия Vessel.','error');return;} if(activeDmId){ const peerId=activeDmId; const {error}=await supabase.from('direct_messages').insert({sender_id:user.id,receiver_id:peerId,body:text}); if(error){vesselNotice(`Не удалось отправить личное сообщение: ${error.message}`,'error');return;} window.__vesselDmThreadsLoaded=false; const refreshes=[syncDmThreads(user)]; if(activeDmId===peerId)refreshes.push(loadDirectMessages(user,peerId)); await Promise.all(refreshes); } else { if(!activeChannelId||activeChannelKind!=='text'){vesselNotice('Сначала выбери текстовый канал.','error');return;} const channelId=activeChannelId; const {error}=await supabase.from('messages').insert({channel_id:channelId,author_id:user.id,body:text}); if(error){vesselNotice(`Не удалось отправить сообщение: ${error.message}`,'error');return;} if(!activeDmId&&activeChannelId===channelId&&activeChannelKind==='text')messages.push({name:user.name,time:'только что',color:user.avatarColor||'#39d9a6',text}); } input.value=''; render(); const list=document.querySelector('.messages'); if(list)list.scrollTop=list.scrollHeight; });"""

if composer_new not in text:
    if composer_old not in text:
        raise SystemExit('composer destination anchor not found')
    text = text.replace(composer_old, composer_new, 1)
    changed = True

for marker in [
    'const targetDmId=activeDmId;',
    'const targetChannelId=!targetDmId',
    'const refreshes=[syncDmThreads(user)];',
    'const channelId=activeChannelId;',
    'cleanupFailedAttachment(attachment)',
]:
    if marker not in text:
        raise SystemExit(f'missing async destination hardening marker: {marker}')

if changed:
    path.write_text(text, encoding='utf-8')
    print('Applied async message/attachment destination hardening')
else:
    print('Async message/attachment destination hardening already applied; nothing to change')
