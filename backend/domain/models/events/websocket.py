"""
WebSocket 事件模型 - Pydantic BaseModel 版本

定义 WebSocket 事件相关的 Pydantic 模型，替代 TypedDict。
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class WSDialogMetadata(BaseModel):
    """对话元信息模型"""

    model: str
    agent_name: str
    tool_calls_count: int = 0
    total_tokens: int = 0


class WSStreamingMessage(BaseModel):
    """流式推送占位消息模型"""

    id: str
    message: Dict[str, Any]  # LangChain 格式消息
    status: str
    timestamp: str
    agent_name: str
    reasoning_content: Optional[str] = None


class WSDialogSnapshot(BaseModel):
    """对话完整快照模型"""

    id: str
    title: str
    status: str
    messages: List[Dict[str, Any]]  # LangChain 格式消息列表
    streaming_message: Optional[WSStreamingMessage] = None
    metadata: WSDialogMetadata
    created_at: str
    updated_at: str


class WSSnapshotEvent(BaseModel):
    """dialog:snapshot 广播事件模型"""

    type: str = "dialog:snapshot"
    dialog_id: str
    data: WSDialogSnapshot
    timestamp: int


class WSDeltaContent(BaseModel):
    """stream:delta 中的增量内容模型"""

    content: str
    reasoning: str = ""


class WSStreamDeltaEvent(BaseModel):
    """stream:delta 广播事件模型"""

    type: str = "stream:delta"
    dialog_id: str
    message_id: str
    delta: WSDeltaContent
    timestamp: int


class WSErrorDetail(BaseModel):
    """错误详情模型"""

    code: str
    message: str


class WSErrorEvent(BaseModel):
    """error 广播事件模型"""

    type: str = "error"
    dialog_id: str
    error: WSErrorDetail
    timestamp: int


class WSHitlRequestEvent(BaseModel):
    """hitl:request 广播事件模型"""

    type: str = "hitl:request"
    dialog_id: str
    data: Dict[str, Any]
    timestamp: int


class WSStatusChangeEvent(BaseModel):
    """status:change 广播事件模型"""

    type: str = "status:change"
    dialog_id: str
    from_status: str = Field(..., alias="from")
    to_status: str = Field(..., alias="to")
    timestamp: int

    class Config:
        populate_by_name = True


class WSToolCall(BaseModel):
    """tool_call:update 事件中的工具调用模型"""

    id: str
    name: str
    arguments: Dict[str, Any]
    status: str  # "pending" | "running" | "completed" | "error"
    result: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class WSToolCallUpdateEvent(BaseModel):
    """tool_call:update 广播事件模型"""

    type: str = "tool_call:update"
    dialog_id: str
    tool_call: WSToolCall
    timestamp: int


class WSTodoItem(BaseModel):
    """Todo 项目模型"""

    id: str
    text: str
    status: str = "pending"  # "pending" | "in_progress" | "completed"


class WSTodoUpdatedEvent(BaseModel):
    """todo:updated 广播事件模型"""

    type: str = "todo:updated"
    dialog_id: str
    todos: List[WSTodoItem]
    rounds_since_todo: int = 0
    timestamp: int


class WSTodoReminderEvent(BaseModel):
    """todo:reminder 广播事件模型"""

    type: str = "todo:reminder"
    dialog_id: str
    message: str
    rounds_since_todo: int = 0
    timestamp: int


class WSStreamStartEvent(BaseModel):
    """stream:start 事件模型"""

    type: str = "stream:start"
    dialog_id: str
    message_id: str
    message: Optional[Dict[str, Any]] = None  # LangChain 格式消息
    timestamp: int


class WSStreamEndEvent(BaseModel):
    """stream:end 事件模型"""

    type: str = "stream:end"
    dialog_id: str
    message_id: str
    message: Optional[Dict[str, Any]] = None  # LangChain 格式消息
    final_content: str = ""
    timestamp: int


class WSStreamTruncatedEvent(BaseModel):
    """stream:truncated 事件模型"""

    type: str = "stream:truncated"
    dialog_id: str
    message_id: str
    reason: str
    timestamp: int


class WSAckEvent(BaseModel):
    """ack 事件模型"""

    type: str = "ack"
    dialog_id: str
    client_id: str
    server_id: Optional[str] = None
    message: Optional[Dict[str, Any]] = None  # LangChain 格式消息
    timestamp: int


class WSMessageAddedEvent(BaseModel):
    """message:added 事件模型"""

    type: str = "message:added"
    dialog_id: str
    message: Dict[str, Any]  # LangChain 格式消息
    timestamp: int


class WSNodeUpdateEvent(BaseModel):
    """node:update 广播事件模型 - updates 模式专用"""

    type: str = "node:update"
    dialog_id: str
    node: str
    messages: List[Dict[str, Any]]  # LangChain 格式消息列表
    timestamp: int


# 导出
__all__ = [
    "WSDialogMetadata",
    "WSStreamingMessage",
    "WSDialogSnapshot",
    "WSSnapshotEvent",
    "WSDeltaContent",
    "WSStreamDeltaEvent",
    "WSErrorDetail",
    "WSErrorEvent",
    "WSHitlRequestEvent",
    "WSStatusChangeEvent",
    "WSToolCall",
    "WSToolCallUpdateEvent",
    "WSTodoItem",
    "WSTodoUpdatedEvent",
    "WSTodoReminderEvent",
    "WSStreamStartEvent",
    "WSStreamEndEvent",
    "WSStreamTruncatedEvent",
    "WSAckEvent",
    "WSMessageAddedEvent",
]
