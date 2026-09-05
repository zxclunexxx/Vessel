from pathlib import Path

main = Path('src/main.js').read_text(encoding='utf-8')

banned = [
    "Марк",
    "Лиза",
    "defaultMessages",
    "name: 'Игры'",
    "name: 'Музыка'",
    "demo@vessel.app",
    "prompt(",
    "confirm(",
    "alert(",
    "`${user.id}/${crypto.randomUUID()}-${safeName}`",
    "savedChannelMap",
    "activeDmId=isDm?null:activeDmId",
    "localStorage.getItem('vesselActiveServer')",
    "localStorage.setItem('vesselActiveServer',",
    "savedUser || JSON.parse(localStorage.getItem('vesselUser')",
    "const selected=servers[activeServerIndex];",
]
found = [item for item in banned if item in main]
if found:
    raise SystemExit(f'Authenticated runtime contains banned prototype/stale state behavior: {found}')

required = [
    'async function bootstrapAuth()',
    'async function syncSocial(user)',
    'async function loadDirectMessages(user, friendId)',
    'async function toggleVoiceRoom(user)',
    'async function endCall(notify=true)',
    "supabase.functions.invoke('search-user'",
    "supabase.functions.invoke('join-server'",
    'function vesselDialog(',
    'function vesselListDialog(',
    'function vesselCodeDialog(',
    'function escapeHtml(',
    'function getActiveServer()',
    'function setActiveServer(serverOrId)',
    "localStorage.getItem('vesselActiveServerId')",
    'callInviteTimer',
    'vessel-memberships-',
    'vessel-channels-',
    'vessel-channel-messages-',
    'vessel-friend-requests-out-',
    'data-remove-friend',
    'data-accept-request',
    'data-decline-request',
    'data-cancel-request',
    'id="mobile-nav"',
    "createSignedUrl(path,60)",
    "activeChannelName = 'нет каналов'",
    "context=`dm/${activeDmId}`",
    "context=`channel/${activeChannelId}`",
    'async function cleanupFailedAttachment(attachment)',
    '25*1024*1024',
    "document.querySelectorAll('.channel:not(.dm)')",
    "document.querySelector('#end-call')?.addEventListener('click',()=>endCall(true));",
    'const openFriendsHome=()=>{friendsOpen=true;currentDm=null;activeDmId=null;',
    "if(callConnection||callStream||incomingCall){vesselNotice('Заверши личный звонок",
    'VOICE_REALTIME_TIMEOUT',
    "activeChannelKind!=='text'",
    'maxlength="32"',
    'const selected=getActiveServer();',
]
for item in required:
    if item not in main:
        raise SystemExit(f'Missing expected runtime feature: {item}')

# Keep the authenticated UI backed by database identities, not fake fallback people.
if "savedUser = JSON.parse(localStorage.getItem('vesselUser')" in main:
    raise SystemExit('Runtime must not trust a cached localStorage user as an authenticated session')

# Channel and DM state are mutually exclusive. The channel click handler must clear the DM id
# before changing activeChannelId, otherwise channel messages can be sent to an old DM.
channel_handler_start = main.find("document.querySelectorAll('.channel:not(.dm)')")
if channel_handler_start < 0:
    raise SystemExit('Missing server-channel click handler')
channel_handler = main[channel_handler_start:channel_handler_start + 1600]
if 'activeDmId=null;' not in channel_handler or 'activeChannelId=channelId;' not in channel_handler:
    raise SystemExit('Channel handler does not isolate DM/channel state')
if channel_handler.find('activeDmId=null;') > channel_handler.find('activeChannelId=channelId;'):
    raise SystemExit('Channel handler must clear DM state before selecting a channel')

# Stable database ids, not array positions, must be the persisted server identity.
if "let activeServerId = localStorage.getItem('vesselActiveServerId')" not in main:
    raise SystemExit('Active server must be persisted by stable database id')

# The Friends home state must not keep a stale direct-message id alive.
friends_start=main.find('const openFriendsHome=')
if friends_start < 0 or 'activeDmId=null;' not in main[friends_start:friends_start+300]:
    raise SystemExit('Friends home must clear active DM state')

# Voice and direct calls share microphone resources and must be mutually exclusive.
voice_start=main.find('async function toggleVoiceRoom(user)')
voice_block=main[voice_start:voice_start+3500]
if "callConnection||callStream||incomingCall" not in voice_block:
    raise SystemExit('Voice room entry must refuse while a direct call is active or incoming')
if "['CHANNEL_ERROR','TIMED_OUT','CLOSED']" not in voice_block:
    raise SystemExit('Voice room must clean up failed Realtime subscriptions')

print('Vessel authenticated runtime smoke check passed')
