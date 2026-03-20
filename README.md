# OneToTwo V3 - 一进二策略分析系统

一进二策略分析系统桌面应用，基于 Electron + React + Vite + TypeScript 构建，集成 Python 后端策略引擎。

## 技术栈

| 层级 | 技术 |
|------|------|
| **桌面框架** | Electron 33 |
| **前端框架** | React 18 + TypeScript |
| **构建工具** | Vite 5 + electron-vite |
| **UI 组件** | Ant Design 5 |
| **路由** | React Router 7 |
| **后端 API** | FastAPI + Uvicorn |
| **策略引擎** | Python 3.11+ |

## 环境要求

- **Node.js**: >= 18.0.0
- **Python**: >= 3.11
- **操作系统**: Windows 10/11, macOS 10.15+, Linux

## 快速开始

### 安装

```bash
# 安装 Node.js 依赖
npm install

# 安装 Python 依赖
pip install -e .
pip install fastapi uvicorn pydantic
```

### 开发模式

```bash
npm run dev
```

应用将自动启动：
- Electron 窗口：http://localhost:5173
- Python API：http://localhost:8000

## 功能模块

| 模块 | 路径 | 功能说明 |
|------|------|----------|
| **模型训练** | `/train` | 训练一进二预测模型 |
| **每日日报** | `/daily` | 生成每日候选股票日报 |
| **滚动评估** | `/rolling` | 滚动窗口验证模型稳定性 |
| **情绪回测** | `/backtest` | 情绪分层回测分析 |
| **热力图** | `/heatmap` | 情绪×模型分数热力图 |
| **缓存同步** | `/sync-cache` | 同步涨停池和指数数据 |
| **报告管理** | `/reports` | 查看 HTML 报告 |
| **定时任务** | `/scheduler` | 配置定时任务 |
| **系统设置** | `/settings` | 配置参数管理 |

## 项目结构

```
one_to_two_V3/
├── electron/                # Electron 主进程
│   ├── main.ts              # 主进程入口
│   └── preload.ts           # 预加载脚本
├── src/                     # React 前端源码
│   ├── components/          # 公共组件
│   ├── pages/               # 页面组件
│   ├── services/            # API 服务
│   ├── stores/              # 状态管理
│   ├── router/              # 路由配置
│   ├── types/               # 类型定义
│   ├── App.tsx              # 主应用组件
│   └── main.tsx             # 入口文件
├── index.html               # HTML 入口
├── python-api/              # Python FastAPI 后端（集中目录）
│   ├── main.py              # API 入口
│   ├── pipeline_defaults.json  # 管道默认配置
│   ├── routes/              # API 路由
│   ├── services/            # 业务服务
│   ├── schemas/             # API 数据模型
│   ├── ml/                  # 机器学习模块
│   ├── core/                # 核心算法模块
│   ├── data/                # 数据处理模块
│   ├── pipeline/            # 流水线模块
│   ├── scripts/             # Python 脚本
│   ├── tests/               # 测试代码
│   └── datasets/            # 数据目录
├── reports/                 # 报告输出
├── build/                   # 构建资源
├── scripts/                 # 构建脚本
└── release/                 # 发布输出
```

## 打包发布

### 打包前准备

```bash
# 激活目标 Python 环境
conda activate <env-name>

# 确保 pyinstaller 已安装
pip install pyinstaller
```

### Windows 打包

```bash
# 完整打包（包含 Python API）
npm run build:win

# 快速打包（不打包 Python API，用于测试）
npm run build:win:quick
```

输出文件：
- `release/OneToTwo-{version}-Setup-x64.exe` - 安装包

### macOS / Linux

```bash
npm run build:mac
npm run build:linux
```

## 常用命令

```bash
npm run dev          # 开发模式
npm run build        # 构建前端
npm run build:python-exe  # 打包 Python API
npm run typecheck    # 类型检查
npm run lint         # 代码检查
npm run preview      # 预览构建结果
```

## 配置说明

- `electron-builder.yml` - 打包配置
- `config/pipeline_defaults.json` - 策略默认配置

## 许可证

MIT License

---

**OneToTwo Team** © 2024
