from pathlib import Path

# Auth/session baseline verifier. The cross-tab lifecycle implementation is already in main.
# Keep this script tolerant of later voice/call cleanup additions inside the same reset helper.
main = Path('src/main.js').read_text(encoding='utf-8')

markers = [
    'function resetAuthenticatedRuntime()',
    'function cleanupAuthenticatedChannels(channels=[])',
    'function scheduleAuthStateRefresh(session)',
    'function handleAuthStateChange(event,session)',
    "event==='INITIAL_SESSION'||event==='TOKEN_REFRESHED'",
    "event==='SIGNED_OUT'||!nextUserId",
    "event==='SIGNED_IN'",
    'auth.onAuthStateChange((event,session)=>handleAuthStateChange(event,session))',
    "window.addEventListener('beforeunload',()=>authStateSubscription?.unsubscribe())",
]

missing = [marker for marker in markers if marker not in main]
if missing:
    raise SystemExit('Vessel session marker missing: ' + ', '.join(missing))

print('Vessel auth/session hardening already applied; nothing to change')
