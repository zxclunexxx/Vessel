from pathlib import Path

path = Path('src/main.js')
text = path.read_text(encoding='utf-8')
changed = False

old = '''  const {data:existing,error:existingError}=await supabase.from('friend_requests').select('id,status,sender_id,receiver_id').or(`and(sender_id.eq.${user.id},receiver_id.eq.${target.id}),and(sender_id.eq.${target.id},receiver_id.eq.${user.id})`).limit(1);
  if(existingError){vesselNotice('Не удалось проверить заявки в друзья.','error');return;}
  const request=existing?.[0];
  if(request?.status==='pending'){
    vesselNotice(request.receiver_id===user.id ? `${target.username} уже отправил тебе заявку. Открой раздел «Друзья».` : 'Заявка уже отправлена.');
    return;
  }
  let sendError=null;
  if(request&&request.sender_id===user.id&&['declined','cancelled'].includes(request.status)){
    const result=await supabase.from('friend_requests').update({status:'pending',updated_at:new Date().toISOString()}).eq('id',request.id).eq('sender_id',user.id).in('status',['declined','cancelled']);
    sendError=result.error;
  }else{
    const result=await supabase.from('friend_requests').insert({sender_id:user.id,receiver_id:target.id,status:'pending'});
    sendError=result.error;
  }'''

new = '''  const {data:existing,error:existingError}=await supabase.from('friend_requests').select('id,status,sender_id,receiver_id').or(`and(sender_id.eq.${user.id},receiver_id.eq.${target.id}),and(sender_id.eq.${target.id},receiver_id.eq.${user.id})`);
  if(existingError){vesselNotice('Не удалось проверить заявки в друзья.','error');return;}
  const requests=existing||[];
  const pending=requests.find(request=>request.status==='pending');
  if(pending){
    vesselNotice(pending.receiver_id===user.id ? `${target.username} уже отправил тебе заявку. Открой раздел «Друзья».` : 'Заявка уже отправлена.');
    return;
  }
  const outgoing=requests.find(request=>request.sender_id===user.id&&request.receiver_id===target.id);
  let sendError=null;
  if(outgoing&&['accepted','declined','cancelled'].includes(outgoing.status)){
    const result=await supabase.from('friend_requests').update({status:'pending',updated_at:new Date().toISOString()}).eq('id',outgoing.id).eq('sender_id',user.id).in('status',['accepted','declined','cancelled']);
    sendError=result.error;
  }else{
    const result=await supabase.from('friend_requests').insert({sender_id:user.id,receiver_id:target.id,status:'pending'});
    sendError=result.error;
  }'''

if new in text:
    pass
elif old in text:
    text = text.replace(old, new, 1)
    changed = True
else:
    raise SystemExit('friend request retry client anchor not found')

for marker in [
    'const requests=existing||[];',
    "const pending=requests.find(request=>request.status==='pending');",
    'const outgoing=requests.find(request=>request.sender_id===user.id&&request.receiver_id===target.id);',
    "['accepted','declined','cancelled'].includes(outgoing.status)",
    ".in('status',['accepted','declined','cancelled'])",
]:
    if marker not in text:
        raise SystemExit(f'missing friend retry client marker: {marker}')
if ".limit(1);\n  if(existingError)" in text:
    raise SystemExit('legacy friend request arbitrary limit remains')

if changed:
    path.write_text(text, encoding='utf-8')
    print('Friend request retry client hardening applied')
else:
    print('Friend request retry client hardening already applied; nothing to change')
