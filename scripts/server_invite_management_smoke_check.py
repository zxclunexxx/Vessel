from pathlib import Path

text = Path('src/main.js').read_text(encoding='utf-8')
required = [
    'async function manageServerInvites(user,server)',
    "server.role!=='owner'",
    ".from('server_invites').select('id,code,created_at,expires_at,max_uses,uses')",
    ".eq('server_id',serverId).eq('created_by',userId)",
    "label:'Управление приглашениями',value:'4'",
    "if(action==='4'){await manageServerInvites(user,server);return;}",
    "action!=='revoke'",
    ".delete().eq('id',invite.id).eq('server_id',serverId).eq('created_by',userId).select('id')",
]
missing = [marker for marker in required if marker not in text]
if missing:
    raise SystemExit('Missing server invite management markers: ' + ', '.join(missing))
print('Server invite management smoke check passed')
