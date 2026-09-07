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

NOTIFICATION_REALTIME_READ_MARKERS = [
    "event:'UPDATE',schema:'public',table:'notifications',filter:`user_id=eq.${user.id}`",
    'notifications=notifications.map(item=>item.id===row.id?{...item,...row}:item);',
]

# Later UX patches intentionally changed which unread notifications are bulk-marked
# (DMs stay unread until their conversation is opened). Validate the security/session
# semantics instead of requiring the original exact unreadIds expression.
NOTIFICATION_READ_SEMANTIC_MARKERS = [
    'const sessionUserId=user.id;',
    'const unreadIds=notifications.filter(',
    'const readAt=new Date().toISOString();',
    ".eq('user_id',sessionUserId).in('id',unreadIds).is('read_at',null).select('id')",
    'if(savedUser?.id!==sessionUserId)return;',
    "if(error){console.warn('Notification read update failed',error);vesselNotice('Не удалось отметить уведомления прочитанными.','error');return;}",
    'const updatedIds=new Set((updated||[]).map(row=>row.id));',
    'notifications=notifications.map(item=>updatedIds.has(item.id)&&!item.read_at?{...item,read_at:readAt}:item);',
]


def has_notification_read_hardening():
    return all(marker in text for marker in NOTIFICATION_READ_SEMANTIC_MARKERS)


def has_notification_realtime_hardening():
    return all(marker in text for marker in NOTIFICATION_REALTIME_READ_MARKERS)


def replace_once(old, new, label, semantic_check=None):
    global text, changed
    if semantic_check and semantic_check():
        print(f'{label}: already applied in current notification UX')
        return
    if new in text:
        print(f'{label}: already applied')
        return
    if old not in text:
        raise SystemExit(f'{label}: expected source or compatible hardened form not found')
    text = text.replace(old, new, 1)
    changed = True
    print(f'{label}: applied')


if all(marker in text for marker in NOTIFICATION_MARKERS) and has_notification_read_hardening() and has_notification_realtime_hardening():
    print('Notification session, Realtime, and read-state hardening already applied; nothing to change')
    raise SystemExit(0)

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
    semantic_check=has_notification_read_hardening,
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
    semantic_check=has_notification_realtime_hardening,
)

for marker in NOTIFICATION_MARKERS:
    if marker not in text:
        raise SystemExit(f'missing notification hardening marker: {marker}')
if not has_notification_read_hardening():
    raise SystemExit('missing notification read snapshot/session semantics')
if not has_notification_realtime_hardening():
    raise SystemExit('missing notification Realtime read-state semantics')

if changed:
    path.write_text(text, encoding='utf-8')
    print('Applied notification session, Realtime, and read-state hardening')
else:
    print('Notification session, Realtime, and read-state hardening already applied; nothing to change')
