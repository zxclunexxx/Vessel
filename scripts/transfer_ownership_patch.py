from pathlib import Path

main_path = Path('src/main.js')
schema_path = Path('server/schema.sql')
main = main_path.read_text(encoding='utf-8')
schema = schema_path.read_text(encoding='utf-8')
changed_main = False
changed_schema = False

old_rpc = '''create or replace function public.vessel_transfer_server_ownership(target_server uuid, target_owner uuid)
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

new_rpc = '''create or replace function public.vessel_transfer_server_ownership(target_server uuid, target_owner uuid, actor_user uuid)
returns jsonb
language plpgsql
security definer
set search_path='pg_catalog','public'
as $$
declare
  current_owner uuid;
begin
  if actor_user is null or target_owner is null then
    raise exception 'Actor and target owner are required' using errcode='22023';
  end if;
  select s.owner_id into current_owner
  from public.servers s
  where s.id=target_server
  for update;
  if not found then
    raise exception 'Server not found' using errcode='P0002';
  end if;
  if current_owner<>actor_user then
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
revoke all on function public.vessel_transfer_server_ownership(uuid,uuid,uuid) from public,anon,authenticated;
grant execute on function public.vessel_transfer_server_ownership(uuid,uuid,uuid) to service_role;'''

if new_rpc in schema:
    pass
elif old_rpc in schema:
    schema = schema.replace(old_rpc, new_rpc, 1)
    changed_schema = True
else:
    raise SystemExit('ownership transfer RPC shape changed; inspect before patching')

old_call = "const {data,error}=await supabase.rpc('vessel_transfer_server_ownership',{target_server:serverId,target_owner:memberId});"
new_call = "const {data,error}=await supabase.functions.invoke('transfer-server-ownership',{body:{server_id:serverId,target_owner:memberId}});"
if new_call in main:
    pass
elif old_call in main:
    main = main.replace(old_call, new_call, 1)
    changed_main = True
else:
    raise SystemExit('ownership transfer client call anchor not found')

for marker in [
    "supabase.functions.invoke('transfer-server-ownership'",
    "Передать владение сервером",
    'window.__vesselServersLoaded=false',
]:
    if marker not in main:
        raise SystemExit(f'missing ownership UI marker: {marker}')
for marker in [
    'create or replace function public.vessel_transfer_server_ownership(target_server uuid, target_owner uuid, actor_user uuid)',
    'current_owner<>actor_user',
    'for update;',
    'revoke all on function public.vessel_transfer_server_ownership(uuid,uuid,uuid) from public,anon,authenticated;',
    'grant execute on function public.vessel_transfer_server_ownership(uuid,uuid,uuid) to service_role;',
]:
    if marker not in schema:
        raise SystemExit(f'missing ownership service boundary marker: {marker}')
if "grant execute on function public.vessel_transfer_server_ownership(uuid,uuid) to authenticated" in schema:
    raise SystemExit('legacy browser-executable ownership transfer RPC is still granted')

if changed_main:
    main_path.write_text(main, encoding='utf-8')
if changed_schema:
    schema_path.write_text(schema, encoding='utf-8')
print('Ownership transfer service-boundary patch applied' if changed_main or changed_schema else 'Ownership transfer service-boundary patch already applied; nothing to change')
