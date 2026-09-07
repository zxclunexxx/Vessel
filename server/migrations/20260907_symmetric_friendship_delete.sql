-- Keep friendships symmetric even if a client deletes only one directional row.
create or replace function public.vessel_delete_reverse_friendship()
returns trigger
language plpgsql
security definer
set search_path='public'
as $$
begin
  delete from public.friendships
  where user_id = old.friend_id
    and friend_id = old.user_id;
  return old;
end;
$$;
revoke all on function public.vessel_delete_reverse_friendship() from public,anon,authenticated;

drop trigger if exists vessel_delete_reverse_friendship_after_delete on public.friendships;
create trigger vessel_delete_reverse_friendship_after_delete
after delete on public.friendships
for each row execute function public.vessel_delete_reverse_friendship();
