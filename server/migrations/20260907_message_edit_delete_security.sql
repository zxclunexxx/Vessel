-- Authors may edit/delete only their own channel messages while they still have
-- access to that server. Routing/identity columns stay immutable from the client.
drop policy if exists "authors can update own channel messages" on public.messages;
drop policy if exists "authors can delete own channel messages" on public.messages;

create policy "authors can update own channel messages"
on public.messages for update to authenticated
using (
  author_id = (select auth.uid())
  and (
    exists (
      select 1 from public.server_members m
      join public.channels c on c.server_id = m.server_id
      where c.id = messages.channel_id and m.user_id = (select auth.uid())
    )
    or exists (
      select 1 from public.channels c
      join public.servers s on s.id = c.server_id
      where c.id = messages.channel_id and s.owner_id = (select auth.uid())
    )
  )
)
with check (
  author_id = (select auth.uid())
  and (
    exists (
      select 1 from public.server_members m
      join public.channels c on c.server_id = m.server_id
      where c.id = messages.channel_id and m.user_id = (select auth.uid())
    )
    or exists (
      select 1 from public.channels c
      join public.servers s on s.id = c.server_id
      where c.id = messages.channel_id and s.owner_id = (select auth.uid())
    )
  )
);

create policy "authors can delete own channel messages"
on public.messages for delete to authenticated
using (
  author_id = (select auth.uid())
  and (
    exists (
      select 1 from public.server_members m
      join public.channels c on c.server_id = m.server_id
      where c.id = messages.channel_id and m.user_id = (select auth.uid())
    )
    or exists (
      select 1 from public.channels c
      join public.servers s on s.id = c.server_id
      where c.id = messages.channel_id and s.owner_id = (select auth.uid())
    )
  )
);

revoke update on table public.messages from authenticated;
grant update (body, attachments, edited_at) on table public.messages to authenticated;
