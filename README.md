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
| **策略引擎** | Python 3.11+ (one_to_two_V2) |

## 快速开始

### 环境要求

- **Node.js**: >= 18.0.0
- **Python**: >= 3.11
- **操作系统**: Windows 10/11, macOS 10.15+, Linux

### 安装步骤

```bash
# 1. 克隆项目
git clone https://github.com/your-repo/one_to_two_V3.git
cd one_to_two_V3

# 2. 安装 Node.js 依赖
npm install

# 3. 安装 Python 依赖
pip install -e ./one_to_two_V2
pip install fastapi uvicorn pydantic
```

### 启动开发模式

```bash
# 启动 Electron 开发模式（自动启动 Python API）
npm run dev
```

应用将自动启动：
- Electron 窗口：http://localhost:5173
- Python API：http://localhost:8000

## 功能模块

| 模块 | 路径 | 功能说明 |
|------|------|----------|
| **模型训练** | `/train` | 训练一进二预测模型，支持自定义训练区间 |
| **每日日报** | `/daily` | 生成每日一进二候选股票日报 |
| **滚动评估** | `/rolling` | 滚动窗口验证模型稳定性，敏感性分析 |
| **情绪回测** | `/backtest` | 情绪分层回测，验证情绪系统有效性 |
| **热力图** | `/heatmap` | 情绪×模型分数交互验证，热力图分析 |
| **缓存同步** | `/sync-cache` | 同步涨停池和指数缓存数据 |
| **报告管理** | `/reports` | 查看和管理所有 HTML 报告 |
| **定时任务** | `/scheduler` | 配置和管理定时任务 |
| **系统设置** | `/settings` | 配置参数管理 |

## 项目结构

```
one_to_two_V3/
├── electron/                # Electron 主进程
│   ├── main.ts              # 主进程入口
│   └── preload.ts           # 预加载脚本
├── src/renderer/            # React 渲染进程
│   ├── components/          # 公共组件
│   ├── pages/               # 页面组件
│   ├── services/            # API 服务
│   └── stores/              # 状态管理
├── python-api/              # Python FastAPI 后端
│   ├── main.py              # API 入口
│   ├── routes/              # API 路由
│   ├── services/            # 业务服务
│   └── models/              # 数据模型
├── one_to_two_V2/           # 策略核心引擎
│   ├── src/                 # 核心源码
│   ├── config/              # 配置文件
│   ├── data/                # 数据目录
│   └── reports/             # 报告输出
├── build/                   # 构建资源
├── scripts/                 # 构建脚本
└── release/                 # 发布输出
```

## 打包发布

### Windows

```bash
# 打包 Windows 安装包 (NSIS)
npm run build:win

# 打包 Windows 便携版
npm run build:unpack
```

输出文件：
- `release/OneToTwo-{version}-x64-win.exe` - 安装包
- `release/OneToTwo-{version}-Portable.exe` - 便携版

### macOS

```bash
npm run build:mac
```

输出文件：
- `release/OneToTwo-{version}-x64-mac.dmg`
- `release/OneToTwo-{version}-arm64-mac.dmg`

### Linux

```bash
npm run build:linux
```

输出文件：
- `release/OneToTwo-{version}-x64-linux.AppImage`
- `release/OneToTwo-{version}-x64-linux.deb`

### 全平台打包

```bash
npm run build:all
```

## 开发指南

### 常用命令

```bash
# 开发模式
npm run dev

# 构建前端
npm run build

# 类型检查
npm run typecheck

# 代码检查
npm run lint

# 预览构建结果
npm run preview
```

### API 文档

详见 [python-api/README.md](./python-api/README.md)

### 策略引擎文档

详见 [one_to_two_V2/README.md](./one_to_two_V2/README.md)

## 配置说明

### 默认配置文件

`one_to_two_V2/config/pipeline_defaults.json`

```json
{
  "production_train": {"months": 6, "cache_check_months": 6},
  "daily": {"cache_check_months": 2, "model_filename": "model_latest.joblib"},
  "emotion_backtest": {"months": 6, "window_days": 64},
  "rolling": {"train_months": 6, "test_months": 1},
  "heatmap": {"months": 1, "model_filename": "model_latest.joblib"}
}
```

### Electron 配置

`electron-builder.yml` - 打包配置

## 许可证

MIT License

---

**OneToTwo Team** © 2024
