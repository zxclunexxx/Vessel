from pathlib import Path
import re

MAIN_PATH = Path('src/main.js')
STYLE_PATH = Path('src/style.css')
MAIN_MARKER = '/* VESSEL_UI_VOICE_CALLS_V1 */'
STYLE_MARKER = '/* VESSEL_UI_VOICE_CALLS_V1 */'

main = MAIN_PATH.read_text(encoding='utf-8')
style = STYLE_PATH.read_text(encoding='utf-8')

if MAIN_MARKER in main or STYLE_MARKER in style:
    required_main = [
        'function callStageMarkup(',
        'function voiceStageMarkup(',
        'function syncRtcVisualRuntime(',
        'function watchSpeakingStream(',
        'data-call-duration',
        'rtc-control-dock',
        'incoming-call-card',
    ]
    required_style = [
        '.rtc-stage',
        '.video-stage-grid',
        '.voice-participant-card',
        '.rtc-control-dock',
        '.incoming-call-card',
        'rtcSpeakingPulse',
    ]
    missing = [item for item in required_main if item not in main] + [item for item in required_style if item not in style]
    if missing:
        raise SystemExit('Voice/calls UI marker exists but generated output is incomplete: ' + ', '.join(missing))
    print('Vessel voice/calls UI already applied')
    raise SystemExit(0)

def replace_once(label, old, new):
    global main
    count = main.count(old)
    if count != 1:
        raise SystemExit(f'Voice/calls UI source drift at {label}: expected 1, found {count}')
    main = main.replace(old, new, 1)

state_old = """let callSignalReconnectTimer = null;
let callSignalReconnectAttempt = 0;
"""
state_new = state_old + """/* VESSEL_UI_VOICE_CALLS_V1 */
let callStartedAt = 0;
let callUiTicker = null;
const rtcSpeakingMeters = new Map();
"""
replace_once('RTC visual state', state_old, state_new)

status_old = """function statusTone(value='online') {
  const key=String(value||'online').toLowerCase();
  if(['dnd','не беспокоить'].includes(key))return 'dnd';
  if(['away','idle','отошёл'].includes(key))return 'away';
  if(['offline','не в сети'].includes(key))return 'offline';
  return 'online';
}
"""

helpers = r'''function formatCallDuration(startedAt=0) {
  if(!startedAt)return '00:00';
  const total=Math.max(0,Math.floor((Date.now()-startedAt)/1000));
  const hours=Math.floor(total/3600);
  const minutes=Math.floor((total%3600)/60);
  const seconds=total%60;
  return hours>0
    ? `${String(hours).padStart(2,'0')}:${String(minutes).padStart(2,'0')}:${String(seconds).padStart(2,'0')}`
    : `${String(minutes).padStart(2,'0')}:${String(seconds).padStart(2,'0')}`;
}
function callVisualState() {
  const state=callConnection?.connectionState||'new';
  if(callSignalReconnectTimer||callIceRestartInFlight||['failed','disconnected'].includes(state))return 'reconnecting';
  if(state==='connected')return 'connected';
  if(callAccepted)return 'connecting';
  return 'calling';
}
function callVisualLabel() {
  const state=callVisualState();
  if(state==='connected')return callVideo?'Видеосвязь защищена':'Голосовая связь';
  if(state==='reconnecting')return 'Восстанавливаем соединение…';
  if(state==='connecting')return 'Соединяем…';
  return 'Вызов…';
}
function voiceVisualState() {
  if(voiceReconnectTimer||(voiceReconnectContext&&!voiceRoom))return 'reconnecting';
  if(voiceStream&&voiceRoom&&voiceChannelId===activeChannelId)return 'connected';
  return 'ready';
}
function voiceVisualLabel() {
  const state=voiceVisualState();
  if(state==='reconnecting')return 'Восстанавливаем комнату…';
  if(state==='connected')return `${Math.max(1,voiceParticipants.length)} в комнате`;
  return 'Готово к подключению';
}
function syncSpeakingClass(key,speaking) {
  document.querySelectorAll('[data-speaking-key]').forEach(node=>{
    if(node.dataset.speakingKey===key)node.classList.toggle('is-speaking',Boolean(speaking));
  });
}
function stopSpeakingMeter(key) {
  const meter=rtcSpeakingMeters.get(key);
  if(!meter)return;
  rtcSpeakingMeters.delete(key);
  if(meter.raf)cancelAnimationFrame(meter.raf);
  try{meter.source?.disconnect();}catch{}
  try{meter.analyser?.disconnect();}catch{}
  try{meter.context?.close();}catch{}
  syncSpeakingClass(key,false);
}
function stopSpeakingMeters(prefix='') {
  for(const key of [...rtcSpeakingMeters.keys()])if(!prefix||key.startsWith(prefix))stopSpeakingMeter(key);
}
function watchSpeakingStream(stream,key) {
  if(!stream?.getAudioTracks?.().length||!key)return;
  const existing=rtcSpeakingMeters.get(key);
  if(existing?.stream===stream)return;
  if(existing)stopSpeakingMeter(key);
  const AudioContextCtor=window.AudioContext||window.webkitAudioContext;
  if(!AudioContextCtor)return;
  try{
    const context=new AudioContextCtor();
    const analyser=context.createAnalyser();
    analyser.fftSize=256;
    analyser.smoothingTimeConstant=.72;
    const source=context.createMediaStreamSource(stream);
    source.connect(analyser);
    context.resume?.().catch(()=>{});
    const data=new Uint8Array(analyser.fftSize);
    const meter={stream,context,source,analyser,raf:null,speaking:false};
    rtcSpeakingMeters.set(key,meter);
    const sample=()=>{
      if(rtcSpeakingMeters.get(key)!==meter)return;
      const live=stream.getAudioTracks().some(track=>track.readyState==='live'&&track.enabled);
      analyser.getByteTimeDomainData(data);
      let energy=0;
      for(const value of data){const normalized=(value-128)/128;energy+=normalized*normalized;}
      const rms=Math.sqrt(energy/data.length);
      const speaking=Boolean(live&&rms>.035);
      if(speaking!==meter.speaking){meter.speaking=speaking;syncSpeakingClass(key,speaking);}
      meter.raf=requestAnimationFrame(sample);
    };
    sample();
  }catch(error){
    console.warn('RTC speaking meter unavailable',error);
  }
}
function syncCallUiTicker(active=Boolean(callConnection||callStream)) {
  const update=()=>{
    document.querySelectorAll('[data-call-duration]').forEach(node=>{
      node.textContent=formatCallDuration(callStartedAt);
    });
  };
  if(!active){
    if(callUiTicker){clearInterval(callUiTicker);callUiTicker=null;}
    return;
  }
  update();
  if(!callUiTicker)callUiTicker=setInterval(update,1000);
}
function callStageMarkup(user) {
  const state=callVisualState();
  const peerName=callPeerName||currentDm||'Пользователь';
  const peerInitial=escapeHtml(peerName?.[0]?.toUpperCase()||'?');
  const selfInitial=escapeHtml(user?.name?.[0]?.toUpperCase()||'?');
  const reconnecting=state==='reconnecting';
  const muted=!callMicEnabled;
  const cameraOff=callVideo&&!callCameraEnabled;
  const controls=`<div class="rtc-control-dock">
    <button id="toggle-call-mic" class="rtc-dock-button ${muted?'off':''}" type="button" title="${muted?'Включить микрофон':'Выключить микрофон'}"><span>${muted?'🔇':'🎙'}</span><small>${muted?'Микрофон выкл.':'Микрофон'}</small></button>
    ${callVideo?`<button id="toggle-call-camera" class="rtc-dock-button ${cameraOff?'off':''}" type="button" title="${cameraOff?'Включить камеру':'Выключить камеру'}"><span>${cameraOff?'🚫':'📷'}</span><small>${cameraOff?'Камера выкл.':'Камера'}</small></button>`:''}
    <button id="end-call" class="rtc-dock-button end" type="button" title="Завершить звонок"><span>☎</span><small>Завершить</small></button>
  </div>`;
  if(callVideo){
    return `<section class="rtc-stage call-stage video-mode state-${state}" data-call-stage data-state="${state}">
      <div class="rtc-ambient rtc-ambient-a"></div><div class="rtc-ambient rtc-ambient-b"></div>
      <div class="rtc-stage-topbar"><div><span class="rtc-eyebrow">VESSEL CALL</span><h2>${escapeHtml(peerName)}</h2></div><div class="rtc-session-meta"><span class="rtc-state-pill ${reconnecting?'warning':''}"><i></i><span data-call-state-label>${escapeHtml(callVisualLabel())}</span></span><time data-call-duration>${formatCallDuration(callStartedAt)}</time></div></div>
      ${reconnecting?'<div class="rtc-reconnect-banner"><span>↻</span><div><b>Связь нестабильна</b><small>Vessel автоматически восстанавливает сигнал и ICE-маршрут.</small></div></div>':''}
      <div class="video-stage-grid">
        <div class="remote-video-tile" data-speaking-key="call-peer"><video id="remote-video" class="remote-video ${remoteCallStream?'':'hidden'}" autoplay playsinline></video><div class="video-placeholder ${remoteCallStream?'hidden':''}"><div class="participant-avatar xl">${peerInitial}</div><span>Ожидаем видео…</span></div><div class="video-label"><span class="speaking-dot"></span>${escapeHtml(peerName)}</div></div>
        <div class="local-preview ${cameraOff?'camera-off':''}" data-speaking-key="call-self"><video id="local-video" class="local-video ${callStream?'':'hidden'}" autoplay muted playsinline></video><div class="local-camera-fallback"><div class="participant-avatar">${selfInitial}</div><span>Камера выключена</span></div><div class="video-label">Ты</div></div>
      </div>${controls}</section>`;
  }
  return `<section class="rtc-stage call-stage audio-mode state-${state}" data-call-stage data-state="${state}">
    <div class="rtc-ambient rtc-ambient-a"></div><div class="rtc-ambient rtc-ambient-b"></div>
    <div class="rtc-stage-topbar"><div><span class="rtc-eyebrow">VESSEL AUDIO</span><h2>Звонок с ${escapeHtml(peerName)}</h2></div><div class="rtc-session-meta"><span class="rtc-state-pill ${reconnecting?'warning':''}"><i></i><span data-call-state-label>${escapeHtml(callVisualLabel())}</span></span><time data-call-duration>${formatCallDuration(callStartedAt)}</time></div></div>
    ${reconnecting?'<div class="rtc-reconnect-banner"><span>↻</span><div><b>Переподключаемся</b><small>Не завершай звонок — Vessel пытается вернуть соединение.</small></div></div>':''}
    <div class="audio-call-focus">
      <div class="audio-orbit orbit-one"></div><div class="audio-orbit orbit-two"></div>
      <div class="participant-avatar hero" data-speaking-key="call-peer">${peerInitial}<span class="speaking-ring"></span></div>
      <h3>${escapeHtml(peerName)}</h3><p>${escapeHtml(callVisualLabel())}</p>
      <div class="audio-wave" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i><i></i><i></i></div>
      <div class="self-audio-chip" data-speaking-key="call-self"><span class="participant-avatar">${selfInitial}</span><div><b>Ты</b><small>${muted?'Микрофон выключен':'Микрофон активен'}</small></div></div>
    </div>${controls}</section>`;
}
function voiceStageMarkup(user) {
  const state=voiceVisualState();
  const connected=state==='connected';
  const reconnecting=state==='reconnecting';
  const micOff=voiceStream?.getAudioTracks?.()[0]?.enabled===false;
  const participants=connected
    ? (voiceParticipants.length?voiceParticipants:[{id:user.id,name:user.name}])
    : [];
  const cards=participants.map(participant=>{
    const self=participant.id===user.id;
    const name=self?'Ты':(participant.name||'Участник');
    const initial=escapeHtml(name?.[0]?.toUpperCase()||'?');
    const key=`voice-${participant.id}`;
    return `<article class="voice-participant-card ${self?'self':''}" data-speaking-key="${escapeHtml(key)}"><div class="participant-avatar">${initial}<span class="speaking-ring"></span></div><div><b>${escapeHtml(name)}</b><small>${self?(micOff?'Микрофон выключен':'Ты в эфире'):'Подключён'}</small></div><span class="voice-card-level"><i></i><i></i><i></i></span></article>`;
  }).join('');
  const controls=connected
    ? `<div class="rtc-control-dock"><button id="mute-voice" class="rtc-dock-button ${micOff?'off':''}" type="button"><span>${micOff?'🔇':'🎙'}</span><small>${micOff?'Включить':'Микрофон'}</small></button><button id="deafen-voice" class="rtc-dock-button ${voiceDeafened?'off':''}" type="button"><span>${voiceDeafened?'🙉':'🎧'}</span><small>${voiceDeafened?'Включить звук':'Заглушить'}</small></button><button id="join-voice" class="rtc-dock-button end" type="button"><span>↙</span><small>Выйти</small></button></div>`
    : `<div class="rtc-control-dock single"><button id="join-voice" class="rtc-dock-button join" type="button"><span>🎙</span><small>${reconnecting?'Подождать':'Войти в комнату'}</small></button></div>`;
  return `<section class="rtc-stage voice-stage state-${state}" data-voice-stage data-state="${state}">
    <div class="rtc-ambient rtc-ambient-a"></div><div class="rtc-ambient rtc-ambient-b"></div>
    <div class="rtc-stage-topbar"><div><span class="rtc-eyebrow">VESSEL VOICE</span><h2>${escapeHtml(activeChannelName)}</h2><p>${escapeHtml(getActiveServer()?.name||'Vessel')}</p></div><span class="rtc-state-pill ${reconnecting?'warning':''}"><i></i><span data-voice-state-label>${escapeHtml(voiceVisualLabel())}</span></span></div>
    ${reconnecting?'<div class="rtc-reconnect-banner"><span>↻</span><div><b>Комната переподключается</b><small>Vessel восстанавливает Realtime и peer-соединения автоматически.</small></div></div>':''}
    <div class="voice-room-hero"><div class="voice-room-symbol">⌁</div><h3>${connected?'Вы в голосовой комнате':'Голосовая комната готова'}</h3><p>${connected?'Говори свободно — активные участники подсвечиваются в реальном времени.':'Подключись, чтобы увидеть участников и начать разговор.'}</p></div>
    <div class="voice-participant-grid">${cards||'<div class="voice-room-empty"><span>◇</span><b>Пока никого нет</b><small>Будь первым, кто подключится.</small></div>'}</div>
    ${controls}</section>`;
}
function syncRtcVisualRuntime() {
  const expected=new Map();
  if(callStream)expected.set('call-self',callStream);
  if(remoteCallStream)expected.set('call-peer',remoteCallStream);
  if(voiceStream&&savedUser?.id)expected.set(`voice-${savedUser.id}`,voiceStream);
  for(const [peerId,state] of voicePeers){
    const stream=state.audio?.srcObject;
    if(stream)expected.set(`voice-${peerId}`,stream);
  }
  for(const [key,meter] of [...rtcSpeakingMeters]){
    if(!expected.has(key)||expected.get(key)!==meter.stream)stopSpeakingMeter(key);
  }
  for(const [key,stream] of expected)watchSpeakingStream(stream,key);
  syncCallUiTicker(Boolean(callConnection||callStream));
  const callStage=document.querySelector('[data-call-stage]');
  if(callStage){
    const state=callVisualState();
    callStage.dataset.state=state;
    callStage.classList.toggle('state-reconnecting',state==='reconnecting');
    callStage.querySelectorAll('[data-call-state-label]').forEach(node=>node.textContent=callVisualLabel());
    const remote=document.querySelector('#remote-video');
    const placeholder=callStage.querySelector('.video-placeholder');
    if(remote)remote.classList.toggle('hidden',!remoteCallStream);
    if(placeholder)placeholder.classList.toggle('hidden',Boolean(remoteCallStream));
  }
  const voiceStage=document.querySelector('[data-voice-stage]');
  if(voiceStage)voiceStage.querySelectorAll('[data-voice-state-label]').forEach(node=>node.textContent=voiceVisualLabel());
}
'''
replace_once('RTC visual helpers', status_old, status_old + helpers)

call_actions_old = """  const callActions=callInProgress
    ? `<button id=\"toggle-call-mic\" class=\"call-control\" title=\"${callMicEnabled?'Выключить микрофон':'Включить микрофон'}\">${callMicEnabled?'🎙':'🔇'}</button>${callVideo?`<button id=\"toggle-call-camera\" class=\"call-control\" title=\"${callCameraEnabled?'Выключить камеру':'Включить камеру'}\">${callCameraEnabled?'📷':'🚫'}</button>`:''}<button id=\"end-call\" class=\"hangup\" title=\"Завершить звонок\">☎</button>`
    : (!friendsOpen&&activeDmId&&activeDmIsFriend) ? `<button id=\"audio-call\" title=\"Аудиозвонок\">📞</button><button id=\"video-call\" title=\"Видеозвонок\">🎥</button>` : '';
"""
call_actions_new = """  const callActions=!callInProgress&&(!friendsOpen&&activeDmId&&activeDmIsFriend)
    ? `<button id=\"audio-call\" title=\"Аудиозвонок\">📞</button><button id=\"video-call\" title=\"Видеозвонок\">🎥</button>`
    : '';
  const rtcStage=callInProgress
    ? callStageMarkup(user)
    : (!friendsOpen&&!activeDmId&&activeChannelKind==='voice' ? voiceStageMarkup(user) : '');
"""
replace_once('header call actions', call_actions_old, call_actions_new)

voice_controls_pattern = re.compile(
    r'\$\{callActions\}<button id=\\"join-voice\\" class=\\"join-voice \$\{!friendsOpen&&activeChannelKind===\'voice\'\?\'\':\'hidden\'\}\\">.*?<button id=\\"search-button\\"',
    re.S
)
main, count = voice_controls_pattern.subn('${callActions}<button id=\\"search-button\\"', main, count=1)
if count != 1:
    raise SystemExit(f'Voice/calls UI source drift at header voice controls: expected 1, found {count}')

videos_old = """<video id=\"remote-video\" class=\"remote-video ${remoteCallStream?'':'hidden'}\" autoplay playsinline></video><video id=\"local-video\" class=\"local-video ${callStream||voiceStream?.getVideoTracks().length?'':'hidden'}\" autoplay muted playsinline></video>"""
replace_once('legacy floating videos', videos_old, '${rtcStage}')

incoming_old = """${incomingCall?`<div class=\"modal call-modal\" id=\"incoming-call-modal\"><div class=\"modal-card\"><div class=\"call-avatar\">${escapeHtml(incomingCall.name?.[0]?.toUpperCase()||'?')}</div><h2>${incomingCall.video?'Видеозвонок':'Аудиозвонок'}</h2><p>${escapeHtml(incomingCall.name)} звонит тебе в Vessel.</p><div class=\"call-actions\"><button class=\"danger\" id=\"reject-call\" type=\"button\">Отклонить</button><button class=\"primary\" id=\"accept-call\" type=\"button\">Принять</button></div></div></div>`:''}"""
incoming_new = """${incomingCall?`<div class=\"modal call-modal incoming-call-modal\" id=\"incoming-call-modal\"><div class=\"modal-card incoming-call-card\"><span class=\"rtc-eyebrow\">ВХОДЯЩИЙ ВЫЗОВ</span><div class=\"incoming-call-orbit\"><i></i><i></i><div class=\"call-avatar\">${escapeHtml(incomingCall.name?.[0]?.toUpperCase()||'?')}</div></div><span class=\"incoming-call-type\">${incomingCall.video?'🎥 Видеозвонок':'🎙 Аудиозвонок'}</span><h2>${escapeHtml(incomingCall.name)}</h2><p>звонит тебе в Vessel</p><div class=\"incoming-call-wave\"><i></i><i></i><i></i><i></i><i></i></div><div class=\"call-actions\"><button class=\"danger incoming-reject\" id=\"reject-call\" type=\"button\"><span>☎</span>Отклонить</button><button class=\"primary incoming-accept\" id=\"accept-call\" type=\"button\"><span>${incomingCall.video?'🎥':'🎙'}</span>Принять</button></div></div></div>`:''}"""
replace_once('incoming call modal', incoming_old, incoming_new)

render_sync_old = """  const nextMessagesPane=document.querySelector('.messages');
"""
replace_once('RTC runtime sync', render_sync_old, "  syncRtcVisualRuntime();\n" + render_sync_old)

connected_old = """    if(state==='connected'){clearCallDisconnectTimer();callIceRestartAttempts=0;callIceRestartInFlight=false;return;}
    if(state==='closed'){clearCallDisconnectTimer();return;}
    if(['failed','disconnected'].includes(state))scheduleCallDisconnectCleanup(connection,user,peerId,video);
"""
connected_new = """    if(state==='connected'){clearCallDisconnectTimer();callIceRestartAttempts=0;callIceRestartInFlight=false;if(!callStartedAt)callStartedAt=Date.now();render();return;}
    if(state==='closed'){clearCallDisconnectTimer();syncRtcVisualRuntime();return;}
    if(['failed','disconnected'].includes(state)){render();scheduleCallDisconnectCleanup(connection,user,peerId,video);}
"""
replace_once('call connection visual state', connected_old, connected_new)

end_old = """  callMicEnabled=true;
  callCameraEnabled=true;
  render();
"""
end_new = """  callMicEnabled=true;
  callCameraEnabled=true;
  callStartedAt=0;
  stopSpeakingMeters('call-');
  syncCallUiTicker(false);
  render();
"""
replace_once('call visual cleanup', end_old, end_new)

leave_voice_old = """  voiceParticipants=[];voiceChannelId=null;voiceServerId=null;voiceDeafened=false;
"""
replace_once('voice visual cleanup', leave_voice_old, "  stopSpeakingMeters('voice-');\n" + leave_voice_old)

presence_old = """  const status=document.querySelector('.voice-status');
  if(status)status.textContent=`🎙 В голосовой комнате: ${Math.max(1,voiceParticipants.length)}`;
"""
presence_new = """  const status=document.querySelector('.voice-status');
  if(status)status.textContent=`🎙 В голосовой комнате: ${Math.max(1,voiceParticipants.length)}`;
  if(activeChannelKind==='voice'&&voiceChannelId===activeChannelId)render();
"""
replace_once('voice participant render', presence_old, presence_new)

reconnect_context_old = """  voiceReconnectContext={channelId,serverId};
"""
replace_once('voice reconnect indicator', reconnect_context_old, reconnect_context_old + "  render();\n")

ontrack_old = """  callConnection.ontrack=e=>{remoteCallStream=e.streams[0];const el=document.querySelector('#remote-video');if(el){el.srcObject=remoteCallStream;el.play().catch(()=>{});} };
"""
ontrack_new = """  callConnection.ontrack=e=>{remoteCallStream=e.streams[0];const el=document.querySelector('#remote-video');if(el){el.srcObject=remoteCallStream;el.play().catch(()=>{});}syncRtcVisualRuntime();};
"""
replace_once('call remote speaking meter', ontrack_old, ontrack_new)

foundation = r'''

/* VESSEL_UI_VOICE_CALLS_V1 */
.rtc-stage{position:relative;flex:1;min-height:0;margin:14px 18px 18px;border:1px solid rgba(214,230,255,.08);border-radius:26px;background:radial-gradient(circle at 18% 10%,rgba(59,231,255,.08),transparent 34%),radial-gradient(circle at 85% 20%,rgba(139,92,255,.12),transparent 34%),linear-gradient(145deg,rgba(9,14,24,.97),rgba(10,12,20,.92));box-shadow:0 30px 80px rgba(0,0,0,.32),inset 0 1px 0 rgba(255,255,255,.04);overflow:hidden;display:flex;flex-direction:column;isolation:isolate}
.rtc-stage+.messages,.rtc-stage~.composer{display:none!important}.rtc-ambient{position:absolute;border-radius:50%;filter:blur(70px);pointer-events:none;opacity:.38;z-index:-1}.rtc-ambient-a{width:340px;height:340px;left:-120px;top:-140px;background:rgba(59,231,255,.26)}.rtc-ambient-b{width:380px;height:380px;right:-150px;bottom:-180px;background:rgba(139,92,255,.28)}
.rtc-stage-topbar{min-height:82px;padding:20px 24px;display:flex;justify-content:space-between;gap:20px;align-items:center;border-bottom:1px solid rgba(255,255,255,.055);background:linear-gradient(180deg,rgba(255,255,255,.025),transparent);z-index:2}.rtc-stage-topbar h2{margin:4px 0 0;font-size:clamp(18px,2vw,25px);letter-spacing:-.035em}.rtc-stage-topbar p{margin:5px 0 0;color:var(--v-text-3,#8993a8);font-size:11px}.rtc-eyebrow{color:#8ddff1;font-size:9px;font-weight:800;letter-spacing:.18em}.rtc-session-meta{display:flex;align-items:center;gap:10px}.rtc-session-meta time{min-width:60px;padding:8px 10px;border:1px solid rgba(255,255,255,.07);border-radius:12px;background:rgba(3,7,13,.35);color:#c9d0e0;font-size:11px;font-variant-numeric:tabular-nums;text-align:center}
.rtc-state-pill{display:inline-flex;align-items:center;gap:7px;padding:8px 11px;border:1px solid rgba(71,214,164,.16);border-radius:999px;background:rgba(42,160,123,.08);color:#79e6bf;font-size:10px;font-weight:700;white-space:nowrap}.rtc-state-pill i{width:7px;height:7px;border-radius:50%;background:currentColor;box-shadow:0 0 12px currentColor}.rtc-state-pill.warning{color:#ffd27e;border-color:rgba(255,190,94,.18);background:rgba(181,113,24,.10)}
.rtc-reconnect-banner{margin:14px 20px 0;padding:12px 14px;border:1px solid rgba(255,196,92,.16);border-radius:15px;background:linear-gradient(120deg,rgba(148,88,18,.18),rgba(255,196,92,.055));display:flex;align-items:center;gap:12px;color:#ffe0a7;z-index:3}.rtc-reconnect-banner>span{font-size:21px;animation:rtcReconnectSpin 1.1s linear infinite}.rtc-reconnect-banner b,.rtc-reconnect-banner small{display:block}.rtc-reconnect-banner small{margin-top:3px;color:#b8a98f;font-size:10px}
.video-mode{margin:0;border-radius:0;border-width:0}.video-stage-grid{position:relative;flex:1;min-height:280px;padding:16px;display:grid}.remote-video-tile{position:relative;min-height:100%;border:1px solid rgba(255,255,255,.07);border-radius:24px;overflow:hidden;background:radial-gradient(circle at center,rgba(92,76,188,.18),rgba(3,6,11,.96) 60%);box-shadow:inset 0 1px 0 rgba(255,255,255,.04)}.rtc-stage .remote-video{position:absolute;inset:0;width:100%;height:100%;max-height:none;object-fit:cover;border-radius:0;background:#05070a;z-index:0;box-shadow:none}.video-placeholder{position:absolute;inset:0;display:grid;place-content:center;justify-items:center;gap:14px;color:#8d96aa;font-size:11px}.video-label{position:absolute;left:14px;bottom:14px;display:inline-flex;align-items:center;gap:7px;padding:7px 10px;border:1px solid rgba(255,255,255,.08);border-radius:10px;background:rgba(4,7,12,.56);backdrop-filter:blur(14px);color:#f3f6fb;font-size:10px;z-index:4}.speaking-dot{width:7px;height:7px;border-radius:50%;background:#647084;transition:.18s}.is-speaking .speaking-dot{background:#6ff0c0;box-shadow:0 0 12px rgba(111,240,192,.9)}
.local-preview{position:absolute;right:30px;bottom:90px;width:min(230px,28vw);aspect-ratio:16/10;border:1px solid rgba(255,255,255,.11);border-radius:18px;overflow:hidden;background:rgba(5,8,14,.96);box-shadow:0 18px 50px rgba(0,0,0,.48);z-index:6}.rtc-stage .local-video{position:absolute;inset:0;width:100%;height:100%;max-height:none;margin:0;border:0;border-radius:0;object-fit:cover;transform:scaleX(-1);background:#05070a}.local-camera-fallback{position:absolute;inset:0;display:none;place-content:center;justify-items:center;gap:8px;color:#778297;font-size:10px}.local-preview.camera-off .local-video{opacity:0}.local-preview.camera-off .local-camera-fallback{display:grid}
.audio-call-focus{flex:1;min-height:320px;display:flex;flex-direction:column;align-items:center;justify-content:center;position:relative;padding:40px 20px 120px;text-align:center}.audio-call-focus h3{margin:22px 0 5px;font-size:clamp(25px,3vw,38px);letter-spacing:-.045em}.audio-call-focus>p{margin:0;color:#8993a8;font-size:11px}.audio-orbit{position:absolute;left:50%;top:46%;border:1px solid rgba(126,111,255,.12);border-radius:50%;transform:translate(-50%,-50%);pointer-events:none}.orbit-one{width:260px;height:260px;animation:rtcOrbitBreath 4.2s ease-in-out infinite}.orbit-two{width:360px;height:360px;animation:rtcOrbitBreath 4.2s ease-in-out -1.5s infinite}
.participant-avatar{width:54px;height:54px;display:grid;place-items:center;border-radius:19px;background:linear-gradient(135deg,#5f6df2,#9a67ef);color:white;font-weight:800;font-size:18px;position:relative;flex:none;box-shadow:0 12px 36px rgba(58,56,160,.28)}.participant-avatar.xl{width:92px;height:92px;border-radius:30px;font-size:31px}.participant-avatar.hero{width:112px;height:112px;border-radius:38px;font-size:38px;box-shadow:0 24px 70px rgba(68,63,196,.32);z-index:2}.speaking-ring{position:absolute;inset:-7px;border:2px solid transparent;border-radius:inherit;pointer-events:none}.is-speaking.participant-avatar,.is-speaking .participant-avatar{box-shadow:0 0 0 4px rgba(77,234,194,.10),0 0 38px rgba(77,234,194,.32),0 18px 52px rgba(0,0,0,.28)}.is-speaking .speaking-ring,.participant-avatar.is-speaking .speaking-ring{border-color:rgba(97,240,202,.72);animation:rtcSpeakingPulse 1.1s ease-out infinite}
.audio-wave{height:34px;display:flex;align-items:center;gap:5px;margin-top:22px}.audio-wave i{width:3px;height:9px;border-radius:4px;background:linear-gradient(#6fe5ff,#9e77ff);opacity:.45;animation:rtcWave 1.05s ease-in-out infinite}.audio-wave i:nth-child(2),.audio-wave i:nth-child(6){animation-delay:-.2s;height:17px}.audio-wave i:nth-child(3),.audio-wave i:nth-child(5){animation-delay:-.45s;height:25px}.audio-wave i:nth-child(4){animation-delay:-.65s;height:31px}.self-audio-chip{margin-top:22px;padding:9px 13px 9px 9px;border:1px solid rgba(255,255,255,.07);border-radius:16px;background:rgba(255,255,255,.035);display:flex;align-items:center;gap:10px;text-align:left}.self-audio-chip .participant-avatar{width:38px;height:38px;border-radius:12px;font-size:13px}.self-audio-chip b,.self-audio-chip small{display:block}.self-audio-chip small{margin-top:2px;color:#7f899e;font-size:9px}
.rtc-control-dock{position:absolute;left:50%;bottom:22px;transform:translateX(-50%);z-index:9;display:flex;align-items:center;gap:9px;padding:9px;border:1px solid rgba(255,255,255,.085);border-radius:20px;background:rgba(8,12,20,.68);backdrop-filter:blur(22px) saturate(1.2);box-shadow:0 18px 50px rgba(0,0,0,.42),inset 0 1px 0 rgba(255,255,255,.055)}.rtc-control-dock.single{min-width:200px;justify-content:center}.rtc-dock-button{min-width:74px;height:58px;padding:7px 11px;border:1px solid rgba(255,255,255,.07);border-radius:15px;background:rgba(255,255,255,.05);color:#dfe5f1;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:3px;cursor:pointer;transition:transform .18s ease,background .18s ease,border-color .18s ease,box-shadow .18s ease}.rtc-dock-button:hover{transform:translateY(-2px);background:rgba(255,255,255,.09);border-color:rgba(155,195,255,.16)}.rtc-dock-button span{font-size:19px;line-height:1}.rtc-dock-button small{font-size:8px;color:#9ba6ba;white-space:nowrap}.rtc-dock-button.off{background:rgba(139,69,92,.18);border-color:rgba(255,114,151,.16)}.rtc-dock-button.end{background:linear-gradient(145deg,rgba(222,68,102,.78),rgba(151,39,68,.78));border-color:rgba(255,126,153,.2);color:#fff}.rtc-dock-button.end small{color:#ffe2e8}.rtc-dock-button.join{min-width:170px;background:linear-gradient(120deg,rgba(45,180,143,.65),rgba(67,120,211,.58));color:#fff}.rtc-dock-button.join small{color:#e8fffa}
.voice-room-hero{padding:34px 24px 18px;text-align:center}.voice-room-symbol{width:68px;height:68px;margin:0 auto 14px;border-radius:24px;display:grid;place-items:center;background:linear-gradient(145deg,rgba(66,220,198,.18),rgba(117,93,238,.22));border:1px solid rgba(121,230,220,.12);color:#8ce7df;font-size:34px;box-shadow:0 20px 55px rgba(44,80,153,.14)}.voice-room-hero h3{margin:0;font-size:22px;letter-spacing:-.03em}.voice-room-hero p{max-width:500px;margin:8px auto 0;color:#8590a4;font-size:11px;line-height:1.6}.voice-participant-grid{width:min(820px,calc(100% - 36px));margin:0 auto 110px;display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:10px;overflow:auto}.voice-participant-card{min-height:76px;padding:11px 13px;border:1px solid rgba(255,255,255,.065);border-radius:18px;background:linear-gradient(145deg,rgba(255,255,255,.05),rgba(255,255,255,.018));display:flex;align-items:center;gap:11px;transition:border-color .18s ease,box-shadow .18s ease,transform .18s ease}.voice-participant-card:hover{transform:translateY(-2px);border-color:rgba(121,203,255,.14)}.voice-participant-card.is-speaking{border-color:rgba(94,236,196,.28);box-shadow:0 0 30px rgba(74,224,187,.09),inset 0 1px 0 rgba(255,255,255,.06)}.voice-participant-card b,.voice-participant-card small{display:block}.voice-participant-card small{margin-top:3px;color:#7d879a;font-size:9px}.voice-card-level{margin-left:auto;display:flex;align-items:end;gap:2px;height:18px}.voice-card-level i{width:2px;height:5px;border-radius:2px;background:#566174}.voice-card-level i:nth-child(2){height:10px}.voice-card-level i:nth-child(3){height:15px}.voice-participant-card.is-speaking .voice-card-level i{background:#69e8c0;animation:rtcWave .85s ease-in-out infinite}.voice-room-empty{grid-column:1/-1;min-height:150px;display:grid;place-content:center;justify-items:center;gap:6px;border:1px dashed rgba(255,255,255,.07);border-radius:20px;color:#7f899d;text-align:center}.voice-room-empty>span{font-size:28px;color:#7783a0}.voice-room-empty b{color:#cbd1df}.voice-room-empty small{font-size:9px}
.incoming-call-modal{backdrop-filter:blur(12px)}.incoming-call-card{width:min(430px,100%);padding:34px 30px 28px!important;text-align:center;border-color:rgba(137,126,255,.18)!important;background:radial-gradient(circle at 50% 0,rgba(108,87,235,.20),transparent 42%),linear-gradient(155deg,rgba(18,23,36,.98),rgba(10,13,22,.98))!important;overflow:hidden}.incoming-call-orbit{position:relative;width:132px;height:132px;margin:20px auto 12px;display:grid;place-items:center}.incoming-call-orbit>i{position:absolute;inset:8px;border:1px solid rgba(120,105,255,.22);border-radius:40px;animation:rtcIncomingPulse 1.8s ease-out infinite}.incoming-call-orbit>i:nth-child(2){inset:-8px;animation-delay:-.75s}.incoming-call-card .call-avatar{margin:0;width:76px;height:76px;border-radius:26px;font-size:27px;z-index:2}.incoming-call-type{display:inline-flex;margin:4px 0 5px;padding:6px 9px;border-radius:999px;background:rgba(255,255,255,.05);color:#aeb8ca;font-size:9px}.incoming-call-card h2{margin:8px 0 3px;font-size:25px}.incoming-call-card>p{margin:0 0 12px!important;color:#8993a7!important}.incoming-call-wave{height:26px;display:flex;align-items:center;justify-content:center;gap:4px;margin-bottom:18px}.incoming-call-wave i{width:3px;height:8px;border-radius:3px;background:#8c7eff;animation:rtcWave 1s ease-in-out infinite}.incoming-call-wave i:nth-child(2),.incoming-call-wave i:nth-child(4){height:16px;animation-delay:-.2s}.incoming-call-wave i:nth-child(3){height:23px;animation-delay:-.5s}.incoming-call-card .call-actions{gap:10px}.incoming-call-card .call-actions button{height:54px;border-radius:15px;display:flex;align-items:center;justify-content:center;gap:8px;font-size:12px}.incoming-call-card .call-actions button span{font-size:17px}.incoming-reject{margin:0!important}.incoming-accept{margin:0!important;background:linear-gradient(120deg,#3cbf94,#6778ef)!important}
@keyframes rtcWave{0%,100%{transform:scaleY(.55);opacity:.35}50%{transform:scaleY(1.15);opacity:1}}@keyframes rtcOrbitBreath{0%,100%{opacity:.25;transform:translate(-50%,-50%) scale(.9)}50%{opacity:.7;transform:translate(-50%,-50%) scale(1.06)}}@keyframes rtcSpeakingPulse{0%{opacity:.8;transform:scale(.96)}100%{opacity:0;transform:scale(1.18)}}@keyframes rtcIncomingPulse{0%{opacity:.7;transform:scale(.85)}100%{opacity:0;transform:scale(1.22)}}@keyframes rtcReconnectSpin{to{transform:rotate(360deg)}}
@media(max-width:760px){.rtc-stage{margin:8px;border-radius:20px}.video-mode{margin:0;border-radius:0}.rtc-stage-topbar{min-height:70px;padding:14px 15px;align-items:flex-start}.rtc-session-meta{gap:6px;align-items:flex-end;flex-direction:column}.rtc-state-pill{max-width:165px;overflow:hidden;text-overflow:ellipsis}.video-stage-grid{padding:8px}.remote-video-tile{border-radius:18px}.local-preview{right:18px;bottom:88px;width:124px;border-radius:14px}.rtc-control-dock{bottom:14px;gap:6px;padding:7px;border-radius:17px}.rtc-dock-button{min-width:58px;height:52px;padding:6px 8px}.rtc-dock-button small{font-size:7px}.audio-call-focus{padding:25px 12px 105px}.participant-avatar.hero{width:92px;height:92px;border-radius:31px;font-size:31px}.orbit-one{width:210px;height:210px}.orbit-two{width:285px;height:285px}.voice-room-hero{padding:24px 14px 15px}.voice-participant-grid{width:calc(100% - 20px);grid-template-columns:1fr;margin-bottom:94px}}
@media(max-width:520px){.rtc-stage-topbar h2{font-size:17px}.rtc-stage-topbar .rtc-eyebrow{font-size:8px}.rtc-session-meta time{display:none}.rtc-reconnect-banner{margin:9px 10px 0;padding:9px 10px}.rtc-reconnect-banner small{display:none}.local-preview{width:105px;right:12px;bottom:80px}.rtc-control-dock{width:calc(100% - 20px);justify-content:center}.rtc-dock-button{flex:1;min-width:0;max-width:92px}.rtc-dock-button.join{max-width:none}.audio-call-focus h3{font-size:25px}.incoming-call-card{padding:28px 20px 22px!important}}
@media (prefers-reduced-motion: reduce){.audio-orbit,.audio-wave i,.voice-participant-card.is-speaking .voice-card-level i,.incoming-call-orbit>i,.incoming-call-wave i,.rtc-reconnect-banner>span,.is-speaking .speaking-ring,.participant-avatar.is-speaking .speaking-ring{animation:none!important}.rtc-dock-button,.voice-participant-card{transition:none!important}}
'''

style += foundation
MAIN_PATH.write_text(main, encoding='utf-8')
STYLE_PATH.write_text(style, encoding='utf-8')
print('Applied Vessel UI Batch 3: Voice + Calls')
