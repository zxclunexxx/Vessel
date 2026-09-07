from pathlib import Path

path = Path('src/main.js')
main = path.read_text(encoding='utf-8')

replacements = [
    ('video stage state', '<section class="rtc-stage call-stage video-mode state-${state}" data-call-stage>', '<section class="rtc-stage call-stage video-mode state-${state}" data-call-stage data-state="${state}">'),
    ('audio stage state', '<section class="rtc-stage call-stage audio-mode state-${state}" data-call-stage>', '<section class="rtc-stage call-stage audio-mode state-${state}" data-call-stage data-state="${state}">'),
    ('voice stage state', '<section class="rtc-stage voice-stage state-${state}" data-voice-stage>', '<section class="rtc-stage voice-stage state-${state}" data-voice-stage data-state="${state}">'),
]
for label, old, new in replacements:
    if new in main:
        continue
    count = main.count(old)
    if count != 1:
        raise SystemExit(f'RTC visual refresh source drift at {label}: expected 1, found {count}')
    main = main.replace(old, new, 1)

old_interval = """setInterval(()=>{const video=document.querySelector('#local-video');const stream=callStream||voiceStream;if(video&&stream&&video.srcObject!==stream){video.srcObject=stream;video.play().catch(()=>{});}const remote=document.querySelector('#remote-video');if(remote&&remoteCallStream&&remote.srcObject!==remoteCallStream){remote.srcObject=remoteCallStream;remote.play().catch(()=>{});}},500);"""
new_interval = """setInterval(()=>{
  const callStage=document.querySelector('[data-call-stage]');
  if(callStage&&callStage.dataset.state!==callVisualState()){render();return;}
  const voiceStage=document.querySelector('[data-voice-stage]');
  if(voiceStage&&voiceStage.dataset.state!==voiceVisualState()){render();return;}
  syncRtcVisualRuntime();
  const video=document.querySelector('#local-video');
  const stream=callStream||voiceStream;
  if(video&&stream&&video.srcObject!==stream){video.srcObject=stream;video.play().catch(()=>{});}
  const remote=document.querySelector('#remote-video');
  if(remote&&remoteCallStream&&remote.srcObject!==remoteCallStream){remote.srcObject=remoteCallStream;remote.play().catch(()=>{});}
},500);"""
if new_interval not in main:
    count = main.count(old_interval)
    if count != 1:
        raise SystemExit(f'RTC visual refresh interval source drift: expected 1, found {count}')
    main = main.replace(old_interval, new_interval, 1)

path.write_text(main, encoding='utf-8')
print('Enabled live Vessel call/voice state refresh without touching RTC recovery logic')
