from pathlib import Path

main = Path('src/main.js').read_text(encoding='utf-8')

history_start = main.find('async function loadDirectMessages(user, friendId)')
if history_start < 0:
    raise SystemExit('DM history loader is missing')
history = main[history_start:history_start + 1800]
for marker in [
    'const dmLoadUserId=user.id;',
    'if(savedUser?.id!==dmLoadUserId)return;',
    'if(savedUser?.id!==dmLoadUserId||activeDmId!==friendId)return;',
]:
    if marker not in history:
        raise SystemExit(f'DM history auth-session guard missing: {marker}')

access_start = main.find('async function verifyDirectMessageAccess(user,peerId')
if access_start < 0:
    raise SystemExit('DM access verifier is missing')
access = main[access_start:access_start + 2200]
for marker in [
    'const accessUserId=user.id;',
    'if(savedUser?.id!==accessUserId)return null;',
    "eq('user_id',accessUserId)",
]:
    if marker not in access:
        raise SystemExit(f'DM access auth-session guard missing: {marker}')

render_start = main.find('function render()')
composer_start = main.find("document.querySelector('.composer').addEventListener('submit', async e =>", render_start)
attach_start = main.find("document.querySelector('.attach').addEventListener('click'", render_start)
if composer_start < 0 or attach_start < 0:
    raise SystemExit('Composer or attachment handler is missing')
composer = main[composer_start:composer_start + 5200]
attachment = main[attach_start:attach_start + 5200]
for marker in [
    'const sendSessionUserId=user.id;',
    'if(savedUser?.id!==sendSessionUserId)return;',
    'author_id:sendSessionUserId',
    'sender_id:sendSessionUserId',
]:
    if marker not in composer:
        raise SystemExit(f'Composer auth-session guard missing: {marker}')
for marker in [
    'const attachmentSessionUserId=user.id;',
    'if(savedUser?.id!==attachmentSessionUserId){await cleanupFailedAttachment(attachment);return;}',
    'author_id:attachmentSessionUserId',
    'sender_id:attachmentSessionUserId',
]:
    if marker not in attachment:
        raise SystemExit(f'Attachment auth-session guard missing: {marker}')

print('Vessel DM history and message send auth-session smoke check passed')
