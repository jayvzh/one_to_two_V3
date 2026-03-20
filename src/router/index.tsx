import React from 'react'
import { createHashRouter, Navigate } from 'react-router-dom'
import { MainLayout } from '../components/Layout'

const TrainPage = React.lazy(() => import('../pages/Train'))
const DailyPage = React.lazy(() => import('../pages/Daily'))
const RollingPage = React.lazy(() => import('../pages/Rolling'))
const BacktestPage = React.lazy(() => import('../pages/Backtest'))
const HeatmapPage = React.lazy(() => import('../pages/Heatmap'))
const SyncCachePage = React.lazy(() => import('../pages/SyncCache'))
const SchedulerPage = React.lazy(() => import('../pages/Scheduler'))
const SettingsPage = React.lazy(() => import('../pages/Settings'))
const ReportsPage = React.lazy(() => import('../pages/Reports'))

const LazyLoad = ({ children }: { children: React.ReactNode }) => (
  <React.Suspense
    fallback={
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
        加载中...
      </div>
    }
  >
    {children}
  </React.Suspense>
)

export const router = createHashRouter([
  {
    path: '/',
    element: <MainLayout />,
    children: [
      {
        index: true,
        element: <Navigate to="/train" replace />,
      },
      {
        path: 'train',
        element: (
          <LazyLoad>
            <TrainPage />
          </LazyLoad>
        ),
      },
      {
        path: 'daily',
        element: (
          <LazyLoad>
            <DailyPage />
          </LazyLoad>
        ),
      },
      {
        path: 'rolling',
        element: (
          <LazyLoad>
            <RollingPage />
          </LazyLoad>
        ),
      },
      {
        path: 'backtest',
        element: (
          <LazyLoad>
            <BacktestPage />
          </LazyLoad>
        ),
      },
      {
        path: 'heatmap',
        element: (
          <LazyLoad>
            <HeatmapPage />
          </LazyLoad>
        ),
      },
      {
        path: 'sync-cache',
        element: (
          <LazyLoad>
            <SyncCachePage />
          </LazyLoad>
        ),
      },
      {
        path: 'scheduler',
        element: (
          <LazyLoad>
            <SchedulerPage />
          </LazyLoad>
        ),
      },
      {
        path: 'settings',
        element: (
          <LazyLoad>
            <SettingsPage />
          </LazyLoad>
        ),
      },
      {
        path: 'reports',
        element: (
          <LazyLoad>
            <ReportsPage />
          </LazyLoad>
        ),
      },
    ],
  },
])
