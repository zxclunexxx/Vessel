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
    "  if(error){vesselNotice('Не удалось загрузить сообщения канала.','error');return;}\n  messages = (data||[]).reverse().map(m=>({name:m.profiles?.username||'Участник',time:new Date(m.created_at).toLocaleString('ru-RU'),color:m.profiles?.avatar_color||'#8b7cff',text:m.body,attachments:m.attachments||[]}));",
    "  if(activeDmId||activeChannelId!==channelId||activeChannelKind!=='text')return;\n  if(error){vesselNotice('Не удалось загрузить сообщения канала.','error');return;}\n  messages = (data||[]).reverse().map(m=>({name:m.profiles?.username||'Участник',time:new Date(m.created_at).toLocaleString('ru-RU'),color:m.profiles?.avatar_color||'#8b7cff',text:m.body,attachments:m.attachments||[]}));",
    'channel message context guard',
)

replace_once(
    "  if(error){vesselNotice('Не удалось загрузить личные сообщения.','error');return;}\n  dmMessages = (data || []).reverse().map(row => ({name:row.profiles?.username || 'Пользователь',time:new Date(row.created_at).toLocaleString('ru-RU'),color:row.profiles?.avatar_color || '#8b7cff',text:row.body,attachments:row.attachments||[]}));",
    "  if(activeDmId!==friendId)return;\n  if(error){vesselNotice('Не удалось загрузить личные сообщения.','error');return;}\n  dmMessages = (data || []).reverse().map(row => ({name:row.profiles?.username || 'Пользователь',time:new Date(row.created_at).toLocaleString('ru-RU'),color:row.profiles?.avatar_color || '#8b7cff',text:row.body,attachments:row.attachments||[]}));",
    'direct message context guard',
)

for marker in [
    "if(activeDmId||activeChannelId!==channelId||activeChannelKind!=='text')return;",
    'if(activeDmId!==friendId)return;',
]:
    if marker not in text:
        raise SystemExit(f'missing message context marker: {marker}')

if changed:
    path.write_text(text, encoding='utf-8')
    print('Applied async message context guards')
else:
    print('Async message context guards already applied; nothing to change')
