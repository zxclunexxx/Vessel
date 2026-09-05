from pathlib import Path
import re
p=Path("src/main.js")
s=p.read_text(encoding="utf-8")
def sub(pattern,repl,label):
    global s
    ns,n=re.subn(pattern,repl,s,count=1,flags=re.S)
    if n!=1: raise SystemExit(f"{label}: {n}")
    s=ns
s=s.replace("const savedChannelMap = JSON.parse(localStorage.getItem('vesselChannelMap') || '{}');","const savedChannelMap = {};",1)
sub(r"async function syncSupabaseMessages\(\) \{.*?\n\}","""async function syncSupabaseMessages() {
  if (!supabase || !activeChannelId || activeChannelKind !== 'text') return;
  await loadChannelMessages(activeChannelId);
}""","messages")
sub(r"async function syncSupabaseChannels\(server\) \{.*?\n\}","""async function syncSupabaseChannels(server) {
  if (!supabase || !server?.dbId || server.__channelsLoaded) return;
  const {data,error}=await supabase.from('channels').select('id,name,kind,position').eq('server_id',server.dbId).order('position');
  if(error){console.warn('Channels failed',error);dbChannels=[];return;}
  dbChannels=data||[];
  server.__channelsLoaded=true;
  if(server.id!==servers[activeServerIndex]?.id)return;
  const selected=dbChannels.find(c=>c.id===activeChannelId)||dbChannels.find(c=>c.kind==='text')||dbChannels[0]||null;
  activeChannelId=selected?.id||null;activeChannelName=selected?.name||'';activeChannelKind=selected?.kind||'text';
  currentDm=null;activeDmId=null;messages=[];render();
  if(selected?.kind==='text')await loadChannelMessages(selected.id);
}""","channels")
sub(r"function serverChannels\(\) \{.*?\n\}\n\nfunction saveChannelMap\(\) \{.*?\n\}","""function serverChannels() {
  return dbChannels;
}
function saveChannelMap() {}""","cache")
s=s.replace("connectSupabaseRealtime(user); ensureCallInbox(user).catch(()=>{}); syncSupabaseMessages(); syncSupabaseServers(user); syncSupabaseChannels(servers[activeServerIndex]);","connectSupabaseRealtime(user); ensureCallInbox(user).catch(()=>{}); syncSupabaseServers(user); syncSupabaseChannels(servers[activeServerIndex]);",1)
sub(r"  const addChannel = async kind => \{.*?\n  \};","""  const addChannel = async kind => {
    const name=prompt(kind==='voice'?'Название голосовой комнаты:':'Название нового канала:');
    if(!name?.trim())return;
    const server=servers[activeServerIndex];
    if(!supabase||!user.id||!server?.dbId){alert('Сначала выбери настоящий сервер.');return;}
    const {data,error}=await supabase.from('channels').insert({server_id:server.dbId,name:name.trim(),kind,position:dbChannels.length}).select('id,name,kind,position').single();
    if(error){alert('Не удалось создать канал: '+error.message);return;}
    dbChannels=[...dbChannels,data];activeChannelId=data.id;activeChannelName=data.name;activeChannelKind=data.kind;
    currentDm=null;activeDmId=null;messages=[];render();
  };""","add channel")
p.write_text(s,encoding="utf-8")
print("runtime v3 patch applied")
