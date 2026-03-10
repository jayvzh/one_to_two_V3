import React, { createContext, useContext, useState, useCallback, useRef, useEffect } from 'react'
import type { TaskStatus, LogEntry } from '../services/types'
import { pollTaskStatus, fetchTaskLogs } from '../services/api'

interface TaskState {
  taskId: string | null
  status: TaskStatus | null
  logs: LogEntry[]
  isRunning: boolean
}

interface AppState {
  currentTask: TaskState
  startTask: (taskId: string) => void
  updateTaskStatus: (status: TaskStatus) => void
  addLog: (log: LogEntry) => void
  setLogs: (logs: LogEntry[]) => void
  clearTask: () => void
  stopPolling: () => void
}

const AppContext = createContext<AppState | undefined>(undefined)

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [currentTask, setCurrentTask] = useState<TaskState>({
    taskId: null,
    status: null,
    logs: [],
    isRunning: false,
  })
  
  const pollingRef = useRef<boolean>(false)
  const intervalRef = useRef<NodeJS.Timeout | null>(null)

  const startTask = useCallback((taskId: string) => {
    setCurrentTask({
      taskId,
      status: { task_id: taskId, state: 'pending', progress: 0 },
      logs: [],
      isRunning: true,
    })
    pollingRef.current = true
  }, [])

  const updateTaskStatus = useCallback((status: TaskStatus) => {
    setCurrentTask(prev => ({
      ...prev,
      status,
      isRunning: status.state === 'running' || status.state === 'pending',
    }))
  }, [])

  const addLog = useCallback((log: LogEntry) => {
    setCurrentTask(prev => ({
      ...prev,
      logs: [...prev.logs, log],
    }))
  }, [])

  const setLogs = useCallback((logs: LogEntry[]) => {
    setCurrentTask(prev => ({
      ...prev,
      logs,
    }))
  }, [])

  const clearTask = useCallback(() => {
    pollingRef.current = false
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
    setCurrentTask({
      taskId: null,
      status: null,
      logs: [],
      isRunning: false,
    })
  }, [])

  const stopPolling = useCallback(() => {
    pollingRef.current = false
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
  }, [])

  useEffect(() => {
    return () => {
      pollingRef.current = false
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, [])

  const value: AppState = {
    currentTask,
    startTask,
    updateTaskStatus,
    addLog,
    setLogs,
    clearTask,
    stopPolling,
  }

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>
}

export function useApp() {
  const context = useContext(AppContext)
  if (!context) {
    throw new Error('useApp must be used within AppProvider')
  }
  return context
}

export function useTaskPolling() {
  const { currentTask, startTask, updateTaskStatus, setLogs, stopPolling } = useApp()

  const startPolling = useCallback(
    async (taskId: string) => {
      startTask(taskId)

      try {
        await pollTaskStatus(
          taskId,
          (status) => {
            updateTaskStatus(status)
          },
          2000
        )
        
        const finalLogs = await fetchTaskLogs(taskId)
        if (finalLogs) {
          setLogs(finalLogs.logs)
        }
      } catch (error) {
        console.error('Task polling error:', error)
      }
    },
    [startTask, updateTaskStatus, setLogs]
  )

  return {
    currentTask,
    startPolling,
    stopPolling,
  }
}
