"""
Common Pydantic Models for Agents

通用 Pydantic 模型，用于规范整个 agents 包的数据结构。
"""

from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field


# ============================================================================
# Todo 相关模型
# ============================================================================

class TodoItemModel(BaseModel):
    """单个任务项模型"""
    id: str
    text: str
    status: str  # pending | in_progress | completed


class TodoStateModel(BaseModel):
    """对话级别的 Todo 状态"""
    dialog_id: str
    items: list[TodoItemModel] = Field(default_factory=list)
    rounds_since_todo: int = 0
    used_todo_in_round: bool = False
    updated_at: float = Field(default_factory=lambda: __import__('time').time())


class TodoResponse(BaseModel):
    """Todo 列表响应（用于 REST API）"""
    dialog_id: str
    items: list[dict[str, Any]]
    rounds_since_todo: int
    updated_at: float


class TodoUpdatedEvent(BaseModel):
    """Todo 更新事件"""
    type: str = "todo:updated"
    dialog_id: str
    todos: list[dict[str, Any]]
    rounds_since_todo: int
    timestamp: float


class TodoReminderEvent(BaseModel):
    """Todo 提醒事件"""
    type: str = "todo:reminder"
    dialog_id: str
    message: str
    rounds_since_todo: int
    timestamp: float


# ============================================================================
# Skill Edit 事件模型
# ============================================================================

class SkillEditPendingEvent(BaseModel):
    """Skill Edit 待审批事件"""
    type: str = "skill_edit:pending"
    dialog_id: str
    approval: dict[str, Any]
    timestamp: float


class SkillEditResolvedEvent(BaseModel):
    """Skill Edit 已解决事件"""
    type: str = "skill_edit:resolved"
    dialog_id: str
    approval_id: str
    result: str
    timestamp: float


# ============================================================================
# Session 相关模型
# ============================================================================

class SessionStatus(BaseModel):
    """SessionManager 状态"""
    is_running: bool
    current_dialog_id: Optional[str]
    model: str
    window_rounds: int
    active_history_rounds: int


# ============================================================================
# WebSocket 相关模型
# ============================================================================

class WebSocketBroadcastMessage(BaseModel):
    """WebSocket 广播消息"""
    type: str
    dialog_id: Optional[str] = None
    data: Optional[dict[str, Any]] = None
    timestamp: Optional[float] = None


class WebSocketErrorResponse(BaseModel):
    """WebSocket 错误响应"""
    error: str
    status_code: Optional[int] = None


class WebSocketStatusResponse(BaseModel):
    """WebSocket 状态响应"""
    status: str


# ============================================================================
# Dialog Snapshot 模型
# ============================================================================

class DialogSnapshot(BaseModel):
    """对话框状态快照"""
    type: str = "dialog:snapshot"
    dialog_id: str
    data: dict[str, Any]
    timestamp: float


# ============================================================================
# Hook Logger 模型
# ============================================================================

class HookLogEntry(BaseModel):
    """Hook 日志条目"""
    timestamp: str
    level: str
    hook_name: str
    dialog_id: Optional[str]
    message: str
    context: dict[str, Any]


class HookLoggerStatus(BaseModel):
    """HookLogger 状态"""
    enabled: bool
    log_dir: Optional[str]
    recent_logs: list[HookLogEntry]


# ============================================================================
# Event Bus 模型
# ============================================================================

class EventBusStats(BaseModel):
    """事件总线统计"""
    running: bool
    queue_size: int
    typed_observers: dict[str, int]
    global_observers: int
    handlers: int


# ============================================================================
# Tool/Provider 模型
# ============================================================================

class ToolCallResult(BaseModel):
    """工具调用结果"""
    type: str = "tool_result"
    tool_use_id: str
    content: str


class ToolDefinition(BaseModel):
    """工具定义"""
    type: str = "function"
    function: dict[str, Any]


# ============================================================================
# Background Task 模型
# ============================================================================

class BackgroundTaskStatus(BaseModel):
    """后台任务状态"""
    id: str
    status: str  # running, completed, timeout, error
    command: str
    result: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]


# ============================================================================
# Message Content 模型
# ============================================================================

class TextContentBlock(BaseModel):
    """文本内容块"""
    type: str = "text"
    text: str


class ToolUseContentBlock(BaseModel):
    """工具使用内容块"""
    type: str = "tool_use"
    id: str
    name: str
    input: dict[str, Any]


# ============================================================================
# WebSocket Agent 事件模型
# ============================================================================

class MessageStartEvent(BaseModel):
    """消息开始事件"""
    message_id: str
    role: str
    agent_name: str


class ContentDeltaEvent(BaseModel):
    """内容增量事件"""
    message_id: str
    delta: str
    content: str
    agent_name: str


class ReasoningDeltaEvent(BaseModel):
    """推理内容增量事件"""
    message_id: str
    delta: str
    reasoning_content: str


class ToolCallEvent(BaseModel):
    """工具调用事件"""
    message_id: str
    tool_call: dict[str, Any]


class ToolResultEvent(BaseModel):
    """工具执行结果事件"""
    message_id: str | None
    tool_call_id: str
    tool_name: str
    result: str
    timestamp: float


class MessageCompleteEvent(BaseModel):
    """消息完成事件"""
    message_id: str
    content: str
    reasoning_content: str
    tool_calls: list[dict[str, Any]]


class ReasoningEvent(BaseModel):
    """推理内容事件"""
    message_id: str | None
    reasoning_content: str


class ErrorEvent(BaseModel):
    """错误事件"""
    message_id: str | None
    error: str


class StoppedEvent(BaseModel):
    """停止事件"""
    message_id: str | None


class RunSummaryEvent(BaseModel):
    """运行摘要事件"""
    result: str
    hook_stats: dict[str, Any]
    messages: list[dict[str, Any]]


# ============================================================================
# StateManagedAgentBridge WebSocket 事件模型
# ============================================================================

class AgentMessageStartEvent(BaseModel):
    """Agent 消息开始事件"""
    type: str = "agent:message_start"
    dialog_id: str
    data: MessageStartEvent
    timestamp: float


class StreamDeltaEvent(BaseModel):
    """流式增量事件"""
    type: str = "stream:delta"
    dialog_id: str
    message_id: str
    delta: dict[str, Any]
    timestamp: float


class ToolCallUpdateEvent(BaseModel):
    """工具调用更新事件"""
    type: str = "tool_call:update"
    dialog_id: str
    tool_call: dict[str, Any]
    timestamp: float


class StatusChangeEvent(BaseModel):
    """状态变更事件"""
    type: str = "status:change"
    dialog_id: str
    from_status: str
    to_status: str
    timestamp: float


# ============================================================================
# 导出列表
# ============================================================================

__all__ = [
    # Todo
    "TodoItemModel",
    "TodoStateModel",
    "TodoUpdatedEvent",
    "TodoReminderEvent",
    # Session
    "SessionStatus",
    # WebSocket
    "WebSocketBroadcastMessage",
    "WebSocketErrorResponse",
    "WebSocketStatusResponse",
    # Dialog
    "DialogSnapshot",
    # Hook Logger
    "HookLogEntry",
    "HookLoggerStatus",
    # Event Bus
    "EventBusStats",
    # Tool
    "ToolCallResult",
    "ToolDefinition",
    # Background Task
    "BackgroundTaskStatus",
    # Content
    "TextContentBlock",
    "ToolUseContentBlock",
    # Agent WebSocket Events
    "MessageStartEvent",
    "ContentDeltaEvent",
    "ReasoningDeltaEvent",
    "ToolCallEvent",
    "ToolResultEvent",
    "MessageCompleteEvent",
    "ReasoningEvent",
    "ErrorEvent",
    "StoppedEvent",
    "RunSummaryEvent",
    # StateManagedAgentBridge Events
    "AgentMessageStartEvent",
    "StreamDeltaEvent",
    "ToolCallUpdateEvent",
    "StatusChangeEvent",
]
