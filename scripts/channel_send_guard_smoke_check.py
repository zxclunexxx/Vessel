from pathlib import Path

main=Path('src/main.js').read_text(encoding='utf-8')

required=[
    'async function verifyChannelAccess(user,channelId,{notify=true}={})',
    "supabase.from('channels').select('id').eq('id',channelId).maybeSingle()",
    'async function refreshAfterChannelAccessLoss(user,channelId)',
    'if((await verifyChannelAccess(user,channelId))!==true)return;',
    'const access=await verifyChannelAccess(user,channelId,{notify:false});',
    'if(targetChannelId&&(await verifyChannelAccess(user,targetChannelId))!==true)return;',
    'if(targetChannelId&&(await verifyChannelAccess(user,targetChannelId))!==true){await cleanupFailedAttachment(attachment);return;}',
    'const access=await verifyChannelAccess(user,targetChannelId,{notify:false});',
    "window.__vesselServersLoaded=false;",
]
for marker in required:
    if marker not in main:
        raise SystemExit(f'Missing stale channel send guard: {marker}')

helper_start=main.find('async function refreshAfterChannelAccessLoss(user,channelId)')
verify_start=main.find('async function verifyChannelAccess(user,channelId,{notify=true}={})')
composer_start=main.find("document.querySelector('.composer').addEventListener('submit'")
attach_start=main.find("document.querySelector('.attach').addEventListener('click'")
if min(helper_start,verify_start,composer_start,attach_start)<0:
    raise SystemExit('Channel send guard blocks are missing')

helper=main[helper_start:verify_start]
verify=main[verify_start:verify_start+1300]
composer=main[composer_start:attach_start]
attach=main[attach_start:attach_start+4200]

for marker in ["activeChannelId=null;","dbChannels=[];","messages=[];","await syncSupabaseServers(user);"]:
    if marker not in helper:
        raise SystemExit(f'Channel access loss refresh is incomplete: {marker}')
if "if(data)return true;" not in verify or "await refreshAfterChannelAccessLoss(user,channelId);" not in verify:
    raise SystemExit('Channel access verification must refresh inaccessible server state')
if composer.find('verifyChannelAccess(user,channelId)') > composer.find("supabase.from('messages').insert"):
    raise SystemExit('Channel text send must verify access before insert')
if attach.find('verifyChannelAccess(user,targetChannelId)') > attach.find('uploadVesselFile(file,user,attachmentContext)'):
    raise SystemExit('Channel attachment must verify access before upload')

print('Vessel stale channel send guard smoke check passed')
