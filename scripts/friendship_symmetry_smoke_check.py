from pathlib import Path

schema = Path('server/schema.sql').read_text(encoding='utf-8')
migration = Path('server/migrations/20260907_symmetric_friendship_delete.sql').read_text(encoding='utf-8')
main = Path('src/main.js').read_text(encoding='utf-8')

required = [
    'create or replace function public.vessel_delete_reverse_friendship()',
    'security definer',
    "set search_path='public'",
    'delete from public.friendships',
    'user_id=old.friend_id and friend_id=old.user_id',
    'revoke all on function public.vessel_delete_reverse_friendship() from public,anon,authenticated;',
    'create trigger vessel_delete_reverse_friendship_after_delete after delete on public.friendships',
]
for marker in required:
    if marker not in schema:
        raise SystemExit(f'Bootstrap symmetric friendship delete guard missing: {marker}')

migration_required = [
    'create or replace function public.vessel_delete_reverse_friendship()',
    'where user_id = old.friend_id',
    'and friend_id = old.user_id;',
    'after delete on public.friendships',
]
for marker in migration_required:
    if marker not in migration:
        raise SystemExit(f'Symmetric friendship delete migration missing: {marker}')

client_marker = "supabase.from('friendships').delete().or(`and(user_id.eq.${user.id},friend_id.eq.${friendId}),and(user_id.eq.${friendId},friend_id.eq.${user.id})`)"
if client_marker not in main:
    raise SystemExit('Client no longer requests both friendship directions on explicit unfriend')

print('Vessel symmetric friendship delete smoke check passed')
