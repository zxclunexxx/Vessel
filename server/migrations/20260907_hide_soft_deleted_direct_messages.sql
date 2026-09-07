drop policy if exists "dm participants can read" on public.direct_messages;
create policy "dm participants can read"
on public.direct_messages for select to authenticated
using (
  deleted_at is null
  and (sender_id = (select auth.uid()) or receiver_id = (select auth.uid()))
);

create or replace function public.vessel_dm_threads()
returns table(peer_id uuid, username text, avatar_color text, status text, last_message_at timestamptz)
language sql
stable
security invoker
set search_path='pg_catalog','public'
as $$
  with peer_messages as (
    select
      case when dm.sender_id = auth.uid() then dm.receiver_id else dm.sender_id end as peer_id,
      max(dm.created_at) as last_message_at
    from public.direct_messages dm
    where auth.uid() is not null
      and dm.deleted_at is null
      and (dm.sender_id = auth.uid() or dm.receiver_id = auth.uid())
    group by 1
  )
  select p.id, p.username, p.avatar_color, p.status, pm.last_message_at
  from peer_messages pm
  join public.profiles p on p.id = pm.peer_id
  order by pm.last_message_at desc;
$$;
revoke all on function public.vessel_dm_threads() from public, anon;
grant execute on function public.vessel_dm_threads() to authenticated, service_role;
