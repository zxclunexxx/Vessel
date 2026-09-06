from pathlib import Path

main = Path('src/main.js').read_text(encoding='utf-8')

for banned in [
    'voiceStream=await navigator.mediaDevices.getUserMedia',
    'callStream=await navigator.mediaDevices.getUserMedia',
]:
    if banned in main:
        raise SystemExit(f'Media stream is published before async context validation: {banned}')

voice_start = main.find('async function toggleVoiceRoom(user,reconnecting=false)')
signal_start = main.find('async function handleCallSignal(user,peerId,signal,video)')
start_call_start = main.find('async function startCall(video,user)')
accept_call_start = main.find('async function acceptIncomingCall(user)')
if min(voice_start, signal_start, start_call_start, accept_call_start) < 0:
    raise SystemExit('Missing media entry point')

voice = main[voice_start:voice_start + 6200]
signal = main[signal_start:start_call_start]
start_call = main[start_call_start:accept_call_start]
accept_call = main[accept_call_start:accept_call_start + 2600]

for marker in [
    'const targetServerId=getActiveServer()?.dbId||null;',
    'const stream=await navigator.mediaDevices.getUserMedia({audio:true,video:false});',
    "activeChannelId!==targetChannelId||activeChannelKind!=='voice'",
    'getActiveServer()?.dbId!==targetServerId',
    'stream.getTracks().forEach(track=>track.stop());',
    'voiceStream=stream;',
]:
    if marker not in voice:
        raise SystemExit(f'Voice media context guard missing: {marker}')
if voice.find('stream.getTracks().forEach(track=>track.stop());') > voice.find('voiceStream=stream;'):
    raise SystemExit('Voice stream must be validated before publication')

for marker in [
    'const signalStream=await navigator.mediaDevices.getUserMedia({audio:true,video:!!video});',
    'const signalAccess=await verifyDirectMessageAccess(user,peerId,{notify:false});',
    'callPeer!==peerId||signalAccess!==true',
    'signalStream.getTracks().forEach(track=>track.stop());',
    'callStream=signalStream;',
]:
    if marker not in signal:
        raise SystemExit(f'Call offer media context guard missing: {marker}')
if signal.find('signalStream.getTracks().forEach(track=>track.stop());') > signal.find('callStream=signalStream;'):
    raise SystemExit('Offer media stream must be validated before publication')

for marker in [
    'const mediaStream=await navigator.mediaDevices.getUserMedia({audio:true,video:!!video});',
    'const accessAfterMedia=await verifyDirectMessageAccess(user,peerId,{notify:false});',
    'activeDmId!==peerId||callPeer!==peerId||incomingCall||accessAfterMedia!==true',
    'mediaStream.getTracks().forEach(track=>track.stop());',
    'callStream=mediaStream;',
]:
    if marker not in start_call:
        raise SystemExit(f'Outgoing call media context guard missing: {marker}')
if start_call.find('mediaStream.getTracks().forEach(track=>track.stop());') > start_call.find('callStream=mediaStream;'):
    raise SystemExit('Outgoing call media stream must be validated before publication')

for marker in [
    'const acceptedStream=await navigator.mediaDevices.getUserMedia({audio:true,video:callVideo});',
    'const acceptedAccess=await verifyDirectMessageAccess(user,invite.from,{notify:false});',
    'callPeer!==invite.from||!callAccepted||acceptedAccess!==true',
    'acceptedStream.getTracks().forEach(track=>track.stop());',
    'callStream=acceptedStream;',
]:
    if marker not in accept_call:
        raise SystemExit(f'Incoming call media context guard missing: {marker}')
if accept_call.find('acceptedStream.getTracks().forEach(track=>track.stop());') > accept_call.find('callStream=acceptedStream;'):
    raise SystemExit('Incoming call media stream must be validated before publication')

print('Vessel media context smoke check passed')
