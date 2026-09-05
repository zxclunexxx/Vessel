from pathlib import Path

path = Path('src/main.js')
text = path.read_text(encoding='utf-8')

# Escape user-controlled content before inserting it into the large innerHTML template.
anchor = "const savedChannelMap = JSON.parse(localStorage.getItem('vesselChannelMap') || '{}');"
helper = """const savedChannelMap = JSON.parse(localStorage.getItem('vesselChannelMap') || '{}');
function escapeHtml(value='') {
  return String(value).replace(/[&<>\"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',\"'\":'&#39;'}[char]));
}
function attachmentMarkup(attachments=[]) {
  return (attachments||[]).map(file=>`<button class=\"attachment-link\" data-attachment-path=\"${escapeHtml(file.path||'')}\">📎 ${escapeHtml(file.name||'Файл')}</button>`).join('');
}
async function openAttachment(path) {
  if(!supabase||!path)return;
  const {data,error}=await supabase.storage.from('vessel-files').createSignedUrl(path,60);
  if(error||!data?.signedUrl){alert('Не удалось открыть файл.');return;}
  window.open(data.signedUrl,'_blank','noopener,noreferrer');
}"""
if anchor not in text:
    raise SystemExit('savedChannelMap anchor not found')
text = text.replace(anchor, helper, 1)

# Preserve attachment metadata when loading channel and DM history.
old = "select('body,created_at,profiles(username,avatar_color)')"
new = "select('body,attachments,created_at,profiles(username,avatar_color)')"
if old not in text:
    raise SystemExit('channel message select not found')
text = text.replace(old, new, 1)

old = "messages = data?.length ? data.map(m=>({name:m.profiles?.username||'Участник',time:new Date(m.created_at).toLocaleString('ru-RU'),color:m.profiles?.avatar_color||'#8b7cff',text:m.body})) : [];"
new = "messages = data?.length ? data.map(m=>({name:m.profiles?.username||'Участник',time:new Date(m.created_at).toLocaleString('ru-RU'),color:m.profiles?.avatar_color||'#8b7cff',text:m.body,attachments:m.attachments||[]})) : [];"
if old not in text:
    raise SystemExit('channel message mapping not found')
text = text.replace(old, new, 1)

old = "dmMessages = (data || []).map(row => ({name:row.profiles?.username || 'Пользователь',time:new Date(row.created_at).toLocaleString('ru-RU'),color:row.profiles?.avatar_color || '#8b7cff',text:row.body}));"
new = "dmMessages = (data || []).map(row => ({name:row.profiles?.username || 'Пользователь',time:new Date(row.created_at).toLocaleString('ru-RU'),color:row.profiles?.avatar_color || '#8b7cff',text:row.body,attachments:row.attachments||[]}));"
if old not in text:
    raise SystemExit('DM message mapping not found')
text = text.replace(old, new, 1)

# Escape rendered message text and expose attachments with short-lived signed URLs.
old = "<article class=\"message\"><div class=\"avatar\" style=\"background:${m.color}\">${m.name[0]}</div><div><div class=\"message-meta\"><b>${m.name}</b><time>${m.time}</time></div><p>${m.text}</p></div></article>"
new = "<article class=\"message\"><div class=\"avatar\" style=\"background:${escapeHtml(m.color||'#8b7cff')}\">${escapeHtml(m.name?.[0]||'?')}</div><div><div class=\"message-meta\"><b>${escapeHtml(m.name)}</b><time>${escapeHtml(m.time)}</time></div><p>${escapeHtml(m.text)}</p>${attachmentMarkup(m.attachments)}</div></article>"
if old not in text:
    raise SystemExit('message article template not found')
text = text.replace(old, new, 1)

# Store attachment metadata in optimistic local entries too.
text = text.replace("dmMessages.push({name:user.name,time:'только что',color:user.avatarColor||'#39d9a6',text:body});", "dmMessages.push({name:user.name,time:'только что',color:user.avatarColor||'#39d9a6',text:body,attachments:[attachment]});", 1)
text = text.replace("messages.push({name:user.name,time:'только что',color:user.avatarColor||'#39d9a6',text:body});", "messages.push({name:user.name,time:'только что',color:user.avatarColor||'#39d9a6',text:body,attachments:[attachment]});", 1)

# Add an explicit remove-friend control.
old = "<button data-call-id=\"${friend.id}\" data-call=\"${friend.username}\">📞</button>"
new = "<button data-call-id=\"${friend.id}\" data-call=\"${escapeHtml(friend.username)}\">📞</button><button class=\"danger compact\" data-remove-friend=\"${friend.id}\" title=\"Удалить из друзей\">×</button>"
if old not in text:
    raise SystemExit('friend call button not found')
text = text.replace(old, new, 1)

# Escape the most exposed user-controlled names in friend/DM lists and channel labels.
text = text.replace('data-dm=\"${friend.username}\"', 'data-dm=\"${escapeHtml(friend.username)}\"')
text = text.replace(' ${friend.username} <em>', ' ${escapeHtml(friend.username)} <em>')
text = text.replace('<b>${friend.username}</b>', '<b>${escapeHtml(friend.username)}</b>')
text = text.replace('<b>${request.profiles?.username||\'Пользователь\'}</b>', '<b>${escapeHtml(request.profiles?.username||\'Пользователь\')}</b>')
text = text.replace('data-channel-name=\"${c.name}\"', 'data-channel-name=\"${escapeHtml(c.name)}\"')
text = text.replace(' ${c.name}</button>', ' ${escapeHtml(c.name)}</button>')

# Wire attachment opening and reciprocal friendship removal.
anchor = "document.querySelectorAll('[data-accept-request]').forEach"
addition = """document.querySelectorAll('[data-attachment-path]').forEach(button=>button.addEventListener('click',()=>openAttachment(button.dataset.attachmentPath)));
  document.querySelectorAll('[data-remove-friend]').forEach(button=>button.addEventListener('click',async()=>{
    if(!supabase||!user.id)return;
    const friendId=button.dataset.removeFriend;
    const friend=friends.find(item=>item.id===friendId);
    if(!confirm(`Удалить ${friend?.username||'пользователя'} из друзей?`))return;
    const {error}=await supabase.from('friendships').delete().or(`and(user_id.eq.${user.id},friend_id.eq.${friendId}),and(user_id.eq.${friendId},friend_id.eq.${user.id})`);
    if(error){alert(`Не удалось удалить друга: ${error.message}`);return;}
    if(activeDmId===friendId){activeDmId=null;currentDm=null;dmMessages=[];window.__vesselDmLoaded=false;}
    window.__vesselSocialLoaded=false;await syncSocial(user);render();
  }));
  document.querySelectorAll('[data-accept-request]').forEach"""
if anchor not in text:
    raise SystemExit('accept request listener anchor not found')
text = text.replace(anchor, addition, 1)

path.write_text(text, encoding='utf-8')
print('Applied social, attachment and content-safety patch')
