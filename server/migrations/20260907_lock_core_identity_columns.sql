-- Keep row identity and ownership fields immutable from browser clients.
-- RLS still decides which rows can be updated; these grants constrain which columns can change.

revoke update on table public.servers from authenticated;
grant update (name, icon) on table public.servers to authenticated;

revoke update on table public.channels from authenticated;
grant update (name, kind, position) on table public.channels to authenticated;

revoke update on table public.server_members from authenticated;
grant update (role) on table public.server_members to authenticated;

revoke update on table public.notifications from authenticated;
grant update (read_at) on table public.notifications to authenticated;

revoke all privileges on table public.servers from anon;
revoke all privileges on table public.channels from anon;
revoke all privileges on table public.server_members from anon;
revoke all privileges on table public.notifications from anon;
