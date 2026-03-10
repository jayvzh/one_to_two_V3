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
  Divider,
} from 'antd'
import { SaveOutlined, ReloadOutlined } from '@ant-design/icons'
import { api } from '../../services/api'
import type { ConfigData } from '../../services/types'
import styles from './Settings.module.less'

const SettingsPage: React.FC = () => {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [config, setConfig] = useState<ConfigData>({})

  useEffect(() => {
    loadConfig()
  }, [])

  const loadConfig = async () => {
    setLoading(true)
    try {
      const response = await api.config.get()
      if (response.success && response.data) {
        setConfig(response.data)
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
        setConfig(values)
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

  const renderField = (key: string, value: unknown) => {
    if (typeof value === 'boolean') {
      return (
        <Form.Item name={key} label={key} valuePropName="checked">
          <Switch />
        </Form.Item>
      )
    }
    if (typeof value === 'number') {
      return (
        <Form.Item name={key} label={key}>
          <InputNumber style={{ width: '100%' }} />
        </Form.Item>
      )
    }
    if (typeof value === 'string') {
      return (
        <Form.Item name={key} label={key}>
          <Input />
        </Form.Item>
      )
    }
    return (
      <Form.Item name={key} label={key}>
        <Input.TextArea rows={4} />
      </Form.Item>
    )
  }

  return (
    <div className={styles.settingsPage}>
      <Card
        title="系统配置"
        extra={
          <Button icon={<ReloadOutlined />} onClick={loadConfig}>
            刷新
          </Button>
        }
      >
        <Spin spinning={loading}>
          <Form form={form} layout="vertical">
            {Object.keys(config).map((key) => (
              <React.Fragment key={key}>
                {renderField(key, config[key])}
              </React.Fragment>
            ))}
          </Form>
        </Spin>

        <Divider />

        <Button
          type="primary"
          icon={<SaveOutlined />}
          onClick={handleSave}
          loading={saving}
          size="large"
        >
          保存配置
        </Button>
      </Card>
    </div>
  )
}

export default SettingsPage
