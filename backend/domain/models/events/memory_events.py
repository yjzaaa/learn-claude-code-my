"""
Memory Events - 记忆相关领域事件

定义记忆系统相关的领域事件，用于事件驱动架构。
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any

from backend.domain.models.events.base import BaseEvent, EventPriority
from backend.domain.models.memory.types import MemoryType


@dataclass
class MemoryCreatedEvent(BaseEvent):
    """
    记忆创建事件

    当新记忆被创建时触发。
    """
    memory_id: str = field(default="")
    user_id: str = field(default="")
    project_path: str = field(default="")
    memory_type: MemoryType = field(default=MemoryType.USER)
    name: str = field(default="")
    source_dialog_id: Optional[str] = field(default=None)
    priority: EventPriority = field(default=EventPriority.NORMAL)


@dataclass
class MemoryExtractedEvent(BaseEvent):
    """
    记忆提取事件

    当从对话中提取出新记忆时触发。
    这是 MemoryCreatedEvent 的前置事件，表示提取动作发生。
    """
    memory_id: str = field(default="")
    user_id: str = field(default="")
    project_path: str = field(default="")
    memory_type: MemoryType = field(default=MemoryType.USER)
    name: str = field(default="")
    source_dialog_id: str = field(default="")
    extraction_confidence: float = field(default=1.0)
    raw_extraction: Dict[str, Any] = field(default_factory=dict)
    priority: EventPriority = field(default=EventPriority.NORMAL)


@dataclass
class MemoryRetrievedEvent(BaseEvent):
    """
    记忆检索事件

    当记忆被检索并用于增强提示词时触发。
    用于跟踪记忆的使用情况和效果。
    """
    memory_id: str = field(default="")
    user_id: str = field(default="")
    project_path: str = field(default="")
    query: str = field(default="")
    retrieval_score: float = field(default=0.0)
    target_dialog_id: str = field(default="")
    priority: EventPriority = field(default=EventPriority.LOW)


@dataclass
class MemoryUpdatedEvent(BaseEvent):
    """
    记忆更新事件

    当记忆内容被更新时触发。
    """
    memory_id: str = field(default="")
    user_id: str = field(default="")
    project_path: str = field(default="")
    name: str = field(default="")
    previous_content_hash: str = field(default="")
    priority: EventPriority = field(default=EventPriority.NORMAL)


@dataclass
class MemoryDeletedEvent(BaseEvent):
    """
    记忆删除事件

    当记忆被删除时触发。
    """
    memory_id: str = field(default="")
    user_id: str = field(default="")
    project_path: str = field(default="")
    name: str = field(default="")
    priority: EventPriority = field(default=EventPriority.NORMAL)
