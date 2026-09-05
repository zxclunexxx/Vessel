from pathlib import Path

path = Path('src/main.js')
text = path.read_text(encoding='utf-8')

old = """    if (payload.from !== callPeer) return;
    if (payload.type === 'accept') {"""
new = """    if (payload.type === 'bye') {
      if (incomingCall?.from === payload.from) {
        incomingCall = null;
        render();
        return;
      }
      if (payload.from === callPeer) await endCall(false);
      return;
    }
    if (payload.from !== callPeer) return;
    if (payload.type === 'accept') {"""
if old not in text:
    raise SystemExit('call inbox peer gate not found')
text = text.replace(old, new, 1)

old = """    if (payload.type === 'bye') await endCall(false);
"""
if old in text:
    text = text.replace(old, '', 1)

old = """  callConnection.onconnectionstatechange=()=>{if(connection===callConnection&&['failed','closed'].includes(connection.connectionState)){endCall(false);}};"""
new = """  callConnection.onconnectionstatechange=()=>{
    if(connection!==callConnection) return;
    const state=connection.connectionState;
    if(['failed','closed'].includes(state)){endCall(false);return;}
    if(state==='disconnected'){
      setTimeout(()=>{
        if(connection===callConnection && connection.connectionState==='disconnected') endCall(false);
      },3000);
    }
  };"""
if old not in text:
    raise SystemExit('connection state handler not found')
text = text.replace(old, new, 1)

text = text.replace("if(signal.type==='bye'){endCall(false);return;}", "if(signal.type==='bye'){await endCall(false);return;}", 1)
text = text.replace("if(callConnection || callStream){endCall(true);return;}", "if(callConnection || callStream){await endCall(true);return;}", 1)

old = """  render();
  if(room&&supabase) supabase.removeChannel(room).catch(()=>{});
  if(notify&&peer&&user?.id) sendCallInvite(user,peer,{type:'bye'}).catch(()=>{});
}"""
new = """  render();
  if(notify&&peer&&user?.id&&room?.__subscribed){
    try {
      await room.send({type:'broadcast',event:'signal',payload:{from:user.id,to:peer,signal:{type:'bye'},video:false}});
    } catch(error) {
      console.warn('Call room hangup signal failed',error);
    }
  }
  if(notify&&peer&&user?.id){
    try { await sendCallInvite(user,peer,{type:'bye'}); } catch(error) { console.warn('Call inbox hangup signal failed',error); }
  }
  if(room&&supabase){ try { await supabase.removeChannel(room); } catch {} }
}"""
if old not in text:
    raise SystemExit('endCall tail not found')
text = text.replace(old, new, 1)

path.write_text(text, encoding='utf-8')
print('Applied call lifecycle reliability patch')
