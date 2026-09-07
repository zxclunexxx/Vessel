-- Keep friend-request routing immutable from browser clients.
-- Participants may transition status and refresh updated_at, but cannot retarget an existing request.
revoke update on table public.friend_requests from anon, authenticated;
grant update (status, updated_at) on table public.friend_requests to authenticated;
