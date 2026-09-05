const {app, BrowserWindow, session} = require('electron');
const path = require('node:path');

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

  window.loadFile(path.join(__dirname, '..', 'dist', 'index.html'));
}

app.whenReady().then(() => {
  const allowMedia = (_webContents, permission) => ['media', 'notifications'].includes(permission);
  session.defaultSession.setPermissionRequestHandler((_webContents, permission, callback) => callback(allowMedia(_webContents, permission)));
  session.defaultSession.setPermissionCheckHandler((_webContents, permission) => allowMedia(_webContents, permission));
  createWindow();
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
