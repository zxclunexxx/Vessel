from pathlib import Path

schema = Path('server/schema.sql').read_text(encoding='utf-8')
migration = Path('server/migrations/20260907_protect_server_owner_membership.sql').read_text(encoding='utf-8')

required = [
    'user_id=(select auth.uid())',
    'and not exists(',
    'where s.id=server_members.server_id and s.owner_id=(select auth.uid())',
    'and server_members.user_id<>s.owner_id',
]
for marker in required:
    if marker not in schema:
        raise SystemExit(f'Bootstrap server-owner membership guard missing: {marker}')

migration_required = [
    'drop policy if exists "members can leave or owners can remove" on public.server_members;',
    'user_id = (select auth.uid())',
    'and not exists (',
    'and server_members.user_id <> s.owner_id',
]
for marker in migration_required:
    if marker not in migration:
        raise SystemExit(f'Server-owner membership migration guard missing: {marker}')

legacy = 'user_id=(select auth.uid()) or exists(select 1 from public.servers s where s.id=server_members.server_id and s.owner_id=(select auth.uid()) and server_members.user_id<>s.owner_id)'
if legacy in schema:
    raise SystemExit('Legacy policy still lets an owner delete their own membership row')

print('Vessel server owner membership invariant smoke check passed')
