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

export type ElectronAPI = {
  api: {
    get: <T = unknown>(endpoint: string) => Promise<ApiResponse<T>>
    post: <T = unknown>(endpoint: string, body?: unknown) => Promise<ApiResponse<T>>
    put: <T = unknown>(endpoint: string, body?: unknown) => Promise<ApiResponse<T>>
    delete: <T = unknown>(endpoint: string) => Promise<ApiResponse<T>>
    health: () => Promise<{ healthy: boolean }>
  }

  dialog: {
    openFile: (options?: Electron.OpenDialogOptions) => Promise<OpenDialogResult>
    saveFile: (options?: Electron.SaveDialogOptions) => Promise<SaveDialogResult>
    openDirectory: () => Promise<OpenDialogResult>
  }

  shell: {
    openExternal: (url: string) => Promise<boolean>
    openPath: (path: string) => Promise<string>
  }

  app: {
    getVersion: () => Promise<string>
    getPythonPath: () => Promise<string>
    getApiUrl: () => Promise<string>
    getPaths: () => Promise<AppPaths>
  }

  window: {
    minimize: () => Promise<boolean>
    maximize: () => Promise<boolean>
    close: () => Promise<boolean>
    show: () => Promise<boolean>
  }

  invoke: (channel: string, ...args: unknown[]) => Promise<unknown>
  send: (channel: string, data?: unknown) => void
  receive: (channel: string, callback: (...args: unknown[]) => void) => void
  removeListener: (channel: string, callback: (...args: unknown[]) => void) => void
  ping: () => void
}

declare global {
  interface Window {
    electronAPI: ElectronAPI
  }
}

export {}
