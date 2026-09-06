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
    "if(voiceStream && voiceChannelId!==activeChannelId){await leaveVoiceRoom();}",
]
found = [item for item in banned if item in main]
if found:
    raise SystemExit(f'Authenticated runtime contains banned prototype/stale state behavior: {found}')

required = [
    'async function bootstrapAuth()',
    'async function syncSocial(user)',
    'async function loadDirectMessages(user, friendId)',
    'async function toggleVoiceRoom(user,reconnecting=false)',
    'function scheduleVoiceReconnect(user,channelId,serverId)',
    'function cancelVoiceReconnect()',
    'async function endCall(notify=true)',
    'function subscribeChannel(channel,onDisconnect=null)',
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
    'scheduleVoiceReconnect(user,failedChannelId,failedServerId);',
    "vesselNotice('Голосовая связь восстановлена.','success');",
    'Call inbox ${status}; reconnecting',
    'Call signaling ${status}; reconnecting',
    'Call inbox reconnect failed',
    'Call signaling reconnect failed',
    "activeChannelKind!=='text'",
    'maxlength="32"',
    'const selected=getActiveServer();',
    "if(activeDmId||activeChannelId!==channelId||activeChannelKind!=='text')return;",
    'if(activeDmId!==friendId)return;',
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
voice_start=main.find('async function toggleVoiceRoom(user,reconnecting=false)')
if voice_start < 0:
    raise SystemExit('Missing reconnect-aware voice room entry point')
voice_block=main[voice_start:voice_start+5200]
if "callConnection||callStream||incomingCall" not in voice_block:
    raise SystemExit('Voice room entry must refuse while a direct call is active or incoming')
if "['CHANNEL_ERROR','TIMED_OUT','CLOSED']" not in voice_block:
    raise SystemExit('Voice room must handle failed Realtime subscriptions')
if 'scheduleVoiceReconnect(user,failedChannelId,failedServerId);' not in voice_block:
    raise SystemExit('Voice room must schedule recovery after an established Realtime channel fails')
if 'voiceStream?.getTracks().forEach(track=>track.stop());voiceStream=null;' not in voice_block:
    raise SystemExit('Voice room recovery must release the failed microphone stream before reconnecting')

# Established call inbox/signaling channels must recover after Realtime churn without
# requiring a page reload or tearing down a healthy WebRTC media connection.
subscribe_start=main.find('function subscribeChannel(channel,onDisconnect=null)')
if subscribe_start < 0:
    raise SystemExit('Missing established Realtime disconnect callback')
subscribe_block=main[subscribe_start:subscribe_start+2200]
for marker in ['everSubscribed', 'disconnectNotified', "typeof onDisconnect === 'function'"]:
    if marker not in subscribe_block:
        raise SystemExit(f'Realtime subscription helper missing disconnect recovery marker: {marker}')

inbox_start=main.find('async function ensureCallInbox(user)')
channel_start=main.find('async function ensureCallChannel(user, peerId)')
if inbox_start < 0 or channel_start < 0:
    raise SystemExit('Missing call Realtime channel setup')
inbox_block=main[inbox_start:channel_start]
call_block=main[channel_start:channel_start+3200]
if 'ensureCallInbox(savedUser)' not in inbox_block or 'Call inbox reconnect failed' not in inbox_block:
    raise SystemExit('Call inbox must resubscribe after an established Realtime disconnect')
if 'ensureCallChannel(savedUser,peerId)' not in call_block or 'Call signaling reconnect failed' not in call_block:
    raise SystemExit('Active call signaling must resubscribe after an established Realtime disconnect')
if 'callConnection&&!callChannel' not in call_block:
    raise SystemExit('Call signaling reconnect must be scoped to an active WebRTC call')

# Slow responses from a previously selected channel/DM must never overwrite the conversation
# currently on screen. These guards execute immediately after each async message query returns.
channel_load_start=main.find('async function loadChannelMessages(channelId)')
dm_load_start=main.find('async function loadDirectMessages(user, friendId)')
if channel_load_start < 0 or dm_load_start < 0:
    raise SystemExit('Missing message loaders')
channel_load=main[channel_load_start:channel_load_start+1200]
dm_load=main[dm_load_start:dm_load_start+1600]
if "if(activeDmId||activeChannelId!==channelId||activeChannelKind!=='text')return;" not in channel_load:
    raise SystemExit('Channel message loader must discard stale async responses')
if 'if(activeDmId!==friendId)return;' not in dm_load:
    raise SystemExit('Direct-message loader must discard stale async responses')

print('Vessel authenticated runtime smoke check passed')
