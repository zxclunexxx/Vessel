from pathlib import Path

schema_path = Path('server/schema.sql')
schema = schema_path.read_text(encoding='utf-8')

old_comment = "-- Call/voice WebRTC signaling uses private Supabase Realtime topics. Read access is scoped\n-- to the current inbox, the current friendship pair, or an authorized voice channel; writes\n-- additionally bind broadcast payload.from to auth.uid() to prevent sender spoofing."
new_comment = "-- Call/voice WebRTC signaling uses private Supabase Realtime topics. Realtime Authorization\n-- is calculated and cached when a client joins a topic, so policies intentionally rely on\n-- authenticated topic access (friendship / voice-channel visibility), not per-message payload data."
if old_comment in schema:
    schema = schema.replace(old_comment, new_comment, 1)

start = schema.find('create policy "vessel realtime send"')
end_marker = '\n\n-- Column-level profile privacy'
end = schema.find(end_marker, start)
if start < 0 or end < 0:
    raise SystemExit('Realtime send policy block not found')

new_policy = '''create policy "vessel realtime send"
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
);'''

current = schema[start:end].rstrip()
if current != new_policy:
    schema = schema[:start] + new_policy + schema[end:]
    schema_path.write_text(schema, encoding='utf-8')
    print('Aligned Realtime RLS with join-time authorization semantics')
else:
    if old_comment in schema:
        schema_path.write_text(schema, encoding='utf-8')
    print('Realtime RLS already uses join-time authorization semantics; nothing to change')
