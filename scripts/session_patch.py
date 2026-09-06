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


# Keep authenticated UI/runtime state synchronized with Supabase Auth events from this
# tab and other tabs. The Auth callback itself stays synchronous: Supabase API work is
# deliberately deferred to avoid onAuthStateChange callback deadlocks.
auth_helpers_old = """let savedUser = null;

async function bootstrapAuth() {
"""
auth_helpers_new = """let savedUser = null;
let authStateSyncTimer = null;

function resetAuthenticatedRuntime() {
  const channels=[...(window.__vesselRealtimeChannels||[]),voiceRoom,callChannel,callInboxChannel].filter(Boolean);
  window.__vesselRealtimeChannels=null;
  voiceRoom=null;
  callChannel=null;
  callInboxChannel=null;

  voiceStream?.getTracks().forEach(track=>track.stop());
  callStream?.getTracks().forEach(track=>track.stop());
  remoteCallStream?.getTracks?.().forEach(track=>track.stop?.());
  voiceStream=null;
  callStream=null;
  remoteCallStream=null;
  callConnection?.close();
  callConnection=null;
  for(const peerId of [...voicePeers.keys()])removeVoicePeer(peerId);
  voiceParticipants=[];
  voiceChannelId=null;
  incomingCall=null;
  callPeer=null;
  callPeerName='';
  callOffer=null;
  callVideo=false;
  callAccepted=false;
  pendingIceCandidates=[];
  localIceCandidates=[];
  if(callInviteTimer){clearTimeout(callInviteTimer);callInviteTimer=null;}
  callMicEnabled=true;
  callCameraEnabled=true;

  savedUser=null;
  friends=[];
  dmThreads=[];
  friendRequests=[];
  outgoingFriendRequests=[];
  dmMessages=[];
  notifications=[];
  serverMembers=[];
  messages=[];
  dbChannels=[];
  servers=[{id:'add-server',icon:'+',name:'Добавить сервер',add:true}];
  activeServerId=null;
  activeServerIndex=0;
  activeChannelId=null;
  activeChannelName='нет каналов';
  activeChannelKind='text';
  currentDm=null;
  activeDmId=null;
  friendsOpen=false;

  window.__vesselDbLoaded=false;
  window.__vesselServersLoaded=false;
  window.__vesselSocialLoaded=false;
  window.__vesselDmThreadsLoaded=false;
  window.__vesselDmLoaded=false;
  window.__vesselMembersServerId=null;
  localStorage.removeItem('vesselUser');
  localStorage.removeItem('vesselToken');
  localStorage.removeItem('vesselActiveServerId');
  return [...new Set(channels)];
}

async function cleanupAuthenticatedChannels(channels=[]) {
  if(!supabase||!channels.length)return;
  await Promise.allSettled(channels.map(channel=>supabase.removeChannel(channel)));
}

function scheduleAuthStateRefresh(session) {
  const nextUserId=session?.user?.id||null;
  if(!nextUserId)return;
  if(authStateSyncTimer)clearTimeout(authStateSyncTimer);
  authStateSyncTimer=setTimeout(async()=>{
    authStateSyncTimer=null;
    if(savedUser?.id===nextUserId)return;
    try{
      await bootstrapAuth();
      render();
    }catch(error){
      console.error('Auth state refresh failed',error);
      const staleChannels=resetAuthenticatedRuntime();
      render();
      cleanupAuthenticatedChannels(staleChannels).catch(cleanupError=>console.warn('Auth cleanup failed',cleanupError));
    }
  },80);
}

function handleAuthStateChange(event,session) {
  if(event==='INITIAL_SESSION'||event==='TOKEN_REFRESHED')return;
  const nextUserId=session?.user?.id||null;
  if(event==='SIGNED_OUT'||!nextUserId){
    if(authStateSyncTimer){clearTimeout(authStateSyncTimer);authStateSyncTimer=null;}
    const staleChannels=resetAuthenticatedRuntime();
    render();
    setTimeout(()=>cleanupAuthenticatedChannels(staleChannels).catch(error=>console.warn('Auth channel cleanup failed',error)),0);
    return;
  }
  if(event==='SIGNED_IN'){
    if(savedUser?.id===nextUserId)return;
    const staleChannels=savedUser?.id&&savedUser.id!==nextUserId?resetAuthenticatedRuntime():[];
    if(staleChannels.length)setTimeout(()=>cleanupAuthenticatedChannels(staleChannels).catch(error=>console.warn('Auth account-switch cleanup failed',error)),0);
    scheduleAuthStateRefresh(session);
  }
}

async function bootstrapAuth() {
"""
replace_once(auth_helpers_old, auth_helpers_new, 'auth state helpers')


startup_old = """}
bootstrapAuth().then(render).catch(error=>{console.error('Vessel bootstrap failed',error);savedUser=null;render();});
setInterval(()=>{const video=document.querySelector('#local-video');const stream=callStream||voiceStream;if(video&&stream&&video.srcObject!==stream){video.srcObject=stream;video.play().catch(()=>{});}const remote=document.querySelector('#remote-video');if(remote&&remoteCallStream&&remote.srcObject!==remoteCallStream){remote.srcObject=remoteCallStream;remote.play().catch(()=>{});}},500);
"""
startup_new = """}
const authStateSubscription=supabase?.auth.onAuthStateChange((event,session)=>handleAuthStateChange(event,session)).data?.subscription||null;
window.addEventListener('beforeunload',()=>authStateSubscription?.unsubscribe());
bootstrapAuth().then(render).catch(error=>{console.error('Vessel bootstrap failed',error);const staleChannels=resetAuthenticatedRuntime();render();cleanupAuthenticatedChannels(staleChannels).catch(()=>{});});
setInterval(()=>{const video=document.querySelector('#local-video');const stream=callStream||voiceStream;if(video&&stream&&video.srcObject!==stream){video.srcObject=stream;video.play().catch(()=>{});}const remote=document.querySelector('#remote-video');if(remote&&remoteCallStream&&remote.srcObject!==remoteCallStream){remote.srcObject=remoteCallStream;remote.play().catch(()=>{});}},500);
"""
replace_once(startup_old, startup_new, 'auth state listener startup')


for marker in [
    'function resetAuthenticatedRuntime()',
    'function handleAuthStateChange(event,session)',
    "event==='INITIAL_SESSION'||event==='TOKEN_REFRESHED'",
    "setTimeout(()=>cleanupAuthenticatedChannels",
    'auth.onAuthStateChange((event,session)=>handleAuthStateChange(event,session))',
]:
    if marker not in text:
        raise SystemExit(f'missing session hardening marker: {marker}')

if changed:
    path.write_text(text,encoding='utf-8')
    print('Applied Vessel auth/session lifecycle hardening')
else:
    print('Vessel auth/session lifecycle hardening already applied; nothing to change')
