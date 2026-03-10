from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

from services import ConfigService

router = APIRouter()
config_service = ConfigService()


class ConfigUpdateRequest(BaseModel):
    production_train: Optional[Dict[str, Any]] = None
    daily: Optional[Dict[str, Any]] = None
    emotion_backtest: Optional[Dict[str, Any]] = None
    rolling: Optional[Dict[str, Any]] = None
    heatmap: Optional[Dict[str, Any]] = None


@router.get("/config")
async def get_config():
    config = config_service.get_config()
    return {"success": True, "data": config}


@router.put("/config")
async def update_config(request: ConfigUpdateRequest):
    updates = request.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="没有提供更新内容")
    
    updated_config = config_service.update_config(updates)
    return {"success": True, "data": updated_config, "message": "配置已更新"}


@router.get("/config/{section}")
async def get_config_section(section: str):
    config_section = config_service.get_section(section)
    if config_section is None:
        raise HTTPException(status_code=404, detail=f"配置项 {section} 不存在")
    return {"success": True, "data": config_section}


@router.put("/config/{section}")
async def update_config_section(section: str, values: Dict[str, Any]):
    updated_section = config_service.update_section(section, values)
    if updated_section is None:
        raise HTTPException(status_code=404, detail=f"配置项 {section} 不存在")
    return {"success": True, "data": updated_section, "message": f"配置项 {section} 已更新"}
