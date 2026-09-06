from pathlib import Path

# Idempotent patch: secure Vessel WebRTC signaling and voice presence with private Realtime.
# Supabase Realtime Authorization is evaluated when a client joins a private topic, so the
# database policies below authorize topic access; they intentionally do not inspect individual
# broadcast payloads as if RLS were re-evaluated for every message.
main_path = Path('src/main.js')
schema_path = Path('server/schema.sql')
main = main_path.read_text(encoding='utf-8')
schema = schema_path.read_text(encoding='utf-8')
main_changed = False
schema_changed = False

def replace_main(old, new, label):
    global main, main_changed
    if new in main:
        return
    if old not in main:
        raise SystemExit(f'{label}: expected source or secured form not found')
    main = main.replace(old, new, 1)
    main_changed = True

replace_main(
    "room=supabase.channel(`voice-${targetChannelId}`,{config:{presence:{key:user.id}}});",
    "room=supabase.channel(`voice-${targetChannelId}`,{config:{private:true,presence:{key:user.id}}});",
    'voice channel private authorization',
)
replace_main(
    "const channel = supabase.channel(callInboxName(peerId));",
    "const channel = supabase.channel(callInboxName(peerId),{config:{private:true}});",
    'call invite sender private inbox',
)
replace_main(
    "const inbox=supabase.channel(name);",
    "const inbox=supabase.channel(name,{config:{private:true}});",
    'call inbox private authorization',
)
replace_main(
    "const room=supabase.channel(name);\n  callChannel=room;",
    "const room=supabase.channel(name,{config:{private:true}});\n  callChannel=room;",
    'call signaling private authorization',
)

schema_marker = '-- Vessel private Realtime authorization -----------------------------------------'
if schema_marker not in schema:
    anchor = "alter table public.notifications enable row level security;\n\n"
    if anchor not in schema:
        raise SystemExit('RLS schema anchor not found')
    block = r'''-- Vessel private Realtime authorization -----------------------------------------
-- Call/voice WebRTC signaling uses private Supabase Realtime topics. Realtime Authorization
-- is calculated and cached when a client joins a topic, so policies intentionally rely on
-- authenticated topic access (friendship / voice-channel visibility), not per-message payload data.
alter table realtime.messages enable row level security;
drop policy if exists "vessel realtime receive" on realtime.messages;
drop policy if exists "vessel realtime send" on realtime.messages;

create policy "vessel realtime receive"
on realtime.messages
for select
to authenticated
using (
  (
    realtime.messages.extension = 'broadcast'
    and realtime.topic() = ('vessel-call-inbox-' || (select auth.uid())::text)
  )
  or (
    realtime.messages.extension = 'broadcast'
    and exists (
      select 1
      from public.friendships f
      where f.user_id = (select auth.uid())
        and realtime.topic() = (
          'vessel-call-'
          || least((select auth.uid())::text, f.friend_id::text)
          || '-'
          || greatest((select auth.uid())::text, f.friend_id::text)
        )
    )
  )
  or (
    realtime.messages.extension in ('broadcast','presence')
    and exists (
      select 1
      from public.channels c
      where c.kind = 'voice'
        and realtime.topic() = ('voice-' || c.id::text)
    )
  )
);

create policy "vessel realtime send"
on realtime.messages
for insert
to authenticated
with check (
  (
    realtime.messages.extension = 'broadcast'
    and exists (
      select 1
      from public.friendships f
      where f.user_id = (select auth.uid())
        and realtime.topic() = ('vessel-call-inbox-' || f.friend_id::text)
    )
  )
  or (
    realtime.messages.extension = 'broadcast'
    and exists (
      select 1
      from public.friendships f
      where f.user_id = (select auth.uid())
        and realtime.topic() = (
          'vessel-call-'
          || least((select auth.uid())::text, f.friend_id::text)
          || '-'
          || greatest((select auth.uid())::text, f.friend_id::text)
        )
    )
  )
  or (
    realtime.messages.extension in ('broadcast','presence')
    and exists (
      select 1
      from public.channels c
      where c.kind = 'voice'
        and realtime.topic() = ('voice-' || c.id::text)
    )
  )
);

'''
    schema = schema.replace(anchor, anchor + block, 1)
    schema_changed = True

required_main = [
    "supabase.channel(`voice-${targetChannelId}`,{config:{private:true,presence:{key:user.id}}})",
    "supabase.channel(callInboxName(peerId),{config:{private:true}})",
    "supabase.channel(name,{config:{private:true}})",
]
for marker in required_main:
    if marker not in main:
        raise SystemExit(f'missing secured Realtime client marker: {marker}')
for marker in [
    schema_marker,
    'vessel realtime receive',
    'vessel realtime send',
    "realtime.topic() = ('vessel-call-inbox-' || f.friend_id::text)",
    "realtime.messages.extension in ('broadcast','presence')",
]:
    if marker not in schema:
        raise SystemExit(f'missing secured Realtime schema marker: {marker}')

if main_changed:
    main_path.write_text(main, encoding='utf-8')
if schema_changed:
    schema_path.write_text(schema, encoding='utf-8')
if main_changed or schema_changed:
    print('Applied private Realtime authorization for Vessel voice and calls')
else:
    print('Private Realtime authorization already applied; nothing to change')
