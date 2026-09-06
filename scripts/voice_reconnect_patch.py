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
    """let voiceParticipants = [];
const voicePeers = new Map();
let callStream = null;""",
    """let voiceParticipants = [];
const voicePeers = new Map();
let voiceReconnectTimer = null;
let voiceReconnectAttempt = 0;
let voiceReconnectContext = null;
let callStream = null;""",
    'voice reconnect state',
)

replace_once(
    """async function leaveVoiceRoom(){
  const room=voiceRoom;
  voiceRoom=null;
  voiceStream?.getTracks().forEach(track=>track.stop());voiceStream=null;
  for(const peerId of [...voicePeers.keys()])removeVoicePeer(peerId);
  voiceParticipants=[];voiceChannelId=null;voiceServerId=null;
  if(room&&supabase){try{await supabase.removeChannel(room);}catch{}}
  render();
}

async function toggleVoiceRoom(user){
  if(voiceStream && voiceChannelId===activeChannelId){await leaveVoiceRoom();return;}
""",
    """function cancelVoiceReconnect(){
  if(voiceReconnectTimer){clearTimeout(voiceReconnectTimer);voiceReconnectTimer=null;}
  voiceReconnectAttempt=0;
  voiceReconnectContext=null;
}

function scheduleVoiceReconnect(user,channelId,serverId){
  if(!user?.id||!channelId||!serverId)return;
  if(voiceReconnectContext&&(voiceReconnectContext.channelId!==channelId||voiceReconnectContext.serverId!==serverId))cancelVoiceReconnect();
  if(voiceReconnectTimer)return;
  voiceReconnectContext={channelId,serverId};
  voiceReconnectAttempt=Math.min(voiceReconnectAttempt+1,4);
  const attempt=voiceReconnectAttempt;
  const delay=Math.min(1000*(2**(attempt-1)),8000);
  voiceReconnectTimer=setTimeout(async()=>{
    voiceReconnectTimer=null;
    if(!voiceReconnectContext||voiceReconnectContext.channelId!==channelId||voiceReconnectContext.serverId!==serverId)return;
    if(activeChannelId!==channelId||activeChannelKind!=='voice'||getActiveServer()?.dbId!==serverId){cancelVoiceReconnect();return;}
    if(callConnection||callStream||incomingCall){cancelVoiceReconnect();return;}
    await toggleVoiceRoom(user,true);
    if(voiceStream&&voiceRoom&&voiceChannelId===channelId){
      cancelVoiceReconnect();
      vesselNotice('Голосовая связь восстановлена.','success');
      return;
    }
    if(attempt<4){scheduleVoiceReconnect(user,channelId,serverId);return;}
    cancelVoiceReconnect();
    vesselNotice('Голосовая связь потеряна. Нажми «Войти», чтобы попробовать снова.','error');
  },delay);
}

async function leaveVoiceRoom(){
  cancelVoiceReconnect();
  const room=voiceRoom;
  voiceRoom=null;
  voiceStream?.getTracks().forEach(track=>track.stop());voiceStream=null;
  for(const peerId of [...voicePeers.keys()])removeVoicePeer(peerId);
  voiceParticipants=[];voiceChannelId=null;voiceServerId=null;
  if(room&&supabase){try{await supabase.removeChannel(room);}catch{}}
  render();
}

async function toggleVoiceRoom(user,reconnecting=false){
  if(!reconnecting)cancelVoiceReconnect();
  if(voiceStream && voiceChannelId===activeChannelId){await leaveVoiceRoom();return;}
""",
    'voice reconnect scheduler',
)

replace_once(
    """        if(['CHANNEL_ERROR','TIMED_OUT','CLOSED'].includes(status)){
          for(const peerId of [...voicePeers.keys()])removeVoicePeer(peerId);
          voiceParticipants=[];
          render();
          if(!settled){settled=true;clearTimeout(timer);reject(new Error(`VOICE_REALTIME_${status}`));}
        }
""",
    """        if(['CHANNEL_ERROR','TIMED_OUT','CLOSED'].includes(status)){
          if(!settled){
            for(const peerId of [...voicePeers.keys()])removeVoicePeer(peerId);
            voiceParticipants=[];
            render();
            settled=true;clearTimeout(timer);reject(new Error(`VOICE_REALTIME_${status}`));
            return;
          }
          const failedChannelId=voiceChannelId;
          const failedServerId=voiceServerId;
          voiceRoom=null;
          voiceStream?.getTracks().forEach(track=>track.stop());voiceStream=null;
          for(const peerId of [...voicePeers.keys()])removeVoicePeer(peerId);
          voiceParticipants=[];voiceChannelId=null;voiceServerId=null;
          if(supabase)void supabase.removeChannel(room).catch(error=>console.warn('Voice channel cleanup failed',error));
          render();
          scheduleVoiceReconnect(user,failedChannelId,failedServerId);
        }
""",
    'post-subscription voice disconnect recovery',
)

replace_once(
    """    voiceParticipants=[];voiceChannelId=null;
    if(room&&supabase){try{await supabase.removeChannel(room);}catch{}}
    if(voiceRoom===room)voiceRoom=null;
    vesselNotice(error?.message?.startsWith('VOICE_REALTIME_')?'Не удалось подключиться к голосовой комнате. Попробуй ещё раз.':'Разреши Vessel доступ к микрофону.','error');
    render();
""",
    """    voiceParticipants=[];voiceChannelId=null;voiceServerId=null;
    if(room&&supabase){try{await supabase.removeChannel(room);}catch{}}
    if(voiceRoom===room)voiceRoom=null;
    if(!reconnecting)vesselNotice(error?.message?.startsWith('VOICE_REALTIME_')?'Не удалось подключиться к голосовой комнате. Попробуй ещё раз.':'Разреши Vessel доступ к микрофону.','error');
    render();
""",
    'silent reconnect failure cleanup',
)

for marker in [
    'let voiceReconnectTimer = null;',
    'function scheduleVoiceReconnect(user,channelId,serverId)',
    'async function toggleVoiceRoom(user,reconnecting=false)',
    'scheduleVoiceReconnect(user,failedChannelId,failedServerId);',
    "if(!reconnecting)vesselNotice(error?.message?.startsWith('VOICE_REALTIME_')",
]:
    if marker not in text:
        raise SystemExit(f'missing voice reconnect marker: {marker}')

if changed:
    path.write_text(text, encoding='utf-8')
    print('Applied bounded voice Realtime reconnect recovery')
else:
    print('Voice Realtime reconnect recovery already applied; nothing to change')
