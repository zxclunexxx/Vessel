from pathlib import Path

path = Path('src/main.js')
text = path.read_text(encoding='utf-8')
changed = False


def replace_once(old, new, label):
    global text, changed
    if new in text:
        print(f'{label}: already applied')
        return
    if old not in text:
        raise SystemExit(f'{label}: expected source or patched form not found')
    text = text.replace(old, new, 1)
    changed = True


helper_old = """function render() {
"""
helper_new = """async function refreshReadOnlyDirectMessage(user,peerId){
  window.__vesselSocialLoaded=false;
  window.__vesselDmThreadsLoaded=false;
  await Promise.all([syncSocial(user),syncDmThreads(user)]);
  if(activeDmId===peerId){
    window.__vesselDmLoaded=false;
    await loadDirectMessages(user,peerId);
  }else render();
}
async function verifyDirectMessageAccess(user,peerId,{notify=true}={}){
  if(!supabase||!user?.id||!peerId)return false;
  const {data,error}=await supabase.from('friendships').select('friend_id').eq('user_id',user.id).eq('friend_id',peerId).maybeSingle();
  if(error){
    console.warn('DM friendship verification failed',error);
    if(notify)vesselNotice('Не удалось проверить доступ к переписке. Попробуй ещё раз.','error');
    return null;
  }
  if(data)return true;
  await refreshReadOnlyDirectMessage(user,peerId);
  if(notify)vesselNotice('Пользователь больше не в друзьях. История оставлена только для чтения.','error');
  return false;
}
function render() {
"""
replace_once(helper_old, helper_new, 'DM access verifier')

composer_old = """  document.querySelector('.composer').addEventListener('submit', async e => { e.preventDefault(); const input=e.currentTarget.querySelector('input'); const text=input.value.trim(); if(!text)return; if(!supabase||!user.id){vesselNotice('Нужна активная сессия Vessel.','error');return;} if(activeDmId){ const peerId=activeDmId; const {error}=await supabase.from('direct_messages').insert({sender_id:user.id,receiver_id:peerId,body:text}); if(error){vesselNotice(`Не удалось отправить личное сообщение: ${error.message}`,'error');return;} window.__vesselDmThreadsLoaded=false; const refreshes=[syncDmThreads(user)]; if(activeDmId===peerId)refreshes.push(loadDirectMessages(user,peerId)); await Promise.all(refreshes); } else { if(!activeChannelId||activeChannelKind!=='text'){vesselNotice('Сначала выбери текстовый канал.','error');return;} const channelId=activeChannelId; const {error}=await supabase.from('messages').insert({channel_id:channelId,author_id:user.id,body:text}); if(error){vesselNotice(`Не удалось отправить сообщение: ${error.message}`,'error');return;} if(!activeDmId&&activeChannelId===channelId&&activeChannelKind==='text')messages.push({name:user.name,time:'только что',color:user.avatarColor||'#39d9a6',text}); } input.value=''; render(); const list=document.querySelector('.messages'); if(list)list.scrollTop=list.scrollHeight; });
"""
composer_new = """  document.querySelector('.composer').addEventListener('submit', async e => {
    e.preventDefault();
    const input=e.currentTarget.querySelector('input');
    const text=input.value.trim();
    if(!text)return;
    if(!supabase||!user.id){vesselNotice('Нужна активная сессия Vessel.','error');return;}
    if(activeDmId){
      const peerId=activeDmId;
      if((await verifyDirectMessageAccess(user,peerId))!==true)return;
      const {error}=await supabase.from('direct_messages').insert({sender_id:user.id,receiver_id:peerId,body:text});
      if(error){
        const access=await verifyDirectMessageAccess(user,peerId,{notify:false});
        if(access===false){vesselNotice('Пользователь больше не в друзьях. История оставлена только для чтения.','error');return;}
        vesselNotice(`Не удалось отправить личное сообщение: ${error.message}`,'error');
        return;
      }
      window.__vesselDmThreadsLoaded=false;
      const refreshes=[syncDmThreads(user)];
      if(activeDmId===peerId)refreshes.push(loadDirectMessages(user,peerId));
      await Promise.all(refreshes);
    } else {
      if(!activeChannelId||activeChannelKind!=='text'){vesselNotice('Сначала выбери текстовый канал.','error');return;}
      const channelId=activeChannelId;
      const {error}=await supabase.from('messages').insert({channel_id:channelId,author_id:user.id,body:text});
      if(error){vesselNotice(`Не удалось отправить сообщение: ${error.message}`,'error');return;}
      if(!activeDmId&&activeChannelId===channelId&&activeChannelKind==='text')messages.push({name:user.name,time:'только что',color:user.avatarColor||'#39d9a6',text});
    }
    input.value='';
    render();
    const list=document.querySelector('.messages');
    if(list)list.scrollTop=list.scrollHeight;
  });
"""
replace_once(composer_old, composer_new, 'DM text send guard')

attachment_old = """      const targetDmId=activeDmId;
      const targetChannelId=!targetDmId&&activeChannelKind==='text'?activeChannelId:null;
      if(!targetDmId&&!targetChannelId){vesselNotice('Открой текстовый канал или личный чат.','error');return;}
      const attachment=await uploadVesselFile(file,user); if(!attachment)return;
      const body=`📎 ${file.name}`;
      if(targetDmId){
        const peerId=targetDmId;
        const {error}=await supabase.from('direct_messages').insert({sender_id:user.id,receiver_id:peerId,body,attachments:[attachment]});
        if(error){await cleanupFailedAttachment(attachment);vesselNotice(`Не удалось отправить файл: ${error.message}`,'error');return;}
"""
attachment_new = """      const targetDmId=activeDmId;
      const targetChannelId=!targetDmId&&activeChannelKind==='text'?activeChannelId:null;
      if(!targetDmId&&!targetChannelId){vesselNotice('Открой текстовый канал или личный чат.','error');return;}
      if(targetDmId&&(await verifyDirectMessageAccess(user,targetDmId))!==true)return;
      const attachment=await uploadVesselFile(file,user); if(!attachment)return;
      if(targetDmId&&(await verifyDirectMessageAccess(user,targetDmId))!==true){await cleanupFailedAttachment(attachment);return;}
      const body=`📎 ${file.name}`;
      if(targetDmId){
        const peerId=targetDmId;
        const {error}=await supabase.from('direct_messages').insert({sender_id:user.id,receiver_id:peerId,body,attachments:[attachment]});
        if(error){
          await cleanupFailedAttachment(attachment);
          const access=await verifyDirectMessageAccess(user,peerId,{notify:false});
          if(access===false){vesselNotice('Пользователь больше не в друзьях. История оставлена только для чтения.','error');return;}
          vesselNotice(`Не удалось отправить файл: ${error.message}`,'error');
          return;
        }
"""
replace_once(attachment_old, attachment_new, 'DM attachment send guard')

required = [
    'async function verifyDirectMessageAccess(user,peerId,{notify=true}={})',
    "supabase.from('friendships').select('friend_id').eq('user_id',user.id).eq('friend_id',peerId).maybeSingle()",
    'if((await verifyDirectMessageAccess(user,peerId))!==true)return;',
    'if(targetDmId&&(await verifyDirectMessageAccess(user,targetDmId))!==true)return;',
    'if(targetDmId&&(await verifyDirectMessageAccess(user,targetDmId))!==true){await cleanupFailedAttachment(attachment);return;}',
    "const access=await verifyDirectMessageAccess(user,peerId,{notify:false});",
]
for marker in required:
    if marker not in text:
        raise SystemExit(f'missing DM send guard marker: {marker}')

if changed:
    path.write_text(text, encoding='utf-8')
    print('Applied DM friendship revalidation for text and attachment sends')
else:
    print('DM send access guards already applied; nothing to change')
