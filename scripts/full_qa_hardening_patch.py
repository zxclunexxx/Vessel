from pathlib import Path

root = Path(__file__).resolve().parents[1]
main_path = root / 'src' / 'main.js'
text = main_path.read_text(encoding='utf-8')
marker = '/* VESSEL_FULL_QA_HARDENING_V1 */'
if marker in text:
    print('Full QA hardening patch already applied')
    raise SystemExit(0)

old_status = """function statusLabel(value='online') {\n  const key=String(value||'online').toLowerCase();\n  if(['dnd','не беспокоить'].includes(key))return 'Не беспокоить';\n  if(['away','idle','отошёл'].includes(key))return 'Отошёл';\n  return 'В сети';\n}\n"""
new_status = """function statusLabel(value='online') {\n  const key=String(value||'online').toLowerCase();\n  if(['dnd','не беспокоить'].includes(key))return 'Не беспокоить';\n  if(['away','idle','отошёл'].includes(key))return 'Отошёл';\n  if(['offline','не в сети'].includes(key))return 'Не в сети';\n  return 'В сети';\n}\n"""
if old_status not in text:
    raise SystemExit('statusLabel anchor not found')
text = text.replace(old_status, new_status, 1)

old_dialog = """function vesselDialog({title,message='',input=false,value='',placeholder='',choices=[]}) {\n  return new Promise(resolve=>{\n    const overlay=document.createElement('div');\n    overlay.className='modal vessel-dialog';\n    const choiceMarkup=choices.map(choice=>`<button type=\"button\" class=\"dialog-choice ${choice.danger?'dialog-danger':''}\" data-dialog-value=\"${escapeHtml(choice.value)}\">${escapeHtml(choice.label)}</button>`).join('');\n    overlay.innerHTML=`<div class=\"modal-card dialog-card\"><button class=\"modal-close\" data-dialog-cancel>×</button><h2>${escapeHtml(title)}</h2>${message?`<p>${escapeHtml(message)}</p>`:''}${input?`<input class=\"dialog-input\" value=\"${escapeHtml(value)}\" placeholder=\"${escapeHtml(placeholder)}\" />`:''}<div class=\"dialog-actions\">${choiceMarkup}${input?'<button type=\"button\" class=\"primary\" data-dialog-submit>Готово</button>':''}</div></div>`;\n    document.body.appendChild(overlay);\n    const finish=result=>{overlay.remove();resolve(result);};\n    overlay.querySelector('[data-dialog-cancel]').addEventListener('click',()=>finish(null));\n    overlay.addEventListener('click',event=>{if(event.target===overlay)finish(null);});\n    overlay.querySelectorAll('[data-dialog-value]').forEach(button=>button.addEventListener('click',()=>finish(button.dataset.dialogValue)));\n    if(input){\n      const field=overlay.querySelector('.dialog-input');\n      const submit=()=>finish(field.value);\n      overlay.querySelector('[data-dialog-submit]').addEventListener('click',submit);\n      field.addEventListener('keydown',event=>{if(event.key==='Enter')submit();if(event.key==='Escape')finish(null);});\n      setTimeout(()=>{field.focus();field.select();},0);\n    }\n  });\n}\n"""
new_dialog = """function vesselDialog({title,message='',input=false,value='',placeholder='',choices=[]}) {\n  return new Promise(resolve=>{\n    const previousFocus=document.activeElement;\n    const overlay=document.createElement('div');\n    overlay.className='modal vessel-dialog';\n    overlay.setAttribute('role','dialog');\n    overlay.setAttribute('aria-modal','true');\n    const choiceMarkup=choices.map(choice=>`<button type=\"button\" class=\"dialog-choice ${choice.danger?'dialog-danger':''}\" data-dialog-value=\"${escapeHtml(choice.value)}\">${escapeHtml(choice.label)}</button>`).join('');\n    overlay.innerHTML=`<div class=\"modal-card dialog-card\"><button class=\"modal-close\" data-dialog-cancel aria-label=\"Закрыть диалог\">×</button><h2>${escapeHtml(title)}</h2>${message?`<p>${escapeHtml(message)}</p>`:''}${input?`<input class=\"dialog-input\" value=\"${escapeHtml(value)}\" placeholder=\"${escapeHtml(placeholder)}\" />`:''}<div class=\"dialog-actions\">${choiceMarkup}${input?'<button type=\"button\" class=\"primary\" data-dialog-submit>Готово</button>':''}</div></div>`;\n    document.body.appendChild(overlay);\n    let finished=false;\n    const finish=result=>{\n      if(finished)return;\n      finished=true;\n      document.removeEventListener('keydown',onKeyDown,true);\n      overlay.remove();\n      if(previousFocus?.isConnected&&typeof previousFocus.focus==='function')previousFocus.focus();\n      resolve(result);\n    };\n    const onKeyDown=event=>{if(event.key==='Escape'){event.preventDefault();finish(null);}};\n    document.addEventListener('keydown',onKeyDown,true);\n    overlay.querySelector('[data-dialog-cancel]').addEventListener('click',()=>finish(null));\n    overlay.addEventListener('click',event=>{if(event.target===overlay)finish(null);});\n    overlay.querySelectorAll('[data-dialog-value]').forEach(button=>button.addEventListener('click',()=>finish(button.dataset.dialogValue)));\n    const field=input?overlay.querySelector('.dialog-input'):null;\n    if(field){\n      const submit=()=>finish(field.value);\n      overlay.querySelector('[data-dialog-submit]').addEventListener('click',submit);\n      field.addEventListener('keydown',event=>{if(event.key==='Enter'){event.preventDefault();submit();}});\n    }\n    setTimeout(()=>{\n      const target=field||overlay.querySelector('[data-dialog-value], [data-dialog-submit], [data-dialog-cancel]');\n      target?.focus();\n      if(field)field.select();\n    },0);\n  });\n}\n"""
if old_dialog not in text:
    raise SystemExit('vesselDialog anchor not found')
text = text.replace(old_dialog, new_dialog, 1)

old_reset = """function resetAuthenticatedRuntime() {\n  clearDataRealtimeRecovery();\n  cancelVoiceReconnect();\n  cancelAllVoicePeerReconnects();\n  cancelCallInboxReconnect();\n  cancelCallSignalReconnect();\n  resetRtcConfiguration();\n  dmMessagesSyncRevision++;\n"""
new_reset = """function resetAuthenticatedRuntime() {\n  clearDataRealtimeRecovery();\n  cancelVoiceReconnect();\n  cancelAllVoicePeerReconnects();\n  cancelCallInboxReconnect();\n  cancelCallSignalReconnect();\n  resetRtcConfiguration();\n  stopSpeakingMeters();\n  syncCallUiTicker(false);\n  callStartedAt=0;\n  dmMessagesSyncRevision++;\n"""
if old_reset not in text:
    raise SystemExit('resetAuthenticatedRuntime anchor not found')
text = text.replace(old_reset, new_reset, 1)

insert_anchor = "/* VESSEL_AUTH_EMAIL_RESILIENCE_V1 */"
if insert_anchor not in text:
    raise SystemExit('hardening marker insertion anchor not found')
text = text.replace(insert_anchor, marker + "\n" + insert_anchor, 1)

main_path.write_text(text, encoding='utf-8')
print('Applied Vessel Full QA hardening patch')
