from pathlib import Path
import re

path=Path('src/main.js')
text=path.read_text(encoding='utf-8')

def replace_once(old,new,label):
    global text
    if old not in text:
        raise SystemExit(f'{label} anchor not found')
    text=text.replace(old,new,1)

# Persist the active server by stable database id, never by array index.
replace_once(
"let activeServerIndex = Number(localStorage.getItem('vesselActiveServer') || 0);",
"let activeServerIndex = 0;\nlet activeServerId = localStorage.getItem('vesselActiveServerId') || null;",
'active server state')

# Authenticated channel state must come from Supabase, not a localStorage channel cache.
replace_once("const savedChannelMap = JSON.parse(localStorage.getItem('vesselChannelMap') || '{}');\n",'', 'legacy channel cache state')

old="""let servers = [{ id: 'add-server', icon: '+', name: 'Добавить сервер', add: true }];
if (activeServerIndex < 0) activeServerIndex = 0;

function serverChannels() {
  const server = servers[activeServerIndex];
  return savedChannelMap[server?.id] || [];
}

function saveChannelMap() {
  localStorage.setItem('vesselChannelMap', JSON.stringify(savedChannelMap));
}
"""
new="""let servers = [{ id: 'add-server', icon: '+', name: 'Добавить сервер', add: true }];

function getActiveServer() {
  const selected=activeServerId ? servers.find(item=>!item.add&&item.id===activeServerId) : null;
  const fallback=selected || servers.find(item=>!item.add) || null;
  activeServerIndex=fallback ? servers.indexOf(fallback) : 0;
  if(fallback?.id!==activeServerId){
    activeServerId=fallback?.id||null;
    if(activeServerId)localStorage.setItem('vesselActiveServerId',activeServerId);else localStorage.removeItem('vesselActiveServerId');
  }
  return fallback;
}
function setActiveServer(serverOrId) {
  const id=typeof serverOrId==='string' ? serverOrId : serverOrId?.id;
  const target=id ? servers.find(item=>!item.add&&item.id===id) : null;
  activeServerId=target?.id||null;
  activeServerIndex=target ? servers.indexOf(target) : 0;
  if(activeServerId)localStorage.setItem('vesselActiveServerId',activeServerId);else localStorage.removeItem('vesselActiveServerId');
  localStorage.removeItem('vesselActiveServer');
  return target;
}
function serverChannels() {
  return getActiveServer()?.channels || [];
}
"""
replace_once(old,new,'server helper block')

# Do not touch a removed local channel cache during legacy cleanup.
text=text.replace("    Object.keys(savedChannelMap).forEach(key => delete savedChannelMap[key]);\n",'')

# Replace server sync with error-aware, id-stable state restoration.
pattern=re.compile(r"async function syncSupabaseServers\(user\) \{.*?\n\}",re.S)
match=pattern.search(text)
if not match: raise SystemExit('syncSupabaseServers not found')
replacement="""async function syncSupabaseServers(user) {
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
}"""
text=text[:match.start()]+replacement+text[match.end():]

# Channel sync preserves the selected channel when it still exists and never reads/writes a local cache.
pattern=re.compile(r"async function syncSupabaseChannels\(server\) \{.*?\n\}",re.S)
match=pattern.search(text)
if not match: raise SystemExit('syncSupabaseChannels not found')
replacement="""async function syncSupabaseChannels(server) {
  if (!supabase || !server?.dbId || server.__channelsLoaded) return;
  const {data,error}=await supabase.from('channels').select('id,name,kind,position').eq('server_id',server.dbId).order('position');
  if(error){console.warn('Channel sync failed',error);vesselNotice('Не удалось загрузить каналы сервера.','error');return;}
  const rows=data||[];
  server.channels=rows;
  server.__channelsLoaded=true;
  if(server.id===getActiveServer()?.id){
    dbChannels=rows;
    let selected=rows.find(channel=>channel.id===activeChannelId)||null;
    if(!selected)selected=rows.find(channel=>channel.kind==='text')||rows[0]||null;
    activeChannelId=selected?.id||null;
    activeChannelName=selected?.name||'нет каналов';
    activeChannelKind=selected?.kind||'text';
    currentDm=null;
    activeDmId=null;
    messages=[];
    if(activeChannelId&&activeChannelKind==='text')await loadChannelMessages(activeChannelId);else render();
  }
}"""
text=text[:match.start()]+replacement+text[match.end():]

# Surface profile lookup failures in member roster instead of silently showing fake-looking placeholders.
old="""  if(ids.length){
    const result=await supabase.from('profiles').select('id,username,avatar_color,status').in('id',ids);
    profiles=result.data||[];
  }"""
new="""  if(ids.length){
    const result=await supabase.from('profiles').select('id,username,avatar_color,status').in('id',ids);
    if(result.error){console.warn('Member profiles failed',result.error);vesselNotice('Не удалось загрузить профили участников.','error');return;}
    profiles=result.data||[];
  }"""
replace_once(old,new,'member profiles error handling')

# Render uses the stable active server helper.
replace_once("  const activeServer=servers[activeServerIndex]?.add?null:servers[activeServerIndex];","  const activeServer=getActiveServer();",'render active server')
text=text.replace("escapeHtml(servers[activeServerIndex]?.name || 'Vessel')","escapeHtml(activeServer?.name || 'Vessel')")

# On app render, synchronize the stable active server rather than whatever currently occupies an array index.
replace_once(
"connectSupabaseRealtime(user); ensureCallInbox(user).catch(()=>{}); syncSupabaseMessages(); syncSupabaseServers(user); syncSupabaseChannels(servers[activeServerIndex]); syncServerMembers(user,servers[activeServerIndex]); syncSocial(user); syncNotifications(user);",
"connectSupabaseRealtime(user); ensureCallInbox(user).catch(()=>{}); syncSupabaseMessages(); syncSupabaseServers(user); const selectedServer=getActiveServer(); if(selectedServer){syncSupabaseChannels(selectedServer);syncServerMembers(user,selectedServer);} syncSocial(user); syncNotifications(user);",
'render sync line')

# Critical bug: switching from a DM to a server channel must clear activeDmId.
pattern=re.compile(r"  document\.querySelectorAll\('\.channel:not\(\.dm\)'\)\.forEach\(channel => channel\.addEventListener\('click', \(\) => \{.*?\n  \}\)\);",re.S)
match=pattern.search(text)
if not match: raise SystemExit('channel click handler not found')
replacement="""  document.querySelectorAll('.channel:not(.dm)').forEach(channel=>channel.addEventListener('click',async()=>{
    const channelId=channel.dataset.channelId||null;
    if(!channelId)return;
    const kind=channel.dataset.kind||'text';
    const name=channel.dataset.channelName||channel.textContent.replace('#','').replace('⌁','').trim();
    currentDm=null;
    activeDmId=null;
    friendsOpen=false;
    window.__vesselDmLoaded=false;
    activeChannelId=channelId;
    activeChannelName=name;
    activeChannelKind=kind;
    messages=[];
    document.querySelector('.channels')?.classList.remove('mobile-open');
    if(kind==='text')await loadChannelMessages(channelId);else render();
  }));"""
text=text[:match.start()]+replacement+text[match.end():]

# Prefer the stable active server in management actions.
text=text.replace("const server=servers[activeServerIndex];","const server=getActiveServer();")

# Join/create actions persist the selected server by id.
text=text.replace("  const index=servers.findIndex(item=>item.id===data.server_id);\n  if(index>=0)activeServerIndex=index;\n  localStorage.setItem('vesselActiveServer',activeServerIndex);","  setActiveServer(data.server_id);")
text=text.replace("        activeServerIndex=Math.max(0,servers.findIndex(item=>item.id===data.id));\n        localStorage.setItem('vesselActiveServer',activeServerIndex);","        setActiveServer(data.id);")

# Normal server selection persists by server id and clears stale channel/DM state before loading.
old="""    activeServerIndex=Number(server.dataset.serverIndex);localStorage.setItem('vesselActiveServer',activeServerIndex);activeChannelName='загрузка…';activeChannelKind='text';activeChannelId=null;currentDm=null;activeDmId=null;friendsOpen=false;serverMembers=[];window.__vesselMembersServerId=null;render();syncSupabaseChannels(servers[activeServerIndex]);syncServerMembers(user,servers[activeServerIndex]);"""
new="""    const selected=servers[Number(server.dataset.serverIndex)];
    if(!selected||selected.add)return;
    setActiveServer(selected);
    activeChannelName='загрузка…';activeChannelKind='text';activeChannelId=null;currentDm=null;activeDmId=null;friendsOpen=false;dbChannels=[];messages=[];serverMembers=[];window.__vesselMembersServerId=null;
    selected.__channelsLoaded=false;
    render();
    await syncSupabaseChannels(selected);
    await syncServerMembers(user,selected);"""
replace_once(old,new,'server click selection')

# Deleting/leaving should select the next real server instead of blindly trusting index zero.
text=text.replace("window.__vesselServersLoaded=false; activeServerIndex=0; activeChannelId=null; currentDm=null; activeDmId=null; messages=[]; serverMembers=[]; window.__vesselMembersServerId=null;","window.__vesselServersLoaded=false; activeServerId=null; localStorage.removeItem('vesselActiveServerId'); activeServerIndex=0; activeChannelId=null; currentDm=null; activeDmId=null; dbChannels=[]; messages=[]; serverMembers=[]; window.__vesselMembersServerId=null;")
text=text.replace("const next=servers[activeServerIndex];","const next=getActiveServer();")

# Membership realtime reload must also resolve by stable id.
text=text.replace("          if(activeServerIndex>=Math.max(servers.length-1,1))activeServerIndex=0;\n          const active=servers[activeServerIndex];","          const active=getActiveServer();")
text=text.replace("        const active=servers[activeServerIndex];","        const active=getActiveServer();")

# Remove the legacy active-server index key from cleanup/state writes.
text=text.replace("localStorage.setItem('vesselActiveServer',activeServerIndex);", "localStorage.setItem('vesselActiveServerId',getActiveServer()?.id||'');")

# Guardrails for the exact regressions this patch is meant to eliminate.
for forbidden in ["savedChannelMap", "activeDmId=isDm?null:activeDmId", "localStorage.getItem('vesselActiveServer')"]:
    if forbidden in text:
        raise SystemExit(f'legacy runtime state remains: {forbidden}')

path.write_text(text,encoding='utf-8')
print('Applied stable server/channel state and DM isolation patch')
