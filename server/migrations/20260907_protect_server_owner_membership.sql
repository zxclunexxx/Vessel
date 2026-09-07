-- Keep the server owner's membership row immutable through DELETE.
-- Owners delete the server itself; non-owner members may leave, and owners may remove non-owners.
drop policy if exists "members can leave or owners can remove" on public.server_members;

create policy "members can leave or owners can remove"
on public.server_members
for delete
to authenticated
using (
  (
    user_id = (select auth.uid())
    and not exists (
      select 1 from public.servers s
      where s.id = server_members.server_id
        and s.owner_id = (select auth.uid())
    )
  )
  or exists (
    select 1 from public.servers s
    where s.id = server_members.server_id
      and s.owner_id = (select auth.uid())
      and server_members.user_id <> s.owner_id
  )
);
