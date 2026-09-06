from pathlib import Path

# Reliability baseline verifier. The fixes originally applied by this script are already
# committed to main and server/schema.sql; exact replacement anchors made later patches
# conflict unnecessarily. Verify behavior markers instead.
main = Path('src/main.js').read_text(encoding='utf-8')
schema = Path('server/schema.sql').read_text(encoding='utf-8')

main_markers = [
    'channel.__subscribePromise',
    "channel.__subscribed = false",
    'CALL_SIGNAL_CHANNEL_UNAVAILABLE',
    'Call inbox retry failed',
    'Voice presence restore failed',
]
schema_markers = [
    'senders can cancel pending friend requests',
]

missing = [marker for marker in main_markers if marker not in main]
missing += [marker for marker in schema_markers if marker not in schema]
if not any(marker in schema for marker in [
    'senders can retry terminal friend requests',
    'participants can update friend requests',
]):
    missing.append('friend request retry/update policy')
if missing:
    raise SystemExit('Vessel reliability marker missing: ' + ', '.join(missing))

print('Vessel reliability hardening already applied; nothing to change')
