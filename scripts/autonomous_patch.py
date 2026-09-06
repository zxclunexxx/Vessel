from pathlib import Path

main_path = Path('src/main.js')
schema_path = Path('server/schema.sql')
text = main_path.read_text(encoding='utf-8')
schema = schema_path.read_text(encoding='utf-8')
changed = False

# Reciprocal pending friend requests are rejected by PostgreSQL. Turn the expected unique
# violation into a useful UI state rather than a generic failure.
friend_old = "  if(sendError){vesselNotice('Не удалось отправить заявку.','error');return;}"
friend_new = """  if(sendError){
    if(sendError.code==='23505'){
      window.__vesselSocialLoaded=false;
      await syncSocial(user);
      vesselNotice('Заявка уже существует или пользователь одновременно отправил заявку тебе. Открой раздел «Друзья».');
      return;
    }
    vesselNotice('Не удалось отправить заявку.','error');return;
  }"""
if friend_new not in text:
    if friend_old not in text:
        raise SystemExit('friend request error-handling anchor not found')
    text = text.replace(friend_old, friend_new, 1)
    changed = True

# Keep the checked-in bootstrap snapshot aligned with the production migration.
index_marker = 'friend_requests_pending_pair_uidx'
if index_marker not in schema:
    schema_anchor = 'create index if not exists friend_requests_receiver_status_idx on public.friend_requests(receiver_id,status);\n'
    if schema_anchor not in schema:
        raise SystemExit('friend request schema anchor not found')
    schema_insert = schema_anchor + """create unique index if not exists friend_requests_pending_pair_uidx
on public.friend_requests (least(sender_id,receiver_id), greatest(sender_id,receiver_id))
where status='pending';
"""
    schema = schema.replace(schema_anchor, schema_insert, 1)
    changed = True

if friend_new not in text:
    raise SystemExit('friend request duplicate handling missing after patch')
if index_marker not in schema:
    raise SystemExit('friend request symmetric pending index missing after patch')

if changed:
    main_path.write_text(text, encoding='utf-8')
    schema_path.write_text(schema, encoding='utf-8')
    print('Applied Vessel friend-request hardening')
else:
    print('Vessel friend-request hardening already applied; nothing to change')
