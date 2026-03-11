import React, { useState, useEffect } from 'react'
import {
  Card,
  Form,
  Input,
  InputNumber,
  Switch,
  Button,
  message,
  Spin,
  Typography,
  Tooltip,
} from 'antd'
import { SaveOutlined, ReloadOutlined, InfoCircleOutlined } from '@ant-design/icons'
import { api } from '../../services/api'
import { useApp } from '../../stores/AppContext'
import styles from './Settings.module.less'

const { Text, Paragraph } = Typography

interface FieldMetadata {
  label: string
  description: string
  type: 'number' | 'string' | 'array'
  default: number | string | number[]
  min?: number
  max?: number
}

interface GroupMetadata {
  label: string
  description: string
  fields: Record<string, FieldMetadata>
}

type ConfigMetadata = Record<string, GroupMetadata>

const CONFIG_METADATA: ConfigMetadata = {
  production_train: {
    label: '生产训练',
    description: '生产环境模型训练配置',
    fields: {
      months: { label: '训练月数', description: '模型训练使用的历史数据月数', type: 'number', default: 6, min: 1, max: 120 },
      cache_check_months: { label: '缓存检查月数', description: '训练前检查缓存数据的月数', type: 'number', default: 6, min: 1, max: 24 }
    }
  },
  daily: {
    label: '日报生成',
    description: '每日日报生成配置',
    fields: {
      cache_check_months: { label: '缓存检查月数', description: '生成日报前检查缓存数据的月数', type: 'number', default: 2, min: 1, max: 24 },
      model_filename: { label: '模型文件名', description: '日报使用的模型文件名', type: 'string', default: 'model_latest.joblib' }
    }
  },
  emotion_backtest: {
    label: '情绪回测',
    description: '情绪指标回测配置',
    fields: {
      months: { label: '回测月数', description: '回测使用的历史数据月数', type: 'number', default: 6, min: 1, max: 120 },
      window_days: { label: '窗口天数', description: '滚动窗口天数', type: 'number', default: 64, min: 1, max: 365 },
      cache_check_months: { label: '缓存检查月数', description: '回测前检查缓存数据的月数', type: 'number', default: 3, min: 1, max: 24 }
    }
  },
  rolling: {
    label: '滚动训练',
    description: '滚动训练配置',
    fields: {
      train_months: { label: '训练月数', description: '每次训练使用的历史数据月数', type: 'number', default: 6, min: 1, max: 120 },
      test_months: { label: '测试月数', description: '每次测试使用的数据月数', type: 'number', default: 1, min: 1, max: 12 },
      sensitivity_train_months: { label: '敏感性测试月数', description: '敏感性测试使用的训练月数列表，用逗号分隔', type: 'array', default: [2, 3, 4, 6] }
    }
  },
  heatmap: {
    label: '热力图',
    description: '热力图分析配置',
    fields: {
      months: { label: '分析月数', description: '热力图分析使用的历史数据月数', type: 'number', default: 1, min: 1, max: 120 },
      model_filename: { label: '模型文件名', description: '热力图使用的模型文件名', type: 'string', default: 'model_latest.joblib' }
    }
  }
}

const SettingsPage: React.FC = () => {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const { appSettings, updateSettings } = useApp()

  useEffect(() => {
    loadConfig()
  }, [])

  const loadConfig = async () => {
    setLoading(true)
    try {
      const response = await api.config.get()
      if (response.success && response.data) {
        form.setFieldsValue(response.data)
      }
    } catch (error) {
      console.error('Load config error:', error)
      message.error('加载配置失败')
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    try {
      const values = await form.validateFields()
      setSaving(true)
      const response = await api.config.update(values)
      
      if (response.success) {
        message.success('配置已保存')
      } else {
        message.error(response.error || '保存配置失败')
      }
    } catch (error) {
      console.error('Save config error:', error)
      message.error('保存配置失败')
    } finally {
      setSaving(false)
    }
  }

  const handleCloseToTrayChange = async (checked: boolean) => {
    await updateSettings({ closeToTray: checked })
    message.success(`已设置为${checked ? '最小化到托盘' : '完全退出'}`)
  }

  const renderField = (groupKey: string, fieldKey: string, fieldMeta: FieldMetadata) => {
    const formFieldName = [groupKey, fieldKey]
    const labelWithInfo = (
      <span>
        {fieldMeta.label}
        <Tooltip title={`默认值: ${Array.isArray(fieldMeta.default) ? fieldMeta.default.join(', ') : fieldMeta.default}`}>
          <InfoCircleOutlined style={{ marginLeft: 4, color: '#999', fontSize: 12 }} />
        </Tooltip>
      </span>
    )

    if (fieldMeta.type === 'number') {
      return (
        <Form.Item
          key={fieldKey}
          name={formFieldName}
          label={labelWithInfo}
          help={<span style={{ fontSize: 12, color: '#999' }}>{fieldMeta.description}</span>}
        >
          <InputNumber
            style={{ width: 200 }}
            min={fieldMeta.min}
            max={fieldMeta.max}
            placeholder={`默认: ${fieldMeta.default}`}
          />
        </Form.Item>
      )
    }

    if (fieldMeta.type === 'string') {
      return (
        <Form.Item
          key={fieldKey}
          name={formFieldName}
          label={labelWithInfo}
          help={<span style={{ fontSize: 12, color: '#999' }}>{fieldMeta.description}</span>}
        >
          <Input
            style={{ width: 300 }}
            placeholder={`默认: ${fieldMeta.default}`}
          />
        </Form.Item>
      )
    }

    if (fieldMeta.type === 'array') {
      return (
        <Form.Item
          key={fieldKey}
          name={formFieldName}
          label={labelWithInfo}
          help={<span style={{ fontSize: 12, color: '#999' }}>{fieldMeta.description}</span>}
          normalize={(value: string) => {
            if (!value) return []
            return value.split(',').map((v) => parseInt(v.trim(), 10)).filter((v) => !isNaN(v))
          }}
          getValueProps={(value: number[]) => ({
            value: Array.isArray(value) ? value.join(', ') : '',
          })}
        >
          <Input
            style={{ width: 300 }}
            placeholder={`默认: ${(fieldMeta.default as number[]).join(', ')}`}
          />
        </Form.Item>
      )
    }

    return null
  }

  const renderConfigGroup = (groupKey: string) => {
    const groupMeta = CONFIG_METADATA[groupKey]
    if (!groupMeta) return null

    return (
      <Card
        key={groupKey}
        title={groupMeta.label}
        extra={<Text type="secondary" style={{ fontSize: 12 }}>{groupMeta.description}</Text>}
        style={{ marginBottom: 16 }}
      >
        {Object.entries(groupMeta.fields).map(([fieldKey, fieldMeta]) => (
          renderField(groupKey, fieldKey, fieldMeta)
        ))}
      </Card>
    )
  }

  return (
    <div className={styles.settingsPage}>
      <Card
        title="应用设置"
        style={{ marginBottom: 16 }}
      >
        <div className={styles.settingItem}>
          <div className={styles.settingInfo}>
            <Text strong>关闭窗口行为</Text>
            <Paragraph type="secondary" style={{ margin: 0, fontSize: 12 }}>
              选择关闭窗口时的行为。最小化到托盘：窗口隐藏到系统托盘，应用继续运行；完全退出：关闭所有进程并退出应用。
            </Paragraph>
          </div>
          <div className={styles.settingControl}>
            <Switch
              checked={appSettings.closeToTray}
              onChange={handleCloseToTrayChange}
              checkedChildren="托盘"
              unCheckedChildren="退出"
            />
          </div>
        </div>
      </Card>

      <Spin spinning={loading}>
        <Form form={form} layout="vertical">
          {Object.keys(CONFIG_METADATA).map((groupKey) => renderConfigGroup(groupKey))}
        </Form>

        <div style={{ marginTop: 16, display: 'flex', gap: 8 }}>
          <Button
            type="primary"
            icon={<SaveOutlined />}
            onClick={handleSave}
            loading={saving}
            size="large"
          >
            保存配置
          </Button>
          <Button
            icon={<ReloadOutlined />}
            onClick={loadConfig}
            size="large"
          >
            刷新
          </Button>
        </div>
      </Spin>
    </div>
  )
}

export default SettingsPage
