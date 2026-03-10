from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from services import FileService

router = APIRouter()
file_service = FileService()


@router.get("/reports")
async def get_reports(
    type: Optional[str] = Query(None, description="报告类型: daily, backtest, heatmap, stability, sensitivity"),
):
    reports = file_service.get_reports(report_type=type)
    return {"success": True, "data": reports, "total": len(reports)}


@router.get("/reports/{filename}")
async def get_report(filename: str):
    content = file_service.get_report_content(filename)
    if content is None:
        raise HTTPException(status_code=404, detail="报告不存在")
    return {"success": True, "filename": filename, "content": content}


@router.delete("/reports/{filename}")
async def delete_report(filename: str):
    success = file_service.delete_report(filename)
    if not success:
        raise HTTPException(status_code=404, detail="报告不存在")
    return {"success": True, "message": f"报告 {filename} 已删除"}


@router.get("/images")
async def get_images():
    images = file_service.get_images()
    return {"success": True, "data": images, "total": len(images)}
