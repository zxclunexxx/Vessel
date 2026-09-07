from pathlib import Path

schema = Path('server/schema.sql').read_text(encoding='utf-8')
migration = Path('server/migrations/20260907_lock_direct_message_identity_columns.sql').read_text(encoding='utf-8')

required = [
    'revoke update on table public.direct_messages from authenticated;',
    'grant update (body, attachments, edited_at, deleted_at) on table public.direct_messages to authenticated;',
]

for marker in required:
    if marker not in schema:
        raise SystemExit(f'schema snapshot missing DM identity hardening: {marker}')
    if marker not in migration:
        raise SystemExit(f'migration missing DM identity hardening: {marker}')

grant_line = next((line.strip() for line in schema.splitlines() if line.strip().startswith('grant update (') and 'public.direct_messages' in line), '')
for forbidden in ('id', 'sender_id', 'receiver_id', 'created_at'):
    if forbidden in grant_line.replace('edited_at', '').replace('deleted_at', ''):
        raise SystemExit(f'DM identity column unexpectedly updateable: {forbidden}')

print('DM identity update privileges are restricted to mutable content fields')
