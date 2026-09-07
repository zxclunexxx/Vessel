from pathlib import Path

path = Path('src/main.js')
text = path.read_text(encoding='utf-8')
changed = False

required = [
    'async function manageServerInvites(user,server)',
    "label:'Управление приглашениями',value:'4'",
    "if(action==='4'){await manageServerInvites(user,server);return;}",
    ".from('server_invites').select('id,code,created_at,expires_at,max_uses,uses')",
    ".delete().eq('id',invite.id).eq('server_id',serverId).eq('created_by',userId)",
]
if all(marker in text for marker in required):
    print('Server invite management already applied; nothing to change')
    raise SystemExit(0)

helper = r'''async function manageServerInvites(user,server){
  if(!supabase||!user?.id||!server?.dbId||server.role!=='owner'){vesselNotice('Управлять приглашениями может только владелец сервера.','error');return;}
  const userId=user.id;
  const serverId=server.dbId;
  const {data,error}=await supabase.from('server_invites').select('id,code,created_at,expires_at,max_uses,uses').eq('server_id',serverId).eq('created_by',userId).order('created_at',{ascending:false}).limit(100);
  if(savedUser?.id!==userId||getActiveServer()?.dbId!==serverId)return;
  if(error){vesselNotice('Не удалось загрузить приглашения сервера.','error');return;}
  const invites=data||[];
  const items=invites.map(invite=>{
    const expired=invite.expires_at&&new Date(invite.expires_at).getTime()<=Date.now();
    const exhausted=Number(invite.max_uses)>0&&Number(invite.uses)>=Number(invite.max_uses);
    const status=expired?'Истекло':exhausted?'Использовано':'Активно';
    const uses=Number(invite.max_uses)>0?`${Number(invite.uses)||0}/${Number(invite.max_uses)}`:`${Number(invite.uses)||0}/∞`;
    const expires=invite.expires_at?new Date(invite.expires_at).toLocaleString('ru-RU'):'без срока';
    return {title:invite.code,meta:status,body:`Использований: ${uses} · Срок: ${expires}`,value:invite.id,invite};
  });
  vesselListDialog(`Приглашения · ${server.name}`,items,'Активных или старых приглашений пока нет.',async item=>{
    const invite=item?.invite;
    if(!invite||savedUser?.id!==userId)return;
    const action=await vesselChoice(`Приглашение ${invite.code}`,[{label:'Показать и скопировать код',value:'copy'},{label:'Отозвать приглашение',value:'revoke',danger:true}]);
    if(action==='copy'){vesselCodeDialog(`Приглашение в ${server.name}`,invite.code);return;}
    if(action!=='revoke')return;
    if(!await vesselConfirm(`Отозвать приглашение ${invite.code}?`,'После этого по этому коду больше нельзя будет вступить в сервер.'))return;
    if(savedUser?.id!==userId)return;
    const {data:deleted,error:deleteError}=await supabase.from('server_invites').delete().eq('id',invite.id).eq('server_id',serverId).eq('created_by',userId).select('id');
    if(savedUser?.id!==userId)return;
    if(deleteError||!deleted?.some(row=>row.id===invite.id)){vesselNotice('Не удалось отозвать приглашение.','error');return;}
    vesselNotice('Приглашение отозвано.','success');
  });
}

'''
anchor = 'async function refreshReadOnlyDirectMessage(user,peerId){'
if 'async function manageServerInvites(user,server)' not in text:
    if anchor not in text:
        raise SystemExit('server invite management helper anchor not found')
    text = text.replace(anchor, helper + anchor, 1)
    changed = True

old_choice = "const action=await vesselChoice('Управление сервером',[{label:'Создать приглашение',value:'1'},{label:'Переименовать сервер',value:'2'},{label:'Удалить сервер',value:'3',danger:true}]);"
new_choice = "const action=await vesselChoice('Управление сервером',[{label:'Создать приглашение',value:'1'},{label:'Управление приглашениями',value:'4'},{label:'Переименовать сервер',value:'2'},{label:'Удалить сервер',value:'3',danger:true}]);"
if "label:'Управление приглашениями',value:'4'" not in text:
    if old_choice not in text:
        raise SystemExit('server owner menu anchor not found')
    text = text.replace(old_choice, new_choice, 1)
    changed = True

old_after_create = """        if(error)vesselNotice(`Не удалось создать приглашение: ${error.message}`,'error');else vesselCodeDialog(`Приглашение в ${server.name}`,code);
        return;
      }
      if(action==='2'){"""
new_after_create = """        if(error)vesselNotice(`Не удалось создать приглашение: ${error.message}`,'error');else vesselCodeDialog(`Приглашение в ${server.name}`,code);
        return;
      }
      if(action==='4'){await manageServerInvites(user,server);return;}
      if(action==='2'){"""
if "if(action==='4'){await manageServerInvites(user,server);return;}" not in text:
    if old_after_create not in text:
        raise SystemExit('server invite menu action anchor not found')
    text = text.replace(old_after_create, new_after_create, 1)
    changed = True

for marker in required:
    if marker not in text:
        raise SystemExit(f'missing server invite management marker: {marker}')

if changed:
    path.write_text(text, encoding='utf-8')
    print('Applied server invite management')
else:
    print('Server invite management already applied; nothing to change')
