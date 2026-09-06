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
    """let activeServerIndex = 0;
let activeServerId = localStorage.getItem('vesselActiveServerId') || null;
let activeChannelName = 'нет каналов';
""",
    """let activeServerIndex = 0;
let activeServerId = localStorage.getItem('vesselActiveServerId') || null;
let serversSyncRevision = 0;
let activeChannelName = 'нет каналов';
""",
    'server list revision state',
)

replace_once(
    """async function syncSupabaseServers(user) {
  if (!supabase || window.__vesselServersLoaded || !user?.id) return;
  const membershipsResult=await supabase.from('server_members').select('server_id,role').eq('user_id',user.id);
  if(membershipsResult.error){vesselNotice('Не удалось загрузить список серверов.','error');return;}
  const memberships=membershipsResult.data||[];
  const memberIds=memberships.map(row=>row.server_id).filter(Boolean);
  const [ownedResult,memberResult]=await Promise.all([
    supabase.from('servers').select('id,name,icon,owner_id').eq('owner_id',user.id).order('created_at'),
    memberIds.length ? supabase.from('servers').select('id,name,icon,owner_id').in('id',memberIds).order('created_at') : Promise.resolve({data:[],error:null})
  ]);
  if(ownedResult.error||memberResult.error){vesselNotice('Не удалось загрузить данные серверов.','error');return;}
  const owned=ownedResult.data||[];
  const all=[...owned,...(memberResult.data||[]).filter(server=>!owned.some(item=>item.id===server.id))];
  servers=[...all.map(server=>({id:server.id,dbId:server.id,icon:server.icon||server.name?.[0]?.toUpperCase()||'V',name:server.name,role:server.owner_id===user.id?'owner':memberships.find(member=>member.server_id===server.id)?.role||'member',channels:[]})),{id:'add-server',icon:'+',name:'Добавить сервер',add:true}];
  window.__vesselServersLoaded=true;
  const selected=setActiveServer(activeServerId && all.some(server=>server.id===activeServerId) ? activeServerId : all[0]?.id||null);
  if(!selected){activeChannelId=null;activeChannelName='нет каналов';activeChannelKind='text';dbChannels=[];messages=[];serverMembers=[];window.__vesselMembersServerId=null;}
  render();
}
""",
    """async function syncSupabaseServers(user) {
  if (!supabase || window.__vesselServersLoaded || !user?.id) return;
  const revision=++serversSyncRevision;
  const membershipsResult=await supabase.from('server_members').select('server_id,role').eq('user_id',user.id);
  if(savedUser?.id!==user.id||revision!==serversSyncRevision)return;
  if(membershipsResult.error){vesselNotice('Не удалось загрузить список серверов.','error');return;}
  const memberships=membershipsResult.data||[];
  const memberIds=memberships.map(row=>row.server_id).filter(Boolean);
  const [ownedResult,memberResult]=await Promise.all([
    supabase.from('servers').select('id,name,icon,owner_id').eq('owner_id',user.id).order('created_at'),
    memberIds.length ? supabase.from('servers').select('id,name,icon,owner_id').in('id',memberIds).order('created_at') : Promise.resolve({data:[],error:null})
  ]);
  if(savedUser?.id!==user.id||revision!==serversSyncRevision)return;
  if(ownedResult.error||memberResult.error){vesselNotice('Не удалось загрузить данные серверов.','error');return;}
  const owned=ownedResult.data||[];
  const all=[...owned,...(memberResult.data||[]).filter(server=>!owned.some(item=>item.id===server.id))];
  const nextServers=[...all.map(server=>({id:server.id,dbId:server.id,icon:server.icon||server.name?.[0]?.toUpperCase()||'V',name:server.name,role:server.owner_id===user.id?'owner':memberships.find(member=>member.server_id===server.id)?.role||'member',channels:[]})),{id:'add-server',icon:'+',name:'Добавить сервер',add:true}];
  servers=nextServers;
  window.__vesselServersLoaded=true;
  const selected=setActiveServer(activeServerId && all.some(server=>server.id===activeServerId) ? activeServerId : all[0]?.id||null);
  if(!selected){activeChannelId=null;activeChannelName='нет каналов';activeChannelKind='text';dbChannels=[];messages=[];serverMembers=[];window.__vesselMembersServerId=null;}
  render();
}
""",
    'server list async revision guards',
)

replace_once(
    """  window.__vesselDbLoaded=false;
  window.__vesselServersLoaded=false;
  window.__vesselSocialLoaded=false;
""",
    """  window.__vesselDbLoaded=false;
  window.__vesselServersLoaded=false;
  serversSyncRevision++;
  window.__vesselSocialLoaded=false;
""",
    'server list revision reset lifecycle',
)

for marker in [
    'let serversSyncRevision = 0;',
    'const revision=++serversSyncRevision;',
    'revision!==serversSyncRevision',
    'const nextServers=',
    'serversSyncRevision++;',
]:
    if marker not in text:
        raise SystemExit(f'missing server sync hardening marker: {marker}')

if text.count('revision!==serversSyncRevision') < 2:
    raise SystemExit('missing one of the server list async revision guards')

if changed:
    path.write_text(text, encoding='utf-8')
    print('Applied server list async race hardening')
else:
    print('Server list async race hardening already applied; nothing to change')
