-- Vessel's messaging and friendship runtime requires an authenticated session.
-- Anonymous Data API access is unnecessary; RLS remains enabled as defense in depth.
revoke all privileges on table public.direct_messages from anon;
revoke all privileges on table public.friendships from anon;
revoke all privileges on table public.messages from anon;
