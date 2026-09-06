from pathlib import Path

path = Path('src/main.js')
text = path.read_text(encoding='utf-8')
changed = False

def replace_once(old, new, label):
    global text, changed
    if new in text:
        return
    if old not in text:
        raise SystemExit(f'{label}: expected source or guarded form not found')
    text = text.replace(old, new, 1)
    changed = True

replacements = [
    (
        "supabase.channel(`vessel-dm-${user.id}`).on('postgres_changes',{event:'INSERT',schema:'public',table:'direct_messages'},payload=>{\n      const row=payload.new;",
        "supabase.channel(`vessel-dm-${user.id}`).on('postgres_changes',{event:'INSERT',schema:'public',table:'direct_messages'},payload=>{\n      if(savedUser?.id!==user.id)return;\n      const row=payload.new;",
        'direct-message realtime session guard',
    ),
    (
        "supabase.channel(`vessel-friends-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'friend_requests',filter:`receiver_id=eq.${user.id}`},()=>{window.__vesselSocialLoaded=false;syncSocial(user);}).subscribe(),",
        "supabase.channel(`vessel-friends-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'friend_requests',filter:`receiver_id=eq.${user.id}`},()=>{if(savedUser?.id!==user.id)return;window.__vesselSocialLoaded=false;syncSocial(user);}).subscribe(),",
        'incoming friend-request realtime session guard',
    ),
    (
        "supabase.channel(`vessel-friend-requests-out-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'friend_requests',filter:`sender_id=eq.${user.id}`},()=>{window.__vesselSocialLoaded=false;syncSocial(user);}).subscribe(),",
        "supabase.channel(`vessel-friend-requests-out-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'friend_requests',filter:`sender_id=eq.${user.id}`},()=>{if(savedUser?.id!==user.id)return;window.__vesselSocialLoaded=false;syncSocial(user);}).subscribe(),",
        'outgoing friend-request realtime session guard',
    ),
    (
        "supabase.channel(`vessel-friendships-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'friendships',filter:`user_id=eq.${user.id}`},async payload=>{\n      const row=payload.new?.friend_id?payload.new:payload.old;",
        "supabase.channel(`vessel-friendships-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'friendships',filter:`user_id=eq.${user.id}`},async payload=>{\n      if(savedUser?.id!==user.id)return;\n      const row=payload.new?.friend_id?payload.new:payload.old;",
        'friendship realtime session guard',
    ),
    (
        "supabase.channel(`vessel-memberships-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'server_members'},async payload=>{\n      const row=payload.new?.server_id?payload.new:payload.old;",
        "supabase.channel(`vessel-memberships-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'server_members'},async payload=>{\n      if(savedUser?.id!==user.id)return;\n      const row=payload.new?.server_id?payload.new:payload.old;",
        'membership realtime session guard',
    ),
    (
        "supabase.channel(`vessel-channels-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'channels'},async payload=>{\n      const row=payload.new?.server_id?payload.new:payload.old;",
        "supabase.channel(`vessel-channels-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'channels'},async payload=>{\n      if(savedUser?.id!==user.id)return;\n      const row=payload.new?.server_id?payload.new:payload.old;",
        'channel realtime session guard',
    ),
    (
        "supabase.channel(`vessel-channel-messages-${user.id}`).on('postgres_changes',{event:'INSERT',schema:'public',table:'messages'},payload=>{\n      if(payload.new.channel_id===activeChannelId",
        "supabase.channel(`vessel-channel-messages-${user.id}`).on('postgres_changes',{event:'INSERT',schema:'public',table:'messages'},payload=>{\n      if(savedUser?.id!==user.id)return;\n      if(payload.new.channel_id===activeChannelId",
        'channel-message realtime session guard',
    ),
    (
        "supabase.channel(`vessel-profiles-${user.id}`).on('postgres_changes',{event:'UPDATE',schema:'public',table:'profiles'},payload=>{\n      const row=payload.new;",
        "supabase.channel(`vessel-profiles-${user.id}`).on('postgres_changes',{event:'UPDATE',schema:'public',table:'profiles'},payload=>{\n      if(savedUser?.id!==user.id)return;\n      const row=payload.new;",
        'profile realtime session guard',
    ),
    (
        "supabase.channel(`vessel-servers-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'servers'},async payload=>{\n      const row=payload.new?.id?payload.new:payload.old;",
        "supabase.channel(`vessel-servers-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'servers'},async payload=>{\n      if(savedUser?.id!==user.id)return;\n      const row=payload.new?.id?payload.new:payload.old;",
        'server realtime session guard',
    ),
    (
        ".on('postgres_changes',{event:'INSERT',schema:'public',table:'notifications',filter:`user_id=eq.${user.id}`},payload=>{\n        const row=payload.new;",
        ".on('postgres_changes',{event:'INSERT',schema:'public',table:'notifications',filter:`user_id=eq.${user.id}`},payload=>{\n        if(savedUser?.id!==user.id)return;\n        const row=payload.new;",
        'notification insert realtime session guard',
    ),
    (
        ".on('postgres_changes',{event:'UPDATE',schema:'public',table:'notifications',filter:`user_id=eq.${user.id}`},payload=>{\n        const row=payload.new;",
        ".on('postgres_changes',{event:'UPDATE',schema:'public',table:'notifications',filter:`user_id=eq.${user.id}`},payload=>{\n        if(savedUser?.id!==user.id)return;\n        const row=payload.new;",
        'notification update realtime session guard',
    ),
]

for old, new, label in replacements:
    replace_once(old, new, label)

required = [
    "vessel-dm-${user.id}`).on('postgres_changes'",
    "vessel-memberships-${user.id}`).on('postgres_changes'",
    "vessel-channels-${user.id}`).on('postgres_changes'",
    "vessel-servers-${user.id}`).on('postgres_changes'",
    "if(savedUser?.id!==user.id)return;",
]
for marker in required:
    if marker not in text:
        raise SystemExit(f'missing realtime session isolation marker: {marker}')

if changed:
    path.write_text(text, encoding='utf-8')
    print('Applied authenticated Realtime session isolation')
else:
    print('Authenticated Realtime session isolation already applied; nothing to change')
