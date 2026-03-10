# OneToTwo API 文档

一进二策略分析系统 RESTful API，基于 FastAPI 构建。

## 基础信息

- **Base URL**: `http://localhost:8000`
- **API 前缀**: `/api`
- **文档地址**: `http://localhost:8000/docs` (Swagger UI)
- **OpenAPI 规范**: `http://localhost:8000/openapi.json`

## 通用响应格式

### 成功响应

```json
{
  "success": true,
  "data": { ... },
  "message": "操作成功"
}
```

### 错误响应

```json
{
  "success": false,
  "error": "错误类型",
  "detail": "详细错误信息"
}
```

---

## API 接口

### 1. 系统状态

#### GET `/` - API 信息

获取 API 基本信息。

**响应示例**:

```json
{
  "name": "OneToTwo API",
  "version": "1.0.0",
  "status": "running"
}
```

#### GET `/health` - 健康检查

**响应示例**:

```json
{
  "status": "healthy"
}
```

---

### 2. Pipeline 接口

#### POST `/api/train` - 模型训练

启动模型训练任务。

**请求体**:

```json
{
  "months": 6,
  "start": "20250801",
  "end": "20260215"
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| months | int | 否 | 训练月数，默认 6 |
| start | string | 否 | 开始日期 (YYYYMMDD) |
| end | string | 否 | 结束日期 (YYYYMMDD) |

**响应示例**:

```json
{
  "success": true,
  "task_id": "task_a1b2c3d4",
  "message": "训练任务已创建"
}
```

---

#### POST `/api/daily` - 生成每日日报

**请求体**:

```json
{
  "date": "20260306"
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| date | string | 否 | 日期 (YYYYMMDD)，默认今天 |

**响应示例**:

```json
{
  "success": true,
  "task_id": "task_e5f6g7h8",
  "message": "日报任务已创建"
}
```

---

#### POST `/api/rolling` - 滚动评估

**请求体**:

```json
{
  "start": "20250801",
  "end": "20260215",
  "sensitivity": true
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| start | string | 否 | 开始日期 |
| end | string | 否 | 结束日期 |
| sensitivity | bool | 否 | 是否进行敏感性分析，默认 false |

**响应示例**:

```json
{
  "success": true,
  "task_id": "task_i9j0k1l2",
  "message": "滚动评估任务已创建"
}
```

---

#### POST `/api/backtest-emotion` - 情绪分层回测

**请求体**:

```json
{
  "start": "20260101",
  "end": "20260214",
  "months": 6
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| start | string | 否 | 开始日期 |
| end | string | 否 | 结束日期 |
| months | int | 否 | 回测月数，默认 6 |

**响应示例**:

```json
{
  "success": true,
  "task_id": "task_m3n4o5p6",
  "message": "回测任务已创建"
}
```

---

#### POST `/api/heatmap` - 热力图分析

**请求体**:

```json
{
  "start": "20260101",
  "end": "20260214",
  "model": "model_latest.joblib"
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| start | string | 否 | 开始日期 |
| end | string | 否 | 结束日期 |
| model | string | 否 | 模型文件名 |

**响应示例**:

```json
{
  "success": true,
  "task_id": "task_q7r8s9t0",
  "message": "热力图分析任务已创建"
}
```

---

#### POST `/api/sync-cache` - 缓存同步

**请求体**:

```json
{
  "zt_trade_days": 14,
  "index_months": 2
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| zt_trade_days | int | 否 | 同步涨停池天数，默认 14 |
| index_months | int | 否 | 同步指数月数，默认 2 |

**响应示例**:

```json
{
  "success": true,
  "task_id": "task_u1v2w3x4",
  "message": "缓存同步任务已创建"
}
```

---

### 3. 任务管理接口

#### GET `/api/tasks` - 任务列表

获取所有任务列表。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| task_type | string | 否 | 任务类型筛选 |

**响应示例**:

```json
{
  "success": true,
  "data": [
    {
      "task_id": "task_a1b2c3d4",
      "task_type": "train",
      "state": "completed",
      "created_at": "2026-03-06T10:30:00"
    }
  ],
  "total": 1
}
```

---

#### GET `/api/tasks/{task_id}` - 任务详情

获取指定任务的详细信息。

**响应示例**:

```json
{
  "success": true,
  "data": {
    "task_id": "task_a1b2c3d4",
    "task_type": "train",
    "state": "completed",
    "progress": 1.0,
    "message": "训练完成",
    "result": {
      "model_path": "data/models/model_20250801_20260215.joblib",
      "sample_size": 1500,
      "base_success_rate": 0.35
    },
    "created_at": "2026-03-06T10:30:00",
    "started_at": "2026-03-06T10:30:01",
    "completed_at": "2026-03-06T10:35:00",
    "logs": [
      "[2026-03-06T10:30:01] 开始训练",
      "[2026-03-06T10:35:00] 训练完成"
    ]
  }
}
```

**任务状态**:

| 状态 | 说明 |
|------|------|
| pending | 等待执行 |
| running | 执行中 |
| completed | 已完成 |
| failed | 执行失败 |
| cancelled | 已取消 |

---

#### GET `/api/tasks/{task_id}/logs` - 任务日志

获取任务的执行日志。

**响应示例**:

```json
{
  "success": true,
  "data": [
    "[2026-03-06T10:30:01] 开始训练",
    "[2026-03-06T10:30:05] 加载训练数据...",
    "[2026-03-06T10:35:00] 训练完成"
  ]
}
```

---

#### DELETE `/api/tasks/completed` - 清理已完成任务

清理所有已完成、失败或取消的任务。

**响应示例**:

```json
{
  "success": true,
  "message": "已清理 5 个已完成任务"
}
```

---

### 4. 模型接口

#### GET `/api/models` - 模型列表

获取所有已训练的模型列表。

**响应示例**:

```json
{
  "success": true,
  "data": [
    {
      "filename": "model_latest.joblib",
      "meta": {
        "train_start": "20250801",
        "train_end": "20260215",
        "sample_size": 1500,
        "base_success_rate": 0.35,
        "features": ["circ_mv", "turnover", "amount"],
        "model_type": "logistic_regression",
        "version": "2026-02-16"
      },
      "created_at": "2026-02-16T10:00:00",
      "size_kb": 256
    }
  ],
  "total": 1
}
```

---

### 5. 报告接口

#### GET `/api/reports` - 报告列表

获取所有 HTML 报告列表。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| type | string | 否 | 报告类型: daily, backtest, heatmap, stability, sensitivity |

**响应示例**:

```json
{
  "success": true,
  "data": [
    {
      "filename": "daily_report_20260306.html",
      "type": "daily",
      "size_kb": 128,
      "created_at": "2026-03-06T18:00:00",
      "url": "/reports/daily_report_20260306.html"
    }
  ],
  "total": 1
}
```

---

#### GET `/api/reports/{filename}` - 报告内容

获取指定报告的 HTML 内容。

**响应示例**:

```json
{
  "success": true,
  "filename": "daily_report_20260306.html",
  "content": "<!DOCTYPE html>..."
}
```

---

#### DELETE `/api/reports/{filename}` - 删除报告

删除指定报告。

**响应示例**:

```json
{
  "success": true,
  "message": "报告 daily_report_20260306.html 已删除"
}
```

---

#### GET `/api/images` - 图片列表

获取所有报告图片列表。

**响应示例**:

```json
{
  "success": true,
  "data": [
    {
      "filename": "heatmap_20260306.png",
      "size_kb": 64,
      "created_at": "2026-03-06T18:00:00",
      "url": "/images/heatmap_20260306.png"
    }
  ],
  "total": 1
}
```

---

### 6. 配置接口

#### GET `/api/config` - 获取全部配置

**响应示例**:

```json
{
  "success": true,
  "data": {
    "production_train": {"months": 6, "cache_check_months": 6},
    "daily": {"cache_check_months": 2, "model_filename": "model_latest.joblib"},
    "emotion_backtest": {"months": 6, "window_days": 64},
    "rolling": {"train_months": 6, "test_months": 1},
    "heatmap": {"months": 1, "model_filename": "model_latest.joblib"}
  }
}
```

---

#### PUT `/api/config` - 更新配置

**请求体**:

```json
{
  "production_train": {"months": 4},
  "daily": {"model_filename": "model_custom.joblib"}
}
```

**响应示例**:

```json
{
  "success": true,
  "data": { ... },
  "message": "配置已更新"
}
```

---

#### GET `/api/config/{section}` - 获取配置项

获取指定配置项。

**响应示例**:

```json
{
  "success": true,
  "data": {
    "months": 6,
    "cache_check_months": 6
  }
}
```

---

#### PUT `/api/config/{section}` - 更新配置项

更新指定配置项。

**请求体**:

```json
{
  "months": 4,
  "cache_check_months": 3
}
```

**响应示例**:

```json
{
  "success": true,
  "data": {"months": 4, "cache_check_months": 3},
  "message": "配置项 production_train 已更新"
}
```

---

### 7. 定时任务接口

#### GET `/api/scheduler/status` - 定时任务状态

**响应示例**:

```json
{
  "success": true,
  "data": {
    "installed": true,
    "tasks": [
      {
        "name": "daily_report",
        "schedule": "0 18 * * 1-5",
        "next_run": "2026-03-07T18:00:00"
      }
    ]
  }
}
```

---

#### POST `/api/scheduler/install` - 安装定时任务

安装系统定时任务。

**响应示例**:

```json
{
  "success": true,
  "message": "定时任务已安装"
}
```

---

#### POST `/api/scheduler/uninstall` - 卸载定时任务

卸载系统定时任务。

**响应示例**:

```json
{
  "success": true,
  "message": "定时任务已卸载"
}
```

---

## 静态文件服务

### 报告文件

- **URL**: `http://localhost:8000/reports/{filename}`
- **说明**: 直接访问 HTML 报告文件

### 图片文件

- **URL**: `http://localhost:8000/images/{filename}`
- **说明**: 直接访问报告图片

---

## 错误码

| HTTP 状态码 | 说明 |
|-------------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

---

## 开发说明

### 启动开发服务器

```bash
cd python-api
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 依赖

- fastapi
- uvicorn
- pydantic
