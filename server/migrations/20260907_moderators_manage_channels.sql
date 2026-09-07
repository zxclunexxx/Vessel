-- Keep channel management aligned with the Vessel role model:
-- owners and moderators may manage channels; regular members may only use them.

drop policy if exists "owners can create channels" on public.channels;
drop policy if exists "owners can update channels" on public.channels;
drop policy if exists "owners can delete channels" on public.channels;
drop policy if exists "owners and moderators can create channels" on public.channels;
drop policy if exists "owners and moderators can update channels" on public.channels;
drop policy if exists "owners and moderators can delete channels" on public.channels;

create policy "owners and moderators can create channels"
on public.channels for insert to authenticated
with check (
  exists (
    select 1 from public.servers s
    where s.id = channels.server_id and s.owner_id = (select auth.uid())
  )
  or exists (
    select 1 from public.server_members m
    where m.server_id = channels.server_id
      and m.user_id = (select auth.uid())
      and m.role = 'moderator'
  )
);

create policy "owners and moderators can update channels"
on public.channels for update to authenticated
using (
  exists (
    select 1 from public.servers s
    where s.id = channels.server_id and s.owner_id = (select auth.uid())
  )
  or exists (
    select 1 from public.server_members m
    where m.server_id = channels.server_id
      and m.user_id = (select auth.uid())
      and m.role = 'moderator'
  )
)
with check (
  exists (
    select 1 from public.servers s
    where s.id = channels.server_id and s.owner_id = (select auth.uid())
  )
  or exists (
    select 1 from public.server_members m
    where m.server_id = channels.server_id
      and m.user_id = (select auth.uid())
      and m.role = 'moderator'
  )
);

create policy "owners and moderators can delete channels"
on public.channels for delete to authenticated
using (
  exists (
    select 1 from public.servers s
    where s.id = channels.server_id and s.owner_id = (select auth.uid())
  )
  or exists (
    select 1 from public.server_members m
    where m.server_id = channels.server_id
      and m.user_id = (select auth.uid())
      and m.role = 'moderator'
  )
);
