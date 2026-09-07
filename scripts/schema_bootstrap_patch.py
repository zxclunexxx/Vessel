from pathlib import Path

path = Path('server/schema.sql')
text = path.read_text(encoding='utf-8')
changed = False

old_header = '-- Updated 2026-09-05 to match the secured production schema.'
new_header = '-- Updated 2026-09-07 to match the secured production schema.'
if old_header in text:
    text = text.replace(old_header, new_header, 1)
    changed = True

old_block = '''-- Profile + starter server are created only from a real Auth user.
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
$$;'''
new_block = '''-- Profile is created from a real Auth user; servers are explicit user actions.
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
  return new;
end;
$$;'''
if new_block not in text:
    if old_block not in text:
        raise SystemExit('fresh bootstrap handle_new_user anchor not found')
    text = text.replace(old_block, new_block, 1)
    changed = True

start = text.find('create or replace function public.handle_new_user()')
end = text.find('-- Every real server receives its owner membership', start)
if start < 0 or end < 0:
    raise SystemExit('handle_new_user validation range not found')
block = text[start:end]
if 'insert into public.profiles' not in block:
    raise SystemExit('profile bootstrap missing after patch')
if 'insert into public.servers' in block:
    raise SystemExit('implicit starter server still present after patch')
if 'Profile is created from a real Auth user; servers are explicit user actions.' not in text:
    raise SystemExit('bootstrap contract marker missing after patch')

if changed:
    path.write_text(text, encoding='utf-8')
    print('Aligned fresh bootstrap server lifecycle with production')
else:
    print('Fresh bootstrap server lifecycle already aligned with production')
