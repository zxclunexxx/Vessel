from pathlib import Path

schema_path = Path('server/schema.sql')
schema = schema_path.read_text(encoding='utf-8')

policy = 'create policy "senders can update dms" on public.direct_messages for update to authenticated using(sender_id=(select auth.uid())) with check(sender_id=(select auth.uid()));'
hardening = '''-- Direct-message routing/identity is immutable from the browser.\n-- Senders may edit content or soft-delete their own messages, but cannot retarget an existing row.\nrevoke update on table public.direct_messages from authenticated;\ngrant update (body, attachments, edited_at, deleted_at) on table public.direct_messages to authenticated;'''

if hardening in schema:
    print('DM identity column hardening already applied; nothing to change')
elif policy in schema:
    schema = schema.replace(policy, policy + '\n\n' + hardening, 1)
    schema_path.write_text(schema, encoding='utf-8')
    print('Applied DM identity column hardening to schema snapshot')
else:
    raise SystemExit('DM update policy marker not found; refusing to patch unknown schema state')

schema = schema_path.read_text(encoding='utf-8')
required = [
    'revoke update on table public.direct_messages from authenticated;',
    'grant update (body, attachments, edited_at, deleted_at) on table public.direct_messages to authenticated;',
]
for marker in required:
    if marker not in schema:
        raise SystemExit(f'missing DM identity hardening marker: {marker}')
