drop policy if exists "senders can delete own dms" on public.direct_messages;
create policy "senders can delete own dms"
on public.direct_messages for delete to authenticated
using (sender_id = (select auth.uid()));
