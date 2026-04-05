"""
Agent Events - 统一事件模型

前后端共享的事件 schema 定义。
- AgentEvent: Runtime 内部产出的事件 (Runtime -> EventCoordinator)
- ServerPushEvent*: 通过 WebSocket 发送到前端的事件
"""

from typing import Any, Dict, Literal, Optional, Union
from pydantic import BaseModel, Field


class AgentEvent(BaseModel):
    """
    Runtime 内部统一事件模型

    Runtime 只产出此类型事件，由 EventCoordinator 转换为 ServerPushEvent。
    dialog_id 为可选，因为 ingest() 方法会单独传入。
    """

    type: Literal[
        "text_delta",
        "reasoning_delta",
        "message_complete",
        "tool_call",
        "tool_result",
        "snapshot",
        "status_change",
        "error",
    ]
    data: Any = Field(default_factory=dict)
    metadata: Optional[Dict[str, Any]] = None
    timestamp: Optional[int] = None


# ═══════════════════════════════════════════════════════════
# Server Push Events (WebSocket -> frontend)
# ═══════════════════════════════════════════════════════════


class DialogSnapshotEvent(BaseModel):
    """dialog:snapshot - 完整对话快照"""
    type: Literal["dialog:snapshot"] = "dialog:snapshot"
    dialog_id: str
    data: Dict[str, Any]
    timestamp: int


class StreamDeltaEvent(BaseModel):
    """stream:delta - 流式文本增量"""
    type: Literal["stream:delta"] = "stream:delta"
    dialog_id: str
    message_id: str
    delta: Dict[str, Optional[str]]
    timestamp: int


class StatusChangeEvent(BaseModel):
    """status:change - 对话状态变更"""
    type: Literal["status:change"] = "status:change"
    dialog_id: str
    data: Dict[str, str]
    timestamp: int


class ToolCallEvent(BaseModel):
    """agent:tool_call - 工具调用"""
    type: Literal["agent:tool_call"] = "agent:tool_call"
    dialog_id: str
    data: Dict[str, Any]
    timestamp: int


class ToolResultEvent(BaseModel):
    """agent:tool_result - 工具结果"""
    type: Literal["agent:tool_result"] = "agent:tool_result"
    dialog_id: str
    data: Dict[str, Any]
    timestamp: int


class ErrorEvent(BaseModel):
    """error - 错误事件"""
    type: Literal["error"] = "error"
    dialog_id: str
    data: Dict[str, Any]
    timestamp: int


class TodoUpdatedEvent(BaseModel):
    """todo:updated - Todo 列表更新"""
    type: Literal["todo:updated"] = "todo:updated"
    dialog_id: str
    data: Dict[str, Any]
    timestamp: int


class TodoReminderEvent(BaseModel):
    """todo:reminder - Todo 提醒"""
    type: Literal["todo:reminder"] = "todo:reminder"
    dialog_id: str
    data: Dict[str, Any]
    timestamp: int


class RoundsLimitEvent(BaseModel):
    """agent:rounds_limit_reached - 轮数限制"""
    type: Literal["agent:rounds_limit_reached"] = "agent:rounds_limit_reached"
    dialog_id: str
    data: Dict[str, Any]
    timestamp: int


# Union type for type checking
ServerPushEvent = Union[
    DialogSnapshotEvent,
    StreamDeltaEvent,
    StatusChangeEvent,
    ToolCallEvent,
    ToolResultEvent,
    ErrorEvent,
    TodoUpdatedEvent,
    TodoReminderEvent,
    RoundsLimitEvent,
]


__all__ = [
    "AgentEvent",
    "DialogSnapshotEvent",
    "StreamDeltaEvent",
    "StatusChangeEvent",
    "ToolCallEvent",
    "ToolResultEvent",
    "ErrorEvent",
    "TodoUpdatedEvent",
    "TodoReminderEvent",
    "RoundsLimitEvent",
    "ServerPushEvent",
]
