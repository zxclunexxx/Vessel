from pathlib import Path

main = Path('src/main.js').read_text(encoding='utf-8')

checks = {
    'call stage remains isolated from chat composer': "const rtcStage=callInProgress?callStageMarkup(user)" in main,
    'voice stage uses existing active channel context': "activeChannelKind==='voice'?voiceStageMarkup(user)" in main,
    'call action ids remain wired': "querySelector('#end-call')" in main and "querySelector('#toggle-call-mic')" in main,
    'voice action ids remain wired': "querySelector('#join-voice')" in main and "querySelector('#mute-voice')" in main and "querySelector('#deafen-voice')" in main,
    'video elements remain stream targets': 'id="remote-video"' in main and 'id="local-video"' in main,
    'media reattachment remains active': "remote.srcObject=remoteCallStream" in main and "video.srcObject=stream" in main,
    'rtc polling does not rewrite recovery handler': "callStage.dataset.state!==callVisualState()" in main and "scheduleCallDisconnectCleanup(connection,user,peerId,video);" in main,
}

failed = [name for name, ok in checks.items() if not ok]
if failed:
    raise SystemExit('Voice/calls stage integrity failed: ' + ', '.join(failed))

print(f'Voice/calls stage integrity passed ({len(checks)} checks)')
