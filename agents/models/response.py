"""
API 响应数据模型

统一后端 API 返回格式，替代裸字典
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Generic, List, Optional, TypeVar
import json


T = TypeVar("T")


@dataclass
class ApiResponse(Generic[T]):
    """
    标准 API 响应格式

    与前端 ApiResponse<T> 对齐：
    {
        "success": boolean,
        "data"?: T,
        "message"?: string,
        "error"?: string,
        "metadata"?: Record<string, any>
    }
    """
    success: bool
    data: Optional[T] = None
    message: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result: Dict[str, Any] = {"success": self.success}
        if self.data is not None:
            if hasattr(self.data, "to_dict"):
                result["data"] = self.data.to_dict()
            elif isinstance(self.data, list):
                result["data"] = [
                    item.to_dict() if hasattr(item, "to_dict") else item
                    for item in self.data
                ]
            else:
                result["data"] = self.data
        if self.message is not None:
            result["message"] = self.message
        if self.error is not None:
            result["error"] = self.error
        if self.metadata:
            result["metadata"] = self.metadata
        return result

    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def success(cls, data: T, message: Optional[str] = None, **metadata) -> "ApiResponse[T]":
        """创建成功响应"""
        return cls(
            success=True,
            data=data,
            message=message,
            metadata=metadata
        )

    @classmethod
    def failure(cls, error: str, message: Optional[str] = None, **metadata) -> "ApiResponse[T]":
        """创建失败响应"""
        return cls(
            success=False,
            error=error,
            message=message,
            metadata=metadata
        )


@dataclass
class PaginatedData(Generic[T]):
    """
    分页数据格式

    {
        "items": T[],
        "total": number,
        "page": number,
        "page_size": number,
        "total_pages": number
    }
    """
    items: List[T]
    total: int
    page: int = 1
    page_size: int = 20

    @property
    def total_pages(self) -> int:
        """计算总页数"""
        if self.page_size <= 0:
            return 0
        return (self.total + self.page_size - 1) // self.page_size

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "items": [
                item.to_dict() if hasattr(item, "to_dict") else item
                for item in self.items
            ],
            "total": self.total,
            "page": self.page,
            "page_size": self.page_size,
            "total_pages": self.total_pages,
        }


@dataclass
class DialogListResponse:
    """对话框列表响应数据"""
    dialogs: List[Dict[str, Any]]
    total: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dialogs": self.dialogs,
            "total": self.total,
        }


@dataclass
class DialogDetailResponse:
    """对话框详情响应数据"""
    id: str
    title: str
    messages: List[Dict[str, Any]]
    status: str
    created_at: str
    updated_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "messages": self.messages,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class SkillInfoResponse:
    """技能信息响应数据"""
    name: str
    description: str
    version: str
    author: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "tags": self.tags,
        }


@dataclass
class SkillListResponse:
    """技能列表响应数据"""
    skills: List[SkillInfoResponse]
    total: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skills": [s.to_dict() for s in self.skills],
            "total": self.total,
        }


@dataclass
class AgentStatusResponse:
    """Agent 状态响应数据"""
    is_running: bool
    current_dialog_id: Optional[str]
    model: str
    agent_type: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_running": self.is_running,
            "current_dialog_id": self.current_dialog_id,
            "model": self.model,
            "agent_type": self.agent_type,
        }


@dataclass
class MessageSendResponse:
    """消息发送响应数据"""
    message_id: str
    dialog_id: str
    queued: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "dialog_id": self.dialog_id,
            "queued": self.queued,
        }


@dataclass
class ConfigUpdateResponse:
    """配置更新响应数据"""
    updated_keys: List[str]
    config: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "updated_keys": self.updated_keys,
            "config": self.config,
        }


@dataclass
class ErrorDetail:
    """错误详情"""
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "code": self.code,
            "message": self.message,
        }
        if self.details:
            result["details"] = self.details
        return result


@dataclass
class ValidationErrorResponse:
    """验证错误响应"""
    errors: List[ErrorDetail]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "errors": [e.to_dict() for e in self.errors],
        }


# 常用响应快捷方法

def success_response(data: Any, message: Optional[str] = None) -> Dict[str, Any]:
    """创建成功响应字典"""
    return ApiResponse.success(data=data, message=message).to_dict()


def error_response(error: str, message: Optional[str] = None) -> Dict[str, Any]:
    """创建错误响应字典"""
    return ApiResponse.failure(error=error, message=message).to_dict()


def paginated_response(
    items: List[Any],
    total: int,
    page: int = 1,
    page_size: int = 20
) -> Dict[str, Any]:
    """创建分页响应字典"""
    paginated = PaginatedData(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )
    return ApiResponse.success(data=paginated.to_dict()).to_dict()
