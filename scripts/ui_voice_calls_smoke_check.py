from pathlib import Path

main = Path('src/main.js').read_text(encoding='utf-8')
style = Path('src/style.css').read_text(encoding='utf-8')

checks = {
    'runtime marker': 'VESSEL_UI_VOICE_CALLS_V1' in main,
    'style marker': 'VESSEL_UI_VOICE_CALLS_V1' in style,
    'call stage helper': 'function callStageMarkup(' in main,
    'voice stage helper': 'function voiceStageMarkup(' in main,
    'call duration timer': 'data-call-duration' in main and 'syncCallUiTicker' in main,
    'call connection indicator': 'data-call-state-label' in main and 'callVisualState' in main,
    'reconnect state': "'reconnecting'" in main and 'rtc-reconnect-banner' in main,
    'audio speaking meter': 'watchSpeakingStream' in main and 'data-speaking-key' in main,
    'meter cleanup': 'stopSpeakingMeters' in main,
    'call controls': 'rtc-control-dock' in main and 'toggle-call-mic' in main and 'end-call' in main,
    'video call stage': 'video-stage-grid' in main and 'remote-video' in main and 'local-video' in main,
    'voice participants': 'voice-participant-grid' in main and 'voiceParticipants' in main,
    'incoming call redesign': 'incoming-call-card' in main and 'incoming-call-orbit' in main,
    'call stage css': '.rtc-stage' in style and '.call-stage' in style,
    'video stage css': '.video-stage-grid' in style and '.remote-video-tile' in style,
    'voice cards css': '.voice-participant-card' in style and '.participant-avatar' in style,
    'speaking glow css': '.is-speaking' in style and 'rtcSpeakingPulse' in style,
    'floating dock css': '.rtc-control-dock' in style,
    'reconnect banner css': '.rtc-reconnect-banner' in style,
    'incoming call css': '.incoming-call-card' in style,
    'responsive call css': '@media(max-width:760px)' in style and '.rtc-stage' in style,
    'reduced motion': '@media (prefers-reduced-motion: reduce)' in style and 'rtcSpeakingPulse' in style,
}

failed = [name for name, ok in checks.items() if not ok]
if failed:
    raise SystemExit('Voice/calls visual smoke failed: ' + ', '.join(failed))

print(f'Voice/calls visual smoke passed ({len(checks)} checks)')
