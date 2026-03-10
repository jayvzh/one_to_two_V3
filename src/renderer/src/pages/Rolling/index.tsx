import React, { useState } from 'react'
import {
  Card,
  Form,
  Switch,
  DatePicker,
  Button,
  message,
  Divider,
} from 'antd'
import { PlayCircleOutlined } from '@ant-design/icons'
import { api } from '../../services/api'
import { useTaskPolling } from '../../stores'
import LogViewer from '../../components/LogViewer'
import TaskStatus from '../../components/TaskStatus'
import type { RollingParams } from '../../services/types'
import styles from './Rolling.module.less'

const RollingPage: React.FC = () => {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const { currentTask, startPolling } = useTaskPolling()

  const handleStart = async () => {
    try {
      const values = await form.validateFields()
      const params: RollingParams = {
        sensitivity_test: values.sensitivity_test || false,
        start_date: values.dateRange?.[0]?.format('YYYY-MM-DD'),
        end_date: values.dateRange?.[1]?.format('YYYY-MM-DD'),
      }

      setLoading(true)
      const response = await api.rolling.start(params)

      if (response.success && response.data) {
        message.success('滚动训练任务已启动')
        startPolling(response.data.task_id)
      } else {
        message.error(response.error || '启动滚动训练失败')
      }
    } catch (error) {
      console.error('Rolling error:', error)
      message.error('启动滚动训练失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={styles.rollingPage}>
      <Card title="滚动训练配置" className={styles.configCard}>
        <Form form={form} layout="vertical">
          <Form.Item
            name="sensitivity_test"
            label="敏感性测试"
            valuePropName="checked"
          >
            <Switch checkedChildren="开启" unCheckedChildren="关闭" />
          </Form.Item>

          <Form.Item
            name="dateRange"
            label="日期范围"
            rules={[{ required: true, message: '请选择日期范围' }]}
          >
            <DatePicker.RangePicker style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item>
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={handleStart}
              loading={loading}
              disabled={currentTask.isRunning}
              size="large"
            >
              开始滚动训练
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

export default RollingPage
