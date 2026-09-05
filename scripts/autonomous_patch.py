from pathlib import Path

path=Path('src/main.js')
text=path.read_text(encoding='utf-8')

old="""async function uploadVesselFile(file, user) {
  if (!supabase || !user?.id) { vesselNotice('Для загрузки файлов нужен настоящий аккаунт.','error'); return null; }
  const safeName=file.name.replace(/[^a-zA-Z0-9._-]/g,'_');
  const path=`${user.id}/${crypto.randomUUID()}-${safeName}`;
  const {error}=await supabase.storage.from('vessel-files').upload(path,file,{contentType:file.type||'application/octet-stream',upsert:false});
  if(error){vesselNotice(`Файл не загрузился: ${error.message}`,'error');return null;}
  return {name:file.name,path,type:file.type||'application/octet-stream',size:file.size};
}"""
new="""async function uploadVesselFile(file, user) {
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
}
async function cleanupFailedAttachment(attachment){
  if(!supabase||!attachment?.path)return;
  try{await supabase.storage.from('vessel-files').remove([attachment.path]);}catch(error){console.warn('Attachment cleanup failed',error);}
}"""
if old not in text: raise SystemExit('upload function anchor not found')
text=text.replace(old,new,1)

text=text.replace("if(error){vesselNotice(`Не удалось отправить файл: ${error.message}`,'error');return;}\n        await loadDirectMessages(user,peerId);","if(error){await cleanupFailedAttachment(attachment);vesselNotice(`Не удалось отправить файл: ${error.message}`,'error');return;}\n        await loadDirectMessages(user,peerId);",1)
text=text.replace("if(error){vesselNotice(`Не удалось отправить файл: ${error.message}`,'error');return;}\n        messages.push({name:user.name,time:'только что',color:user.avatarColor||'#39d9a6',text:body,attachments:[attachment]});","if(error){await cleanupFailedAttachment(attachment);vesselNotice(`Не удалось отправить файл: ${error.message}`,'error');return;}\n        messages.push({name:user.name,time:'только что',color:user.avatarColor||'#39d9a6',text:body,attachments:[attachment]});",1)

if "`${user.id}/${crypto.randomUUID()}-${safeName}`" in text:
    raise SystemExit('legacy unscoped attachment path remains')
path.write_text(text,encoding='utf-8')
print('Applied context-scoped private attachment patch')
