import React, { useState, useEffect } from 'react'
import {
  Card,
  Table,
  Button,
  Space,
  message,
  Tag,
  Popconfirm,
} from 'antd'
import {
  FolderOpenOutlined,
  DeleteOutlined,
  ReloadOutlined,
  FileTextOutlined,
} from '@ant-design/icons'
import { api } from '../../services/api'
import type { ReportInfo } from '../../services/types'
import styles from './Reports.module.less'

const ReportsPage: React.FC = () => {
  const [reports, setReports] = useState<ReportInfo[]>([])
  const [loading, setLoading] = useState(false)
  const [openingId, setOpeningId] = useState<string | null>(null)

  useEffect(() => {
    loadReports()
  }, [])

  const loadReports = async () => {
    setLoading(true)
    try {
      const response = await api.reports.list()
      if (response.success && response.data) {
        setReports(response.data)
      }
    } catch (error) {
      console.error('Load reports error:', error)
      message.error('加载报告列表失败')
    } finally {
      setLoading(false)
    }
  }

  const handleOpen = async (report: ReportInfo) => {
    setOpeningId(report.id)
    try {
      const response = api.reports.open(report.id)
      if (response.success && response.data) {
        window.open(response.data.url, '_blank')
      }
    } catch (error) {
      console.error('Open report error:', error)
      message.error('打开报告失败')
    } finally {
      setOpeningId(null)
    }
  }

  const handleDelete = async (reportId: string) => {
    try {
      const response = await api.reports.delete(reportId)
      if (response.success) {
        message.success('报告已删除')
        loadReports()
      } else {
        message.error(response.error || '删除报告失败')
      }
    } catch (error) {
      console.error('Delete report error:', error)
      message.error('删除报告失败')
    }
  }

  const formatSize = (bytes?: number) => {
    if (!bytes) return '-'
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
  }

  const columns = [
    {
      title: '报告名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string) => (
        <Space>
          <FileTextOutlined />
          {name}
        </Space>
      ),
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      render: (type: string) => <Tag color="blue">{type}</Tag>,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
    },
    {
      title: '大小',
      dataIndex: 'size',
      key: 'size',
      width: 100,
      render: (size: number) => formatSize(size),
    },
    {
      title: '操作',
      key: 'action',
      width: 180,
      render: (_: unknown, record: ReportInfo) => (
        <Space>
          <Button
            type="link"
            icon={<FolderOpenOutlined />}
            onClick={() => handleOpen(record)}
            loading={openingId === record.id}
          >
            打开
          </Button>
          <Popconfirm
            title="确定要删除此报告吗？"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button type="link" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div className={styles.reportsPage}>
      <Card
        title="报告管理"
        extra={
          <Button icon={<ReloadOutlined />} onClick={loadReports}>
            刷新
          </Button>
        }
      >
        <Table
          columns={columns}
          dataSource={reports}
          rowKey="id"
          loading={loading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`,
          }}
        />
      </Card>
    </div>
  )
}

export default ReportsPage
