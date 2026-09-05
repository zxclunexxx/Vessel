from pathlib import Path
import re

main_path=Path('src/main.js')
css_path=Path('src/style.css')
text=main_path.read_text(encoding='utf-8')
css=css_path.read_text(encoding='utf-8')

# Track outgoing pending requests separately so users can see that a request was actually sent.
anchor="let friendRequests = [];"
if anchor not in text: raise SystemExit('friendRequests anchor not found')
text=text.replace(anchor,anchor+"\nlet outgoingFriendRequests = [];",1)

# Refresh the social state immediately after sending a request.
old="""  if(sendError){vesselNotice('Не удалось отправить заявку.','error');return;}
  vesselNotice(`Заявка пользователю ${target.username} отправлена.`,'success');
}"""
new="""  if(sendError){vesselNotice('Не удалось отправить заявку.','error');return;}
  window.__vesselSocialLoaded=false;
  await syncSocial(user);
  vesselNotice(`Заявка пользователю ${target.username} отправлена.`,'success');
}"""
if old not in text: raise SystemExit('send friend request tail not found')
text=text.replace(old,new,1)

# Load incoming + outgoing pending requests with their profile names.
pattern=re.compile(r"async function syncSocial\(user\) \{.*?\n\}",re.S)
match=pattern.search(text)
if not match: raise SystemExit('syncSocial not found')
replacement="""async function syncSocial(user) {
  if (!supabase || !user?.id || window.__vesselSocialLoaded) return;
  const {data: links, error: linksError} = await supabase.from('friendships').select('friend_id').eq('user_id', user.id);
  if(linksError){vesselNotice('Не удалось загрузить список друзей.','error');return;}
  const ids = (links || []).map(row => row.friend_id).filter(Boolean);
  friends = [];
  if (ids.length) {
    const {data: profiles, error: profilesError} = await supabase.from('profiles').select('id,username,avatar_color,status').in('id', ids);
    if(profilesError){vesselNotice('Не удалось загрузить профили друзей.','error');return;}
    friends = profiles || [];
  }
  const [incomingResult,outgoingResult]=await Promise.all([
    supabase.from('friend_requests').select('id,sender_id,status,created_at,profiles!friend_requests_sender_id_fkey(username,avatar_color)').eq('receiver_id', user.id).eq('status','pending').order('created_at',{ascending:false}),
    supabase.from('friend_requests').select('id,receiver_id,status,created_at,profiles!friend_requests_receiver_id_fkey(username,avatar_color)').eq('sender_id', user.id).eq('status','pending').order('created_at',{ascending:false})
  ]);
  if(incomingResult.error||outgoingResult.error){vesselNotice('Не удалось загрузить заявки в друзья.','error');return;}
  friendRequests = incomingResult.data || [];
  outgoingFriendRequests = outgoingResult.data || [];
  window.__vesselSocialLoaded = true;
  if (document.querySelector('#app')) render();
}"""
text=text[:match.start()]+replacement+text[match.end():]

# Insert outgoing request rows in the friends screen.
needle="${friendRequests.map(request=>`<div class=\"friend-row request-row\""
idx=text.find(needle)
if idx<0: raise SystemExit('friends request render anchor not found')
# Find the end of incoming-request map expression and append outgoing rows.
end_marker=".join('')}${friends.length ?"
end_idx=text.find(end_marker,idx)
if end_idx<0: raise SystemExit('friend requests render end not found')
outgoing=""".join('')}${outgoingFriendRequests.map(request=>`<div class=\"friend-row outgoing-request-row\"><div class=\"avatar\" style=\"background:#5a6380\">${escapeHtml((request.profiles?.username||'?')[0].toUpperCase())}</div><b>${escapeHtml(request.profiles?.username||'Пользователь')}</b><span class=\"pending-label\">Ожидает подтверждения</span><button class=\"danger compact\" data-cancel-request=\"${request.id}\" title=\"Отменить заявку\">×</button></div>`).join('')}${friends.length ?"""
text=text[:end_idx]+outgoing+text[end_idx+len(end_marker):]

# Add cancellation handler before incoming acceptance handlers.
anchor="  document.querySelectorAll('[data-accept-request]').forEach"
if anchor not in text: raise SystemExit('accept request listener anchor not found')
handler="""  document.querySelectorAll('[data-cancel-request]').forEach(button=>button.addEventListener('click',async()=>{
    if(!supabase||!user.id)return;
    const requestId=button.dataset.cancelRequest;
    const {error}=await supabase.from('friend_requests').delete().eq('id',requestId).eq('sender_id',user.id).eq('status','pending');
    if(error){vesselNotice('Не удалось отменить заявку.','error');return;}
    window.__vesselSocialLoaded=false;
    await syncSocial(user);
    vesselNotice('Заявка отменена.','success');
  }));
"""+anchor
text=text.replace(anchor,handler,1)

# Make the friends list layouts robust with 4/5/6 controls instead of one rigid grid.
css += """
.outgoing-request-row{grid-template-columns:44px minmax(120px,1fr) auto 42px}.outgoing-request-row .pending-label{color:#aab1c5}.request-row{grid-template-columns:44px minmax(120px,1fr) auto 76px 76px}.request-row button{width:auto;padding:0 12px}.friends-view .empty-state{color:#858ca0;line-height:1.55}@media(max-width:600px){.outgoing-request-row{grid-template-columns:40px minmax(0,1fr) 36px}.outgoing-request-row .pending-label{grid-column:2}.request-row{grid-template-columns:40px minmax(0,1fr) 72px 72px}.request-row>span{grid-column:2}.request-row button{width:auto}}
"""

main_path.write_text(text,encoding='utf-8')
css_path.write_text(css,encoding='utf-8')
print('Applied friend request visibility and cancellation patch')
