-- Vessel database bootstrap snapshot (PostgreSQL / Supabase)
-- Updated 2026-09-05 to match the secured production schema.
-- Intended for a fresh Supabase project. Existing deployments should use migrations.

create extension if not exists pgcrypto;
create schema if not exists private;
revoke all on schema private from public, anon;
grant usage on schema private to authenticated, service_role;

-- Core identity and server model ------------------------------------------------
create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  username text not null unique,
  email text not null,
  avatar_color text not null default '#8b7cff',
  status text not null default 'online' check (status in ('online','dnd','away')),
  created_at timestamptz not null default now(),
  constraint profiles_username_length_check check (char_length(trim(username)) between 2 and 64)
);
create unique index if not exists profiles_username_lower_uidx on public.profiles(lower(username));

create table if not exists public.servers (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  icon text not null default 'V',
  owner_id uuid not null references public.profiles(id) on delete cascade,
  created_at timestamptz not null default now(),
  constraint servers_name_length_check check (char_length(trim(name)) between 2 and 80),
  constraint servers_icon_length_check check (char_length(icon) between 1 and 12)
);
create index if not exists servers_owner_id_idx on public.servers(owner_id);

create table if not exists public.server_members (
  server_id uuid not null references public.servers(id) on delete cascade,
  user_id uuid not null references public.profiles(id) on delete cascade,
  role text not null default 'member' check (role in ('owner','moderator','member')),
  joined_at timestamptz not null default now(),
  primary key (server_id,user_id)
);
create index if not exists server_members_user_id_idx on public.server_members(user_id);

create table if not exists public.channels (
  id uuid primary key default gen_random_uuid(),
  server_id uuid not null references public.servers(id) on delete cascade,
  name text not null,
  kind text not null default 'text' check (kind in ('text','voice')),
  position integer not null default 0 check (position >= 0),
  created_at timestamptz not null default now(),
  constraint channels_name_length_check check (char_length(trim(name)) between 1 and 80)
);
create index if not exists channels_server_id_idx on public.channels(server_id);

create table if not exists public.messages (
  id uuid primary key default gen_random_uuid(),
  channel_id uuid not null references public.channels(id) on delete cascade,
  author_id uuid not null references public.profiles(id) on delete cascade,
  body text not null check (char_length(body) between 1 and 4000),
  created_at timestamptz not null default now(),
  edited_at timestamptz,
  attachments jsonb not null default '[]'::jsonb check (jsonb_typeof(attachments)='array')
);
create index if not exists messages_channel_created_idx on public.messages(channel_id,created_at);
create index if not exists messages_author_id_idx on public.messages(author_id);

-- Social model -----------------------------------------------------------------
create table if not exists public.friend_requests (
  id uuid primary key default gen_random_uuid(),
  sender_id uuid not null references public.profiles(id) on delete cascade,
  receiver_id uuid not null references public.profiles(id) on delete cascade,
  status text not null default 'pending' check (status in ('pending','accepted','declined','cancelled')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(sender_id,receiver_id),
  check (sender_id <> receiver_id)
);
create index if not exists friend_requests_receiver_status_idx on public.friend_requests(receiver_id,status);

create table if not exists public.friendships (
  user_id uuid not null references public.profiles(id) on delete cascade,
  friend_id uuid not null references public.profiles(id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key(user_id,friend_id),
  check(user_id <> friend_id)
);
create index if not exists friendships_friend_idx on public.friendships(friend_id);

create table if not exists public.direct_messages (
  id uuid primary key default gen_random_uuid(),
  sender_id uuid not null references public.profiles(id) on delete cascade,
  receiver_id uuid not null references public.profiles(id) on delete cascade,
  body text not null check (char_length(body) between 1 and 4000),
  created_at timestamptz not null default now(),
  edited_at timestamptz,
  deleted_at timestamptz,
  attachments jsonb not null default '[]'::jsonb check (jsonb_typeof(attachments)='array'),
  check(sender_id <> receiver_id)
);
create index if not exists direct_messages_pair_created_idx on public.direct_messages(sender_id,receiver_id,created_at);
create index if not exists direct_messages_receiver_id_idx on public.direct_messages(receiver_id);

-- Invitations and notifications ------------------------------------------------
create table if not exists public.server_invites (
  id uuid primary key default gen_random_uuid(),
  server_id uuid not null references public.servers(id) on delete cascade,
  created_by uuid not null references public.profiles(id) on delete cascade,
  code text not null unique check (code ~ '^VSL-[A-Z0-9-]{4,40}$'),
  role text not null default 'member' check (role in ('moderator','member')),
  max_uses integer not null default 0 check (max_uses >= 0),
  uses integer not null default 0 check (uses >= 0),
  expires_at timestamptz,
  created_at timestamptz not null default now()
);
create index if not exists server_invites_code_idx on public.server_invites(code);
create index if not exists server_invites_created_by_idx on public.server_invites(created_by);
create index if not exists server_invites_server_id_idx on public.server_invites(server_id);

create table if not exists public.notifications (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  type text not null check (type in ('friend_request','friend_accepted','direct_message','server_invite','system')),
  title text not null,
  body text not null,
  data jsonb not null default '{}'::jsonb,
  read_at timestamptz,
  created_at timestamptz not null default now()
);
create index if not exists notifications_user_created_idx on public.notifications(user_id,created_at desc);

-- Security helper functions ----------------------------------------------------
create or replace function private.is_server_member(target_server uuid)
returns boolean
language sql
stable
security definer
set search_path='pg_catalog','public'
as $$
  select exists (
    select 1 from public.server_members sm
    where sm.server_id=target_server and sm.user_id=(select auth.uid())
  );
$$;
revoke all on function private.is_server_member(uuid) from public,anon;
grant execute on function private.is_server_member(uuid) to authenticated,service_role;

-- Profile + starter server are created only from a real Auth user.
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path='public'
as $$
declare desired_username text;
begin
  desired_username := nullif(trim(coalesce(new.raw_user_meta_data->>'username','')), '');
  if desired_username is null then
    desired_username := split_part(coalesce(new.email,'user'),'@',1);
  end if;
  insert into public.profiles(id,username,email)
  values(new.id,desired_username,coalesce(new.email,new.id::text||'@vessel.local'));
  insert into public.servers(name,icon,owner_id) values('Мой Vessel','V',new.id);
  return new;
end;
$$;
revoke all on function public.handle_new_user() from public,anon,authenticated;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created after insert on auth.users
for each row execute function public.handle_new_user();

-- Every real server receives its owner membership and starter text/voice rooms.
create or replace function public.vessel_after_server_created()
returns trigger
language plpgsql
security definer
set search_path='public'
as $$
begin
  insert into public.server_members(server_id,user_id,role)
  values(new.id,new.owner_id,'owner')
  on conflict(server_id,user_id) do update set role='owner';
  insert into public.channels(server_id,name,kind,position)
  values(new.id,'общий','text',0),(new.id,'Lounge','voice',1);
  return new;
end;
$$;
revoke all on function public.vessel_after_server_created() from public,anon,authenticated;

drop trigger if exists vessel_after_server_created_trigger on public.servers;
create trigger vessel_after_server_created_trigger after insert on public.servers
for each row execute function public.vessel_after_server_created();

create or replace function public.vessel_create_friendship_on_accept()
returns trigger
language plpgsql
security definer
set search_path='public'
as $$
begin
  if old.status is distinct from new.status and new.status='accepted' then
    insert into public.friendships(user_id,friend_id)
    values(new.sender_id,new.receiver_id),(new.receiver_id,new.sender_id)
    on conflict do nothing;
  end if;
  return new;
end;
$$;
revoke all on function public.vessel_create_friendship_on_accept() from public,anon,authenticated;

drop trigger if exists vessel_create_friendship_after_accept on public.friend_requests;
create trigger vessel_create_friendship_after_accept after update of status on public.friend_requests
for each row execute function public.vessel_create_friendship_on_accept();

create or replace function public.vessel_notify_friend_request()
returns trigger
language plpgsql
security definer
set search_path='public'
as $$
begin
  insert into public.notifications(user_id,type,title,body,data)
  values(new.receiver_id,'friend_request','Новая заявка в друзья','Кто-то хочет добавить тебя в друзья',jsonb_build_object('request_id',new.id,'sender_id',new.sender_id));
  return new;
end;
$$;
revoke all on function public.vessel_notify_friend_request() from public,anon,authenticated;

drop trigger if exists vessel_friend_request_notification on public.friend_requests;
create trigger vessel_friend_request_notification after insert on public.friend_requests
for each row execute function public.vessel_notify_friend_request();

create or replace function public.vessel_notify_direct_message()
returns trigger
language plpgsql
security definer
set search_path='public'
as $$
begin
  insert into public.notifications(user_id,type,title,body,data)
  values(new.receiver_id,'direct_message','Новое личное сообщение',left(new.body,140),jsonb_build_object('message_id',new.id,'sender_id',new.sender_id));
  return new;
end;
$$;
revoke all on function public.vessel_notify_direct_message() from public,anon,authenticated;

drop trigger if exists vessel_direct_message_notification on public.direct_messages;
create trigger vessel_direct_message_notification after insert on public.direct_messages
for each row execute function public.vessel_notify_direct_message();

-- Service-role-only RPCs used by JWT-protected Edge Functions.
create or replace function public.vessel_find_profile_exact(search_username text)
returns table(id uuid,username text,avatar_color text,status text)
language sql
stable
security definer
set search_path='pg_catalog','public'
as $$
  select p.id,p.username,p.avatar_color,p.status
  from public.profiles p
  where lower(p.username)=lower(trim(search_username))
  limit 1;
$$;
revoke all on function public.vessel_find_profile_exact(text) from public,anon,authenticated;
grant execute on function public.vessel_find_profile_exact(text) to service_role;

create or replace function public.vessel_redeem_server_invite(invite_code text,target_user uuid)
returns jsonb
language plpgsql
security definer
set search_path='pg_catalog','public'
as $$
declare
  inv public.server_invites%rowtype;
  existing boolean;
  member_role text;
begin
  select * into inv from public.server_invites
  where code=upper(trim(invite_code)) for update;
  if not found then return jsonb_build_object('ok',false,'reason','not_found'); end if;
  if inv.expires_at is not null and inv.expires_at<now() then return jsonb_build_object('ok',false,'reason','expired'); end if;
  if inv.max_uses>0 and inv.uses>=inv.max_uses then return jsonb_build_object('ok',false,'reason','used_up'); end if;
  select exists(select 1 from public.server_members sm where sm.server_id=inv.server_id and sm.user_id=target_user) into existing;
  if existing then return jsonb_build_object('ok',true,'server_id',inv.server_id,'already_member',true); end if;
  member_role := case when inv.role='moderator' then 'moderator' else 'member' end;
  insert into public.server_members(server_id,user_id,role) values(inv.server_id,target_user,member_role);
  update public.server_invites set uses=uses+1 where id=inv.id;
  return jsonb_build_object('ok',true,'server_id',inv.server_id,'already_member',false);
end;
$$;
revoke all on function public.vessel_redeem_server_invite(text,uuid) from public,anon,authenticated;
grant execute on function public.vessel_redeem_server_invite(text,uuid) to service_role;

-- RLS --------------------------------------------------------------------------
alter table public.profiles enable row level security;
alter table public.servers enable row level security;
alter table public.server_members enable row level security;
alter table public.channels enable row level security;
alter table public.messages enable row level security;
alter table public.friend_requests enable row level security;
alter table public.friendships enable row level security;
alter table public.direct_messages enable row level security;
alter table public.server_invites enable row level security;
alter table public.notifications enable row level security;

create policy "profiles visible to related users" on public.profiles for select to authenticated using (
  id=(select auth.uid())
  or exists(select 1 from public.friendships f where (f.user_id=(select auth.uid()) and f.friend_id=profiles.id) or (f.friend_id=(select auth.uid()) and f.user_id=profiles.id))
  or exists(select 1 from public.friend_requests fr where (fr.sender_id=(select auth.uid()) and fr.receiver_id=profiles.id) or (fr.receiver_id=(select auth.uid()) and fr.sender_id=profiles.id))
  or exists(select 1 from public.server_members mine join public.server_members theirs on theirs.server_id=mine.server_id where mine.user_id=(select auth.uid()) and theirs.user_id=profiles.id)
);
create policy "own profile update" on public.profiles for update to authenticated
using(id=(select auth.uid())) with check(id=(select auth.uid()));

create policy "server members can read servers" on public.servers for select to authenticated using (
  owner_id=(select auth.uid()) or exists(select 1 from public.server_members m where m.server_id=servers.id and m.user_id=(select auth.uid()))
);
create policy "users can create own servers" on public.servers for insert to authenticated with check(owner_id=(select auth.uid()));
create policy "owners can update servers" on public.servers for update to authenticated using(owner_id=(select auth.uid())) with check(owner_id=(select auth.uid()));
create policy "owners can delete servers" on public.servers for delete to authenticated using(owner_id=(select auth.uid()));

create policy "server members can read roster" on public.server_members for select to authenticated using(private.is_server_member(server_id));
create policy "owners can add members" on public.server_members for insert to authenticated with check(
  exists(select 1 from public.servers s where s.id=server_members.server_id and s.owner_id=(select auth.uid()))
);
create policy "owners can update member roles" on public.server_members for update to authenticated using(
  exists(select 1 from public.servers s where s.id=server_members.server_id and s.owner_id=(select auth.uid()) and server_members.user_id<>s.owner_id)
) with check(
  role in ('moderator','member') and exists(select 1 from public.servers s where s.id=server_members.server_id and s.owner_id=(select auth.uid()) and server_members.user_id<>s.owner_id)
);
create policy "members can leave or owners can remove" on public.server_members for delete to authenticated using(
  user_id=(select auth.uid()) or exists(select 1 from public.servers s where s.id=server_members.server_id and s.owner_id=(select auth.uid()) and server_members.user_id<>s.owner_id)
);

create policy "members can read channels" on public.channels for select to authenticated using(
  exists(select 1 from public.server_members m where m.server_id=channels.server_id and m.user_id=(select auth.uid()))
  or exists(select 1 from public.servers s where s.id=channels.server_id and s.owner_id=(select auth.uid()))
);
create policy "owners can create channels" on public.channels for insert to authenticated with check(exists(select 1 from public.servers s where s.id=channels.server_id and s.owner_id=(select auth.uid())));
create policy "owners can update channels" on public.channels for update to authenticated using(exists(select 1 from public.servers s where s.id=channels.server_id and s.owner_id=(select auth.uid()))) with check(exists(select 1 from public.servers s where s.id=channels.server_id and s.owner_id=(select auth.uid())));
create policy "owners can delete channels" on public.channels for delete to authenticated using(exists(select 1 from public.servers s where s.id=channels.server_id and s.owner_id=(select auth.uid())));

create policy "members can read channel messages" on public.messages for select to authenticated using(
  exists(select 1 from public.server_members m join public.channels c on c.server_id=m.server_id where c.id=messages.channel_id and m.user_id=(select auth.uid()))
  or exists(select 1 from public.channels c join public.servers s on s.id=c.server_id where c.id=messages.channel_id and s.owner_id=(select auth.uid()))
);
create policy "members can send channel messages" on public.messages for insert to authenticated with check(
  author_id=(select auth.uid()) and (
    exists(select 1 from public.server_members m join public.channels c on c.server_id=m.server_id where c.id=messages.channel_id and m.user_id=(select auth.uid()))
    or exists(select 1 from public.channels c join public.servers s on s.id=c.server_id where c.id=messages.channel_id and s.owner_id=(select auth.uid()))
  )
);

create policy "friend requests participants can read" on public.friend_requests for select to authenticated using(sender_id=(select auth.uid()) or receiver_id=(select auth.uid()));
create policy "users can send friend requests" on public.friend_requests for insert to authenticated with check(sender_id=(select auth.uid()) and sender_id<>receiver_id);
create policy "receivers can answer friend requests" on public.friend_requests for update to authenticated using(receiver_id=(select auth.uid())) with check(receiver_id=(select auth.uid()) and status in ('accepted','declined'));

create policy "friends can read friendships" on public.friendships for select to authenticated using(user_id=(select auth.uid()) or friend_id=(select auth.uid()));
create policy "friends can delete friendship links" on public.friendships for delete to authenticated using(user_id=(select auth.uid()) or friend_id=(select auth.uid()));

create policy "dm participants can read" on public.direct_messages for select to authenticated using(sender_id=(select auth.uid()) or receiver_id=(select auth.uid()));
create policy "friends can send dms" on public.direct_messages for insert to authenticated with check(
  sender_id=(select auth.uid()) and exists(select 1 from public.friendships f where f.user_id=(select auth.uid()) and f.friend_id=direct_messages.receiver_id)
);
create policy "senders can update dms" on public.direct_messages for update to authenticated using(sender_id=(select auth.uid())) with check(sender_id=(select auth.uid()));

create policy "owners can read own server invites" on public.server_invites for select to authenticated using(created_by=(select auth.uid()));
create policy "owners can create server invites" on public.server_invites for insert to authenticated with check(
  created_by=(select auth.uid()) and exists(select 1 from public.servers s where s.id=server_invites.server_id and s.owner_id=(select auth.uid()))
);
create policy "owners can delete server invites" on public.server_invites for delete to authenticated using(created_by=(select auth.uid()));

create policy "users can read own notifications" on public.notifications for select to authenticated using(user_id=(select auth.uid()));
create policy "users can update own notifications" on public.notifications for update to authenticated using(user_id=(select auth.uid())) with check(user_id=(select auth.uid()));

-- Context-scoped private message attachments ----------------------------------
insert into storage.buckets(id,name,public,file_size_limit)
values('vessel-files','vessel-files',false,26214400)
on conflict(id) do update set public=false,file_size_limit=26214400;

create or replace function private.can_read_vessel_file(object_name text)
returns boolean
language plpgsql
stable
security definer
set search_path='pg_catalog','public','storage'
as $$
declare
  parts text[];
  channel_uuid uuid;
  uid uuid;
begin
  uid := (select auth.uid());
  if uid is null then return false; end if;
  parts := storage.foldername(object_name);
  if coalesce(array_length(parts,1),0)<3 then return false; end if;
  if parts[1]=uid::text then return true; end if;
  if parts[2]='dm' then return parts[3]=uid::text; end if;
  if parts[2]='channel' then
    begin channel_uuid:=parts[3]::uuid; exception when others then return false; end;
    return exists(
      select 1 from public.channels c
      left join public.server_members sm on sm.server_id=c.server_id and sm.user_id=uid
      left join public.servers s on s.id=c.server_id
      where c.id=channel_uuid and (sm.user_id is not null or s.owner_id=uid)
    );
  end if;
  return false;
end;
$$;
revoke all on function private.can_read_vessel_file(text) from public,anon;
grant execute on function private.can_read_vessel_file(text) to authenticated,service_role;

create policy "vessel files read for authorized context" on storage.objects for select to authenticated
using(bucket_id='vessel-files' and private.can_read_vessel_file(name));
create policy "users upload vessel files" on storage.objects for insert to authenticated
with check(bucket_id='vessel-files' and (storage.foldername(name))[1]=(select auth.uid())::text);
create policy "users update vessel files" on storage.objects for update to authenticated
using(bucket_id='vessel-files' and owner_id=(select auth.uid())::text)
with check(bucket_id='vessel-files' and owner_id=(select auth.uid())::text);
create policy "users delete vessel files" on storage.objects for delete to authenticated
using(bucket_id='vessel-files' and owner_id=(select auth.uid())::text);

-- The JWT-protected Edge Functions `search-user` and `join-server` use the two
-- service-role-only RPCs above. Their TypeScript source is deployed in Supabase.
