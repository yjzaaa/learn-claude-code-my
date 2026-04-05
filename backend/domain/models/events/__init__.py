"""
Event Models - 事件模型

定义事件总线使用的事件基类和具体事件类型。
"""

from .base import (
    BaseEvent,
    EventPriority,
    DialogCreated,
    MessageReceived,
    StreamDelta,
    MessageCompleted,
    DialogClosed,
    ToolCallStarted,
    ToolStartData,
    ToolCallCompleted,
    ToolCallFailed,
    SystemStarted,
    SystemStopped,
    ErrorOccurred,
    AgentRoundsLimitReached,
    SkillLoaded,
    SkillUnloaded,
)

from .agent import (
    AgentEvent,
    DialogSnapshotEvent,
    StreamDeltaEvent,
    StatusChangeEvent,
    ToolCallEvent,
    ToolResultEvent,
    ErrorEvent,
    TodoUpdatedEvent,
    TodoReminderEvent,
    RoundsLimitEvent,
    ServerPushEvent,
)

__all__ = [
    # Base
    "BaseEvent",
    "EventPriority",
    "DialogCreated",
    "MessageReceived",
    "StreamDelta",
    "MessageCompleted",
    "DialogClosed",
    "ToolCallStarted",
    "ToolStartData",
    "ToolCallCompleted",
    "ToolCallFailed",
    "SystemStarted",
    "SystemStopped",
    "ErrorOccurred",
    "AgentRoundsLimitReached",
    "SkillLoaded",
    "SkillUnloaded",
    # Agent
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
