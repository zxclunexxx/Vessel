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

# Later lifecycle patches may insert their own revision counters between these lines.
# Once all observable notification hardening markers exist, treat the migration as
# complete instead of requiring the original contiguous reset anchor forever.
if all(marker in text for marker in NOTIFICATION_MARKERS):
    print('Notification session and Realtime race hardening already applied; nothing to change')
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

for marker in NOTIFICATION_MARKERS:
    if marker not in text:
        raise SystemExit(f'missing notification hardening marker: {marker}')

if changed:
    path.write_text(text, encoding='utf-8')
    print('Applied notification session and Realtime race hardening')
else:
    print('Notification session and Realtime race hardening already applied; nothing to change')
