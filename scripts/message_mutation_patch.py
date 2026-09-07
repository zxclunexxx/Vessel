from pathlib import Path

main_path = Path('src/main.js')
style_path = Path('src/style.css')
schema_path = Path('server/schema.sql')

text = main_path.read_text(encoding='utf-8')
style = style_path.read_text(encoding='utf-8')
schema = schema_path.read_text(encoding='utf-8')
changed = False
style_changed = False
schema_changed = False


def replace_once(source, old, new, label):
    if new in source:
        print(f'{label}: already applied')
        return source, False
    if old not in source:
        raise SystemExit(f'{label}: expected source or patched form not found')
    return source.replace(old, new, 1), True


# Message objects need stable ids/authors so the UI can safely expose mutation controls.
old = """function attachmentMarkup(attachments=[]) {
  return (attachments||[]).map(file=>`<button class=\"attachment-link\" data-attachment-path=\"${escapeHtml(file.path||'')}\">📎 ${escapeHtml(file.name||'Файл')}</button>`).join('');
}
async function openAttachment(path) {
"""
new = """function attachmentMarkup(attachments=[]) {
  return (attachments||[]).map(file=>`<button class=\"attachment-link\" data-attachment-path=\"${escapeHtml(file.path||'')}\">📎 ${escapeHtml(file.name||'Файл')}</button>`).join('');
}
function messageMarkup(message,user,canMutate=true) {
  const own=Boolean(canMutate&&message?.id&&message.authorId===user?.id);
  const edited=message?.editedAt?' · изменено':'';
  const actions=own?`<span class=\"message-actions\"><button type=\"button\" data-edit-message=\"${escapeHtml(message.id)}\" title=\"Редактировать сообщение\">✎</button><button type=\"button\" data-delete-message=\"${escapeHtml(message.id)}\" title=\"Удалить сообщение\">×</button></span>`:'';
  return `<article class=\"message\" data-message-id=\"${escapeHtml(message?.id||'')}\"><div class=\"avatar\" style=\"background:${escapeHtml(message?.color||'#8b7cff')}\">${escapeHtml(message?.name?.[0]||'?')}</div><div class=\"message-content\"><div class=\"message-meta\"><b>${escapeHtml(message?.name||'Пользователь')}</b><time>${escapeHtml(message?.time||'')}${edited}</time>${actions}</div><p>${escapeHtml(message?.text||'')}</p>${attachmentMarkup(message?.attachments)}</div></article>`;
}
async function openAttachment(path) {
"""
text, did = replace_once(text, old, new, 'message render helper')
changed |= did

old = """  const {data,error} = await supabase.from('messages').select('body,attachments,created_at,profiles(username,avatar_color)').eq('channel_id',channelId).order('created_at',{ascending:false}).limit(100);
  if(savedUser?.id!==sessionUserId||activeDmId||activeChannelId!==channelId||activeChannelKind!=='text')return;
  if(activeDmId||activeChannelId!==channelId||activeChannelKind!=='text')return;
  if(error){vesselNotice('Не удалось загрузить сообщения канала.','error');return;}
  messages = (data||[]).reverse().map(m=>({name:m.profiles?.username||'Участник',time:new Date(m.created_at).toLocaleString('ru-RU'),color:m.profiles?.avatar_color||'#8b7cff',text:m.body,attachments:m.attachments||[]}));
"""
new = """  const {data,error} = await supabase.from('messages').select('id,author_id,body,attachments,created_at,edited_at,profiles(username,avatar_color)').eq('channel_id',channelId).order('created_at',{ascending:false}).limit(100);
  if(savedUser?.id!==sessionUserId||activeDmId||activeChannelId!==channelId||activeChannelKind!=='text')return;
  if(activeDmId||activeChannelId!==channelId||activeChannelKind!=='text')return;
  if(error){vesselNotice('Не удалось загрузить сообщения канала.','error');return;}
  messages = (data||[]).reverse().map(m=>({id:m.id,authorId:m.author_id,name:m.profiles?.username||'Участник',time:new Date(m.created_at).toLocaleString('ru-RU'),editedAt:m.edited_at||null,color:m.profiles?.avatar_color||'#8b7cff',text:m.body,attachments:m.attachments||[]}));
"""
text, did = replace_once(text, old, new, 'channel message identity load')
changed |= did

old = """  const {data,error} = await supabase.from('direct_messages').select('id,sender_id,receiver_id,body,attachments,created_at,profiles!direct_messages_sender_id_fkey(username,avatar_color)').or(`and(sender_id.eq.${dmLoadUserId},receiver_id.eq.${friendId}),and(sender_id.eq.${friendId},receiver_id.eq.${dmLoadUserId})`).order('created_at',{ascending:false}).limit(100);
  if(savedUser?.id!==dmLoadUserId||activeDmId!==friendId)return;
  if(activeDmId!==friendId)return;
  if(error){vesselNotice('Не удалось загрузить личные сообщения.','error');return;}
  dmMessages = (data || []).reverse().map(row => ({name:row.profiles?.username || 'Пользователь',time:new Date(row.created_at).toLocaleString('ru-RU'),color:row.profiles?.avatar_color || '#8b7cff',text:row.body,attachments:row.attachments||[]}));
"""
new = """  const {data,error} = await supabase.from('direct_messages').select('id,sender_id,receiver_id,body,attachments,created_at,edited_at,deleted_at,profiles!direct_messages_sender_id_fkey(username,avatar_color)').or(`and(sender_id.eq.${dmLoadUserId},receiver_id.eq.${friendId}),and(sender_id.eq.${friendId},receiver_id.eq.${dmLoadUserId})`).is('deleted_at',null).order('created_at',{ascending:false}).limit(100);
  if(savedUser?.id!==dmLoadUserId||activeDmId!==friendId)return;
  if(activeDmId!==friendId)return;
  if(error){vesselNotice('Не удалось загрузить личные сообщения.','error');return;}
  dmMessages = (data || []).reverse().map(row => ({id:row.id,authorId:row.sender_id,name:row.profiles?.username || 'Пользователь',time:new Date(row.created_at).toLocaleString('ru-RU'),editedAt:row.edited_at||null,color:row.profiles?.avatar_color || '#8b7cff',text:row.body,attachments:row.attachments||[]}));
"""
text, did = replace_once(text, old, new, 'direct message identity load')
changed |= did

# Mutations capture the current chat/channel before awaiting, then re-check it to
# avoid editing/deleting a stale context after the user switches conversations.
old = """async function cleanupFailedAttachment(attachment){
  if(!supabase||!attachment?.path)return;
  try{await supabase.storage.from('vessel-files').remove([attachment.path]);}catch(error){console.warn('Attachment cleanup failed',error);}
}

function removeVoicePeer(peerId) {
"""
new = """async function cleanupFailedAttachment(attachment){
  if(!supabase||!attachment?.path)return;
  try{await supabase.storage.from('vessel-files').remove([attachment.path]);}catch(error){console.warn('Attachment cleanup failed',error);}
}
async function editOwnMessage(user,messageId){
  if(!supabase||!user?.id||!messageId)return;
  const sessionUserId=user.id;
  const peerId=activeDmId||null;
  const channelId=!peerId&&activeChannelKind==='text'?activeChannelId:null;
  const source=peerId?dmMessages:messages;
  const message=source.find(item=>item.id===messageId);
  if(!message||message.authorId!==sessionUserId)return;
  if(peerId&&(await verifyDirectMessageAccess(user,peerId))!==true)return;
  if(channelId&&(await verifyChannelAccess(user,channelId))!==true)return;
  if(savedUser?.id!==sessionUserId||activeDmId!==peerId||(!peerId&&activeChannelId!==channelId))return;
  const value=await vesselPrompt('Редактировать сообщение',message.text||'','Текст сообщения');
  const body=String(value||'').trim();
  if(!body||body===message.text)return;
  if(body.length>4000){vesselNotice('Сообщение не может быть длиннее 4000 символов.','error');return;}
  if(savedUser?.id!==sessionUserId||activeDmId!==peerId||(!peerId&&activeChannelId!==channelId))return;
  const editedAt=new Date().toISOString();
  let result;
  if(peerId){
    if((await verifyDirectMessageAccess(user,peerId,{notify:false}))!==true)return;
    result=await supabase.from('direct_messages').update({body,edited_at:editedAt}).eq('id',messageId).eq('sender_id',sessionUserId).is('deleted_at',null).select('id,body,edited_at').maybeSingle();
  }else{
    if(!channelId||(await verifyChannelAccess(user,channelId,{notify:false}))!==true)return;
    result=await supabase.from('messages').update({body,edited_at:editedAt}).eq('id',messageId).eq('author_id',sessionUserId).eq('channel_id',channelId).select('id,body,edited_at').maybeSingle();
  }
  if(savedUser?.id!==sessionUserId)return;
  if(result.error||!result.data){vesselNotice('Не удалось отредактировать сообщение.','error');return;}
  const liveSource=peerId?dmMessages:messages;
  const live=liveSource.find(item=>item.id===messageId);
  if(live){live.text=result.data.body;live.editedAt=result.data.edited_at||editedAt;}
  render();
}
async function deleteOwnMessage(user,messageId){
  if(!supabase||!user?.id||!messageId)return;
  const sessionUserId=user.id;
  const peerId=activeDmId||null;
  const channelId=!peerId&&activeChannelKind==='text'?activeChannelId:null;
  const source=peerId?dmMessages:messages;
  const message=source.find(item=>item.id===messageId);
  if(!message||message.authorId!==sessionUserId)return;
  if(peerId&&(await verifyDirectMessageAccess(user,peerId))!==true)return;
  if(channelId&&(await verifyChannelAccess(user,channelId))!==true)return;
  if(!await vesselConfirm('Удалить сообщение?','Это действие нельзя отменить.'))return;
  if(savedUser?.id!==sessionUserId||activeDmId!==peerId||(!peerId&&activeChannelId!==channelId))return;
  let result;
  if(peerId){
    result=await supabase.from('direct_messages').delete().eq('id',messageId).eq('sender_id',sessionUserId).select('id');
  }else{
    if(!channelId)return;
    result=await supabase.from('messages').delete().eq('id',messageId).eq('author_id',sessionUserId).eq('channel_id',channelId).select('id');
  }
  if(savedUser?.id!==sessionUserId)return;
  if(result.error||!result.data?.some(row=>row.id===messageId)){vesselNotice('Не удалось удалить сообщение.','error');return;}
  if(peerId&&activeDmId===peerId)dmMessages=dmMessages.filter(item=>item.id!==messageId);
  if(!peerId&&activeChannelId===channelId)messages=messages.filter(item=>item.id!==messageId);
  Promise.allSettled((message.attachments||[]).map(cleanupFailedAttachment)).catch(()=>{});
  if(peerId){window.__vesselDmThreadsLoaded=false;syncDmThreads(user).catch(error=>console.warn('DM thread refresh after delete failed',error));}
  render();
}

function removeVoicePeer(peerId) {
"""
text, did = replace_once(text, old, new, 'message mutation functions')
changed |= did

old = """    supabase.channel(`vessel-dm-${user.id}`).on('postgres_changes',{event:'INSERT',schema:'public',table:'direct_messages'},payload=>{
      if(savedUser?.id!==user.id)return;
      const row=payload.new;
      window.__vesselDmThreadsLoaded=false;
      syncDmThreads(user).catch(error=>console.warn('DM thread realtime refresh failed',error));
      if(activeDmId && (row.sender_id===activeDmId || row.receiver_id===activeDmId)){ window.__vesselDmLoaded=false; loadDirectMessages(user,activeDmId); }
    }).subscribe(),
"""
new = """    supabase.channel(`vessel-dm-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'direct_messages'},payload=>{
      if(savedUser?.id!==user.id)return;
      if(payload.eventType==='DELETE'){
        const deletedId=payload.old?.id;
        if(deletedId&&dmMessages.some(item=>item.id===deletedId)){
          dmMessages=dmMessages.filter(item=>item.id!==deletedId);
          window.__vesselDmThreadsLoaded=false;
          syncDmThreads(user).catch(error=>console.warn('DM thread delete refresh failed',error));
          render();
        }
        return;
      }
      const row=payload.new;
      if(!row?.id||![row.sender_id,row.receiver_id].includes(user.id))return;
      window.__vesselDmThreadsLoaded=false;
      syncDmThreads(user).catch(error=>console.warn('DM thread realtime refresh failed',error));
      if(activeDmId && (row.sender_id===activeDmId || row.receiver_id===activeDmId)){ window.__vesselDmLoaded=false; loadDirectMessages(user,activeDmId); }
    }).subscribe(),
"""
text, did = replace_once(text, old, new, 'DM mutation realtime')
changed |= did

old = """    supabase.channel(`vessel-channel-messages-${user.id}`).on('postgres_changes',{event:'INSERT',schema:'public',table:'messages'},payload=>{
      if(savedUser?.id!==user.id)return;
      if(payload.new.channel_id===activeChannelId && payload.new.author_id!==user.id)loadChannelMessages(activeChannelId).catch(error=>console.warn('Message refresh failed',error));
    }).subscribe(),
"""
new = """    supabase.channel(`vessel-channel-messages-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'messages'},payload=>{
      if(savedUser?.id!==user.id)return;
      if(payload.eventType==='DELETE'){
        const deletedId=payload.old?.id;
        if(deletedId&&messages.some(item=>item.id===deletedId)){messages=messages.filter(item=>item.id!==deletedId);render();}
        return;
      }
      const row=payload.new;
      if(row?.channel_id===activeChannelId)loadChannelMessages(activeChannelId).catch(error=>console.warn('Message refresh failed',error));
    }).subscribe(),
"""
text, did = replace_once(text, old, new, 'channel mutation realtime')
changed |= did

old = """${(activeDmId?dmMessages:messages).map(m => `<article class=\"message\"><div class=\"avatar\" style=\"background:${escapeHtml(m.color||'#8b7cff')}\">${escapeHtml(m.name?.[0]||'?')}</div><div><div class=\"message-meta\"><b>${escapeHtml(m.name)}</b><time>${escapeHtml(m.time)}</time></div><p>${escapeHtml(m.text)}</p>${attachmentMarkup(m.attachments)}</div></article>`).join('')}"""
new = """${(activeDmId?dmMessages:messages).map(m=>messageMarkup(m,user,!activeDmId||activeDmIsFriend)).join('')}"""
text, did = replace_once(text, old, new, 'message mutation controls render')
changed |= did

old = """      if(!activeDmId&&activeChannelId===channelId&&activeChannelKind==='text')messages.push({name:user.name,time:'только что',color:user.avatarColor||'#39d9a6',text});
"""
new = """      if(!activeDmId&&activeChannelId===channelId&&activeChannelKind==='text')await loadChannelMessages(channelId);
"""
text, did = replace_once(text, old, new, 'channel send authoritative reload')
changed |= did

old = """        if(!activeDmId&&activeChannelId===targetChannelId&&activeChannelKind==='text'){
          messages.push({name:user.name,time:'только что',color:user.avatarColor||'#39d9a6',text:body,attachments:[attachment]});
        }
"""
new = """        if(!activeDmId&&activeChannelId===targetChannelId&&activeChannelKind==='text'){
          await loadChannelMessages(targetChannelId);
        }
"""
text, did = replace_once(text, old, new, 'channel attachment authoritative reload')
changed |= did

old = """  document.querySelectorAll('[data-attachment-path]').forEach(button=>button.addEventListener('click',()=>openAttachment(button.dataset.attachmentPath)));
  document.querySelectorAll('[data-remove-friend]').forEach(button=>button.addEventListener('click',async()=>{
"""
new = """  document.querySelectorAll('[data-attachment-path]').forEach(button=>button.addEventListener('click',()=>openAttachment(button.dataset.attachmentPath)));
  document.querySelectorAll('[data-edit-message]').forEach(button=>button.addEventListener('click',()=>editOwnMessage(user,button.dataset.editMessage)));
  document.querySelectorAll('[data-delete-message]').forEach(button=>button.addEventListener('click',()=>deleteOwnMessage(user,button.dataset.deleteMessage)));
  document.querySelectorAll('[data-remove-friend]').forEach(button=>button.addEventListener('click',async()=>{
"""
text, did = replace_once(text, old, new, 'message mutation event handlers')
changed |= did

# Compact controls stay hidden until hover/focus and remain usable on touch devices.
style_marker = '.message-actions{'
if style_marker not in style:
    style += "\n.message-content{min-width:0;flex:1}.message-actions{display:inline-flex;gap:3px;margin-left:auto;opacity:0;transition:.16s}.message:hover .message-actions,.message-actions:focus-within{opacity:1}.message-actions button{border:0;background:#252a38;color:#8f97ab;width:26px;height:26px;border-radius:7px;cursor:pointer;font:600 14px Inter}.message-actions button:hover{background:#32394c;color:#fff}.message-actions button[data-delete-message]:hover{background:#3b202c;color:#ff9db2}@media(max-width:760px){.message-actions{opacity:1}}\n"
    style_changed = True
else:
    print('message mutation styles: already applied')

message_insert_policy = """create policy \"members can send channel messages\" on public.messages for insert to authenticated with check(
  author_id=(select auth.uid()) and (
    exists(select 1 from public.server_members m join public.channels c on c.server_id=m.server_id where c.id=messages.channel_id and m.user_id=(select auth.uid()))
    or exists(select 1 from public.channels c join public.servers s on s.id=c.server_id where c.id=messages.channel_id and s.owner_id=(select auth.uid()))
  )
);
"""
message_mutation_schema = """
create policy \"authors can update own channel messages\" on public.messages for update to authenticated using(
  author_id=(select auth.uid()) and (
    exists(select 1 from public.server_members m join public.channels c on c.server_id=m.server_id where c.id=messages.channel_id and m.user_id=(select auth.uid()))
    or exists(select 1 from public.channels c join public.servers s on s.id=c.server_id where c.id=messages.channel_id and s.owner_id=(select auth.uid()))
  )
) with check(
  author_id=(select auth.uid()) and (
    exists(select 1 from public.server_members m join public.channels c on c.server_id=m.server_id where c.id=messages.channel_id and m.user_id=(select auth.uid()))
    or exists(select 1 from public.channels c join public.servers s on s.id=c.server_id where c.id=messages.channel_id and s.owner_id=(select auth.uid()))
  )
);
create policy \"authors can delete own channel messages\" on public.messages for delete to authenticated using(
  author_id=(select auth.uid()) and (
    exists(select 1 from public.server_members m join public.channels c on c.server_id=m.server_id where c.id=messages.channel_id and m.user_id=(select auth.uid()))
    or exists(select 1 from public.channels c join public.servers s on s.id=c.server_id where c.id=messages.channel_id and s.owner_id=(select auth.uid()))
  )
);
revoke update on table public.messages from authenticated;
grant update (body, attachments, edited_at) on table public.messages to authenticated;
"""
if 'authors can update own channel messages' not in schema:
    if message_insert_policy not in schema:
        raise SystemExit('channel message insert policy marker missing from schema')
    schema = schema.replace(message_insert_policy, message_insert_policy + message_mutation_schema, 1)
    schema_changed = True
else:
    print('channel message mutation schema: already applied')

old_dm_read = 'create policy "dm participants can read" on public.direct_messages for select to authenticated using(sender_id=(select auth.uid()) or receiver_id=(select auth.uid()));'
new_dm_read = """create policy \"dm participants can read\" on public.direct_messages for select to authenticated using(
  deleted_at is null and (sender_id=(select auth.uid()) or receiver_id=(select auth.uid()))
);"""
schema, did = replace_once(schema, old_dm_read, new_dm_read, 'soft-deleted DM visibility schema')
schema_changed |= did

old_dm_update = 'create policy "senders can update dms" on public.direct_messages for update to authenticated using(sender_id=(select auth.uid())) with check(sender_id=(select auth.uid()));'
new_dm_update = old_dm_update + '\ncreate policy "senders can delete own dms" on public.direct_messages for delete to authenticated using(sender_id=(select auth.uid()));'
schema, did = replace_once(schema, old_dm_update, new_dm_update, 'own DM delete schema')
schema_changed |= did

rpc_marker = 'create or replace function public.vessel_dm_threads()'
if rpc_marker not in schema:
    grant_marker = 'grant update (body, attachments, edited_at, deleted_at) on table public.direct_messages to authenticated;'
    rpc = """

create or replace function public.vessel_dm_threads()
returns table(peer_id uuid, username text, avatar_color text, status text, last_message_at timestamptz)
language sql
stable
security invoker
set search_path='pg_catalog','public'
as $$
  with peer_messages as (
    select
      case when dm.sender_id = auth.uid() then dm.receiver_id else dm.sender_id end as peer_id,
      max(dm.created_at) as last_message_at
    from public.direct_messages dm
    where auth.uid() is not null
      and dm.deleted_at is null
      and (dm.sender_id = auth.uid() or dm.receiver_id = auth.uid())
    group by 1
  )
  select p.id, p.username, p.avatar_color, p.status, pm.last_message_at
  from peer_messages pm
  join public.profiles p on p.id = pm.peer_id
  order by pm.last_message_at desc;
$$;
revoke all on function public.vessel_dm_threads() from public, anon;
grant execute on function public.vessel_dm_threads() to authenticated, service_role;
"""
    if grant_marker not in schema:
        raise SystemExit('DM identity grant marker missing from schema')
    schema = schema.replace(grant_marker, grant_marker + rpc, 1)
    schema_changed = True
else:
    print('DM thread RPC schema snapshot: already present')

required_main = [
    "select('id,author_id,body,attachments,created_at,edited_at,profiles(username,avatar_color)')",
    "select('id,sender_id,receiver_id,body,attachments,created_at,edited_at,deleted_at,profiles!direct_messages_sender_id_fkey(username,avatar_color)')",
    "event:'*',schema:'public',table:'messages'",
    "event:'*',schema:'public',table:'direct_messages'",
    'data-edit-message',
    'data-delete-message',
    'async function editOwnMessage',
    'async function deleteOwnMessage',
]
for marker in required_main:
    if marker not in text:
        raise SystemExit(f'missing message mutation marker: {marker}')

required_schema = [
    'authors can update own channel messages',
    'authors can delete own channel messages',
    'grant update (body, attachments, edited_at) on table public.messages to authenticated;',
    'senders can delete own dms',
    'dm.deleted_at is null',
]
for marker in required_schema:
    if marker not in schema:
        raise SystemExit(f'missing message mutation schema marker: {marker}')

if changed:
    main_path.write_text(text, encoding='utf-8')
    print('Applied message edit/delete UI and realtime mutations')
else:
    print('Message edit/delete UI and realtime mutations already applied')
if style_changed:
    style_path.write_text(style, encoding='utf-8')
    print('Applied message mutation styles')
if schema_changed:
    schema_path.write_text(schema, encoding='utf-8')
    print('Aligned schema snapshot with message mutation security')
