"""
Event Models - 事件模型

定义事件总线使用的事件基类和优先级。
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum
from typing import Any

try:
    from dataclasses_json import dataclass_json  # type: ignore[import-not-found]
except ImportError:

    def dataclass_json(cls):  # type: ignore[no-redef]
        return cls


class EventPriority(IntEnum):
    """事件优先级"""

    CRITICAL = 0  # 关键事件，立即处理
    HIGH = 1  # 高优先级
    NORMAL = 2  # 正常优先级
    LOW = 3  # 低优先级
    BACKGROUND = 4  # 后台任务


@dataclass_json
@dataclass
class BaseEvent:
    """事件基类"""

    timestamp: datetime = field(default_factory=datetime.now)
    priority: EventPriority = field(default=EventPriority.NORMAL)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def event_type(self) -> str:
        """事件类型名称"""
        return self.__class__.__name__


# ═══════════════════════════════════════════════════════════
# Dialog Events
# ═══════════════════════════════════════════════════════════


@dataclass_json
@dataclass
class DialogCreated(BaseEvent):
    """对话创建事件"""

    dialog_id: str = field(default="")
    user_input: str = field(default="")


@dataclass_json
@dataclass
class MessageReceived(BaseEvent):
    """消息接收事件"""

    dialog_id: str = field(default="")
    message_id: str = field(default="")
    content: str = field(default="")
    priority: EventPriority = field(default=EventPriority.HIGH)


@dataclass_json
@dataclass
class StreamDelta(BaseEvent):
    """流式输出增量事件"""

    dialog_id: str = field(default="")
    delta: str = field(default="")
    is_reasoning: bool = field(default=False)
    priority: EventPriority = field(default=EventPriority.HIGH)


@dataclass_json
@dataclass
class MessageCompleted(BaseEvent):
    """消息完成事件"""

    dialog_id: str = field(default="")
    message_id: str = field(default="")
    content: str = field(default="")
    token_count: int = field(default=0)
    priority: EventPriority = field(default=EventPriority.NORMAL)


@dataclass_json
@dataclass
class DialogClosed(BaseEvent):
    """对话关闭事件"""

    dialog_id: str = field(default="")
    reason: str = field(default="completed")
    priority: EventPriority = field(default=EventPriority.NORMAL)


# ═══════════════════════════════════════════════════════════
# Tool Events
# ═══════════════════════════════════════════════════════════


@dataclass_json
@dataclass
class ToolCallStarted(BaseEvent):
    """工具调用开始事件"""

    dialog_id: str = field(default="")
    tool_call_id: str = field(default="")
    tool_name: str = field(default="")
    arguments: dict[str, Any] = field(default_factory=dict)
    priority: EventPriority = field(default=EventPriority.HIGH)


# 别名，用于兼容 simple_runtime.py
ToolStartData = ToolCallStarted


@dataclass_json
@dataclass
class ToolCallCompleted(BaseEvent):
    """工具调用完成事件"""

    dialog_id: str = field(default="")
    tool_call_id: str = field(default="")
    tool_name: str = field(default="")
    result: str = field(default="")
    duration_ms: int = field(default=0)
    priority: EventPriority = field(default=EventPriority.HIGH)


@dataclass_json
@dataclass
class ToolCallFailed(BaseEvent):
    """工具调用失败事件"""

    dialog_id: str = field(default="")
    tool_call_id: str = field(default="")
    tool_name: str = field(default="")
    error: str = field(default="")
    priority: EventPriority = field(default=EventPriority.HIGH)


# ═══════════════════════════════════════════════════════════
# System Events
# ═══════════════════════════════════════════════════════════


@dataclass_json
@dataclass
class SystemStarted(BaseEvent):
    """系统启动事件"""

    version: str = field(default="0.1.0")
    priority: EventPriority = field(default=EventPriority.CRITICAL)


@dataclass_json
@dataclass
class SystemStopped(BaseEvent):
    """系统停止事件"""

    reason: str = field(default="shutdown")
    priority: EventPriority = field(default=EventPriority.CRITICAL)


@dataclass_json
@dataclass
class ErrorOccurred(BaseEvent):
    """错误事件"""

    error_type: str = field(default="")
    error_message: str = field(default="")
    dialog_id: str | None = field(default=None)
    stack_trace: str | None = field(default=None)
    priority: EventPriority = field(default=EventPriority.CRITICAL)


@dataclass_json
@dataclass
class AgentRoundsLimitReached(BaseEvent):
    """Agent 轮次上限事件"""

    dialog_id: str = field(default="")
    rounds: int = field(default=0)
    priority: EventPriority = field(default=EventPriority.HIGH)


# ═══════════════════════════════════════════════════════════
# Skill Events
# ═══════════════════════════════════════════════════════════


@dataclass_json
@dataclass
class SkillLoaded(BaseEvent):
    """技能加载事件"""

    skill_id: str = field(default="")
    name: str = field(default="")
    tool_count: int = field(default=0)
    priority: EventPriority = field(default=EventPriority.NORMAL)


@dataclass_json
@dataclass
class SkillUnloaded(BaseEvent):
    """技能卸载事件"""

    skill_id: str = field(default="")
    priority: EventPriority = field(default=EventPriority.NORMAL)
