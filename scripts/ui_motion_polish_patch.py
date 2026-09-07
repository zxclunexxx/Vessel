from pathlib import Path

main_path = Path('src/main.js')
style_path = Path('src/style.css')
main = main_path.read_text(encoding='utf-8')
style = style_path.read_text(encoding='utf-8')
marker = 'VESSEL_UI_MOTION_POLISH_V1'


def replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected exactly one anchor, found {count}')
    return source.replace(old, new, 1)


if marker in main or marker in style:
    raise SystemExit('Motion/polish migration marker already exists; refusing partial or repeated application')

old_notice = """function vesselNotice(message,type='info') {
  const toast=document.createElement('div');
  toast.className=`vessel-toast ${type}`;
  toast.textContent=message;
  document.body.appendChild(toast);
  requestAnimationFrame(()=>toast.classList.add('show'));
  setTimeout(()=>{toast.classList.remove('show');setTimeout(()=>toast.remove(),180);},3200);
}
"""
new_notice = """/* VESSEL_UI_MOTION_POLISH_V1 */
function ensureVesselToastStack() {
  let stack=document.querySelector('#vessel-toast-stack');
  if(stack)return stack;
  stack=document.createElement('div');
  stack.id='vessel-toast-stack';
  stack.className='vessel-toast-stack';
  stack.setAttribute('aria-live','polite');
  stack.setAttribute('aria-atomic','false');
  document.body.appendChild(stack);
  return stack;
}
function vesselNotice(message,type='info') {
  const tone=['success','error','info'].includes(type)?type:'info';
  const stack=ensureVesselToastStack();
  const toast=document.createElement('div');
  toast.className=`vessel-toast ${tone}`;
  toast.setAttribute('role',tone==='error'?'alert':'status');
  const icon=document.createElement('span');
  icon.className='vessel-toast-icon';
  icon.textContent=tone==='success'?'✓':tone==='error'?'!':'i';
  const copy=document.createElement('span');
  copy.className='vessel-toast-copy';
  copy.textContent=String(message||'');
  const close=document.createElement('button');
  close.type='button';
  close.className='vessel-toast-close';
  close.setAttribute('aria-label','Закрыть уведомление');
  close.textContent='×';
  toast.append(icon,copy,close);
  stack.appendChild(toast);
  let dismissed=false;
  const dismiss=()=>{
    if(dismissed)return;
    dismissed=true;
    toast.classList.remove('show');
    toast.classList.add('leaving');
    setTimeout(()=>{
      toast.remove();
      if(!stack.childElementCount)stack.remove();
    },240);
  };
  close.addEventListener('click',dismiss);
  requestAnimationFrame(()=>toast.classList.add('show'));
  setTimeout(dismiss,3600);
}
function triggerVesselViewMotion(previousContext,currentContext) {
  if(previousContext===currentContext)return;
  if(window.matchMedia?.('(prefers-reduced-motion: reduce)').matches)return;
  const targets=[
    ['.chat-head','view-motion-head'],
    ['.messages','view-motion-content'],
    ['.composer:not(.hidden)','view-motion-composer'],
    ['.rtc-stage','view-motion-stage']
  ];
  requestAnimationFrame(()=>targets.forEach(([selector,className])=>{
    const node=document.querySelector(selector);
    if(!node)return;
    node.classList.add(className);
    node.addEventListener('animationend',()=>node.classList.remove(className),{once:true});
  }));
}
"""
main = replace_once(main, old_notice, new_notice, 'toast runtime')

old_render_start = """function render() {
  const previousMessagesPane=document.querySelector('.messages');
"""
new_render_start = """function render() {
  document.body.classList.remove('mobile-drawer-open');
  const previousMessagesPane=document.querySelector('.messages');
"""
main = replace_once(main, old_render_start, new_render_start, 'render mobile state cleanup')

old_view_hook = """  lastRenderedMessageContext=currentMessageContext;
  document.querySelector('.composer').addEventListener('submit', async e => {
"""
new_view_hook = """  lastRenderedMessageContext=currentMessageContext;
  triggerVesselViewMotion(previousMessageContext,currentMessageContext);
  document.querySelector('.composer').addEventListener('submit', async e => {
"""
main = replace_once(main, old_view_hook, new_view_hook, 'view transition hook')

old_drawer = """  const setMobileDrawerOpen=open=>document.querySelector('.channels')?.classList.toggle('mobile-open',Boolean(open));
"""
new_drawer = """  const setMobileDrawerOpen=open=>{
    const channels=document.querySelector('.channels');
    const next=Boolean(open&&channels);
    channels?.classList.toggle('mobile-open',next);
    document.body.classList.toggle('mobile-drawer-open',next);
    let scrim=document.querySelector('.mobile-drawer-scrim');
    if(next&&!scrim){
      scrim=document.createElement('button');
      scrim.type='button';
      scrim.className='mobile-drawer-scrim';
      scrim.setAttribute('aria-label','Закрыть меню каналов');
      document.querySelector('.shell')?.appendChild(scrim);
      scrim.addEventListener('click',()=>setMobileDrawerOpen(false));
      requestAnimationFrame(()=>scrim?.classList.add('show'));
    }else if(!next&&scrim){
      scrim.classList.remove('show');
      setTimeout(()=>scrim?.remove(),180);
    }
  };
"""
main = replace_once(main, old_drawer, new_drawer, 'mobile drawer polish')

style_block = r'''

/* VESSEL_UI_MOTION_POLISH_V1 */
:root {
  --v-motion-view: 300ms;
  --v-motion-modal: 240ms;
  --v-motion-toast: 260ms;
  --v-ease-emphasized: cubic-bezier(.2,.78,.22,1);
  --v-ease-exit: cubic-bezier(.4,0,1,1);
}

::selection { background: rgba(139,92,255,.38); color: #fff; }
button, input, select, a { -webkit-tap-highlight-color: transparent; }
button { touch-action: manipulation; user-select: none; }
.messages, .channels, .members { overscroll-behavior: contain; }
.friend-row.friend-card,
.voice-participant-card,
.remote-video-tile,
.local-preview,
.dialog-list-item { contain: paint; }

/* Context changes animate once; ordinary realtime renders stay still. */
.view-motion-head { animation: vesselViewHeadIn var(--v-motion-view) var(--v-ease-emphasized) both; will-change: transform, opacity; }
.view-motion-content { animation: vesselViewContentIn var(--v-motion-view) var(--v-ease-emphasized) both; will-change: transform, opacity; }
.view-motion-composer { animation: vesselViewComposerIn calc(var(--v-motion-view) + 40ms) var(--v-ease-emphasized) both; will-change: transform, opacity; }
.view-motion-stage { animation: vesselViewStageIn calc(var(--v-motion-view) + 30ms) var(--v-ease-emphasized) both; will-change: transform, opacity; }
@keyframes vesselViewHeadIn { from { opacity:.68; transform:translate3d(0,-6px,0); } to { opacity:1; transform:none; } }
@keyframes vesselViewContentIn { from { opacity:.25; transform:translate3d(0,9px,0); } to { opacity:1; transform:none; } }
@keyframes vesselViewComposerIn { from { opacity:.25; transform:translate3d(0,8px,0) scale(.995); } to { opacity:1; transform:none; } }
@keyframes vesselViewStageIn { from { opacity:.25; transform:translate3d(0,8px,0) scale(.992); } to { opacity:1; transform:none; } }

/* Unified tactile feedback without forcing hover effects on touch devices. */
.primary,
.auth-switch,
.dialog-choice,
.attachment-link,
.friend-action,
.rtc-dock-button,
.message-actions button,
.modal-close,
.more,
.icon-btn,
.member-manage,
.section-title button,
.head-actions button,
.composer button {
  transform-origin: center;
}
.primary { position: relative; overflow: hidden; }
.primary::after {
  content: '';
  position: absolute;
  top: -70%;
  bottom: -70%;
  left: -42%;
  width: 25%;
  pointer-events: none;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,.22), transparent);
  transform: skewX(-20deg) translateX(-260%);
  transition: transform 540ms var(--v-ease-emphasized);
}
@media (hover:hover) and (pointer:fine) {
  .primary:hover::after { transform: skewX(-20deg) translateX(720%); }
  .dialog-choice:hover,
  .attachment-link:hover,
  .friend-action:hover,
  .rtc-dock-button:hover,
  .message-actions button:hover,
  .modal-close:hover,
  .more:hover,
  .icon-btn:hover,
  .member-manage:hover,
  .section-title button:hover,
  .head-actions button:hover,
  .composer button:hover { filter: brightness(1.055); }
}
button:active:not(:disabled),
.attachment-link:active { transform: translate3d(0,1px,0) scale(.965)!important; }

/* Modal system: one material language for settings, prompts and lists. */
.modal:not(.hidden):not(.incoming-call-modal) {
  animation: vesselModalBackdropIn var(--v-motion-modal) ease-out both;
}
.modal:not(.hidden):not(.incoming-call-modal) > .modal-card {
  overflow: hidden;
  animation: vesselModalCardIn var(--v-motion-modal) var(--v-ease-emphasized) both;
  transform-origin: 50% 56%;
}
.modal-card::before {
  content: '';
  position: absolute;
  left: 14%;
  right: 14%;
  top: 0;
  height: 1px;
  pointer-events: none;
  background: linear-gradient(90deg, transparent, rgba(120,220,255,.42), rgba(176,117,255,.45), transparent);
  opacity: .72;
}
.modal-close {
  width: 34px;
  height: 34px;
  right: 14px;
  top: 12px;
  display: grid;
  place-items: center;
  border: 1px solid transparent;
  border-radius: 11px;
  line-height: 1;
  transition: transform var(--v-fast) var(--v-ease-ui), background var(--v-fast), color var(--v-fast), border-color var(--v-fast);
}
.modal-close:hover { color:#fff; background:rgba(255,255,255,.065); border-color:rgba(255,255,255,.07); transform:rotate(4deg) scale(1.04); }
.dialog-choice {
  position: relative;
  min-height: 44px;
  border-radius: 13px;
  transition: transform var(--v-fast) var(--v-ease-ui), background var(--v-fast), border-color var(--v-fast), box-shadow var(--v-fast);
}
.dialog-choice:hover { box-shadow: 0 9px 22px rgba(0,0,0,.16); transform: translateY(-1px); }
.dialog-list { scrollbar-width: thin; scrollbar-color: rgba(139,92,255,.25) transparent; }
@keyframes vesselModalBackdropIn { from { opacity:0; } to { opacity:1; } }
@keyframes vesselModalCardIn { from { opacity:0; transform:translate3d(0,12px,0) scale(.975); } to { opacity:1; transform:none; } }

/* Toasts stack instead of overlapping each other. */
.vessel-toast-stack {
  position: fixed;
  right: max(18px, env(safe-area-inset-right));
  bottom: max(18px, env(safe-area-inset-bottom));
  z-index: 80;
  width: min(390px, calc(100vw - 32px));
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 9px;
  pointer-events: none;
}
.vessel-toast-stack .vessel-toast {
  position: relative;
  right: auto;
  bottom: auto;
  width: 100%;
  max-width: none;
  min-height: 54px;
  display: grid;
  grid-template-columns: 30px minmax(0,1fr) 28px;
  align-items: center;
  gap: 10px;
  padding: 10px 10px 10px 12px;
  overflow: hidden;
  pointer-events: auto;
  opacity: 0;
  transform: translate3d(0,12px,0) scale(.985);
  transition: opacity var(--v-motion-toast), transform var(--v-motion-toast) var(--v-ease-emphasized), border-color var(--v-fast);
}
.vessel-toast-stack .vessel-toast.show { opacity:1; transform:none; }
.vessel-toast-stack .vessel-toast.leaving { opacity:0; transform:translate3d(8px,0,0) scale(.985); transition-timing-function:var(--v-ease-exit); }
.vessel-toast-icon {
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border: 1px solid rgba(160,184,255,.14);
  border-radius: 10px;
  color: #b7d8ff;
  background: rgba(97,118,181,.10);
  font-size: 12px;
  font-weight: 800;
  box-shadow: inset 0 1px 0 rgba(255,255,255,.06);
}
.vessel-toast.success .vessel-toast-icon { color:#9ff2d3; border-color:rgba(94,231,178,.22); background:rgba(94,231,178,.09); }
.vessel-toast.error .vessel-toast-icon { color:#ff9bb3; border-color:rgba(255,111,145,.24); background:rgba(255,111,145,.09); }
.vessel-toast-copy { min-width:0; color:var(--v-text-1); font-size:12px; line-height:1.45; overflow-wrap:anywhere; }
.vessel-toast-close {
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border: 0;
  border-radius: 9px;
  color: var(--v-text-3);
  background: transparent;
  font-size: 18px;
  cursor: pointer;
  transition: color var(--v-fast), background var(--v-fast), transform var(--v-fast) var(--v-ease-ui);
}
.vessel-toast-close:hover { color:#fff; background:rgba(255,255,255,.06); }
.vessel-toast-stack .vessel-toast::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 2px;
  transform-origin: left center;
  background: linear-gradient(90deg, var(--v-cyan), var(--v-violet));
  animation: vesselToastLife 3600ms linear forwards;
  opacity: .52;
}
.vessel-toast.success::after { background: linear-gradient(90deg, var(--v-green), var(--v-cyan)); }
.vessel-toast.error::after { background: linear-gradient(90deg, var(--v-danger), var(--v-magenta)); }
@keyframes vesselToastLife { from { transform:scaleX(1); } to { transform:scaleX(0); } }

/* Mobile drawer gets a real scrim, safe-area spacing and larger touch targets. */
.mobile-drawer-scrim { display: none; }
@media (max-width: 600px) {
  .shell { height: 100dvh; padding-bottom: max(6px, env(safe-area-inset-bottom)); }
  .servers { padding-top: max(10px, env(safe-area-inset-top)); }
  .channels { overscroll-behavior: contain; }
  .mobile-drawer-scrim {
    display: block;
    position: fixed;
    inset: 6px 6px max(6px, env(safe-area-inset-bottom)) 62px;
    z-index: 24;
    border: 0;
    border-radius: 21px;
    background: rgba(2,5,12,.54);
    backdrop-filter: blur(5px);
    -webkit-backdrop-filter: blur(5px);
    opacity: 0;
    transition: opacity 180ms ease-out;
  }
  .mobile-drawer-scrim.show { opacity:1; }
  body.mobile-drawer-open .chat { transform: scale(.997); }
  .channel { min-height: 44px; }
  .head-actions button,
  .composer button,
  .mobile-drawer-close { min-width: 40px; min-height: 40px; }
  .composer { margin-bottom: max(10px, env(safe-area-inset-bottom)); }
  .vessel-toast-stack {
    left: 68px;
    right: 10px;
    bottom: max(10px, env(safe-area-inset-bottom));
    width: auto;
  }
  .modal:not(.hidden):not(.incoming-call-modal) {
    place-items: end center;
    padding: 0 6px max(6px, env(safe-area-inset-bottom));
  }
  .modal:not(.hidden):not(.incoming-call-modal) > .modal-card {
    width: 100%;
    max-height: min(88dvh, 720px);
    overflow-y: auto;
    border-radius: 24px 24px 18px 18px;
    animation-name: vesselSheetIn;
  }
  .servers,
  .channels,
  .chat,
  .members { backdrop-filter: blur(15px) saturate(118%); -webkit-backdrop-filter: blur(15px) saturate(118%); }
  .brand,
  .chat-head,
  .composer { backdrop-filter: blur(13px) saturate(115%); -webkit-backdrop-filter: blur(13px) saturate(115%); }
}
@keyframes vesselSheetIn { from { opacity:0; transform:translate3d(0,22px,0) scale(.99); } to { opacity:1; transform:none; } }

@media (prefers-reduced-motion: reduce) {
  .view-motion-head,
  .view-motion-content,
  .view-motion-composer,
  .view-motion-stage,
  .modal:not(.hidden):not(.incoming-call-modal),
  .modal:not(.hidden):not(.incoming-call-modal) > .modal-card,
  .vessel-toast-stack .vessel-toast,
  .vessel-toast-stack .vessel-toast::after,
  .auth-card { animation: none!important; transition-duration:.01ms!important; }
  .primary::after { display:none; }
}
'''
style = style.rstrip() + style_block + '\n'

main_path.write_text(main, encoding='utf-8')
style_path.write_text(style, encoding='utf-8')
print('Vessel UI Motion + Polish migration applied')
