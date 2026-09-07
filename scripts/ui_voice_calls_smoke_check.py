from pathlib import Path

main = Path('src/main.js').read_text(encoding='utf-8')
style = Path('src/style.css').read_text(encoding='utf-8')

checks = {
    'runtime marker': 'VESSEL_UI_VOICE_CALLS_V1' in main,
    'style marker': 'VESSEL_UI_VOICE_CALLS_V1' in style,
    'call stage helper': 'function callStageMarkup(' in main,
    'voice stage helper': 'function voiceStageMarkup(' in main,
    'call duration timer': 'data-call-duration' in main and 'syncCallUiTicker' in main,
    'connection state labels': 'data-call-state-label' in main and 'callVisualState' in main and 'voiceVisualState' in main,
    'live visual state polling': "callStage.dataset.state!==callVisualState()" in main and "voiceStage.dataset.state!==voiceVisualState()" in main,
    'reconnect indicator': 'rtc-reconnect-banner' in main and "'reconnecting'" in main,
    'audio speaking meter': 'function watchSpeakingStream(' in main and 'createAnalyser()' in main and 'data-speaking-key' in main,
    'speaking meter cleanup': 'stopSpeakingMeters' in main,
    'floating call controls': 'rtc-control-dock' in main and 'toggle-call-mic' in main and 'end-call' in main,
    'single voice join invariant': main.count('id="join-voice"') == 1,
    'video call stage': 'video-stage-grid' in main and 'remote-video-tile' in main and 'local-preview' in main,
    'voice participant cards': 'voice-participant-grid' in main and 'voiceParticipants' in main,
    'incoming call redesign': 'incoming-call-card' in main and 'incoming-call-orbit' in main and 'incoming-call-wave' in main,
    'verified ICE recovery preserved': "if(state==='connected'){clearCallDisconnectTimer();callIceRestartAttempts=0;callIceRestartInFlight=false;return;}" in main and "if(['failed','disconnected'].includes(state))scheduleCallDisconnectCleanup(connection,user,peerId,video);" in main,
    'call stage css': '.rtc-stage{' in style and '.audio-call-focus' in style and '.video-mode' in style,
    'video stage css': '.video-stage-grid' in style and '.remote-video-tile' in style and '.local-preview' in style,
    'voice cards css': '.voice-participant-card' in style and '.participant-avatar' in style,
    'speaking glow css': '.is-speaking' in style and 'rtcSpeakingPulse' in style,
    'floating dock css': '.rtc-control-dock' in style and '.rtc-dock-button' in style,
    'reconnect banner css': '.rtc-reconnect-banner' in style and 'rtcReconnectSpin' in style,
    'incoming call css': '.incoming-call-card' in style and 'rtcIncomingPulse' in style,
    'responsive call css': '@media(max-width:760px)' in style and '@media(max-width:520px)' in style,
    'reduced motion': '@media (prefers-reduced-motion: reduce)' in style and 'rtcSpeakingPulse' in style,
}

failed = [name for name, ok in checks.items() if not ok]
if failed:
    raise SystemExit('Voice/calls visual smoke failed: ' + ', '.join(failed))

print(f'Voice/calls visual smoke passed ({len(checks)} checks)')
