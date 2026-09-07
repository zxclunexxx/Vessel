from pathlib import Path

text = Path('src/main.js').read_text(encoding='utf-8')

required = [
    "document.querySelector('#join-voice')?.addEventListener('click'",
    'await toggleVoiceRoom(user)',
    "document.querySelector('#mute-voice')?.addEventListener('click',toggleVoiceMicrophone)",
    "document.querySelector('#deafen-voice')?.addEventListener('click',toggleVoiceDeafen)",
    'function toggleVoiceDeafen()',
    'audio.muted=voiceDeafened;',
    'const uniqueParticipants=new Map();',
    'voiceParticipants=[...uniqueParticipants.values()];',
]

missing = [marker for marker in required if marker not in text]
if missing:
    raise SystemExit('Voice controls regression: missing ' + ', '.join(missing))

if text.count("id=\"join-voice\"") != 1:
    raise SystemExit('Voice join control should be rendered exactly once')
if text.count("id=\"mute-voice\"") != 1:
    raise SystemExit('Voice mute control should be rendered exactly once')
if text.count("id=\"deafen-voice\"") != 1:
    raise SystemExit('Voice deafen control should be rendered exactly once')

print('Voice controls wiring smoke check passed')
