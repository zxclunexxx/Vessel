from pathlib import Path

MAIN_PATH = Path('src/main.js')
MARKER = '/* VESSEL_AUTH_EMAIL_RESILIENCE_V1 */'

source = MAIN_PATH.read_text(encoding='utf-8')

helper_anchor = "function vesselListDialog(title,items=[],emptyText='Ничего нет',onSelect=null) {"
try_anchor = """      try {
        if (mode === 'login') {
"""
old_tail = """      } catch (error) {
        console.error('Authentication failed', error);
        vesselNotice(error?.message || 'Не удалось выполнить авторизацию.','error');
      } finally {
        submit.disabled = false;
      }
    });
    authSwitch.addEventListener('click', () => setAuthMode((authForm.dataset.mode || 'signup') === 'login' ? 'signup' : 'login'));
"""

helper = r'''/* VESSEL_AUTH_EMAIL_RESILIENCE_V1 */
let signupEmailCooldownUntil = 0;
let authSignupCooldownTimer = null;

function authErrorFeedback(error, mode='login') {
  const code=String(error?.code||'').toLowerCase();
  const message=String(error?.message||'').toLowerCase();
  const status=Number(error?.status||0);
  if(code==='over_email_send_rate_limit'||message.includes('email rate limit')){
    return {
      message:'Почтовый сервис временно исчерпал лимит писем подтверждения. Подожди немного и попробуй снова.',
      cooldownMs:60000
    };
  }
  if(code==='email_not_confirmed'||message.includes('email not confirmed')){
    return {message:'Почта ещё не подтверждена. Открой письмо от Vessel и перейди по ссылке подтверждения.',cooldownMs:0};
  }
  if(code==='invalid_credentials'||message.includes('invalid login credentials')){
    return {message:'Неверная электронная почта или пароль.',cooldownMs:0};
  }
  if(code==='user_already_exists'||message.includes('user already registered')){
    return {message:'Аккаунт с этой почтой уже существует. Попробуй войти.',cooldownMs:0};
  }
  if(code==='weak_password'||message.includes('password should be at least')){
    return {message:'Пароль слишком слабый. Используй не менее 6 символов.',cooldownMs:0};
  }
  if(code==='email_address_invalid'||message.includes('invalid email')){
    return {message:'Проверь электронную почту — адрес выглядит некорректно.',cooldownMs:0};
  }
  if(code==='signup_disabled'){
    return {message:'Регистрация новых аккаунтов сейчас временно отключена.',cooldownMs:0};
  }
  if(status===429){
    return {message:'Слишком много попыток. Подожди немного и повтори действие.',cooldownMs:30000};
  }
  return {message:mode==='signup'?'Не удалось создать аккаунт. Попробуй ещё раз чуть позже.':'Не удалось войти в аккаунт. Проверь данные и повтори попытку.',cooldownMs:0};
}

function remainingSignupEmailCooldownSeconds() {
  return Math.max(0,Math.ceil((signupEmailCooldownUntil-Date.now())/1000));
}

function refreshAuthSubmitAvailability(form) {
  if(authSignupCooldownTimer){clearTimeout(authSignupCooldownTimer);authSignupCooldownTimer=null;}
  if(!form?.isConnected)return;
  const submit=form.querySelector('button[type="submit"]');
  if(!submit)return;
  const mode=form.dataset.mode||'signup';
  if(mode!=='signup'){
    submit.disabled=false;
    return;
  }
  const remaining=remainingSignupEmailCooldownSeconds();
  if(remaining<=0){
    submit.disabled=false;
    submit.innerHTML='Создать аккаунт <span>→</span>';
    return;
  }
  submit.disabled=true;
  submit.textContent=`Повторить через ${remaining} с`;
  authSignupCooldownTimer=setTimeout(()=>refreshAuthSubmitAvailability(form),1000);
}

'''

new_try = """      try {
        if (mode === 'signup' && Date.now() < signupEmailCooldownUntil) {
          refreshAuthSubmitAvailability(form);
          vesselNotice('Почтовый лимит ещё действует. Подожди немного перед повторной регистрацией.','error');
          return;
        }
        if (mode === 'login') {
"""

new_tail = """      } catch (error) {
        console.error('Authentication failed', error);
        const feedback=authErrorFeedback(error,mode);
        if(feedback.cooldownMs){
          signupEmailCooldownUntil=Math.max(signupEmailCooldownUntil,Date.now()+feedback.cooldownMs);
        }
        vesselNotice(feedback.message,'error');
      } finally {
        if(mode==='signup')refreshAuthSubmitAvailability(form);
        else submit.disabled=false;
      }
    });
    authSwitch.addEventListener('click', () => {
      setAuthMode((authForm.dataset.mode || 'signup') === 'login' ? 'signup' : 'login');
      refreshAuthSubmitAvailability(authForm);
    });
    refreshAuthSubmitAvailability(authForm);
"""

if MARKER in source:
    required = [
        "code==='over_email_send_rate_limit'",
        'signupEmailCooldownUntil',
        'refreshAuthSubmitAvailability(authForm);',
        "vesselNotice(feedback.message,'error');",
    ]
    missing=[item for item in required if item not in source]
    if missing:
        raise SystemExit('Auth email resilience marker exists but generated behavior is incomplete: '+', '.join(missing))
    print('Vessel auth email resilience already applied')
    raise SystemExit(0)

for name, anchor in [('helper', helper_anchor), ('try', try_anchor), ('tail', old_tail)]:
    count=source.count(anchor)
    if count!=1:
        raise SystemExit(f'Auth email resilience source drift at {name} anchor: expected 1, found {count}')

source = source.replace(helper_anchor, helper + helper_anchor, 1)
source = source.replace(try_anchor, new_try, 1)
source = source.replace(old_tail, new_tail, 1)
MAIN_PATH.write_text(source, encoding='utf-8')
print('Applied Vessel auth email resilience patch')
