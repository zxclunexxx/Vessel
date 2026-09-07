from pathlib import Path

MAIN_PATH = Path('src/main.js')
STYLE_PATH = Path('src/style.css')
MARKER = '/* VESSEL_UI_MESSAGING_SOCIAL_V1 */'

main = MAIN_PATH.read_text(encoding='utf-8')
style = STYLE_PATH.read_text(encoding='utf-8')

status_old = """function statusLabel(value='online') {
  const key=String(value||'online').toLowerCase();
  if(['dnd','не беспокоить'].includes(key))return 'Не беспокоить';
  if(['away','idle','отошёл'].includes(key))return 'Отошёл';
  return 'В сети';
}
"""
status_new = status_old + """function statusTone(value='online') {
  const key=String(value||'online').toLowerCase();
  if(['dnd','не беспокоить'].includes(key))return 'dnd';
  if(['away','idle','отошёл'].includes(key))return 'away';
  if(['offline','не в сети'].includes(key))return 'offline';
  return 'online';
}
"""

message_old = """function messageMarkup(message,user,canMutate=true) {
  const own=Boolean(canMutate&&message?.id&&message.authorId===user?.id);
  const edited=message?.editedAt?' · изменено':'';
  const actions=own?`<span class=\"message-actions\"><button type=\"button\" data-edit-message=\"${escapeHtml(message.id)}\" title=\"Редактировать сообщение\">✎</button><button type=\"button\" data-delete-message=\"${escapeHtml(message.id)}\" title=\"Удалить сообщение\">×</button></span>`:'';
  return `<article class=\"message\" data-message-id=\"${escapeHtml(message?.id||'')}\"><div class=\"avatar\" style=\"background:${escapeHtml(message?.color||'#8b7cff')}\">${escapeHtml(message?.name?.[0]||'?')}</div><div class=\"message-content\"><div class=\"message-meta\"><b>${escapeHtml(message?.name||'Пользователь')}</b><time>${escapeHtml(message?.time||'')}${edited}</time>${actions}</div><p>${escapeHtml(message?.text||'')}</p>${attachmentMarkup(message?.attachments)}</div></article>`;
}
"""
message_new = """function messageMarkup(message,user,canMutate=true) {
  const isMine=Boolean(message?.authorId===user?.id);
  const own=Boolean(canMutate&&message?.id&&isMine);
  const edited=message?.editedAt?' · изменено':'';
  const actions=own?`<span class=\"message-actions\"><button type=\"button\" data-edit-message=\"${escapeHtml(message.id)}\" title=\"Редактировать сообщение\">✎</button><button type=\"button\" data-delete-message=\"${escapeHtml(message.id)}\" title=\"Удалить сообщение\">×</button></span>`:'';
  return `<article class=\"message ${isMine?'mine':''}\" data-message-id=\"${escapeHtml(message?.id||'')}\"><div class=\"avatar message-avatar\" style=\"background:${escapeHtml(message?.color||'#8b7cff')}\">${escapeHtml(message?.name?.[0]||'?')}</div><div class=\"message-content\"><div class=\"message-meta\"><b>${escapeHtml(message?.name||'Пользователь')}</b><time>${escapeHtml(message?.time||'')}${edited}</time>${actions}</div><p>${escapeHtml(message?.text||'')}</p>${attachmentMarkup(message?.attachments)}</div></article>`;
}
"""

dm_old = """  const dmList=dmThreads.length
    ? dmThreads.map(thread=>{const unread=unreadDirectMessageCount(thread.id);return `<button class=\"channel dm ${activeDmId===thread.id?'active':''}\" data-dm-id=\"${thread.id}\" data-dm=\"${escapeHtml(thread.username)}\"><div class=\"mini-avatar\" style=\"background:${thread.avatar_color||'#8b7cff'}\">${(thread.username||'?')[0].toUpperCase()}</div> ${escapeHtml(thread.username)} ${unread?`<em class=\"dm-unread\" title=\"Непрочитанных: ${unread}\">${unread>99?'99+':unread}</em>`:''}</button>`;}).join('')
    : `<div class=\"dm-empty\">Пока нет личных чатов</div>`;
"""
dm_new = """  const dmList=dmThreads.length
    ? dmThreads.map(thread=>{const unread=unreadDirectMessageCount(thread.id);const tone=statusTone(thread.status);return `<button class=\"channel dm status-${tone} ${activeDmId===thread.id?'active':''}\" data-dm-id=\"${thread.id}\" data-dm=\"${escapeHtml(thread.username)}\"><span class=\"dm-avatar-wrap\"><span class=\"mini-avatar\" style=\"background:${thread.avatar_color||'#8b7cff'}\">${escapeHtml((thread.username||'?')[0].toUpperCase())}</span><i class=\"presence-dot\"></i></span><span class=\"dm-copy\"><b>${escapeHtml(thread.username)}</b><small>${escapeHtml(statusLabel(thread.status))}</small></span>${unread?`<em class=\"dm-unread\" title=\"Непрочитанных: ${unread}\">${unread>99?'99+':unread}</em>`:''}</button>`;}).join('')
    : window.__vesselDmThreadsLoaded
      ? `<div class=\"social-empty compact\"><span class=\"social-empty-orb\">✦</span><b>Диалогов пока нет</b><small>Добавь друга и начни личное общение.</small></div>`
      : `<div class=\"dm-skeleton-stack\"><span></span><span></span><span></span></div>`;
"""

hero_old = """<div class=\"friends-view\"><div class=\"friends-hero\"><h2>Друзья</h2><button id=\"add-friend\" class=\"primary\">Найти пользователя</button></div>"""
hero_new = """<div class=\"friends-view\"><div class=\"friends-hero\"><div class=\"friends-title\"><span class=\"social-eyebrow\">VESSEL SOCIAL</span><h2>Друзья</h2><p>Люди, заявки и быстрый доступ к личному общению.</p></div><div class=\"social-stats\"><span><b>${friends.length}</b> друзей</span><span><b>${friendRequests.length}</b> входящих</span><span><b>${outgoingFriendRequests.length}</b> ожидают</span></div><button id=\"add-friend\" class=\"primary social-add\">Найти пользователя <span>＋</span></button></div>${!window.__vesselSocialLoaded?'<div class=\"social-skeleton\"><i></i><i></i><i></i></div>':''}"""

replacements = [
    ('status helper', status_old, status_new),
    ('message markup', message_old, message_new),
    ('DM list', dm_old, dm_new),
    ('friends hero', hero_old, hero_new),
    ('incoming friend card', '<div class=\"friend-row request-row\">', '<div class=\"friend-row friend-card request-row incoming-request\">'),
    ('incoming badge', '<span>Заявка</span><button data-accept-request=', '<span class=\"request-badge\">Входящая заявка</span><button class=\"friend-action accept-action\" data-accept-request='),
    ('decline action', '<button class=\"danger compact\" data-decline-request=', '<button class=\"danger compact friend-action\" data-decline-request='),
    ('outgoing friend card', '<div class=\"friend-row outgoing-request-row\">', '<div class=\"friend-row friend-card outgoing-request-row\">'),
    ('cancel action', '<button class=\"danger compact\" data-cancel-request=', '<button class=\"danger compact friend-action\" data-cancel-request='),
    ('friend card', 'friends.map(friend=>`<div class=\"friend-row\"><div class=\"avatar\"', 'friends.map(friend=>`<div class=\"friend-row friend-card status-${statusTone(friend.status)}\"><div class=\"avatar\"'),
    ('DM friend action', '<button data-dm-id=\"${friend.id}\" data-dm=\"${escapeHtml(friend.username)}\">💬</button>', '<button class=\"friend-action dm-action\" data-dm-id=\"${friend.id}\" data-dm=\"${escapeHtml(friend.username)}\" title=\"Написать\">💬</button>'),
    ('call friend action', '<button data-call-id=\"${friend.id}\" data-call=\"${escapeHtml(friend.username)}\">📞</button>', '<button class=\"friend-action call-action\" data-call-id=\"${friend.id}\" data-call=\"${escapeHtml(friend.username)}\" title=\"Позвонить\">📞</button>'),
    ('remove friend action', '<button class=\"danger compact\" data-remove-friend=\"${friend.id}\" title=\"Удалить из друзей\">×</button>', '<button class=\"danger compact friend-action remove-action\" data-remove-friend=\"${friend.id}\" title=\"Удалить из друзей\">×</button>'),
    ('friends empty state', '<p class=\"empty-state\">Пока нет добавленных друзей. Нажми «Найти пользователя».</p>', '<div class=\"social-empty\"><span class=\"social-empty-orb\">◇</span><h3>Здесь пока тихо</h3><p>Найди пользователя Vessel и начни общение.</p></div>'),
]

if MARKER in style:
    required_main = [
        'function statusTone(',
        'class=\"message ${isMine?',
        'dm-avatar-wrap',
        'friends-title',
        'friend-row friend-card',
    ]
    missing = [item for item in required_main if item not in main]
    if missing:
        raise SystemExit('Messaging/social UI marker exists but runtime is incomplete: ' + ', '.join(missing))
    print('Vessel messaging/social UI already applied')
    raise SystemExit(0)

for name, old, new in replacements:
    count = main.count(old)
    if count != 1:
        raise SystemExit(f'Messaging/social UI source drift at {name}: expected 1, found {count}')
    main = main.replace(old, new, 1)

foundation = r'''

/* VESSEL_UI_MESSAGING_SOCIAL_V1 */
.friends-view {
  width: min(960px, 100%);
  max-width: 960px;
  margin: 0 auto;
  padding-bottom: 34px;
}
.friends-hero {
  position: relative;
  display: grid;
  grid-template-columns: minmax(220px,1fr) auto auto;
  align-items: center;
  gap: 18px;
  margin: 0 0 20px;
  padding: 24px;
  border: 1px solid var(--v-border);
  border-radius: 24px;
  background:
    radial-gradient(circle at 10% 0, rgba(59,231,255,.10), transparent 38%),
    radial-gradient(circle at 92% 18%, rgba(217,70,239,.10), transparent 34%),
    linear-gradient(145deg, rgba(255,255,255,.055), rgba(255,255,255,.022));
  box-shadow: 0 22px 55px rgba(0,0,0,.22), inset 0 1px 0 rgba(255,255,255,.045);
  overflow: hidden;
}
.friends-hero::after {
  content: '';
  position: absolute;
  width: 180px;
  height: 180px;
  right: -72px;
  top: -98px;
  border-radius: 50%;
  background: linear-gradient(135deg, rgba(59,231,255,.24), rgba(139,92,255,.18), rgba(217,70,239,.15));
  filter: blur(28px);
  pointer-events: none;
}
.friends-title { min-width: 0; position: relative; z-index: 1; }
.social-eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  margin-bottom: 8px;
  color: #8ddff1;
  font-size: 9px;
  font-weight: 800;
  letter-spacing: .19em;
}
.social-eyebrow::before {
  content: '';
  width: 17px;
  height: 1px;
  background: linear-gradient(90deg,var(--v-cyan),var(--v-violet));
  box-shadow: 0 0 8px rgba(59,231,255,.4);
}
.friends-title h2 { margin: 0; font-size: clamp(23px,2.4vw,32px); letter-spacing: -.035em; }
.friends-title p { margin: 7px 0 0; color: var(--v-text-3); font-size: 12px; line-height: 1.5; }
.social-stats { display: flex; align-items: stretch; gap: 7px; position: relative; z-index: 1; }
.social-stats > span {
  min-width: 76px;
  padding: 9px 10px;
  border: 1px solid rgba(255,255,255,.065);
  border-radius: 13px;
  color: var(--v-text-3);
  background: rgba(4,8,15,.22);
  font-size: 9px;
  text-align: center;
}
.social-stats b { display: block; margin-bottom: 2px; color: var(--v-text-1); font-size: 14px; }
.social-add {
  width: auto!important;
  min-width: 154px;
  margin: 0!important;
  padding: 12px 14px!important;
  border: 1px solid rgba(153,123,255,.24)!important;
  background: linear-gradient(120deg, rgba(59,231,255,.16), rgba(139,92,255,.36) 55%, rgba(217,70,239,.20))!important;
  box-shadow: 0 10px 28px rgba(76,63,214,.15), inset 0 1px 0 rgba(255,255,255,.12);
  position: relative;
  z-index: 1;
  transition: transform var(--v-fast) var(--v-ease-ui), box-shadow var(--v-normal), border-color var(--v-normal)!important;
}
.social-add:hover { transform: translateY(-2px); border-color: rgba(117,225,255,.32)!important; box-shadow: 0 15px 36px rgba(76,63,214,.22), 0 0 24px rgba(59,231,255,.08); }
.social-add span { float: none!important; margin-left: 8px; }

.friend-row.friend-card {
  position: relative;
  display: grid;
  grid-template-columns: 48px minmax(130px,1fr) minmax(100px,auto) 40px 40px 40px;
  align-items: center;
  gap: 11px;
  min-height: 70px;
  margin: 8px 0;
  padding: 10px 12px;
  border: 1px solid rgba(214,230,255,.065);
  border-radius: 18px;
  background: linear-gradient(145deg, rgba(255,255,255,.044), rgba(255,255,255,.018));
  box-shadow: inset 0 1px 0 rgba(255,255,255,.028);
  overflow: hidden;
  transition: transform var(--v-normal) var(--v-ease-spring), border-color var(--v-normal), background var(--v-normal), box-shadow var(--v-normal);
}
.friend-row.friend-card::before {
  content: '';
  position: absolute;
  left: 0;
  top: 16px;
  bottom: 16px;
  width: 2px;
  border-radius: 99px;
  background: linear-gradient(180deg,var(--v-cyan),var(--v-violet));
  opacity: .28;
  transition: opacity var(--v-normal), box-shadow var(--v-normal);
}
.friend-row.friend-card:hover {
  transform: translateY(-2px);
  border-color: rgba(137,164,255,.15);
  background: linear-gradient(145deg, rgba(255,255,255,.065), rgba(110,90,255,.035));
  box-shadow: 0 15px 36px rgba(0,0,0,.16), inset 0 1px 0 rgba(255,255,255,.04);
}
.friend-row.friend-card:hover::before { opacity: .9; box-shadow: 0 0 13px rgba(59,231,255,.35); }
.friend-card .avatar {
  position: relative;
  width: 42px;
  height: 42px;
  border-radius: 15px;
  box-shadow: 0 8px 22px rgba(0,0,0,.22), inset 0 1px 0 rgba(255,255,255,.14);
}
.friend-card.status-online .avatar::after,
.friend-card.status-away .avatar::after,
.friend-card.status-dnd .avatar::after,
.friend-card.status-offline .avatar::after {
  content: '';
  position: absolute;
  width: 10px;
  height: 10px;
  right: -3px;
  bottom: -2px;
  border: 3px solid #111725;
  border-radius: 50%;
  background: var(--v-green);
  box-shadow: 0 0 10px rgba(94,231,178,.35);
}
.friend-card.status-away .avatar::after { background: #f8c95f; box-shadow: 0 0 10px rgba(248,201,95,.28); }
.friend-card.status-dnd .avatar::after { background: var(--v-danger); box-shadow: 0 0 10px rgba(255,111,145,.3); }
.friend-card.status-offline .avatar::after { background: #657086; box-shadow: none; }
.friend-card > b { color: var(--v-text-1); font-size: 13px; letter-spacing: -.01em; overflow: hidden; text-overflow: ellipsis; }
.friend-card > span { color: var(--v-text-3); font-size: 10px; }
.friend-card.status-online > span:not(.request-badge):not(.pending-label) { color: #7edfc1; }
.friend-action {
  width: 36px!important;
  height: 36px!important;
  margin: 0!important;
  padding: 0!important;
  display: grid!important;
  place-items: center;
  border: 1px solid rgba(255,255,255,.055)!important;
  border-radius: 12px!important;
  background: rgba(255,255,255,.035)!important;
  color: var(--v-text-2)!important;
  transition: transform var(--v-fast) var(--v-ease-ui), background var(--v-fast), color var(--v-fast), border-color var(--v-fast)!important;
}
.friend-action:hover { transform: translateY(-2px); color: #fff!important; border-color: rgba(139,92,255,.18)!important; background: rgba(139,92,255,.12)!important; }
.friend-action.accept-action { width: auto!important; min-width: 82px!important; padding: 0 11px!important; color: #aff4dd!important; border-color: rgba(94,231,178,.14)!important; background: rgba(94,231,178,.075)!important; }
.friend-action.accept-action:hover { background: rgba(94,231,178,.15)!important; border-color: rgba(94,231,178,.26)!important; }
.friend-action.remove-action,
.friend-action[data-decline-request],
.friend-action[data-cancel-request] { color: #ff9db4!important; border-color: rgba(255,111,145,.12)!important; background: rgba(255,111,145,.055)!important; }
.request-row.friend-card { border-color: rgba(255,190,101,.10); background: linear-gradient(145deg,rgba(255,183,92,.055),rgba(255,255,255,.018)); }
.request-row.friend-card::before { background: linear-gradient(180deg,#ffca6a,#ff7b95); }
.outgoing-request-row.friend-card { border-color: rgba(139,92,255,.11); }
.outgoing-request-row.friend-card::before { background: linear-gradient(180deg,#8d8aff,var(--v-magenta)); }
.request-badge,
.pending-label {
  justify-self: start;
  padding: 5px 8px;
  border: 1px solid rgba(255,186,104,.13);
  border-radius: 999px;
  color: #ffd49a!important;
  background: rgba(255,179,92,.065);
  font-size: 9px!important;
  white-space: nowrap;
}
.pending-label { color: #b8adff!important; border-color: rgba(139,92,255,.15); background: rgba(139,92,255,.075); }

.channel.dm {
  min-height: 51px;
  padding: 7px 9px!important;
  gap: 9px;
  border-radius: 14px!important;
}
.dm-avatar-wrap { position: relative; display: inline-grid; flex: none; }
.channel.dm .mini-avatar { width: 32px; height: 32px; margin: 0; border-radius: 11px; box-shadow: 0 7px 18px rgba(0,0,0,.2); }
.presence-dot {
  position: absolute;
  right: -2px;
  bottom: -2px;
  width: 9px;
  height: 9px;
  border: 2px solid #121827;
  border-radius: 50%;
  background: var(--v-green);
  box-shadow: 0 0 9px rgba(94,231,178,.36);
}
.channel.dm.status-away .presence-dot { background: #f8c95f; box-shadow: none; }
.channel.dm.status-dnd .presence-dot { background: var(--v-danger); box-shadow: none; }
.channel.dm.status-offline .presence-dot { background: #657086; box-shadow: none; }
.dm-copy { min-width: 0; display: flex; flex: 1; flex-direction: column; gap: 2px; }
.dm-copy b { overflow: hidden; color: var(--v-text-2); font-size: 11px; font-weight: 650; text-overflow: ellipsis; white-space: nowrap; }
.dm-copy small { color: #66728a; font-size: 8.5px; }
.channel.dm.active .dm-copy b,
.channel.dm:hover .dm-copy b { color: #fff; }
.channel.dm.active .dm-copy small { color: #9bbcf0; }
.channel.dm em.dm-unread {
  flex: none;
  min-width: 20px;
  height: 20px;
  border: 1px solid rgba(255,255,255,.12);
  background: linear-gradient(135deg,var(--v-cyan),var(--v-violet) 55%,var(--v-magenta));
  box-shadow: 0 0 18px rgba(116,95,255,.25);
  animation: vesselUnreadBreath 2.8s ease-in-out infinite;
}
@keyframes vesselUnreadBreath { 0%,100%{transform:scale(1);filter:saturate(1)} 50%{transform:scale(1.06);filter:saturate(1.18)} }

.message {
  position: relative;
  align-items: flex-start;
  gap: 12px;
  margin: 3px -10px;
  padding: 12px 12px;
  border: 1px solid transparent;
  border-radius: 17px;
  transition: transform var(--v-fast) var(--v-ease-ui), background var(--v-normal), border-color var(--v-normal), box-shadow var(--v-normal);
}
.message::before {
  content: '';
  position: absolute;
  left: 2px;
  top: 17px;
  bottom: 17px;
  width: 2px;
  border-radius: 99px;
  background: linear-gradient(180deg,var(--v-cyan),var(--v-violet));
  opacity: 0;
  transition: opacity var(--v-fast);
}
.message:hover {
  transform: translateX(2px);
  border-color: rgba(214,230,255,.055);
  background: linear-gradient(100deg,rgba(255,255,255,.038),rgba(139,92,255,.018));
  box-shadow: inset 0 1px 0 rgba(255,255,255,.02);
}
.message:hover::before { opacity: .42; }
.message.mine::before { opacity: .28; background: linear-gradient(180deg,var(--v-violet),var(--v-magenta)); }
.message.mine:hover::before { opacity: .8; box-shadow: 0 0 11px rgba(139,92,255,.28); }
.message-avatar {
  width: 39px;
  height: 39px;
  border-radius: 14px;
  box-shadow: 0 8px 20px rgba(0,0,0,.22), inset 0 1px 0 rgba(255,255,255,.13);
}
.message-content { min-width: 0; flex: 1; }
.message-meta { min-height: 21px; gap: 8px; }
.message-meta b { color: #eef4ff; font-size: 12px; letter-spacing: -.008em; }
.message-meta time { color: #5e6a80; font-size: 9px; }
.message p { margin: 3px 0 0; color: #cbd4e4; font-size: 12.5px; line-height: 1.58; }
.message-actions {
  display: inline-flex;
  gap: 4px;
  margin-left: auto;
  opacity: 0;
  transform: translateY(3px);
  transition: opacity var(--v-fast), transform var(--v-fast) var(--v-ease-ui);
}
.message:hover .message-actions,
.message:focus-within .message-actions { opacity: 1; transform: translateY(0); }
.message-actions button {
  width: 28px;
  height: 28px;
  border: 1px solid rgba(255,255,255,.055);
  border-radius: 9px;
  color: #8793a8;
  background: rgba(9,13,22,.58);
  cursor: pointer;
}
.message-actions button:hover { color: #fff; border-color: rgba(139,92,255,.18); background: rgba(139,92,255,.12); }
.attachment-link {
  margin-top: 8px;
  border-color: rgba(131,151,255,.12);
  border-radius: 11px;
  color: #b9c8e5;
  background: linear-gradient(145deg,rgba(79,124,255,.065),rgba(139,92,255,.045));
  transition: transform var(--v-fast), border-color var(--v-fast), background var(--v-fast);
}
.attachment-link:hover { transform: translateY(-1px); border-color: rgba(105,203,255,.22); background: rgba(79,124,255,.11); }

.composer {
  position: relative;
  min-height: 54px;
  overflow: visible;
}
.composer::before {
  content: '';
  position: absolute;
  inset: -1px;
  z-index: -1;
  border-radius: inherit;
  background: linear-gradient(110deg,rgba(59,231,255,.10),rgba(139,92,255,.17),rgba(217,70,239,.08));
  opacity: .25;
  filter: blur(8px);
  transition: opacity var(--v-normal);
}
.composer:focus-within::before { opacity: .75; }
.composer input { caret-color: var(--v-cyan); }
.composer .send {
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  border: 1px solid rgba(139,92,255,.14)!important;
  border-radius: 11px;
  color: #fff!important;
  background: linear-gradient(135deg,rgba(59,231,255,.16),rgba(139,92,255,.32),rgba(217,70,239,.16))!important;
  box-shadow: 0 7px 20px rgba(79,76,220,.13);
  transition: transform var(--v-fast) var(--v-ease-ui), box-shadow var(--v-fast)!important;
}
.composer .send:hover { transform: translateY(-2px); box-shadow: 0 11px 25px rgba(79,76,220,.22),0 0 16px rgba(59,231,255,.06); }

.social-empty {
  display: grid;
  justify-items: center;
  gap: 7px;
  margin: 28px auto;
  padding: 34px 24px;
  border: 1px dashed rgba(145,164,210,.13);
  border-radius: 22px;
  color: var(--v-text-3);
  background: linear-gradient(145deg,rgba(255,255,255,.025),rgba(139,92,255,.018));
  text-align: center;
}
.social-empty.compact { margin: 8px 5px; padding: 18px 10px; border-radius: 15px; }
.social-empty-orb {
  width: 48px;
  height: 48px;
  display: grid;
  place-items: center;
  margin-bottom: 3px;
  border: 1px solid rgba(139,92,255,.16);
  border-radius: 17px;
  color: #a8b6ff;
  background: radial-gradient(circle at 35% 30%,rgba(59,231,255,.12),rgba(139,92,255,.10) 48%,rgba(217,70,239,.05));
  box-shadow: 0 13px 30px rgba(0,0,0,.17),inset 0 1px 0 rgba(255,255,255,.05);
}
.social-empty h3,.social-empty b { margin: 4px 0 0; color: var(--v-text-2); font-size: 13px; }
.social-empty p,.social-empty small { margin: 0; max-width: 310px; color: var(--v-text-3); font-size: 10px; line-height: 1.55; }

.social-skeleton,
.dm-skeleton-stack { display: grid; gap: 9px; margin: 10px 0; }
.social-skeleton i,
.dm-skeleton-stack span {
  display: block;
  height: 66px;
  border: 1px solid rgba(255,255,255,.035);
  border-radius: 17px;
  background: linear-gradient(105deg,rgba(255,255,255,.025) 20%,rgba(139,92,255,.085) 42%,rgba(255,255,255,.025) 64%);
  background-size: 220% 100%;
  animation: vesselSocialShimmer 1.45s linear infinite;
}
.dm-skeleton-stack { margin: 5px 4px; }
.dm-skeleton-stack span { height: 45px; border-radius: 13px; }
@keyframes vesselSocialShimmer { from{background-position:180% 0} to{background-position:-40% 0} }

.members .members-title + .dm-empty {
  margin-top: 7px;
  border: 1px solid rgba(255,255,255,.04);
  border-radius: 13px;
  background: rgba(255,255,255,.018);
}

@media (max-width: 900px) {
  .friends-hero { grid-template-columns: 1fr auto; }
  .social-stats { grid-column: 1 / -1; order: 3; justify-content: flex-start; }
  .social-stats > span { min-width: 84px; }
}
@media (max-width: 700px) {
  .friends-hero { grid-template-columns: 1fr; padding: 18px; }
  .social-add { width: 100%!important; }
  .social-stats { display: grid; grid-template-columns: repeat(3,1fr); width: 100%; }
  .social-stats > span { min-width: 0; }
  .friend-row.friend-card { grid-template-columns: 43px minmax(0,1fr) 36px 36px 36px; padding: 9px 10px; }
  .friend-card > span:not(.friend-action) { grid-column: 2; }
  .request-row.friend-card,
  .outgoing-request-row.friend-card { grid-template-columns: 43px minmax(0,1fr) auto 36px; }
  .request-row .accept-action { grid-column: 2 / 4; width: 100%!important; }
  .message { margin-left: -5px; margin-right: -5px; padding: 10px 8px; }
  .message-avatar { width: 35px; height: 35px; border-radius: 12px; }
}
@media (max-width: 460px) {
  .friends-title p { display: none; }
  .social-stats { gap: 5px; }
  .social-stats > span { padding: 7px 5px; font-size: 8px; }
  .friend-row.friend-card { grid-template-columns: 40px minmax(0,1fr) 34px 34px; }
  .friend-card .avatar { width: 38px; height: 38px; }
  .friend-row.friend-card > .remove-action { display: none!important; }
  .request-row.friend-card,.outgoing-request-row.friend-card { grid-template-columns: 40px minmax(0,1fr) 34px; }
  .request-row .request-badge,.outgoing-request-row .pending-label { grid-column: 2; }
  .request-row .accept-action { grid-column: 2; }
}
@media (prefers-reduced-motion: reduce) {
  .channel.dm em.dm-unread,
  .social-skeleton i,
  .dm-skeleton-stack span { animation: none!important; }
}
'''

if style.count('/* VESSEL_UI_FOUNDATION_SHELL_V1 */') != 1:
    raise SystemExit('Messaging/social UI requires exactly one foundation shell marker')
if MARKER in style:
    raise SystemExit('Messaging/social UI marker appeared unexpectedly during patch application')

MAIN_PATH.write_text(main, encoding='utf-8')
STYLE_PATH.write_text(style.rstrip() + foundation + '\n', encoding='utf-8')
print('Applied Vessel messaging/social UI patch')
