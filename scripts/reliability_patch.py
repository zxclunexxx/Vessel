from pathlib import Path

main_path = Path('src/main.js')
schema_path = Path('server/schema.sql')
text = main_path.read_text(encoding='utf-8')
schema = schema_path.read_text(encoding='utf-8')
changed = False


def replace_once(old, new, label):
    global text, changed
    if new in text:
        return
    if old not in text:
        raise SystemExit(f'{label} anchor not found')
    text = text.replace(old, new, 1)
    changed = True


def replace_schema_once(old, new, label):
    global schema, changed
    if new in schema:
        return
    if old not in schema:
        raise SystemExit(f'{label} schema anchor not found')
    schema = schema.replace(old, new, 1)
    changed = True


# Keep the bootstrap snapshot aligned with production friend-request lifecycle policies.
friend_policies_old = """create policy \"friend requests participants can read\" on public.friend_requests for select to authenticated using(sender_id=(select auth.uid()) or receiver_id=(select auth.uid()));
create policy \"users can send friend requests\" on public.friend_requests for insert to authenticated with check(sender_id=(select auth.uid()) and sender_id<>receiver_id);
create policy \"receivers can answer friend requests\" on public.friend_requests for update to authenticated using(receiver_id=(select auth.uid())) with check(receiver_id=(select auth.uid()) and status in ('accepted','declined'));
"""
friend_policies_new = """create policy \"friend requests participants can read\" on public.friend_requests for select to authenticated using(sender_id=(select auth.uid()) or receiver_id=(select auth.uid()));
create policy \"users can send friend requests\" on public.friend_requests for insert to authenticated with check(
  sender_id=(select auth.uid())
  and sender_id<>receiver_id
  and not exists(select 1 from public.friendships f where f.user_id=(select auth.uid()) and f.friend_id=friend_requests.receiver_id)
);
create policy \"receivers can answer friend requests\" on public.friend_requests for update to authenticated using(receiver_id=(select auth.uid())) with check(receiver_id=(select auth.uid()) and status in ('accepted','declined'));
create policy \"senders can retry terminal friend requests\" on public.friend_requests for update to authenticated
using(sender_id=(select auth.uid()) and status in ('accepted','declined','cancelled'))
with check(
  sender_id=(select auth.uid())
  and sender_id<>receiver_id
  and status='pending'
  and not exists(select 1 from public.friendships f where f.user_id=(select auth.uid()) and f.friend_id=friend_requests.receiver_id)
);
create policy \"senders can cancel pending friend requests\" on public.friend_requests for delete to authenticated
using(sender_id=(select auth.uid()) and status='pending');
"""
replace_schema_once(friend_policies_old, friend_policies_new, 'friend request lifecycle policies')


# Realtime channels must not remain marked as healthy after an error/timeout/close.
subscribe_old = """function subscribeChannel(channel) {
  if (channel.__subscribed) return Promise.resolve(channel);
  return new Promise((resolve, reject) => {
    let settled = false;
    const timer = setTimeout(() => {
      if (!settled) { settled = true; reject(new Error('Realtime channel timeout')); }
    }, 10000);
    channel.subscribe(status => {
      if (settled) return;
      if (status === 'SUBSCRIBED') {
        settled = true;
        clearTimeout(timer);
        channel.__subscribed = true;
        resolve(channel);
      } else if (['CHANNEL_ERROR', 'TIMED_OUT', 'CLOSED'].includes(status)) {
        settled = true;
        clearTimeout(timer);
        reject(new Error(`Realtime channel ${status}`));
      }
    });
  });
}
"""
subscribe_new = """function subscribeChannel(channel) {
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
"""
replace_once(subscribe_old, subscribe_new, 'realtime subscription state')


# If the inbox subscription fails, clear the dead channel and retry instead of caching it forever.
inbox_old = """  try { await subscribeChannel(callInboxChannel); } catch (error) { console.warn('Call inbox failed', error); }
  return callInboxChannel;
}
"""
inbox_new = """  try {
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
"""
replace_once(inbox_old, inbox_new, 'call inbox recovery')


# A failed Broadcast send is not a delivered WebRTC signal.
signal_old = """async function sendCallSignal(user,peerId,signal,video) {
  const room=await ensureCallChannel(user,peerId); if(!room)return;
  await room.send({type:'broadcast',event:'signal',payload:{from:user.id,to:peerId,signal,video:!!video}});
}
"""
signal_new = """async function sendCallSignal(user,peerId,signal,video) {
  const room=await ensureCallChannel(user,peerId);
  if(!room)throw new Error('CALL_SIGNAL_CHANNEL_UNAVAILABLE');
  const result=await room.send({type:'broadcast',event:'signal',payload:{from:user.id,to:peerId,signal,video:!!video}});
  if(result!=='ok')throw new Error(`CALL_SIGNAL_${String(result||'FAILED').toUpperCase()}`);
}
"""
replace_once(signal_old, signal_new, 'call signal delivery check')


# Ignore CLOSED callbacks from an intentional voice-room leave and allow Realtime to
# re-track presence after a transient reconnect.
leave_voice_old = """async function leaveVoiceRoom(){
  voiceStream?.getTracks().forEach(track=>track.stop());voiceStream=null;
  for(const peerId of [...voicePeers.keys()])removeVoicePeer(peerId);
  voiceParticipants=[];voiceChannelId=null;
  if(voiceRoom&&supabase){try{await supabase.removeChannel(voiceRoom);}catch{}}
  voiceRoom=null;
  render();
}
"""
leave_voice_new = """async function leaveVoiceRoom(){
  const room=voiceRoom;
  voiceRoom=null;
  voiceStream?.getTracks().forEach(track=>track.stop());voiceStream=null;
  for(const peerId of [...voicePeers.keys()])removeVoicePeer(peerId);
  voiceParticipants=[];voiceChannelId=null;
  if(room&&supabase){try{await supabase.removeChannel(room);}catch{}}
  render();
}
"""
replace_once(leave_voice_old, leave_voice_new, 'intentional voice leave state')

voice_subscribe_old = """      room.subscribe(async status=>{
        if(settled||room!==voiceRoom)return;
        if(status==='SUBSCRIBED'){
          settled=true;clearTimeout(timer);
          try{await room.track({user_id:user.id,name:user.name});await syncVoicePresence(user);resolve();}
          catch(error){reject(error);}
          return;
        }
        if(['CHANNEL_ERROR','TIMED_OUT','CLOSED'].includes(status)){
          settled=true;clearTimeout(timer);reject(new Error(`VOICE_REALTIME_${status}`));
        }
      });
"""
voice_subscribe_new = """      room.subscribe(async status=>{
        if(room!==voiceRoom)return;
        if(status==='SUBSCRIBED'){
          try{
            await room.track({user_id:user.id,name:user.name});
            await syncVoicePresence(user);
            if(!settled){settled=true;clearTimeout(timer);resolve();}
            else render();
          }catch(error){
            if(!settled){settled=true;clearTimeout(timer);reject(error);}
            else console.warn('Voice presence restore failed',error);
          }
          return;
        }
        if(['CHANNEL_ERROR','TIMED_OUT','CLOSED'].includes(status)){
          for(const peerId of [...voicePeers.keys()])removeVoicePeer(peerId);
          voiceParticipants=[];
          render();
          if(!settled){settled=true;clearTimeout(timer);reject(new Error(`VOICE_REALTIME_${status}`));}
        }
      });
"""
replace_once(voice_subscribe_old, voice_subscribe_new, 'voice realtime recovery')


for marker in [
    'senders can retry terminal friend requests',
    'senders can cancel pending friend requests',
    'channel.__subscribePromise',
    "CALL_SIGNAL_CHANNEL_UNAVAILABLE",
    "Call inbox retry failed",
    "Voice presence restore failed",
]:
    source = schema if marker.startswith('senders can') else text
    if marker not in source:
        raise SystemExit(f'missing reliability marker after patch: {marker}')

if changed:
    main_path.write_text(text, encoding='utf-8')
    schema_path.write_text(schema, encoding='utf-8')
    print('Applied Vessel friend lifecycle and Realtime recovery hardening')
else:
    print('Vessel friend lifecycle and Realtime recovery hardening already applied; nothing to change')
