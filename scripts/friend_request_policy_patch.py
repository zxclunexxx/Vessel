from pathlib import Path

path = Path('server/schema.sql')
schema = path.read_text(encoding='utf-8')
changed = False

old = """create policy \"receivers can answer friend requests\" on public.friend_requests for update to authenticated using(receiver_id=(select auth.uid())) with check(receiver_id=(select auth.uid()) and status in ('accepted','declined'));
create policy \"senders can retry terminal friend requests\" on public.friend_requests for update to authenticated
using(sender_id=(select auth.uid()) and status in ('accepted','declined','cancelled'))
with check(
  sender_id=(select auth.uid())
  and sender_id<>receiver_id
  and status='pending'
  and not exists(select 1 from public.friendships f where f.user_id=(select auth.uid()) and f.friend_id=friend_requests.receiver_id)
);"""

new = """create policy \"participants can update friend requests\" on public.friend_requests for update to authenticated
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
);"""

if new in schema:
    print('Friend request update policy already consolidated; nothing to change')
elif old in schema:
    schema = schema.replace(old, new, 1)
    changed = True
else:
    raise SystemExit('friend request update policy anchor not found')

for marker in [
    'create policy "participants can update friend requests"',
    "receiver_id=(select auth.uid()) and status in ('accepted','declined')",
    "sender_id=(select auth.uid()) and status in ('accepted','declined','cancelled')",
]:
    if marker not in schema:
        raise SystemExit(f'missing consolidated friend request policy marker: {marker}')

if changed:
    path.write_text(schema, encoding='utf-8')
    print('Consolidated friend request UPDATE policies')
