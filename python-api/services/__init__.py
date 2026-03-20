def __getattr__(name):
    if name == "PipelineService":
        from .pipeline_service import PipelineService
        return PipelineService
    elif name == "ConfigService":
        from .config_service import ConfigService
        return ConfigService
    elif name == "SchedulerService":
        from .scheduler_service import SchedulerService
        return SchedulerService
    elif name == "FileService":
        from .file_service import FileService
        return FileService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["PipelineService", "ConfigService", "SchedulerService", "FileService"]
