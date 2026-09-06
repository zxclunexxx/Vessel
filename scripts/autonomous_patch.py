from pathlib import Path

main_path = Path('src/main.js')
schema_path = Path('server/schema.sql')
text = main_path.read_text(encoding='utf-8')
schema = schema_path.read_text(encoding='utf-8')
changed = False

def replace_once(old, new, label):
    global text, changed
    if new in text:
        return
    if old not in text:
        raise SystemExit(f'{label} anchor not found')
    text = text.replace(old, new, 1)
    changed = True

# Preserve the already-verified reciprocal friend-request handling.
friend_old = "  if(sendError){vesselNotice('Не удалось отправить заявку.','error');return;}"
friend_new = """  if(sendError){
    if(sendError.code==='23505'){
      window.__vesselSocialLoaded=false;
      await syncSocial(user);
      vesselNotice('Заявка уже существует или пользователь одновременно отправил заявку тебе. Открой раздел «Друзья».');
      return;
    }
    vesselNotice('Не удалось отправить заявку.','error');return;
  }"""
replace_once(friend_old, friend_new, 'friend request error handling')

index_marker = 'friend_requests_pending_pair_uidx'
if index_marker not in schema:
    schema_anchor = 'create index if not exists friend_requests_receiver_status_idx on public.friend_requests(receiver_id,status);\n'
    if schema_anchor not in schema:
        raise SystemExit('friend request schema anchor not found')
    schema = schema.replace(schema_anchor, schema_anchor + """create unique index if not exists friend_requests_pending_pair_uidx
on public.friend_requests (least(sender_id,receiver_id), greatest(sender_id,receiver_id))
where status='pending';
""", 1)
    changed = True

# DM sidebar must represent real conversation history rather than the current friendship list.
replace_once(
    "let friends = [];\nlet friendRequests = [];",
    "let friends = [];\nlet dmThreads = [];\nlet friendRequests = [];",
    'dm thread state'
)

sync_anchor = """async function syncNotifications(user) {
  if (!supabase || !user?.id || window.__vesselNotificationsLoaded) return;
"""
sync_insert = """async function syncDmThreads(user) {
  if (!supabase || !user?.id || window.__vesselDmThreadsLoaded) return;
  const {data,error}=await supabase.rpc('vessel_dm_threads');
  if(error){console.warn('DM thread sync failed',error);vesselNotice('Не удалось загрузить список личных чатов.','error');return;}
  dmThreads=(data||[]).map(row=>({id:row.peer_id,username:row.username||'Пользователь',avatar_color:row.avatar_color||'#8b7cff',status:row.status||'online',last_message_at:row.last_message_at}));
  window.__vesselDmThreadsLoaded=true;
  if(document.querySelector('#app'))render();
}
async function syncNotifications(user) {
  if (!supabase || !user?.id || window.__vesselNotificationsLoaded) return;
"""
replace_once(sync_anchor, sync_insert, 'dm thread sync function')

realtime_old = """    supabase.channel(`vessel-dm-${user.id}`).on('postgres_changes',{event:'INSERT',schema:'public',table:'direct_messages'},payload=>{
      const row=payload.new;
      if(activeDmId && (row.sender_id===activeDmId || row.receiver_id===activeDmId)){ window.__vesselDmLoaded=false; loadDirectMessages(user,activeDmId); }
    }).subscribe(),"""
realtime_new = """    supabase.channel(`vessel-dm-${user.id}`).on('postgres_changes',{event:'INSERT',schema:'public',table:'direct_messages'},payload=>{
      const row=payload.new;
      window.__vesselDmThreadsLoaded=false;
      syncDmThreads(user).catch(error=>console.warn('DM thread realtime refresh failed',error));
      if(activeDmId && (row.sender_id===activeDmId || row.receiver_id===activeDmId)){ window.__vesselDmLoaded=false; loadDirectMessages(user,activeDmId); }
    }).subscribe(),"""
replace_once(realtime_old, realtime_new, 'dm thread realtime refresh')

render_sync_old = "syncSocial(user); syncNotifications(user);"
render_sync_new = "syncSocial(user); syncDmThreads(user); syncNotifications(user);"
replace_once(render_sync_old, render_sync_new, 'dm thread render sync')

dm_list_old = """  const dmList=friends.length
    ? friends.map(friend=>`<button class="channel dm ${activeDmId===friend.id?'active':''}" data-dm-id="${friend.id}" data-dm="${escapeHtml(friend.username)}"><div class="mini-avatar" style="background:${friend.avatar_color||'#8b7cff'}">${(friend.username||'?')[0].toUpperCase()}</div> ${escapeHtml(friend.username)} <em></em></button>`).join('')
    : `<div class="dm-empty">Пока нет личных чатов</div>`;"""
dm_list_new = """  const dmList=dmThreads.length
    ? dmThreads.map(thread=>`<button class="channel dm ${activeDmId===thread.id?'active':''}" data-dm-id="${thread.id}" data-dm="${escapeHtml(thread.username)}"><div class="mini-avatar" style="background:${thread.avatar_color||'#8b7cff'}">${(thread.username||'?')[0].toUpperCase()}</div> ${escapeHtml(thread.username)} <em></em></button>`).join('')
    : `<div class="dm-empty">Пока нет личных чатов</div>`;"""
replace_once(dm_list_old, dm_list_new, 'real DM conversation list')

send_old = """if(activeDmId){ const peerId=activeDmId; const {error}=await supabase.from('direct_messages').insert({sender_id:user.id,receiver_id:peerId,body:text}); if(error){vesselNotice(`Не удалось отправить личное сообщение: ${error.message}`,'error');return;} await loadDirectMessages(user,peerId); }"""
send_new = """if(activeDmId){ const peerId=activeDmId; const {error}=await supabase.from('direct_messages').insert({sender_id:user.id,receiver_id:peerId,body:text}); if(error){vesselNotice(`Не удалось отправить личное сообщение: ${error.message}`,'error');return;} window.__vesselDmThreadsLoaded=false; await Promise.all([loadDirectMessages(user,peerId),syncDmThreads(user)]); }"""
replace_once(send_old, send_new, 'dm send thread refresh')

attachment_old = """        await loadDirectMessages(user,peerId);
      } else {"""
attachment_new = """        window.__vesselDmThreadsLoaded=false;
        await Promise.all([loadDirectMessages(user,peerId),syncDmThreads(user)]);
      } else {"""
replace_once(attachment_old, attachment_new, 'dm attachment thread refresh')

# Snapshot the safe, auth-scoped DM-thread RPC. It intentionally exposes no email address.
rpc_marker = 'create or replace function public.vessel_dm_threads()'
if rpc_marker not in schema:
    schema += """

-- Safe list of direct-message peers for the authenticated user. This avoids broadening
-- profiles RLS (profiles also stores email) while keeping old conversations discoverable.
create or replace function public.vessel_dm_threads()
returns table(peer_id uuid, username text, avatar_color text, status text, last_message_at timestamptz)
language sql
security definer
set search_path = public
stable
as $$
  with peer_messages as (
    select
      case when dm.sender_id = auth.uid() then dm.receiver_id else dm.sender_id end as peer_id,
      max(dm.created_at) as last_message_at
    from public.direct_messages dm
    where auth.uid() is not null
      and (dm.sender_id = auth.uid() or dm.receiver_id = auth.uid())
    group by 1
  )
  select p.id, p.username, p.avatar_color, p.status, pm.last_message_at
  from peer_messages pm
  join public.profiles p on p.id = pm.peer_id
  order by pm.last_message_at desc;
$$;
revoke all on function public.vessel_dm_threads() from public;
grant execute on function public.vessel_dm_threads() to authenticated;
"""
    changed = True

for marker in [friend_new, 'let dmThreads = [];', "supabase.rpc('vessel_dm_threads')", 'const dmList=dmThreads.length', rpc_marker, index_marker]:
    source = schema if marker in (rpc_marker,index_marker) else text
    if marker not in source:
        raise SystemExit(f'missing expected Vessel marker after patch: {marker[:80]}')

if changed:
    main_path.write_text(text, encoding='utf-8')
    schema_path.write_text(schema, encoding='utf-8')
    print('Applied Vessel DM-thread and friend-request hardening')
else:
    print('Vessel DM-thread and friend-request hardening already applied; nothing to change')
