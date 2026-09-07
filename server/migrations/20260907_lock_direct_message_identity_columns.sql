-- A direct message may be edited by its sender, but its identity/routing fields
-- must never be mutable from the browser. Otherwise an existing authored row
-- could be retargeted to another receiver and bypass the friends-only INSERT RLS.
revoke update on table public.direct_messages from authenticated;
grant update (body, attachments, edited_at, deleted_at) on table public.direct_messages to authenticated;
