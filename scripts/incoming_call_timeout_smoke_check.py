from pathlib import Path

text = Path('src/main.js').read_text(encoding='utf-8')

required = [
    'let incomingCallTimer = null;',
    'function clearIncomingCallTimer()',
    'incomingCallTimer=setTimeout(()=>{',
    'if(savedUser?.id!==user.id||incomingCall?.from!==incomingFrom)return;',
    '},32000);',
    "if (payload.type === 'bye') {\n      if (incomingCall?.from === payload.from) {\n        clearIncomingCallTimer();",
    'const invite=incomingCall;\n  clearIncomingCallTimer();\n  const access=await verifyDirectMessageAccess',
    'const invite=incomingCall; clearIncomingCallTimer(); incomingCall=null;',
    'clearCallDisconnectTimer();\n  clearIncomingCallTimer();\n  if(callInviteTimer)',
    'if(incomingCall?.from===row.friend_id){clearIncomingCallTimer();incomingCall=null;render();}',
]

missing = [marker for marker in required if marker not in text]
if missing:
    raise SystemExit('Incoming-call timeout regression: missing ' + ', '.join(missing))

if text.count('let incomingCallTimer = null;') != 1:
    raise SystemExit('Incoming-call timeout state must be declared exactly once')
if text.count('incomingCallTimer=setTimeout(()=>{') != 1:
    raise SystemExit('Incoming-call timeout must be scheduled exactly once per invite path')

print('Incoming-call timeout lifecycle smoke check passed')
