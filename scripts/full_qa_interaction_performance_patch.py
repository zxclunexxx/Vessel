from pathlib import Path

root = Path(__file__).resolve().parents[1]
main_path = root / 'src' / 'main.js'
text = main_path.read_text(encoding='utf-8')
marker = '/* VESSEL_FULL_QA_INTERACTION_PERF_V1 */'
if marker in text:
    print('Full QA interaction/performance patch already applied')
    raise SystemExit(0)

old_globals = """let callStartedAt = 0;\nlet callUiTicker = null;\nconst rtcSpeakingMeters = new Map();\n"""
new_globals = """let callStartedAt = 0;\nlet callUiTicker = null;\nlet rtcVisualRuntimeTicker = null;\nconst rtcSpeakingMeters = new Map();\n"""
if old_globals not in text:
    raise SystemExit('RTC UI ticker globals anchor not found')
text = text.replace(old_globals, new_globals, 1)

sync_tail = """  const voiceStage=document.querySelector('[data-voice-stage]');if(voiceStage)voiceStage.querySelectorAll('[data-voice-state-label]').forEach(node=>node.textContent=voiceVisualLabel());\n}\nfunction vesselDialog"""
helpers = """  const voiceStage=document.querySelector('[data-voice-stage]');if(voiceStage)voiceStage.querySelectorAll('[data-voice-state-label]').forEach(node=>node.textContent=voiceVisualLabel());\n  syncRtcVisualRuntimeTicker();\n}\nfunction rtcVisualRuntimeActive(){return Boolean(callConnection||callStream||voiceStream||voiceRoom||voiceReconnectContext);}\nfunction runRtcVisualRuntimeTick(){\n  if(!rtcVisualRuntimeActive()){syncRtcVisualRuntimeTicker(false);return;}\n  const callStage=document.querySelector('[data-call-stage]');\n  if(callStage&&callStage.dataset.state!==callVisualState()){render();return;}\n  const voiceStage=document.querySelector('[data-voice-stage]');\n  if(voiceStage&&voiceStage.dataset.state!==voiceVisualState()){render();return;}\n  syncRtcVisualRuntime();\n  const video=document.querySelector('#local-video');\n  const stream=callStream||voiceStream;\n  if(video&&stream&&video.srcObject!==stream){video.srcObject=stream;video.play().catch(()=>{});}\n  const remote=document.querySelector('#remote-video');\n  if(remote&&remoteCallStream&&remote.srcObject!==remoteCallStream){remote.srcObject=remoteCallStream;remote.play().catch(()=>{});}\n}\nfunction syncRtcVisualRuntimeTicker(active=rtcVisualRuntimeActive()){\n  if(!active){if(rtcVisualRuntimeTicker){clearInterval(rtcVisualRuntimeTicker);rtcVisualRuntimeTicker=null;}return;}\n  if(!rtcVisualRuntimeTicker)rtcVisualRuntimeTicker=setInterval(runRtcVisualRuntimeTick,500);\n}\nfunction vesselDialog"""
if sync_tail not in text:
    raise SystemExit('syncRtcVisualRuntime tail anchor not found')
text = text.replace(sync_tail, helpers, 1)

reset_old = """  stopSpeakingMeters();\n  syncCallUiTicker(false);\n  callStartedAt=0;\n"""
reset_new = """  stopSpeakingMeters();\n  syncCallUiTicker(false);\n  syncRtcVisualRuntimeTicker(false);\n  callStartedAt=0;\n"""
if reset_old not in text:
    raise SystemExit('authenticated reset RTC cleanup anchor not found')
text = text.replace(reset_old, reset_new, 1)

render_anchor = "function render() {\n"
render_replacement = "function render() {\n  document.body.classList.remove('mobile-drawer-open');\n  document.querySelector('.mobile-drawer-scrim')?.remove();\n"
if render_anchor not in text:
    raise SystemExit('render anchor not found')
text = text.replace(render_anchor, render_replacement, 1)

legacy_close = "document.querySelector('.channels')?.classList.remove('mobile-open');"
legacy_count = text.count(legacy_close)
if legacy_count != 3:
    raise SystemExit(f'Expected exactly 3 legacy mobile drawer closes, found {legacy_count}')
text = text.replace(legacy_close, 'setMobileDrawerOpen(false);')

old_settings_open = """  const modal = document.querySelector('#settings-modal');\n  document.querySelector('#profile-settings').addEventListener('click', () => modal.classList.remove('hidden'));\n  const setMobileDrawerOpen=open=>{\n"""
new_settings_open = """  const modal = document.querySelector('#settings-modal');\n  let settingsReturnFocus=null;\n  const openSettingsModal=trigger=>{\n    settingsReturnFocus=trigger||document.activeElement;\n    modal.classList.remove('hidden');\n    requestAnimationFrame(()=>modal.querySelector('input,select,button')?.focus());\n  };\n  const closeSettingsModal=()=>{\n    modal.classList.add('hidden');\n    if(settingsReturnFocus?.isConnected&&typeof settingsReturnFocus.focus==='function')settingsReturnFocus.focus();\n    settingsReturnFocus=null;\n  };\n  modal.setAttribute('role','dialog');\n  modal.setAttribute('aria-modal','true');\n  modal.addEventListener('click',event=>{if(event.target===modal)closeSettingsModal();});\n  modal.addEventListener('keydown',event=>{if(event.key==='Escape'){event.preventDefault();closeSettingsModal();}});\n  document.querySelector('#profile-settings').addEventListener('click', event => openSettingsModal(event.currentTarget));\n  const setMobileDrawerOpen=open=>{\n"""
if old_settings_open not in text:
    raise SystemExit('settings modal open anchor not found')
text = text.replace(old_settings_open, new_settings_open, 1)

if "document.querySelector('#close-settings').addEventListener('click', () => modal.classList.add('hidden'));" not in text:
    raise SystemExit('settings modal close anchor not found')
text = text.replace("document.querySelector('#close-settings').addEventListener('click', () => modal.classList.add('hidden'));", "document.querySelector('#close-settings').addEventListener('click', closeSettingsModal);", 1)

if "    modal.classList.add('hidden');\n    vesselNotice('Профиль сохранён.','success');" not in text:
    raise SystemExit('settings save close anchor not found')
text = text.replace("    modal.classList.add('hidden');\n    vesselNotice('Профиль сохранён.','success');", "    closeSettingsModal();\n    vesselNotice('Профиль сохранён.','success');", 1)

if "document.querySelector('#head-settings').addEventListener('click',()=>modal.classList.remove('hidden'));" not in text:
    raise SystemExit('header settings modal open anchor not found')
text = text.replace("document.querySelector('#head-settings').addEventListener('click',()=>modal.classList.remove('hidden'));", "document.querySelector('#head-settings').addEventListener('click',event=>openSettingsModal(event.currentTarget));", 1)

old_interval = """setInterval(()=>{\n  const callStage=document.querySelector('[data-call-stage]');\n  if(callStage&&callStage.dataset.state!==callVisualState()){render();return;}\n  const voiceStage=document.querySelector('[data-voice-stage]');\n  if(voiceStage&&voiceStage.dataset.state!==voiceVisualState()){render();return;}\n  syncRtcVisualRuntime();\n  const video=document.querySelector('#local-video');\n  const stream=callStream||voiceStream;\n  if(video&&stream&&video.srcObject!==stream){video.srcObject=stream;video.play().catch(()=>{});}\n  const remote=document.querySelector('#remote-video');\n  if(remote&&remoteCallStream&&remote.srcObject!==remoteCallStream){remote.srcObject=remoteCallStream;remote.play().catch(()=>{});}\n},500);"""
if old_interval not in text:
    raise SystemExit('legacy global RTC polling interval anchor not found')
text = text.replace(old_interval, marker, 1)

main_path.write_text(text, encoding='utf-8')
print('Applied Vessel Full QA interaction/performance patch')

# Touching this migration after smoke-alignment intentionally retriggers the autonomous verifier.
