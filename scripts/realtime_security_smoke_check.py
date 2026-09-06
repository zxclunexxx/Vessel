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

required_schema = [
    'create policy "vessel realtime receive"',
    'create policy "vessel realtime send"',
    "realtime.topic() = ('vessel-call-inbox-' || (select auth.uid())::text)",
    "realtime.topic() = ('vessel-call-inbox-' || f.friend_id::text)",
    "'vessel-call-'",
    'from public.friendships f',
    "realtime.messages.extension in ('broadcast','presence')",
    "realtime.topic() = ('voice-' || c.id::text)",
    "c.kind = 'voice'",
]
for marker in required_schema:
    if marker not in schema:
        raise SystemExit(f'Missing private Realtime topic authorization: {marker}')

marker = '-- Vessel private Realtime authorization -----------------------------------------'
start = schema.find(marker)
end = schema.find('-- Column-level profile privacy', start)
if start < 0 or end < 0:
    raise SystemExit('Private Realtime policy block is missing')
policy_block = schema[start:end]

# Supabase Realtime Authorization is evaluated and cached when a private topic is joined;
# do not regress to pretending RLS validates individual broadcast payloads/events.
for stale in [
    'realtime.messages.event =',
    "realtime.messages.payload ->> 'from'",
    "realtime.messages.payload ->> 'to'",
]:
    if stale in policy_block:
        raise SystemExit(f'Realtime RLS incorrectly depends on per-message data: {stale}')

if 'calculated and cached when a client joins a topic' not in policy_block:
    raise SystemExit('Realtime schema must document join-time cached authorization semantics')

# Inbox publishing must still be scoped to a current friend; room publishing must be scoped
# to a current friendship pair. Sender identity itself is not inferred from broadcast payload RLS.
send_start = policy_block.find('create policy "vessel realtime send"')
if send_start < 0:
    raise SystemExit('Realtime send policy missing')
send_block = policy_block[send_start:]
for required in [
    'from public.friendships f',
    "realtime.topic() = ('vessel-call-inbox-' || f.friend_id::text)",
    "least((select auth.uid())::text, f.friend_id::text)",
    "greatest((select auth.uid())::text, f.friend_id::text)",
]:
    if required not in send_block:
        raise SystemExit(f'Realtime send topic authorization missing: {required}')

print('Vessel private Realtime join-authorization smoke check passed')
