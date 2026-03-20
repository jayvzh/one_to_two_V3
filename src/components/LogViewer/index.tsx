import React, { useEffect, useRef } from 'react'
import { Card, Tag, Empty } from 'antd'
import type { LogEntry } from '../../services/types'
import styles from './LogViewer.module.less'

interface LogViewerProps {
  logs: LogEntry[]
  title?: string
  maxHeight?: string | number
  autoScroll?: boolean
}

const levelColors: Record<string, string> = {
  INFO: 'blue',
  WARNING: 'orange',
  ERROR: 'red',
  DEBUG: 'gray',
}

const LogViewer: React.FC<LogViewerProps> = ({
  logs,
  title = '执行日志',
  maxHeight = 400,
  autoScroll = true,
}) => {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight
    }
  }, [logs, autoScroll])

  const formatTimestamp = (timestamp: string) => {
    try {
      const date = new Date(timestamp)
      return date.toLocaleTimeString('zh-CN', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      })
    } catch {
      return timestamp
    }
  }

  return (
    <Card title={title} className={styles.logViewer}>
      <div
        ref={containerRef}
        className={styles.logContainer}
        style={{ maxHeight }}
      >
        {logs.length === 0 ? (
          <Empty description="暂无日志" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        ) : (
          logs.map((log, index) => (
            <div key={index} className={styles.logLine}>
              <span className={styles.timestamp}>
                [{formatTimestamp(log.timestamp)}]
              </span>
              <Tag color={levelColors[log.level] || 'default'} className={styles.level}>
                {log.level}
              </Tag>
              <span className={styles.message}>{log.message}</span>
            </div>
          ))
        )}
      </div>
    </Card>
  )
}

export default LogViewer
