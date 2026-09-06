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

for marker in [
    'async function resolveCallableFriend(user, peerId)',
    "select('friend_id').eq('user_id',user.id).eq('friend_id',peerId).maybeSingle()",
    "if(!caller){console.warn('Ignored call invite from non-friend');return;}",
    "name:caller.username || 'Пользователь'",
    "payload.to!==user.id || payload.from!==callPeer",
]:
    if marker not in text:
        raise SystemExit(f'missing call security marker: {marker}')

if changed:
    path.write_text(text, encoding='utf-8')
    print('Applied Vessel call authorization hardening')
else:
    print('Vessel call authorization hardening already applied; nothing to change')
