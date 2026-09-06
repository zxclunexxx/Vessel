from pathlib import Path

main = Path('src/main.js').read_text(encoding='utf-8')

handler_start = main.find("document.querySelector('#notifications').addEventListener('click', async () => {")
if handler_start < 0:
    raise SystemExit('Notification click handler is missing')
handler = main[handler_start:handler_start + 2600]

banned = [
    ".update({read_at:new Date().toISOString()}).eq('user_id',user.id).is('read_at',null)",
    "notifications=notifications.map(item=>({...item,read_at:item.read_at||new Date().toISOString()}));",
]
for marker in banned:
    if marker in handler:
        raise SystemExit(f'Unsafe notification read behavior is still present: {marker}')

required = [
    'const sessionUserId=user.id;',
    'const unreadIds=notifications.filter(item=>!item.read_at).map(item=>item.id).filter(Boolean);',
    'const readAt=new Date().toISOString();',
    ".eq('user_id',sessionUserId).in('id',unreadIds).is('read_at',null).select('id')",
    'if(savedUser?.id!==sessionUserId)return;',
    "if(error){console.warn('Notification read update failed',error);vesselNotice('Не удалось отметить уведомления прочитанными.','error');return;}",
    'const updatedIds=new Set((updated||[]).map(row=>row.id));',
    'notifications=notifications.map(item=>updatedIds.has(item.id)&&!item.read_at?{...item,read_at:readAt}:item);',
]
for marker in required:
    if marker not in handler:
        raise SystemExit(f'Notification read guard missing: {marker}')

print('Vessel notification read smoke check passed')
