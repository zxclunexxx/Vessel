from pathlib import Path

path = Path('src/main.js')
main = path.read_text(encoding='utf-8')

marker = "const logoutButton=document.querySelector('#logout');"
old = "document.querySelector('#logout').addEventListener('click', async () => { if(supabase) await supabase.auth.signOut().catch(()=>{}); localStorage.removeItem('vesselUser'); localStorage.removeItem('vesselToken'); location.reload(); });"
new = """const logoutButton=document.querySelector('#logout');
  logoutButton.addEventListener('click', async () => {
    if(!supabase){vesselNotice('Сервис авторизации временно недоступен.','error');return;}
    logoutButton.disabled=true;
    try{
      const {error}=await supabase.auth.signOut();
      if(error){vesselNotice('Не удалось выйти из аккаунта. Попробуй ещё раз.','error');return;}
      if(savedUser){
        const staleChannels=resetAuthenticatedRuntime();
        render();
        cleanupAuthenticatedChannels(staleChannels).catch(cleanupError=>console.warn('Logout cleanup failed',cleanupError));
      }
    }catch(error){
      console.warn('Logout failed',error);
      vesselNotice('Не удалось выйти из аккаунта. Попробуй ещё раз.','error');
    }finally{
      if(logoutButton.isConnected)logoutButton.disabled=false;
    }
  });"""

if marker in main:
    print('Reliable logout handler already present')
elif old in main:
    path.write_text(main.replace(old, new, 1), encoding='utf-8')
    print('Replaced reload-based logout with verified Supabase sign-out flow')
else:
    raise SystemExit('Legacy logout handler not found; inspect src/main.js before patching')
