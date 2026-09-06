-- Align DM peer discovery with profile column privacy and avoid SECURITY DEFINER exposure.
alter policy "profiles visible to related users" on public.profiles
using (
  id=(select auth.uid())
  or exists(select 1 from public.friendships f where (f.user_id=(select auth.uid()) and f.friend_id=profiles.id) or (f.friend_id=(select auth.uid()) and f.user_id=profiles.id))
  or exists(select 1 from public.friend_requests fr where (fr.sender_id=(select auth.uid()) and fr.receiver_id=profiles.id) or (fr.receiver_id=(select auth.uid()) and fr.sender_id=profiles.id))
  or exists(select 1 from public.server_members mine join public.server_members theirs on theirs.server_id=mine.server_id where mine.user_id=(select auth.uid()) and theirs.user_id=profiles.id)
  or exists(select 1 from public.direct_messages dm where (dm.sender_id=(select auth.uid()) and dm.receiver_id=profiles.id) or (dm.receiver_id=(select auth.uid()) and dm.sender_id=profiles.id))
);

alter function public.vessel_dm_threads() security invoker;
revoke execute on function public.vessel_dm_threads() from public, anon;
grant execute on function public.vessel_dm_threads() to authenticated;
