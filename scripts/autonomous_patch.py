from pathlib import Path
import re

path = Path('src/main.js')
text = path.read_text(encoding='utf-8')

pattern = r"async function joinByInvite\(code, user\) \{.*?\n\}"
replacement = """async function joinByInvite(code, user) {
  if (!supabase || !user?.id) { alert('Для вступления нужен настоящий аккаунт.'); return false; }
  const normalized=code?.trim().toUpperCase();
  if(!normalized)return false;
  const {data,error}=await supabase.functions.invoke('join-server',{body:{code:normalized}});
  if(error){
    let message='Не удалось вступить в сервер.';
    try{
      const payload=await error.context?.json?.();
      if(payload?.error)message=payload.error;
    }catch{}
    alert(message);
    return false;
  }
  if(!data?.ok){alert(data?.error||'Не удалось вступить в сервер.');return false;}
  window.__vesselServersLoaded=false;
  serverMembers=[];window.__vesselMembersServerId=null;
  await syncSupabaseServers(user);
  const index=servers.findIndex(item=>item.id===data.server_id);
  if(index>=0)activeServerIndex=index;
  localStorage.setItem('vesselActiveServer',activeServerIndex);
  const server=servers[activeServerIndex];
  if(server?.dbId){server.__channelsLoaded=false;await syncSupabaseChannels(server);await syncServerMembers(user,server);}
  alert(data.already_member?'Ты уже состоишь в этом сервере.':'Ты вступил в сервер.');
  return true;
}"""
text, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
if count != 1:
    raise SystemExit(f'joinByInvite replacement count={count}')

path.write_text(text, encoding='utf-8')
print('Applied secure server invite redemption patch')
