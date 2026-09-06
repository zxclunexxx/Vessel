from pathlib import Path

path = Path('src/main.js')
text = path.read_text(encoding='utf-8')
changed = False

HARDENED_MARKERS = [
    'const refreshUserId=user?.id||null;',
    'if(savedUser?.id!==refreshUserId)return;',
    'const accessUserId=user.id;',
    'if(savedUser?.id!==accessUserId)return null;',
    'const dmLoadUserId=user.id;',
    'if(savedUser?.id!==dmLoadUserId||activeDmId!==friendId)return;',
    'const sendSessionUserId=user.id;',
    'if(savedUser?.id!==sendSessionUserId)return;',
    'const attachmentSessionUserId=user.id;',
    'if(savedUser?.id!==attachmentSessionUserId){await cleanupFailedAttachment(attachment);return;}',
]

if all(marker in text for marker in HARDENED_MARKERS):
    print('DM/channel send and history auth-session hardening already applied; nothing to change')
    raise SystemExit(0)


def replace_once(old, new, label):
    global text, changed
    if new in text:
        print(f'{label}: already applied')
        return
    if old not in text:
        raise SystemExit(f'{label}: expected source or patched form not found')
    text = text.replace(old, new, 1)
    changed = True


helper_old = """async function refreshReadOnlyDirectMessage(user,peerId){
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
"""
helper_new = """async function refreshReadOnlyDirectMessage(user,peerId){
  const refreshUserId=user?.id||null;
  if(!refreshUserId||savedUser?.id!==refreshUserId)return;
  window.__vesselSocialLoaded=false;
  window.__vesselDmThreadsLoaded=false;
  await Promise.all([syncSocial(user),syncDmThreads(user)]);
  if(savedUser?.id!==refreshUserId)return;
  if(activeDmId===peerId){
    window.__vesselDmLoaded=false;
    await loadDirectMessages(user,peerId);
  }else render();
}
async function verifyDirectMessageAccess(user,peerId,{notify=true}={}){
  if(!supabase||!user?.id||!peerId)return false;
  const accessUserId=user.id;
  if(savedUser?.id!==accessUserId)return null;
  const {data,error}=await supabase.from('friendships').select('friend_id').eq('user_id',accessUserId).eq('friend_id',peerId).maybeSingle();
  if(savedUser?.id!==accessUserId)return null;
  if(error){
    console.warn('DM friendship verification failed',error);
    if(notify)vesselNotice('Не удалось проверить доступ к переписке. Попробуй ещё раз.','error');
    return null;
  }
  if(data)return true;
  await refreshReadOnlyDirectMessage(user,peerId);
  if(savedUser?.id!==accessUserId)return null;
  if(notify)vesselNotice('Пользователь больше не в друзьях. История оставлена только для чтения.','error');
  return false;
}
"""
replace_once(helper_old, helper_new, 'DM access verifier auth-session guard')

history_old = """async function loadDirectMessages(user, friendId) {
  if (!supabase || !user?.id || !friendId) return;
  const {data,error} = await supabase.from('direct_messages').select('id,sender_id,receiver_id,body,attachments,created_at,profiles!direct_messages_sender_id_fkey(username,avatar_color)').or(`and(sender_id.eq.${user.id},receiver_id.eq.${friendId}),and(sender_id.eq.${friendId},receiver_id.eq.${user.id})`).order('created_at',{ascending:false}).limit(100);
  if(activeDmId!==friendId)return;
"""
history_new = """async function loadDirectMessages(user, friendId) {
  if (!supabase || !user?.id || !friendId) return;
  const dmLoadUserId=user.id;
  if(savedUser?.id!==dmLoadUserId)return;
  const {data,error} = await supabase.from('direct_messages').select('id,sender_id,receiver_id,body,attachments,created_at,profiles!direct_messages_sender_id_fkey(username,avatar_color)').or(`and(sender_id.eq.${dmLoadUserId},receiver_id.eq.${friendId}),and(sender_id.eq.${friendId},receiver_id.eq.${dmLoadUserId})`).order('created_at',{ascending:false}).limit(100);
  if(savedUser?.id!==dmLoadUserId||activeDmId!==friendId)return;
"""
replace_once(history_old, history_new, 'DM history auth-session guard')

replace_once(
    """    if(!supabase||!user.id){vesselNotice('Нужна активная сессия Vessel.','error');return;}
    if(activeDmId){
""",
    """    if(!supabase||!user.id){vesselNotice('Нужна активная сессия Vessel.','error');return;}
    const sendSessionUserId=user.id;
    if(activeDmId){
""",
    'composer session capture',
)

replace_once(
    """      const {error}=await supabase.from('direct_messages').insert({sender_id:user.id,receiver_id:peerId,body:text});
      if(error){
""",
    """      const {error}=await supabase.from('direct_messages').insert({sender_id:sendSessionUserId,receiver_id:peerId,body:text});
      if(savedUser?.id!==sendSessionUserId)return;
      if(error){
""",
    'DM text post-insert session guard',
)

replace_once(
    """      const {error}=await supabase.from('messages').insert({channel_id:channelId,author_id:user.id,body:text});
      if(error){vesselNotice(`Не удалось отправить сообщение: ${error.message}`,'error');return;}
""",
    """      const {error}=await supabase.from('messages').insert({channel_id:channelId,author_id:sendSessionUserId,body:text});
      if(savedUser?.id!==sendSessionUserId)return;
      if(error){vesselNotice(`Не удалось отправить сообщение: ${error.message}`,'error');return;}
""",
    'channel text post-insert session guard',
)

replace_once(
    """    }
    input.value='';
    render();
""",
    """    }
    if(savedUser?.id!==sendSessionUserId)return;
    input.value='';
    render();
""",
    'composer final session guard',
)

replace_once(
    """      const file=picker.files[0]; if(!file)return;
      const targetDmId=activeDmId;
""",
    """      const file=picker.files[0]; if(!file)return;
      const attachmentSessionUserId=user.id;
      if(savedUser?.id!==attachmentSessionUserId)return;
      const targetDmId=activeDmId;
""",
    'attachment session capture',
)

replace_once(
    """      if(targetDmId&&(await verifyDirectMessageAccess(user,targetDmId))!==true)return;
      const attachment=await uploadVesselFile(file,user); if(!attachment)return;
      if(targetDmId&&(await verifyDirectMessageAccess(user,targetDmId))!==true){await cleanupFailedAttachment(attachment);return;}
""",
    """      if(targetDmId&&(await verifyDirectMessageAccess(user,targetDmId))!==true)return;
      if(savedUser?.id!==attachmentSessionUserId)return;
      const attachment=await uploadVesselFile(file,user); if(!attachment)return;
      if(savedUser?.id!==attachmentSessionUserId){await cleanupFailedAttachment(attachment);return;}
      if(targetDmId&&(await verifyDirectMessageAccess(user,targetDmId))!==true){await cleanupFailedAttachment(attachment);return;}
      if(savedUser?.id!==attachmentSessionUserId){await cleanupFailedAttachment(attachment);return;}
""",
    'attachment upload session guard',
)

replace_once(
    """        const {error}=await supabase.from('direct_messages').insert({sender_id:user.id,receiver_id:peerId,body,attachments:[attachment]});
        if(error){
""",
    """        const {error}=await supabase.from('direct_messages').insert({sender_id:attachmentSessionUserId,receiver_id:peerId,body,attachments:[attachment]});
        if(savedUser?.id!==attachmentSessionUserId){if(error)await cleanupFailedAttachment(attachment);return;}
        if(error){
""",
    'DM attachment post-insert session guard',
)

replace_once(
    """        const {error}=await supabase.from('messages').insert({channel_id:targetChannelId,author_id:user.id,body,attachments:[attachment]});
        if(error){await cleanupFailedAttachment(attachment);vesselNotice(`Не удалось отправить файл: ${error.message}`,'error');return;}
""",
    """        const {error}=await supabase.from('messages').insert({channel_id:targetChannelId,author_id:attachmentSessionUserId,body,attachments:[attachment]});
        if(savedUser?.id!==attachmentSessionUserId){if(error)await cleanupFailedAttachment(attachment);return;}
        if(error){await cleanupFailedAttachment(attachment);vesselNotice(`Не удалось отправить файл: ${error.message}`,'error');return;}
""",
    'channel attachment post-insert session guard',
)

replace_once(
    """      }
      render();
    };
""",
    """      }
      if(savedUser?.id!==attachmentSessionUserId)return;
      render();
    };
""",
    'attachment final session guard',
)

for marker in HARDENED_MARKERS:
    if marker not in text:
        raise SystemExit(f'missing message auth-session hardening marker: {marker}')

if changed:
    path.write_text(text, encoding='utf-8')
    print('Applied DM/channel send and history auth-session hardening')
else:
    print('DM/channel send and history auth-session hardening already applied; nothing to change')
