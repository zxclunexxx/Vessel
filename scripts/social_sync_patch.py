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


replace_once(
    """let friends = [];
let dmThreads = [];
let friendRequests = [];
""",
    """let friends = [];
let socialSyncRevision = 0;
let dmThreads = [];
let dmThreadsSyncRevision = 0;
let friendRequests = [];
""",
    'social sync revision state',
)

replace_once(
    """async function syncSocial(user) {
  if (!supabase || !user?.id || window.__vesselSocialLoaded) return;
  const {data: links, error: linksError} = await supabase.from('friendships').select('friend_id').eq('user_id', user.id);
  if(linksError){vesselNotice('Не удалось загрузить список друзей.','error');return;}
  const ids = (links || []).map(row => row.friend_id).filter(Boolean);
  friends = [];
  if (ids.length) {
    const {data: profiles, error: profilesError} = await supabase.from('profiles').select('id,username,avatar_color,status').in('id', ids);
    if(profilesError){vesselNotice('Не удалось загрузить профили друзей.','error');return;}
    friends = profiles || [];
  }
  const [incomingResult,outgoingResult]=await Promise.all([
    supabase.from('friend_requests').select('id,sender_id,status,created_at,profiles!friend_requests_sender_id_fkey(username,avatar_color)').eq('receiver_id', user.id).eq('status','pending').order('created_at',{ascending:false}),
    supabase.from('friend_requests').select('id,receiver_id,status,created_at,profiles!friend_requests_receiver_id_fkey(username,avatar_color)').eq('sender_id', user.id).eq('status','pending').order('created_at',{ascending:false})
  ]);
  if(incomingResult.error||outgoingResult.error){vesselNotice('Не удалось загрузить заявки в друзья.','error');return;}
  friendRequests = incomingResult.data || [];
  outgoingFriendRequests = outgoingResult.data || [];
  window.__vesselSocialLoaded = true;
  if (document.querySelector('#app')) render();
}
async function syncDmThreads(user) {
  if (!supabase || !user?.id || window.__vesselDmThreadsLoaded) return;
  const {data,error}=await supabase.rpc('vessel_dm_threads');
  if(error){console.warn('DM thread sync failed',error);vesselNotice('Не удалось загрузить список личных чатов.','error');return;}
  dmThreads=(data||[]).map(row=>({id:row.peer_id,username:row.username||'Пользователь',avatar_color:row.avatar_color||'#8b7cff',status:row.status||'online',last_message_at:row.last_message_at}));
  window.__vesselDmThreadsLoaded=true;
  if(document.querySelector('#app'))render();
}
""",
    """async function syncSocial(user) {
  if (!supabase || !user?.id || window.__vesselSocialLoaded) return;
  const revision=++socialSyncRevision;
  const {data: links, error: linksError} = await supabase.from('friendships').select('friend_id').eq('user_id', user.id);
  if(savedUser?.id!==user.id||revision!==socialSyncRevision)return;
  if(linksError){vesselNotice('Не удалось загрузить список друзей.','error');return;}
  const ids = (links || []).map(row => row.friend_id).filter(Boolean);
  let nextFriends = [];
  if (ids.length) {
    const {data: profiles, error: profilesError} = await supabase.from('profiles').select('id,username,avatar_color,status').in('id', ids);
    if(savedUser?.id!==user.id||revision!==socialSyncRevision)return;
    if(profilesError){vesselNotice('Не удалось загрузить профили друзей.','error');return;}
    nextFriends = profiles || [];
  }
  const [incomingResult,outgoingResult]=await Promise.all([
    supabase.from('friend_requests').select('id,sender_id,status,created_at,profiles!friend_requests_sender_id_fkey(username,avatar_color)').eq('receiver_id', user.id).eq('status','pending').order('created_at',{ascending:false}),
    supabase.from('friend_requests').select('id,receiver_id,status,created_at,profiles!friend_requests_receiver_id_fkey(username,avatar_color)').eq('sender_id', user.id).eq('status','pending').order('created_at',{ascending:false})
  ]);
  if(savedUser?.id!==user.id||revision!==socialSyncRevision)return;
  if(incomingResult.error||outgoingResult.error){vesselNotice('Не удалось загрузить заявки в друзья.','error');return;}
  friends = nextFriends;
  friendRequests = incomingResult.data || [];
  outgoingFriendRequests = outgoingResult.data || [];
  window.__vesselSocialLoaded = true;
  if (document.querySelector('#app')) render();
}
async function syncDmThreads(user) {
  if (!supabase || !user?.id || window.__vesselDmThreadsLoaded) return;
  const revision=++dmThreadsSyncRevision;
  const {data,error}=await supabase.rpc('vessel_dm_threads');
  if(savedUser?.id!==user.id||revision!==dmThreadsSyncRevision)return;
  if(error){console.warn('DM thread sync failed',error);vesselNotice('Не удалось загрузить список личных чатов.','error');return;}
  dmThreads=(data||[]).map(row=>({id:row.peer_id,username:row.username||'Пользователь',avatar_color:row.avatar_color||'#8b7cff',status:row.status||'online',last_message_at:row.last_message_at}));
  window.__vesselDmThreadsLoaded=true;
  if(document.querySelector('#app'))render();
}
""",
    'social and DM thread async revision guards',
)

replace_once(
    """  window.__vesselSocialLoaded=false;
  window.__vesselDmThreadsLoaded=false;
  window.__vesselDmLoaded=false;
""",
    """  window.__vesselSocialLoaded=false;
  socialSyncRevision++;
  window.__vesselDmThreadsLoaded=false;
  dmThreadsSyncRevision++;
  window.__vesselDmLoaded=false;
""",
    'social revision reset lifecycle',
)

for marker in [
    'let socialSyncRevision = 0;',
    'let dmThreadsSyncRevision = 0;',
    'const revision=++socialSyncRevision;',
    'revision!==socialSyncRevision',
    'let nextFriends = [];',
    'const revision=++dmThreadsSyncRevision;',
    'revision!==dmThreadsSyncRevision',
    'socialSyncRevision++;',
    'dmThreadsSyncRevision++;',
]:
    if marker not in text:
        raise SystemExit(f'missing social sync hardening marker: {marker}')

if changed:
    path.write_text(text, encoding='utf-8')
    print('Applied social and DM thread async race hardening')
else:
    print('Social and DM thread async race hardening already applied; nothing to change')
