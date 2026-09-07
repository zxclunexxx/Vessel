from pathlib import Path
import subprocess
import sys

scripts_dir = Path(__file__).resolve().parent

preferred_order = [
    'autonomous_patch.py',
    'reliability_patch.py',
    'session_patch.py',
    'lifecycle_patch.py',
    'attachment_context_patch.py',
    'attachment_storage_context_patch.py',
    'call_security_patch.py',
    'profile_privacy_patch.py',
    'dm_thread_security_patch.py',
    'friend_request_policy_patch.py',
    'voice_reconnect_patch.py',
    'voice_switch_patch.py',
    'voice_controls_patch.py',
    'call_reconnect_patch.py',
    'call_access_race_patch.py',
    'call_network_loss_patch.py',
    'incoming_call_timeout_patch.py',
    'message_context_patch.py',
    'server_context_patch.py',
    'server_delete_realtime_patch.py',
    'realtime_session_guard_patch.py',
    'realtime_security_patch.py',
    'realtime_policy_cache_patch.py',
    'dm_unfriend_history_patch.py',
    'notification_session_patch.py',
    'social_sync_patch.py',
    'dm_send_guard_patch.py',
    'server_sync_patch.py',
    'media_context_patch.py',
    'channel_send_guard_patch.py',
    'dm_identity_security_patch.py',
    'message_mutation_rpc_patch.py',
    'message_mutation_patch.py',
    'dm_unread_patch.py',
    'notification_navigation_patch.py',
    'mobile_drawer_close_patch.py',
]

runner_name = Path(__file__).name
ordered = []
seen = set()
for name in preferred_order:
    path = scripts_dir / name
    if path.exists():
        ordered.append(path)
        seen.add(name)

# New feature patches are intentionally appended after the compatibility/hardening chain.
# This keeps the historical order stable while removing the need to edit the workflow for
# every new patch file.
extras = sorted(
    path for path in scripts_dir.glob('*_patch.py')
    if path.name not in seen and path.name != runner_name
)
ordered.extend(extras)

if not ordered:
    raise SystemExit('No Vessel patch scripts found')

print('Vessel patch pipeline:')
for path in ordered:
    print(f'  - {path.name}')

for path in ordered:
    print(f'\n=== {path.name} ===', flush=True)
    subprocess.run([sys.executable, str(path)], cwd=scripts_dir.parent, check=True)

print('\nVessel patch pipeline completed successfully')
