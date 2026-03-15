"""
MonitoringEvent - 监控事件领域模型

不可变值对象，用于表示监控系统中的各种事件。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Optional
from uuid import UUID, uuid4


class EventPriority(Enum):
    """事件优先级"""
    CRITICAL = 0   # 系统关键事件：错误、状态变更
    HIGH = 1       # 用户关注事件：消息完成、工具结果
    NORMAL = 2     # 常规事件：token 流、工具调用
    LOW = 3        # 诊断事件：性能指标、调试信息


class EventType(Enum):
    """事件类型枚举"""
    # === Agent 生命周期 ===
    AGENT_STARTED = "agent:started"
    AGENT_STOPPED = "agent:stopped"
    AGENT_ERROR = "agent:error"
    AGENT_PAUSED = "agent:paused"
    AGENT_RESUMED = "agent:resumed"

    # === 消息流事件 ===
    MESSAGE_START = "message:start"
    MESSAGE_DELTA = "message:delta"
    MESSAGE_COMPLETE = "message:complete"
    REASONING_DELTA = "reasoning:delta"

    # === 工具调用事件 ===
    TOOL_CALL_START = "tool_call:start"
    TOOL_CALL_END = "tool_call:end"
    TOOL_CALL_ERROR = "tool_call:error"
    TOOL_RESULT = "tool:result"

    # === 子智能体事件 ===
    SUBAGENT_SPAWNED = "subagent:spawned"
    SUBAGENT_STARTED = "subagent:started"
    SUBAGENT_PROGRESS = "subagent:progress"
    SUBAGENT_COMPLETED = "subagent:completed"
    SUBAGENT_FAILED = "subagent:failed"

    # === 后台任务事件 ===
    BG_TASK_QUEUED = "bg_task:queued"
    BG_TASK_STARTED = "bg_task:started"
    BG_TASK_PROGRESS = "bg_task:progress"
    BG_TASK_COMPLETED = "bg_task:completed"
    BG_TASK_FAILED = "bg_task:failed"

    # === 状态机事件 ===
    STATE_TRANSITION = "state:transition"
    STATE_ENTER = "state:enter"
    STATE_EXIT = "state:exit"

    # === 资源使用事件 ===
    TOKEN_USAGE = "metrics:tokens"
    MEMORY_USAGE = "metrics:memory"
    LATENCY_METRIC = "metrics:latency"

    # === Todo 管理事件 ===
    TODO_CREATED = "todo:created"
    TODO_UPDATED = "todo:updated"
    TODO_COMPLETED = "todo:completed"


@dataclass(frozen=True)
class MonitoringEvent:
    """
    监控事件值对象

    特性:
    - 不可变性 (frozen=True)
    - 唯一标识 (UUID)
    - 层级关系 (parent_id)
    - 优先级支持
    - 完整序列化

    Example:
        >>> event = MonitoringEvent(
        ...     type=EventType.AGENT_STARTED,
        ...     dialog_id="dialog-123",
        ...     source="SFullAgent",
        ...     context_id=uuid4(),
        ...     payload={"agent_name": "TeamLeadAgent"}
        ... )
        >>> child = MonitoringEvent.create_child(
        ...     parent=event,
        ...     type=EventType.SUBAGENT_SPAWNED,
        ...     payload={"subagent_name": "ExploreAgent"}
        ... )
    """

    type: EventType
    dialog_id: str
    source: str
    context_id: UUID
    timestamp: datetime = field(default_factory=datetime.utcnow)
    id: UUID = field(default_factory=uuid4)
    parent_id: Optional[UUID] = None
    priority: EventPriority = EventPriority.NORMAL
    payload: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_child_of(self, parent: MonitoringEvent) -> bool:
        """
        检查是否为指定事件的子事件

        Args:
            parent: 可能的父事件

        Returns:
            True 如果当前事件是 parent 的子事件
        """
        return self.parent_id == parent.id

    def get_duration_ms(self, since: datetime) -> int:
        """
        计算自指定时间以来的毫秒数

        Args:
            since: 起始时间

        Returns:
            毫秒数
        """
        return int((self.timestamp - since).total_seconds() * 1000)

    def to_dict(self) -> dict[str, Any]:
        """
        序列化为字典

        Returns:
            可序列化的字典
        """
        return {
            "id": str(self.id),
            "type": self.type.value,
            "dialog_id": self.dialog_id,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "context_id": str(self.context_id),
            "parent_id": str(self.parent_id) if self.parent_id else None,
            "priority": self.priority.value,
            "payload": self.payload,
            "metadata": self.metadata,
        }

    @staticmethod
    def create_child(
        parent: MonitoringEvent,
        type: EventType,
        payload: dict[str, Any],
        priority: EventPriority = EventPriority.NORMAL,
        metadata: Optional[dict[str, Any]] = None
    ) -> MonitoringEvent:
        """
        工厂方法：创建子事件

        自动继承父事件的 dialog_id, source, context_id
        设置 parent_id 为父事件的 id

        Args:
            parent: 父事件
            type: 子事件类型
            payload: 子事件载荷
            priority: 优先级（默认 NORMAL）
            metadata: 元数据（默认空字典）

        Returns:
            新的子事件实例
        """
        return MonitoringEvent(
            type=type,
            dialog_id=parent.dialog_id,
            source=parent.source,
            context_id=parent.context_id,
            parent_id=parent.id,
            priority=priority,
            payload=payload,
            metadata=metadata or {}
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MonitoringEvent:
        """
        从字典反序列化

        Args:
            data: 序列化的字典

        Returns:
            MonitoringEvent 实例
        """
        return cls(
            id=UUID(data["id"]) if "id" in data else uuid4(),
            type=EventType(data["type"]),
            dialog_id=data["dialog_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.utcnow(),
            source=data["source"],
            context_id=UUID(data["context_id"]),
            parent_id=UUID(data["parent_id"]) if data.get("parent_id") else None,
            priority=EventPriority(data["priority"]) if "priority" in data else EventPriority.NORMAL,
            payload=data.get("payload", {}),
            metadata=data.get("metadata", {})
        )
