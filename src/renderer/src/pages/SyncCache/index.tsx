import React, { useState } from 'react'
import {
  Card,
  Form,
  InputNumber,
  Button,
  message,
  Divider,
} from 'antd'
import { PlayCircleOutlined } from '@ant-design/icons'
import { api } from '../../services/api'
import { useTaskPolling } from '../../stores'
import LogViewer from '../../components/LogViewer'
import TaskStatus from '../../components/TaskStatus'
import type { SyncCacheParams } from '../../services/types'
import styles from './SyncCache.module.less'

const SyncCachePage: React.FC = () => {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const { currentTask, startPolling } = useTaskPolling()

  const handleSync = async () => {
    try {
      const values = await form.validateFields()
      const params: SyncCacheParams = {
        limit_pool_days: values.limit_pool_days,
        index_months: values.index_months,
      }

      setLoading(true)
      const response = await api.syncCache.run(params)

      if (response.success && response.data) {
        message.success('缓存同步任务已启动')
        startPolling(response.data.task_id)
      } else {
        message.error(response.error || '启动缓存同步失败')
      }
    } catch (error) {
      console.error('Sync cache error:', error)
      message.error('启动缓存同步失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={styles.syncCachePage}>
      <Card title="缓存同步配置" className={styles.configCard}>
        <Form
          form={form}
          layout="vertical"
          initialValues={{ limit_pool_days: 30, index_months: 12 }}
        >
          <Form.Item
            name="limit_pool_days"
            label="涨停池天数"
          >
            <InputNumber min={1} max={365} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item
            name="index_months"
            label="指数月数"
          >
            <InputNumber min={1} max={120} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item>
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={handleSync}
              loading={loading}
              disabled={currentTask.isRunning}
              size="large"
            >
              开始同步
            </Button>
          </Form.Item>
        </Form>
      </Card>

      {currentTask.status && (
        <>
          <Divider />
          <TaskStatus
            status={currentTask.status}
            isRunning={currentTask.isRunning}
          />
        </>
      )}

      {currentTask.logs.length > 0 && (
        <>
          <Divider />
          <LogViewer logs={currentTask.logs} maxHeight={500} />
        </>
      )}
    </div>
  )
}

export default SyncCachePage
