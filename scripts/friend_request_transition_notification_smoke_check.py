from pathlib import Path

schema = Path('server/schema.sql').read_text(encoding='utf-8')
migration = Path('server/migrations/20260907_friend_request_transition_notifications.sql').read_text(encoding='utf-8')

required_schema = [
    "(receiver_id=(select auth.uid()) and status='pending')",
    'create or replace function public.vessel_notify_friend_accepted()',
    'create trigger vessel_friend_request_retry_notification',
    "new.status='pending'",
    'create trigger vessel_friend_request_accepted_notification',
    "new.status='accepted'",
    "'friend_accepted'",
    "jsonb_build_object('request_id',new.id,'friend_id',new.receiver_id)",
]
for marker in required_schema:
    if marker not in schema:
        raise SystemExit(f'Friend transition/notification bootstrap guard missing: {marker}')

required_migration = [
    "(receiver_id = (select auth.uid()) and status = 'pending')",
    'create or replace function public.vessel_notify_friend_accepted()',
    'vessel_friend_request_retry_notification',
    'vessel_friend_request_accepted_notification',
    "'friend_accepted'",
]
for marker in required_migration:
    if marker not in migration:
        raise SystemExit(f'Friend transition/notification migration guard missing: {marker}')

legacy = '''using(\n  receiver_id=(select auth.uid())\n  or (sender_id=(select auth.uid()) and status in ('accepted','declined','cancelled'))'''
if legacy in schema:
    raise SystemExit('Receiver can still rewrite a terminal friend-request status')

print('Vessel friend request transition and notification smoke check passed')
