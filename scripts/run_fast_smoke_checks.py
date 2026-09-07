from pathlib import Path
import subprocess
import sys

scripts_dir = Path(__file__).resolve().parent
repo_dir = scripts_dir.parent
log_path = repo_dir / 'fast-gate-smoke.log'
checks = [
    'runtime_smoke_check_current.py',
    'auth_email_resilience_smoke_check.py',
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
    'voice_turn_ready_smoke_check.py',
    'incoming_call_timeout_smoke_check.py',
    'call_ice_restart_smoke_check.py',
    'call_session_cleanup_smoke_check.py',
    'media_context_smoke_check.py',
    'notification_read_smoke_check.py',
    'server_context_smoke_check.py',
    'message_auth_context_smoke_check.py',
    'channel_send_guard_smoke_check.py',
    'ui_foundation_shell_smoke_check.py',
    'ui_messaging_social_smoke_check.py',
    'ui_voice_calls_smoke_check.py',
    'ui_motion_polish_smoke_check.py',
]

missing = [name for name in checks if not (scripts_dir / name).is_file()]
if missing:
    raise SystemExit('Missing Fast Gate smoke checks: ' + ', '.join(missing))

lines = [f'Vessel Fast Gate smoke suite: {len(checks)} checks']
print(lines[0], flush=True)
for name in checks:
    heading = f'\n=== {name} ==='
    print(heading, flush=True)
    lines.append(heading)
    result = subprocess.run(
        [sys.executable, str(scripts_dir / name)],
        cwd=repo_dir,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    output = result.stdout or ''
    if output:
        print(output, end='' if output.endswith('\n') else '\n', flush=True)
        lines.append(output.rstrip('\n'))
    if result.returncode != 0:
        failure = f'FAILED: {name} (exit {result.returncode})'
        print(failure, flush=True)
        lines.append(failure)
        log_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        raise SystemExit(result.returncode)

success = '\nAll Vessel Fast Gate smoke checks passed'
print(success, flush=True)
lines.append(success)
log_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')