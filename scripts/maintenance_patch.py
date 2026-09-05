from pathlib import Path
import re

path = Path('src/main.js')
text = path.read_text(encoding='utf-8')


def sub(pattern, replacement, *, count=1, flags=re.S, label='patch'):
    global text
    updated, n = re.subn(pattern, replacement, text, count=count, flags=flags)
    if n != count:
        raise SystemExit(f'{label}: expected {count} replacement(s), got {n}')
    text = updated

# 1) Authenticated runtime must never start from fake local servers/messages.
sub(
    r"let servers = JSON\.parse\(localStorage\.getItem\('vesselServers'\) \|\| 'null'\) \|\| \[.*?\n\];\nservers = servers\.map\(\(server, index\) => \(\{\.\.\.server, id: server\.id \|\| `local-\$\{index\}`\}\)\);\nif \(activeServerIndex >= servers\.length - 1\) activeServerIndex = 0;",
    "let servers = [{ id: 'add-server', icon: '+', name: 'Добавить сервер', add: true }];\nif (activeServerIndex < 0) activeServerIndex = 0;",
    label='remove fake servers',
)

sub(
    r"function serverChannels\(\) \{.*?\n\}",
    "function serverChannels() {\n  const server = servers[activeServerIndex];\n  return savedChannelMap[server?.id] || [];\n}",
    label='remove fake channels',
)

sub(
    r"const defaultMessages = \[.*?\n\];\nlet messages = JSON\.parse\(localStorage\.getItem\('vesselMessages'\) \|\| 'null'\) \|\| defaultMessages;\nconst API_URL = 'http://localhost:8080';\n\nfunction connectRealtime\(\) \{.*?\n\}",
    "let messages = [];",
    label='remove fake messages and localhost realtime',
)

# 2) Supabase session is the only source of truth for authenticated mode.
sub(
    r"const savedUser = JSON\.parse\(localStorage\.getItem\('vesselUser'\) \|\| 'null'\);",
    """let savedUser = null;

async function bootstrapAuth() {
  if (!supabase) {
    console.error('Supabase client is unavailable.');
    savedUser = null;
    return;
  }

  // One-time cleanup of the old prototype runtime. These keys previously allowed
  // an unauthenticated local user and fake servers/messages to masquerade as real data.
  if (localStorage.getItem('vesselRuntimeV2') !== '1') {
    ['vesselUser','vesselToken','vesselServers','vesselMessages','vesselChannelMap','vesselActiveServer'].forEach(key => localStorage.removeItem(key));
    localStorage.setItem('vesselRuntimeV2', '1');
    activeServerIndex = 0;
    Object.keys(savedChannelMap).forEach(key => delete savedChannelMap[key]);
  }

  const {data, error} = await supabase.auth.getSession();
  if (error) {
    console.error('Unable to restore Supabase session', error);
    savedUser = null;
    return;
  }

  const session = data?.session;
  if (!session?.user) {
    localStorage.removeItem('vesselUser');
    localStorage.removeItem('vesselToken');
    savedUser = null;
    return;
  }

  const authUser = session.user;
  const {data: profile, error: profileError} = await supabase.from('profiles').select('id,username,email,status,avatar_color').eq('id', authUser.id).maybeSingle();
  if (profileError) console.warn('Profile load failed', profileError);

  savedUser = {
    id: authUser.id,
    name: profile?.username || authUser.user_metadata?.username || authUser.email?.split('@')[0] || 'Пользователь',
    email: profile?.email || authUser.email || '',
    status: profile?.status || 'online',
    avatarColor: profile?.avatar_color || '#8b7cff'
  };
  // Cache only. render() never trusts this value until getSession() succeeded.
  localStorage.setItem('vesselUser', JSON.stringify(savedUser));
}
""",
    label='bootstrap auth',
)

text = text.replace("if (!savedUser && !localStorage.getItem('vesselUser')) {", "if (!savedUser) {", 1)
text = text.replace('minlength="4" placeholder="Минимум 4 символа"', 'minlength="6" placeholder="Минимум 6 символов"', 1)
text = text.replace('minlength="4" placeholder="Твой пароль"', 'minlength="6" placeholder="Твой пароль"', 1)
text = text.replace("        <div class=\"auth-divider\"><span>или</span></div><button class=\"ghost\" type=\"button\" id=\"demo-login\">Войти в демо-режим</button><button class=\"auth-switch\" type=\"button\" id=\"auth-switch\">У меня уже есть аккаунт</button><small>Продолжая, ты принимаешь правила Vessel</small>", "        <button class=\"auth-switch\" type=\"button\" id=\"auth-switch\">У меня уже есть аккаунт</button><small>Продолжая, ты принимаешь правила Vessel</small>", 1)

sub(
    r"    document\.querySelector\('\.auth-form'\)\.addEventListener\('submit', async e => \{.*?\}\);\n    document\.querySelector\('#demo-login'\)\.addEventListener\('click', \(\) => \{.*?\}\);\n    document\.querySelector\('#auth-switch'\)\.addEventListener\('click', \(\) => \{.*?\}\);",
    """    const authForm = document.querySelector('.auth-form');
    const authSwitch = document.querySelector('#auth-switch');
    const setAuthMode = mode => {
      authForm.dataset.mode = mode;
      if (mode === 'login') {
        authForm.innerHTML = '<label>Электронная почта<input name="email" type="email" required placeholder="you@example.com" /></label><label>Пароль<input name="password" type="password" required minlength="6" placeholder="Твой пароль" /></label><button class="primary" type="submit">Войти <span>→</span></button>';
        authSwitch.textContent = 'Создать новый аккаунт';
      } else {
        authForm.innerHTML = '<label>Имя пользователя<input name="name" required minlength="2" placeholder="Например, Артём" /></label><label>Электронная почта<input name="email" type="email" required placeholder="you@example.com" /></label><label>Пароль<input name="password" type="password" required minlength="6" placeholder="Минимум 6 символов" /></label><button class="primary" type="submit">Создать аккаунт <span>→</span></button>';
        authSwitch.textContent = 'У меня уже есть аккаунт';
      }
    };
    authForm.addEventListener('submit', async e => {
      e.preventDefault();
      if (!supabase) { alert('Сервис авторизации временно недоступен.'); return; }
      const form = e.currentTarget;
      const data = new FormData(form);
      const mode = form.dataset.mode || 'signup';
      const submit = form.querySelector('button[type="submit"]');
      submit.disabled = true;
      try {
        if (mode === 'login') {
          const {error} = await supabase.auth.signInWithPassword({email:data.get('email'), password:data.get('password')});
          if (error) throw error;
          await bootstrapAuth();
          render();
          return;
        }
        const payload = {name:String(data.get('name') || '').trim(), email:String(data.get('email') || '').trim(), password:String(data.get('password') || '')};
        const {data: result, error} = await supabase.auth.signUp({email:payload.email,password:payload.password,options:{data:{username:payload.name}}});
        if (error) throw error;
        if (!result.session) {
          alert('Аккаунт создан. Если подтверждение почты включено, открой письмо от Vessel, а затем войди.');
          setAuthMode('login');
          return;
        }
        await bootstrapAuth();
        render();
      } catch (error) {
        console.error('Authentication failed', error);
        alert(error?.message || 'Не удалось выполнить авторизацию.');
      } finally {
        submit.disabled = false;
      }
    });
    authSwitch.addEventListener('click', () => setAuthMode((authForm.dataset.mode || 'signup') === 'login' ? 'signup' : 'login'));""",
    flags=re.S,
    label='replace auth form handlers',
)

text = text.replace("  const user = JSON.parse(localStorage.getItem('vesselUser'));", "  const user = savedUser;", 1)
text = text.replace("  connectRealtime(); connectSupabaseRealtime(user);", "  connectSupabaseRealtime(user);", 1)

# 3) Channel messages must use Supabase only; never localhost/localStorage as a second database.
sub(
    r"^  document\.querySelector\('\.composer'\)\.addEventListener\('submit', async e => \{.*$",
    """  document.querySelector('.composer').addEventListener('submit', async e => { e.preventDefault(); const input=e.currentTarget.querySelector('input'); const text=input.value.trim(); if(!text)return; if(!supabase||!user.id){alert('Нужна активная сессия Vessel.');return;} if(activeDmId){ const {error}=await supabase.from('direct_messages').insert({sender_id:user.id,receiver_id:activeDmId,body:text}); if(error){alert(`Не удалось отправить личное сообщение: ${error.message}`);return;} dmMessages.push({name:user.name,time:'только что',color:user.avatarColor||'#39d9a6',text}); } else { if(!activeChannelId){alert('Сначала выбери текстовый канал.');return;} const {error}=await supabase.from('messages').insert({channel_id:activeChannelId,author_id:user.id,body:text}); if(error){alert(`Не удалось отправить сообщение: ${error.message}`);return;} messages.push({name:user.name,time:'только что',color:user.avatarColor||'#39d9a6',text}); } input.value=''; render(); const list=document.querySelector('.messages'); if(list)list.scrollTop=list.scrollHeight; });""",
    flags=re.M,
    label='supabase-only composer',
)

# 4) Friend list should update for both sides after friendship rows appear.
needle = "    supabase.channel(`vessel-friends-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'friend_requests',filter:`receiver_id=eq.${user.id}`},()=>{window.__vesselSocialLoaded=false;syncSocial(user).then(()=>{if(friendsOpen)render();});}).subscribe(),"
if needle not in text:
    raise SystemExit('friend realtime anchor missing')
text = text.replace(needle, needle + "\n    supabase.channel(`vessel-friendships-${user.id}`).on('postgres_changes',{event:'*',schema:'public',table:'friendships',filter:`user_id=eq.${user.id}`},()=>{window.__vesselSocialLoaded=false;syncSocial(user);}).subscribe(),", 1)

# 5) Hang-up must clean local UI/media immediately, not wait up to 10 seconds for signaling.
sub(
    r"async function endCall\(notify=true\) \{.*?\n\}\n\nfunction toggleCallMicrophone",
    """async function endCall(notify=true) {
  const user=savedUser || JSON.parse(localStorage.getItem('vesselUser')||'null');
  const peer=callPeer;
  const room=callChannel;
  const connection=callConnection;
  callConnection=null;
  callChannel=null;
  connection?.close();
  callStream?.getTracks().forEach(track=>track.stop());
  remoteCallStream?.getTracks?.().forEach(track=>track.stop?.());
  callStream=null;
  remoteCallStream=null;
  callPeer=null;
  callPeerName='';
  pendingIceCandidates=[];
  localIceCandidates=[];
  callOffer=null;
  callVideo=false;
  callAccepted=false;
  callMicEnabled=true;
  callCameraEnabled=true;
  render();
  if(room&&supabase) supabase.removeChannel(room).catch(()=>{});
  if(notify&&peer&&user?.id) sendCallInvite(user,peer,{type:'bye'}).catch(()=>{});
}

function toggleCallMicrophone""",
    label='instant hangup cleanup',
)

text = text.replace("await sendCallInvite(user,activeDmId,{type:'invite',name:callPeerName,video:callVideo,offer:callOffer});", "await sendCallInvite(user,activeDmId,{type:'invite',name:user.name,video:callVideo,offer:callOffer});", 1)

# 6) Boot from Supabase session instead of trusting localStorage.
if "\nrender();\nsetInterval(" not in text:
    raise SystemExit('bottom render anchor missing')
text = text.replace("\nrender();\nsetInterval(", "\nbootstrapAuth().then(render).catch(error=>{console.error('Vessel bootstrap failed',error);savedUser=null;render();});\nsetInterval(", 1)

path.write_text(text, encoding='utf-8')
print('Vessel authenticated runtime foundation patched successfully')
