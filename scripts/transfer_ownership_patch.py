from pathlib import Path

main_path = Path('src/main.js')
schema_path = Path('server/schema.sql')
main = main_path.read_text(encoding='utf-8')
schema = schema_path.read_text(encoding='utf-8')
changed_main = False
changed_schema = False

rpc_sql = '''create or replace function public.vessel_transfer_server_ownership(target_server uuid, target_owner uuid)
returns jsonb
language plpgsql
security definer
set search_path='pg_catalog','public'
as $$
declare
  current_owner uuid;
begin
  if (select auth.uid()) is null then
    raise exception 'Authentication required' using errcode='42501';
  end if;
  if target_owner is null then
    raise exception 'Target owner is required' using errcode='22023';
  end if;
  select s.owner_id into current_owner
  from public.servers s
  where s.id=target_server
  for update;
  if not found then
    raise exception 'Server not found' using errcode='P0002';
  end if;
  if current_owner<>(select auth.uid()) then
    raise exception 'Only the current owner can transfer ownership' using errcode='42501';
  end if;
  if target_owner=current_owner then
    return jsonb_build_object('ok',true,'server_id',target_server,'owner_id',current_owner,'already_owner',true);
  end if;
  if not exists(
    select 1 from public.server_members sm
    where sm.server_id=target_server and sm.user_id=target_owner
  ) then
    raise exception 'Target owner must already be a server member' using errcode='42501';
  end if;
  update public.server_members
  set role=case
    when user_id=target_owner then 'owner'
    when user_id=current_owner then 'member'
    else role
  end
  where server_id=target_server and user_id in (current_owner,target_owner);
  update public.servers
  set owner_id=target_owner
  where id=target_server and owner_id=current_owner;
  if not found then
    raise exception 'Ownership changed concurrently' using errcode='40001';
  end if;
  return jsonb_build_object('ok',true,'server_id',target_server,'owner_id',target_owner,'previous_owner_id',current_owner,'already_owner',false);
end;
$$;
revoke all on function public.vessel_transfer_server_ownership(uuid,uuid) from public,anon;
grant execute on function public.vessel_transfer_server_ownership(uuid,uuid) to authenticated,service_role;'''

if 'create or replace function public.vessel_transfer_server_ownership' not in schema:
    anchor = '-- RLS --------------------------------------------------------------------------'
    if anchor not in schema:
        raise SystemExit('RLS anchor not found for ownership transfer RPC')
    schema = schema.replace(anchor, rpc_sql + '\n\n' + anchor, 1)
    changed_schema = True

old = '''    const action=await vesselChoice(`Участник ${member.username}`,[{label:'Сделать участником',value:'1'},{label:'Сделать модератором',value:'2'},{label:'Исключить из сервера',value:'3',danger:true}]);
    if(action==='1'||action==='2'){'''
new = '''    const action=await vesselChoice(`Участник ${member.username}`,[{label:'Сделать участником',value:'1'},{label:'Сделать модератором',value:'2'},{label:'Передать владение сервером',value:'4',danger:true},{label:'Исключить из сервера',value:'3',danger:true}]);
    if(action==='4'){
      if(!await vesselConfirm(`Передать сервер пользователю ${member.username}?`,'Ты перестанешь быть владельцем и станешь обычным участником.'))return;
      const serverId=server.dbId;
      const {data,error}=await supabase.rpc('vessel_transfer_server_ownership',{target_server:serverId,target_owner:memberId});
      if(error||data?.ok!==true){vesselNotice(`Не удалось передать сервер: ${error?.message||'неизвестная ошибка'}`,'error');return;}
      window.__vesselServersLoaded=false;
      window.__vesselMembersServerId=null;
      serverMembers=[];
      await syncSupabaseServers(user);
      const refreshedServer=getActiveServer();
      if(refreshedServer?.dbId===serverId){
        refreshedServer.__channelsLoaded=false;
        await Promise.all([syncSupabaseChannels(refreshedServer),syncServerMembers(user,refreshedServer)]);
      }
      vesselNotice(`Сервер передан пользователю ${member.username}.`,'success');
      render();
      return;
    }
    if(action==='1'||action==='2'){'''

if new in main:
    pass
elif old in main:
    main = main.replace(old, new, 1)
    changed_main = True
else:
    raise SystemExit('member management anchor not found for ownership transfer UI')

for marker in [
    "supabase.rpc('vessel_transfer_server_ownership'",
    "Передать владение сервером",
    'window.__vesselServersLoaded=false',
]:
    if marker not in main:
        raise SystemExit(f'missing ownership UI marker: {marker}')
for marker in [
    'create or replace function public.vessel_transfer_server_ownership',
    'for update;',
    "grant execute on function public.vessel_transfer_server_ownership(uuid,uuid) to authenticated,service_role;",
]:
    if marker not in schema:
        raise SystemExit(f'missing ownership RPC marker: {marker}')

if changed_main:
    main_path.write_text(main, encoding='utf-8')
if changed_schema:
    schema_path.write_text(schema, encoding='utf-8')
print('Ownership transfer patch applied' if changed_main or changed_schema else 'Ownership transfer patch already applied; nothing to change')
