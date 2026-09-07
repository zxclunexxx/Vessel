from pathlib import Path

path = Path('src/main.js')
text = path.read_text(encoding='utf-8')
changed = False

end_call_start = text.find('async function endCall(')
end_call_end = text.find('function toggleCallMicrophone', end_call_start)
end_call_block = text[end_call_start:end_call_end] if end_call_start >= 0 and end_call_end > end_call_start else ''
semantic_markers = [
    'let incomingCallTimer = null;',
    'function clearIncomingCallTimer()',
    'incomingCallTimer=setTimeout(()=>{',
    '},32000);',
    'if(incomingCall?.from===row.friend_id){clearIncomingCallTimer();incomingCall=null;render();}',
    'voiceDeafened=false;\n  clearIncomingCallTimer();\n  incomingCall=null;',
    'const invite=incomingCall;\n  clearIncomingCallTimer();',
    'const invite=incomingCall; clearIncomingCallTimer(); incomingCall=null;',
]
if all(marker in text for marker in semantic_markers) and 'clearIncomingCallTimer();' in end_call_block:
    print('Incoming-call timeout cleanup already applied; nothing to change')
    raise SystemExit(0)


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

end_call_start = text.find('async function endCall(')
end_call_end = text.find('function toggleCallMicrophone', end_call_start)
end_call_block = text[end_call_start:end_call_end] if end_call_start >= 0 and end_call_end > end_call_start else ''
if 'clearIncomingCallTimer();' not in end_call_block:
    old = """  callAccepted=false;\n  clearCallDisconnectTimer();\n  if(callInviteTimer){clearTimeout(callInviteTimer);callInviteTimer=null;}\n"""
    new = """  callAccepted=false;\n  clearCallDisconnectTimer();\n  clearIncomingCallTimer();\n  if(callInviteTimer){clearTimeout(callInviteTimer);callInviteTimer=null;}\n"""
    if old not in text:
        raise SystemExit('end call incoming timer cleanup anchor not found')
    text = text.replace(old, new, 1)
    changed = True
else:
    print('end call incoming timer cleanup already applied')

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
end_call_start = text.find('async function endCall(')
end_call_end = text.find('function toggleCallMicrophone', end_call_start)
if end_call_start < 0 or end_call_end <= end_call_start or 'clearIncomingCallTimer();' not in text[end_call_start:end_call_end]:
    raise SystemExit('missing end-call incoming timer cleanup')

if changed:
    path.write_text(text, encoding='utf-8')
    print('Applied stale incoming-call timeout cleanup')
else:
    print('Incoming-call timeout cleanup already applied; nothing to change')
