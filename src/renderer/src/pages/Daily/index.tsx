import React, { useState } from 'react'
import {
  Card,
  Form,
  DatePicker,
  Button,
  message,
  Divider,
  Space,
} from 'antd'
import { PlayCircleOutlined } from '@ant-design/icons'
import { api } from '../../services/api'
import { useTaskPolling } from '../../stores'
import LogViewer from '../../components/LogViewer'
import TaskStatus from '../../components/TaskStatus'
import styles from './Daily.module.less'

const DailyPage: React.FC = () => {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const { currentTask, startPolling } = useTaskPolling()

  const handleGenerate = async () => {
    try {
      const values = await form.validateFields()
      const params = {
        date: values.date?.format('YYYY-MM-DD'),
      }

      setLoading(true)
      const response = await api.daily.generate(params)

      if (response.success && response.data) {
        message.success('日报生成任务已启动')
        startPolling(response.data.task_id)
      } else {
        message.error(response.error || '启动日报生成失败')
      }
    } catch (error) {
      console.error('Daily error:', error)
      message.error('启动日报生成失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={styles.dailyPage}>
      <Card title="每日日报生成" className={styles.configCard}>
        <Form form={form} layout="vertical">
          <Form.Item
            name="date"
            label="日期"
            extra="留空则使用今天日期"
          >
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button
                type="primary"
                icon={<PlayCircleOutlined />}
                onClick={handleGenerate}
                loading={loading}
                disabled={currentTask.isRunning}
                size="large"
              >
                生成日报
              </Button>
            </Space>
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

export default DailyPage
