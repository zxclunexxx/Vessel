from pathlib import Path

main = Path('src/main.js').read_text(encoding='utf-8')
style = Path('src/style.css').read_text(encoding='utf-8')

checks = {
    'runtime marker': 'VESSEL_UI_MOTION_POLISH_V1' in main,
    'style marker': 'VESSEL_UI_MOTION_POLISH_V1' in style,
    'single motion marker': main.count('VESSEL_UI_MOTION_POLISH_V1') == 1 and style.count('VESSEL_UI_MOTION_POLISH_V1') == 1,
    'toast stack runtime': 'function ensureVesselToastStack()' in main and "stack.id='vessel-toast-stack'" in main,
    'toast accessibility': "stack.setAttribute('aria-live','polite')" in main and "toast.setAttribute('role',tone==='error'?'alert':'status')" in main and "close.setAttribute('aria-label','Закрыть уведомление')" in main,
    'toast lifecycle': "toast.classList.add('show')" in main and "toast.classList.add('leaving')" in main and 'setTimeout(dismiss,3600)' in main,
    'context motion helper': 'function triggerVesselViewMotion(previousContext,currentContext)' in main,
    'context motion guard': 'if(previousContext===currentContext)return;' in main and "window.matchMedia?.('(prefers-reduced-motion: reduce)').matches" in main,
    'context motion classes': all(token in main for token in ['view-motion-head','view-motion-content','view-motion-composer','view-motion-stage']),
    'render motion hook': 'triggerVesselViewMotion(previousMessageContext,currentMessageContext);' in main,
    'render drawer cleanup': "document.body.classList.remove('mobile-drawer-open');" in main,
    'mobile drawer state': "document.body.classList.toggle('mobile-drawer-open',next);" in main and "scrim.className='mobile-drawer-scrim'" in main,
    'mobile drawer accessibility': "scrim.setAttribute('aria-label','Закрыть меню каналов')" in main and "scrim.addEventListener('click',()=>setMobileDrawerOpen(false))" in main,
    'view motion css': all(token in style for token in ['.view-motion-head','.view-motion-content','.view-motion-composer','.view-motion-stage']),
    'view motion keyframes': all(token in style for token in ['vesselViewHeadIn','vesselViewContentIn','vesselViewComposerIn','vesselViewStageIn']),
    'modal motion css': 'vesselModalBackdropIn' in style and 'vesselModalCardIn' in style and 'vesselSheetIn' in style,
    'incoming call animation isolation': '.modal:not(.hidden):not(.incoming-call-modal)' in style,
    'toast stack css': '.vessel-toast-stack' in style and '.vessel-toast-icon' in style and '.vessel-toast-close' in style,
    'toast life animation': 'vesselToastLife' in style and '.vessel-toast.success::after' in style and '.vessel-toast.error::after' in style,
    'pointer-aware hover': '@media (hover:hover) and (pointer:fine)' in style,
    'press feedback': 'button:active:not(:disabled)' in style and 'scale(.965)!important' in style,
    'mobile safe area': '100dvh' in style and 'env(safe-area-inset-bottom)' in style,
    'mobile drawer scrim css': '.mobile-drawer-scrim' in style and 'body.mobile-drawer-open .chat' in style,
    'mobile touch targets': '.mobile-drawer-close { min-width: 40px; min-height: 40px; }' in style,
    'mobile blur budget': 'backdrop-filter: blur(15px) saturate(118%)' in style and 'backdrop-filter: blur(13px) saturate(115%)' in style,
    'paint containment': 'contain: paint' in style,
    'reduced motion coverage': '@media (prefers-reduced-motion: reduce)' in style and '.primary::after { display:none; }' in style,
    'verified call recovery preserved': "if(state==='connected'){clearCallDisconnectTimer();callIceRestartAttempts=0;callIceRestartInFlight=false;return;}" in main and "if(['failed','disconnected'].includes(state))scheduleCallDisconnectCleanup(connection,user,peerId,video);" in main,
    'previous visual batches preserved': all(token in main + style for token in ['VESSEL_UI_MESSAGING_SOCIAL_V1','VESSEL_UI_VOICE_CALLS_V1']),
}

failed = [name for name, ok in checks.items() if not ok]
if failed:
    raise SystemExit('Motion/polish visual smoke failed: ' + ', '.join(failed))

print(f'Motion/polish visual smoke passed ({len(checks)} checks)')
