from pathlib import Path

path = Path('src/main.js')
main = path.read_text(encoding='utf-8')

start_token = 'function voiceStageMarkup(user){'
end_token = 'function syncRtcVisualRuntime()'
if start_token not in main or end_token not in main:
    raise SystemExit('Voice/calls runtime is missing before join-control normalization')

start = main.index(start_token)
end = main.index(end_token, start)
segment = main[start:end]

old = """  const controls=connected?`<div class=\"rtc-control-dock\"><button id=\"mute-voice\" class=\"rtc-dock-button ${micOff?'off':''}\" type=\"button\"><span>${micOff?'🔇':'🎙'}</span><small>Микрофон</small></button><button id=\"deafen-voice\" class=\"rtc-dock-button ${voiceDeafened?'off':''}\" type=\"button\"><span>${voiceDeafened?'🙉':'🎧'}</span><small>Звук</small></button><button id=\"join-voice\" class=\"rtc-dock-button end\" type=\"button\"><span>↙</span><small>Выйти</small></button></div>`:`<div class=\"rtc-control-dock single\"><button id=\"join-voice\" class=\"rtc-dock-button join\" type=\"button\"><span>🎙</span><small>${reconnecting?'Подождать':'Войти в комнату'}</small></button></div>`;
"""
new = """  const controls=`<div class=\"rtc-control-dock ${connected?'':'single'}\">${connected?`<button id=\"mute-voice\" class=\"rtc-dock-button ${micOff?'off':''}\" type=\"button\"><span>${micOff?'🔇':'🎙'}</span><small>Микрофон</small></button><button id=\"deafen-voice\" class=\"rtc-dock-button ${voiceDeafened?'off':''}\" type=\"button\"><span>${voiceDeafened?'🙉':'🎧'}</span><small>Звук</small></button>`:''}<button id=\"join-voice\" class=\"rtc-dock-button ${connected?'end':'join'}\" type=\"button\"><span>${connected?'↙':'🎙'}</span><small>${connected?'Выйти':reconnecting?'Подождать':'Войти в комнату'}</small></button></div>`;
"""

count = segment.count(old)
if count == 0 and segment.count('id="join-voice"') == 1:
    print('Vessel voice join control already normalized')
    raise SystemExit(0)
if count != 1:
    raise SystemExit(f'Voice join-control source drift: expected exact generated block once, found {count}')

segment = segment.replace(old, new, 1)
main = main[:start] + segment + main[end:]

if main.count('id="join-voice"') != 1:
    raise SystemExit(f'Voice join control invariant failed after normalization: found {main.count("id=\"join-voice\"")}')

path.write_text(main, encoding='utf-8')
print('Normalized Vessel voice join control to one rendered source control')
