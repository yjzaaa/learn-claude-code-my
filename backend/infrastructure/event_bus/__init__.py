"""Event Bus with AsyncQueue integration.

提供基于 AsyncQueue 的背压控制事件总线。

Classes:
    QueuedEventBus: 使用队列缓冲的事件总线，防止高并发时任务爆炸
"""

from .queued_event_bus import QueuedEventBus

__all__ = ["QueuedEventBus"]
