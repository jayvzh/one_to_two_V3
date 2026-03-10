from dataclasses import dataclass, field
from typing import Any, Generic, Optional, TypeVar

T = TypeVar("T")


@dataclass
class APIResponse(Generic[T]):
    success: bool
    data: Optional[T] = None
    message: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        result = {"success": self.success}
        if self.data is not None:
            result["data"] = self.data
        if self.message is not None:
            result["message"] = self.message
        if self.error is not None:
            result["error"] = self.error
        return result


@dataclass
class ErrorResponse:
    success: bool = False
    error: str = ""
    detail: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        result = {"success": False, "error": self.error}
        if self.detail:
            result["detail"] = self.detail
        return result


@dataclass
class PaginatedResponse(Generic[T]):
    success: bool = True
    data: list[T] = field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "total": self.total,
            "page": self.page,
            "page_size": self.page_size,
        }
