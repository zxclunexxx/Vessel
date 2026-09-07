from pathlib import Path

path = Path('server/schema.sql')
schema = path.read_text(encoding='utf-8')

old_policy = '''create policy "participants can update friend requests" on public.friend_requests for update to authenticated
using(
  receiver_id=(select auth.uid())
  or (sender_id=(select auth.uid()) and status in ('accepted','declined','cancelled'))
)
with check(
  (receiver_id=(select auth.uid()) and status in ('accepted','declined'))
  or (
    sender_id=(select auth.uid())
    and sender_id<>receiver_id
    and status='pending'
    and not exists(select 1 from public.friendships f where f.user_id=(select auth.uid()) and f.friend_id=friend_requests.receiver_id)
  )
);'''
new_policy = '''create policy "participants can update friend requests" on public.friend_requests for update to authenticated
using(
  (receiver_id=(select auth.uid()) and status='pending')
  or (sender_id=(select auth.uid()) and status in ('accepted','declined','cancelled'))
)
with check(
  (receiver_id=(select auth.uid()) and status in ('accepted','declined'))
  or (
    sender_id=(select auth.uid())
    and sender_id<>receiver_id
    and status='pending'
    and not exists(select 1 from public.friendships f where f.user_id=(select auth.uid()) and f.friend_id=friend_requests.receiver_id)
  )
);'''
if new_policy not in schema:
    if old_policy not in schema:
        raise SystemExit('Friend-request update policy shape changed; inspect before patching')
    schema = schema.replace(old_policy, new_policy, 1)

accepted_marker = 'create or replace function public.vessel_notify_friend_accepted()'
if accepted_marker not in schema:
    anchor = '''drop trigger if exists vessel_friend_request_notification on public.friend_requests;
create trigger vessel_friend_request_notification after insert on public.friend_requests
for each row execute function public.vessel_notify_friend_request();
'''
    addition = '''
create or replace function public.vessel_notify_friend_accepted()
returns trigger
language plpgsql
security definer
set search_path='public'
as $$
declare accepter_name text;
begin
  select p.username into accepter_name from public.profiles p where p.id=new.receiver_id;
  insert into public.notifications(user_id,type,title,body,data)
  values(new.sender_id,'friend_accepted','Заявка в друзья принята',coalesce(accepter_name,'Пользователь') || ' принял(а) твою заявку в друзья',jsonb_build_object('request_id',new.id,'friend_id',new.receiver_id));
  return new;
end;
$$;
revoke all on function public.vessel_notify_friend_accepted() from public,anon,authenticated;

drop trigger if exists vessel_friend_request_retry_notification on public.friend_requests;
create trigger vessel_friend_request_retry_notification after update of status on public.friend_requests
for each row when (old.status is distinct from new.status and new.status='pending')
execute function public.vessel_notify_friend_request();

drop trigger if exists vessel_friend_request_accepted_notification on public.friend_requests;
create trigger vessel_friend_request_accepted_notification after update of status on public.friend_requests
for each row when (old.status is distinct from new.status and new.status='accepted')
execute function public.vessel_notify_friend_accepted();
'''
    if anchor not in schema:
        raise SystemExit('Friend-request notification trigger anchor missing')
    schema = schema.replace(anchor, anchor + addition, 1)

path.write_text(schema, encoding='utf-8')
print('Hardened friend-request transitions and added retry/accept notifications')
