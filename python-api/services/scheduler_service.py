import sys
from pathlib import Path
from typing import Optional
from dataclasses import asdict

PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.scheduler import (
    get_task_status,
    install_task,
    uninstall_task,
    TaskStatus,
    check_task_exists,
)


class SchedulerService:
    def __init__(self):
        pass

    def get_status(self) -> dict:
        status = get_task_status()
        return {
            "exists": status.exists,
            "enabled": status.enabled,
            "last_run_time": status.last_run_time,
            "last_run_result": status.last_run_result,
            "run_count": status.run_count,
            "next_run_time": status.next_run_time,
            "error_message": status.error_message,
        }

    def install(self) -> dict:
        success, message = install_task()
        return {
            "success": success,
            "message": message,
        }

    def uninstall(self) -> dict:
        success, message = uninstall_task()
        return {
            "success": success,
            "message": message,
        }

    def is_installed(self) -> bool:
        return check_task_exists()
