from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import asyncio
import tempfile
import os

from services import PipelineService
from services.file_service import FileService
from schemas.tasks import TaskManager, TaskState

router = APIRouter()
task_manager = TaskManager()
pipeline_service = PipelineService()
file_service = FileService()


class TrainRequest(BaseModel):
    months: Optional[int] = None
    start: Optional[str] = None
    end: Optional[str] = None


class DailyRequest(BaseModel):
    date: Optional[str] = None


class RollingRequest(BaseModel):
    start: Optional[str] = None
    end: Optional[str] = None
    sensitivity: Optional[bool] = False


class BacktestRequest(BaseModel):
    start: Optional[str] = None
    end: Optional[str] = None
    months: Optional[int] = None


class HeatmapRequest(BaseModel):
    start: Optional[str] = None
    end: Optional[str] = None
    model: Optional[str] = None


class SyncRequest(BaseModel):
    zt_trade_days: Optional[int] = 14
    index_months: Optional[int] = 2


def run_train_task(task_id: str, request: TrainRequest):
    task = task_manager.get_task(task_id)
    if not task:
        return
    
    def log_callback(msg: str):
        task_manager.update_task(task_id, log=msg, message=msg)
    
    try:
        task_manager.update_task(task_id, state=TaskState.RUNNING, message="开始训练")
        
        result = asyncio.run(pipeline_service.train_model(
            months=request.months,
            start_date=request.start,
            end_date=request.end,
            log_callback=log_callback,
        ))
        
        task_manager.update_task(
            task_id,
            state=TaskState.COMPLETED,
            progress=1.0,
            result=result,
            message="训练完成",
        )
    except Exception as e:
        task_manager.update_task(
            task_id,
            state=TaskState.FAILED,
            error=str(e),
            message=f"训练失败: {e}",
        )


def run_daily_task(task_id: str, request: DailyRequest):
    task = task_manager.get_task(task_id)
    if not task:
        return
    
    def log_callback(msg: str):
        task_manager.update_task(task_id, log=msg, message=msg)
    
    try:
        task_manager.update_task(task_id, state=TaskState.RUNNING, message="开始生成日报")
        
        result = asyncio.run(pipeline_service.generate_daily_report(
            date=request.date,
            log_callback=log_callback,
        ))
        
        task_manager.update_task(
            task_id,
            state=TaskState.COMPLETED,
            progress=1.0,
            result=result,
            message="日报生成完成",
        )
    except Exception as e:
        task_manager.update_task(
            task_id,
            state=TaskState.FAILED,
            error=str(e),
            message=f"日报生成失败: {e}",
        )


def run_rolling_task(task_id: str, request: RollingRequest):
    task = task_manager.get_task(task_id)
    if not task:
        return
    
    def log_callback(msg: str):
        task_manager.update_task(task_id, log=msg, message=msg)
    
    try:
        task_manager.update_task(task_id, state=TaskState.RUNNING, message="开始滚动评估")
        
        result = asyncio.run(pipeline_service.run_rolling_evaluation(
            start_date=request.start,
            end_date=request.end,
            sensitivity=request.sensitivity,
            log_callback=log_callback,
        ))
        
        task_manager.update_task(
            task_id,
            state=TaskState.COMPLETED,
            progress=1.0,
            result=result,
            message="滚动评估完成",
        )
    except Exception as e:
        task_manager.update_task(
            task_id,
            state=TaskState.FAILED,
            error=str(e),
            message=f"滚动评估失败: {e}",
        )


def run_backtest_task(task_id: str, request: BacktestRequest):
    task = task_manager.get_task(task_id)
    if not task:
        return
    
    def log_callback(msg: str):
        task_manager.update_task(task_id, log=msg, message=msg)
    
    try:
        task_manager.update_task(task_id, state=TaskState.RUNNING, message="开始情绪分层回测")
        
        result = asyncio.run(pipeline_service.run_backtest_emotion(
            start_date=request.start,
            end_date=request.end,
            months=request.months,
            log_callback=log_callback,
        ))
        
        task_manager.update_task(
            task_id,
            state=TaskState.COMPLETED,
            progress=1.0,
            result=result,
            message="回测完成",
        )
    except Exception as e:
        task_manager.update_task(
            task_id,
            state=TaskState.FAILED,
            error=str(e),
            message=f"回测失败: {e}",
        )


def run_heatmap_task(task_id: str, request: HeatmapRequest):
    task = task_manager.get_task(task_id)
    if not task:
        return
    
    def log_callback(msg: str):
        task_manager.update_task(task_id, log=msg, message=msg)
    
    try:
        task_manager.update_task(task_id, state=TaskState.RUNNING, message="开始热力图分析")
        
        result = asyncio.run(pipeline_service.run_heatmap_analysis(
            start_date=request.start,
            end_date=request.end,
            model=request.model,
            log_callback=log_callback,
        ))
        
        task_manager.update_task(
            task_id,
            state=TaskState.COMPLETED,
            progress=1.0,
            result=result,
            message="热力图分析完成",
        )
    except Exception as e:
        task_manager.update_task(
            task_id,
            state=TaskState.FAILED,
            error=str(e),
            message=f"热力图分析失败: {e}",
        )


def run_sync_task(task_id: str, request: SyncRequest):
    task = task_manager.get_task(task_id)
    if not task:
        return
    
    def log_callback(msg: str):
        task_manager.update_task(task_id, log=msg, message=msg)
    
    try:
        task_manager.update_task(task_id, state=TaskState.RUNNING, message="开始同步缓存")
        
        result = asyncio.run(pipeline_service.sync_cache(
            zt_trade_days=request.zt_trade_days,
            index_months=request.index_months,
            log_callback=log_callback,
        ))
        
        task_manager.update_task(
            task_id,
            state=TaskState.COMPLETED,
            progress=1.0,
            result=result,
            message="缓存同步完成",
        )
    except Exception as e:
        task_manager.update_task(
            task_id,
            state=TaskState.FAILED,
            error=str(e),
            message=f"缓存同步失败: {e}",
        )


@router.post("/train")
async def train_model(request: TrainRequest, background_tasks: BackgroundTasks):
    task = task_manager.create_task("train")
    background_tasks.add_task(run_train_task, task.task_id, request)
    return {"success": True, "task_id": task.task_id, "message": "训练任务已创建"}


@router.post("/daily")
async def generate_daily(request: DailyRequest, background_tasks: BackgroundTasks):
    task = task_manager.create_task("daily")
    background_tasks.add_task(run_daily_task, task.task_id, request)
    return {"success": True, "task_id": task.task_id, "message": "日报任务已创建"}


@router.post("/rolling")
async def run_rolling(request: RollingRequest, background_tasks: BackgroundTasks):
    task = task_manager.create_task("rolling")
    background_tasks.add_task(run_rolling_task, task.task_id, request)
    return {"success": True, "task_id": task.task_id, "message": "滚动评估任务已创建"}


@router.post("/backtest-emotion")
async def run_backtest(request: BacktestRequest, background_tasks: BackgroundTasks):
    task = task_manager.create_task("backtest")
    background_tasks.add_task(run_backtest_task, task.task_id, request)
    return {"success": True, "task_id": task.task_id, "message": "回测任务已创建"}


@router.post("/heatmap")
async def run_heatmap(request: HeatmapRequest, background_tasks: BackgroundTasks):
    task = task_manager.create_task("heatmap")
    background_tasks.add_task(run_heatmap_task, task.task_id, request)
    return {"success": True, "task_id": task.task_id, "message": "热力图分析任务已创建"}


@router.post("/sync-cache")
async def sync_cache(request: SyncRequest, background_tasks: BackgroundTasks):
    task = task_manager.create_task("sync")
    background_tasks.add_task(run_sync_task, task.task_id, request)
    return {"success": True, "task_id": task.task_id, "message": "缓存同步任务已创建"}


@router.get("/cache/status")
async def get_cache_status():
    """获取缓存状态"""
    return file_service.get_cache_status()


@router.post("/cache/import")
async def import_cache(file: UploadFile = File(...)):
    """导入缓存数据"""
    if not file.filename or not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="请上传 zip 文件")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_file:
        temp_path = temp_file.name
        content = await file.read()
        temp_file.write(content)
    
    try:
        from pathlib import Path
        result = file_service.import_cache(Path(temp_path))
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
