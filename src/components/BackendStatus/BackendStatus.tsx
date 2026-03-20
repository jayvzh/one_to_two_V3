import React from 'react'
import { SyncOutlined } from '@ant-design/icons'
import { useApp } from '../../stores/AppContext'
import styles from './BackendStatus.module.less'

const BackendStatus: React.FC = () => {
  const { backendStatus, checkBackendHealth } = useApp()

  const handleClick = () => {
    if (!backendStatus.checking) {
      checkBackendHealth()
    }
  }

  const getStatusText = () => {
    if (backendStatus.checking) {
      return '检测中...'
    }
    return backendStatus.connected ? '后端已连接' : '后端断开'
  }

  const getStatusDotClass = () => {
    if (backendStatus.checking) {
      return styles.checking
    }
    return backendStatus.connected ? styles.connected : styles.disconnected
  }

  return (
    <div className={styles.backendStatus} onClick={handleClick}>
      <div className={`${styles.statusDot} ${getStatusDotClass()}`} />
      <span className={styles.statusText}>{getStatusText()}</span>
      <div className={`${styles.refreshIcon} ${backendStatus.checking ? styles.spinning : ''}`}>
        <SyncOutlined />
      </div>
    </div>
  )
}

export default BackendStatus
