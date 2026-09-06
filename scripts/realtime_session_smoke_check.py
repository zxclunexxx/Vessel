from pathlib import Path

main = Path('src/main.js').read_text(encoding='utf-8')

checks = [
    ("vessel-dm-${user.id}", "if(savedUser?.id!==user.id)return;"),
    ("vessel-friends-${user.id}", "if(savedUser?.id!==user.id)return;"),
    ("vessel-friend-requests-out-${user.id}", "if(savedUser?.id!==user.id)return;"),
    ("vessel-friendships-${user.id}", "if(savedUser?.id!==user.id)return;"),
    ("vessel-memberships-${user.id}", "if(savedUser?.id!==user.id)return;"),
    ("vessel-channels-${user.id}", "if(savedUser?.id!==user.id)return;"),
    ("vessel-channel-messages-${user.id}", "if(savedUser?.id!==user.id)return;"),
    ("vessel-profiles-${user.id}", "if(savedUser?.id!==user.id)return;"),
    ("vessel-servers-${user.id}", "if(savedUser?.id!==user.id)return;"),
]

for channel, guard in checks:
    start = main.find(channel)
    if start < 0:
        raise SystemExit(f'Missing realtime channel: {channel}')
    block = main[start:start + 700]
    guard_pos = block.find(guard)
    if guard_pos < 0:
        raise SystemExit(f'Realtime channel lacks auth-session guard: {channel}')
    # Guard must happen before normal payload/state handling, not after side effects.
    side_effect_positions = [pos for marker in ('payload.new', 'payload.old', 'window.__vessel', 'leaveVoiceRoom()', 'render()') if (pos := block.find(marker)) >= 0]
    if side_effect_positions and guard_pos > min(side_effect_positions):
        raise SystemExit(f'Realtime auth-session guard is too late: {channel}')

notification_start = main.find("supabase.channel(`vessel-notifications-${user.id}`)")
if notification_start < 0:
    raise SystemExit('Missing notifications realtime channel')
notification_block = main[notification_start:notification_start + 1900]
if notification_block.count('if(savedUser?.id!==user.id)return;') < 2:
    raise SystemExit('Notification INSERT and UPDATE callbacks must both reject stale auth sessions')

server_start = main.find("vessel-servers-${user.id}")
server_block = main[server_start:server_start + 1000]
if server_block.find('if(savedUser?.id!==user.id)return;') > server_block.find('leaveVoiceRoom()'):
    raise SystemExit('Server DELETE must validate auth session before touching voice state')

print('Vessel Realtime auth-session isolation smoke check passed')
