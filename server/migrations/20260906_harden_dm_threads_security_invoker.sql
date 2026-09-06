-- Keep direct-message thread discovery behind normal caller permissions and RLS.
-- Production migration applied on 2026-09-06.
alter function public.vessel_dm_threads() security invoker;
revoke execute on function public.vessel_dm_threads() from public, anon;
grant execute on function public.vessel_dm_threads() to authenticated;
