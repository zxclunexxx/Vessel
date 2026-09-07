-- Atomically transfer a server to an existing member.
create or replace function public.vessel_transfer_server_ownership(target_server uuid, target_owner uuid)
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
grant execute on function public.vessel_transfer_server_ownership(uuid,uuid) to authenticated,service_role;
