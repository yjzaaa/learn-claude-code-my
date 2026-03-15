"""
通用响应模型

统一项目中所有 API 和工具函数的响应格式。
"""

from __future__ import annotations

from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


# ============================================================================
# 基础响应模型
# ============================================================================

class SuccessResponse(BaseModel, Generic[T]):
    """成功响应"""
    success: bool = True
    data: T


class ErrorResponse(BaseModel):
    """错误响应"""
    success: bool = False
    error: str
    message: Optional[str] = None


class MessageResponse(BaseModel):
    """消息响应"""
    success: bool = True
    message: str


# ============================================================================
# Skill 相关响应
# ============================================================================

class SkillInfo(BaseModel):
    """技能信息"""
    name: str
    description: str
    tags: str
    path: str


class SkillDetail(BaseModel):
    """技能详情"""
    name: str
    content: str


class SkillListResponse(BaseModel):
    """技能列表响应"""
    success: bool = True
    data: list[SkillInfo]


class SkillDetailResponse(BaseModel):
    """技能详情响应"""
    success: bool = True
    data: SkillDetail


class SkillUpdateResponse(BaseModel):
    """技能更新响应"""
    success: bool = True
    data: dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# Skill Edit HITL 响应
# ============================================================================

class SkillEditDecisionResponse(BaseModel):
    """Skill Edit 审批响应"""
    success: bool
    message: Optional[str] = None
    data: Optional[dict[str, Any]] = None


# ============================================================================
# Todo 工具响应
# ============================================================================

class TodoUpdateResponse(BaseModel):
    """Todo 更新响应"""
    success: bool
    dialog_id: Optional[str] = None
    item_count: Optional[int] = None
    items: Optional[list[dict[str, Any]]] = None
    error: Optional[str] = None


# ============================================================================
# Context Compact 响应
# ============================================================================

class ContextCompactResponse(BaseModel):
    """上下文压缩响应"""
    compaction_requested: bool = True
    summary: str
    note: str = "Context will be compacted in next iteration"


# ============================================================================
# Agent 状态响应
# ============================================================================

class AgentStatusResponse(BaseModel):
    """Agent 状态响应"""
    success: bool = True
    data: dict[str, Any]


class StopAgentResponse(BaseModel):
    """停止 Agent 响应"""
    success: bool = True
    data: dict[str, Any]


# ============================================================================
# WebSocket 事件模型
# ============================================================================

class WebSocketEvent(BaseModel):
    """WebSocket 事件基类"""
    type: str


class WebSocketErrorDetail(BaseModel):
    """WebSocket 错误详情"""
    code: str
    message: str


class WebSocketErrorMessage(WebSocketEvent):
    """WebSocket 错误消息"""
    type: str = "error"
    error: WebSocketErrorDetail

    @classmethod
    def invalid_dialog_id(cls, message: str = "dialog_id is required") -> "WebSocketErrorMessage":
        """创建无效对话框ID错误"""
        return cls(
            error=WebSocketErrorDetail(
                code="INVALID_DIALOG_ID",
                message=message
            )
        )

    @classmethod
    def dialog_not_found(cls, dialog_id: str) -> "WebSocketErrorMessage":
        """创建对话框不存在错误"""
        return cls(
            error=WebSocketErrorDetail(
                code="DIALOG_NOT_FOUND",
                message=f"Dialog {dialog_id} not found"
            )
        )

    @classmethod
    def no_context(cls, dialog_id: str) -> "WebSocketErrorMessage":
        """创建无上下文错误"""
        return cls(
            error=WebSocketErrorDetail(
                code="NO_CONTEXT",
                message="No user context to resume"
            )
        )

    @classmethod
    def unknown_type(cls, msg_type: str) -> "WebSocketErrorMessage":
        """创建未知消息类型错误"""
        return cls(
            error=WebSocketErrorDetail(
                code="UNKNOWN_TYPE",
                message=f"Unknown message type: {msg_type}"
            )
        )


# ============================================================================
# 导出列表
# ============================================================================

__all__ = [
    # 基础响应
    "SuccessResponse",
    "ErrorResponse",
    "MessageResponse",
    # Skill 响应
    "SkillInfo",
    "SkillDetail",
    "SkillListResponse",
    "SkillDetailResponse",
    "SkillUpdateResponse",
    # Skill Edit HITL
    "SkillEditDecisionResponse",
    # Todo
    "TodoUpdateResponse",
    # Context Compact
    "ContextCompactResponse",
    # Agent 状态
    "AgentStatusResponse",
    "StopAgentResponse",
    # WebSocket
    "WebSocketEvent",
    "WebSocketErrorDetail",
    "WebSocketErrorMessage",
]
