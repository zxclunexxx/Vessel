from pathlib import Path

path = Path('src/main.js')
text = path.read_text(encoding='utf-8')

legacy_tail = "if(error)throw error;localStorage.setItem('vesselToken',data.session.access_token);localStorage.setItem('vesselUser',JSON.stringify({id:data.user.id,name:data.user.user_metadata.username||data.user.email.split('@')[0],email:data.user.email}));location.reload();}catch{alert('Не удалось войти. Проверь почту и пароль.');}}; });"

if legacy_tail in text:
    text = text.replace(legacy_tail, '', 1)
    path.write_text(text, encoding='utf-8')
    print('Removed legacy auth handler tail')
else:
    print('Legacy auth handler tail already absent; nothing to clean')
