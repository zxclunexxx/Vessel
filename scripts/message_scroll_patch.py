from pathlib import Path

path = Path('src/main.js')
text = path.read_text(encoding='utf-8')
changed = False


def replace_once(old, new, label, marker=None):
    global text, changed
    if marker and marker in text:
        print(f'{label}: already applied')
        return
    if new in text:
        print(f'{label}: already applied')
        return
    if old not in text:
        raise SystemExit(f'{label}: expected source not found')
    text = text.replace(old, new, 1)
    changed = True
    print(f'{label}: applied')


replace_once(
    """let notificationsSyncRevision = 0;
let serverMembers = [];
""",
    """let notificationsSyncRevision = 0;
let serverMembers = [];
let lastRenderedMessageContext = null;
""",
    'message scroll context state',
    marker='let lastRenderedMessageContext = null;',
)

replace_once(
    """function render() {
  if (!savedUser) {
""",
    """function render() {
  const previousMessagesPane=document.querySelector('.messages');
  const previousMessageContext=lastRenderedMessageContext;
  const previousMessageScroll=previousMessagesPane?{
    top:previousMessagesPane.scrollTop,
    atBottom:(previousMessagesPane.scrollHeight-previousMessagesPane.scrollTop-previousMessagesPane.clientHeight)<80
  }:null;
  if (!savedUser) {
    lastRenderedMessageContext=null;
""",
    'capture message scroll before render',
    marker='const previousMessageContext=lastRenderedMessageContext;',
)

replace_once(
    """  const user = savedUser;
  connectSupabaseRealtime(user);""",
    """  const user = savedUser;
  const currentMessageContext=friendsOpen
    ? `user:${user.id}:friends`
    : activeDmId
      ? `user:${user.id}:dm:${activeDmId}`
      : `user:${user.id}:channel:${activeChannelId||'none'}:${activeChannelKind}`;
  connectSupabaseRealtime(user);""",
    'message render context key',
    marker='const currentMessageContext=friendsOpen',
)

replace_once(
    """  document.querySelector('.composer').addEventListener('submit', async e => {
""",
    """  const nextMessagesPane=document.querySelector('.messages');
  if(nextMessagesPane){
    const contextChanged=previousMessageContext!==currentMessageContext;
    if(contextChanged||!previousMessageScroll||previousMessageScroll.atBottom){
      requestAnimationFrame(()=>{
        if(nextMessagesPane.isConnected)nextMessagesPane.scrollTop=nextMessagesPane.scrollHeight;
      });
    }else{
      const maxTop=Math.max(0,nextMessagesPane.scrollHeight-nextMessagesPane.clientHeight);
      nextMessagesPane.scrollTop=Math.min(previousMessageScroll.top,maxTop);
    }
  }
  lastRenderedMessageContext=currentMessageContext;
  document.querySelector('.composer').addEventListener('submit', async e => {
""",
    'restore smart message scroll after render',
    marker='const nextMessagesPane=document.querySelector(\'.messages\');',
)

required = [
    'let lastRenderedMessageContext = null;',
    'const previousMessageContext=lastRenderedMessageContext;',
    'const currentMessageContext=friendsOpen',
    'const nextMessagesPane=document.querySelector(\'.messages\');',
    'previousMessageScroll.atBottom',
]
for marker in required:
    if marker not in text:
        raise SystemExit(f'missing message scroll marker: {marker}')

if changed:
    path.write_text(text, encoding='utf-8')
    print('Smart message scroll patch applied')
else:
    print('Smart message scroll patch already applied; nothing to change')
