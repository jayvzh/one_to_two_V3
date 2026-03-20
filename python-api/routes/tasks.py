from fastapi import APIRouter, HTTPException
from typing import Optional

from schemas.tasks import TaskManager

router = APIRouter()
task_manager = TaskManager()


@router.get("")
async def list_tasks(
    task_type: Optional[str] = None,
):
    tasks = task_manager.list_tasks(task_type=task_type)
    return {
        "success": True,
        "data": [t.to_dict() for t in tasks],
        "total": len(tasks),
    }


@router.get("/{task_id}")
async def get_task(task_id: str):
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"success": True, "data": task.to_dict()}


@router.get("/{task_id}/logs")
async def get_task_logs(task_id: str):
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"success": True, "data": task.logs}


@router.delete("/completed")
async def clear_completed_tasks():
    count = task_manager.clear_completed_tasks()
    return {"success": True, "message": f"已清理 {count} 个已完成任务"}
