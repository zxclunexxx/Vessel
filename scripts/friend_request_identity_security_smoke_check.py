from pathlib import Path

schema = Path('server/schema.sql').read_text(encoding='utf-8')
migration = Path('server/migrations/20260907_lock_friend_request_identity_columns.sql').read_text(encoding='utf-8')
main = Path('src/main.js').read_text(encoding='utf-8')

required_sql = [
    'revoke update on table public.friend_requests from anon, authenticated;',
    'grant update (status, updated_at) on table public.friend_requests to authenticated;',
]
for marker in required_sql:
    if marker not in schema:
        raise SystemExit(f'Bootstrap friend-request identity grant missing: {marker}')
    if marker not in migration:
        raise SystemExit(f'Friend-request identity migration missing: {marker}')

for forbidden in [
    "update({sender_id:",
    "update({receiver_id:",
    "update({sender_id :",
    "update({receiver_id :",
]:
    if forbidden in main:
        raise SystemExit(f'Client attempts to mutate immutable friend-request identity: {forbidden}')

required_client = [
    "update({status:'pending',updated_at:new Date().toISOString()})",
    "update({status:'accepted',updated_at:new Date().toISOString()})",
    "update({status:'declined',updated_at:new Date().toISOString()})",
]
for marker in required_client:
    if marker not in main:
        raise SystemExit(f'Expected safe friend-request transition missing: {marker}')

print('Vessel friend-request identity privilege smoke check passed')
