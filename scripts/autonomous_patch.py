from pathlib import Path
import re

main_path = Path('src/main.js')
css_path = Path('src/style.css')
text = main_path.read_text(encoding='utf-8')
css = css_path.read_text(encoding='utf-8')

# Native Vessel dialogs replace the rough prompt/confirm flows used by the prototype.
anchor = """function attachmentMarkup(attachments=[]) {"""
helpers = r'''function vesselDialog({title,message='',input=false,value='',placeholder='',choices=[]}) {
  return new Promise(resolve=>{
    const overlay=document.createElement('div');
    overlay.className='modal vessel-dialog';
    const choiceMarkup=choices.map(choice=>`<button type="button" class="dialog-choice ${choice.danger?'dialog-danger':''}" data-dialog-value="${escapeHtml(choice.value)}">${escapeHtml(choice.label)}</button>`).join('');
    overlay.innerHTML=`<div class="modal-card dialog-card"><button class="modal-close" data-dialog-cancel>×</button><h2>${escapeHtml(title)}</h2>${message?`<p>${escapeHtml(message)}</p>`:''}${input?`<input class="dialog-input" value="${escapeHtml(value)}" placeholder="${escapeHtml(placeholder)}" />`:''}<div class="dialog-actions">${choiceMarkup}${input?'<button type="button" class="primary" data-dialog-submit>Готово</button>':''}</div></div>`;
    document.body.appendChild(overlay);
    const finish=result=>{overlay.remove();resolve(result);};
    overlay.querySelector('[data-dialog-cancel]').addEventListener('click',()=>finish(null));
    overlay.addEventListener('click',event=>{if(event.target===overlay)finish(null);});
    overlay.querySelectorAll('[data-dialog-value]').forEach(button=>button.addEventListener('click',()=>finish(button.dataset.dialogValue)));
    if(input){
      const field=overlay.querySelector('.dialog-input');
      const submit=()=>finish(field.value);
      overlay.querySelector('[data-dialog-submit]').addEventListener('click',submit);
      field.addEventListener('keydown',event=>{if(event.key==='Enter')submit();if(event.key==='Escape')finish(null);});
      setTimeout(()=>{field.focus();field.select();},0);
    }
  });
}
function vesselPrompt(title,value='',placeholder='') { return vesselDialog({title,input:true,value,placeholder}); }
function vesselChoice(title,choices,message='') { return vesselDialog({title,message,choices}); }
async function vesselConfirm(title,message='') { return (await vesselChoice(title,[{label:'Отмена',value:'no'},{label:'Подтвердить',value:'yes',danger:true}],message))==='yes'; }
function vesselNotice(message,type='info') {
  const toast=document.createElement('div');
  toast.className=`vessel-toast ${type}`;
  toast.textContent=message;
  document.body.appendChild(toast);
  requestAnimationFrame(()=>toast.classList.add('show'));
  setTimeout(()=>{toast.classList.remove('show');setTimeout(()=>toast.remove(),180);},3200);
}
function attachmentMarkup(attachments=[]) {'''
if anchor not in text:
    raise SystemExit('attachmentMarkup anchor not found')
text = text.replace(anchor, helpers, 1)

# Friend search.
text = text.replace("const query=prompt('Введи точное имя пользователя:');", "const query=await vesselPrompt('Добавить друга','','Точное имя пользователя');", 1)

# Server owner menu and confirmations.
text = text.replace("const action=prompt('Управление сервером:\\n1 — создать приглашение\\n2 — переименовать сервер\\n3 — удалить сервер');", "const action=await vesselChoice('Управление сервером',[{label:'Создать приглашение',value:'1'},{label:'Переименовать сервер',value:'2'},{label:'Удалить сервер',value:'3',danger:true}]);", 1)
text = text.replace("const name=prompt('Новое название сервера:',server.name);", "const name=await vesselPrompt('Переименовать сервер',server.name,'Название сервера');", 1)
text = text.replace("if(!confirm(`Удалить сервер «${server.name}» вместе с каналами и сообщениями?`))return;", "if(!await vesselConfirm(`Удалить сервер «${server.name}»?`,'Каналы и сообщения этого сервера тоже будут удалены.'))return;", 1)
text = text.replace("if(confirm(`Выйти из сервера «${server.name}»?`)){", "if(await vesselConfirm(`Выйти из сервера «${server.name}»?`)){", 1)

# Channel creation and settings.
text = text.replace("const name=prompt(kind==='voice'?'Название голосовой комнаты:':'Название нового канала:');", "const name=await vesselPrompt(kind==='voice'?'Новая голосовая комната':'Новый текстовый канал','','Название');", 1)
text = text.replace("const action=prompt(`Канал «${channel.name}»:\\n1 — переименовать\\n2 — удалить`);", "const action=await vesselChoice(`Канал «${channel.name}»`,[{label:'Переименовать',value:'1'},{label:'Удалить',value:'2',danger:true}]);", 1)
text = text.replace("const name=prompt('Новое название канала:',channel.name);", "const name=await vesselPrompt('Переименовать канал',channel.name,'Название канала');", 1)
text = text.replace("if(!confirm(`Удалить канал «${channel.name}»?`))return;", "if(!await vesselConfirm(`Удалить канал «${channel.name}»?`))return;", 1)

# Friend removal and member moderation.
text = text.replace("if(!confirm(`Удалить ${friend?.username||'пользователя'} из друзей?`))return;", "if(!await vesselConfirm(`Удалить ${friend?.username||'пользователя'} из друзей?`))return;", 1)
text = text.replace("const action=prompt(`Участник ${member.username}:\\n1 — сделать участником\\n2 — сделать модератором\\n3 — исключить из сервера`);", "const action=await vesselChoice(`Участник ${member.username}`,[{label:'Сделать участником',value:'1'},{label:'Сделать модератором',value:'2'},{label:'Исключить из сервера',value:'3',danger:true}]);", 1)
text = text.replace("if(!confirm(`Исключить ${member.username} из сервера?`))return;", "if(!await vesselConfirm(`Исключить ${member.username} из сервера?`))return;", 1)

# Replace the particularly rough add-server confirm/prompt branch with a single Vessel choice dialog.
pattern = re.compile(r"if\(supabase&&user\.id&&confirm\('У тебя есть код приглашения\? Нажми «ОК», чтобы вступить в сервер\.'\)\)\{const code=prompt\('Введи код приглашения:'\);if\(code\?\.trim\(\)\)\{await joinByInvite\(code,user\);return;\}\}\n      const name=prompt\('Название нового сервера:'\);")
replacement = """const addMode=await vesselChoice('Добавить сервер',[{label:'Вступить по приглашению',value:'join'},{label:'Создать свой сервер',value:'create'}]);
      if(addMode==='join'){
        const code=await vesselPrompt('Вступить в сервер','','Код VSL-…');
        if(code?.trim())await joinByInvite(code,user);
        return;
      }
      if(addMode!=='create')return;
      const name=await vesselPrompt('Создать сервер','','Название сервера');"""
text, count = pattern.subn(replacement, text, count=1)
if count != 1:
    raise SystemExit(f'add server flow replacement count={count}')

# Use lightweight in-app notices for the most common success states.
text = text.replace("alert(data.already_member?'Ты уже состоишь в этом сервере.':'Ты вступил в сервер.');", "vesselNotice(data.already_member?'Ты уже состоишь в этом сервере.':'Ты вступил в сервер.','success');", 1)
text = text.replace("alert(sendError?'Не удалось отправить заявку.':`Заявка пользователю ${target.username} отправлена.`);", "sendError?alert('Не удалось отправить заявку.'):vesselNotice(`Заявка пользователю ${target.username} отправлена.`,'success');", 1)

css += r'''
.vessel-dialog .dialog-card{max-width:460px}.dialog-input{width:100%;margin:10px 0 4px;border:1px solid #3b4258;background:#222735;color:#fff;border-radius:10px;padding:13px 14px;font:inherit;outline:0}.dialog-input:focus{border-color:#8378ff;box-shadow:0 0 0 3px #8378ff22}.dialog-actions{display:grid;gap:9px;margin-top:18px}.dialog-choice{border:1px solid #383e52;background:#252a39;color:#e1e4ee;border-radius:10px;padding:12px 14px;text-align:left;font:600 13px Inter;cursor:pointer}.dialog-choice:hover{background:#303649;border-color:#555d78}.dialog-choice.dialog-danger{border-color:#633445;background:#321d28;color:#ff9eb4}.vessel-toast{position:fixed;right:22px;bottom:22px;z-index:50;max-width:min(420px,calc(100vw - 32px));background:#242a38;border:1px solid #3d455b;color:#eef0f7;border-radius:12px;padding:12px 15px;box-shadow:0 16px 48px #0008;opacity:0;transform:translateY(10px);transition:.18s}.vessel-toast.show{opacity:1;transform:none}.vessel-toast.success{border-color:#315f50;color:#8ff0ca}.vessel-toast.error{border-color:#71384a;color:#ff9db2}@media(max-width:600px){.vessel-toast{right:12px;bottom:12px;left:12px;max-width:none}}
'''

main_path.write_text(text, encoding='utf-8')
css_path.write_text(css, encoding='utf-8')
print('Applied Vessel native dialog UX patch')
