# One to Two Tool

项目终极成熟目标：构建一个概率驱动的一进二交易决策系统，能够持续学习、持续评估、持续输出稳定的候选排序，并辅助实际交易决策。

## 项目架构

```
one_to_two_V2/              # 项目根目录
├── data/                   # 【项目数据仓库】仅存放静态文件与缓存
│   ├── cache/              # 运行时缓存数据（可被程序清空）
│   │   ├── index/          # 指数数据缓存
│   │   ├── zt/             # 涨停数据缓存
│   │   ├── emotion/        # 情绪分层回测缓存
│   │   └── heatmap/        # 热力图分析缓存
│   ├── models/             # 训练好的模型文件 (.joblib + .meta.json)
│   ├── snapshots/          # 训练数据快照 (.csv)
│   └── trade_calendar.csv  # 交易日历静态数据
│
├── config/                 # 运行参数配置（可调默认值）
│   └── pipeline_defaults.json
│
├── reports/                # HTML报告输出目录
│   ├── images/             # 热力图图片
│   └── *.html              # 各类报告
│
├── src/                    # 【源代码目录】所有核心逻辑
│   ├── core/               # 策略大脑 (必须纯净)
│   │   ├── __init__.py
│   │   ├── constants.py    # 领域常量、模式验证、自定义异常类
│   │   ├── scoring.py      # 一进二计算逻辑
│   │   ├── rules.py        # 买卖/过滤规则引擎
│   │   ├── emotion.py      # 市场情绪指标计算
│   │   ├── features.py     # 特征工程
│   │   ├── label.py        # 标签生成逻辑
│   │   └── heatmap.py      # 热力图核心计算
│   │
│   ├── data/               # 数据层 (包含数据获取、缓存、列名映射等)
│   │   ├── __init__.py
│   │   ├── ak.py           # 数据获取 (akshare封装，异常处理)
│   │   ├── trade_calendar.py # 交易日历服务
│   │   ├── cache.py        # 特征缓存管理
│   │   ├── columns.py      # 列名映射与数据模式定义
│   │   ├── prepare.py      # 训练数据构建工具
│   │   └── sync_cache.py   # 缓存同步脚本
│   │
│   ├── model/              # 模型层
│   │   ├── __init__.py
│   │   ├── trainer.py      # 模型训练与预测
│   │   └── evaluator.py    # 模型评估与报告
│   │
│   ├── pipeline/           # 编排层 (只负责流程组装)
│   │   ├── __init__.py
│   │   ├── train_model.py  # 模型训练
│   │   ├── rolling.py      # 滚动训练与评估
│   │   ├── daily.py        # 每日执行流程
│   │   ├── backtest_emotion.py # 情绪分层回测
│   │   ├── heatmap.py      # 热力图分析
│   │   ├── report.py       # HTML报告生成
│   │   └── templates/      # Jinja2报告模板
│   │
│   └── utils/              # 工具层
│       ├── __init__.py
│       └── logging_config.py # 统一日志配置
│
├── app/                    # 应用入口
│   └── menu.py             # 交互式菜单脚本
├── tests/                  # 测试目录
├── run.bat                 # Windows启动器
├── pyproject.toml
├── requirements.txt
└── README.md
```

## 架构规则

### 四层单向依赖

```
pipeline → (core, data, model, utils)
model    → (core, utils)
data     → (core, utils)
core     → ❌ 禁止导入 data、pipeline 或任何执行I/O的模块
utils    → ❌ 禁止导入任何业务模块（core/data/model/pipeline）
```

### 各层职责

| 层级 | 职责 | 禁止事项 |
|------|------|----------|
| **Core层** | 纯净的策略大脑，只包含特征工程、标签计算、规则判断、评分等确定性计算 | 文件操作、网络请求、数据库查询 |
| **Data层** | 健壮的I/O边界，处理所有对外部系统的交互，数据清洗与格式转换 | 包含策略逻辑 |
| **Pipeline层** | 单一的编排职责，按正确顺序调用各层，传递数据 | 直接进行数据转换、特征计算或模型算法实现 |
| **Model层** | 专注的算法实现，执行模型训练/预测/评估 | 关心数据来源、特征生成方式 |
| **Utils层** | 通用工具模块，提供日志配置等基础能力 | 包含业务逻辑 |

---

## 快速开始

### 安装

```bash
pip install -e .
```

### 启动菜单 (推荐)

双击 `run.bat` 或运行以下命令启动交互式菜单：

```bash
python menu.py
```

菜单功能：
- 1-5: 默认模式快速运行
- 6: 自定义模式（指定参数）
- 7: 安装依赖（检测Python环境）

### 命令列表

| 命令 | 模块 | 说明 |
|------|------|------|
| `menu` | `app.menu` | 交互式菜单 (推荐) |
| `train` | `pipeline.train_model` | 模型训练 |
| `run-daily` | `pipeline.daily` | 每日执行流程（日报） |
| `train-rolling` | `pipeline.rolling` | 滚动训练与评估 |
| `backtest-emotion` | `pipeline.backtest_emotion` | 情绪分层回测 |
| `heatmap` | `pipeline.heatmap` | 热力图分析 |
| `sync-cache` | `data.sync_cache` | 同步缓存数据 |

---


## 可调默认配置（推荐）

现在支持通过独立配置文件统一管理各 pipeline 的默认参数：

- 配置文件：`config/pipeline_defaults.json`
- 典型可调项：
  - 生产训练默认月数、缓存检查月数
  - 每日日报默认模型文件名
  - 情绪分层回测默认月份、默认窗口天数
  - 滚动训练默认训练/测试月数、敏感性测试月数组
  - 热力图默认分析月份、默认模型文件名

示例：

```json
{
  "production_train": {"months": 6, "cache_check_months": 6},
  "daily": {"cache_check_months": 2, "model_filename": "model_latest.joblib"},
  "emotion_backtest": {"months": 6, "window_days": 64, "cache_check_months": 3},
  "rolling": {"train_months": 6, "test_months": 1, "sensitivity_train_months": [2, 3, 4, 6]},
  "heatmap": {"months": 1, "model_filename": "model_latest.joblib"}
}
```

> 建议：团队可按“稳健版/激进版”维护两份配置，切换时只替换该 JSON 文件即可。

## 详细用法

### 1. 模型训练 (train_model.py)

训练一进二预测模型。

```bash
# 使用最近6个月数据训练（默认）
python -m src.pipeline.train_model

# 指定训练月数
python -m src.pipeline.train_model --months 4

# 指定日期范围
python -m src.pipeline.train_model --start 20250801 --end 20260215
```

**输出**：
- 模型文件：`data/models/model_{start}_{end}.joblib`
- 元信息：`data/models/model_{start}_{end}.meta.json`
- 训练快照：`data/snapshots/train_{start}_{end}.csv`

---

### 2. 每日日报 (daily.py)

使用最新模型输出每日一进二候选股票日报。

```bash
# 使用最新模型输出日报
python -m src.pipeline.daily
```

**输出**：
- HTML日报：`reports/daily_report_{date}.html`

---

### 3. 滚动训练与评估 (rolling.py)

评估模型分数的可靠性，通过滚动窗口验证模型稳定性。

```bash
# 基本用法：固定6+1窗口（6个月训练 + 1个月测试）
python -m src.pipeline.rolling

# 敏感性测试（测试不同训练窗口）
python -m src.pipeline.rolling --sensitivity

# 指定日期范围
python -m src.pipeline.rolling --start 20250801 --end 20260215
```

**输出**：
- 模型评估报告：`reports/stability_report_{date}.html`
- 敏感性分析报告：`reports/sensitivity_report_{date}.html`

---

### 4. 情绪分层回测 (backtest_emotion.py)

评估情绪分数的可靠性，验证情绪系统有效性。

```bash
# 使用最近6个月自动分析（默认）
python -m src.pipeline.backtest_emotion

# 指定日期范围
python -m src.pipeline.backtest_emotion --start 20260101 --end 20260214

# 强制重新计算
python -m src.pipeline.backtest_emotion --force
```

**输出**：
- HTML报告：`reports/backtest_report_{start}_{end}.html`
- 详细数据：`data/cache/emotion/emotion_backtest_{start}_{end}.csv`
- 汇总数据：`data/cache/emotion/emotion_backtest_summary_{start}_{end}.csv`

**验证目标**：情绪分数越高，一进二成功率应越高。

---

### 5. 热力图分析 (heatmap.py)

评估情绪分数×模型分数的交互验证可靠性，验证模型在不同情绪状态下的有效性（Regime Dependence）。

```bash
# 使用最近1个月自动分析（默认）
python -m src.pipeline.heatmap

# 指定日期范围
python -m src.pipeline.heatmap --start 20260101 --end 20260214

# 指定模型文件
python -m src.pipeline.heatmap --model data/models/model_xxx.joblib

# 强制重新计算
python -m src.pipeline.heatmap --force
```

**输出**：
- HTML报告：`reports/heatmap_report_{date}.html`
- 热力图图片：`reports/images/heatmap_{date}.png`
- 历史数据：`data/cache/heatmap/heatmap_history_{start}_{end}.csv`

**验证目标**：
- 情绪有效性：情绪分数越高，成功率越高
- 模型有效性：模型分数越高，成功率越高
- 组合有效性：高情绪+高模型分 应有最高成功率

---

### 6. 缓存同步 (sync_cache.py)

手动同步涨停池和指数缓存数据。

```bash
# 同步最近14个交易日涨停池 + 最近2个月指数数据
python -m src.data.sync_cache

# 自定义参数
python -m src.data.sync_cache --zt-trade-days 14 --index-months 2 --index-symbol 000300
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--cache-root` | `data/cache` | 缓存根目录 |
| `--zt-trade-days` | `14` | 同步最近 N 个交易日 |
| `--index-months` | `2` | 同步最近 N 个月指数数据 |
| `--index-symbol` | `000300` | 指数代码 |

---

## 模块详解

### Core层 - 策略大脑

纯净的领域逻辑层，不依赖任何外部I/O。

| 模块 | 功能 | 已实现 |
|------|------|--------|
| **constants.py** | 领域常量与异常 | ✅ 业务常量（成功率阈值、连板高度阈值、情绪阈值）、`SchemaError`/`DataValidationError`/`InsufficientDataError`/`ModelNotTrainedError`/`CacheError` 异常类、`validate_required_columns()` 列验证函数 |
| **scoring.py** | 一进二计算逻辑 | ✅ `detect_first_board()` 首板检测、`calc_one_to_two()` 一进二成功率计算 |
| **emotion.py** | 市场情绪分析 | ✅ `MarketEmotionAnalyzer` 情绪评分引擎（成功率+连板高度+涨停趋势三维评分） |
| **rules.py** | 交易规则引擎 | ✅ `TradeRuleEngine` 交易决策引擎（强势/中性/弱势三档决策） |
| **features.py** | 特征工程 | ✅ `StockFeatureBuilder` 股票特征构建、`MarketFeatureBuilder` 市场特征构建 |
| **label.py** | 标签生成 | ✅ `OneToTwoLabelBuilder` 一进二标签构建器 |
| **heatmap.py** | 热力图核心 | ✅ `HeatmapCell`/`HeatmapData` 数据结构、`calc_success_matrix()` 成功率矩阵计算、`HeatmapPlotter` 热力图绑定 |

### Data层 - 数据访问

统一的数据访问层，封装所有I/O操作。

| 模块 | 功能 | 已实现 |
|------|------|--------|
| **ak.py** | 数据源封装 | ✅ `AkshareDataSource` 数据源（带重试机制）、`ZtRepository` 涨停池仓库、`IndexRepository` 指数仓库 |
| **trade_calendar.py** | 交易日历 | ✅ `TradingCalendar` 交易日历服务 |
| **cache.py** | 特征缓存 | ✅ `FeatureRepository` 特征数据缓存管理 |
| **columns.py** | 列名映射 | ✅ 涨停池/指数列名中英文映射 |
| **prepare.py** | 数据构建 | ✅ `build_training_data()` 从涨停池缓存构建训练数据 |
| **sync_cache.py** | 缓存同步 | ✅ 命令行工具，同步涨停池和指数缓存数据 |

### Model层 - 机器学习

纯粹的模型算法层，不关心数据来源。

| 模块 | 功能 | 已实现 |
|------|------|--------|
| **trainer.py** | 模型训练 | ✅ `Dataset` 数据集类、`ModelMeta` 模型元信息、`OneToTwoPredictor` 逻辑回归预测器 |
| **evaluator.py** | 模型评估 | ✅ `ModelEvaluator` 评估器（AUC、Top5/Top10晋级率、分位数分析） |

### Pipeline层 - 流程编排

组装各层组件，实现完整业务流程。

| 模块 | 功能 | 已实现 |
|------|------|--------|
| **train_model.py** | 模型训练 | ✅ 训练流程编排（数据加载→特征构建→标签生成→模型训练→快照保存） |
| **rolling.py** | 滚动训练 | ✅ `RollingTrainPipeline` 滚动训练编排（窗口生成→训练→评估→报告输出） |
| **daily.py** | 每日评分 | ✅ `DailyScorer` 每日流程编排（涨停数据获取→一进二计算→情绪分析→交易决策→模型打分→报告生成） |
| **backtest_emotion.py** | 情绪分层回测 | ✅ `EmotionLayerBacktest` 情绪分层回测（历史遍历→情绪计算→分层统计→报告生成） |
| **heatmap.py** | 热力图分析 | ✅ `HeatmapAnalyzer` 系统有效性验证（历史遍历→情绪×模型分数矩阵→热力图生成→报告输出） |
| **report.py** | 报告生成 | ✅ 结构化结果数据类、HTML报告生成函数 |

### Utils层 - 工具模块

通用工具模块，提供基础能力支持。

| 模块 | 功能 | 已实现 |
|------|------|--------|
| **logging_config.py** | 日志配置 | ✅ `setup_logging()` 日志系统配置、`get_logger()` 获取日志实例、统一日志格式 |

---

## 测试覆盖

项目包含完整的单元测试，测试覆盖率 >= 80%。

```
tests/
├── core/
│   ├── test_emotion.py      # 情绪分析测试
│   ├── test_features.py     # 特征工程测试
│   ├── test_heatmap.py      # 热力图测试
│   ├── test_label.py        # 标签生成测试
│   ├── test_rules.py        # 交易规则测试
│   └── test_scoring.py      # 一进二计算测试
└── model/
    ├── test_evaluator.py    # 模型评估测试
    └── test_trainer.py      # 模型训练测试
```

运行测试：
```bash
python -m pytest tests/ -v
```

---

## 代码质量

项目配置了代码质量检查工具：

```bash
# 运行 lint 检查
ruff check src/ tests/

# 运行类型检查
mypy src/
```

---

## 输出文件说明

### 模型文件 (data/models/)

| 文件 | 说明 |
|------|------|
| `model_{start}_{end}.joblib` | 训练好的模型文件 |
| `model_{start}_{end}.meta.json` | 模型元信息（训练区间、样本量、基础胜率、特征列表等） |

### HTML报告 (reports/)

| 文件 | 说明 |
|------|------|
| `daily_report_{date}.html` | 每日日报 |
| `backtest_report_{start}_{end}.html` | 情绪分层回测报告 |
| `heatmap_report_{date}.html` | 热力图分析报告 |
| `stability_report_{date}.html` | 滚动训练稳定性报告 |
| `sensitivity_report_{date}.html` | 敏感性分析报告 |
| `images/heatmap_{date}.png` | 热力图图片 |

### 缓存数据 (data/cache/)

| 目录 | 说明 |
|------|------|
| `zt/` | 涨停池缓存数据 |
| `index/` | 指数缓存数据 |
| `emotion/` | 情绪分层回测缓存 |
| `heatmap/` | 热力图分析缓存 |

---

## 模型元信息 (ModelMeta)

```json
{
  "train_start": "20250801",
  "train_end": "20260215",
  "sample_size": 1500,
  "base_success_rate": 0.35,
  "features": ["circ_mv", "turnover", "amount", ...],
  "model_type": "logistic_regression",
  "version": "2026-02-16"
}
```

| 字段 | 说明 |
|------|------|
| `train_start` / `train_end` | 训练数据区间 |
| `sample_size` | 训练样本数量 |
| `base_success_rate` | 基础一进二成功率 |
| `features` | 使用的特征列表 |
| `model_type` | 模型类型 |
| `version` | 模型版本号 |
