from fastapi import APIRouter, HTTPException
from typing import Optional

from services import PipelineService

router = APIRouter()
pipeline_service = PipelineService()


@router.get("/models")
async def get_models():
    models = pipeline_service.get_model_list()
    return {"success": True, "data": models, "total": len(models)}
