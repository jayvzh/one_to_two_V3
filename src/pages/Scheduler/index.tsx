import React, { useState, useEffect } from 'react'
import {
  Card,
  Button,
  message,
  Descriptions,
  Tag,
  Space,
  Divider,
  Spin,
} from 'antd'
import {
  PlayCircleOutlined,
  StopOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons'
import { api } from '../../services/api'
import type { SchedulerStatus } from '../../services/types'
import styles from './Scheduler.module.less'

const SchedulerPage: React.FC = () => {
  const [status, setStatus] = useState<SchedulerStatus | null>(null)
  const [loading, setLoading] = useState(false)
  const [actionLoading, setActionLoading] = useState(false)

  useEffect(() => {
    loadStatus()
    const interval = setInterval(loadStatus, 10000)
    return () => clearInterval(interval)
  }, [])

  const loadStatus = async () => {
    setLoading(true)
    try {
      const response = await api.scheduler.status()
      if (response.success && response.data) {
        setStatus(response.data)
      }
    } catch (error) {
      console.error('Load scheduler status error:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleInstall = async () => {
    setActionLoading(true)
    try {
      const response = await api.scheduler.install()
      if (response.success) {
        message.success('计划任务已安装')
        loadStatus()
      } else {
        message.error(response.error || '安装计划任务失败')
      }
    } catch (error) {
      console.error('Install scheduler error:', error)
      message.error('安装计划任务失败')
    } finally {
      setActionLoading(false)
    }
  }

  const handleUninstall = async () => {
    setActionLoading(true)
    try {
      const response = await api.scheduler.uninstall()
      if (response.success) {
        message.success('计划任务已卸载')
        loadStatus()
      } else {
        message.error(response.error || '卸载计划任务失败')
      }
    } catch (error) {
      console.error('Uninstall scheduler error:', error)
      message.error('卸载计划任务失败')
    } finally {
      setActionLoading(false)
    }
  }

  return (
    <div className={styles.schedulerPage}>
      <Card title="计划任务状态" className={styles.statusCard}>
        <Spin spinning={loading}>
          <Descriptions column={2} bordered>
            <Descriptions.Item label="状态">
              {status?.installed ? (
                <Tag color="success" icon={<CheckCircleOutlined />}>
                  已安装
                </Tag>
              ) : (
                <Tag color="default" icon={<CloseCircleOutlined />}>
                  未安装
                </Tag>
              )}
            </Descriptions.Item>
            <Descriptions.Item label="运行状态">
              {status?.running ? (
                <Tag color="processing">运行中</Tag>
              ) : (
                <Tag>已停止</Tag>
              )}
            </Descriptions.Item>
            <Descriptions.Item label="任务名称">
              {status?.task_name || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="上次运行">
              {status?.last_run || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="下次运行" span={2}>
              {status?.next_run || '-'}
            </Descriptions.Item>
          </Descriptions>
        </Spin>

        <Divider />

        <Space>
          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            onClick={handleInstall}
            loading={actionLoading}
            disabled={status?.installed}
          >
            安装计划任务
          </Button>
          <Button
            danger
            icon={<StopOutlined />}
            onClick={handleUninstall}
            loading={actionLoading}
            disabled={!status?.installed}
          >
            卸载计划任务
          </Button>
        </Space>
      </Card>
    </div>
  )
}

export default SchedulerPage
