-- Keep friend-request lifecycle aligned with the client while preserving RLS.
-- Senders may cancel only their own pending request and may recycle only their own
-- terminal request back to pending after the friendship no longer exists.

drop policy if exists "users can send friend requests" on public.friend_requests;
create policy "users can send friend requests" on public.friend_requests
for insert to authenticated
with check (
  sender_id=(select auth.uid())
  and sender_id<>receiver_id
  and not exists (
    select 1 from public.friendships f
    where f.user_id=(select auth.uid()) and f.friend_id=friend_requests.receiver_id
  )
);

drop policy if exists "senders can retry terminal friend requests" on public.friend_requests;
create policy "senders can retry terminal friend requests" on public.friend_requests
for update to authenticated
using (
  sender_id=(select auth.uid())
  and status in ('accepted','declined','cancelled')
)
with check (
  sender_id=(select auth.uid())
  and sender_id<>receiver_id
  and status='pending'
  and not exists (
    select 1 from public.friendships f
    where f.user_id=(select auth.uid()) and f.friend_id=friend_requests.receiver_id
  )
);

drop policy if exists "senders can cancel pending friend requests" on public.friend_requests;
create policy "senders can cancel pending friend requests" on public.friend_requests
for delete to authenticated
using (sender_id=(select auth.uid()) and status='pending');
