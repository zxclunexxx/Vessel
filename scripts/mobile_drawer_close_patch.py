from pathlib import Path

# Mobile channel drawer must always have an explicit in-panel close control.
main_path = Path('src/main.js')
style_path = Path('src/style.css')
main = main_path.read_text(encoding='utf-8')
style = style_path.read_text(encoding='utf-8')
changed = False


def replace_once(source, old, new, label, marker=None):
    global changed
    if marker and marker in source:
        print(f'{label}: already applied')
        return source
    if new in source:
        print(f'{label}: already applied')
        return source
    if old not in source:
        raise SystemExit(f'{label}: expected source not found')
    changed = True
    print(f'{label}: applied')
    return source.replace(old, new, 1)


old_brand = """<div class=\"brand\"><span class=\"brand-mark\">◈</span><span>${friendsOpen?'Друзья':escapeHtml(activeServer?.name || 'Vessel')}</span><button class=\"more ${friendsOpen?'hidden':''}\">•••</button></div>"""
new_brand = """<div class=\"brand\"><span class=\"brand-mark\">◈</span><span>${friendsOpen?'Друзья':escapeHtml(activeServer?.name || 'Vessel')}</span><button class=\"more ${friendsOpen?'hidden':''}\">•••</button><button class=\"mobile-drawer-close\" id=\"mobile-nav-close\" type=\"button\" title=\"Закрыть каналы\" aria-label=\"Закрыть каналы\">×</button></div>"""
main = replace_once(main, old_brand, new_brand, 'mobile drawer close control', marker='id=\"mobile-nav-close\"')

old_handler = """  document.querySelector('#mobile-nav')?.addEventListener('click',()=>document.querySelector('.channels')?.classList.toggle('mobile-open'));"""
new_handler = """  const setMobileDrawerOpen=open=>document.querySelector('.channels')?.classList.toggle('mobile-open',Boolean(open));
  document.querySelector('#mobile-nav')?.addEventListener('click',()=>setMobileDrawerOpen(!document.querySelector('.channels')?.classList.contains('mobile-open')));
  document.querySelector('#mobile-nav-close')?.addEventListener('click',()=>setMobileDrawerOpen(false));"""
main = replace_once(main, old_handler, new_handler, 'mobile drawer open/close handler', marker='const setMobileDrawerOpen=open=>')

style_marker = '.mobile-drawer-close{'
if style_marker not in style:
    style += "\n.mobile-drawer-close{display:none;border:0;background:none;color:#9ca4b8;font-size:26px;line-height:1;cursor:pointer;padding:4px 7px;border-radius:8px}.mobile-drawer-close:hover{background:#292e3e;color:#fff}@media(max-width:600px){.mobile-drawer-close{display:grid;place-items:center}.channels .brand{padding-right:10px}}\n"
    changed = True
    print('mobile drawer close styling: applied')
else:
    print('mobile drawer close styling: already applied')

if changed:
    main_path.write_text(main, encoding='utf-8')
    style_path.write_text(style, encoding='utf-8')
    print('Mobile drawer close patch applied')
else:
    print('Mobile drawer close patch already applied; nothing to change')
