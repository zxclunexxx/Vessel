from pathlib import Path

path = Path('src/main.js')
text = path.read_text(encoding='utf-8')
changed = False


def replace_once(old, new, label, markers=()):
    global text, changed
    for marker in markers:
        if marker in text:
            print(f'{label}: already applied in newer message model')
            return
    if new in text:
        print(f'{label}: already applied')
        return
    if old not in text:
        raise SystemExit(f'{label}: expected source or patched form not found')
    text = text.replace(old, new, 1)
    changed = True
    print(f'{label}: applied')


channel_marker = "if(activeDmId||activeChannelId!==channelId||activeChannelKind!=='text')return;"
dm_legacy_marker = 'if(activeDmId!==friendId)return;'
dm_revision_marker = 'if(savedUser?.id!==dmLoadUserId||revision!==dmMessagesSyncRevision||activeDmId!==friendId)return;'

replace_once(
    "  if(error){vesselNotice('Не удалось загрузить сообщения канала.','error');return;}\n  messages = (data||[]).reverse().map(m=>({name:m.profiles?.username||'Участник',time:new Date(m.created_at).toLocaleString('ru-RU'),color:m.profiles?.avatar_color||'#8b7cff',text:m.body,attachments:m.attachments||[]}));",
    "  if(activeDmId||activeChannelId!==channelId||activeChannelKind!=='text')return;\n  if(error){vesselNotice('Не удалось загрузить сообщения канала.','error');return;}\n  messages = (data||[]).reverse().map(m=>({name:m.profiles?.username||'Участник',time:new Date(m.created_at).toLocaleString('ru-RU'),color:m.profiles?.avatar_color||'#8b7cff',text:m.body,attachments:m.attachments||[]}));",
    'channel message context guard',
    markers=(channel_marker,),
)

replace_once(
    "  if(error){vesselNotice('Не удалось загрузить личные сообщения.','error');return;}\n  dmMessages = (data || []).reverse().map(row => ({name:row.profiles?.username || 'Пользователь',time:new Date(row.created_at).toLocaleString('ru-RU'),color:row.profiles?.avatar_color || '#8b7cff',text:row.body,attachments:row.attachments||[]}));",
    "  if(activeDmId!==friendId)return;\n  if(error){vesselNotice('Не удалось загрузить личные сообщения.','error');return;}\n  dmMessages = (data || []).reverse().map(row => ({name:row.profiles?.username || 'Пользователь',time:new Date(row.created_at).toLocaleString('ru-RU'),color:row.profiles?.avatar_color || '#8b7cff',text:row.body,attachments:row.attachments||[]}));",
    'direct message context guard',
    markers=(dm_revision_marker, dm_legacy_marker),
)

if channel_marker not in text:
    raise SystemExit(f'missing message context marker: {channel_marker}')
if dm_revision_marker not in text and dm_legacy_marker not in text:
    raise SystemExit('missing direct-message context guard')

if changed:
    path.write_text(text, encoding='utf-8')
    print('Applied async message context guards')
else:
    print('Async message context guards already applied; nothing to change')
