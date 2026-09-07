from pathlib import Path

# Legacy baseline verifier.
# The original autonomous patch grew into a sequence of exact text replacements and became
# fragile once newer reliability/session/lifecycle patches legitimately changed the same code.
# All of those baseline changes are already committed in main; keep this script idempotent and
# fail only if a required capability actually disappears.
main = Path('src/main.js').read_text(encoding='utf-8')
schema = Path('server/schema.sql').read_text(encoding='utf-8')

main_markers = [
    "supabase.rpc('vessel_dm_threads')",
    'let dmThreads = [];',
    'const dmList=dmThreads.length',
    'activeDmIsFriend',
    'История доступна только для чтения.',
    'vessel-profiles-${user.id}',
    'vessel-servers-${user.id}',
    ".select('username,status,avatar_color').single()",
    "sendError.code==='23505'",
]

schema_markers = [
    'friend_requests_pending_pair_uidx',
    'create or replace function public.vessel_dm_threads()',
]

missing = [marker for marker in main_markers if marker not in main]
missing += [marker for marker in schema_markers if marker not in schema]
if missing:
    raise SystemExit('Vessel baseline marker missing: ' + ', '.join(missing))

rpc_start = schema.find('create or replace function public.vessel_dm_threads()')
rpc_grant = 'grant execute on function public.vessel_dm_threads() to authenticated;'
rpc_end = schema.find(rpc_grant, rpc_start)
if rpc_start < 0 or rpc_end < 0:
    raise SystemExit('Vessel DM-thread RPC security block is incomplete')
rpc_block = schema[rpc_start:rpc_end + len(rpc_grant)]
rpc_lower = rpc_block.lower()
if 'security invoker' not in rpc_lower or 'security definer' in rpc_lower:
    raise SystemExit('Vessel DM-thread RPC must remain SECURITY INVOKER')
combined_revoke = 'revoke all on function public.vessel_dm_threads() from public,anon;'
split_revoke = 'revoke all on function public.vessel_dm_threads() from public;\nrevoke execute on function public.vessel_dm_threads() from anon;'
if combined_revoke not in rpc_block and split_revoke not in rpc_block:
    raise SystemExit('Vessel DM-thread RPC must revoke anonymous/public execution')

print('Vessel baseline already applied; nothing to change')
