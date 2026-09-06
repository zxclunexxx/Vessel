from pathlib import Path

path = Path('src/main.js')
text = path.read_text(encoding='utf-8')
changed = False


def replace_once(old, new, label):
    global text, changed
    if new in text:
        return
    if old not in text:
        raise SystemExit(f'{label} anchor not found')
    text = text.replace(old, new, 1)
    changed = True


replace_once(
    """function subscribeChannel(channel) {
  if (channel.__subscribed) return Promise.resolve(channel);
  if (channel.__subscribePromise) return channel.__subscribePromise;
  channel.__subscribePromise = new Promise((resolve, reject) => {
    let settled = false;
    const timer = setTimeout(() => {
      if (!settled) { settled = true; channel.__subscribed = false; reject(new Error('Realtime channel timeout')); }
    }, 10000);
    channel.subscribe(status => {
      if (status === 'SUBSCRIBED') {
        channel.__subscribed = true;
        if (!settled) {
          settled = true;
          clearTimeout(timer);
          resolve(channel);
        }
        return;
      }
      if (['CHANNEL_ERROR', 'TIMED_OUT', 'CLOSED'].includes(status)) {
        channel.__subscribed = false;
        if (!settled) {
          settled = true;
          clearTimeout(timer);
          reject(new Error(`Realtime channel ${status}`));
        }
      }
    });
  }).finally(() => { channel.__subscribePromise = null; });
  return channel.__subscribePromise;
}
""",
    """function subscribeChannel(channel,onDisconnect=null) {
  if (channel.__subscribed) return Promise.resolve(channel);
  if (channel.__subscribePromise) return channel.__subscribePromise;
  channel.__subscribePromise = new Promise((resolve, reject) => {
    let settled = false;
    let everSubscribed = false;
    let disconnectNotified = false;
    const timer = setTimeout(() => {
      if (!settled) { settled = true; channel.__subscribed = false; reject(new Error('Realtime channel timeout')); }
    }, 10000);
    channel.subscribe(status => {
      if (status === 'SUBSCRIBED') {
        channel.__subscribed = true;
        everSubscribed = true;
        disconnectNotified = false;
        if (!settled) {
          settled = true;
          clearTimeout(timer);
          resolve(channel);
        }
        return;
      }
      if (['CHANNEL_ERROR', 'TIMED_OUT', 'CLOSED'].includes(status)) {
        channel.__subscribed = false;
        if (!settled) {
          settled = true;
          clearTimeout(timer);
          reject(new Error(`Realtime channel ${status}`));
          return;
        }
        if (everSubscribed && !disconnectNotified && typeof onDisconnect === 'function') {
          disconnectNotified = true;
          Promise.resolve().then(() => onDisconnect(status)).catch(error => console.warn('Realtime disconnect handler failed', error));
        }
      }
    });
  }).finally(() => { channel.__subscribePromise = null; });
  return channel.__subscribePromise;
}
""",
    'realtime established disconnect callback',
)

replace_once(
    """  if (callInboxChannel?.__roomName === name && callInboxChannel.__subscribed) return callInboxChannel;
  if (callInboxChannel) await supabase.removeChannel(callInboxChannel);
  callInboxChannel = supabase.channel(name);
  callInboxChannel.__roomName = name;
  callInboxChannel.on('broadcast', {event:'call'}, async ({payload}) => {
""",
    """  if (callInboxChannel?.__roomName === name && callInboxChannel.__subscribed) return callInboxChannel;
  const previousInbox=callInboxChannel;
  callInboxChannel=null;
  if (previousInbox) await supabase.removeChannel(previousInbox).catch(()=>{});
  const inbox=supabase.channel(name);
  callInboxChannel=inbox;
  inbox.__roomName = name;
  inbox.on('broadcast', {event:'call'}, async ({payload}) => {
""",
    'call inbox replacement safety',
)

replace_once(
    """  try {
    await subscribeChannel(callInboxChannel);
  } catch (error) {
    console.warn('Call inbox failed', error);
    const failedChannel=callInboxChannel;
    callInboxChannel=null;
    if(failedChannel&&supabase){try{await supabase.removeChannel(failedChannel);}catch{}}
    setTimeout(()=>{if(savedUser?.id===user.id)ensureCallInbox(savedUser).catch(retryError=>console.warn('Call inbox retry failed',retryError));},3000);
    return null;
  }
  return callInboxChannel;
}
""",
    """  try {
    await subscribeChannel(inbox,status=>{
      if(callInboxChannel!==inbox||savedUser?.id!==user.id)return;
      console.warn(`Call inbox ${status}; reconnecting`);
      callInboxChannel=null;
      if(supabase)void supabase.removeChannel(inbox).catch(error=>console.warn('Call inbox cleanup failed',error));
      setTimeout(()=>{
        if(savedUser?.id===user.id&&!callInboxChannel)ensureCallInbox(savedUser).catch(retryError=>console.warn('Call inbox reconnect failed',retryError));
      },1000);
    });
  } catch (error) {
    console.warn('Call inbox failed', error);
    if(callInboxChannel===inbox)callInboxChannel=null;
    if(supabase){try{await supabase.removeChannel(inbox);}catch{}}
    setTimeout(()=>{if(savedUser?.id===user.id&&!callInboxChannel)ensureCallInbox(savedUser).catch(retryError=>console.warn('Call inbox retry failed',retryError));},3000);
    return null;
  }
  return callInboxChannel===inbox?inbox:callInboxChannel;
}
""",
    'call inbox established reconnect',
)

replace_once(
    """  if(callChannel?.__roomName===name && callChannel.__subscribed) return callChannel;
  if(callChannel) await supabase.removeChannel(callChannel);
  callChannel=supabase.channel(name);
  callChannel.__roomName=name;
  callChannel.on('broadcast',{event:'signal'},async({payload})=>{
    if(!payload || payload.to!==user.id || payload.from!==callPeer) return;
    await handleCallSignal(user,payload.from,payload.signal,payload.video).catch(error=>{console.warn('Call signal failed',error);endCall(false);});
  });
  await subscribeChannel(callChannel);
  return callChannel;
}
""",
    """  if(callChannel?.__roomName===name && callChannel.__subscribed) return callChannel;
  const previousCallChannel=callChannel;
  callChannel=null;
  if(previousCallChannel)await supabase.removeChannel(previousCallChannel).catch(()=>{});
  const room=supabase.channel(name);
  callChannel=room;
  room.__roomName=name;
  room.on('broadcast',{event:'signal'},async({payload})=>{
    if(!payload || payload.to!==user.id || payload.from!==callPeer) return;
    await handleCallSignal(user,payload.from,payload.signal,payload.video).catch(error=>{console.warn('Call signal failed',error);endCall(false);});
  });
  try{
    await subscribeChannel(room,status=>{
      if(callChannel!==room||savedUser?.id!==user.id||callPeer!==peerId)return;
      console.warn(`Call signaling ${status}; reconnecting`);
      callChannel=null;
      if(supabase)void supabase.removeChannel(room).catch(error=>console.warn('Call signaling cleanup failed',error));
      setTimeout(()=>{
        if(savedUser?.id===user.id&&callPeer===peerId&&callConnection&&!callChannel){
          ensureCallChannel(savedUser,peerId).catch(error=>console.warn('Call signaling reconnect failed',error));
        }
      },1000);
    });
  }catch(error){
    if(callChannel===room)callChannel=null;
    if(supabase)await supabase.removeChannel(room).catch(()=>{});
    throw error;
  }
  return room;
}
""",
    'active call signaling reconnect',
)

# The up-front voiceStream branch now handles both toggling the current room and leaving
# a previous room before switching. Remove the old duplicate branch.
dead_voice = "  if(voiceStream && voiceChannelId!==activeChannelId){await leaveVoiceRoom();}\n"
if dead_voice in text:
    text = text.replace(dead_voice, '', 1)
    changed = True

for marker in [
    'function subscribeChannel(channel,onDisconnect=null)',
    'Call inbox ${status}; reconnecting',
    'Call signaling ${status}; reconnecting',
    'ensureCallInbox(savedUser).catch(retryError=>console.warn(\'Call inbox reconnect failed\'',
    'ensureCallChannel(savedUser,peerId).catch(error=>console.warn(\'Call signaling reconnect failed\'',
]:
    if marker not in text:
        raise SystemExit(f'missing call reconnect marker: {marker}')

if dead_voice in text:
    raise SystemExit('stale duplicate voice-switch cleanup remains')

if changed:
    path.write_text(text, encoding='utf-8')
    print('Applied call Realtime reconnect recovery and voice-switch cleanup')
else:
    print('Call Realtime reconnect recovery already applied; nothing to change')
