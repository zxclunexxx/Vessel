from pathlib import Path

main = Path('src/main.js').read_text(encoding='utf-8')
schema = Path('server/schema.sql').read_text(encoding='utf-8')

required_main = [
    'let dmMessagesSyncRevision = 0;',
    'const revision=++dmMessagesSyncRevision;',
    'revision!==dmMessagesSyncRevision',
    "if(error){window.__vesselDmLoaded=false;vesselNotice('Не удалось загрузить личные сообщения.','error');return;}",
    'let dataRealtimeReconnectTimer = null;',
    'let dataRealtimeRecoveryInFlight = false;',
    'function handleDataRealtimeStatus(user,status)',
    "if(['CHANNEL_ERROR','TIMED_OUT','CLOSED'].includes(status))scheduleDataRealtimeRecovery(user,status);",
    'function scheduleDataRealtimeRecovery(user,status=',
    'window.__vesselRealtimeChannels=null;',
    'await Promise.allSettled(stale.map(channel=>supabase.removeChannel(channel)))',
    'connectSupabaseRealtime(user);',
    'clearDataRealtimeRecovery();',
    "select('id,status').maybeSingle()",
    ".eq('receiver_id',user.id).eq('status','pending').select('id,status').maybeSingle()",
    ".eq('status','pending').select('id')",
    ".select('user_id,friend_id')",
]
for marker in required_main:
    if marker not in main:
        raise SystemExit(f'Missing social/realtime resilience marker: {marker}')

connect_start = main.find('function connectSupabaseRealtime(user) {')
connect_end = main.find('\n\nlet savedUser = null;', connect_start)
if connect_start < 0 or connect_end < 0:
    raise SystemExit('Data Realtime connect block not found')
connect_block = main[connect_start:connect_end]
monitored = '.subscribe(status=>handleDataRealtimeStatus(user,status))'
if connect_block.count(monitored) != 10:
    raise SystemExit(f'Expected 10 monitored data Realtime subscriptions, found {connect_block.count(monitored)}')
if '.subscribe()' in connect_block:
    raise SystemExit('Unmonitored data Realtime subscription remains')

reset_start = main.find('function resetAuthenticatedRuntime() {')
reset_end = main.find('\n}\n\nasync function cleanupAuthenticatedChannels', reset_start)
reset_block = main[reset_start:reset_end]
for marker in ('clearDataRealtimeRecovery();', 'dmMessagesSyncRevision++;', 'window.__vesselRealtimeChannels=null;'):
    if marker not in reset_block:
        raise SystemExit(f'Authenticated reset is missing {marker}')

accept_start = main.find("document.querySelectorAll('[data-accept-request]')")
decline_start = main.find("document.querySelectorAll('[data-decline-request]')")
if accept_start < 0 or decline_start < 0:
    raise SystemExit('Friend request action handlers not found')
accept_block = main[accept_start:decline_start]
if ".eq('status','pending')" not in accept_block or 'if(!accepted)' not in accept_block:
    raise SystemExit('Accept friend-request path can still report stale zero-row success')
decline_block = main[decline_start:decline_start + 1200]
if ".eq('status','pending')" not in decline_block or 'if(!declined)' not in decline_block:
    raise SystemExit('Decline friend-request path can still report stale zero-row success')

required_schema = [
    'create or replace function public.vessel_dm_threads()',
    'returns table(peer_id uuid,username text,avatar_color text,status text,last_message_at timestamptz)',
    'security invoker',
    "set search_path='pg_catalog','public'",
    'dm.deleted_at is null',
    'revoke all on function public.vessel_dm_threads() from public,anon;',
    'grant execute on function public.vessel_dm_threads() to authenticated;',
]
for marker in required_schema:
    if marker not in schema:
        raise SystemExit(f'Missing secure DM-thread bootstrap marker: {marker}')

if 'security definer' in schema[schema.find('create or replace function public.vessel_dm_threads()'):schema.find('-- Service-role-only RPCs', schema.find('create or replace function public.vessel_dm_threads()'))]:
    raise SystemExit('vessel_dm_threads bootstrap RPC must not bypass RLS')

print('Vessel social/DM/data-Realtime resilience smoke check passed')
