from pathlib import Path

main = Path('src/main.js').read_text(encoding='utf-8')

message_start = main.find('async function loadChannelMessages(channelId)')
if message_start < 0:
    raise SystemExit('Channel message loader is missing')
message_block = main[message_start:message_start + 1800]
for marker in [
    'const sessionUserId=savedUser?.id||null;',
    'if(!sessionUserId)return;',
    "if(savedUser?.id!==sessionUserId||activeDmId||activeChannelId!==channelId||activeChannelKind!=='text')return;",
]:
    if marker not in message_block:
        raise SystemExit(f'Channel message auth/session guard missing: {marker}')

channel_start = main.find('async function syncSupabaseChannels(server)')
if channel_start < 0:
    raise SystemExit('Channel list sync is missing')
channel_block = main[channel_start:channel_start + 3000]
for marker in [
    'const sessionUserId=savedUser?.id||null;',
    'const serverId=server.dbId;',
    'const activeServer=getActiveServer();',
    'const serverStillActive=Boolean(savedUser?.id===sessionUserId&&server===activeServer&&serverId===activeServer?.dbId);',
    'if(savedUser?.id!==sessionUserId||!servers.includes(server))return;',
]:
    if marker not in channel_block:
        raise SystemExit(f'Channel list auth/session guard missing: {marker}')

print('Vessel server/channel async context smoke check passed')
