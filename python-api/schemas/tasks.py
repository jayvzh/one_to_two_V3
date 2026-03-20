from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
import asyncio
import uuid
from collections import OrderedDict


class TaskState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskStatus:
    task_id: str
    task_type: str
    state: TaskState
    progress: float = 0.0
    message: str = ""
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    created_at: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    logs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "state": self.state.value,
            "progress": self.progress,
            "message": self.message,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "logs": self.logs[-100:],
        }


@dataclass
class TaskInfo:
    task_id: str
    task_type: str
    state: TaskState
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "state": self.state.value,
            "created_at": self.created_at,
        }


class TaskManager:
    _instance = None
    _lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tasks: OrderedDict[str, TaskStatus] = OrderedDict()
            cls._instance._max_tasks = 100
        return cls._instance

    def _generate_task_id(self) -> str:
        return f"task_{uuid.uuid4().hex[:8]}"

    def create_task(self, task_type: str) -> TaskStatus:
        task_id = self._generate_task_id()
        now = datetime.now().isoformat()
        task = TaskStatus(
            task_id=task_id,
            task_type=task_type,
            state=TaskState.PENDING,
            created_at=now,
        )
        self._tasks[task_id] = task
        self._cleanup_old_tasks()
        return task

    def get_task(self, task_id: str) -> Optional[TaskStatus]:
        return self._tasks.get(task_id)

    def update_task(
        self,
        task_id: str,
        state: Optional[TaskState] = None,
        progress: Optional[float] = None,
        message: Optional[str] = None,
        result: Optional[dict] = None,
        error: Optional[str] = None,
        log: Optional[str] = None,
    ) -> Optional[TaskStatus]:
        task = self._tasks.get(task_id)
        if not task:
            return None

        if state is not None:
            task.state = state
            if state == TaskState.RUNNING:
                task.started_at = datetime.now().isoformat()
            elif state in (TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED):
                task.completed_at = datetime.now().isoformat()

        if progress is not None:
            task.progress = progress

        if message is not None:
            task.message = message

        if result is not None:
            task.result = result

        if error is not None:
            task.error = error

        if log is not None:
            task.logs.append(f"[{datetime.now().isoformat()}] {log}")

        return task

    def list_tasks(self, task_type: Optional[str] = None) -> list[TaskInfo]:
        tasks = []
        for task in reversed(list(self._tasks.values())):
            if task_type is None or task.task_type == task_type:
                tasks.append(TaskInfo(
                    task_id=task.task_id,
                    task_type=task.task_type,
                    state=task.state,
                    created_at=task.created_at,
                ))
        return tasks

    def _cleanup_old_tasks(self):
        if len(self._tasks) > self._max_tasks:
            oldest_keys = list(self._tasks.keys())[:len(self._tasks) - self._max_tasks]
            for key in oldest_keys:
                del self._tasks[key]

    def clear_completed_tasks(self) -> int:
        to_remove = [
            task_id for task_id, task in self._tasks.items()
            if task.state in (TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED)
        ]
        for task_id in to_remove:
            del self._tasks[task_id]
        return len(to_remove)
