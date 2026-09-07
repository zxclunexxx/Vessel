-- Invite consumption is performed by the authenticated join-server Edge Function via service role.
-- Browser clients create/read/delete their own invites through RLS and do not need UPDATE.
revoke update on table public.server_invites from authenticated;
revoke all privileges on table public.server_invites from anon;
