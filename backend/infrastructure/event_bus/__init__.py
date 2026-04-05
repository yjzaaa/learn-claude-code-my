"""Event Bus with AsyncQueue integration.

提供基于 AsyncQueue 的背压控制事件总线。

Classes:
    EventBus: 基础事件总线，支持过滤订阅
    QueuedEventBus: 使用队列缓冲的事件总线，防止高并发时任务爆炸
"""

from .core import EventBus, EventFilter
from .queued_event_bus import QueuedEventBus

__all__ = ["EventBus", "EventFilter", "QueuedEventBus"]
