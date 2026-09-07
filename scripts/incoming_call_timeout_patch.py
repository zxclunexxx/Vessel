from pathlib import Path

path = Path('src/main.js')
text = path.read_text(encoding='utf-8')
changed = False


def replace_once(old, new, label):
    global text, changed
    if new in text:
        print(f'{label} already applied')
        return
    if old not in text:
        raise SystemExit(f'{label} anchor not found')
    text = text.replace(old, new, 1)
    changed = True


replace_once(
    """let callInviteTimer = null;\nlet callDisconnectTimer = null;\n""",
    """let callInviteTimer = null;\nlet incomingCallTimer = null;\nlet callDisconnectTimer = null;\n""",
    'incoming call timer state',
)

replace_once(
    """function clearCallDisconnectTimer(){\n  if(callDisconnectTimer){clearTimeout(callDisconnectTimer);callDisconnectTimer=null;}\n}\n""",
    """function clearIncomingCallTimer(){\n  if(incomingCallTimer){clearTimeout(incomingCallTimer);incomingCallTimer=null;}\n}\nfunction clearCallDisconnectTimer(){\n  if(callDisconnectTimer){clearTimeout(callDisconnectTimer);callDisconnectTimer=null;}\n}\n""",
    'incoming call timer helper',
)

replace_once(
    """      incomingCall = {from:payload.from, name:caller.username || 'Пользователь', video:!!payload.video, offer:payload.offer};\n      render();\n      return;\n""",
    """      incomingCall = {from:payload.from, name:caller.username || 'Пользователь', video:!!payload.video, offer:payload.offer};\n      clearIncomingCallTimer();\n      const incomingFrom=payload.from;\n      incomingCallTimer=setTimeout(()=>{\n        incomingCallTimer=null;\n        if(savedUser?.id!==user.id||incomingCall?.from!==incomingFrom)return;\n        incomingCall=null;\n        render();\n      },32000);\n      render();\n      return;\n""",
    'incoming invite expiry',
)

replace_once(
    """      if (incomingCall?.from === payload.from) {\n        incomingCall = null;\n        render();\n        return;\n      }\n""",
    """      if (incomingCall?.from === payload.from) {\n        clearIncomingCallTimer();\n        incomingCall = null;\n        render();\n        return;\n      }\n""",
    'incoming bye timer cleanup',
)

replace_once(
    """        if(incomingCall?.from===row.friend_id){incomingCall=null;render();}\n""",
    """        if(incomingCall?.from===row.friend_id){clearIncomingCallTimer();incomingCall=null;render();}\n""",
    'friend removal incoming timer cleanup',
)

replace_once(
    """  voiceDeafened=false;\n  incomingCall=null;\n""",
    """  voiceDeafened=false;\n  clearIncomingCallTimer();\n  incomingCall=null;\n""",
    'auth reset incoming timer cleanup',
)

replace_once(
    """async function acceptIncomingCall(user) {\n  if (!incomingCall || !user?.id) return;\n  const invite=incomingCall;\n""",
    """async function acceptIncomingCall(user) {\n  if (!incomingCall || !user?.id) return;\n  const invite=incomingCall;\n  clearIncomingCallTimer();\n""",
    'accept incoming timer cleanup',
)

replace_once(
    """async function rejectIncomingCall(user) {\n  if (!incomingCall) return;\n  const invite=incomingCall; incomingCall=null;\n""",
    """async function rejectIncomingCall(user) {\n  if (!incomingCall) return;\n  const invite=incomingCall; clearIncomingCallTimer(); incomingCall=null;\n""",
    'reject incoming timer cleanup',
)

replace_once(
    """  callAccepted=false;\n  clearCallDisconnectTimer();\n  if(callInviteTimer){clearTimeout(callInviteTimer);callInviteTimer=null;}\n""",
    """  callAccepted=false;\n  clearCallDisconnectTimer();\n  clearIncomingCallTimer();\n  if(callInviteTimer){clearTimeout(callInviteTimer);callInviteTimer=null;}\n""",
    'end call incoming timer cleanup',
)

required = [
    'let incomingCallTimer = null;',
    'function clearIncomingCallTimer()',
    'incomingCallTimer=setTimeout(()=>{',
    '},32000);',
    'clearIncomingCallTimer();\n        incomingCall = null;',
    'const invite=incomingCall;\n  clearIncomingCallTimer();',
    'const invite=incomingCall; clearIncomingCallTimer(); incomingCall=null;',
]
for marker in required:
    if marker not in text:
        raise SystemExit(f'missing incoming call timeout marker: {marker}')

if changed:
    path.write_text(text, encoding='utf-8')
    print('Applied stale incoming-call timeout cleanup')
else:
    print('Incoming-call timeout cleanup already applied; nothing to change')
