import { contextBridge, ipcRenderer } from 'electron'

console.log('[Preload] Script is executing...')
console.log('[Preload] contextBridge available:', typeof contextBridge !== 'undefined')
console.log('[Preload] ipcRenderer available:', typeof ipcRenderer !== 'undefined')

export type ApiResponse<T = unknown> = {
  success: boolean
  data?: T
  error?: string
}

export type OpenDialogResult = {
  canceled: boolean
  filePaths: string[]
}

export type SaveDialogResult = {
  canceled: boolean
  filePath?: string
}

export type AppPaths = {
  appPath: string
  userData: string
  logs: string
  temp: string
  home: string
}

export type AppSettings = {
  closeToTray: boolean
  firstCloseShown: boolean
}

const validInvokeChannels = [
  'api:get',
  'api:post',
  'api:put',
  'api:delete',
  'api:health',
  'api:download',
  'api:upload',
  'dialog:openFile',
  'dialog:saveFile',
  'dialog:openDirectory',
  'shell:openExternal',
  'shell:openPath',
  'app:getVersion',
  'app:getPythonPath',
  'app:getApiUrl',
  'app:getPaths',
  'app:quit',
  'window:minimize',
  'window:maximize',
  'window:close',
  'window:show',
  'settings:get',
  'settings:set',
] as const

type InvokeChannel = (typeof validInvokeChannels)[number]

const validSendChannels = ['ping'] as const
type SendChannel = (typeof validSendChannels)[number]

const validReceiveChannels = ['ping'] as const
type ReceiveChannel = (typeof validReceiveChannels)[number]

const electronAPI = {
  api: {
    get: <T = unknown>(endpoint: string): Promise<ApiResponse<T>> => {
      return ipcRenderer.invoke('api:get', endpoint)
    },

    post: <T = unknown>(endpoint: string, body?: unknown): Promise<ApiResponse<T>> => {
      return ipcRenderer.invoke('api:post', endpoint, body)
    },

    put: <T = unknown>(endpoint: string, body?: unknown): Promise<ApiResponse<T>> => {
      return ipcRenderer.invoke('api:put', endpoint, body)
    },

    delete: <T = unknown>(endpoint: string): Promise<ApiResponse<T>> => {
      return ipcRenderer.invoke('api:delete', endpoint)
    },

    health: (): Promise<{ healthy: boolean }> => {
      return ipcRenderer.invoke('api:health')
    },

    download: (endpoint: string): Promise<ApiResponse<{ path: string }>> => {
      return ipcRenderer.invoke('api:download', endpoint)
    },

    uploadFile: <T = unknown>(endpoint: string, filePath: string): Promise<ApiResponse<T>> => {
      return ipcRenderer.invoke('api:upload', endpoint, filePath)
    },
  },

  dialog: {
    openFile: (options?: Electron.OpenDialogOptions): Promise<OpenDialogResult> => {
      return ipcRenderer.invoke('dialog:openFile', options)
    },

    saveFile: (options?: Electron.SaveDialogOptions): Promise<SaveDialogResult> => {
      return ipcRenderer.invoke('dialog:saveFile', options)
    },

    openDirectory: (): Promise<OpenDialogResult> => {
      return ipcRenderer.invoke('dialog:openDirectory')
    },
  },

  shell: {
    openExternal: (url: string): Promise<boolean> => {
      return ipcRenderer.invoke('shell:openExternal', url)
    },

    openPath: (path: string): Promise<string> => {
      return ipcRenderer.invoke('shell:openPath', path)
    },
  },

  app: {
    getVersion: (): Promise<string> => {
      return ipcRenderer.invoke('app:getVersion')
    },

    getPythonPath: (): Promise<string> => {
      return ipcRenderer.invoke('app:getPythonPath')
    },

    getApiUrl: (): Promise<string> => {
      return ipcRenderer.invoke('app:getApiUrl')
    },

    getPaths: (): Promise<AppPaths> => {
      return ipcRenderer.invoke('app:getPaths')
    },

    quit: (): Promise<boolean> => {
      return ipcRenderer.invoke('app:quit')
    },
  },

  settings: {
    get: (): Promise<AppSettings> => {
      return ipcRenderer.invoke('settings:get')
    },

    set: (settings: Partial<AppSettings>): Promise<AppSettings> => {
      return ipcRenderer.invoke('settings:set', settings)
    },
  },

  window: {
    minimize: (): Promise<boolean> => {
      return ipcRenderer.invoke('window:minimize')
    },

    maximize: (): Promise<boolean> => {
      return ipcRenderer.invoke('window:maximize')
    },

    close: (): Promise<boolean> => {
      return ipcRenderer.invoke('window:close')
    },

    show: (): Promise<boolean> => {
      return ipcRenderer.invoke('window:show')
    },
  },

  invoke: (channel: InvokeChannel, ...args: unknown[]): Promise<unknown> => {
    if (validInvokeChannels.includes(channel as InvokeChannel)) {
      return ipcRenderer.invoke(channel, ...args)
    }
    return Promise.reject(new Error(`Invalid invoke channel: ${channel}`))
  },

  send: (channel: SendChannel, data?: unknown): void => {
    if (validSendChannels.includes(channel as SendChannel)) {
      ipcRenderer.send(channel, data)
    } else {
      console.error(`Invalid send channel: ${channel}`)
    }
  },

  receive: (channel: ReceiveChannel, callback: (...args: unknown[]) => void): void => {
    if (validReceiveChannels.includes(channel as ReceiveChannel)) {
      const subscription = (_event: Electron.IpcRendererEvent, ...args: unknown[]) =>
        callback(...args)
      ipcRenderer.on(channel, subscription)
    } else {
      console.error(`Invalid receive channel: ${channel}`)
    }
  },

  removeListener: (channel: ReceiveChannel, callback: (...args: unknown[]) => void): void => {
    if (validReceiveChannels.includes(channel as ReceiveChannel)) {
      ipcRenderer.removeListener(channel, callback)
    }
  },

  ping: (): void => {
    ipcRenderer.send('ping')
  },
}

contextBridge.exposeInMainWorld('electronAPI', electronAPI)

export type ElectronAPI = typeof electronAPI
