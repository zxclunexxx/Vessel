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


# Ignore message query results that were started by a previous authenticated user.
replace_once(
    """async function loadChannelMessages(channelId) {
  if (!supabase || !channelId) return;
  const {data,error} = await supabase.from('messages').select('body,attachments,created_at,profiles(username,avatar_color)').eq('channel_id',channelId).order('created_at',{ascending:false}).limit(100);
  if(activeDmId||activeChannelId!==channelId||activeChannelKind!=='text')return;
""",
    """async function loadChannelMessages(channelId) {
  if (!supabase || !channelId) return;
  const sessionUserId=savedUser?.id||null;
  if(!sessionUserId)return;
  const {data,error} = await supabase.from('messages').select('body,attachments,created_at,profiles(username,avatar_color)').eq('channel_id',channelId).order('created_at',{ascending:false}).limit(100);
  if(savedUser?.id!==sessionUserId||activeDmId||activeChannelId!==channelId||activeChannelKind!=='text')return;
""",
    'channel message auth-session guard',
)

# Bind a channel-list query to both the authenticated user and the exact server object
# that launched it. This prevents a late response from a previous account/server from
# becoming the active channel list after logout, account switch, or membership loss.
replace_once(
    """async function syncSupabaseChannels(server) {
  if (!supabase || !server?.dbId || server.__channelsLoaded) return;
  const {data,error}=await supabase.from('channels').select('id,name,kind,position').eq('server_id',server.dbId).order('position');
  const serverStillActive=server.id===getActiveServer()?.id;
  if(error){console.warn('Channel sync failed',error);if(serverStillActive)vesselNotice('Не удалось загрузить каналы сервера.','error');return;}
  const rows=data||[];
  server.channels=rows;
  server.__channelsLoaded=true;
""",
    """async function syncSupabaseChannels(server) {
  if (!supabase || !server?.dbId || server.__channelsLoaded) return;
  const sessionUserId=savedUser?.id||null;
  const serverId=server.dbId;
  if(!sessionUserId)return;
  const {data,error}=await supabase.from('channels').select('id,name,kind,position').eq('server_id',serverId).order('position');
  const activeServer=getActiveServer();
  const serverStillActive=Boolean(savedUser?.id===sessionUserId&&server===activeServer&&serverId===activeServer?.dbId);
  if(savedUser?.id!==sessionUserId||!servers.includes(server))return;
  if(error){console.warn('Channel sync failed',error);if(serverStillActive)vesselNotice('Не удалось загрузить каналы сервера.','error');return;}
  const rows=data||[];
  server.channels=rows;
  server.__channelsLoaded=true;
""",
    'channel list auth/session object guard',
)

# Older server-context migration: suppress an error toast when the user already moved
# to another server. The newer auth/object guard above subsumes its active-server marker.
replace_once(
    """  const {data,error}=await supabase.from('channels').select('id,name,kind,position').eq('server_id',server.dbId).order('position');
  if(error){console.warn('Channel sync failed',error);vesselNotice('Не удалось загрузить каналы сервера.','error');return;}
""",
    """  const {data,error}=await supabase.from('channels').select('id,name,kind,position').eq('server_id',server.dbId).order('position');
  const serverStillActive=server.id===getActiveServer()?.id;
  if(error){console.warn('Channel sync failed',error);if(serverStillActive)vesselNotice('Не удалось загрузить каналы сервера.','error');return;}
""",
    'stale channel error suppression',
)

replace_once(
    """  const {data: memberships, error} = await supabase.from('server_members').select('user_id,role').eq('server_id',server.dbId);
  if (error) { console.warn('Server members failed', error); serverMembers=[]; return; }
""",
    """  const {data: memberships, error} = await supabase.from('server_members').select('user_id,role').eq('server_id',server.dbId);
  if(savedUser?.id!==user.id||server.dbId!==getActiveServer()?.dbId)return;
  if (error) { console.warn('Server members failed', error); serverMembers=[]; return; }
""",
    'server member list context guard',
)

replace_once(
    """    const result=await supabase.from('profiles').select('id,username,avatar_color,status').in('id',ids);
    if(result.error){console.warn('Member profiles failed',result.error);vesselNotice('Не удалось загрузить профили участников.','error');return;}
""",
    """    const result=await supabase.from('profiles').select('id,username,avatar_color,status').in('id',ids);
    if(savedUser?.id!==user.id||server.dbId!==getActiveServer()?.dbId)return;
    if(result.error){console.warn('Member profiles failed',result.error);vesselNotice('Не удалось загрузить профили участников.','error');return;}
""",
    'server member profile context guard',
)

required_markers = [
    'const sessionUserId=savedUser?.id||null;',
    "if(savedUser?.id!==sessionUserId||activeDmId||activeChannelId!==channelId||activeChannelKind!=='text')return;",
    'const serverId=server.dbId;',
    'const serverStillActive=Boolean(savedUser?.id===sessionUserId&&server===activeServer&&serverId===activeServer?.dbId);',
    'if(savedUser?.id!==sessionUserId||!servers.includes(server))return;',
    'if(savedUser?.id!==user.id||server.dbId!==getActiveServer()?.dbId)return;',
]
for marker in required_markers:
    if marker not in text:
        raise SystemExit(f'missing server/channel context marker: {marker}')

if text.count('if(savedUser?.id!==user.id||server.dbId!==getActiveServer()?.dbId)return;') < 2:
    raise SystemExit('missing one of the server member async context guards')

if changed:
    path.write_text(text, encoding='utf-8')
    print('Applied server/channel auth-session and async context hardening')
else:
    print('Server/channel auth-session and async context hardening already applied; nothing to change')
