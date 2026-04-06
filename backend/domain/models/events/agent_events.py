"""Agent 相关事件定义

完全事件驱动架构的核心事件类型
"""

from dataclasses import dataclass, field
from typing import Any

from backend.domain.models.events.base import BaseEvent, EventPriority


@dataclass
class AgentExecuteRequest(BaseEvent):
    """Agent 执行请求事件

    由 main.py 发射，Agent Runtime 订阅处理
    """

    dialog_id: str = ""
    content: str = ""
    message_id: str = ""
    stream: bool = True
    priority: EventPriority = EventPriority.HIGH


@dataclass
class AgentProgressEvent(BaseEvent):
    """Agent 执行进度事件

    由 Agent Runtime 发射，main.py 订阅并广播到 WebSocket
    """

    dialog_id: str = ""
    message_id: str = ""
    delta: str = ""
    is_reasoning: bool = False
    accumulated: str = ""
    priority: EventPriority = EventPriority.HIGH


@dataclass
class AgentCompleteEvent(BaseEvent):
    """Agent 执行完成事件

    由 Agent Runtime 发射，通知执行完成
    """

    dialog_id: str = ""
    message_id: str = ""
    final_content: str = ""
    token_count: int = 0
    priority: EventPriority = EventPriority.NORMAL


@dataclass
class AgentErrorEvent(BaseEvent):
    """Agent 执行错误事件

    由 Agent Runtime 发射，通知执行错误
    """

    dialog_id: str = ""
    message_id: str = ""
    error_type: str = ""
    error_message: str = ""
    priority: EventPriority = EventPriority.CRITICAL


@dataclass
class ToolCallRequest(BaseEvent):
    """工具调用请求事件"""

    dialog_id: str = ""
    tool_call_id: str = ""
    tool_name: str = ""
    arguments: dict = field(default_factory=dict)
    priority: EventPriority = EventPriority.HIGH


@dataclass
class ToolCallResultEvent(BaseEvent):
    """工具调用结果事件"""

    dialog_id: str = ""
    tool_call_id: str = ""
    tool_name: str = ""
    result: Any = None
    duration_ms: int = 0
    error: str | None = None
    priority: EventPriority = EventPriority.HIGH


@dataclass
class AgentRoundsLimitReached(BaseEvent):
    """Agent 轮次限制达到事件"""

    dialog_id: str = ""
    rounds: int = 0
    priority: EventPriority = EventPriority.NORMAL
