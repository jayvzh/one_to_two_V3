import React, { useState } from 'react'
import { Layout, Menu, theme } from 'antd'
import {
  RocketOutlined,
  FileTextOutlined,
  SyncOutlined,
  LineChartOutlined,
  HeatMapOutlined,
  CloudSyncOutlined,
  ScheduleOutlined,
  SettingOutlined,
  FolderOutlined,
} from '@ant-design/icons'
import { useNavigate, useLocation, Outlet } from 'react-router-dom'
import BackendStatus from '../BackendStatus'
import styles from './MainLayout.module.less'

const { Header, Content, Sider } = Layout

const menuItems = [
  {
    key: '/train',
    icon: <RocketOutlined />,
    label: '模型训练',
  },
  {
    key: '/daily',
    icon: <FileTextOutlined />,
    label: '每日日报',
  },
  {
    key: '/rolling',
    icon: <SyncOutlined />,
    label: '滚动训练',
  },
  {
    key: '/backtest',
    icon: <LineChartOutlined />,
    label: '情绪回测',
  },
  {
    key: '/heatmap',
    icon: <HeatMapOutlined />,
    label: '热力图分析',
  },
  {
    key: '/sync-cache',
    icon: <CloudSyncOutlined />,
    label: '缓存同步',
  },
  {
    key: '/scheduler',
    icon: <ScheduleOutlined />,
    label: '计划任务',
  },
  {
    key: '/settings',
    icon: <SettingOutlined />,
    label: '设置',
  },
  {
    key: '/reports',
    icon: <FolderOutlined />,
    label: '报告管理',
  },
]

const MainLayout: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const {
    token: { colorBgContainer, borderRadiusLG },
  } = theme.useToken()

  const handleMenuClick = ({ key }: { key: string }) => {
    navigate(key)
  }

  return (
    <Layout className={styles.layout}>
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        theme="light"
        className={styles.sider}
      >
        <div className={styles.logo}>
          <span className={styles.logoText}>
            {collapsed ? 'V3' : 'OneToTwo V3'}
          </span>
        </div>
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={handleMenuClick}
        />
      </Sider>
      <Layout>
        <Header className={styles.header} style={{ background: colorBgContainer }}>
          <div className={styles.headerContent}>
            <h2 className={styles.title}>
              {menuItems.find((item) => item.key === location.pathname)?.label || 'OneToTwo V3'}
            </h2>
            <BackendStatus />
          </div>
        </Header>
        <Content className={styles.content}>
          <div
            className={styles.contentWrapper}
            style={{
              background: colorBgContainer,
              borderRadius: borderRadiusLG,
            }}
          >
            <Outlet />
          </div>
        </Content>
      </Layout>
    </Layout>
  )
}

export default MainLayout
