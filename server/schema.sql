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
