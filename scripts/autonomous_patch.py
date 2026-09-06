from pathlib import Path

path=Path('src/main.js')
text=path.read_text(encoding='utf-8')
changed=False

def replace_once(old,new,label):
    global text, changed
    if old not in text:
        if new in text:
            return
        raise SystemExit(f'{label} anchor not found')
    text=text.replace(old,new,1)
    changed=True

# Server renames/icons and profile status/name changes should propagate to every authorized
# open client instead of requiring a reload.
old="""    supabase.channel(`vessel-channel-messages-${user.id}`).on('postgres_changes',{event:'INSERT',schema:'public',table:'messages'},payload=>{
      if(payload.new.channel_id===activeChannelId && payload.new.author_id!==user.id)loadChannelMessages(activeChannelId).catch(error=>console.warn('Message refresh failed',error));
    }).subscribe(),
    supabase.channel(`vessel-notifications-${user.id}`).on('postgres_changes',{event:'INSERT',schema:'public',table:'notifications',filter:`user_id=eq.${user.id}`},payload=>{notifications=[payload.new,...notifications];render();}).subscribe()
"""
new="""    supabase.channel(`vessel-channel-messages-${user.id}`).on('postgres_changes',{event:'INSERT',schema:'public',table:'messages'},payload=>{
      if(payload.new.channel_id===activeChannelId && payload.new.author_id!==user.id)loadChannelMessages(activeChannelId).catch(error=>console.warn('Message refresh failed',error));
    }).subscribe(),
    supabase.channel(`vessel-profiles-${user.id}`).on('postgres_changes',{event:'UPDATE',schema:'public',table:'profiles'},payload=>{
      const row=payload.new;
      if(!row?.id)return;
      let changed=false;
      if(savedUser?.id===row.id){
        savedUser={...savedUser,name:row.username||savedUser.name,status:row.status||savedUser.status,avatarColor:row.avatar_color||savedUser.avatarColor};
        localStorage.setItem('vesselUser',JSON.stringify(savedUser));
        changed=true;
      }
      const friend=friends.find(item=>item.id===row.id);
      if(friend){friend.username=row.username||friend.username;friend.status=row.status||friend.status;friend.avatar_color=row.avatar_color||friend.avatar_color;changed=true;}
      const member=serverMembers.find(item=>item.id===row.id);
      if(member){member.username=row.username||member.username;member.status=row.status||member.status;member.avatar_color=row.avatar_color||member.avatar_color;changed=true;}
      if(activeDmId===row.id&&row.username){currentDm=row.username;changed=true;}
      if(changed)render();
    }).subscribe(),
    supabase.channel(`vessel-servers-${user.id}`).on('postgres_changes',{event:'UPDATE',schema:'public',table:'servers'},payload=>{
      const row=payload.new;
      const server=row?.id?servers.find(item=>item.id===row.id):null;
      if(!server)return;
      server.name=row.name||server.name;
      server.icon=row.icon||server.icon;
      render();
    }).subscribe(),
    supabase.channel(`vessel-notifications-${user.id}`).on('postgres_changes',{event:'INSERT',schema:'public',table:'notifications',filter:`user_id=eq.${user.id}`},payload=>{notifications=[payload.new,...notifications];render();}).subscribe()
"""
replace_once(old,new,'profile/server realtime insertion')

# When the current user edits profile settings, update the authenticated local state only after
# the database confirms the write; remote clients then receive the same change through Realtime.
old="""    const {error}=await supabase.from('profiles').update({username:name,status}).eq('id',user.id);
    if(error){vesselNotice(`Не удалось сохранить профиль: ${error.message}`,'error');return;}
    savedUser={...user,name,status};localStorage.setItem('vesselUser',JSON.stringify(savedUser));modal.classList.add('hidden');render();"""
new="""    const {data:updated,error}=await supabase.from('profiles').update({username:name,status}).eq('id',user.id).select('username,status,avatar_color').single();
    if(error){
      const duplicate=error.code==='23505';
      vesselNotice(duplicate?'Это имя пользователя уже занято.':`Не удалось сохранить профиль: ${error.message}`,'error');
      return;
    }
    savedUser={...user,name:updated?.username||name,status:updated?.status||status,avatarColor:updated?.avatar_color||user.avatarColor};
    localStorage.setItem('vesselUser',JSON.stringify(savedUser));modal.classList.add('hidden');render();"""
replace_once(old,new,'confirmed profile update')

# Reciprocal pending friend requests are blocked by the database. Surface the race/duplicate
# case as a normal state instead of a generic failure.
old="""  if(sendError){vesselNotice('Не удалось отправить заявку.','error');return;}"""
new="""  if(sendError){
    if(sendError.code==='23505'){
      window.__vesselSocialLoaded=false;
      await syncSocial(user);
      vesselNotice('Заявка уже существует или пользователь одновременно отправил заявку тебе. Открой раздел «Друзья».');
      return;
    }
    vesselNotice('Не удалось отправить заявку.','error');return;
  }"""
replace_once(old,new,'friend request duplicate handling')

schema_path=Path('server/schema.sql')
schema=schema_path.read_text(encoding='utf-8')
schema_old="""create index if not exists friend_requests_receiver_status_idx on public.friend_requests(receiver_id,status);
"""
schema_new="""create index if not exists friend_requests_receiver_status_idx on public.friend_requests(receiver_id,status);
create unique index if not exists friend_requests_pending_pair_uidx
on public.friend_requests (least(sender_id,receiver_id), greatest(sender_id,receiver_id))
where status='pending';
"""
if schema_old in schema and 'friend_requests_pending_pair_uidx' not in schema:
    schema=schema.replace(schema_old,schema_new,1)
    schema_path.write_text(schema,encoding='utf-8')
    changed=True
elif 'friend_requests_pending_pair_uidx' not in schema:
    raise SystemExit('friend request schema anchor not found')

for required in ['vessel-profiles-${user.id}','vessel-servers-${user.id}',"error.code==='23505'",'.select(\'username,status,avatar_color\').single()','friend_requests_pending_pair_uidx']:
    source=text if required!='friend_requests_pending_pair_uidx' else schema
    if required not in source:
        raise SystemExit(f'missing Vessel hardening: {required}')

if changed:
    path.write_text(text,encoding='utf-8')
    print('Applied Vessel realtime/profile/friend-request hardening')
else:
    print('Vessel hardening already applied; nothing to change')
