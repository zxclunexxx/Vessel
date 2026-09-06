from pathlib import Path

# Keep file sends bound to the conversation that owned the composer when selection began.
path = Path('src/main.js')
text = path.read_text(encoding='utf-8')

old = """    picker.onchange=async()=>{
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

new = """    picker.onchange=async()=>{
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

if new in text:
    print('Attachment destination hardening already applied; nothing to change')
elif old in text:
    text = text.replace(old, new, 1)
    path.write_text(text, encoding='utf-8')
    print('Applied attachment destination hardening')
else:
    raise SystemExit('attachment upload anchor not found')
