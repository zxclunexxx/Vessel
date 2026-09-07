from pathlib import Path

schema_path = Path('server/schema.sql')
schema = schema_path.read_text(encoding='utf-8')

marker = '-- Friend-request routing/identity is immutable from the browser.'
block = '''-- Friend-request routing/identity is immutable from the browser.
-- Participants may transition status and refresh updated_at, but cannot retarget an existing request.
revoke update on table public.friend_requests from anon, authenticated;
grant update (status, updated_at) on table public.friend_requests to authenticated;

'''
anchor = 'create policy "friends can read friendships" on public.friendships'

if marker not in schema:
    if anchor not in schema:
        raise SystemExit('Friendship policy anchor missing from server/schema.sql')
    schema = schema.replace(anchor, block + anchor, 1)
    schema_path.write_text(schema, encoding='utf-8')
    print('Added friend-request immutable routing grants to bootstrap schema')
else:
    required = [
        'revoke update on table public.friend_requests from anon, authenticated;',
        'grant update (status, updated_at) on table public.friend_requests to authenticated;',
    ]
    missing = [item for item in required if item not in schema]
    if missing:
        raise SystemExit(f'Friend-request identity marker exists but grants are incomplete: {missing}')
    print('Friend-request immutable routing grants already present')
