from pathlib import Path

path = Path('server/schema.sql')
schema = path.read_text(encoding='utf-8')

helper_marker = 'create or replace function private.can_upload_vessel_file(object_name text)'
if helper_marker not in schema:
    anchor = '''revoke all on function private.can_read_vessel_file(text) from public,anon;
grant execute on function private.can_read_vessel_file(text) to authenticated,service_role;
'''
    helper = '''
create or replace function private.can_upload_vessel_file(object_name text)
returns boolean
language plpgsql
stable
security definer
set search_path='pg_catalog','public','storage'
as $$
declare
  parts text[];
  uid uuid;
  peer_uuid uuid;
  channel_uuid uuid;
begin
  uid := (select auth.uid());
  if uid is null then return false; end if;
  parts := storage.foldername(object_name);
  if coalesce(array_length(parts,1),0)<3 or parts[1]<>uid::text then return false; end if;
  if parts[2]='dm' then
    begin peer_uuid:=parts[3]::uuid; exception when others then return false; end;
    return peer_uuid<>uid and exists(select 1 from public.friendships f where f.user_id=uid and f.friend_id=peer_uuid);
  end if;
  if parts[2]='channel' then
    begin channel_uuid:=parts[3]::uuid; exception when others then return false; end;
    return exists(
      select 1 from public.channels c
      left join public.server_members sm on sm.server_id=c.server_id and sm.user_id=uid
      left join public.servers s on s.id=c.server_id
      where c.id=channel_uuid and c.kind='text' and (sm.user_id is not null or s.owner_id=uid)
    );
  end if;
  return false;
end;
$$;
revoke all on function private.can_upload_vessel_file(text) from public,anon;
grant execute on function private.can_upload_vessel_file(text) to authenticated,service_role;
'''
    if anchor not in schema:
        raise SystemExit('Storage read helper anchor missing')
    schema = schema.replace(anchor, anchor + helper, 1)

old_insert = '''create policy "users upload vessel files" on storage.objects for insert to authenticated
with check(bucket_id='vessel-files' and (storage.foldername(name))[1]=(select auth.uid())::text);'''
new_insert = '''create policy "users upload vessel files" on storage.objects for insert to authenticated
with check(bucket_id='vessel-files' and private.can_upload_vessel_file(name));'''
if new_insert not in schema:
    if old_insert not in schema:
        raise SystemExit('Storage upload policy shape changed; inspect before patching')
    schema = schema.replace(old_insert, new_insert, 1)

old_update = '''create policy "users update vessel files" on storage.objects for update to authenticated
using(bucket_id='vessel-files' and owner_id=(select auth.uid())::text)
with check(bucket_id='vessel-files' and owner_id=(select auth.uid())::text);'''
new_update = '''create policy "users update vessel files" on storage.objects for update to authenticated
using(bucket_id='vessel-files' and owner_id=(select auth.uid())::text)
with check(bucket_id='vessel-files' and owner_id=(select auth.uid())::text and private.can_upload_vessel_file(name));'''
if new_update not in schema:
    if old_update not in schema:
        raise SystemExit('Storage update policy shape changed; inspect before patching')
    schema = schema.replace(old_update, new_update, 1)

path.write_text(schema, encoding='utf-8')
print('Hardened Vessel attachment upload context policies')
