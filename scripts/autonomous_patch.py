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
    'revoke execute on function public.vessel_dm_threads() from anon;',
]

missing = [marker for marker in main_markers if marker not in main]
missing += [marker for marker in schema_markers if marker not in schema]
if missing:
    raise SystemExit('Vessel baseline marker missing: ' + ', '.join(missing))

print('Vessel baseline already applied; nothing to change')
