from pathlib import Path

path = Path('src/main.js')
text = path.read_text(encoding='utf-8')
changed = False

VOICE_CAPTURE_MARKERS = [
    "voiceServerId=getActiveServer()?.dbId||null;",
    "voiceServerId=targetServerId;",
]
LIFECYCLE_MARKERS = [
    'let voiceServerId = null;',
    "payload.eventType==='DELETE'&&voiceStream&&voiceServerId===row.server_id",
    "payload.eventType==='DELETE'&&voiceStream&&row?.id===voiceChannelId",
    'if(voiceStream&&voiceServerId===server.dbId)await leaveVoiceRoom();',
]


def hardening_complete():
    return all(marker in text for marker in LIFECYCLE_MARKERS) and any(marker in text for marker in VOICE_CAPTURE_MARKERS)


# Newer reconnect/switch hardening captures the target server before joining voice
# and therefore uses targetServerId instead of re-reading the currently active server.
# Both forms satisfy this older lifecycle migration. Avoid replaying stale anchors when
# a later patch has already evolved the same code path.
if hardening_complete():
    print('Vessel voice lifecycle hardening already applied; nothing to change')
    raise SystemExit(0)


def replace_once(old, new, label, already_markers=()):
    global text, changed
    if new in text or any(marker in text for marker in already_markers):
        print(f'{label}: already applied')
        return
    if old not in text:
        raise SystemExit(f'{label} anchor not found')
    text = text.replace(old, new, 1)
    changed = True


# Remember which server owns the currently connected voice room. The UI can move to
# another server while the user stays in voice, so activeServerId is not sufficient.
replace_once(
    "let voiceChannelId = null;\nlet voiceParticipants = [];",
    "let voiceChannelId = null;\nlet voiceServerId = null;\nlet voiceParticipants = [];",
    'voice server state',
)

# Joining a voice channel captures its owning server at the same time as its channel id.
# Later reconnect hardening legitimately evolved this to targetServerId.
replace_once(
    "    voiceChannelId=targetChannelId;\n    room=supabase.channel(`voice-${targetChannelId}`,{config:{presence:{key:user.id}}});",
    "    voiceChannelId=targetChannelId;\n    voiceServerId=getActiveServer()?.dbId||null;\n    room=supabase.channel(`voice-${targetChannelId}`,{config:{presence:{key:user.id}}});",
    'voice server capture',
    already_markers=("voiceServerId=targetServerId;",),
)

# Leaving voice must clear both channel and server ownership state.
replace_once(
    "  voiceParticipants=[];voiceChannelId=null;\n  if(room&&supabase){try{await supabase.removeChannel(room);}catch{}}",
    "  voiceParticipants=[];voiceChannelId=null;voiceServerId=null;\n  if(room&&supabase){try{await supabase.removeChannel(room);}catch{}}",
    'voice server clear',
)

# Auth/session reset must not retain stale voice ownership either.
replace_once(
    "  voiceParticipants=[];\n  voiceChannelId=null;\n  incomingCall=null;",
    "  voiceParticipants=[];\n  voiceChannelId=null;\n  voiceServerId=null;\n  incomingCall=null;",
    'auth voice server reset',
)

# If this user loses membership (kick, leave, cascading server deletion), disconnect any
# voice room owned by that server before refreshing the remaining server list.
membership_old = """    supabase.channel(`vessel-memberships-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'server_members'},payload=>{
      const row=payload.new?.server_id?payload.new:payload.old;
      if(!row)return;
      if(row.user_id===user.id){
        window.__vesselServersLoaded=false;
        syncSupabaseServers(user).then(()=>{
          const active=getActiveServer();
          serverMembers=[];window.__vesselMembersServerId=null;
          if(active?.dbId){active.__channelsLoaded=false;syncSupabaseChannels(active);syncServerMembers(user,active);}else render();
        });
      }else{
        const active=getActiveServer();
        if(active?.dbId===row.server_id){window.__vesselMembersServerId=null;serverMembers=[];syncServerMembers(user,active);}
      }
    }).subscribe(),"""
membership_new = """    supabase.channel(`vessel-memberships-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'server_members'},async payload=>{
      const row=payload.new?.server_id?payload.new:payload.old;
      if(!row)return;
      if(row.user_id===user.id){
        if(payload.eventType==='DELETE'&&voiceStream&&voiceServerId===row.server_id)await leaveVoiceRoom();
        window.__vesselServersLoaded=false;
        syncSupabaseServers(user).then(()=>{
          const active=getActiveServer();
          serverMembers=[];window.__vesselMembersServerId=null;
          if(active?.dbId){active.__channelsLoaded=false;syncSupabaseChannels(active);syncServerMembers(user,active);}else render();
        });
      }else{
        const active=getActiveServer();
        if(active?.dbId===row.server_id){window.__vesselMembersServerId=null;serverMembers=[];syncServerMembers(user,active);}
      }
    }).subscribe(),"""
replace_once(membership_old, membership_new, 'membership voice disconnect')

# If an owner deletes the voice channel remotely while a member is connected, stop media and
# close peer connections immediately instead of leaving a ghost room alive in the client.
channel_old = """    supabase.channel(`vessel-channels-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'channels'},payload=>{
      const row=payload.new?.server_id?payload.new:payload.old;
      const active=getActiveServer();
      if(row?.server_id&&active?.dbId===row.server_id){active.__channelsLoaded=false;syncSupabaseChannels(active);}
    }).subscribe(),"""
channel_new = """    supabase.channel(`vessel-channels-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'channels'},async payload=>{
      const row=payload.new?.server_id?payload.new:payload.old;
      if(payload.eventType==='DELETE'&&voiceStream&&row?.id===voiceChannelId)await leaveVoiceRoom();
      const active=getActiveServer();
      if(row?.server_id&&active?.dbId===row.server_id){active.__channelsLoaded=false;syncSupabaseChannels(active);}
    }).subscribe(),"""
replace_once(channel_old, channel_new, 'deleted voice channel disconnect')

# Local leave/delete should disconnect before the membership/channel rows disappear.
replace_once(
    "        if(!await vesselConfirm(`Удалить сервер «${server.name}»?`,'Каналы и сообщения этого сервера тоже будут удалены.'))return;\n        const {error}=await supabase.from('servers').delete().eq('id',server.dbId).eq('owner_id',user.id);",
    "        if(!await vesselConfirm(`Удалить сервер «${server.name}»?`,'Каналы и сообщения этого сервера тоже будут удалены.'))return;\n        if(voiceStream&&voiceServerId===server.dbId)await leaveVoiceRoom();\n        const {error}=await supabase.from('servers').delete().eq('id',server.dbId).eq('owner_id',user.id);",
    'local server delete voice disconnect',
)
replace_once(
    "    if(await vesselConfirm(`Выйти из сервера «${server.name}»?`)){\n      const {error}=await supabase.from('server_members').delete().eq('server_id',server.dbId).eq('user_id',user.id);",
    "    if(await vesselConfirm(`Выйти из сервера «${server.name}»?`)){\n      if(voiceStream&&voiceServerId===server.dbId)await leaveVoiceRoom();\n      const {error}=await supabase.from('server_members').delete().eq('server_id',server.dbId).eq('user_id',user.id);",
    'local server leave voice disconnect',
)

if not hardening_complete():
    missing=[marker for marker in LIFECYCLE_MARKERS if marker not in text]
    if not any(marker in text for marker in VOICE_CAPTURE_MARKERS):
        missing.append('voice server capture')
    raise SystemExit(f"missing voice lifecycle hardening marker(s): {', '.join(missing)}")

if changed:
    path.write_text(text, encoding='utf-8')
    print('Applied Vessel voice membership/channel lifecycle hardening')
else:
    print('Vessel voice lifecycle hardening already applied; nothing to change')
