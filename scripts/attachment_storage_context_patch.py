from pathlib import Path

path = Path('src/main.js')
text = path.read_text(encoding='utf-8')
changed = False

required = [
    'async function uploadVesselFile(file, user, context)',
    "const attachmentContext=targetDmId?`dm/${targetDmId}`:`channel/${targetChannelId}`;",
    'uploadVesselFile(file,user,attachmentContext)',
]
if all(marker in text for marker in required):
    print('Attachment storage context hardening already applied; nothing to change')
    raise SystemExit(0)

old_function = """async function uploadVesselFile(file, user) {
  if (!supabase || !user?.id) { vesselNotice('Для загрузки файлов нужен настоящий аккаунт.','error'); return null; }
  if(file.size>25*1024*1024){vesselNotice('Максимальный размер файла — 25 МБ.','error');return null;}
  let context=null;
  if(activeDmId)context=`dm/${activeDmId}`;
  else if(activeChannelId&&activeChannelKind==='text')context=`channel/${activeChannelId}`;
  if(!context){vesselNotice('Открой личный чат или текстовый канал перед загрузкой файла.','error');return null;}
  const safeName=file.name.replace(/[^a-zA-Z0-9._-]/g,'_')||'file';
  const objectPath=`${user.id}/${context}/${crypto.randomUUID()}-${safeName}`;
  const {error}=await supabase.storage.from('vessel-files').upload(objectPath,file,{contentType:file.type||'application/octet-stream',upsert:false});
  if(error){vesselNotice(`Файл не загрузился: ${error.message}`,'error');return null;}
  return {name:file.name,path:objectPath,type:file.type||'application/octet-stream',size:file.size};
}"""

new_function = """async function uploadVesselFile(file, user, context) {
  if (!supabase || !user?.id) { vesselNotice('Для загрузки файлов нужен настоящий аккаунт.','error'); return null; }
  if(file.size>25*1024*1024){vesselNotice('Максимальный размер файла — 25 МБ.','error');return null;}
  const storageContext=String(context||'');
  if(!/^(dm|channel)\/[^/]+$/.test(storageContext)){vesselNotice('Контекст загрузки файла устарел. Выбери чат или канал ещё раз.','error');return null;}
  const safeName=file.name.replace(/[^a-zA-Z0-9._-]/g,'_')||'file';
  const objectPath=`${user.id}/${storageContext}/${crypto.randomUUID()}-${safeName}`;
  const {error}=await supabase.storage.from('vessel-files').upload(objectPath,file,{contentType:file.type||'application/octet-stream',upsert:false});
  if(error){vesselNotice(`Файл не загрузился: ${error.message}`,'error');return null;}
  return {name:file.name,path:objectPath,type:file.type||'application/octet-stream',size:file.size};
}"""

if old_function in text:
    text = text.replace(old_function, new_function, 1)
    changed = True
elif new_function not in text:
    raise SystemExit('uploadVesselFile anchor not found')

old_call = """      const attachment=await uploadVesselFile(file,user); if(!attachment)return;"""
new_call = """      const attachmentContext=targetDmId?`dm/${targetDmId}`:`channel/${targetChannelId}`;
      const attachment=await uploadVesselFile(file,user,attachmentContext); if(!attachment)return;"""

if old_call in text:
    text = text.replace(old_call, new_call, 1)
    changed = True
elif new_call not in text:
    raise SystemExit('attachment upload call anchor not found')

for marker in required:
    if marker not in text:
        raise SystemExit(f'missing attachment storage context marker: {marker}')

if changed:
    path.write_text(text, encoding='utf-8')
    print('Applied attachment storage context hardening')
else:
    print('Attachment storage context hardening already applied; nothing to change')
