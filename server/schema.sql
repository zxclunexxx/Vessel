-- Vessel database schema (PostgreSQL / Supabase)
create extension if not exists pgcrypto;

create table if not exists profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  username text not null unique,
  email text not null,
  avatar_color text not null default '#8b7cff',
  status text not null default 'online',
  created_at timestamptz not null default now()
);

create table if not exists servers (
  id uuid primary key default gen_random_uuid(),
  name text not null check (char_length(name) between 2 and 80),
  icon text not null default 'V',
  owner_id uuid not null references profiles(id) on delete cascade,
  created_at timestamptz not null default now()
);

create table if not exists server_members (
  server_id uuid references servers(id) on delete cascade,
  user_id uuid references profiles(id) on delete cascade,
  role text not null default 'member' check (role in ('owner','admin','member')),
  joined_at timestamptz not null default now(),
  primary key (server_id, user_id)
);

create table if not exists channels (
  id uuid primary key default gen_random_uuid(),
  server_id uuid not null references servers(id) on delete cascade,
  name text not null check (char_length(name) between 1 and 80),
  kind text not null default 'text' check (kind in ('text','voice')),
  position integer not null default 0,
  created_at timestamptz not null default now()
);

create table if not exists messages (
  id uuid primary key default gen_random_uuid(),
  channel_id uuid not null references channels(id) on delete cascade,
  author_id uuid not null references profiles(id) on delete cascade,
  body text not null check (char_length(body) between 1 and 4000),
  created_at timestamptz not null default now(),
  edited_at timestamptz
);

create index if not exists messages_channel_created_idx on messages(channel_id, created_at);
create index if not exists members_user_idx on server_members(user_id);

create or replace function public.handle_new_user()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  insert into public.profiles (id, username, email)
  values (new.id, coalesce(new.raw_user_meta_data->>'username', split_part(new.email, '@', 1)), new.email);
  insert into public.servers (name, icon, owner_id)
  values ('Мой Vessel', 'V', new.id);
  insert into public.server_members (server_id, user_id, role)
  select id, new.id, 'owner' from public.servers
  where owner_id = new.id order by created_at desc limit 1;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created after insert on auth.users
for each row execute function public.handle_new_user();

-- Create a default text channel whenever a new server is created.
create or replace function vessel_create_default_channel()
returns trigger language plpgsql as $$
begin
  insert into channels(server_id, name, kind, position) values (new.id, 'общий', 'text', 0);
  return new;
end;
$$;

drop trigger if exists create_default_channel on servers;
create trigger create_default_channel after insert on servers
for each row execute function vessel_create_default_channel();

-- Friends and direct messages.
create table if not exists public.friend_requests (
  id uuid primary key default gen_random_uuid(),
  sender_id uuid not null references public.profiles(id) on delete cascade,
  receiver_id uuid not null references public.profiles(id) on delete cascade,
  status text not null default 'pending' check (status in ('pending','accepted','declined','cancelled')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(sender_id, receiver_id),
  check (sender_id <> receiver_id)
);

create table if not exists public.friendships (
  user_id uuid not null references public.profiles(id) on delete cascade,
  friend_id uuid not null references public.profiles(id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (user_id, friend_id),
  check (user_id <> friend_id)
);

create table if not exists public.direct_messages (
  id uuid primary key default gen_random_uuid(),
  sender_id uuid not null references public.profiles(id) on delete cascade,
  receiver_id uuid not null references public.profiles(id) on delete cascade,
  body text not null check (char_length(body) between 1 and 4000),
  created_at timestamptz not null default now(),
  edited_at timestamptz,
  deleted_at timestamptz,
  check (sender_id <> receiver_id)
);

create index if not exists friend_requests_receiver_status_idx on public.friend_requests(receiver_id, status);
create index if not exists friendships_friend_idx on public.friendships(friend_id);
create index if not exists direct_messages_pair_created_idx on public.direct_messages(sender_id, receiver_id, created_at);

alter table public.friend_requests enable row level security;
alter table public.friendships enable row level security;
alter table public.direct_messages enable row level security;

drop policy if exists "friend requests participants can read" on public.friend_requests;
create policy "friend requests participants can read" on public.friend_requests for select to authenticated
using ((select auth.uid()) = sender_id or (select auth.uid()) = receiver_id);
drop policy if exists "users can send friend requests" on public.friend_requests;
create policy "users can send friend requests" on public.friend_requests for insert to authenticated
with check ((select auth.uid()) = sender_id and sender_id <> receiver_id);
drop policy if exists "request participants can update" on public.friend_requests;
create policy "request participants can update" on public.friend_requests for update to authenticated
using ((select auth.uid()) = sender_id or (select auth.uid()) = receiver_id)
with check ((select auth.uid()) = sender_id or (select auth.uid()) = receiver_id);

drop policy if exists "friends can read friendships" on public.friendships;
create policy "friends can read friendships" on public.friendships for select to authenticated
using ((select auth.uid()) = user_id or (select auth.uid()) = friend_id);
drop policy if exists "users can create friendship links" on public.friendships;
create policy "users can create friendship links" on public.friendships for insert to authenticated
with check ((select auth.uid()) = user_id or (select auth.uid()) = friend_id);
drop policy if exists "friends can delete friendship links" on public.friendships;
create policy "friends can delete friendship links" on public.friendships for delete to authenticated
using ((select auth.uid()) = user_id or (select auth.uid()) = friend_id);

drop policy if exists "dm participants can read" on public.direct_messages;
create policy "dm participants can read" on public.direct_messages for select to authenticated
using ((select auth.uid()) = sender_id or (select auth.uid()) = receiver_id);
drop policy if exists "users can send dms" on public.direct_messages;
create policy "users can send dms" on public.direct_messages for insert to authenticated
with check ((select auth.uid()) = sender_id);
drop policy if exists "senders can update dms" on public.direct_messages;
create policy "senders can update dms" on public.direct_messages for update to authenticated
using ((select auth.uid()) = sender_id)
with check ((select auth.uid()) = sender_id);

-- Server, channel and channel-message access.
alter table public.servers enable row level security;
alter table public.server_members enable row level security;
alter table public.channels enable row level security;
alter table public.messages enable row level security;

drop policy if exists "server members can read servers" on public.servers;
create policy "server members can read servers" on public.servers for select to authenticated
using (owner_id = (select auth.uid()) or exists (select 1 from public.server_members m where m.server_id = id and m.user_id = (select auth.uid())));
drop policy if exists "users can create own servers" on public.servers;
create policy "users can create own servers" on public.servers for insert to authenticated
with check (owner_id = (select auth.uid()));
drop policy if exists "owners can update servers" on public.servers;
create policy "owners can update servers" on public.servers for update to authenticated
using (owner_id = (select auth.uid())) with check (owner_id = (select auth.uid()));

drop policy if exists "members can read memberships" on public.server_members;
create policy "members can read memberships" on public.server_members for select to authenticated
using (user_id = (select auth.uid()) or exists (select 1 from public.server_members own where own.server_id = server_id and own.user_id = (select auth.uid())));
drop policy if exists "owners can add members" on public.server_members;
create policy "owners can add members" on public.server_members for insert to authenticated
with check (exists (select 1 from public.servers s where s.id = server_id and s.owner_id = (select auth.uid())) or user_id = (select auth.uid()));

drop policy if exists "members can read channels" on public.channels;
create policy "members can read channels" on public.channels for select to authenticated
using (exists (select 1 from public.server_members m where m.server_id = channels.server_id and m.user_id = (select auth.uid())) or exists (select 1 from public.servers s where s.id = channels.server_id and s.owner_id = (select auth.uid())));
drop policy if exists "owners can create channels" on public.channels;
create policy "owners can create channels" on public.channels for insert to authenticated
with check (exists (select 1 from public.servers s where s.id = server_id and s.owner_id = (select auth.uid())));

drop policy if exists "members can read channel messages" on public.messages;
create policy "members can read channel messages" on public.messages for select to authenticated
using (exists (select 1 from public.server_members m join public.channels c on c.server_id=m.server_id where c.id=channel_id and m.user_id=(select auth.uid())) or exists (select 1 from public.channels c join public.servers s on s.id=c.server_id where c.id=channel_id and s.owner_id=(select auth.uid())));
drop policy if exists "members can send channel messages" on public.messages;
create policy "members can send channel messages" on public.messages for insert to authenticated
with check ((select auth.uid()) = author_id and (exists (select 1 from public.server_members m join public.channels c on c.server_id=m.server_id where c.id=channel_id and m.user_id=(select auth.uid())) or exists (select 1 from public.channels c join public.servers s on s.id=c.server_id where c.id=channel_id and s.owner_id=(select auth.uid()))));
