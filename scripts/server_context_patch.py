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

for marker in [
    'const serverStillActive=server.id===getActiveServer()?.id;',
    'if(savedUser?.id!==user.id||server.dbId!==getActiveServer()?.dbId)return;',
]:
    if marker not in text:
        raise SystemExit(f'missing server context marker: {marker}')

if text.count('if(savedUser?.id!==user.id||server.dbId!==getActiveServer()?.dbId)return;') < 2:
    raise SystemExit('missing one of the server member async context guards')

if changed:
    path.write_text(text, encoding='utf-8')
    print('Applied server/channel async context hardening')
else:
    print('Server/channel async context hardening already applied; nothing to change')
