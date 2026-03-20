import React from 'react'
import { Card, Progress, Tag, Space, Button } from 'antd'
import {
  ClockCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
  StopOutlined,
} from '@ant-design/icons'
import type { TaskStatus } from '../../services/types'
import styles from './TaskStatus.module.less'

interface TaskStatusProps {
  status: TaskStatus | null
  isRunning: boolean
  onStop?: () => void
}

const statusConfig: Record<
  string,
  { color: string; icon: React.ReactNode; text: string }
> = {
  pending: {
    color: 'default',
    icon: <ClockCircleOutlined />,
    text: '等待中',
  },
  running: {
    color: 'processing',
    icon: <LoadingOutlined spin />,
    text: '执行中',
  },
  completed: {
    color: 'success',
    icon: <CheckCircleOutlined />,
    text: '已完成',
  },
  failed: {
    color: 'error',
    icon: <CloseCircleOutlined />,
    text: '失败',
  },
  cancelled: {
    color: 'warning',
    icon: <StopOutlined />,
    text: '已取消',
  },
}

const TaskStatusComponent: React.FC<TaskStatusProps> = ({
  status,
  isRunning,
  onStop,
}) => {
  if (!status) {
    return null
  }

  const taskState = status.state || 'pending'
  const config = statusConfig[taskState] || statusConfig.pending

  return (
    <Card className={styles.taskStatus}>
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        <div className={styles.header}>
          <Space>
            <Tag color={config.color} icon={config.icon}>
              {config.text}
            </Tag>
            {status.task_id && (
              <span className={styles.taskId}>ID: {status.task_id.slice(0, 8)}...</span>
            )}
          </Space>
          {isRunning && onStop && (
            <Button
              size="small"
              danger
              icon={<StopOutlined />}
              onClick={onStop}
            >
              停止
            </Button>
          )}
        </div>

        {(taskState === 'running' || taskState === 'pending') && (
          <Progress
            percent={Math.round((status.progress || 0) * 100)}
            status={taskState === 'running' ? 'active' : 'normal'}
            strokeColor={{
              '0%': '#108ee9',
              '100%': '#87d068',
            }}
          />
        )}

        {status.message && (
          <div className={styles.message}>{status.message}</div>
        )}

        {status.error && (
          <div className={styles.error}>
            <CloseCircleOutlined /> {status.error}
          </div>
        )}
      </Space>
    </Card>
  )
}

export default TaskStatusComponent
