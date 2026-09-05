from pathlib import Path

main_path = Path('src/main.js')
css_path = Path('src/style.css')
text = main_path.read_text(encoding='utf-8')
css = css_path.read_text(encoding='utf-8')

old = """serverMembers.map(member=>`<div class=\"member online\"><div class=\"avatar\" style=\"background:${member.avatar_color}\">${member.username[0]?.toUpperCase()||'?'}</div><span>${member.username}<small>${member.role==='owner'?'Создатель':member.status}</small></span><i></i></div>`).join('')"""
new = """serverMembers.map(member=>`<div class=\"member online\"><div class=\"avatar\" style=\"background:${escapeHtml(member.avatar_color||'#8b7cff')}\">${escapeHtml(member.username[0]?.toUpperCase()||'?')}</div><span>${escapeHtml(member.username)}<small>${member.role==='owner'?'Создатель':member.role==='moderator'?'Модератор':escapeHtml(member.status)}</small></span>${activeServer?.role==='owner'&&member.role!=='owner'?`<button class=\"member-manage\" data-manage-member=\"${member.id}\" title=\"Управление участником\">•••</button>`:'<i></i>'}</div>`).join('')"""
if old not in text:
    raise SystemExit('member list template not found')
text = text.replace(old, new, 1)

anchor = """  document.querySelector('#head-settings').addEventListener('click',()=>modal.classList.remove('hidden'));"""
addition = """  document.querySelector('#head-settings').addEventListener('click',()=>modal.classList.remove('hidden'));
  document.querySelectorAll('[data-manage-member]').forEach(button=>button.addEventListener('click',async()=>{
    const server=servers[activeServerIndex];
    if(!supabase||!user.id||server?.role!=='owner')return;
    const memberId=button.dataset.manageMember;
    const member=serverMembers.find(item=>item.id===memberId);
    if(!member)return;
    const action=prompt(`Участник ${member.username}:\n1 — сделать участником\n2 — сделать модератором\n3 — исключить из сервера`);
    if(action==='1'||action==='2'){
      const role=action==='2'?'moderator':'member';
      const {error}=await supabase.from('server_members').update({role}).eq('server_id',server.dbId).eq('user_id',memberId);
      if(error){alert(`Не удалось изменить роль: ${error.message}`);return;}
      window.__vesselMembersServerId=null;serverMembers=[];await syncServerMembers(user,server);render();return;
    }
    if(action==='3'){
      if(!confirm(`Исключить ${member.username} из сервера?`))return;
      const {error}=await supabase.from('server_members').delete().eq('server_id',server.dbId).eq('user_id',memberId);
      if(error){alert(`Не удалось исключить участника: ${error.message}`);return;}
      window.__vesselMembersServerId=null;serverMembers=[];await syncServerMembers(user,server);render();
    }
  }));"""
if anchor not in text:
    raise SystemExit('head settings anchor not found')
text = text.replace(anchor, addition, 1)

# Improve layout for attachment buttons, friend removal and member moderation.
css += "\n.attachment-link{display:inline-flex;align-items:center;gap:7px;margin-top:7px;margin-right:7px;border:1px solid #3b4257;background:#222735;color:#cfd4e6;border-radius:9px;padding:8px 10px;font:500 12px Inter;cursor:pointer}.attachment-link:hover{background:#2c3243;border-color:#5b6380}.member-manage{margin-left:auto;border:0;background:#252a38;color:#9ca4ba;border-radius:8px;min-width:30px;height:30px;cursor:pointer}.member-manage:hover{background:#32394c;color:#fff}.friend-row{grid-template-columns:44px minmax(120px,1fr) auto 42px 42px 42px}@media(max-width:600px){.friend-row{grid-template-columns:40px minmax(0,1fr) 36px 36px 36px}}\n"

main_path.write_text(text, encoding='utf-8')
css_path.write_text(css, encoding='utf-8')
print('Applied member role management and attachment UI patch')
