const { app, BrowserWindow, ipcMain, Menu, MenuItem, dialog } = require('electron/main');
const path = require('path');
const http = require("http");
const fs = require("fs");
const { exec } = require('child_process');

// Configure environment
app.commandLine.appendSwitch('charset', 'utf-8');
process.env.CACHE_PATH = path.join(__dirname, 'cache');
process.env.FFMPEG_PATH = path.join(__dirname, 'ffmpeg', 'ffmpeg.exe');

let win, sub;
let animation;

// Handle single instance with file association
const gotTheLock = app.requestSingleInstanceLock();
let cliFilePath = process.argv.find(arg => arg.endsWith('.skel') || arg.endsWith('.json'));

if (!gotTheLock) {
  if (cliFilePath) {
    // Focus existing window and quit this instance
    app.quit();
  }
} else {
  app.on('second-instance', (event, argv, cwd) => {
    // Another instance launched with file
    const newFile = argv.find(arg => arg.endsWith('.skel') || arg.endsWith('.json'));
    if (newFile && win) {
      win.webContents.send('load-spine-file', path.resolve(newFile));
      if (win.isMinimized()) win.restore();
      win.focus();
    }
  });
}

const createWindow = (log) => {
  win = new BrowserWindow({
    width: 1200,
    height: 800,
    frame: false,
    minWidth: 400,
    minHeight: 40,
    fullscreenable: false,
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      enableRemoteModule: false
    },
    icon: path.join(__dirname, 'assets', 'image', 'otogi.ico')
  });

  win.on('maximize', () => {
    win.webContents.send('set-maximized-icon');
  });

  win.on('unmaximize', () => {
    win.webContents.send('set-unmaximized-icon');
  });

  win.loadFile('./src/index.html').then(() => {
    // win.webContents.openDevTools();
    win.webContents.send('debug', log);
    
    // Load CLI file if provided
    if (cliFilePath) {
      win.webContents.send('load-spine-file', path.resolve(cliFilePath));
    }

    sub = new BrowserWindow({
      width: 450,
      height: 300,
      frame: false,
      parent: win,
      modal: true,
      show: false,
      resizable: false,
      minimizable: false,
      maximizable: false,
      fullscreenable: false,
      autoHideMenuBar: true,
      webPreferences: {
        preload: path.join(__dirname, 'preload.js')
      }
    });
    sub.loadFile('./src/pages/export.html').then(() => {
      ipcMain.on('open-export-window', (ev, animations) => {
        sub.webContents.send('receive-export-animations', animations);
        sub.show();
      });
      ipcMain.on('close-export-window', () => {
        sub.hide();
        win.webContents.send('export-window-closed');
      });
      ipcMain.on('send-export-progress', (ev, data) => {
        sub.webContents.send('set-export-progress', data);
      });
      ipcMain.on('send-export-options', (ev, options) => {
        win.webContents.send('receive-export-options', options);
      });
    });
  });
};

// Create local HTTP server
const server = http.createServer((req, res) => {
  let filePath = decodeURIComponent(req.url.slice(1));
  let fileExists;
  if (filePath.endsWith('.atlas')) {
    let txtPath = filePath + '.txt';
    filePath = (fs.existsSync(filePath) && filePath) || (fs.existsSync(txtPath) && txtPath);
    fileExists = !!filePath;
  } else {
    fileExists = fs.existsSync(filePath);
  }
  if (!fileExists) {
    res.writeHead(404);
    res.end('File not found');
    return;
  }

  fs.readFile(filePath, (err, data) => {
    if (err) {
      res.writeHead(500);
      res.end('Error loading file');
      return;
    }
    res.writeHead(200);
    res.end(data);
  });
});

server.listen(0, 'localhost', () => {});

app.whenReady().then(() => {
  let log = {};
  if (!fs.existsSync(process.env.CACHE_PATH)) {
    fs.mkdirSync(process.env.CACHE_PATH, { recursive: true });
  }
  if (!fs.existsSync(process.env.FFMPEG_PATH)) {
    log.error = 'ffmpeg not found!';
  }

  createWindow(log);

  ipcMain.handle('port', () => server.address().port);
  ipcMain.on('minimize', () => win.minimize());
  ipcMain.on('toggle-maximize', () => win.isMaximized() ? win.unmaximize() : win.maximize());
  ipcMain.on('close', () => win.close());
  ipcMain.on('show-context-menu', (ev) => {
    const contextMenu = new Menu();
    contextMenu.append(new MenuItem({
      label: 'Copy image',
      click: () => {
        win.webContents.send('copy-image');
      }
    }));
    contextMenu.popup(win, ev.x, ev.y);
  });

  // Export GIF related
  ipcMain.handle('select-export-path', () => {
    const exportPath = dialog.showOpenDialogSync(win, {
      title: 'OutputFolder',
      properties: ['openDirectory']
    });
    return exportPath ? exportPath[0] : '';
  });
  ipcMain.handle('prepare-export', (ev, name) => {
    animation = name.replace(/[\\/:"*?<>|]/g, '_');
    fs.mkdirSync(path.join(process.env.CACHE_PATH, animation), { recursive: true });
  });
  ipcMain.handle('save-image', (ev, image) => saveBase64Image(image));
  ipcMain.handle('ffmpeg', (ev, options) => {
    const imagePath = path.join(process.env.CACHE_PATH, animation);
    const outputPath = options.output;
    let instruction;
    switch (options.format) {
      case 'APNG':
        instruction = `"${process.env.FFMPEG_PATH}" -y -r ${options.framerate} -i "${path.join(imagePath, '%05d.png')}" -vf "split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" -plays 0 "${path.join(outputPath, options.animation + '.apng')}"`;
        break;
      case 'MP4':
        instruction = `"${process.env.FFMPEG_PATH}" -y -r ${options.framerate} -i "${path.join(imagePath, '%05d.png')}" -crf 17 "${path.join(outputPath, options.animation + '.mp4')}"`;
        break;
      case 'GIF':
      default:
        instruction = `"${process.env.FFMPEG_PATH}" -y -r ${options.framerate} -i "${path.join(imagePath, '%05d.png')}" -vf "split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" "${path.join(outputPath, options.animation + '.gif')}"`;
        break;
    }
    exec(instruction, (error, stdout, stderr) => {
      win.webContents.send('debug', { stdout, stderr });
      fs.readdir(imagePath, (err, files) => {
        files.forEach(file => {
          const filePath = path.join(imagePath, file);
          fs.unlinkSync(filePath);
        });
        fs.rmdirSync(imagePath);
      });
      sub.webContents.send('export-complete');
      win.webContents.send('export-complete');
    });
  });

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// Save base64 image to local file
function saveBase64Image(image) {
  const base64Image = image.data.split(';base64,').pop();
  const imageBuffer = Buffer.from(base64Image, 'base64');

  fs.writeFileSync(path.join(process.env.CACHE_PATH, animation, `${image.index}.png`), imageBuffer);

  return true;
}