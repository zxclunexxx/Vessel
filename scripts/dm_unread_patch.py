from pathlib import Path

# Persistent DM unread state reuses server-generated direct_message notifications.
main_path = Path('src/main.js')
style_path = Path('src/style.css')
main = main_path.read_text(encoding='utf-8')
style = style_path.read_text(encoding='utf-8')
changed = False


def replace_once_or_already(source, old, new, label):
    global changed
    if new in source:
        print(f'{label}: already applied')
        return source
    if old not in source:
        raise SystemExit(f'{label}: expected source not found')
    changed = True
    print(f'{label}: applied')
    return source.replace(old, new, 1)


main = replace_once_or_already(
    main,
    """  const {data,error}=await supabase.from('notifications').select('id,type,title,body,data,read_at,created_at').eq('user_id',user.id).order('created_at',{ascending:false}).limit(30);""",
    """  const {data,error}=await supabase.from('notifications').select('id,type,title,body,data,read_at,created_at').eq('user_id',user.id).order('created_at',{ascending:false}).limit(100);""",
    'load more notification state for unread badges'
)

helper_marker = "function unreadDirectMessageCount(peerId)"
if helper_marker not in main:
    anchor = """async function loadDirectMessages(user, friendId) {"""
    if anchor not in main:
        raise SystemExit('DM unread helpers: insertion anchor not found')
    helpers = """function unreadDirectMessageCount(peerId) {
  if(!peerId)return 0;
  return notifications.filter(item=>!item.read_at&&item.type==='direct_message'&&item.data?.sender_id===peerId).length;
}
async function markDirectMessageNotificationsRead(user,peerId,notificationId=null) {
  if(!supabase||!user?.id||!peerId)return;
  const sessionUserId=user.id;
  if(savedUser?.id!==sessionUserId)return;
  const localUnread=notifications.filter(item=>!item.read_at&&item.type==='direct_message'&&item.data?.sender_id===peerId&&(!notificationId||item.id===notificationId));
  if(notificationId&&!localUnread.length)return;
  const readAt=new Date().toISOString();
  let query=supabase.from('notifications').update({read_at:readAt}).eq('user_id',sessionUserId).eq('type','direct_message').is('read_at',null);
  const result=notificationId
    ? await query.eq('id',notificationId).select('id')
    : await query.contains('data',{sender_id:peerId}).select('id');
  if(savedUser?.id!==sessionUserId)return;
  if(result.error){console.warn('DM notification read update failed',result.error);return;}
  const updatedIds=new Set((result.data||[]).map(row=>row.id));
  if(!updatedIds.size)return;
  notifications=notifications.map(item=>updatedIds.has(item.id)&&!item.read_at?{...item,read_at:readAt}:item);
  render();
}
"""
    main = main.replace(anchor, helpers + anchor, 1)
    changed = True
    print('DM unread helpers: applied')
else:
    print('DM unread helpers: already applied')

old_realtime = """      .on('postgres_changes',{event:'INSERT',schema:'public',table:'notifications',filter:`user_id=eq.${user.id}`},payload=>{
        if(savedUser?.id!==user.id)return;
        const row=payload.new;
        notificationsSyncRevision++;
        window.__vesselNotificationsLoaded=true;
        notifications=[row,...notifications.filter(item=>item.id!==row.id)];
        render();
      })"""
new_realtime = """      .on('postgres_changes',{event:'INSERT',schema:'public',table:'notifications',filter:`user_id=eq.${user.id}`},async payload=>{
        if(savedUser?.id!==user.id)return;
        const row=payload.new;
        notificationsSyncRevision++;
        window.__vesselNotificationsLoaded=true;
        notifications=[row,...notifications.filter(item=>item.id!==row.id)];
        if(row?.type==='direct_message'&&row.data?.sender_id===activeDmId&&!friendsOpen){
          await markDirectMessageNotificationsRead(user,activeDmId,row.id);
          return;
        }
        render();
      })"""
main = replace_once_or_already(main, old_realtime, new_realtime, 'active DM auto-read realtime notification')

old_dm_list = """  const dmList=dmThreads.length
    ? dmThreads.map(thread=>`<button class=\"channel dm ${activeDmId===thread.id?'active':''}\" data-dm-id=\"${thread.id}\" data-dm=\"${escapeHtml(thread.username)}\"><div class=\"mini-avatar\" style=\"background:${thread.avatar_color||'#8b7cff'}\">${(thread.username||'?')[0].toUpperCase()}</div> ${escapeHtml(thread.username)} <em></em></button>`).join('')
    : `<div class=\"dm-empty\">Пока нет личных чатов</div>`;"""
new_dm_list = """  const dmList=dmThreads.length
    ? dmThreads.map(thread=>{const unread=unreadDirectMessageCount(thread.id);return `<button class=\"channel dm ${activeDmId===thread.id?'active':''}\" data-dm-id=\"${thread.id}\" data-dm=\"${escapeHtml(thread.username)}\"><div class=\"mini-avatar\" style=\"background:${thread.avatar_color||'#8b7cff'}\">${(thread.username||'?')[0].toUpperCase()}</div> ${escapeHtml(thread.username)} ${unread?`<em class=\"dm-unread\" title=\"Непрочитанных: ${unread}\">${unread>99?'99+':unread}</em>`:''}</button>`;}).join('')
    : `<div class=\"dm-empty\">Пока нет личных чатов</div>`;"""
main = replace_once_or_already(main, old_dm_list, new_dm_list, 'DM unread count badge')

old_notification_center = """    const unreadIds=notifications.filter(item=>!item.read_at).map(item=>item.id).filter(Boolean);"""
new_notification_center = """    const unreadIds=notifications.filter(item=>!item.read_at&&item.type!=='direct_message').map(item=>item.id).filter(Boolean);"""
main = replace_once_or_already(main, old_notification_center, new_notification_center, 'keep DM unread until chat is opened')

old_dm_click = """  document.querySelectorAll('[data-dm]').forEach(button=>button.addEventListener('click',()=>{currentDm=button.dataset.dm;activeDmId=button.dataset.dmId||null;friendsOpen=false;window.__vesselDmLoaded=false;render();}));"""
new_dm_click = """  document.querySelectorAll('[data-dm]').forEach(button=>button.addEventListener('click',async()=>{currentDm=button.dataset.dm;activeDmId=button.dataset.dmId||null;friendsOpen=false;window.__vesselDmLoaded=false;render();if(activeDmId)await markDirectMessageNotificationsRead(user,activeDmId);}));"""
main = replace_once_or_already(main, old_dm_click, new_dm_click, 'mark DM read when opened')

old_style = ".channel.dm em{margin-left:auto;width:7px;height:7px;border-radius:50%;background:#42d39a}"
new_style = ".channel.dm em.dm-unread{margin-left:auto;min-width:18px;height:18px;padding:0 5px;border-radius:9px;background:#786cff;color:#fff;font-style:normal;font-size:10px;font-weight:800;display:grid;place-items:center}"
style = replace_once_or_already(style, old_style, new_style, 'DM unread badge styling')

if changed:
    main_path.write_text(main, encoding='utf-8')
    style_path.write_text(style, encoding='utf-8')
    print('DM unread patch applied')
else:
    print('DM unread patch already applied; nothing to change')
