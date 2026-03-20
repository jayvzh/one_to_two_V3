from fastapi import APIRouter

router = APIRouter()

def _include_routers():
    from .pipeline import router as pipeline_router
    from .models import router as models_router
    from .reports import router as reports_router
    from .config import router as config_router
    from .scheduler import router as scheduler_router
    from .tasks import router as tasks_router
    
    router.include_router(pipeline_router, prefix="/api", tags=["pipeline"])
    router.include_router(models_router, prefix="/api", tags=["models"])
    router.include_router(reports_router, prefix="/api", tags=["reports"])
    router.include_router(config_router, prefix="/api", tags=["config"])
    router.include_router(scheduler_router, prefix="/api/scheduler", tags=["scheduler"])
    router.include_router(tasks_router, prefix="/api/tasks", tags=["tasks"])

_include_routers()
