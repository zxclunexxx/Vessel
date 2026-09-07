from pathlib import Path

# Notification list items may navigate to the related DM or friend-request screen.
main_path = Path('src/main.js')
style_path = Path('src/style.css')
main = main_path.read_text(encoding='utf-8')
style = style_path.read_text(encoding='utf-8')
changed = False


def replace_once_or_already(source, old, new, label, marker=None):
    global changed
    if marker and marker in source:
        print(f'{label}: already applied')
        return source
    if new in source:
        print(f'{label}: already applied')
        return source
    if old not in source:
        raise SystemExit(f'{label}: expected source not found')
    changed = True
    print(f'{label}: applied')
    return source.replace(old, new, 1)


old_dialog = """function vesselListDialog(title,items=[],emptyText='Ничего нет') {
  const overlay=document.createElement('div');
  overlay.className='modal vessel-dialog';
  const content=items.length?items.map(item=>`<div class=\"dialog-list-item\"><div><b>${escapeHtml(item.title||'')}</b>${item.meta?`<time>${escapeHtml(item.meta)}</time>`:''}</div><p>${escapeHtml(item.body||'')}</p></div>`).join(''):`<div class=\"dialog-empty\">${escapeHtml(emptyText)}</div>`;
  overlay.innerHTML=`<div class=\"modal-card dialog-card dialog-list-card\"><button class=\"modal-close\" data-dialog-close>×</button><h2>${escapeHtml(title)}</h2><div class=\"dialog-list\">${content}</div></div>`;
  document.body.appendChild(overlay);
  const close=()=>overlay.remove();
  overlay.querySelector('[data-dialog-close]').addEventListener('click',close);
  overlay.addEventListener('click',event=>{if(event.target===overlay)close();});
}"""
new_dialog = """function vesselListDialog(title,items=[],emptyText='Ничего нет',onSelect=null) {
  const overlay=document.createElement('div');
  overlay.className='modal vessel-dialog';
  const content=items.length?items.map((item,index)=>{
    const inner=`<div><b>${escapeHtml(item.title||'')}</b>${item.meta?`<time>${escapeHtml(item.meta)}</time>`:''}</div><p>${escapeHtml(item.body||'')}</p>`;
    return onSelect&&item.value?`<button type=\"button\" class=\"dialog-list-item dialog-list-button\" data-list-index=\"${index}\">${inner}</button>`:`<div class=\"dialog-list-item\">${inner}</div>`;
  }).join(''):`<div class=\"dialog-empty\">${escapeHtml(emptyText)}</div>`;
  overlay.innerHTML=`<div class=\"modal-card dialog-card dialog-list-card\"><button class=\"modal-close\" data-dialog-close>×</button><h2>${escapeHtml(title)}</h2><div class=\"dialog-list\">${content}</div></div>`;
  document.body.appendChild(overlay);
  const close=()=>overlay.remove();
  overlay.querySelector('[data-dialog-close]').addEventListener('click',close);
  overlay.addEventListener('click',event=>{if(event.target===overlay)close();});
  overlay.querySelectorAll('[data-list-index]').forEach(button=>button.addEventListener('click',async()=>{
    const item=items[Number(button.dataset.listIndex)];
    close();
    try{await onSelect?.(item);}catch(error){console.warn('Dialog list action failed',error);vesselNotice('Не удалось открыть уведомление.','error');}
  }));
}"""
main = replace_once_or_already(main, old_dialog, new_dialog, 'actionable list dialog', marker="data-list-index=\"${index}\"")

old_notifications = """  document.querySelector('#notifications').addEventListener('click', async () => {
    vesselListDialog('Уведомления',notifications.map(item=>({title:item.title||'Vessel',body:item.body||'',meta:item.created_at?new Date(item.created_at).toLocaleString('ru-RU'):''})), 'Уведомлений пока нет');
    const sessionUserId=user.id;
    const unreadIds=notifications.filter(item=>!item.read_at&&item.type!=='direct_message').map(item=>item.id).filter(Boolean);
"""
new_notifications = """  document.querySelector('#notifications').addEventListener('click', async () => {
    const openNotification=async selected=>{
      const notification=notifications.find(item=>item.id===selected?.value);
      if(!notification)return;
      if(notification.type==='direct_message'&&notification.data?.sender_id){
        const peerId=notification.data.sender_id;
        let peer=dmThreads.find(item=>item.id===peerId)||friends.find(item=>item.id===peerId)||null;
        if(!peer&&supabase){
          const {data:profile,error}=await supabase.from('profiles').select('id,username,avatar_color,status').eq('id',peerId).maybeSingle();
          if(error)console.warn('Notification peer profile load failed',error);else peer=profile;
        }
        currentDm=peer?.username||'Пользователь';
        activeDmId=peerId;
        friendsOpen=false;
        window.__vesselDmLoaded=false;
        document.querySelector('.channels')?.classList.remove('mobile-open');
        render();
        await markDirectMessageNotificationsRead(user,peerId);
        return;
      }
      if(notification.type==='friend_request'){
        friendsOpen=true;
        currentDm=null;
        activeDmId=null;
        dmMessages=[];
        window.__vesselDmLoaded=false;
        document.querySelector('.channels')?.classList.remove('mobile-open');
        render();
      }
    };
    vesselListDialog('Уведомления',notifications.map(item=>({title:item.title||'Vessel',body:item.body||'',meta:item.created_at?new Date(item.created_at).toLocaleString('ru-RU'):'',value:['direct_message','friend_request'].includes(item.type)?item.id:null})), 'Уведомлений пока нет',openNotification);
    const sessionUserId=user.id;
    const unreadIds=notifications.filter(item=>!item.read_at&&item.type!=='direct_message').map(item=>item.id).filter(Boolean);
"""
main = replace_once_or_already(main, old_notifications, new_notifications, 'notification navigation', marker='const openNotification=async selected=>')

style_marker = '.dialog-list-button{'
if style_marker not in style:
    style += "\n.dialog-list-button{width:100%;text-align:left;border:0;color:inherit;font:inherit;cursor:pointer}.dialog-list-button:hover{background:rgba(255,255,255,.07)}\n"
    changed = True
    print('notification navigation styling: applied')
else:
    print('notification navigation styling: already applied')

if changed:
    main_path.write_text(main, encoding='utf-8')
    style_path.write_text(style, encoding='utf-8')
    print('Notification navigation patch applied')
else:
    print('Notification navigation patch already applied; nothing to change')
