import React, { useState, useEffect } from 'react'
import {
  Card,
  Form,
  InputNumber,
  Button,
  message,
  Divider,
  Descriptions,
  Space,
  Spin,
  Empty,
} from 'antd'
import { PlayCircleOutlined, DownloadOutlined, UploadOutlined, ReloadOutlined } from '@ant-design/icons'
import { api } from '../../services/api'
import { useTaskPolling } from '../../stores'
import LogViewer from '../../components/LogViewer'
import TaskStatus from '../../components/TaskStatus'
import type { SyncCacheParams, CacheStatus } from '../../services/types'
import styles from './SyncCache.module.less'

const SyncCachePage: React.FC = () => {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [cacheStatus, setCacheStatus] = useState<CacheStatus | null>(null)
  const [statusLoading, setStatusLoading] = useState(true)
  const [exportLoading, setExportLoading] = useState(false)
  const [importLoading, setImportLoading] = useState(false)
  const { currentTask, startPolling } = useTaskPolling()

  const fetchCacheStatus = async () => {
    setStatusLoading(true)
    const response = await api.cache.getStatus()
    if (response.success && response.data) {
      setCacheStatus(response.data)
    } else {
      message.error(response.error || '获取缓存状态失败')
    }
    setStatusLoading(false)
  }

  useEffect(() => {
    fetchCacheStatus()
  }, [])

  useEffect(() => {
    if (currentTask.status?.state === 'completed') {
      fetchCacheStatus()
    }
  }, [currentTask.status?.state])

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

  const handleExport = async () => {
    setExportLoading(true)
    try {
      const response = await api.cache.export()
      if (response.success) {
        message.success('缓存导出成功')
      } else {
        if (response.error !== 'Cancelled') {
          message.error(response.error || '导出失败')
        }
      }
    } catch (error) {
      console.error('Export cache error:', error)
      message.error('导出失败')
    } finally {
      setExportLoading(false)
    }
  }

  const handleImport = async () => {
    setImportLoading(true)
    try {
      const response = await api.cache.import()
      if (response.success && response.data) {
        message.success(response.data.message)
        fetchCacheStatus()
      } else {
        if (response.error !== 'Cancelled') {
          message.error(response.error || '导入失败')
        }
      }
    } catch (error) {
      console.error('Import cache error:', error)
      message.error('导入失败')
    } finally {
      setImportLoading(false)
    }
  }

  const formatDate = (date: string | null) => {
    if (!date) return '-'
    return `${date.slice(0, 4)}-${date.slice(4, 6)}-${date.slice(6, 8)}`
  }

  return (
    <div className={styles.syncCachePage}>
      <Card
        title="缓存状态"
        className={styles.configCard}
        extra={
          <Button
            icon={<ReloadOutlined />}
            onClick={fetchCacheStatus}
            loading={statusLoading}
          >
            刷新
          </Button>
        }
      >
        {statusLoading ? (
          <Spin />
        ) : cacheStatus ? (
          <Descriptions column={2} bordered size="small">
            <Descriptions.Item label="涨停池缓存">
              {cacheStatus.zt_cache.available ? (
                <span>
                  {formatDate(cacheStatus.zt_cache.start_date)} ~ {formatDate(cacheStatus.zt_cache.end_date)}
                  <span style={{ color: '#888', marginLeft: 8 }}>
                    ({cacheStatus.zt_cache.count} 天)
                  </span>
                </span>
              ) : (
                <span style={{ color: '#999' }}>无数据</span>
              )}
            </Descriptions.Item>
            <Descriptions.Item label="指数缓存">
              {cacheStatus.index_cache.available ? (
                <span>
                  {formatDate(cacheStatus.index_cache.start_date)} ~ {formatDate(cacheStatus.index_cache.end_date)}
                  <span style={{ color: '#888', marginLeft: 8 }}>
                    ({cacheStatus.index_cache.count} 条)
                  </span>
                </span>
              ) : (
                <span style={{ color: '#999' }}>无数据</span>
              )}
            </Descriptions.Item>
            <Descriptions.Item label="缓存目录" span={2}>
              <code style={{ fontSize: 12 }}>{cacheStatus.cache_dir}</code>
            </Descriptions.Item>
          </Descriptions>
        ) : (
          <Empty description="无法获取缓存状态" />
        )}
      </Card>

      <Card title="缓存管理" className={styles.configCard}>
        <Space>
          <Button
            icon={<DownloadOutlined />}
            onClick={handleExport}
            loading={exportLoading}
            disabled={!cacheStatus?.zt_cache.available && !cacheStatus?.index_cache.available}
          >
            导出缓存
          </Button>
          <Button
            icon={<UploadOutlined />}
            onClick={handleImport}
            loading={importLoading}
          >
            导入缓存
          </Button>
        </Space>
      </Card>

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
