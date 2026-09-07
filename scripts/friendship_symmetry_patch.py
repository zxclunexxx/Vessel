from pathlib import Path

path = Path('server/schema.sql')
schema = path.read_text(encoding='utf-8')

marker = 'create or replace function public.vessel_delete_reverse_friendship()'
if marker in schema:
    print('Reverse friendship delete trigger already present')
else:
    anchor = '''drop trigger if exists vessel_create_friendship_after_accept on public.friend_requests;
create trigger vessel_create_friendship_after_accept after update of status on public.friend_requests
for each row execute function public.vessel_create_friendship_on_accept();
'''
    block = '''
create or replace function public.vessel_delete_reverse_friendship()
returns trigger
language plpgsql
security definer
set search_path='public'
as $$
begin
  delete from public.friendships
  where user_id=old.friend_id and friend_id=old.user_id;
  return old;
end;
$$;
revoke all on function public.vessel_delete_reverse_friendship() from public,anon,authenticated;

drop trigger if exists vessel_delete_reverse_friendship_after_delete on public.friendships;
create trigger vessel_delete_reverse_friendship_after_delete after delete on public.friendships
for each row execute function public.vessel_delete_reverse_friendship();
'''
    if anchor not in schema:
        raise SystemExit('Friendship acceptance trigger anchor missing')
    schema = schema.replace(anchor, anchor + block, 1)
    path.write_text(schema, encoding='utf-8')
    print('Added symmetric friendship delete trigger')
