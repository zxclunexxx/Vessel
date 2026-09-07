-- Registration should create only the real user profile. Servers are explicit user actions.
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path to 'public'
as $function$
declare
  desired_username text;
begin
  desired_username := nullif(trim(coalesce(new.raw_user_meta_data->>'username','')), '');
  if desired_username is null then
    desired_username := split_part(coalesce(new.email, 'user'), '@', 1);
  end if;

  insert into public.profiles (id, username, email)
  values (new.id, desired_username, coalesce(new.email, new.id::text || '@vessel.local'));

  return new;
end;
$function$;

-- Remove only untouched legacy bootstrap servers. Used/user-created servers are preserved.
delete from public.servers s
where s.name = 'Мой Vessel'
  and exists (
    select 1 from public.server_members sm
    where sm.server_id=s.id and sm.user_id=s.owner_id and sm.role='owner'
  )
  and 1 = (select count(*) from public.server_members sm where sm.server_id=s.id)
  and 2 = (select count(*) from public.channels c where c.server_id=s.id)
  and exists (select 1 from public.channels c where c.server_id=s.id and c.name='общий' and c.kind='text')
  and exists (select 1 from public.channels c where c.server_id=s.id and c.name='Lounge' and c.kind='voice')
  and not exists (
    select 1 from public.messages m
    join public.channels c on c.id=m.channel_id
    where c.server_id=s.id
  );
