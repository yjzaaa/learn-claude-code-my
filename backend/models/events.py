"""
Event Models - 事件模型

定义事件总线使用的事件基类和优先级。
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import IntEnum

try:
    from dataclasses_json import dataclass_json  # type: ignore[import-not-found]
except ImportError:
    def dataclass_json(cls):  # type: ignore[no-redef]
        return cls


class EventPriority(IntEnum):
    """事件优先级"""
    CRITICAL = 0    # 关键事件，立即处理
    HIGH = 1        # 高优先级
    NORMAL = 2      # 正常优先级
    LOW = 3         # 低优先级
    BACKGROUND = 4  # 后台任务


@dataclass_json
@dataclass_json
@dataclass(kw_only=True)
class BaseEvent:
    """事件基类"""
    priority: EventPriority = EventPriority.NORMAL
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def event_type(self) -> str:
        """事件类型名称"""
        return self.__class__.__name__
    


# ═══════════════════════════════════════════════════════════
# Dialog Events
# ═══════════════════════════════════════════════════════════

@dataclass_json
@dataclass_json
@dataclass(kw_only=True)
class DialogCreated(BaseEvent):
    """对话创建事件"""
    dialog_id: str
    user_input: str
    priority: EventPriority = EventPriority.NORMAL


@dataclass_json
@dataclass(kw_only=True)
class MessageReceived(BaseEvent):
    """消息接收事件"""
    dialog_id: str
    message_id: str
    content: str
    priority: EventPriority = EventPriority.HIGH


@dataclass_json
@dataclass(kw_only=True)
class StreamDelta(BaseEvent):
    """流式输出增量事件"""
    dialog_id: str
    delta: str
    is_reasoning: bool = False
    priority: EventPriority = EventPriority.HIGH


@dataclass_json
@dataclass(kw_only=True)
class MessageCompleted(BaseEvent):
    """消息完成事件"""
    dialog_id: str
    message_id: str
    content: str
    token_count: int = 0
    priority: EventPriority = EventPriority.NORMAL


@dataclass_json
@dataclass(kw_only=True)
class DialogClosed(BaseEvent):
    """对话关闭事件"""
    dialog_id: str
    reason: str = "completed"
    priority: EventPriority = EventPriority.NORMAL


# ═══════════════════════════════════════════════════════════
# Tool Events
# ═══════════════════════════════════════════════════════════

@dataclass_json
@dataclass(kw_only=True)
class ToolCallStarted(BaseEvent):
    """工具调用开始事件"""
    dialog_id: str
    tool_call_id: str
    tool_name: str
    arguments: Dict[str, Any] = field(default_factory=dict)
    priority: EventPriority = EventPriority.HIGH


# 别名，用于兼容 simple_runtime.py
ToolStartData = ToolCallStarted


@dataclass_json
@dataclass(kw_only=True)
class ToolCallCompleted(BaseEvent):
    """工具调用完成事件"""
    dialog_id: str
    tool_call_id: str
    tool_name: str
    result: str = ""
    duration_ms: int = 0
    priority: EventPriority = EventPriority.HIGH


@dataclass_json
@dataclass(kw_only=True)
class ToolCallFailed(BaseEvent):
    """工具调用失败事件"""
    dialog_id: str
    tool_call_id: str
    tool_name: str
    error: str = ""
    priority: EventPriority = EventPriority.HIGH


# ═══════════════════════════════════════════════════════════
# System Events
# ═══════════════════════════════════════════════════════════

@dataclass_json
@dataclass(kw_only=True)
class SystemStarted(BaseEvent):
    """系统启动事件"""
    version: str = "0.1.0"
    priority: EventPriority = EventPriority.CRITICAL


@dataclass_json
@dataclass(kw_only=True)
class SystemStopped(BaseEvent):
    """系统停止事件"""
    reason: str = "shutdown"
    priority: EventPriority = EventPriority.CRITICAL


@dataclass_json
@dataclass(kw_only=True)
class ErrorOccurred(BaseEvent):
    """错误事件"""
    error_type: str = ""
    error_message: str = ""
    dialog_id: Optional[str] = None
    stack_trace: Optional[str] = None
    priority: EventPriority = EventPriority.CRITICAL


@dataclass_json
@dataclass(kw_only=True)
class AgentRoundsLimitReached(BaseEvent):
    """Agent 轮次上限事件"""
    dialog_id: str = ""
    rounds: int = 0
    priority: EventPriority = EventPriority.HIGH


# ═══════════════════════════════════════════════════════════
# Skill Events
# ═══════════════════════════════════════════════════════════

@dataclass_json
@dataclass(kw_only=True)
class SkillLoaded(BaseEvent):
    """技能加载事件"""
    skill_id: str
    name: str
    tool_count: int = 0
    priority: EventPriority = EventPriority.NORMAL


@dataclass_json
@dataclass(kw_only=True)
class SkillUnloaded(BaseEvent):
    """技能卸载事件"""
    skill_id: str
    priority: EventPriority = EventPriority.NORMAL
