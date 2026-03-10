# Electron + React + Ant Design 桌面应用升级 Spec

## Why
one_to_two_V2 项目目前是一个纯命令行工具，用户需要通过命令行菜单操作，体验不够直观。升级为带 UI 界面的桌面应用可以提供更好的用户体验，让用户通过图形界面完成模型训练、日报生成、回测分析等操作，并实时查看执行进度和结果。

## What Changes
- 新增 Electron 主进程，负责窗口管理和 Python 进程调度
- 新增 React 前端应用，使用 Ant Design 构建用户界面
- 新增 IPC 通信层，实现前端与后端的数据交互
- 新增 Python API 服务层，提供 HTTP API 接口供 Electron 调用
- 保留现有 Python 核心逻辑（core、data、model、pipeline 层）
- 新增打包配置，支持 Windows 平台安装包生成

## Impact
- Affected specs: 用户交互方式从命令行变为图形界面
- Affected code: 
  - 新增 `electron/` 目录（Electron 主进程）
  - 新增 `src/renderer/` 目录（React 前端）
  - 新增 `python-api/` 目录（Python HTTP API 服务）
  - 现有 `one_to_two_V2/src/` 核心代码保持不变

## ADDED Requirements

### Requirement: Electron 主进程架构
系统 SHALL 提供 Electron 主进程，负责创建应用窗口、管理应用生命周期、调度 Python 后端进程。

#### Scenario: 应用启动
- **WHEN** 用户启动桌面应用
- **THEN** 系统创建主窗口并加载 React 前端
- **AND** 系统启动 Python API 服务进程

#### Scenario: 应用关闭
- **WHEN** 用户关闭应用窗口
- **THEN** 系统优雅关闭 Python API 服务进程
- **AND** 系统释放所有资源

### Requirement: React 前端界面
系统 SHALL 提供 React 前端界面，使用 Ant Design 组件库构建现代化的用户界面。

#### Scenario: 主界面布局
- **WHEN** 用户打开应用
- **THEN** 系统显示左侧导航菜单和右侧内容区域
- **AND** 导航菜单包含：模型训练、每日日报、滚动训练、情绪回测、热力图分析、缓存同步、计划任务、设置等功能入口

#### Scenario: 模型训练界面
- **WHEN** 用户进入模型训练页面
- **THEN** 系统显示训练参数配置表单（训练月数、日期范围）
- **AND** 系统提供"开始训练"按钮
- **AND** 系统显示训练进度和日志输出

#### Scenario: 每日日报界面
- **WHEN** 用户进入每日日报页面
- **THEN** 系统显示日报生成按钮和进度
- **AND** 系统生成完成后显示日报预览或打开报告链接

#### Scenario: 参数配置界面
- **WHEN** 用户进入设置页面
- **THEN** 系统显示 pipeline_defaults.json 的可编辑配置项
- **AND** 系统提供保存配置功能

### Requirement: Python API 服务层
系统 SHALL 提供 Python HTTP API 服务，封装现有 pipeline 功能供前端调用。

#### Scenario: API 接口设计
- **WHEN** 前端发起 API 请求
- **THEN** 系统提供以下 RESTful 接口：
  - `POST /api/train` - 模型训练
  - `POST /api/daily` - 生成每日日报
  - `POST /api/rolling` - 滚动训练评估
  - `POST /api/backtest-emotion` - 情绪分层回测
  - `POST /api/heatmap` - 热力图分析
  - `POST /api/sync-cache` - 同步缓存数据
  - `GET /api/models` - 获取模型列表
  - `GET /api/reports` - 获取报告列表
  - `GET /api/config` - 获取配置
  - `PUT /api/config` - 更新配置
  - `GET /api/scheduler/status` - 获取计划任务状态
  - `POST /api/scheduler/install` - 安装计划任务
  - `POST /api/scheduler/uninstall` - 卸载计划任务

#### Scenario: 异步任务执行
- **WHEN** 用户执行耗时操作（如模型训练）
- **THEN** 系统异步执行任务并返回任务 ID
- **AND** 前端可通过任务 ID 查询执行进度和日志

### Requirement: 实时日志输出
系统 SHALL 提供实时日志输出功能，让用户能够查看执行过程的详细信息。

#### Scenario: 日志流输出
- **WHEN** 用户执行任何 pipeline 操作
- **THEN** 系统实时推送日志到前端界面
- **AND** 日志支持不同级别的颜色区分（INFO/WARNING/ERROR）

### Requirement: 报告管理
系统 SHALL 提供报告管理功能，让用户能够查看和打开生成的报告。

#### Scenario: 报告列表
- **WHEN** 用户进入报告管理页面
- **THEN** 系统显示 reports 目录下的所有 HTML 报告
- **AND** 用户可以点击报告在浏览器中打开

### Requirement: 打包发布
系统 SHALL 支持打包为 Windows 安装包，方便用户安装使用。

#### Scenario: 安装包生成
- **WHEN** 执行打包命令
- **THEN** 系统生成 Windows 安装包（.exe 或 .msi）
- **AND** 安装包包含 Python 运行时和所有依赖

## MODIFIED Requirements
无修改的需求。

## REMOVED Requirements
无移除的需求。
