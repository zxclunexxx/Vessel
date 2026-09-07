from pathlib import Path

main_path = Path('src/main.js')
schema_path = Path('server/schema.sql')
main = main_path.read_text(encoding='utf-8')
schema = schema_path.read_text(encoding='utf-8')
main_changed = False
schema_changed = False


def replace_once(text, old, new, label):
    if new in text:
        return text, False
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected one anchor, found {count}')
    return text.replace(old, new, 1), True


# Async DM loads must not let an older request overwrite a newer render of the same peer.
old_globals = '''let outgoingFriendRequests = [];
let dmMessages = [];
let notifications = [];
let notificationsSyncRevision = 0;'''
new_globals = '''let outgoingFriendRequests = [];
let dmMessages = [];
let dmMessagesSyncRevision = 0;
let notifications = [];
let notificationsSyncRevision = 0;
let dataRealtimeReconnectTimer = null;
let dataRealtimeReconnectAttempt = 0;
let dataRealtimeRecoveryInFlight = false;'''
main, changed = replace_once(main, old_globals, new_globals, 'social/realtime globals')
main_changed |= changed

old_dm_load = '''async function loadDirectMessages(user, friendId) {
  if (!supabase || !user?.id || !friendId) return;
  const dmLoadUserId=user.id;
  if(savedUser?.id!==dmLoadUserId)return;
  const {data,error} = await supabase.from('direct_messages').select('id,sender_id,receiver_id,body,attachments,created_at,edited_at,deleted_at,profiles!direct_messages_sender_id_fkey(username,avatar_color)').or(`and(sender_id.eq.${dmLoadUserId},receiver_id.eq.${friendId}),and(sender_id.eq.${friendId},receiver_id.eq.${dmLoadUserId})`).is('deleted_at',null).order('created_at',{ascending:false}).limit(100);
  if(savedUser?.id!==dmLoadUserId||activeDmId!==friendId)return;
  if(activeDmId!==friendId)return;
  if(error){vesselNotice('Не удалось загрузить личные сообщения.','error');return;}
  dmMessages = (data || []).reverse().map(row => ({id:row.id,authorId:row.sender_id,name:row.profiles?.username || 'Пользователь',time:new Date(row.created_at).toLocaleString('ru-RU'),editedAt:row.edited_at||null,color:row.profiles?.avatar_color || '#8b7cff',text:row.body,attachments:row.attachments||[]}));
  render();
}'''
new_dm_load = '''async function loadDirectMessages(user, friendId) {
  if (!supabase || !user?.id || !friendId) return;
  const dmLoadUserId=user.id;
  const revision=++dmMessagesSyncRevision;
  if(savedUser?.id!==dmLoadUserId)return;
  const {data,error} = await supabase.from('direct_messages').select('id,sender_id,receiver_id,body,attachments,created_at,edited_at,deleted_at,profiles!direct_messages_sender_id_fkey(username,avatar_color)').or(`and(sender_id.eq.${dmLoadUserId},receiver_id.eq.${friendId}),and(sender_id.eq.${friendId},receiver_id.eq.${dmLoadUserId})`).is('deleted_at',null).order('created_at',{ascending:false}).limit(100);
  if(savedUser?.id!==dmLoadUserId||revision!==dmMessagesSyncRevision||activeDmId!==friendId)return;
  if(error){window.__vesselDmLoaded=false;vesselNotice('Не удалось загрузить личные сообщения.','error');return;}
  dmMessages = (data || []).reverse().map(row => ({id:row.id,authorId:row.sender_id,name:row.profiles?.username || 'Пользователь',time:new Date(row.created_at).toLocaleString('ru-RU'),editedAt:row.edited_at||null,color:row.profiles?.avatar_color || '#8b7cff',text:row.body,attachments:row.attachments||[]}));
  render();
}'''
main, changed = replace_once(main, old_dm_load, new_dm_load, 'direct-message revision guard')
main_changed |= changed

# A stale friend-request mutation can legally affect zero rows. Treat that as a race, not success.
old_retry = '''  let sendError=null;
  if(outgoing&&['accepted','declined','cancelled'].includes(outgoing.status)){
    const result=await supabase.from('friend_requests').update({status:'pending',updated_at:new Date().toISOString()}).eq('id',outgoing.id).eq('sender_id',user.id).in('status',['accepted','declined','cancelled']);
    sendError=result.error;
  }else{
    const result=await supabase.from('friend_requests').insert({sender_id:user.id,receiver_id:target.id,status:'pending'});
    sendError=result.error;
  }
  if(sendError){'''
new_retry = '''  let sendError=null;
  let sentRequest=null;
  if(outgoing&&['accepted','declined','cancelled'].includes(outgoing.status)){
    const result=await supabase.from('friend_requests').update({status:'pending',updated_at:new Date().toISOString()}).eq('id',outgoing.id).eq('sender_id',user.id).in('status',['accepted','declined','cancelled']).select('id,status').maybeSingle();
    sendError=result.error;
    sentRequest=result.data;
    if(!sendError&&!sentRequest){
      window.__vesselSocialLoaded=false;
      await syncSocial(user);
      vesselNotice('Состояние заявки уже изменилось. Список друзей обновлён.');
      return;
    }
  }else{
    const result=await supabase.from('friend_requests').insert({sender_id:user.id,receiver_id:target.id,status:'pending'}).select('id,status').single();
    sendError=result.error;
    sentRequest=result.data;
  }
  if(sendError){'''
main, changed = replace_once(main, old_retry, new_retry, 'friend-request retry result check')
main_changed |= changed

old_cancel = '''  document.querySelectorAll('[data-cancel-request]').forEach(button=>button.addEventListener('click',async()=>{
    if(!supabase||!user.id)return;
    const requestId=button.dataset.cancelRequest;
    const {error}=await supabase.from('friend_requests').delete().eq('id',requestId).eq('sender_id',user.id).eq('status','pending');
    if(error){vesselNotice('Не удалось отменить заявку.','error');return;}
    window.__vesselSocialLoaded=false;
    await syncSocial(user);
    vesselNotice('Заявка отменена.','success');
  }));
  document.querySelectorAll('[data-accept-request]').forEach(button=>button.addEventListener('click',async()=>{if(!supabase||!user.id)return;const {error}=await supabase.from('friend_requests').update({status:'accepted',updated_at:new Date().toISOString()}).eq('id',button.dataset.acceptRequest).eq('receiver_id',user.id);if(error){vesselNotice('Не удалось принять заявку.','error');return;}else vesselNotice('Заявка принята.','success');window.__vesselSocialLoaded=false;await syncSocial(user);render();}));
  document.querySelectorAll('[data-decline-request]').forEach(button=>button.addEventListener('click',async()=>{if(!supabase||!user.id)return;const {error}=await supabase.from('friend_requests').update({status:'declined',updated_at:new Date().toISOString()}).eq('id',button.dataset.declineRequest).eq('receiver_id',user.id);if(error){vesselNotice('Не удалось отклонить заявку.','error');return;}else vesselNotice('Заявка отклонена.');window.__vesselSocialLoaded=false;await syncSocial(user);render();}));'''
new_cancel = '''  document.querySelectorAll('[data-cancel-request]').forEach(button=>button.addEventListener('click',async()=>{
    if(!supabase||!user.id)return;
    const requestId=button.dataset.cancelRequest;
    const {data:cancelled,error}=await supabase.from('friend_requests').delete().eq('id',requestId).eq('sender_id',user.id).eq('status','pending').select('id');
    if(error){vesselNotice('Не удалось отменить заявку.','error');return;}
    window.__vesselSocialLoaded=false;
    await syncSocial(user);
    if(!cancelled?.some(row=>row.id===requestId)){vesselNotice('Заявка уже была обработана. Список обновлён.');return;}
    vesselNotice('Заявка отменена.','success');
  }));
  document.querySelectorAll('[data-accept-request]').forEach(button=>button.addEventListener('click',async()=>{
    if(!supabase||!user.id)return;
    const requestId=button.dataset.acceptRequest;
    const {data:accepted,error}=await supabase.from('friend_requests').update({status:'accepted',updated_at:new Date().toISOString()}).eq('id',requestId).eq('receiver_id',user.id).eq('status','pending').select('id,status').maybeSingle();
    if(error){vesselNotice('Не удалось принять заявку.','error');return;}
    window.__vesselSocialLoaded=false;
    await syncSocial(user);
    if(!accepted){vesselNotice('Заявка уже была обработана. Список обновлён.');return;}
    vesselNotice('Заявка принята.','success');
    render();
  }));
  document.querySelectorAll('[data-decline-request]').forEach(button=>button.addEventListener('click',async()=>{
    if(!supabase||!user.id)return;
    const requestId=button.dataset.declineRequest;
    const {data:declined,error}=await supabase.from('friend_requests').update({status:'declined',updated_at:new Date().toISOString()}).eq('id',requestId).eq('receiver_id',user.id).eq('status','pending').select('id,status').maybeSingle();
    if(error){vesselNotice('Не удалось отклонить заявку.','error');return;}
    window.__vesselSocialLoaded=false;
    await syncSocial(user);
    if(!declined){vesselNotice('Заявка уже была обработана. Список обновлён.');return;}
    vesselNotice('Заявка отклонена.');
    render();
  }));'''
main, changed = replace_once(main, old_cancel, new_cancel, 'friend-request action result checks')
main_changed |= changed

old_unfriend = '''    const {error}=await supabase.from('friendships').delete().or(`and(user_id.eq.${user.id},friend_id.eq.${friendId}),and(user_id.eq.${friendId},friend_id.eq.${user.id})`);
    if(error){vesselNotice(`Не удалось удалить друга: ${error.message}`,'error');return;}'''
new_unfriend = '''    const {data:removed,error}=await supabase.from('friendships').delete().or(`and(user_id.eq.${user.id},friend_id.eq.${friendId}),and(user_id.eq.${friendId},friend_id.eq.${user.id})`).select('user_id,friend_id');
    if(error){vesselNotice(`Не удалось удалить друга: ${error.message}`,'error');return;}
    if(!removed?.length){
      window.__vesselSocialLoaded=false;
      await syncSocial(user);
      vesselNotice('Пользователь уже удалён из друзей. Список обновлён.');
      return;
    }'''
main, changed = replace_once(main, old_unfriend, new_unfriend, 'unfriend result check')
main_changed |= changed

# Recover the ordinary Postgres-change channels as one authenticated group after a hard disconnect.
realtime_anchor = '''let messages = [];
function connectSupabaseRealtime(user) {'''
realtime_helpers = '''let messages = [];
function clearDataRealtimeRecovery(){
  if(dataRealtimeReconnectTimer){clearTimeout(dataRealtimeReconnectTimer);dataRealtimeReconnectTimer=null;}
  dataRealtimeReconnectAttempt=0;
  dataRealtimeRecoveryInFlight=false;
}
function handleDataRealtimeStatus(user,status){
  if(savedUser?.id!==user?.id||dataRealtimeRecoveryInFlight)return;
  if(['CHANNEL_ERROR','TIMED_OUT','CLOSED'].includes(status))scheduleDataRealtimeRecovery(user,status);
}
function scheduleDataRealtimeRecovery(user,status='CHANNEL_ERROR'){
  if(!supabase||!user?.id||savedUser?.id!==user.id||dataRealtimeReconnectTimer||dataRealtimeRecoveryInFlight)return;
  const sessionUserId=user.id;
  dataRealtimeReconnectAttempt=Math.min(dataRealtimeReconnectAttempt+1,5);
  const attempt=dataRealtimeReconnectAttempt;
  const delay=Math.min(1000*(2**(attempt-1)),10000);
  console.warn(`Data Realtime ${status}; recovery attempt ${attempt} scheduled`);
  dataRealtimeReconnectTimer=setTimeout(async()=>{
    dataRealtimeReconnectTimer=null;
    if(savedUser?.id!==sessionUserId)return;
    dataRealtimeRecoveryInFlight=true;
    const stale=window.__vesselRealtimeChannels||[];
    window.__vesselRealtimeChannels=null;
    try{
      if(stale.length)await Promise.allSettled(stale.map(channel=>supabase.removeChannel(channel)));
    }finally{
      dataRealtimeRecoveryInFlight=false;
    }
    if(savedUser?.id!==sessionUserId)return;
    window.__vesselSocialLoaded=false;
    window.__vesselDmThreadsLoaded=false;
    window.__vesselNotificationsLoaded=false;
    if(activeDmId)window.__vesselDmLoaded=false;
    connectSupabaseRealtime(user);
    const refreshes=[syncSocial(user),syncDmThreads(user),syncNotifications(user)];
    if(activeDmId)refreshes.push(loadDirectMessages(user,activeDmId));
    await Promise.allSettled(refreshes);
    if(savedUser?.id===sessionUserId)dataRealtimeReconnectAttempt=0;
  },delay);
}
function connectSupabaseRealtime(user) {'''
main, changed = replace_once(main, realtime_anchor, realtime_helpers, 'data realtime recovery helpers')
main_changed |= changed

connect_start = main.find('function connectSupabaseRealtime(user) {')
connect_end = main.find('\n\nlet savedUser = null;', connect_start)
if connect_start < 0 or connect_end < 0:
    raise SystemExit('realtime connect block not found')
connect_block = main[connect_start:connect_end]
legacy_count = connect_block.count('.subscribe()')
monitored = '.subscribe(status=>handleDataRealtimeStatus(user,status))'
if monitored not in connect_block:
    if legacy_count != 10:
        raise SystemExit(f'expected 10 unmonitored data realtime subscriptions, found {legacy_count}')
    connect_block = connect_block.replace('.subscribe()', monitored)
    main = main[:connect_start] + connect_block + main[connect_end:]
    main_changed = True
elif connect_block.count(monitored) != 10:
    raise SystemExit(f'expected 10 monitored data realtime subscriptions, found {connect_block.count(monitored)}')

reset_anchor = '''function resetAuthenticatedRuntime() {
  const channels=[...(window.__vesselRealtimeChannels||[]),voiceRoom,callChannel,callInboxChannel].filter(Boolean);'''
reset_replacement = '''function resetAuthenticatedRuntime() {
  clearDataRealtimeRecovery();
  dmMessagesSyncRevision++;
  const channels=[...(window.__vesselRealtimeChannels||[]),voiceRoom,callChannel,callInboxChannel].filter(Boolean);'''
main, changed = replace_once(main, reset_anchor, reset_replacement, 'authenticated realtime reset')
main_changed |= changed

# Fresh bootstrap must include the authenticated SECURITY INVOKER RPC the UI calls for DM history.
dm_rpc = '''-- Authenticated DM thread discovery. SECURITY INVOKER keeps RLS and profile column privacy in force.
create or replace function public.vessel_dm_threads()
returns table(peer_id uuid,username text,avatar_color text,status text,last_message_at timestamptz)
language sql
stable
security invoker
set search_path='pg_catalog','public'
as $$
  with peer_messages as (
    select
      case when dm.sender_id=(select auth.uid()) then dm.receiver_id else dm.sender_id end as peer_id,
      max(dm.created_at) as last_message_at
    from public.direct_messages dm
    where (select auth.uid()) is not null
      and dm.deleted_at is null
      and (dm.sender_id=(select auth.uid()) or dm.receiver_id=(select auth.uid()))
    group by 1
  )
  select p.id,p.username,p.avatar_color,p.status,pm.last_message_at
  from peer_messages pm
  join public.profiles p on p.id=pm.peer_id
  order by pm.last_message_at desc;
$$;
revoke all on function public.vessel_dm_threads() from public,anon;
grant execute on function public.vessel_dm_threads() to authenticated;

'''
if 'create or replace function public.vessel_dm_threads()' not in schema:
    schema_anchor = '-- Service-role-only RPCs used by JWT-protected Edge Functions.\n'
    if schema.count(schema_anchor) != 1:
        raise SystemExit('DM RPC bootstrap insertion anchor not found exactly once')
    schema = schema.replace(schema_anchor, dm_rpc + schema_anchor, 1)
    schema_changed = True
else:
    required_rpc = [
        'security invoker',
        "revoke all on function public.vessel_dm_threads() from public,anon;",
        'grant execute on function public.vessel_dm_threads() to authenticated;',
    ]
    if any(marker not in schema for marker in required_rpc):
        raise SystemExit('existing vessel_dm_threads bootstrap definition is not securely invoker-scoped')

if main_changed:
    main_path.write_text(main, encoding='utf-8')
    print('Applied social/DM/data-Realtime resilience patch')
else:
    print('Social/DM/data-Realtime resilience patch already applied')

if schema_changed:
    schema_path.write_text(schema, encoding='utf-8')
    print('Added secure vessel_dm_threads RPC to fresh bootstrap schema')
else:
    print('Secure vessel_dm_threads bootstrap RPC already present')
