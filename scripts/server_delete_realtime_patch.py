from pathlib import Path

path = Path('src/main.js')
text = path.read_text(encoding='utf-8')

markers = [
    "vessel-servers-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'servers'}",
    "if(payload.eventType==='DELETE')",
    'voiceStream&&voiceServerId===row.id',
    'window.__vesselServersLoaded=false;',
    'await syncSupabaseServers(user);',
]
if all(marker in text for marker in markers):
    print('Server delete realtime recovery already applied; nothing to change')
    raise SystemExit(0)

old = """    supabase.channel(`vessel-servers-${user.id}`).on('postgres_changes',{event:'UPDATE',schema:'public',table:'servers'},payload=>{
      const row=payload.new;
      const server=row?.id?servers.find(item=>item.id===row.id):null;
      if(!server)return;
      server.name=row.name||server.name;server.icon=row.icon||server.icon;render();
    }).subscribe(),"""

new = """    supabase.channel(`vessel-servers-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'servers'},async payload=>{
      const row=payload.new?.id?payload.new:payload.old;
      if(!row?.id)return;
      if(payload.eventType==='DELETE'){
        if(voiceStream&&voiceServerId===row.id)await leaveVoiceRoom();
        if(savedUser?.id!==user.id)return;
        window.__vesselServersLoaded=false;
        serversSyncRevision++;
        await syncSupabaseServers(user);
        return;
      }
      const server=servers.find(item=>item.id===row.id);
      if(!server)return;
      server.name=row.name||server.name;
      server.icon=row.icon||server.icon;
      render();
    }).subscribe(),"""

if old not in text:
    raise SystemExit('Server realtime update anchor not found and delete recovery markers are incomplete')

text = text.replace(old, new, 1)
for marker in markers:
    if marker not in text:
        raise SystemExit(f'missing server delete realtime marker after patch: {marker}')

path.write_text(text, encoding='utf-8')
print('Applied server delete realtime recovery')
