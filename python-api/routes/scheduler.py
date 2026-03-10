from fastapi import APIRouter, HTTPException

from ..services import SchedulerService

router = APIRouter()
scheduler_service = SchedulerService()


@router.get("/status")
async def get_scheduler_status():
    status = scheduler_service.get_status()
    return {"success": True, "data": status}


@router.post("/install")
async def install_scheduler():
    result = scheduler_service.install()
    if not result["success"]:
        return {"success": False, "error": result["message"]}
    return {"success": True, "message": result["message"]}


@router.post("/uninstall")
async def uninstall_scheduler():
    result = scheduler_service.uninstall()
    if not result["success"]:
        return {"success": False, "error": result["message"]}
    return {"success": True, "message": result["message"]}
