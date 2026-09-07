const {app, BrowserWindow, session, shell} = require('electron');
const path = require('node:path');

function openExternalHttps(url) {
  try {
    const parsed = new URL(url);
    if (parsed.protocol === 'https:') void shell.openExternal(parsed.href);
  } catch {}
}

function createWindow() {
  const window = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 980,
    minHeight: 640,
    backgroundColor: '#0b0d13',
    autoHideMenuBar: true,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  window.webContents.setWindowOpenHandler(({url}) => {
    openExternalHttps(url);
    return {action: 'deny'};
  });

  window.webContents.on('will-navigate', (event, url) => {
    if (url === window.webContents.getURL()) return;
    event.preventDefault();
    openExternalHttps(url);
  });

  window.loadFile(path.join(__dirname, '..', 'dist', 'index.html'));
}

app.whenReady().then(() => {
  const allowMedia = (webContents, permission) => {
    const owner = BrowserWindow.fromWebContents(webContents);
    const isLocalVesselWindow = Boolean(owner && webContents.getURL().startsWith('file://'));
    return isLocalVesselWindow && ['media', 'notifications'].includes(permission);
  };
  session.defaultSession.setPermissionRequestHandler((webContents, permission, callback) => callback(allowMedia(webContents, permission)));
  session.defaultSession.setPermissionCheckHandler((webContents, permission) => allowMedia(webContents, permission));
  createWindow();
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
