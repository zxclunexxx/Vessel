-- DM thread discovery intentionally remains a narrow SECURITY DEFINER RPC.
-- It returns only peer id/username/avatar/status/last-message time for conversations
-- involving auth.uid(), so old read-only DM threads remain discoverable without
-- broadening profiles RLS (profiles also contains email).
alter function public.vessel_dm_threads() security definer;
revoke execute on function public.vessel_dm_threads() from public, anon;
grant execute on function public.vessel_dm_threads() to authenticated;
