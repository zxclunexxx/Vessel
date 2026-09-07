from pathlib import Path

main = Path('src/main.js').read_text(encoding='utf-8')
style = Path('src/style.css').read_text(encoding='utf-8')

required_main = [
    'function statusTone(',
    "const isMine=Boolean(message?.authorId===user?.id);",
    'class=\"message ${isMine?',
    'message-avatar',
    'dm-avatar-wrap',
    'presence-dot',
    'dm-copy',
    'window.__vesselDmThreadsLoaded',
    'friends-title',
    'social-stats',
    'social-add',
    'friend-row friend-card',
    'incoming-request',
    'outgoing-request-row',
    'friend-action accept-action',
    'social-empty',
    'social-skeleton',
]
missing_main = [marker for marker in required_main if marker not in main]
if missing_main:
    raise SystemExit('Missing messaging/social runtime markers: ' + ', '.join(missing_main))

required_style = [
    '/* VESSEL_UI_MESSAGING_SOCIAL_V1 */',
    '.friends-hero {',
    '.social-eyebrow',
    '.friend-row.friend-card {',
    '.friend-card.status-online .avatar::after',
    '.channel.dm.status-away .presence-dot',
    '.message.mine::before',
    '.message-actions {',
    '.composer::before',
    '.social-empty {',
    '.social-skeleton,',
    '@keyframes vesselSocialShimmer',
    '@keyframes vesselUnreadBreath',
    '@media (prefers-reduced-motion: reduce)',
]
missing_style = [marker for marker in required_style if marker not in style]
if missing_style:
    raise SystemExit('Missing messaging/social visual markers: ' + ', '.join(missing_style))

if style.count('/* VESSEL_UI_MESSAGING_SOCIAL_V1 */') != 1:
    raise SystemExit('Messaging/social UI marker must be unique')
if style.count('/* VESSEL_UI_FOUNDATION_SHELL_V1 */') != 1:
    raise SystemExit('Foundation UI marker must remain unique')

for secret_marker in ['SUPABASE_SERVICE_ROLE_KEY', 'TURN_SHARED_SECRET', 'SMTP_PASSWORD']:
    if secret_marker in style:
        raise SystemExit('Visual stylesheet must never contain backend secret markers: ' + secret_marker)

if "class=\"message\" data-message-id" in main:
    raise SystemExit('Messages must retain semantic mine styling for the social UI')

print('Vessel messaging/social UI smoke check passed')
