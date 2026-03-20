import type {
  ApiResponse,
  TaskResponse,
  TaskStatus,
  TaskLog,
  TrainParams,
  DailyParams,
  RollingParams,
  BacktestParams,
  HeatmapParams,
  SyncCacheParams,
  ModelInfo,
  ReportInfo,
  SchedulerStatus,
  ConfigData,
  LogEntry,
  CacheStatus,
  CacheImportResult,
} from './types'

function getElectronAPI() {
  if (typeof window !== 'undefined' && window.electronAPI) {
    return window.electronAPI
  }
  throw new Error('Electron API not available')
}

async function apiGet<T>(endpoint: string): Promise<ApiResponse<T>> {
  try {
    const api = getElectronAPI()
    const response = await api.api.get<{ success: boolean; data?: T; error?: string; detail?: string }>(endpoint)
    
    if (response.success && response.data) {
      const backendData = response.data
      if (backendData.success && backendData.data !== undefined) {
        return { success: true, data: backendData.data }
      }
      return { success: true, data: backendData as T }
    }
    
    return {
      success: false,
      error: response.error || 'API request failed',
    }
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'API call failed',
    }
  }
}

async function apiPost<T>(endpoint: string, body?: unknown): Promise<ApiResponse<T>> {
  try {
    const api = getElectronAPI()
    const response = await api.api.post<{ success: boolean; data?: T; task_id?: string; error?: string; detail?: string; message?: string }>(endpoint, body)
    
    if (response.success && response.data) {
      const backendData = response.data
      if (backendData.success) {
        const result: TaskResponse = {
          task_id: backendData.task_id || '',
          status: 'pending',
          message: backendData.message,
        }
        return { success: true, data: result as T }
      }
      return { success: false, error: backendData.error || backendData.detail || 'Request failed' }
    }
    
    return {
      success: false,
      error: response.error || 'API request failed',
    }
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'API call failed',
    }
  }
}

async function apiPut<T>(endpoint: string, body?: unknown): Promise<ApiResponse<T>> {
  try {
    const api = getElectronAPI()
    const response = await api.api.put<{ success: boolean; data?: T; error?: string; detail?: string }>(endpoint, body)
    
    if (response.success && response.data) {
      const backendData = response.data
      if (backendData.success && backendData.data !== undefined) {
        return { success: true, data: backendData.data }
      }
      return { success: true, data: backendData as T }
    }
    
    return {
      success: false,
      error: response.error || 'API request failed',
    }
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'API call failed',
    }
  }
}

async function apiDelete<T>(endpoint: string): Promise<ApiResponse<T>> {
  try {
    const api = getElectronAPI()
    const response = await api.api.delete<{ success: boolean; data?: T; error?: string; detail?: string }>(endpoint)
    
    if (response.success && response.data) {
      const backendData = response.data
      if (backendData.success) {
        return { success: true, data: backendData.data as T }
      }
      return { success: true, data: backendData as T }
    }
    
    return {
      success: false,
      error: response.error || 'API request failed',
    }
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'API call failed',
    }
  }
}

export const api = {
  train: {
    start: (params: TrainParams) => {
      const body: Record<string, unknown> = {}
      if (params.months !== undefined) body.months = params.months
      if (params.start_date) body.start = params.start_date
      if (params.end_date) body.end = params.end_date
      return apiPost<TaskResponse>('/api/train', body)
    },
  },

  daily: {
    generate: (params: DailyParams = {}) => {
      const body: Record<string, unknown> = {}
      if (params.date) body.date = params.date
      return apiPost<TaskResponse>('/api/daily', body)
    },
  },

  rolling: {
    start: (params: RollingParams) => {
      const body: Record<string, unknown> = {}
      if (params.sensitivity_test !== undefined) body.sensitivity = params.sensitivity_test
      if (params.start_date) body.start = params.start_date
      if (params.end_date) body.end = params.end_date
      return apiPost<TaskResponse>('/api/rolling', body)
    },
  },

  backtest: {
    emotion: (params: BacktestParams) => {
      const body: Record<string, unknown> = {}
      if (params.months !== undefined) body.months = params.months
      if (params.start_date) body.start = params.start_date
      if (params.end_date) body.end = params.end_date
      return apiPost<TaskResponse>('/api/backtest-emotion', body)
    },
  },

  heatmap: {
    generate: (params: HeatmapParams) => {
      const body: Record<string, unknown> = {}
      if (params.months !== undefined) body.months = params.months
      if (params.start_date) body.start = params.start_date
      if (params.end_date) body.end = params.end_date
      if (params.model) body.model = params.model
      return apiPost<TaskResponse>('/api/heatmap', body)
    },
  },

  syncCache: {
    run: (params: SyncCacheParams = {}) => {
      const body: Record<string, unknown> = {}
      if (params.limit_pool_days !== undefined) body.zt_trade_days = params.limit_pool_days
      if (params.index_months !== undefined) body.index_months = params.index_months
      return apiPost<TaskResponse>('/api/sync-cache', body)
    },
  },

  models: {
    list: async () => {
      const response = await apiGet<Array<{ filename: string; train_start?: string; train_end?: string; sample_size?: number; base_success_rate?: number; version?: string; type?: string; error?: string }>>('/api/models')
      if (response.success && response.data) {
        const models: ModelInfo[] = response.data.map(m => ({
          name: m.filename,
          path: '',
          created_at: m.train_end,
          size: m.sample_size,
        }))
        return { success: true, data: models } as ApiResponse<ModelInfo[]>
      }
      return response as unknown as ApiResponse<ModelInfo[]>
    },
  },

  reports: {
    list: async () => {
      const response = await apiGet<Array<{ filename: string; name: string; type: string; path: string; size?: number; modified?: string }>>('/api/reports')
      if (response.success && response.data) {
        const reports: ReportInfo[] = response.data.map(r => ({
          id: r.filename,
          name: r.name,
          type: r.type,
          path: r.path,
          size: r.size,
          created_at: r.modified || new Date().toISOString(),
        }))
        return { success: true, data: reports } as ApiResponse<ReportInfo[]>
      }
      return response as unknown as ApiResponse<ReportInfo[]>
    },
    open: (reportId: string): ApiResponse<{ url: string }> => {
      const apiUrl = `http://localhost:8000/reports/${reportId}`
      return { success: true, data: { url: apiUrl } }
    },
    delete: (reportId: string) =>
      apiDelete<void>(`/api/reports/${reportId}`),
  },

  config: {
    get: () => apiGet<ConfigData>('/api/config'),
    update: (config: ConfigData) =>
      apiPut<ConfigData>('/api/config', config),
  },

  scheduler: {
    status: () => apiGet<SchedulerStatus>('/api/scheduler/status'),
    install: () =>
      apiPost<TaskResponse>('/api/scheduler/install'),
    uninstall: () =>
      apiPost<void>('/api/scheduler/uninstall'),
  },

  tasks: {
    getStatus: (taskId: string) => apiGet<TaskStatus>(`/api/tasks/${taskId}`),
    getLogs: (taskId: string) => apiGet<string[]>(`/api/tasks/${taskId}/logs`),
  },

  cache: {
    getStatus: () => apiGet<CacheStatus>('/api/cache/status'),
    export: async (): Promise<ApiResponse<void>> => {
      try {
        const api = getElectronAPI()
        await api.api.download('/api/cache/export')
        return { success: true }
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Export failed',
        }
      }
    },
    import: async (): Promise<ApiResponse<CacheImportResult>> => {
      try {
        const api = getElectronAPI()
        const dialogResult = await api.dialog.openFile({
          filters: [{ name: 'ZIP Files', extensions: ['zip'] }],
          properties: ['openFile'],
        })
        if (dialogResult.canceled || dialogResult.filePaths.length === 0) {
          return { success: false, error: 'Cancelled' }
        }
        const filePath = dialogResult.filePaths[0]
        const response = await api.api.uploadFile<CacheImportResult>('/api/cache/import', filePath)
        if (response.success && response.data) {
          return { success: true, data: response.data }
        }
        return {
          success: false,
          error: response.error || 'Import failed',
        }
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Import failed',
        }
      }
    },
  },
}

function parseLogLine(logLine: string): LogEntry {
  const match = logLine.match(/^\[([^\]]+)\]\s*(.*)$/)
  if (match) {
    const timestamp = match[1]
    const rest = match[2]
    
    let level: LogEntry['level'] = 'INFO'
    let message = rest
    
    const levelMatch = rest.match(/^(INFO|WARNING|ERROR|DEBUG)\s*:\s*(.*)$/i)
    if (levelMatch) {
      level = levelMatch[1].toUpperCase() as LogEntry['level']
      message = levelMatch[2]
    }
    
    return { timestamp, level, message }
  }
  
  return {
    timestamp: new Date().toISOString(),
    level: 'INFO',
    message: logLine,
  }
}

export async function pollTaskStatus(
  taskId: string,
  onProgress: (status: TaskStatus) => void,
  interval = 2000
): Promise<TaskStatus> {
  return new Promise((resolve, reject) => {
    const poll = async () => {
      try {
        const response = await api.tasks.getStatus(taskId)
        if (response.success && response.data) {
          onProgress(response.data)
          
          if (response.data.state === 'completed') {
            resolve(response.data)
          } else if (response.data.state === 'failed') {
            reject(new Error(response.data.error || 'Task failed'))
          } else {
            setTimeout(poll, interval)
          }
        } else {
          reject(new Error(response.error || 'Failed to get task status'))
        }
      } catch (error) {
        reject(error)
      }
    }
    
    poll()
  })
}

export async function fetchTaskLogs(
  taskId: string
): Promise<TaskLog | null> {
  const response = await api.tasks.getLogs(taskId)
  if (response.success && response.data) {
    const logArray = response.data
    const logs: LogEntry[] = logArray.map(parseLogLine)
    return { task_id: taskId, logs }
  }
  return null
}

export async function checkApiHealth(): Promise<boolean> {
  try {
    const api = getElectronAPI()
    const result = await api.api.health()
    return result.healthy
  } catch {
    return false
  }
}
