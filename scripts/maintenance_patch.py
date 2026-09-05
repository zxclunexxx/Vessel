from pathlib import Path
import re

path = Path('src/main.js')
text = path.read_text(encoding='utf-8')


def sub(pattern, replacement, *, count=1, flags=re.S, label='patch'):
    global text
    updated, n = re.subn(pattern, replacement, text, count=count, flags=flags)
    if n != count:
        raise SystemExit(f'{label}: expected {count} replacement(s), got {n}')
    text = updated

# Stop selecting an arbitrary channel from the entire database during bootstrap.
sub(
    r"async function syncSupabaseMessages\(\) \{.*?\n\}",
    "async function syncSupabaseMessages() {\n  window.__vesselDbLoaded = true;\n}",
    label='remove arbitrary global channel bootstrap',
)

# Server sync must clear stale state even when the account has no servers yet.
sub(
    r"const all=\[\.\.\.\(ownedResult\.data\|\|\[\]\),\.\.\.\(memberResult\.data\|\|\[\]\)\.filter\(s=>!\(ownedResult\.data\|\|\[\]\)\.some\(o=>o\.id===s\.id\)\)\];\n  window\.__vesselServersLoaded=true;\n  if \(all\.length\) \{ servers=\[\.\.\.all\.map\(s=>\(\{id:s\.id,dbId:s\.id,icon:s\.icon,name:s\.name,role:s\.owner_id===user\.id\?'owner':\(memberships\|\|\[\]\)\.find\(m=>m\.server_id===s\.id\)\?\.role\|\|'member'\}\)\),\{icon:'\+',name:'Добавить сервер',add:true\}\]; if\(activeServerIndex>=servers\.length-1\) activeServerIndex=0; render\(\); \}",
    "const all=[...(ownedResult.data||[]),...(memberResult.data||[]).filter(s=>!(ownedResult.data||[]).some(o=>o.id===s.id))];\n  window.__vesselServersLoaded=true;\n  servers=[...all.map(s=>({id:s.id,dbId:s.id,icon:s.icon,name:s.name,role:s.owner_id===user.id?'owner':(memberships||[]).find(m=>m.server_id===s.id)?.role||'member'})),{id:'add-server',icon:'+',name:'Добавить сервер',add:true}];\n  if(activeServerIndex>=Math.max(servers.length-1,1)) activeServerIndex=0;\n  render();",
    label='clear stale server state',
)

# Channels are database-backed only; empty results must clear stale channel/message state.
sub(
    r"async function syncSupabaseChannels\(server\) \{.*?\n\}",
    "async function syncSupabaseChannels(server) {\n  if (!supabase || !server?.dbId || server.__channelsLoaded) return;\n  const {data,error} = await supabase.from('channels').select('id,name,kind,position').eq('server_id',server.dbId).order('position');\n  if(error){console.warn('Channel sync failed',error);return;}\n  const rows=data||[];\n  dbChannels=rows;\n  savedChannelMap[server.id]=rows;\n  server.__channelsLoaded=true;\n  if(server.id===servers[activeServerIndex]?.id){\n    const firstText=rows.find(channel=>channel.kind==='text')||rows[0]||null;\n    activeChannelId=firstText?.id||null;\n    activeChannelName=firstText?.name||'нет каналов';\n    activeChannelKind=firstText?.kind||'text';\n    messages=[];\n    if(activeChannelId && activeChannelKind==='text') await loadChannelMessages(activeChannelId);\n    else render();\n  }\n}",
    label='database backed channels',
)

# Load attachment metadata in DMs as well.
text = text.replace(
    "select('id,sender_id,receiver_id,body,created_at,profiles!direct_messages_sender_id_fkey(username,avatar_color)')",
    "select('id,sender_id,receiver_id,body,attachments,created_at,profiles!direct_messages_sender_id_fkey(username,avatar_color)')",
)

# Add decline action to incoming friend requests.
text = text.replace(
    "<button data-accept-request=\"${request.id}\" data-sender=\"${request.sender_id}\">Принять</button>",
    "<button data-accept-request=\"${request.id}\" data-sender=\"${request.sender_id}\">Принять</button><button class=\"danger compact\" data-decline-request=\"${request.id}\">Отклонить</button>",
)

# Hide message composer in voice channels.
text = text.replace(
    "<form class=\"composer ${friendsOpen?'hidden':''}\">",
    "<form class=\"composer ${friendsOpen||(!currentDm&&activeChannelKind==='voice')?'hidden':''}\">",
)

# Send attachments to the currently open destination and stop persisting prototype messages locally.
sub(
    r"document\.querySelector\('\.attach'\)\.addEventListener\('click', \(\) => \{.*?\n  \}\);",
    "document.querySelector('.attach').addEventListener('click', () => {\n    const picker=document.createElement('input'); picker.type='file'; picker.accept='image/*,.pdf,.doc,.docx,.zip';\n    picker.onchange=async()=>{\n      const file=picker.files[0]; if(!file)return;\n      const attachment=await uploadVesselFile(file,user); if(!attachment)return;\n      const body=`📎 ${file.name}`;\n      if(activeDmId){\n        const {error}=await supabase.from('direct_messages').insert({sender_id:user.id,receiver_id:activeDmId,body,attachments:[attachment]});\n        if(error){alert(`Не удалось отправить файл: ${error.message}`);return;}\n        dmMessages.push({name:user.name,time:'только что',color:user.avatarColor||'#39d9a6',text:body});\n      } else {\n        if(!activeChannelId||activeChannelKind!=='text'){alert('Открой текстовый канал или личный чат.');return;}\n        const {error}=await supabase.from('messages').insert({channel_id:activeChannelId,author_id:user.id,body,attachments:[attachment]});\n        if(error){alert(`Не удалось отправить файл: ${error.message}`);return;}\n        messages.push({name:user.name,time:'только что',color:user.avatarColor||'#39d9a6',text:body});\n      }\n      render();\n    };\n    picker.click();\n  });",
    label='destination aware attachments',
)

# Channel creation: let the database be the source of truth and refresh from it.
sub(
    r"const addChannel = async kind => \{.*?\};\n  document\.querySelector\('#channel-add'\)",
    "const addChannel = async kind => {\n    const name=prompt(kind==='voice'?'Название голосовой комнаты:':'Название нового канала:');\n    if(!name?.trim())return;\n    const server=servers[activeServerIndex];\n    if(!supabase||!user.id||!server?.dbId){alert('Сначала выбери настоящий сервер.');return;}\n    if(server.role!=='owner'){alert('Создавать каналы может только владелец сервера.');return;}\n    const position=serverChannels().length;\n    const {data,error}=await supabase.from('channels').insert({server_id:server.dbId,name:name.trim(),kind,position}).select('id,name,kind,position').single();\n    if(error){alert(`Не удалось создать канал: ${error.message}`);return;}\n    server.__channelsLoaded=false;\n    await syncSupabaseChannels(server);\n    activeChannelId=data.id; activeChannelName=data.name; activeChannelKind=data.kind; currentDm=null; activeDmId=null;\n    if(kind==='text') await loadChannelMessages(data.id); else render();\n  };\n  document.querySelector('#channel-add')",
    label='database backed channel creation',
)

# Decline friend request cleanly.
needle = "document.querySelectorAll('[data-accept-request]').forEach(button=>button.addEventListener('click',async()=>{if(!supabase||!user.id)return;const {error}=await supabase.from('friend_requests').update({status:'accepted',updated_at:new Date().toISOString()}).eq('id',button.dataset.acceptRequest).eq('receiver_id',user.id);if(error){alert('Не удалось принять заявку.');return;}window.__vesselSocialLoaded=false;await syncSocial(user);render();}));"
if needle not in text:
    raise SystemExit('friend accept listener not found')
text = text.replace(needle, needle + "\n  document.querySelectorAll('[data-decline-request]').forEach(button=>button.addEventListener('click',async()=>{if(!supabase||!user.id)return;const {error}=await supabase.from('friend_requests').update({status:'declined',updated_at:new Date().toISOString()}).eq('id',button.dataset.declineRequest).eq('receiver_id',user.id);if(error){alert('Не удалось отклонить заявку.');return;}window.__vesselSocialLoaded=false;await syncSocial(user);render();}));")

# Creating a server should not inject a fake local channel; the DB trigger creates real defaults.
sub(
    r"const name = prompt\('Название нового сервера:'\);\n      if \(name && name\.trim\(\)\) \{.*?\n      return;",
    "const name=prompt('Название нового сервера:');\n      if(name&&name.trim()){\n        if(!supabase||!user.id){alert('Нужна активная сессия Vessel.');return;}\n        const icon=name.trim()[0].toUpperCase();\n        const {data,error}=await supabase.from('servers').insert({name:name.trim(),icon,owner_id:user.id}).select('id,name,icon').single();\n        if(error){alert(`Не удалось создать сервер: ${error.message}`);return;}\n        window.__vesselServersLoaded=false;\n        await syncSupabaseServers(user);\n        activeServerIndex=Math.max(0,servers.findIndex(item=>item.id===data.id));\n        localStorage.setItem('vesselActiveServer',activeServerIndex);\n        serverMembers=[]; window.__vesselMembersServerId=null;\n        const selected=servers[activeServerIndex];\n        selected.__channelsLoaded=false;\n        await syncSupabaseChannels(selected);\n        await syncServerMembers(user,selected);\n      }\n      return;",
    label='database backed server creation',
)

path.write_text(text, encoding='utf-8')
print('Vessel maintenance patch applied')
