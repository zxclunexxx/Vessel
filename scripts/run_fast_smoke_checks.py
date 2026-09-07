from pathlib import Path
import subprocess
import sys

scripts_dir = Path(__file__).resolve().parent
checks = [
    'runtime_smoke_check_current.py',
    'logout_session_smoke_check.py',
    'realtime_session_smoke_check.py',
    'social_realtime_resilience_smoke_check.py',
    'realtime_security_smoke_check.py',
    'dm_history_smoke_check.py',
    'dm_identity_security_smoke_check.py',
    'friend_request_identity_security_smoke_check.py',
    'friend_request_transition_notification_smoke_check.py',
    'friend_request_retry_client_smoke_check.py',
    'friendship_symmetry_smoke_check.py',
    'attachment_upload_context_smoke_check.py',
    'server_owner_membership_smoke_check.py',
    'server_ownership_transfer_smoke_check.py',
    'schema_bootstrap_smoke_check.py',
    'edge_function_source_smoke_check.py',
    'voice_peer_reconnect_smoke_check.py',
    'voice_controls_smoke_check.py',
    'incoming_call_timeout_smoke_check.py',
    'call_ice_restart_smoke_check.py',
    'call_session_cleanup_smoke_check.py',
    'media_context_smoke_check.py',
    'notification_read_smoke_check.py',
    'server_context_smoke_check.py',
    'message_auth_context_smoke_check.py',
    'channel_send_guard_smoke_check.py',
]

missing = [name for name in checks if not (scripts_dir / name).is_file()]
if missing:
    raise SystemExit('Missing Fast Gate smoke checks: ' + ', '.join(missing))

print(f'Vessel Fast Gate smoke suite: {len(checks)} checks')
for name in checks:
    print(f'\n=== {name} ===', flush=True)
    subprocess.run([sys.executable, str(scripts_dir / name)], cwd=scripts_dir.parent, check=True)

print('\nAll Vessel Fast Gate smoke checks passed')
