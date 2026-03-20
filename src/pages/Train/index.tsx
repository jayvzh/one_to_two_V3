import React, { useState } from 'react'
import {
  Card,
  Form,
  InputNumber,
  DatePicker,
  Button,
  message,
  Radio,
  Divider,
} from 'antd'
import { PlayCircleOutlined } from '@ant-design/icons'
import { api } from '../../services/api'
import { useTaskPolling } from '../../stores'
import LogViewer from '../../components/LogViewer'
import TaskStatus from '../../components/TaskStatus'
import type { TrainParams } from '../../services/types'
import styles from './Train.module.less'

const TrainPage: React.FC = () => {
  const [form] = Form.useForm()
  const [dateMode, setDateMode] = useState<'months' | 'range'>('months')
  const [loading, setLoading] = useState(false)
  const { currentTask, startPolling } = useTaskPolling()

  const handleStartTrain = async () => {
    try {
      const values = await form.validateFields()
      const params: TrainParams = {}

      if (dateMode === 'months') {
        params.months = values.months
      } else {
        params.start_date = values.dateRange?.[0]?.format('YYYY-MM-DD')
        params.end_date = values.dateRange?.[1]?.format('YYYY-MM-DD')
      }

      setLoading(true)
      const response = await api.train.start(params)

      if (response.success && response.data) {
        message.success('训练任务已启动')
        startPolling(response.data.task_id)
      } else {
        message.error(response.error || '启动训练失败')
      }
    } catch (error) {
      console.error('Train error:', error)
      message.error('启动训练失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={styles.trainPage}>
      <Card title="参数配置" className={styles.configCard}>
        <Form form={form} layout="vertical" initialValues={{ months: 6 }}>
          <Form.Item label="日期选择方式">
            <Radio.Group value={dateMode} onChange={(e) => setDateMode(e.target.value)}>
              <Radio value="months">按月数</Radio>
              <Radio value="range">按日期范围</Radio>
            </Radio.Group>
          </Form.Item>

          {dateMode === 'months' ? (
            <Form.Item
              name="months"
              label="训练月数"
              rules={[{ required: true, message: '请输入训练月数' }]}
            >
              <InputNumber min={1} max={120} style={{ width: '100%' }} />
            </Form.Item>
          ) : (
            <Form.Item
              name="dateRange"
              label="日期范围"
              rules={[{ required: true, message: '请选择日期范围' }]}
            >
              <DatePicker.RangePicker style={{ width: '100%' }} />
            </Form.Item>
          )}

          <Form.Item>
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={handleStartTrain}
              loading={loading}
              disabled={currentTask.isRunning}
              size="large"
            >
              开始训练
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

export default TrainPage
