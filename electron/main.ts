import { app, BrowserWindow, shell, ipcMain, Tray, Menu, nativeImage, dialog } from 'electron'
import { join, dirname } from 'path'
import { spawn, ChildProcess, execSync } from 'child_process'
import { electronApp, optimizer, is } from '@electron-toolkit/utils'
import { existsSync, readFileSync, writeFileSync, mkdirSync } from 'fs'
import { fileURLToPath } from 'url'

// 禁用 GPU 缓存以避免权限错误
app.commandLine.appendSwitch('disable-gpu-shader-disk-cache')
app.commandLine.appendSwitch('disable-gpu-disk-cache')
app.commandLine.appendSwitch('disable-gpu-process-crash-limit')
app.commandLine.appendSwitch('disable-features', 'AutofillServerCommunication')
// 禁用磁盘缓存以避免权限问题
app.commandLine.appendSwitch('disable-cache')
app.commandLine.appendSwitch('disable-application-cache')

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

interface AppSettings {
  closeToTray: boolean
  firstCloseShown: boolean
}

const DEFAULT_SETTINGS: AppSettings = {
  closeToTray: true,
  firstCloseShown: false,
}

function getSettingsFilePath(): string {
  return join(app.getPath('userData'), 'app-settings.json')
}

function loadSettings(): AppSettings {
  try {
    const settingsPath = getSettingsFilePath()
    if (existsSync(settingsPath)) {
      const data = readFileSync(settingsPath, 'utf-8')
      const settings = JSON.parse(data) as Partial<AppSettings>
      return { ...DEFAULT_SETTINGS, ...settings }
    }
  } catch (error) {
    console.error('[Settings] Failed to load settings:', error)
  }
  return { ...DEFAULT_SETTINGS }
}

function saveSettings(settings: AppSettings): void {
  try {
    const settingsPath = getSettingsFilePath()
    const settingsDir = dirname(settingsPath)
    if (!existsSync(settingsDir)) {
      mkdirSync(settingsDir, { recursive: true })
    }
    writeFileSync(settingsPath, JSON.stringify(settings, null, 2), 'utf-8')
    console.log('[Settings] Settings saved:', settings)
  } catch (error) {
    console.error('[Settings] Failed to save settings:', error)
  }
}

function getProjectRoot(): string {
  let currentDir = __dirname
  while (currentDir) {
    const packageJsonPath = join(currentDir, 'package.json')
    if (existsSync(packageJsonPath)) {
      return currentDir
    }
    const parentDir = dirname(currentDir)
    if (parentDir === currentDir) break
    currentDir = parentDir
  }
  return join(__dirname, '..')
}

const PYTHON_API_HOST = '127.0.0.1'
const PYTHON_API_PORT = 8000
const PYTHON_API_URL = `http://${PYTHON_API_HOST}:${PYTHON_API_PORT}`

let mainWindow: BrowserWindow | null = null
let tray: Tray | null = null
let pythonProcess: ChildProcess | null = null
let isQuitting = false
let pythonReady = false
let appSettings: AppSettings = { ...DEFAULT_SETTINGS }

function findPythonApiExe(): string | null {
  const projectRoot = getProjectRoot()
  
  const possiblePaths = [
    join(projectRoot, 'resources', 'onetotwo-api.exe'),
    join(projectRoot, 'dist', 'onetotwo-api.exe'),
    join(projectRoot, 'onetotwo-api.exe'),
  ]

  if (!is.dev) {
    const exeDir = dirname(app.getPath('exe'))
    possiblePaths.unshift(
      join(exeDir, 'resources', 'onetotwo-api.exe'),
      join(exeDir, 'onetotwo-api.exe')
    )
    
    const resourcesPath = process.resourcesPath
    if (resourcesPath) {
      possiblePaths.unshift(join(resourcesPath, 'onetotwo-api.exe'))
    }
  }

  for (const path of possiblePaths) {
    console.log(`[Python] Checking path: ${path}`)
    if (existsSync(path)) {
      console.log(`[Python] Found Python API executable at: ${path}`)
      return path
    }
  }

  console.log('[Python] No Python API executable found')
  return null
}

function findPythonExecutable(): string | null {
  const projectRoot = getProjectRoot()

  const venvPythonPaths = [
    join(projectRoot, 'venv', 'Scripts', 'python.exe'),
    join(projectRoot, '.venv', 'Scripts', 'python.exe'),
  ]

  for (const path of venvPythonPaths) {
    if (existsSync(path)) {
      console.log(`[Python] Found venv Python at: ${path}`)
      return path
    }
  }
  
  const pythonCommands = process.platform === 'win32' 
    ? ['python.exe', 'python3.exe', 'py.exe']
    : ['python', 'python3']

  for (const cmd of pythonCommands) {
    try {
      const fullPath = execSync(`where ${cmd}`, { encoding: 'utf-8', timeout: 5000 }).trim().split('\n')[0]
      if (fullPath && existsSync(fullPath)) {
        console.log(`[Python] Found working Python: ${fullPath}`)
        return fullPath
      }
    } catch {
      continue
    }
  }

  if (process.platform === 'win32') {
    const commonPaths = [
      'C:\\Python312\\python.exe',
      'C:\\Python311\\python.exe',
      'C:\\Python310\\python.exe',
      'C:\\Python39\\python.exe',
      process.env.LOCALAPPDATA ? `${process.env.LOCALAPPDATA}\\Programs\\Python\\Python312\\python.exe` : null,
      process.env.LOCALAPPDATA ? `${process.env.LOCALAPPDATA}\\Programs\\Python\\Python311\\python.exe` : null,
    ].filter(Boolean) as string[]

    for (const path of commonPaths) {
      if (existsSync(path)) {
        console.log(`[Python] Found Python at common path: ${path}`)
        return path
      }
    }
  }

  console.log('[Python] No Python installation found')
  return null
}

function getPythonApiPath(): string {
  const projectRoot = getProjectRoot()
  
  if (is.dev) {
    const devApiPath = join(projectRoot, 'python-api', 'main.py')
    if (existsSync(devApiPath)) {
      console.log(`[Python] Found API at: ${devApiPath}`)
      return devApiPath
    }
    return devApiPath
  }

  const possiblePaths = [
    join(projectRoot, 'resources', 'python-api', 'main.py'),
    join(projectRoot, 'python-api', 'main.py'),
  ]

  for (const path of possiblePaths) {
    if (existsSync(path)) {
      console.log(`[Python] Found API at: ${path}`)
      return path
    }
  }

  console.log('[Python] Using default API path')
  return join(projectRoot, 'resources', 'python-api', 'main.py')
}

async function checkPortInUse(port: number): Promise<boolean> {
  try {
    const response = await fetch(`http://127.0.0.1:${port}/health`, {
      method: 'GET',
      signal: AbortSignal.timeout(2000),
    })
    return response.ok
  } catch {
    return false
  }
}

async function startPythonProcess(): Promise<void> {
  const alreadyRunning = await checkPortInUse(PYTHON_API_PORT)
  if (alreadyRunning) {
    console.log('[Python] Python API is already running on port', PYTHON_API_PORT)
    pythonReady = true
    return
  }

  return new Promise((resolve, reject) => {
    const projectRoot = getProjectRoot()
    
    if (!is.dev) {
      const apiExePath = findPythonApiExe()
      
      if (apiExePath) {
        console.log(`[Python] Starting Python API executable...`)
        console.log(`[Python] API executable: ${apiExePath}`)
        
        const exeDir = dirname(apiExePath)
        const workDir = process.resourcesPath || exeDir
        console.log(`[Python] Working directory: ${workDir}`)
        
        pythonProcess = spawn(apiExePath, [], {
          cwd: workDir,
          env: {
            ...process.env,
            ONETOTWO_API_HOST: PYTHON_API_HOST,
            ONETOTWO_API_PORT: String(PYTHON_API_PORT),
          },
          windowsHide: true,
          shell: true,
          detached: false,
        })

        pythonProcess.stdout?.on('data', (data) => {
          const output = data.toString()
          console.log(`[Python stdout] ${output}`)

          if (output.includes('Uvicorn running') || output.includes('Application startup complete') || output.includes('Starting server')) {
            pythonReady = true
            resolve()
          }
        })

        pythonProcess.stderr?.on('data', (data) => {
          const output = data.toString()
          console.error(`[Python stderr] ${output}`)

          if (output.includes('Uvicorn running') || output.includes('Application startup complete') || output.includes('Starting server')) {
            pythonReady = true
            resolve()
          }
          
          if (output.includes('error while attempting to bind') || output.includes('Address already in use') || output.includes('10048')) {
            if (!pythonReady) {
              reject(new Error(`Port ${PYTHON_API_PORT} is already in use.`))
            }
          }
        })

        pythonProcess.on('error', (error) => {
          console.error(`[Python] Process error: ${error.message}`)
          if (!pythonReady) {
            reject(new Error(`Failed to start Python process: ${error.message}`))
          }
        })

        pythonProcess.on('close', (code, signal) => {
          console.log(`[Python] Process closed with code ${code}, signal ${signal}`)
          pythonProcess = null
          pythonReady = false

          if (!isQuitting && code !== 0 && code !== null) {
            console.log('[Python] Process exited unexpectedly, attempting restart...')
            setTimeout(() => {
              startPythonProcess().catch(console.error)
            }, 3000)
          }
        })

        const timeout = setTimeout(() => {
          if (!pythonReady) {
            console.log('[Python] Timeout waiting for startup, assuming ready...')
            pythonReady = true
            resolve()
          }
        }, 15000)

        const checkInterval = setInterval(async () => {
          try {
            const response = await fetch(`${PYTHON_API_URL}/health`)
            if (response.ok) {
              clearTimeout(timeout)
              clearInterval(checkInterval)
              pythonReady = true
              console.log('[Python] API server is ready')
              resolve()
            }
          } catch {
            // Server not ready yet
          }
        }, 500)
        
        return
      }
    }

    const pythonPath = findPythonExecutable()
    const apiPath = getPythonApiPath()

    console.log(`[Python] Starting Python API server (dev mode)...`)
    console.log(`[Python] Python path: ${pythonPath}`)
    console.log(`[Python] API path: ${apiPath}`)
    console.log(`[Python] Project root: ${projectRoot}`)

    if (!pythonPath) {
      reject(new Error('Python not found. Please install Python 3.8+ and ensure it is in your PATH.'))
      return
    }

    if (!existsSync(apiPath)) {
      reject(new Error(`Python API file not found at: ${apiPath}`))
      return
    }

    const args = ['-m', 'uvicorn', 'main:app', '--host', PYTHON_API_HOST, '--port', String(PYTHON_API_PORT)]
    
    const v2Dir = join(projectRoot, 'one_to_two_V2')
    const apiDirForCwd = join(projectRoot, 'python-api')

    pythonProcess = spawn(pythonPath, args, {
      cwd: apiDirForCwd,
      env: {
        ...process.env,
        PYTHONUNBUFFERED: '1',
        PYTHONPATH: v2Dir,
      },
      windowsHide: true,
    })

    pythonProcess.stdout?.on('data', (data) => {
      const output = data.toString()
      console.log(`[Python stdout] ${output}`)

      if (output.includes('Uvicorn running') || output.includes('Application startup complete')) {
        pythonReady = true
        resolve()
      }
    })

    pythonProcess.stderr?.on('data', (data) => {
      const output = data.toString()
      console.error(`[Python stderr] ${output}`)

      if (output.includes('Uvicorn running') || output.includes('Application startup complete')) {
        pythonReady = true
        resolve()
      }
      
      if (output.includes('error while attempting to bind') || output.includes('Address already in use') || output.includes('10048')) {
        if (!pythonReady) {
          reject(new Error(`Port ${PYTHON_API_PORT} is already in use. Please close other applications using this port or wait a moment and try again.`))
        }
      }
    })

    pythonProcess.on('error', (error) => {
      console.error(`[Python] Process error: ${error.message}`)
      if (!pythonReady) {
        reject(new Error(`Failed to start Python process: ${error.message}`))
      }
    })

    pythonProcess.on('close', (code, signal) => {
      console.log(`[Python] Process closed with code ${code}, signal ${signal}`)
      pythonProcess = null
      pythonReady = false

      if (!isQuitting && code !== 0 && code !== null) {
        console.log('[Python] Process exited unexpectedly, attempting restart...')
        setTimeout(() => {
          startPythonProcess().catch(console.error)
        }, 3000)
      }
    })

    const timeout = setTimeout(() => {
      if (!pythonReady) {
        console.log('[Python] Timeout waiting for startup, assuming ready...')
        pythonReady = true
        resolve()
      }
    }, 15000)

    const checkInterval = setInterval(async () => {
      try {
        const response = await fetch(`${PYTHON_API_URL}/health`)
        if (response.ok) {
          clearTimeout(timeout)
          clearInterval(checkInterval)
          pythonReady = true
          console.log('[Python] API server is ready')
          resolve()
        }
      } catch {
        // Server not ready yet
      }
    }, 500)
  })
}

async function stopPythonProcess(): Promise<void> {
  return new Promise((resolve) => {
    if (!pythonProcess) {
      resolve()
      return
    }

    console.log('[Python] Stopping Python API server...')
    isQuitting = true

    const forceKillTimeout = setTimeout(() => {
      if (pythonProcess) {
        console.log('[Python] Force killing process...')
        pythonProcess.kill('SIGKILL')
      }
    }, 5000)

    pythonProcess.on('close', () => {
      clearTimeout(forceKillTimeout)
      pythonProcess = null
      pythonReady = false
      console.log('[Python] Process stopped')
      resolve()
    })

    pythonProcess.kill('SIGTERM')
  })
}

async function checkPythonHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${PYTHON_API_URL}/health`, {
      method: 'GET',
      signal: AbortSignal.timeout(5000),
    })
    return response.ok
  } catch {
    return false
  }
}

async function apiRequest<T>(
  endpoint: string,
  method: string = 'GET',
  body?: unknown
): Promise<{ success: boolean; data?: T; error?: string }> {
  try {
    const options: RequestInit = {
      method,
      headers: {
        'Content-Type': 'application/json',
      },
    }

    if (body) {
      options.body = JSON.stringify(body)
    }

    const response = await fetch(`${PYTHON_API_URL}${endpoint}`, options)

    if (!response.ok) {
      const errorData = (await response.json().catch(() => ({ detail: 'Unknown error' }))) as {
        detail?: string
        error?: string
      }
      return {
        success: false,
        error: errorData.detail || errorData.error || `HTTP ${response.status}`,
      }
    }

    const data = (await response.json()) as T
    return { success: true, data }
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Network error',
    }
  }
}

function createTray(): void {
  const iconPath = join(__dirname, '../build/icon.png')
  let icon: Electron.NativeImage

  if (existsSync(iconPath)) {
    icon = nativeImage.createFromPath(iconPath)
  } else {
    icon = nativeImage.createEmpty()
  }

  if (process.platform === 'win32' && !icon.isEmpty()) {
    icon = icon.resize({ width: 16, height: 16 })
  }

  tray = new Tray(icon)

  const contextMenu = Menu.buildFromTemplate([
    {
      label: '显示窗口',
      click: () => {
        if (mainWindow) {
          if (mainWindow.isMinimized()) {
            mainWindow.restore()
          }
          mainWindow.show()
          mainWindow.focus()
        }
      },
    },
    {
      label: '检查 Python 状态',
      click: async () => {
        const healthy = await checkPythonHealth()
        dialog.showMessageBox(mainWindow!, {
          type: 'info',
          title: 'Python API 状态',
          message: healthy ? 'Python API 运行正常' : 'Python API 未响应',
          buttons: ['确定'],
        })
      },
    },
    { type: 'separator' },
    {
      label: '最小化到托盘',
      type: 'checkbox',
      checked: appSettings.closeToTray,
      click: (menuItem) => {
        appSettings.closeToTray = menuItem.checked
        saveSettings(appSettings)
      },
    },
    { type: 'separator' },
    {
      label: '完全退出',
      click: async () => {
        isQuitting = true
        await stopPythonProcess()
        app.quit()
      },
    },
  ])

  tray.setToolTip('OneToTwo V3')
  tray.setContextMenu(contextMenu)

  tray.on('double-click', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) {
        mainWindow.restore()
      }
      mainWindow.show()
      mainWindow.focus()
    }
  })
}

function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1000,
    minHeight: 700,
    show: false,
    autoHideMenuBar: true,
    titleBarStyle: 'hiddenInset',
    trafficLightPosition: { x: 15, y: 10 },
    webPreferences: {
      preload: join(__dirname, '../preload/index.cjs'),
      sandbox: false,
      contextIsolation: true,
      nodeIntegration: false,
      // 使用内存分区避免缓存冲突
      partition: 'persist:main',
    },
  })

  mainWindow.on('ready-to-show', () => {
    mainWindow?.show()
    if (is.dev) {
      mainWindow?.webContents.openDevTools()
    }
  })

  mainWindow.on('close', async (event) => {
    if (isQuitting) {
      return
    }

    event.preventDefault()

    if (!appSettings.firstCloseShown) {
      const result = await dialog.showMessageBox(mainWindow!, {
        type: 'question',
        title: '选择关闭行为',
        message: '您希望关闭窗口时执行什么操作？',
        detail: '您可以在设置中随时更改此选项。',
        buttons: ['最小化到托盘', '完全退出'],
        defaultId: 0,
        cancelId: 0,
      })

      appSettings.firstCloseShown = true
      appSettings.closeToTray = result.response === 0
      saveSettings(appSettings)
    }

    if (appSettings.closeToTray) {
      mainWindow?.hide()
    } else {
      isQuitting = true
      await stopPythonProcess()
      app.quit()
    }
  })

  mainWindow.webContents.setWindowOpenHandler((details) => {
    shell.openExternal(details.url)
    return { action: 'deny' }
  })

  if (is.dev && process.env['ELECTRON_RENDERER_URL']) {
    mainWindow.loadURL(process.env['ELECTRON_RENDERER_URL'])
  } else {
    mainWindow.loadFile(join(__dirname, '../renderer/index.html'))
  }
}

function setupIpcHandlers(): void {
  ipcMain.handle('api:get', async (_event, endpoint: string) => {
    return apiRequest(endpoint, 'GET')
  })

  ipcMain.handle('api:post', async (_event, endpoint: string, body: unknown) => {
    return apiRequest(endpoint, 'POST', body)
  })

  ipcMain.handle('api:put', async (_event, endpoint: string, body: unknown) => {
    return apiRequest(endpoint, 'PUT', body)
  })

  ipcMain.handle('api:delete', async (_event, endpoint: string) => {
    return apiRequest(endpoint, 'DELETE')
  })

  ipcMain.handle('api:health', async () => {
    return { healthy: await checkPythonHealth() }
  })

  ipcMain.handle('dialog:openFile', async (_event, options: Electron.OpenDialogOptions) => {
    if (!mainWindow) return { canceled: true, filePaths: [] }
    return dialog.showOpenDialog(mainWindow, options)
  })

  ipcMain.handle('dialog:saveFile', async (_event, options: Electron.SaveDialogOptions) => {
    if (!mainWindow) return { canceled: true, filePath: undefined }
    return dialog.showSaveDialog(mainWindow, options)
  })

  ipcMain.handle('dialog:openDirectory', async () => {
    if (!mainWindow) return { canceled: true, filePaths: [] }
    return dialog.showOpenDialog(mainWindow, {
      properties: ['openDirectory', 'createDirectory'],
    })
  })

  ipcMain.handle('shell:openExternal', async (_event, url: string) => {
    await shell.openExternal(url)
    return true
  })

  ipcMain.handle('shell:openPath', async (_event, path: string) => {
    return shell.openPath(path)
  })

  ipcMain.handle('app:getVersion', () => {
    return app.getVersion()
  })

  ipcMain.handle('app:getPythonPath', () => {
    return findPythonExecutable() || 'python'
  })

  ipcMain.handle('app:getApiUrl', () => {
    return PYTHON_API_URL
  })

  ipcMain.handle('app:getPaths', () => {
    return {
      appPath: app.getAppPath(),
      userData: app.getPath('userData'),
      logs: app.getPath('logs'),
      temp: app.getPath('temp'),
      home: app.getPath('home'),
    }
  })

  ipcMain.handle('window:minimize', () => {
    mainWindow?.minimize()
    return true
  })

  ipcMain.handle('window:maximize', () => {
    if (mainWindow?.isMaximized()) {
      mainWindow.unmaximize()
    } else {
      mainWindow?.maximize()
    }
    return true
  })

  ipcMain.handle('window:close', () => {
    mainWindow?.close()
    return true
  })

  ipcMain.handle('window:show', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) {
        mainWindow.restore()
      }
      mainWindow.show()
      mainWindow.focus()
    }
    return true
  })

  ipcMain.handle('settings:get', () => {
    return appSettings
  })

  ipcMain.handle('settings:set', (_event, settings: Partial<AppSettings>) => {
    appSettings = { ...appSettings, ...settings }
    saveSettings(appSettings)
    return appSettings
  })

  ipcMain.handle('app:quit', async () => {
    isQuitting = true
    await stopPythonProcess()
    app.quit()
    return true
  })

  ipcMain.on('ping', () => console.log('pong'))
}

app.whenReady().then(async () => {
  electronApp.setAppUserModelId('com.one_to_two.v3')

  appSettings = loadSettings()
  console.log('[Settings] Loaded settings:', appSettings)

  app.on('browser-window-created', (_, window) => {
    optimizer.watchWindowShortcuts(window)

    window.webContents.on('before-input-event', (event, input) => {
      if (input.key === 'F12') {
        event.preventDefault()
        window.webContents.toggleDevTools()
      }
      if (input.key === 'r' && (input.meta || input.control)) {
        event.preventDefault()
        window.webContents.reload()
      }
    })
  })

  setupIpcHandlers()

  console.log('[Main] Starting Python API server...')
  try {
    await startPythonProcess()
    console.log('[Main] Python API server started successfully')
  } catch (error) {
    console.error('[Main] Failed to start Python API server:', error)
    dialog.showErrorBox(
      'Python API 启动失败',
      `无法启动 Python API 服务: ${error instanceof Error ? error.message : 'Unknown error'}\n\n请确保已安装 Python 和相关依赖。\n\n应用将继续运行，但部分功能可能不可用。`
    )
  }

  createWindow()
  createTray()

  app.on('activate', function () {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    } else if (mainWindow) {
      mainWindow.show()
    }
  })
})

app.on('before-quit', async () => {
  isQuitting = true
  await stopPythonProcess()
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

app.on('will-quit', async () => {
  await stopPythonProcess()
  if (tray) {
    tray.destroy()
    tray = null
  }
})
