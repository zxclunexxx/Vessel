from pathlib import Path

main = Path('src/main.js').read_text(encoding='utf-8')
schema = Path('server/schema.sql').read_text(encoding='utf-8')

required_main = [
    "supabase.channel(`voice-${targetChannelId}`,{config:{private:true,presence:{key:user.id}}})",
    "supabase.channel(callInboxName(peerId),{config:{private:true}})",
    "const inbox=supabase.channel(name,{config:{private:true}});",
    "const room=supabase.channel(name,{config:{private:true}});",
]
for marker in required_main:
    if marker not in main:
        raise SystemExit(f'Missing private Realtime client protection: {marker}')

# Call and voice broadcast payloads must continue to bind the apparent sender to the
# authenticated user. The database policy is the authoritative anti-spoofing boundary.
required_schema = [
    'create policy "vessel realtime receive"',
    'create policy "vessel realtime send"',
    "realtime.messages.extension = 'broadcast'",
    "realtime.messages.event = 'call'",
    "realtime.messages.event = 'signal'",
    "realtime.messages.event = 'voice-signal'",
    "(realtime.messages.payload ->> 'from') = (select auth.uid())::text",
    "realtime.topic() = ('vessel-call-inbox-' || (select auth.uid())::text)",
    "realtime.topic() = ('voice-' || c.id::text)",
]
for marker in required_schema:
    if marker not in schema:
        raise SystemExit(f'Missing private Realtime RLS protection: {marker}')

# Sending into another user's inbox must require a current friendship and a matching target.
inbox_send = schema.find("realtime.messages.event = 'call'")
room_send = schema.find("realtime.messages.event = 'signal'")
if inbox_send < 0 or room_send < 0 or inbox_send > room_send:
    raise SystemExit('Call inbox policy block is missing or malformed')
inbox_block = schema[inbox_send:room_send]
for marker in [
    'from public.friendships f',
    "realtime.topic() = ('vessel-call-inbox-' || f.friend_id::text)",
    "(realtime.messages.payload ->> 'to') = f.friend_id::text",
]:
    if marker not in inbox_block:
        raise SystemExit(f'Call inbox anti-spoofing policy missing: {marker}')

print('Vessel private Realtime security smoke check passed')
