import React, { useState, useEffect } from 'react'
import {
  Card,
  Form,
  InputNumber,
  DatePicker,
  Button,
  message,
  Divider,
  Radio,
  Select,
  Image,
} from 'antd'
import { PlayCircleOutlined } from '@ant-design/icons'
import { api } from '../../services/api'
import { useTaskPolling } from '../../stores'
import LogViewer from '../../components/LogViewer'
import TaskStatus from '../../components/TaskStatus'
import type { HeatmapParams, ModelInfo } from '../../services/types'
import styles from './Heatmap.module.less'

const HeatmapPage: React.FC = () => {
  const [form] = Form.useForm()
  const [dateMode, setDateMode] = useState<'months' | 'range'>('months')
  const [loading, setLoading] = useState(false)
  const [models, setModels] = useState<ModelInfo[]>([])
  const [modelsLoading, setModelsLoading] = useState(false)
  const [heatmapUrl, setHeatmapUrl] = useState<string | null>(null)
  const { currentTask, startPolling } = useTaskPolling()

  useEffect(() => {
    loadModels()
  }, [])

  const loadModels = async () => {
    setModelsLoading(true)
    try {
      const response = await api.models.list()
      if (response.success && response.data) {
        setModels(response.data)
      }
    } catch (error) {
      console.error('Load models error:', error)
    } finally {
      setModelsLoading(false)
    }
  }

  const handleStart = async () => {
    try {
      const values = await form.validateFields()
      const params: HeatmapParams = {}

      if (dateMode === 'months') {
        params.months = values.months
      } else {
        params.start_date = values.dateRange?.[0]?.format('YYYY-MM-DD')
        params.end_date = values.dateRange?.[1]?.format('YYYY-MM-DD')
      }

      if (values.model) {
        params.model = values.model
      }

      setLoading(true)
      setHeatmapUrl(null)
      const response = await api.heatmap.generate(params)

      if (response.success && response.data) {
        message.success('热力图生成任务已启动')
        startPolling(response.data.task_id)
      } else {
        message.error(response.error || '启动热力图生成失败')
      }
    } catch (error) {
      console.error('Heatmap error:', error)
      message.error('启动热力图生成失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={styles.heatmapPage}>
      <Card title="热力图分析配置" className={styles.configCard}>
        <Form form={form} layout="vertical" initialValues={{ months: 12 }}>
          <Form.Item label="日期选择方式">
            <Radio.Group value={dateMode} onChange={(e) => setDateMode(e.target.value)}>
              <Radio value="months">按月数</Radio>
              <Radio value="range">按日期范围</Radio>
            </Radio.Group>
          </Form.Item>

          {dateMode === 'months' ? (
            <Form.Item
              name="months"
              label="分析月数"
              rules={[{ required: true, message: '请输入分析月数' }]}
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

          <Form.Item name="model" label="选择模型">
            <Select
              placeholder="请选择模型（可选）"
              loading={modelsLoading}
              allowClear
            >
              {models.map((model) => (
                <Select.Option key={model.name} value={model.name}>
                  {model.name}
                </Select.Option>
              ))}
            </Select>
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
              生成热力图
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

      {heatmapUrl && (
        <>
          <Divider />
          <Card title="热力图结果">
            <Image src={heatmapUrl} alt="Heatmap" style={{ maxWidth: '100%' }} />
          </Card>
        </>
      )}
    </div>
  )
}

export default HeatmapPage
