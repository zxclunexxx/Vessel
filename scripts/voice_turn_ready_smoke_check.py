from pathlib import Path

main = Path('src/main.js').read_text(encoding='utf-8')
server_fn = Path('server/functions/rtc-config/index.ts')
deploy_fn = Path('supabase/functions/rtc-config/index.ts')

for path in [server_fn, deploy_fn]:
    if not path.exists():
        raise SystemExit(f'Missing RTC config Edge Function source: {path}')

server_text = server_fn.read_text(encoding='utf-8')
deploy_text = deploy_fn.read_text(encoding='utf-8')
if server_text != deploy_text:
    raise SystemExit('Versioned and deployable rtc-config Edge Function sources diverged')

function_required = [
    "req.headers.get('Authorization')",
    'userClient.auth.getUser()',
    "Deno.env.get('TURN_URLS')",
    "Deno.env.get('TURN_SHARED_SECRET')",
    "Deno.env.get('TURN_TTL_SECONDS')",
    "{ name: 'HMAC', hash: 'SHA-1' }",
    "const username = `${expirySeconds}:${user.id}`;",
    'relay_enabled: relayEnabled',
    "'Cache-Control': 'no-store'",
]
missing_fn = [marker for marker in function_required if marker not in server_text]
if missing_fn:
    raise SystemExit('rtc-config missing auth/TURN markers: ' + ', '.join(missing_fn))
if 'SUPABASE_SERVICE_ROLE_KEY' in server_text:
    raise SystemExit('rtc-config must not use service-role credentials')
if 'TURN_SHARED_SECRET =' in server_text:
    raise SystemExit('TURN shared secret must come from Edge Function secrets, not source code')

main_required = [
    'const RTC_FALLBACK_ICE_SERVERS = [',
    "supabase.functions.invoke('rtc-config')",
    'function normaliseRtcIceServers(rows)',
    'async function resolveRtcConfiguration(user,{force=false}={})',
    'async function attemptVoicePeerIceRestart(user,peerId,state)',
    'pc.createOffer({iceRestart:true})',
    'pc.setConfiguration?.(rtcConfiguration);',
    'async function prepareCallConnection(user,peerId,video)',
    'connection.setConfiguration?.(rtcConfiguration);',
    'function scheduleCallInboxReconnect(user,immediate=false)',
    'function scheduleCallSignalReconnect(user,peerId,immediate=false)',
    "window.addEventListener('online'",
    'cancelVoiceReconnect();',
    'cancelAllVoicePeerReconnects();',
    'cancelCallInboxReconnect();',
    'cancelCallSignalReconnect();',
    'resetRtcConfiguration();',
]
missing_main = [marker for marker in main_required if marker not in main]
if missing_main:
    raise SystemExit('Missing TURN-ready runtime markers: ' + ', '.join(missing_main))

if main.count('new RTCPeerConnection(rtcConfiguration)') != 2:
    raise SystemExit('Voice and direct calls must both consume resolved RTC configuration')
if "new RTCPeerConnection({iceServers:[{urls:'stun:stun.l.google.com:19302'}]})" in main:
    raise SystemExit('STUN-only peer construction remains in runtime')
if 'TURN_SHARED_SECRET' in main or 'TURN_TTL_SECONDS' in main:
    raise SystemExit('TURN server secrets/configuration must not be embedded in the browser runtime')
if main.count("resolveRtcConfiguration(user,{force:true})") < 2:
    raise SystemExit('Both voice and call ICE restart paths must refresh ephemeral TURN configuration')

print('Voice/calls reconnect and TURN-ready smoke check passed')
