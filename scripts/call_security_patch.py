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


# Realtime broadcast topics are transport, not authorization. Resolve the caller against the
# authenticated user's current friendship row and derive the visible name from the database.
helper_old = """async function ensureCallInbox(user) {
  if (!supabase || !user?.id) return null;
"""
helper_new = """async function resolveCallableFriend(user, peerId) {
  if(!supabase||!user?.id||!peerId||peerId===user.id)return null;
  const {data:link,error:linkError}=await supabase.from('friendships').select('friend_id').eq('user_id',user.id).eq('friend_id',peerId).maybeSingle();
  if(linkError||!link)return null;
  const {data:profile,error:profileError}=await supabase.from('profiles').select('id,username,avatar_color,status').eq('id',peerId).maybeSingle();
  if(profileError)return null;
  return profile||{id:peerId,username:'Пользователь'};
}
async function ensureCallInbox(user) {
  if (!supabase || !user?.id) return null;
"""
replace_once(helper_old, helper_new, 'call friendship resolver')

invite_old = """    if (payload.type === 'invite') {
      if (callConnection || callStream || incomingCall) {
        await sendCallInvite(user, payload.from, {type:'busy'});
        return;
      }
      incomingCall = {from:payload.from, name:payload.name || 'Пользователь', video:!!payload.video, offer:payload.offer};
      render();
      return;
    }
"""
invite_new = """    if (payload.type === 'invite') {
      const caller=await resolveCallableFriend(user,payload.from);
      if(!caller){console.warn('Ignored call invite from non-friend');return;}
      if (callConnection || callStream || incomingCall) {
        await sendCallInvite(user, payload.from, {type:'busy'});
        return;
      }
      incomingCall = {from:payload.from, name:caller.username || 'Пользователь', video:!!payload.video, offer:payload.offer};
      render();
      return;
    }
"""
replace_once(invite_old, invite_new, 'incoming call authorization')

signal_old = """  callChannel.on('broadcast',{event:'signal'},async({payload})=>{
    if(!payload || payload.to!==user.id) return;
    await handleCallSignal(user,payload.from,payload.signal,payload.video).catch(error=>{console.warn('Call signal failed',error);endCall(false);});
  });
"""
signal_new = """  callChannel.on('broadcast',{event:'signal'},async({payload})=>{
    if(!payload || payload.to!==user.id || payload.from!==callPeer) return;
    await handleCallSignal(user,payload.from,payload.signal,payload.video).catch(error=>{console.warn('Call signal failed',error);endCall(false);});
  });
"""
replace_once(signal_old, signal_new, 'call signal peer validation')

# Friendship deletion is also a call-capability revocation. Tear down active/pending calls as
# soon as Realtime reports the authenticated user's friendship row was deleted.
friendship_realtime_old = """    supabase.channel(`vessel-friendships-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'friendships',filter:`user_id=eq.${user.id}`},()=>{window.__vesselSocialLoaded=false;syncSocial(user);}).subscribe(),"""
friendship_realtime_new = """    supabase.channel(`vessel-friendships-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'friendships',filter:`user_id=eq.${user.id}`},async payload=>{
      const row=payload.new?.friend_id?payload.new:payload.old;
      if(payload.eventType==='DELETE'&&row?.friend_id){
        if(incomingCall?.from===row.friend_id){incomingCall=null;render();}
        if(callPeer===row.friend_id)await endCall(false);
      }
      window.__vesselSocialLoaded=false;
      syncSocial(user);
    }).subscribe(),"""
replace_once(friendship_realtime_old, friendship_realtime_new, 'friendship call teardown realtime')

# Proactively end the local call before deleting both friendship rows, avoiding a window where
# media continues while the database relationship has already been revoked.
remove_friend_old = """    if(!await vesselConfirm(`Удалить ${friend?.username||'пользователя'} из друзей?`))return;
    const {error}=await supabase.from('friendships').delete().or(`and(user_id.eq.${user.id},friend_id.eq.${friendId}),and(user_id.eq.${friendId},friend_id.eq.${user.id})`);"""
remove_friend_new = """    if(!await vesselConfirm(`Удалить ${friend?.username||'пользователя'} из друзей?`))return;
    if(incomingCall?.from===friendId){incomingCall=null;render();}
    if(callPeer===friendId)await endCall(false);
    const {error}=await supabase.from('friendships').delete().or(`and(user_id.eq.${user.id},friend_id.eq.${friendId}),and(user_id.eq.${friendId},friend_id.eq.${user.id})`);"""
replace_once(remove_friend_old, remove_friend_new, 'local unfriend call teardown')

for marker in [
    'async function resolveCallableFriend(user, peerId)',
    "select('friend_id').eq('user_id',user.id).eq('friend_id',peerId).maybeSingle()",
    "if(!caller){console.warn('Ignored call invite from non-friend');return;}",
    "name:caller.username || 'Пользователь'",
    "payload.to!==user.id || payload.from!==callPeer",
    "if(callPeer===row.friend_id)await endCall(false);",
    "if(callPeer===friendId)await endCall(false);",
]:
    if marker not in text:
        raise SystemExit(f'missing call security marker: {marker}')

if changed:
    path.write_text(text, encoding='utf-8')
    print('Applied Vessel call authorization and friendship lifecycle hardening')
else:
    print('Vessel call security/lifecycle hardening already applied; nothing to change')
