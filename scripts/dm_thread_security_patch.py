from pathlib import Path

path = Path('server/schema.sql')
schema = path.read_text(encoding='utf-8')
changed = False


def replace_once(old, new, label):
    global schema, changed
    if new in schema:
        return
    if old not in schema:
        raise SystemExit(f'{label} anchor not found')
    schema = schema.replace(old, new, 1)
    changed = True


# Now that profile.email is protected by column-level grants, users with an existing DM history
# may safely read the peer's public profile row. This preserves historical thread labels after
# unfriend without exposing private profile columns.
policy_old = """create policy \"profiles visible to related users\" on public.profiles for select to authenticated using (
  id=(select auth.uid())
  or exists(select 1 from public.friendships f where (f.user_id=(select auth.uid()) and f.friend_id=profiles.id) or (f.friend_id=(select auth.uid()) and f.user_id=profiles.id))
  or exists(select 1 from public.friend_requests fr where (fr.sender_id=(select auth.uid()) and fr.receiver_id=profiles.id) or (fr.receiver_id=(select auth.uid()) and fr.sender_id=profiles.id))
  or exists(select 1 from public.server_members mine join public.server_members theirs on theirs.server_id=mine.server_id where mine.user_id=(select auth.uid()) and theirs.user_id=profiles.id)
);"""
policy_new = """create policy \"profiles visible to related users\" on public.profiles for select to authenticated using (
  id=(select auth.uid())
  or exists(select 1 from public.friendships f where (f.user_id=(select auth.uid()) and f.friend_id=profiles.id) or (f.friend_id=(select auth.uid()) and f.user_id=profiles.id))
  or exists(select 1 from public.friend_requests fr where (fr.sender_id=(select auth.uid()) and fr.receiver_id=profiles.id) or (fr.receiver_id=(select auth.uid()) and fr.sender_id=profiles.id))
  or exists(select 1 from public.server_members mine join public.server_members theirs on theirs.server_id=mine.server_id where mine.user_id=(select auth.uid()) and theirs.user_id=profiles.id)
  or exists(select 1 from public.direct_messages dm where (dm.sender_id=(select auth.uid()) and dm.receiver_id=profiles.id) or (dm.receiver_id=(select auth.uid()) and dm.sender_id=profiles.id))
);"""
replace_once(policy_old, policy_new, 'historical DM profile visibility')

# The RPC no longer needs elevated privileges. direct_messages RLS limits rows to the caller and
# profiles RLS now allows only peers that have an actual relationship/history with that caller.
function_old = """-- Safe list of direct-message peers for the authenticated user. This avoids broadening
-- profiles RLS (profiles also stores email) while keeping old conversations discoverable.
create or replace function public.vessel_dm_threads()
returns table(peer_id uuid, username text, avatar_color text, status text, last_message_at timestamptz)
language sql
security definer
set search_path = public
stable
as $$
  with peer_messages as (
    select
      case when dm.sender_id = auth.uid() then dm.receiver_id else dm.sender_id end as peer_id,
      max(dm.created_at) as last_message_at
    from public.direct_messages dm
    where auth.uid() is not null
      and (dm.sender_id = auth.uid() or dm.receiver_id = auth.uid())
    group by 1
  )
  select p.id, p.username, p.avatar_color, p.status, pm.last_message_at
  from peer_messages pm
  join public.profiles p on p.id = pm.peer_id
  order by pm.last_message_at desc;
$$;"""
function_new = """-- Safe list of direct-message peers for the authenticated user. The function runs as the
-- caller and relies on direct_messages/profile RLS plus profile column grants.
create or replace function public.vessel_dm_threads()
returns table(peer_id uuid, username text, avatar_color text, status text, last_message_at timestamptz)
language sql
security invoker
set search_path = public
stable
as $$
  with peer_messages as (
    select
      case when dm.sender_id = auth.uid() then dm.receiver_id else dm.sender_id end as peer_id,
      max(dm.created_at) as last_message_at
    from public.direct_messages dm
    where auth.uid() is not null
      and (dm.sender_id = auth.uid() or dm.receiver_id = auth.uid())
    group by 1
  )
  select p.id, p.username, p.avatar_color, p.status, pm.last_message_at
  from peer_messages pm
  join public.profiles p on p.id = pm.peer_id
  order by pm.last_message_at desc;
$$;"""
replace_once(function_old, function_new, 'DM thread security invoker')

for marker in [
    'or exists(select 1 from public.direct_messages dm where (dm.sender_id=(select auth.uid()) and dm.receiver_id=profiles.id) or (dm.receiver_id=(select auth.uid()) and dm.sender_id=profiles.id))',
    'security invoker',
    'relies on direct_messages/profile RLS plus profile column grants',
]:
    if marker not in schema:
        raise SystemExit(f'missing DM thread security marker: {marker}')

if changed:
    path.write_text(schema, encoding='utf-8')
    print('Applied historical DM visibility and SECURITY INVOKER hardening')
else:
    print('DM thread invoker hardening already applied; nothing to change')
