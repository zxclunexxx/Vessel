from pathlib import Path
import re

path = Path('src/main.js')
text = path.read_text(encoding='utf-8')

pattern = r"async function findAndRequestFriend\(user\) \{.*?\n\}"
replacement = """async function findAndRequestFriend(user) {
  const query=await vesselPrompt('Добавить друга','','Точное имя пользователя');
  if(!query?.trim()) return;
  if(!supabase||!user?.id){vesselNotice('Войди через настоящий аккаунт, чтобы добавлять друзей.','error');return;}
  const {data:searchResult,error:searchError}=await supabase.functions.invoke('search-user',{body:{username:query.trim()}});
  if(searchError){vesselNotice('Не удалось выполнить поиск пользователя.','error');return;}
  const target=searchResult?.user;
  if(!target){vesselNotice('Пользователь не найден.','error');return;}
  if(target.self||target.id===user.id){vesselNotice('Нельзя добавить самого себя.','error');return;}
  if(friends.some(friend=>friend.id===target.id)){vesselNotice(`${target.username} уже у тебя в друзьях.`);return;}
  const {data:existing,error:existingError}=await supabase.from('friend_requests').select('id,status,sender_id,receiver_id').or(`and(sender_id.eq.${user.id},receiver_id.eq.${target.id}),and(sender_id.eq.${target.id},receiver_id.eq.${user.id})`).limit(1);
  if(existingError){vesselNotice('Не удалось проверить заявки в друзья.','error');return;}
  const request=existing?.[0];
  if(request?.status==='pending'){
    vesselNotice(request.receiver_id===user.id ? `${target.username} уже отправил тебе заявку. Открой раздел «Друзья».` : 'Заявка уже отправлена.');
    return;
  }
  const {error:sendError}=await supabase.from('friend_requests').upsert({sender_id:user.id,receiver_id:target.id,status:'pending',updated_at:new Date().toISOString()},{onConflict:'sender_id,receiver_id'});
  if(sendError){vesselNotice('Не удалось отправить заявку.','error');return;}
  vesselNotice(`Заявка пользователю ${target.username} отправлена.`,'success');
}"""
text,count = re.subn(pattern,replacement,text,count=1,flags=re.S)
if count != 1:
    raise SystemExit(f'friend search replacement count={count}')

path.write_text(text,encoding='utf-8')
print('Applied private friend directory search patch')
