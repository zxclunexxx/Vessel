from pathlib import Path

path = Path('src/main.js')
text = path.read_text(encoding='utf-8')
changed = False

required = [
    'let callDisconnectTimer = null;',
    'function clearCallDisconnectTimer()',
    'function scheduleCallDisconnectCleanup(connection)',
    "const delay=state==='failed'?5000:8000;",
    "if(state==='connected'){clearCallDisconnectTimer();return;}",
    "if(['failed','disconnected'].includes(state))scheduleCallDisconnectCleanup(connection);",
    "vesselNotice('Связь со звонком прервалась. Попробуй позвонить снова.','error');",
    'callAccepted=false;\n  clearCallDisconnectTimer();',
]
if all(marker in text for marker in required):
    print('Call network-loss handling already applied; nothing to change')
    raise SystemExit(0)

if 'let callDisconnectTimer = null;' not in text:
    anchor = 'let callInviteTimer = null;\n'
    if anchor not in text:
        raise SystemExit('call timer global anchor not found')
    text = text.replace(anchor, anchor + 'let callDisconnectTimer = null;\n', 1)
    changed = True

old_prepare = '''function prepareCallConnection(user,peerId,video) {
  if (callConnection) return callConnection;
  callConnection=new RTCPeerConnection({iceServers:[{urls:'stun:stun.l.google.com:19302'}]});'''
new_prepare = '''function clearCallDisconnectTimer(){
  if(callDisconnectTimer){clearTimeout(callDisconnectTimer);callDisconnectTimer=null;}
}
function scheduleCallDisconnectCleanup(connection){
  if(connection!==callConnection||callDisconnectTimer)return;
  const state=connection.connectionState;
  const delay=state==='failed'?5000:8000;
  callDisconnectTimer=setTimeout(async()=>{
    callDisconnectTimer=null;
    if(connection!==callConnection)return;
    if(!['failed','disconnected'].includes(connection.connectionState))return;
    vesselNotice('Связь со звонком прервалась. Попробуй позвонить снова.','error');
    await endCall(false);
  },delay);
}
function prepareCallConnection(user,peerId,video) {
  if (callConnection) return callConnection;
  callConnection=new RTCPeerConnection({iceServers:[{urls:'stun:stun.l.google.com:19302'}]});'''
if 'function scheduleCallDisconnectCleanup(connection)' not in text:
    if old_prepare not in text:
        raise SystemExit('call connection helper anchor not found')
    text = text.replace(old_prepare, new_prepare, 1)
    changed = True

old_state = '''  callConnection.onconnectionstatechange=()=>{
    if(connection!==callConnection) return;
    const state=connection.connectionState;
    if(['failed','closed'].includes(state)){endCall(false);return;}
    if(state==='disconnected'){
      setTimeout(()=>{
        if(connection===callConnection && connection.connectionState==='disconnected') endCall(false);
      },3000);
    }
  };'''
new_state = '''  callConnection.onconnectionstatechange=()=>{
    if(connection!==callConnection)return;
    const state=connection.connectionState;
    if(state==='connected'){clearCallDisconnectTimer();return;}
    if(state==='closed'){clearCallDisconnectTimer();return;}
    if(['failed','disconnected'].includes(state))scheduleCallDisconnectCleanup(connection);
  };'''
if "if(['failed','disconnected'].includes(state))scheduleCallDisconnectCleanup(connection);" not in text:
    if old_state not in text:
        raise SystemExit('call connection-state anchor not found')
    text = text.replace(old_state, new_state, 1)
    changed = True

old_end = '''  callOffer=null;
  callVideo=false;
  callAccepted=false;
  if(callInviteTimer){clearTimeout(callInviteTimer);callInviteTimer=null;}'''
new_end = '''  callOffer=null;
  callVideo=false;
  callAccepted=false;
  clearCallDisconnectTimer();
  if(callInviteTimer){clearTimeout(callInviteTimer);callInviteTimer=null;}'''
if 'callAccepted=false;\n  clearCallDisconnectTimer();' not in text:
    if old_end not in text:
        raise SystemExit('call cleanup anchor not found')
    text = text.replace(old_end, new_end)
    changed = True

for marker in required:
    if marker not in text:
        raise SystemExit(f'missing call network-loss marker: {marker}')

if changed:
    path.write_text(text, encoding='utf-8')
    print('Call network-loss handling applied')
else:
    print('Call network-loss handling already applied; nothing to change')
