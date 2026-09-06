from pathlib import Path

path = Path('src/main.js')
text = path.read_text(encoding='utf-8')
changed = False

NOTIFICATION_MARKERS = [
    'let notificationsSyncRevision = 0;',
    'const revision=++notificationsSyncRevision;',
    'if(savedUser?.id!==user.id||revision!==notificationsSyncRevision)return;',
    'window.__vesselNotificationsLoaded=false;',
    'notificationsSyncRevision++;',
    "notifications=[row,...notifications.filter(item=>item.id!==row.id)];",
]

NOTIFICATION_READ_MARKERS = [
    'const sessionUserId=user.id;',
    'const unreadIds=notifications.filter(item=>!item.read_at).map(item=>item.id).filter(Boolean);',
    'const readAt=new Date().toISOString();',
    ".eq('user_id',sessionUserId).in('id',unreadIds).is('read_at',null).select('id')",
    'if(savedUser?.id!==sessionUserId)return;',
    "if(error){console.warn('Notification read update failed',error);vesselNotice('Не удалось отметить уведомления прочитанными.','error');return;}",
    'const updatedIds=new Set((updated||[]).map(row=>row.id));',
    'notifications=notifications.map(item=>updatedIds.has(item.id)&&!item.read_at?{...item,read_at:readAt}:item);',
]

NOTIFICATION_REALTIME_READ_MARKERS = [
    "event:'UPDATE',schema:'public',table:'notifications',filter:`user_id=eq.${user.id}`",
    'notifications=notifications.map(item=>item.id===row.id?{...item,...row}:item);',
]

ALL_MARKERS = [*NOTIFICATION_MARKERS, *NOTIFICATION_READ_MARKERS, *NOTIFICATION_REALTIME_READ_MARKERS]

if all(marker in text for marker in ALL_MARKERS):
    print('Notification session, Realtime, and read-state hardening already applied; nothing to change')
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


# The original session/Realtime migration may already be present while later
# lifecycle patches have changed the surrounding source. In that state, do not
# re-run anchor-based replacements: their exact old/new blocks are intentionally
# no longer guaranteed to remain contiguous.
base_hardening_applied = all(marker in text for marker in NOTIFICATION_MARKERS)

if base_hardening_applied:
    print('Notification session and Realtime hardening already applied')
else:
    replace_once(
        """let dmMessages = [];
let notifications = [];
let serverMembers = [];
""",
        """let dmMessages = [];
let notifications = [];
let notificationsSyncRevision = 0;
let serverMembers = [];
""",
        'notification revision state',
    )

    replace_once(
        """async function syncNotifications(user) {
  if (!supabase || !user?.id || window.__vesselNotificationsLoaded) return;
  const {data}=await supabase.from('notifications').select('id,type,title,body,data,read_at,created_at').eq('user_id',user.id).order('created_at',{ascending:false}).limit(30);
  notifications=data||[]; window.__vesselNotificationsLoaded=true;
  if (document.querySelector('#app')) render();
}
""",
        """async function syncNotifications(user) {
  if (!supabase || !user?.id || window.__vesselNotificationsLoaded) return;
  const revision=++notificationsSyncRevision;
  const {data,error}=await supabase.from('notifications').select('id,type,title,body,data,read_at,created_at').eq('user_id',user.id).order('created_at',{ascending:false}).limit(30);
  if(savedUser?.id!==user.id||revision!==notificationsSyncRevision)return;
  if(error){console.warn('Notification sync failed',error);vesselNotice('Не удалось загрузить уведомления.','error');return;}
  notifications=data||[]; window.__vesselNotificationsLoaded=true;
  if (document.querySelector('#app')) render();
}
""",
        'notification fetch session/revision guard',
    )

    replace_once(
        """  window.__vesselDmThreadsLoaded=false;
  window.__vesselDmLoaded=false;
  window.__vesselMembersServerId=null;
""",
        """  window.__vesselDmThreadsLoaded=false;
  window.__vesselDmLoaded=false;
  window.__vesselNotificationsLoaded=false;
  notificationsSyncRevision++;
  window.__vesselMembersServerId=null;
""",
        'notification reset lifecycle',
    )

    replace_once(
        """    supabase.channel(`vessel-notifications-${user.id}`).on('postgres_changes',{event:'INSERT',schema:'public',table:'notifications',filter:`user_id=eq.${user.id}`},payload=>{notifications=[payload.new,...notifications];render();}).subscribe()
""",
        """    supabase.channel(`vessel-notifications-${user.id}`).on('postgres_changes',{event:'INSERT',schema:'public',table:'notifications',filter:`user_id=eq.${user.id}`},payload=>{
      const row=payload.new;
      notificationsSyncRevision++;
      window.__vesselNotificationsLoaded=true;
      notifications=[row,...notifications.filter(item=>item.id!==row.id)];
      render();
    }).subscribe()
""",
        'notification realtime revision guard',
    )

replace_once(
    """  document.querySelector('#notifications').addEventListener('click', async () => {
    vesselListDialog('Уведомления',notifications.map(item=>({title:item.title||'Vessel',body:item.body||'',meta:item.created_at?new Date(item.created_at).toLocaleString('ru-RU'):''})), 'Уведомлений пока нет');
    const unread=notifications.filter(item=>!item.read_at);
    if(unread.length&&supabase&&user.id){
      await supabase.from('notifications').update({read_at:new Date().toISOString()}).eq('user_id',user.id).is('read_at',null);
      notifications=notifications.map(item=>({...item,read_at:item.read_at||new Date().toISOString()}));
      render();
    }
  });
""",
    """  document.querySelector('#notifications').addEventListener('click', async () => {
    vesselListDialog('Уведомления',notifications.map(item=>({title:item.title||'Vessel',body:item.body||'',meta:item.created_at?new Date(item.created_at).toLocaleString('ru-RU'):''})), 'Уведомлений пока нет');
    const sessionUserId=user.id;
    const unreadIds=notifications.filter(item=>!item.read_at).map(item=>item.id).filter(Boolean);
    if(unreadIds.length&&supabase&&sessionUserId){
      const readAt=new Date().toISOString();
      const {data:updated,error}=await supabase.from('notifications').update({read_at:readAt}).eq('user_id',sessionUserId).in('id',unreadIds).is('read_at',null).select('id');
      if(savedUser?.id!==sessionUserId)return;
      if(error){console.warn('Notification read update failed',error);vesselNotice('Не удалось отметить уведомления прочитанными.','error');return;}
      const updatedIds=new Set((updated||[]).map(row=>row.id));
      notifications=notifications.map(item=>updatedIds.has(item.id)&&!item.read_at?{...item,read_at:readAt}:item);
      render();
    }
  });
""",
    'notification read snapshot/session guard',
)

replace_once(
    """    supabase.channel(`vessel-notifications-${user.id}`).on('postgres_changes',{event:'INSERT',schema:'public',table:'notifications',filter:`user_id=eq.${user.id}`},payload=>{
      const row=payload.new;
      notificationsSyncRevision++;
      window.__vesselNotificationsLoaded=true;
      notifications=[row,...notifications.filter(item=>item.id!==row.id)];
      render();
    }).subscribe()
""",
    """    supabase.channel(`vessel-notifications-${user.id}`)
      .on('postgres_changes',{event:'INSERT',schema:'public',table:'notifications',filter:`user_id=eq.${user.id}`},payload=>{
        const row=payload.new;
        notificationsSyncRevision++;
        window.__vesselNotificationsLoaded=true;
        notifications=[row,...notifications.filter(item=>item.id!==row.id)];
        render();
      })
      .on('postgres_changes',{event:'UPDATE',schema:'public',table:'notifications',filter:`user_id=eq.${user.id}`},payload=>{
        const row=payload.new;
        if(!row?.id)return;
        notificationsSyncRevision++;
        window.__vesselNotificationsLoaded=true;
        notifications=notifications.map(item=>item.id===row.id?{...item,...row}:item);
        render();
      })
      .subscribe()
""",
    'notification realtime read-state sync',
)

for marker in ALL_MARKERS:
    if marker not in text:
        raise SystemExit(f'missing notification hardening marker: {marker}')

if changed:
    path.write_text(text, encoding='utf-8')
    print('Applied notification session, Realtime, and read-state hardening')
else:
    print('Notification session, Realtime, and read-state hardening already applied; nothing to change')
