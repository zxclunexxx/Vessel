from pathlib import Path

main = Path('src/main.js').read_text(encoding='utf-8')

required = [
    "const logoutButton=document.querySelector('#logout');",
    "const {error}=await supabase.auth.signOut();",
    "if(error){vesselNotice('Не удалось выйти из аккаунта. Попробуй ещё раз.','error');return;}",
    'const staleChannels=resetAuthenticatedRuntime();',
    "cleanupAuthenticatedChannels(staleChannels).catch(cleanupError=>console.warn('Logout cleanup failed',cleanupError));",
]
for marker in required:
    if marker not in main:
        raise SystemExit(f'Reliable logout guard missing: {marker}')

for banned in [
    "supabase.auth.signOut().catch",
    "localStorage.removeItem('vesselUser'); localStorage.removeItem('vesselToken'); location.reload();",
]:
    if banned in main:
        raise SystemExit(f'Legacy unreliable logout behavior remains: {banned}')

print('Vessel logout/session cleanup smoke check passed')
