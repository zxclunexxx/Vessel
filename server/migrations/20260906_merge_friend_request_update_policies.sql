-- Merge the two permissive UPDATE policies into one equivalent policy.
-- This preserves receiver accept/decline and sender retry semantics while avoiding
-- duplicate permissive-policy evaluation on every UPDATE.
drop policy if exists "receivers can answer friend requests" on public.friend_requests;
drop policy if exists "senders can retry terminal friend requests" on public.friend_requests;

create policy "participants can update friend requests"
on public.friend_requests
for update
to authenticated
using (
  (select auth.uid()) = receiver_id
  or (sender_id = (select auth.uid()) and status in ('accepted','declined','cancelled'))
)
with check (
  ((select auth.uid()) = receiver_id and status in ('accepted','declined'))
  or (
    sender_id = (select auth.uid())
    and sender_id <> receiver_id
    and status = 'pending'
    and not exists (
      select 1 from public.friendships f
      where f.user_id = (select auth.uid()) and f.friend_id = friend_requests.receiver_id
    )
  )
);
