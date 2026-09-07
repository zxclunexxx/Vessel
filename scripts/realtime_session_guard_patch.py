from pathlib import Path

# Idempotent hardening for stale Realtime callbacks after auth account switches.
# Newer Vessel features may change event kinds or make callbacks async, so this patch
# validates the guard near each subscription instead of relying only on exact old text.
path = Path('src/main.js')
text = path.read_text(encoding='utf-8')
changed = False
GUARD = 'if(savedUser?.id!==user.id)return;'


def guard_present(anchor, window=700):
    start = text.find(anchor)
    if start < 0:
        return False
    return GUARD in text[start:start + window]


def replace_or_validate(old, new, label, anchor):
    global text, changed
    if guard_present(anchor):
        print(f'{label}: already applied in current realtime callback')
        return
    if new in text:
        print(f'{label}: already applied')
        return
    if old not in text:
        raise SystemExit(f'{label}: callback exists without a recognized session guard form')
    text = text.replace(old, new, 1)
    changed = True
    print(f'{label}: applied')


replacements = [
    (
        "supabase.channel(`vessel-dm-${user.id}`).on('postgres_changes',{event:'INSERT',schema:'public',table:'direct_messages'},payload=>{\n      const row=payload.new;",
        "supabase.channel(`vessel-dm-${user.id}`).on('postgres_changes',{event:'INSERT',schema:'public',table:'direct_messages'},payload=>{\n      if(savedUser?.id!==user.id)return;\n      const row=payload.new;",
        'direct-message realtime session guard',
        "supabase.channel(`vessel-dm-${user.id}`)",
    ),
    (
        "supabase.channel(`vessel-friends-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'friend_requests',filter:`receiver_id=eq.${user.id}`},()=>{window.__vesselSocialLoaded=false;syncSocial(user);}).subscribe(),",
        "supabase.channel(`vessel-friends-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'friend_requests',filter:`receiver_id=eq.${user.id}`},()=>{if(savedUser?.id!==user.id)return;window.__vesselSocialLoaded=false;syncSocial(user);}).subscribe(),",
        'incoming friend-request realtime session guard',
        "supabase.channel(`vessel-friends-${user.id}`)",
    ),
    (
        "supabase.channel(`vessel-friend-requests-out-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'friend_requests',filter:`sender_id=eq.${user.id}`},()=>{window.__vesselSocialLoaded=false;syncSocial(user);}).subscribe(),",
        "supabase.channel(`vessel-friend-requests-out-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'friend_requests',filter:`sender_id=eq.${user.id}`},()=>{if(savedUser?.id!==user.id)return;window.__vesselSocialLoaded=false;syncSocial(user);}).subscribe(),",
        'outgoing friend-request realtime session guard',
        "supabase.channel(`vessel-friend-requests-out-${user.id}`)",
    ),
    (
        "supabase.channel(`vessel-friendships-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'friendships',filter:`user_id=eq.${user.id}`},async payload=>{\n      const row=payload.new?.friend_id?payload.new:payload.old;",
        "supabase.channel(`vessel-friendships-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'friendships',filter:`user_id=eq.${user.id}`},async payload=>{\n      if(savedUser?.id!==user.id)return;\n      const row=payload.new?.friend_id?payload.new:payload.old;",
        'friendship realtime session guard',
        "supabase.channel(`vessel-friendships-${user.id}`)",
    ),
    (
        "supabase.channel(`vessel-memberships-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'server_members'},async payload=>{\n      const row=payload.new?.server_id?payload.new:payload.old;",
        "supabase.channel(`vessel-memberships-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'server_members'},async payload=>{\n      if(savedUser?.id!==user.id)return;\n      const row=payload.new?.server_id?payload.new:payload.old;",
        'membership realtime session guard',
        "supabase.channel(`vessel-memberships-${user.id}`)",
    ),
    (
        "supabase.channel(`vessel-channels-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'channels'},async payload=>{\n      const row=payload.new?.server_id?payload.new:payload.old;",
        "supabase.channel(`vessel-channels-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'channels'},async payload=>{\n      if(savedUser?.id!==user.id)return;\n      const row=payload.new?.server_id?payload.new:payload.old;",
        'channel realtime session guard',
        "supabase.channel(`vessel-channels-${user.id}`)",
    ),
    (
        "supabase.channel(`vessel-channel-messages-${user.id}`).on('postgres_changes',{event:'INSERT',schema:'public',table:'messages'},payload=>{\n      if(payload.new.channel_id===activeChannelId",
        "supabase.channel(`vessel-channel-messages-${user.id}`).on('postgres_changes',{event:'INSERT',schema:'public',table:'messages'},payload=>{\n      if(savedUser?.id!==user.id)return;\n      if(payload.new.channel_id===activeChannelId",
        'channel-message realtime session guard',
        "supabase.channel(`vessel-channel-messages-${user.id}`)",
    ),
    (
        "supabase.channel(`vessel-profiles-${user.id}`).on('postgres_changes',{event:'UPDATE',schema:'public',table:'profiles'},payload=>{\n      const row=payload.new;",
        "supabase.channel(`vessel-profiles-${user.id}`).on('postgres_changes',{event:'UPDATE',schema:'public',table:'profiles'},payload=>{\n      if(savedUser?.id!==user.id)return;\n      const row=payload.new;",
        'profile realtime session guard',
        "supabase.channel(`vessel-profiles-${user.id}`)",
    ),
    (
        "supabase.channel(`vessel-servers-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'servers'},async payload=>{\n      const row=payload.new?.id?payload.new:payload.old;",
        "supabase.channel(`vessel-servers-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'servers'},async payload=>{\n      if(savedUser?.id!==user.id)return;\n      const row=payload.new?.id?payload.new:payload.old;",
        'server realtime session guard',
        "supabase.channel(`vessel-servers-${user.id}`)",
    ),
    (
        ".on('postgres_changes',{event:'INSERT',schema:'public',table:'notifications',filter:`user_id=eq.${user.id}`},payload=>{\n        const row=payload.new;",
        ".on('postgres_changes',{event:'INSERT',schema:'public',table:'notifications',filter:`user_id=eq.${user.id}`},payload=>{\n        if(savedUser?.id!==user.id)return;\n        const row=payload.new;",
        'notification insert realtime session guard',
        ".on('postgres_changes',{event:'INSERT',schema:'public',table:'notifications',filter:`user_id=eq.${user.id}`}",
    ),
    (
        ".on('postgres_changes',{event:'UPDATE',schema:'public',table:'notifications',filter:`user_id=eq.${user.id}`},payload=>{\n        const row=payload.new;",
        ".on('postgres_changes',{event:'UPDATE',schema:'public',table:'notifications',filter:`user_id=eq.${user.id}`},payload=>{\n        if(savedUser?.id!==user.id)return;\n        const row=payload.new;",
        'notification update realtime session guard',
        ".on('postgres_changes',{event:'UPDATE',schema:'public',table:'notifications',filter:`user_id=eq.${user.id}`}",
    ),
]

for old, new, label, anchor in replacements:
    if anchor not in text:
        raise SystemExit(f'{label}: realtime subscription anchor missing')
    replace_or_validate(old, new, label, anchor)

required_anchors = [
    "supabase.channel(`vessel-dm-${user.id}`)",
    "supabase.channel(`vessel-memberships-${user.id}`)",
    "supabase.channel(`vessel-channels-${user.id}`)",
    "supabase.channel(`vessel-servers-${user.id}`)",
]
for anchor in required_anchors:
    if not guard_present(anchor):
        raise SystemExit(f'missing realtime session guard near: {anchor}')

if changed:
    path.write_text(text, encoding='utf-8')
    print('Applied authenticated Realtime session isolation')
else:
    print('Authenticated Realtime session isolation already applied; nothing to change')
