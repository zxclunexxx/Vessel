from pathlib import Path

path = Path('src/main.js')
main = path.read_text(encoding='utf-8')
marker = '/* VESSEL_UI_VOICE_CALLS_V1 */'

if marker in main:
    required = ['function callStageMarkup(', 'function voiceStageMarkup(', 'function watchSpeakingStream(', 'rtc-control-dock', 'incoming-call-card', 'data-call-duration']
    missing = [item for item in required if item not in main]
    if missing:
        raise SystemExit('Voice/calls runtime marker exists but output is incomplete: ' + ', '.join(missing))
    print('Vessel voice/calls runtime already applied')
    raise SystemExit(0)

def replace_once(label, old, new):
    global main
    count = main.count(old)
    if count != 1:
        raise SystemExit(f'Voice/calls runtime source drift at {label}: expected 1, found {count}')
    main = main.replace(old, new, 1)

state_old = """let callSignalReconnectTimer = null;
let callSignalReconnectAttempt = 0;
"""
state_new = state_old + """/* VESSEL_UI_VOICE_CALLS_V1 */
let callStartedAt = 0;
let callUiTicker = null;
const rtcSpeakingMeters = new Map();
"""
replace_once('visual state', state_old, state_new)

anchor = """function statusTone(value='online') {
  const key=String(value||'online').toLowerCase();
  if(['dnd','не беспокоить'].includes(key))return 'dnd';
  if(['away','idle','отошёл'].includes(key))return 'away';
  if(['offline','не в сети'].includes(key))return 'offline';
  return 'online';
}
"""
helpers = r'''function formatCallDuration(startedAt=0){
  if(!startedAt)return '00:00';
  const total=Math.max(0,Math.floor((Date.now()-startedAt)/1000));
  const h=Math.floor(total/3600),m=Math.floor((total%3600)/60),s=total%60;
  return h?`${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`:`${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
}
function callVisualState(){
  const state=callConnection?.connectionState||'new';
  if(callSignalReconnectTimer||callIceRestartInFlight||['failed','disconnected'].includes(state))return 'reconnecting';
  if(state==='connected')return 'connected';
  if(callAccepted)return 'connecting';
  return 'calling';
}
function callVisualLabel(){
  const state=callVisualState();
  if(state==='connected')return callVideo?'Видеосвязь защищена':'Голосовая связь';
  if(state==='reconnecting')return 'Восстанавливаем соединение…';
  if(state==='connecting')return 'Соединяем…';
  return 'Вызов…';
}
function voiceVisualState(){
  if(voiceReconnectTimer||(voiceReconnectContext&&!voiceRoom))return 'reconnecting';
  if(voiceStream&&voiceRoom&&voiceChannelId===activeChannelId)return 'connected';
  return 'ready';
}
function voiceVisualLabel(){
  const state=voiceVisualState();
  if(state==='reconnecting')return 'Восстанавливаем комнату…';
  if(state==='connected')return `${Math.max(1,voiceParticipants.length)} в комнате`;
  return 'Готово к подключению';
}
function syncSpeakingClass(key,speaking){
  document.querySelectorAll('[data-speaking-key]').forEach(node=>{if(node.dataset.speakingKey===key)node.classList.toggle('is-speaking',Boolean(speaking));});
}
function stopSpeakingMeter(key){
  const meter=rtcSpeakingMeters.get(key);if(!meter)return;rtcSpeakingMeters.delete(key);
  if(meter.raf)cancelAnimationFrame(meter.raf);try{meter.source?.disconnect();}catch{}try{meter.analyser?.disconnect();}catch{}try{meter.context?.close();}catch{}syncSpeakingClass(key,false);
}
function stopSpeakingMeters(prefix=''){for(const key of [...rtcSpeakingMeters.keys()])if(!prefix||key.startsWith(prefix))stopSpeakingMeter(key);}
function watchSpeakingStream(stream,key){
  if(!stream?.getAudioTracks?.().length||!key)return;
  const existing=rtcSpeakingMeters.get(key);if(existing?.stream===stream)return;if(existing)stopSpeakingMeter(key);
  const AudioContextCtor=window.AudioContext||window.webkitAudioContext;if(!AudioContextCtor)return;
  try{
    const context=new AudioContextCtor(),analyser=context.createAnalyser(),source=context.createMediaStreamSource(stream);analyser.fftSize=256;analyser.smoothingTimeConstant=.72;source.connect(analyser);context.resume?.().catch(()=>{});
    const data=new Uint8Array(analyser.fftSize),meter={stream,context,source,analyser,raf:null,speaking:false};rtcSpeakingMeters.set(key,meter);
    const sample=()=>{if(rtcSpeakingMeters.get(key)!==meter)return;const live=stream.getAudioTracks().some(track=>track.readyState==='live'&&track.enabled);analyser.getByteTimeDomainData(data);let energy=0;for(const value of data){const n=(value-128)/128;energy+=n*n;}const speaking=Boolean(live&&Math.sqrt(energy/data.length)>.035);if(speaking!==meter.speaking){meter.speaking=speaking;syncSpeakingClass(key,speaking);}meter.raf=requestAnimationFrame(sample);};sample();
  }catch(error){console.warn('RTC speaking meter unavailable',error);}
}
function syncCallUiTicker(active=Boolean(callConnection||callStream)){
  const update=()=>document.querySelectorAll('[data-call-duration]').forEach(node=>{node.textContent=formatCallDuration(callStartedAt);});
  if(!active){if(callUiTicker){clearInterval(callUiTicker);callUiTicker=null;}return;}update();if(!callUiTicker)callUiTicker=setInterval(update,1000);
}
function callStageMarkup(user){
  const state=callVisualState(),peerName=callPeerName||currentDm||'Пользователь',peerInitial=escapeHtml(peerName?.[0]?.toUpperCase()||'?'),selfInitial=escapeHtml(user?.name?.[0]?.toUpperCase()||'?'),reconnecting=state==='reconnecting',muted=!callMicEnabled,cameraOff=callVideo&&!callCameraEnabled;
  const controls=`<div class="rtc-control-dock"><button id="toggle-call-mic" class="rtc-dock-button ${muted?'off':''}" type="button"><span>${muted?'🔇':'🎙'}</span><small>${muted?'Микрофон выкл.':'Микрофон'}</small></button>${callVideo?`<button id="toggle-call-camera" class="rtc-dock-button ${cameraOff?'off':''}" type="button"><span>${cameraOff?'🚫':'📷'}</span><small>${cameraOff?'Камера выкл.':'Камера'}</small></button>`:''}<button id="end-call" class="rtc-dock-button end" type="button"><span>☎</span><small>Завершить</small></button></div>`;
  const top=`<div class="rtc-stage-topbar"><div><span class="rtc-eyebrow">${callVideo?'VESSEL CALL':'VESSEL AUDIO'}</span><h2>${callVideo?escapeHtml(peerName):`Звонок с ${escapeHtml(peerName)}`}</h2></div><div class="rtc-session-meta"><span class="rtc-state-pill ${reconnecting?'warning':''}"><i></i><span data-call-state-label>${escapeHtml(callVisualLabel())}</span></span><time data-call-duration>${formatCallDuration(callStartedAt)}</time></div></div>`;
  const reconnect=reconnecting?'<div class="rtc-reconnect-banner"><span>↻</span><div><b>Связь нестабильна</b><small>Vessel автоматически восстанавливает сигнал и ICE-маршрут.</small></div></div>':'';
  if(callVideo)return `<section class="rtc-stage call-stage video-mode state-${state}" data-call-stage>${top}${reconnect}<div class="video-stage-grid"><div class="remote-video-tile" data-speaking-key="call-peer"><video id="remote-video" class="remote-video ${remoteCallStream?'':'hidden'}" autoplay playsinline></video><div class="video-placeholder ${remoteCallStream?'hidden':''}"><div class="participant-avatar xl">${peerInitial}</div><span>Ожидаем видео…</span></div><div class="video-label"><span class="speaking-dot"></span>${escapeHtml(peerName)}</div></div><div class="local-preview ${cameraOff?'camera-off':''}" data-speaking-key="call-self"><video id="local-video" class="local-video ${callStream?'':'hidden'}" autoplay muted playsinline></video><div class="local-camera-fallback"><div class="participant-avatar">${selfInitial}</div><span>Камера выключена</span></div><div class="video-label">Ты</div></div></div>${controls}</section>`;
  return `<section class="rtc-stage call-stage audio-mode state-${state}" data-call-stage>${top}${reconnect}<div class="audio-call-focus"><div class="audio-orbit orbit-one"></div><div class="audio-orbit orbit-two"></div><div class="participant-avatar hero" data-speaking-key="call-peer">${peerInitial}<span class="speaking-ring"></span></div><h3>${escapeHtml(peerName)}</h3><p>${escapeHtml(callVisualLabel())}</p><div class="audio-wave"><i></i><i></i><i></i><i></i><i></i><i></i><i></i></div><div class="self-audio-chip" data-speaking-key="call-self"><span class="participant-avatar">${selfInitial}</span><div><b>Ты</b><small>${muted?'Микрофон выключен':'Микрофон активен'}</small></div></div></div>${controls}</section>`;
}
function voiceStageMarkup(user){
  const state=voiceVisualState(),connected=state==='connected',reconnecting=state==='reconnecting',micOff=voiceStream?.getAudioTracks?.()[0]?.enabled===false;
  const participants=connected?(voiceParticipants.length?voiceParticipants:[{id:user.id,name:user.name}]):[];
  const cards=participants.map(participant=>{const self=participant.id===user.id,name=self?'Ты':(participant.name||'Участник'),key=`voice-${participant.id}`;return `<article class="voice-participant-card ${self?'self':''}" data-speaking-key="${escapeHtml(key)}"><div class="participant-avatar">${escapeHtml(name?.[0]?.toUpperCase()||'?')}<span class="speaking-ring"></span></div><div><b>${escapeHtml(name)}</b><small>${self?(micOff?'Микрофон выключен':'Ты в эфире'):'Подключён'}</small></div><span class="voice-card-level"><i></i><i></i><i></i></span></article>`;}).join('');
  const controls=connected?`<div class="rtc-control-dock"><button id="mute-voice" class="rtc-dock-button ${micOff?'off':''}" type="button"><span>${micOff?'🔇':'🎙'}</span><small>Микрофон</small></button><button id="deafen-voice" class="rtc-dock-button ${voiceDeafened?'off':''}" type="button"><span>${voiceDeafened?'🙉':'🎧'}</span><small>Звук</small></button><button id="join-voice" class="rtc-dock-button end" type="button"><span>↙</span><small>Выйти</small></button></div>`:`<div class="rtc-control-dock single"><button id="join-voice" class="rtc-dock-button join" type="button"><span>🎙</span><small>${reconnecting?'Подождать':'Войти в комнату'}</small></button></div>`;
  return `<section class="rtc-stage voice-stage state-${state}" data-voice-stage><div class="rtc-stage-topbar"><div><span class="rtc-eyebrow">VESSEL VOICE</span><h2>${escapeHtml(activeChannelName)}</h2><p>${escapeHtml(getActiveServer()?.name||'Vessel')}</p></div><span class="rtc-state-pill ${reconnecting?'warning':''}"><i></i><span data-voice-state-label>${escapeHtml(voiceVisualLabel())}</span></span></div>${reconnecting?'<div class="rtc-reconnect-banner"><span>↻</span><div><b>Комната переподключается</b><small>Vessel восстанавливает Realtime и peer-соединения автоматически.</small></div></div>':''}<div class="voice-room-hero"><div class="voice-room-symbol">⌁</div><h3>${connected?'Вы в голосовой комнате':'Голосовая комната готова'}</h3><p>${connected?'Активные участники подсвечиваются в реальном времени.':'Подключись, чтобы увидеть участников и начать разговор.'}</p></div><div class="voice-participant-grid">${cards||'<div class="voice-room-empty"><span>◇</span><b>Пока никого нет</b><small>Будь первым, кто подключится.</small></div>'}</div>${controls}</section>`;
}
function syncRtcVisualRuntime(){
  const expected=new Map();if(callStream)expected.set('call-self',callStream);if(remoteCallStream)expected.set('call-peer',remoteCallStream);if(voiceStream&&savedUser?.id)expected.set(`voice-${savedUser.id}`,voiceStream);for(const [peerId,state] of voicePeers){const stream=state.audio?.srcObject;if(stream)expected.set(`voice-${peerId}`,stream);}for(const [key,meter] of [...rtcSpeakingMeters])if(!expected.has(key)||expected.get(key)!==meter.stream)stopSpeakingMeter(key);for(const [key,stream] of expected)watchSpeakingStream(stream,key);syncCallUiTicker(Boolean(callConnection||callStream));
  const callStage=document.querySelector('[data-call-stage]');if(callStage){callStage.querySelectorAll('[data-call-state-label]').forEach(node=>node.textContent=callVisualLabel());const remote=document.querySelector('#remote-video'),placeholder=callStage.querySelector('.video-placeholder');if(remote)remote.classList.toggle('hidden',!remoteCallStream);if(placeholder)placeholder.classList.toggle('hidden',Boolean(remoteCallStream));}
  const voiceStage=document.querySelector('[data-voice-stage]');if(voiceStage)voiceStage.querySelectorAll('[data-voice-state-label]').forEach(node=>node.textContent=voiceVisualLabel());
}
'''
replace_once('visual helpers', anchor, anchor + helpers)

old_actions = """  const callActions=callInProgress
    ? `<button id=\"toggle-call-mic\" class=\"call-control\" title=\"${callMicEnabled?'Выключить микрофон':'Включить микрофон'}\">${callMicEnabled?'🎙':'🔇'}</button>${callVideo?`<button id=\"toggle-call-camera\" class=\"call-control\" title=\"${callCameraEnabled?'Выключить камеру':'Включить камеру'}\">${callCameraEnabled?'📷':'🚫'}</button>`:''}<button id=\"end-call\" class=\"hangup\" title=\"Завершить звонок\">☎</button>`
    : (!friendsOpen&&activeDmId&&activeDmIsFriend) ? `<button id=\"audio-call\" title=\"Аудиозвонок\">📞</button><button id=\"video-call\" title=\"Видеозвонок\">🎥</button>` : '';
"""
new_actions = """  const callActions=!callInProgress&&(!friendsOpen&&activeDmId&&activeDmIsFriend)
    ? `<button id=\"audio-call\" title=\"Аудиозвонок\">📞</button><button id=\"video-call\" title=\"Видеозвонок\">🎥</button>`
    : '';
  const rtcStage=callInProgress?callStageMarkup(user):(!friendsOpen&&!activeDmId&&activeChannelKind==='voice'?voiceStageMarkup(user):'');
"""
replace_once('call actions', old_actions, new_actions)

start = '${callActions}<button id="join-voice"'
end = '<button id="search-button"'
if main.count(start) != 1 or main.count(end) != 1:
    raise SystemExit(f'Voice/calls runtime source drift at header voice controls: start={main.count(start)} end={main.count(end)}')
start_index = main.index(start)
end_index = main.index(end, start_index)
main = main[:start_index] + '${callActions}' + main[end_index:]

replace_once('legacy video nodes', '<video id="remote-video" class="remote-video ${remoteCallStream?\'\':\'hidden\'}" autoplay playsinline></video><video id="local-video" class="local-video ${callStream||voiceStream?.getVideoTracks().length?\'\':\'hidden\'}" autoplay muted playsinline></video>', '${rtcStage}')

incoming_old = """${incomingCall?`<div class=\"modal call-modal\" id=\"incoming-call-modal\"><div class=\"modal-card\"><div class=\"call-avatar\">${escapeHtml(incomingCall.name?.[0]?.toUpperCase()||'?')}</div><h2>${incomingCall.video?'Видеозвонок':'Аудиозвонок'}</h2><p>${escapeHtml(incomingCall.name)} звонит тебе в Vessel.</p><div class=\"call-actions\"><button class=\"danger\" id=\"reject-call\" type=\"button\">Отклонить</button><button class=\"primary\" id=\"accept-call\" type=\"button\">Принять</button></div></div></div>`:''}"""
incoming_new = """${incomingCall?`<div class=\"modal call-modal incoming-call-modal\" id=\"incoming-call-modal\"><div class=\"modal-card incoming-call-card\"><span class=\"rtc-eyebrow\">ВХОДЯЩИЙ ВЫЗОВ</span><div class=\"incoming-call-orbit\"><i></i><i></i><div class=\"call-avatar\">${escapeHtml(incomingCall.name?.[0]?.toUpperCase()||'?')}</div></div><span class=\"incoming-call-type\">${incomingCall.video?'🎥 Видеозвонок':'🎙 Аудиозвонок'}</span><h2>${escapeHtml(incomingCall.name)}</h2><p>звонит тебе в Vessel</p><div class=\"incoming-call-wave\"><i></i><i></i><i></i><i></i><i></i></div><div class=\"call-actions\"><button class=\"danger incoming-reject\" id=\"reject-call\" type=\"button\"><span>☎</span>Отклонить</button><button class=\"primary incoming-accept\" id=\"accept-call\" type=\"button\"><span>${incomingCall.video?'🎥':'🎙'}</span>Принять</button></div></div></div>`:''}"""
replace_once('incoming call', incoming_old, incoming_new)
replace_once('visual runtime sync', "  const nextMessagesPane=document.querySelector('.messages');\n", "  syncRtcVisualRuntime();\n  const nextMessagesPane=document.querySelector('.messages');\n")
replace_once('call connection state', """    if(state==='connected'){clearCallDisconnectTimer();callIceRestartAttempts=0;callIceRestartInFlight=false;return;}
    if(state==='closed'){clearCallDisconnectTimer();return;}
    if(['failed','disconnected'].includes(state))scheduleCallDisconnectCleanup(connection,user,peerId,video);
""", """    if(state==='connected'){clearCallDisconnectTimer();callIceRestartAttempts=0;callIceRestartInFlight=false;if(!callStartedAt)callStartedAt=Date.now();render();return;}
    if(state==='closed'){clearCallDisconnectTimer();syncRtcVisualRuntime();return;}
    if(['failed','disconnected'].includes(state)){render();scheduleCallDisconnectCleanup(connection,user,peerId,video);}
""")
replace_once('call cleanup', """  callMicEnabled=true;
  callCameraEnabled=true;
  render();
""", """  callMicEnabled=true;
  callCameraEnabled=true;
  callStartedAt=0;
  stopSpeakingMeters('call-');
  syncCallUiTicker(false);
  render();
""")
replace_once('voice cleanup', "  voiceParticipants=[];voiceChannelId=null;voiceServerId=null;voiceDeafened=false;\n", "  stopSpeakingMeters('voice-');\n  voiceParticipants=[];voiceChannelId=null;voiceServerId=null;voiceDeafened=false;\n")
replace_once('voice participants refresh', """  const status=document.querySelector('.voice-status');
  if(status)status.textContent=`🎙 В голосовой комнате: ${Math.max(1,voiceParticipants.length)}`;
""", """  const status=document.querySelector('.voice-status');
  if(status)status.textContent=`🎙 В голосовой комнате: ${Math.max(1,voiceParticipants.length)}`;
  if(activeChannelKind==='voice'&&voiceChannelId===activeChannelId)render();
""")
replace_once('voice reconnect visual', "  voiceReconnectContext={channelId,serverId};\n", "  voiceReconnectContext={channelId,serverId};\n  render();\n")
replace_once('remote call meter', "  callConnection.ontrack=e=>{remoteCallStream=e.streams[0];const el=document.querySelector('#remote-video');if(el){el.srcObject=remoteCallStream;el.play().catch(()=>{});} };\n", "  callConnection.ontrack=e=>{remoteCallStream=e.streams[0];const el=document.querySelector('#remote-video');if(el){el.srcObject=remoteCallStream;el.play().catch(()=>{});}syncRtcVisualRuntime();};\n")

path.write_text(main, encoding='utf-8')
print('Applied Vessel voice/calls runtime UI')
