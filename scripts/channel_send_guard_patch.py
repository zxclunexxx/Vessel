from pathlib import Path

# Re-run through the autonomous verifier after wiring this patch into the workflow trigger.
path=Path('src/main.js')
text=path.read_text(encoding='utf-8')
changed=False


def replace_once(old,new,label):
    global text, changed
    if new in text:
        print(f'{label}: already applied')
        return
    if old not in text:
        raise SystemExit(f'{label}: expected source or patched form not found')
    text=text.replace(old,new,1)
    changed=True

helper_old="""function render() {
"""
helper_new="""async function refreshAfterChannelAccessLoss(user,channelId){
  const refreshUserId=user?.id||null;
  if(!refreshUserId||savedUser?.id!==refreshUserId)return;
  const lostServerId=getActiveServer()?.dbId||null;
  if(voiceStream&&lostServerId&&voiceServerId===lostServerId)await leaveVoiceRoom();
  activeChannelId=null;
  activeChannelName='нет каналов';
  activeChannelKind='text';
  dbChannels=[];
  messages=[];
  serverMembers=[];
  window.__vesselMembersServerId=null;
  window.__vesselServersLoaded=false;
  await syncSupabaseServers(user);
  if(savedUser?.id!==refreshUserId)return;
  const next=getActiveServer();
  if(next?.dbId){
    next.__channelsLoaded=false;
    await syncSupabaseChannels(next);
    await syncServerMembers(user,next);
  }else render();
}
async function verifyChannelAccess(user,channelId,{notify=true}={}){
  if(!supabase||!user?.id||!channelId)return false;
  const accessUserId=user.id;
  if(savedUser?.id!==accessUserId)return null;
  const {data,error}=await supabase.from('channels').select('id').eq('id',channelId).maybeSingle();
  if(savedUser?.id!==accessUserId)return null;
  if(error){
    console.warn('Channel access verification failed',error);
    if(notify)vesselNotice('Не удалось проверить доступ к каналу. Попробуй ещё раз.','error');
    return null;
  }
  if(data)return true;
  await refreshAfterChannelAccessLoss(user,channelId);
  if(savedUser?.id!==accessUserId)return null;
  if(notify)vesselNotice('Доступ к каналу потерян. Список серверов обновлён.','error');
  return false;
}
function render() {
"""
if 'async function verifyChannelAccess(user,channelId,{notify=true}={})' not in text:
    replace_once(helper_old,helper_new,'channel access helper')

replace_once(
"""      const channelId=activeChannelId;
      const {error}=await supabase.from('messages').insert({channel_id:channelId,author_id:sendSessionUserId,body:text});
      if(savedUser?.id!==sendSessionUserId)return;
      if(error){vesselNotice(`Не удалось отправить сообщение: ${error.message}`,'error');return;}
""",
"""      const channelId=activeChannelId;
      if((await verifyChannelAccess(user,channelId))!==true)return;
      if(savedUser?.id!==sendSessionUserId)return;
      const {error}=await supabase.from('messages').insert({channel_id:channelId,author_id:sendSessionUserId,body:text});
      if(savedUser?.id!==sendSessionUserId)return;
      if(error){
        const access=await verifyChannelAccess(user,channelId,{notify:false});
        if(access===false){vesselNotice('Доступ к каналу потерян. Список серверов обновлён.','error');return;}
        vesselNotice(`Не удалось отправить сообщение: ${error.message}`,'error');
        return;
      }
""",
'channel text send preflight',
)

replace_once(
"""      if(targetDmId&&(await verifyDirectMessageAccess(user,targetDmId))!==true)return;
      if(savedUser?.id!==attachmentSessionUserId)return;
      const attachmentContext=targetDmId?`dm/${targetDmId}`:`channel/${targetChannelId}`;
""",
"""      if(targetDmId&&(await verifyDirectMessageAccess(user,targetDmId))!==true)return;
      if(targetChannelId&&(await verifyChannelAccess(user,targetChannelId))!==true)return;
      if(savedUser?.id!==attachmentSessionUserId)return;
      const attachmentContext=targetDmId?`dm/${targetDmId}`:`channel/${targetChannelId}`;
""",
'channel attachment pre-upload access check',
)

replace_once(
"""      if(targetDmId&&(await verifyDirectMessageAccess(user,targetDmId))!==true){await cleanupFailedAttachment(attachment);return;}
      if(savedUser?.id!==attachmentSessionUserId){await cleanupFailedAttachment(attachment);return;}
""",
"""      if(targetDmId&&(await verifyDirectMessageAccess(user,targetDmId))!==true){await cleanupFailedAttachment(attachment);return;}
      if(targetChannelId&&(await verifyChannelAccess(user,targetChannelId))!==true){await cleanupFailedAttachment(attachment);return;}
      if(savedUser?.id!==attachmentSessionUserId){await cleanupFailedAttachment(attachment);return;}
""",
'channel attachment post-upload access check',
)

replace_once(
"""        if(savedUser?.id!==attachmentSessionUserId){if(error)await cleanupFailedAttachment(attachment);return;}
        if(error){await cleanupFailedAttachment(attachment);vesselNotice(`Не удалось отправить файл: ${error.message}`,'error');return;}
""",
"""        if(savedUser?.id!==attachmentSessionUserId){if(error)await cleanupFailedAttachment(attachment);return;}
        if(error){
          await cleanupFailedAttachment(attachment);
          const access=await verifyChannelAccess(user,targetChannelId,{notify:false});
          if(access===false){vesselNotice('Доступ к каналу потерян. Список серверов обновлён.','error');return;}
          vesselNotice(`Не удалось отправить файл: ${error.message}`,'error');
          return;
        }
""",
'channel attachment insert failure access check',
)

required=[
    'async function verifyChannelAccess(user,channelId,{notify=true}={})',
    'if((await verifyChannelAccess(user,channelId))!==true)return;',
    'if(targetChannelId&&(await verifyChannelAccess(user,targetChannelId))!==true)return;',
    'if(targetChannelId&&(await verifyChannelAccess(user,targetChannelId))!==true){await cleanupFailedAttachment(attachment);return;}',
    'const access=await verifyChannelAccess(user,targetChannelId,{notify:false});',
]
for marker in required:
    if marker not in text:
        raise SystemExit(f'missing channel send access marker: {marker}')

if changed:
    path.write_text(text,encoding='utf-8')
    print('Applied stale channel send and attachment access guards')
else:
    print('Stale channel send and attachment access guards already applied; nothing to change')
