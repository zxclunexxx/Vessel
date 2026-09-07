from pathlib import Path

STYLE_PATH = Path('src/style.css')
MARKER = '/* VESSEL_UI_FOUNDATION_SHELL_V1 */'

style = STYLE_PATH.read_text(encoding='utf-8')
required_legacy = [
    '.shell{height:100vh;display:grid;',
    '.servers{background:#0d0f15;',
    '.channels{background:#191c26;',
    '.chat{min-width:0;display:flex;',
    '.chat-head{min-height:72px;',
    '.composer{margin:0 25px 22px;',
]
missing = [marker for marker in required_legacy if marker not in style]
if missing:
    raise SystemExit('UI foundation source drift: ' + ', '.join(missing))

if MARKER in style:
    print('Vessel UI foundation already applied')
    raise SystemExit(0)

foundation = r'''

/* VESSEL_UI_FOUNDATION_SHELL_V1 */
:root {
  --v-bg-0: #070910;
  --v-bg-1: #0b0f18;
  --v-bg-2: #111827;
  --v-bg-3: #171c2b;
  --v-surface: rgba(17, 23, 37, .72);
  --v-surface-strong: rgba(20, 27, 43, .88);
  --v-surface-soft: rgba(255, 255, 255, .045);
  --v-surface-hover: rgba(255, 255, 255, .075);
  --v-border: rgba(214, 230, 255, .085);
  --v-border-bright: rgba(214, 230, 255, .16);
  --v-text-1: #f5f8ff;
  --v-text-2: #c4ccdc;
  --v-text-3: #7f8ba3;
  --v-cyan: #3be7ff;
  --v-blue: #4f7cff;
  --v-violet: #8b5cff;
  --v-magenta: #d946ef;
  --v-green: #5ee7b2;
  --v-danger: #ff6f91;
  --v-radius-control: 14px;
  --v-radius-card: 18px;
  --v-radius-panel: 26px;
  --v-shadow-panel: 0 26px 80px rgba(0, 0, 0, .34), inset 0 1px 0 rgba(255, 255, 255, .035);
  --v-shadow-glow: 0 0 0 1px rgba(139, 92, 255, .08), 0 12px 36px rgba(81, 76, 255, .16);
  --v-ease-ui: cubic-bezier(.2, .8, .2, 1);
  --v-ease-spring: cubic-bezier(.16, 1, .3, 1);
  --v-fast: 140ms;
  --v-normal: 220ms;
  --v-slow: 340ms;
  color-scheme: dark;
}

html, body, #app { min-width: 0; min-height: 100%; }
body {
  min-height: 100vh;
  color: var(--v-text-1);
  background:
    radial-gradient(circle at 8% 8%, rgba(59, 231, 255, .105), transparent 27%),
    radial-gradient(circle at 88% 10%, rgba(217, 70, 239, .105), transparent 30%),
    radial-gradient(circle at 70% 88%, rgba(79, 124, 255, .11), transparent 30%),
    linear-gradient(145deg, var(--v-bg-0) 0%, #090c14 42%, #0a0d16 100%);
  overflow: hidden;
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
}
body::before,
body::after {
  content: '';
  position: fixed;
  inset: 0;
  pointer-events: none;
}
body::before {
  background:
    linear-gradient(115deg, transparent 8%, rgba(255,255,255,.018) 34%, transparent 57%),
    radial-gradient(ellipse at 50% -20%, rgba(139,92,255,.09), transparent 48%);
  z-index: 0;
}
body::after {
  z-index: 0;
  opacity: .075;
  background-image: radial-gradient(rgba(255,255,255,.8) .38px, transparent .58px);
  background-size: 4px 4px;
  mix-blend-mode: soft-light;
  mask-image: linear-gradient(to bottom, rgba(0,0,0,.82), rgba(0,0,0,.28));
}
#app { position: relative; z-index: 1; }

.shell {
  height: 100vh;
  padding: 12px;
  gap: 10px;
  grid-template-columns: 84px 268px minmax(420px, 1fr) 256px;
  background: transparent;
  isolation: isolate;
}
.servers,
.channels,
.chat,
.members {
  border: 1px solid var(--v-border);
  background: linear-gradient(180deg, rgba(20, 27, 43, .8), rgba(10, 14, 23, .74));
  box-shadow: var(--v-shadow-panel);
  backdrop-filter: blur(24px) saturate(128%);
  -webkit-backdrop-filter: blur(24px) saturate(128%);
}
.servers {
  border-radius: var(--v-radius-panel);
  padding: 16px 0;
  gap: 10px;
  background:
    linear-gradient(180deg, rgba(17, 23, 38, .91), rgba(9, 12, 20, .86)),
    radial-gradient(circle at 50% 0, rgba(59,231,255,.09), transparent 34%);
  overflow-y: auto;
  scrollbar-width: none;
}
.servers::-webkit-scrollbar { display: none; }
.server {
  position: relative;
  width: 50px;
  height: 50px;
  border: 1px solid rgba(255,255,255,.055);
  border-radius: 18px;
  background: linear-gradient(145deg, rgba(255,255,255,.065), rgba(255,255,255,.025));
  color: var(--v-text-2);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.045);
  transition: transform var(--v-normal) var(--v-ease-spring), border-radius var(--v-normal) var(--v-ease-ui), border-color var(--v-normal), background var(--v-normal), color var(--v-normal), box-shadow var(--v-normal);
}
.server::before {
  content: '';
  position: absolute;
  left: -14px;
  top: 50%;
  width: 3px;
  height: 0;
  border-radius: 99px;
  background: linear-gradient(180deg, var(--v-cyan), var(--v-violet));
  box-shadow: 0 0 14px rgba(59,231,255,.55);
  transform: translateY(-50%);
  opacity: 0;
  transition: height var(--v-normal) var(--v-ease-spring), opacity var(--v-normal);
}
.server:hover {
  transform: translateY(-2px) scale(1.045);
  border-color: rgba(139,92,255,.24);
  border-radius: 15px;
  color: #fff;
  background: linear-gradient(145deg, rgba(139,92,255,.2), rgba(59,231,255,.08));
  box-shadow: 0 12px 30px rgba(0,0,0,.28), 0 0 22px rgba(139,92,255,.11);
}
.server.selected {
  transform: none;
  border-color: rgba(96,214,255,.34);
  border-radius: 15px;
  color: #fff;
  background: linear-gradient(145deg, rgba(65,208,255,.22), rgba(139,92,255,.27) 56%, rgba(217,70,239,.14));
  box-shadow: 0 14px 34px rgba(0,0,0,.28), 0 0 28px rgba(99,105,255,.16), inset 0 1px 0 rgba(255,255,255,.12);
}
.server.selected::before { height: 26px; opacity: 1; }
.server.add {
  color: var(--v-green);
  background: linear-gradient(145deg, rgba(94,231,178,.105), rgba(59,231,255,.045));
  border-color: rgba(94,231,178,.13);
}
.server.add:hover { color: #d9fff1; border-color: rgba(94,231,178,.32); }
.home-tab { font-size: 18px; }

.channels {
  border-radius: var(--v-radius-panel);
  display: flex;
  flex-direction: column;
  overflow-x: hidden;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: rgba(139,92,255,.25) transparent;
}
.channels::-webkit-scrollbar,
.messages::-webkit-scrollbar,
.members::-webkit-scrollbar { width: 7px; }
.channels::-webkit-scrollbar-thumb,
.messages::-webkit-scrollbar-thumb,
.members::-webkit-scrollbar-thumb { background: rgba(139,92,255,.22); border-radius: 99px; }
.brand {
  flex: none;
  position: sticky;
  top: 0;
  z-index: 4;
  height: 78px;
  padding: 0 18px;
  border-bottom: 1px solid var(--v-border);
  background: linear-gradient(180deg, rgba(18,24,39,.96), rgba(18,24,39,.76));
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  letter-spacing: -.02em;
}
.brand-mark {
  font-size: 28px;
  background: linear-gradient(135deg, var(--v-cyan), #8da2ff 46%, var(--v-magenta));
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  filter: drop-shadow(0 0 12px rgba(92,183,255,.2));
}
.more,
.icon-btn,
.section-title button,
.member-manage {
  transition: color var(--v-fast), background var(--v-fast), border-color var(--v-fast), transform var(--v-fast) var(--v-ease-ui);
}
.more:hover,
.icon-btn:hover,
.section-title button:hover { color: var(--v-text-1); transform: translateY(-1px); }
.user-card {
  order: 20;
  flex: none;
  margin: auto 12px 8px;
  padding: 11px;
  border: 1px solid rgba(255,255,255,.085);
  border-radius: var(--v-radius-card);
  background: linear-gradient(145deg, rgba(255,255,255,.065), rgba(255,255,255,.025));
  box-shadow: 0 14px 36px rgba(0,0,0,.19), inset 0 1px 0 rgba(255,255,255,.04);
}
.user-card .avatar { box-shadow: 0 8px 22px rgba(92,85,255,.22); }
.user-card small { color: var(--v-green); }
.user-card .icon-btn {
  width: 34px;
  height: 34px;
  border-radius: 11px;
  display: grid;
  place-items: center;
}
.user-card .icon-btn:hover { background: var(--v-surface-hover); }
.channel-section { order: 10; padding: 11px 10px 2px; }
.section-title,
.members-title {
  padding: 8px 9px;
  color: var(--v-text-3);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: .115em;
}
.section-title button { color: var(--v-text-3); border-radius: 9px; }
.channel {
  position: relative;
  min-height: 40px;
  margin: 2px 0;
  padding: 9px 11px 9px 14px;
  border: 1px solid transparent;
  border-radius: 12px;
  color: #99a6bc;
  overflow: hidden;
  transition: color var(--v-fast), background var(--v-normal), border-color var(--v-normal), transform var(--v-fast) var(--v-ease-ui), box-shadow var(--v-normal);
}
.channel::before {
  content: '';
  position: absolute;
  left: 4px;
  top: 50%;
  width: 2px;
  height: 0;
  border-radius: 99px;
  transform: translateY(-50%);
  background: linear-gradient(180deg, var(--v-cyan), var(--v-violet));
  box-shadow: 0 0 10px rgba(59,231,255,.42);
  opacity: 0;
  transition: height var(--v-normal) var(--v-ease-spring), opacity var(--v-normal);
}
.channel:hover {
  color: var(--v-text-1);
  background: rgba(255,255,255,.045);
  transform: translateX(2px);
}
.channel.active {
  color: #fff;
  border-color: rgba(130,151,255,.13);
  background: linear-gradient(90deg, rgba(59,231,255,.085), rgba(139,92,255,.15) 55%, rgba(217,70,239,.055));
  box-shadow: inset 0 1px 0 rgba(255,255,255,.04), 0 9px 22px rgba(0,0,0,.12);
}
.channel.active::before { height: 22px; opacity: 1; }
.channel span { color: #6f7d96; transition: color var(--v-fast); }
.channel.active span { color: #9edfff; }
.channel.dm .mini-avatar { box-shadow: 0 6px 14px rgba(0,0,0,.2); }
.channel.dm em.dm-unread {
  background: linear-gradient(135deg, var(--v-violet), var(--v-magenta));
  box-shadow: 0 0 14px rgba(191,72,238,.25);
}
.side-footer {
  order: 30;
  position: static;
  width: auto;
  padding: 4px 18px 12px;
  color: #566278;
}
.side-footer span { color: var(--v-green); text-shadow: 0 0 9px rgba(94,231,178,.45); }

.chat {
  border-radius: 28px;
  overflow: hidden;
  background:
    linear-gradient(180deg, rgba(14,19,31,.79), rgba(10,14,23,.86)),
    radial-gradient(circle at 72% 0, rgba(79,124,255,.07), transparent 38%);
}
.chat-head {
  min-height: 78px;
  padding: 0 24px;
  border-bottom: 1px solid var(--v-border);
  background: linear-gradient(180deg, rgba(20,27,43,.78), rgba(14,19,31,.58));
  backdrop-filter: blur(22px) saturate(130%);
  -webkit-backdrop-filter: blur(22px) saturate(130%);
}
.chat-head h1 { font-size: 16px; font-weight: 750; letter-spacing: -.015em; }
.chat-head h1 span { color: #8fcfff; text-shadow: 0 0 14px rgba(59,231,255,.18); }
.chat-head p { color: var(--v-text-3); }
.head-actions { gap: 7px; }
.head-actions button {
  display: inline-grid;
  place-items: center;
  min-width: 36px;
  min-height: 36px;
  border: 1px solid transparent;
  border-radius: 12px;
  color: #8e9ab0;
  background: rgba(255,255,255,.025);
  transition: transform var(--v-fast) var(--v-ease-ui), color var(--v-fast), background var(--v-fast), border-color var(--v-fast), box-shadow var(--v-normal);
}
.head-actions button:hover {
  transform: translateY(-1px);
  color: #fff;
  border-color: rgba(255,255,255,.08);
  background: rgba(255,255,255,.07);
  box-shadow: 0 9px 20px rgba(0,0,0,.16);
}
.head-actions sup {
  background: linear-gradient(135deg, #ff668b, #d946ef);
  box-shadow: 0 0 12px rgba(217,70,239,.22);
}
.join-voice {
  border: 1px solid rgba(94,231,178,.15)!important;
  background: rgba(94,231,178,.105)!important;
  color: #8df3cc!important;
  border-radius: 11px!important;
}
.join-voice.connected { border-color: rgba(139,92,255,.2)!important; background: rgba(139,92,255,.16)!important; }
.messages {
  padding: 28px 30px;
  scrollbar-width: thin;
  scrollbar-color: rgba(139,92,255,.22) transparent;
}
.welcome {
  margin-bottom: 8px;
  padding: 26px 2px 28px;
  border-bottom: 1px solid var(--v-border);
}
.welcome-icon {
  width: 58px;
  height: 58px;
  border: 1px solid rgba(126,170,255,.16);
  border-radius: 20px;
  color: #b3d9ff;
  background: linear-gradient(145deg, rgba(59,231,255,.105), rgba(139,92,255,.15), rgba(217,70,239,.055));
  box-shadow: 0 16px 38px rgba(0,0,0,.2), inset 0 1px 0 rgba(255,255,255,.07);
}
.welcome h2 { color: var(--v-text-1); letter-spacing: -.025em; }
.welcome p { color: var(--v-text-3); }
.message { border-radius: 14px; transition: background var(--v-fast), transform var(--v-fast) var(--v-ease-ui); }
.message:hover { background: rgba(255,255,255,.023); transform: translateX(1px); }
.message .avatar { box-shadow: 0 7px 18px rgba(0,0,0,.2); }
.message-meta b { color: #f3f6ff; }
.message-meta time { color: #66738a; }
.message p { color: #cbd3e1; }
.composer {
  margin: 0 24px 22px;
  min-height: 52px;
  padding: 9px 11px;
  border: 1px solid rgba(214,230,255,.09);
  border-radius: 17px;
  background: linear-gradient(145deg, rgba(255,255,255,.07), rgba(255,255,255,.033));
  box-shadow: 0 16px 34px rgba(0,0,0,.18), inset 0 1px 0 rgba(255,255,255,.045);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
  transition: border-color var(--v-normal), box-shadow var(--v-normal), background var(--v-normal), transform var(--v-fast) var(--v-ease-ui);
}
.composer:focus-within {
  border-color: rgba(99,190,255,.32);
  background: linear-gradient(145deg, rgba(65,111,174,.12), rgba(139,92,255,.07));
  box-shadow: 0 0 0 3px rgba(59,231,255,.055), 0 18px 42px rgba(0,0,0,.22), 0 0 34px rgba(106,92,255,.09);
}
.composer input { color: var(--v-text-1); }
.composer input::placeholder { color: #68758c; }
.composer button {
  width: 34px;
  height: 34px;
  border-radius: 11px;
  transition: color var(--v-fast), background var(--v-fast), transform var(--v-fast) var(--v-ease-ui);
}
.composer button:hover { color: #fff; background: rgba(255,255,255,.07); transform: translateY(-1px); }
.composer .send {
  color: #d9faff!important;
  background: linear-gradient(135deg, rgba(59,231,255,.19), rgba(139,92,255,.29))!important;
  box-shadow: 0 8px 20px rgba(86,91,255,.15);
}

.members {
  border-radius: var(--v-radius-panel);
  border-left: 1px solid var(--v-border);
  padding: 22px 14px;
  background: linear-gradient(180deg, rgba(18,24,39,.78), rgba(10,14,23,.76));
  scrollbar-width: thin;
  scrollbar-color: rgba(139,92,255,.22) transparent;
}
.member {
  margin: 2px 0;
  padding: 10px 8px;
  border: 1px solid transparent;
  border-radius: 13px;
  transition: background var(--v-fast), border-color var(--v-fast), transform var(--v-fast) var(--v-ease-ui);
}
.member:hover { transform: translateX(2px); border-color: rgba(255,255,255,.055); background: rgba(255,255,255,.045); }
.member i { background: var(--v-green); box-shadow: 0 0 10px rgba(94,231,178,.45); }
.member small { color: #77849b; }
.voice-status {
  border: 1px solid rgba(94,231,178,.12);
  background: linear-gradient(135deg, rgba(94,231,178,.09), rgba(59,231,255,.05));
  color: #8decc8;
  box-shadow: inset 0 1px 0 rgba(255,255,255,.035);
}

.auth-page {
  background:
    radial-gradient(circle at 18% 12%, rgba(59,231,255,.13), transparent 26%),
    radial-gradient(circle at 82% 18%, rgba(217,70,239,.13), transparent 30%),
    radial-gradient(circle at 58% 90%, rgba(79,124,255,.12), transparent 34%),
    linear-gradient(145deg, #060810, #0b0f18 52%, #090b13);
}
.auth-glow {
  width: 620px;
  height: 620px;
  top: -300px;
  background: radial-gradient(circle, rgba(119,94,255,.22), rgba(59,231,255,.055) 45%, transparent 70%);
  filter: blur(62px);
}
.auth-card,
.modal-card,
.dialog-list-item,
.vessel-toast {
  border-color: var(--v-border-bright);
  background: linear-gradient(145deg, rgba(25,32,50,.92), rgba(13,18,29,.88));
  box-shadow: var(--v-shadow-panel);
  backdrop-filter: blur(24px) saturate(125%);
  -webkit-backdrop-filter: blur(24px) saturate(125%);
}
.auth-card { border-radius: 28px; }
.auth-logo,
.call-avatar {
  background: linear-gradient(135deg, rgba(59,231,255,.88), rgba(139,92,255,.95) 55%, rgba(217,70,239,.9));
  box-shadow: 0 14px 38px rgba(103,84,255,.28), 0 0 34px rgba(59,231,255,.1);
}
.auth-card h1 { color: var(--v-text-1); }
.auth-card h1 span {
  background: linear-gradient(90deg, #93ecff, #a994ff 52%, #ed8dff);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.auth-form input,
.dialog-input,
.modal-card input,
.modal-card select {
  border-color: rgba(214,230,255,.1);
  background: rgba(255,255,255,.045);
  border-radius: 13px;
  transition: border-color var(--v-fast), box-shadow var(--v-fast), background var(--v-fast);
}
.auth-form input:focus,
.dialog-input:focus,
.modal-card input:focus,
.modal-card select:focus {
  border-color: rgba(94,194,255,.38);
  background: rgba(69,93,142,.1);
  box-shadow: 0 0 0 3px rgba(59,231,255,.055), 0 0 24px rgba(139,92,255,.075);
  outline: none;
}
.primary {
  border: 1px solid rgba(255,255,255,.08);
  border-radius: 13px;
  background: linear-gradient(105deg, #387fe8 0%, #7967f5 52%, #bf55dc 100%);
  box-shadow: 0 10px 28px rgba(87,82,246,.22), inset 0 1px 0 rgba(255,255,255,.13);
  transition: transform var(--v-fast) var(--v-ease-ui), filter var(--v-fast), box-shadow var(--v-fast);
}
.primary:hover { transform: translateY(-1px); filter: brightness(1.07); box-shadow: 0 14px 32px rgba(87,82,246,.27); }
.auth-switch {
  width: 100%;
  margin-top: 14px;
  border: 1px solid rgba(214,230,255,.09);
  border-radius: 13px;
  padding: 12px;
  color: var(--v-text-2);
  background: rgba(255,255,255,.035);
  cursor: pointer;
  transition: color var(--v-fast), background var(--v-fast), border-color var(--v-fast);
}
.auth-switch:hover { color: #fff; border-color: rgba(139,92,255,.2); background: rgba(139,92,255,.075); }
.modal { background: rgba(2,4,10,.7); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); }
.modal-card { border-radius: 22px; }
.vessel-toast {
  border-radius: 15px;
  color: var(--v-text-1);
  box-shadow: 0 18px 48px rgba(0,0,0,.35), 0 0 24px rgba(99,91,255,.08);
}
.vessel-toast.success { border-color: rgba(94,231,178,.25); color: #9ff2d3; }
.vessel-toast.error { border-color: rgba(255,111,145,.28); color: #ff9bb3; }

button:focus-visible,
input:focus-visible,
select:focus-visible,
[tabindex]:focus-visible {
  outline: 2px solid rgba(89,220,255,.72);
  outline-offset: 2px;
}
button:active:not(:disabled) { transform: translateY(0) scale(.975); }
button:disabled { cursor: not-allowed; opacity: .55; }

@media (max-width: 1100px) {
  .shell { padding: 9px; gap: 8px; grid-template-columns: 74px 244px minmax(360px, 1fr); }
  .servers, .channels, .chat { border-radius: 23px; }
}
@media (max-width: 760px) {
  .shell { padding: 7px; gap: 7px; grid-template-columns: 64px 220px minmax(0, 1fr); }
  .servers, .channels, .chat { border-radius: 21px; }
  .server { width: 46px; height: 46px; }
  .chat-head { min-height: 68px; padding: 9px 14px; }
  .messages { padding: 18px; }
  .composer { margin: 0 14px 14px; }
}
@media (max-width: 600px) {
  body { overflow: hidden; }
  .shell { padding: 6px; gap: 6px; grid-template-columns: 56px minmax(0, 1fr); }
  .servers { padding-top: 10px; border-radius: 19px; }
  .server { width: 43px; height: 43px; border-radius: 15px; }
  .server::before { left: -8px; }
  .channels {
    display: block!important;
    position: fixed;
    left: 62px;
    top: 6px;
    bottom: 6px;
    width: min(300px, calc(100vw - 68px));
    z-index: 30;
    border-radius: 22px;
    transform: translateX(-115%);
    transition: transform var(--normal, 220ms) var(--v-ease-spring);
    box-shadow: 22px 0 70px rgba(0,0,0,.54), var(--v-shadow-panel);
  }
  .channels.mobile-open { transform: translateX(0); }
  .brand { height: 68px; }
  .user-card { margin-top: 14px; }
  .chat { border-radius: 21px; }
  .messages { padding: 14px; }
  .composer { margin: 0 10px 10px; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    scroll-behavior: auto!important;
    animation-duration: .01ms!important;
    animation-iteration-count: 1!important;
    transition-duration: .01ms!important;
  }
}
'''

STYLE_PATH.write_text(style.rstrip() + foundation + '\n', encoding='utf-8')
print('Applied Vessel liquid-glass UI foundation and shell')
