export interface ApiResponse<T = unknown> {
  success: boolean
  data?: T
  message?: string
  error?: string
}

export interface TaskResponse {
  task_id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  message?: string
}

export interface TaskStatus {
  task_id: string
  task_type?: string
  state: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  progress: number
  message?: string
  result?: Record<string, unknown>
  error?: string
  created_at?: string
  started_at?: string
  completed_at?: string
  logs?: string[]
}

export interface TaskLog {
  task_id: string
  logs: LogEntry[]
}

export interface LogEntry {
  timestamp: string
  level: 'INFO' | 'WARNING' | 'ERROR' | 'DEBUG'
  message: string
}

export interface TrainParams {
  months?: number
  start_date?: string
  end_date?: string
}

export interface DailyParams {
  date?: string
}

export interface RollingParams {
  sensitivity_test?: boolean
  start_date?: string
  end_date?: string
}

export interface BacktestParams {
  months?: number
  start_date?: string
  end_date?: string
}

export interface HeatmapParams {
  months?: number
  start_date?: string
  end_date?: string
  model?: string
}

export interface SyncCacheParams {
  limit_pool_days?: number
  index_months?: number
}

export interface ModelInfo {
  name: string
  path: string
  created_at?: string
  size?: number
}

export interface ReportInfo {
  id: string
  name: string
  type: string
  path: string
  created_at: string
  size?: number
}

export interface SchedulerStatus {
  installed: boolean
  running: boolean
  last_run?: string
  next_run?: string
  task_name?: string
}

export interface ConfigData {
  [key: string]: string | number | boolean | object | null
}

export interface HeatmapResult {
  image_url: string
  image_path: string
}

export interface CacheInfo {
  available: boolean
  start_date: string | null
  end_date: string | null
  count: number
}

export interface CacheStatus {
  zt_cache: CacheInfo
  index_cache: CacheInfo
  cache_dir: string
}

export interface CacheImportResult {
  success: boolean
  message: string
  zt_count: number
  index_count: number
}
