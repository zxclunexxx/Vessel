from pathlib import Path

path = Path('src/main.js')
main = path.read_text(encoding='utf-8')

modified = """    if(state==='connected'){clearCallDisconnectTimer();callIceRestartAttempts=0;callIceRestartInFlight=false;if(!callStartedAt)callStartedAt=Date.now();render();return;}
    if(state==='closed'){clearCallDisconnectTimer();syncRtcVisualRuntime();return;}
    if(['failed','disconnected'].includes(state)){render();scheduleCallDisconnectCleanup(connection,user,peerId,video);}
"""
verified = """    if(state==='connected'){clearCallDisconnectTimer();callIceRestartAttempts=0;callIceRestartInFlight=false;return;}
    if(state==='closed'){clearCallDisconnectTimer();return;}
    if(['failed','disconnected'].includes(state))scheduleCallDisconnectCleanup(connection,user,peerId,video);
"""

count = main.count(modified)
if count == 1:
    main = main.replace(modified, verified, 1)
elif main.count(verified) != 1:
    raise SystemExit(f'Call recovery compatibility source drift: modified={count}, verified={main.count(verified)}')

sync_anchor = """function syncRtcVisualRuntime(){
  const expected=new Map();"""
sync_new = """function syncRtcVisualRuntime(){
  if((callConnection||callStream)&&!callStartedAt)callStartedAt=Date.now();
  const expected=new Map();"""
if sync_new not in main:
    count = main.count(sync_anchor)
    if count != 1:
        raise SystemExit(f'RTC visual ticker source drift: expected 1, found {count}')
    main = main.replace(sync_anchor, sync_new, 1)

path.write_text(main, encoding='utf-8')
print('Preserved verified call recovery state machine and moved UI timing outside it')
