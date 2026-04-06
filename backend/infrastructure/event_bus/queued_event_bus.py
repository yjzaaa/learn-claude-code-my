"""QueuedEventBus - 基于 AsyncQueue 的背压控制事件总线

使用 AsyncQueue 作为内部缓冲，实现事件发射的背压控制，
防止高并发场景下创建大量未受控的 asyncio.Task。

Example:
    >>> from backend.infrastructure.event_bus import QueuedEventBus
    >>> from backend.domain.models.events import BaseEvent
    >>>
    >>> # 创建带队列的事件总线
    >>> event_bus = QueuedEventBus(maxsize=1000, num_consumers=3)
    >>> await event_bus.start()
    >>>
    >>> # 订阅事件
    >>> def handler(event: BaseEvent):
    ...     print(f"Received: {event}")
    >>> unsubscribe = event_bus.subscribe(handler, event_types=["message"])
    >>>
    >>> # 发射事件（带背压）
    >>> await event_bus.emit(MyEvent())  # 队列满时会等待
    >>>
    >>> await event_bus.shutdown()
"""

import asyncio
from collections.abc import Callable
from typing import Any

from backend.domain.models.events import BaseEvent
from backend.infrastructure.logging import get_logger
from backend.infrastructure.queue import InMemoryAsyncQueue, QueueFull

logger = get_logger(__name__)


class QueuedEventBus:
    """基于 AsyncQueue 的背压控制事件总线

    使用 AsyncQueue 作为内部缓冲，实现：
    - 背压控制：队列满时 emit 操作阻塞等待
    - 并发控制：可配置消费者数量限制并发处理
    - 优雅关闭：shutdown 时等待队列排空

    Attributes:
        maxsize: 队列最大容量，0 表示无限制
        num_consumers: 并发消费者数量
        _event_queue: 内部事件队列
        _subscribers: 事件订阅者列表
        _running: 是否正在运行

    Example:
        >>> bus = QueuedEventBus(maxsize=1000, num_consumers=3)
        >>> await bus.start()
        >>> await bus.emit(MyEvent())
        >>> await bus.shutdown()
    """

    def __init__(self, maxsize: int = 1000, num_consumers: int = 3):
        """初始化 QueuedEventBus

        Args:
            maxsize: 队列最大容量，0 表示无限制（默认 1000）
            num_consumers: 并发消费者数量（默认 3）
        """
        self.maxsize = maxsize
        self.num_consumers = num_consumers
        self._event_queue: InMemoryAsyncQueue[BaseEvent] = InMemoryAsyncQueue(maxsize=maxsize)
        self._subscribers: list[tuple[str, Callable[[BaseEvent], Any], list[str] | None]] = []
        self._running = False
        self._consumer_tasks: list[asyncio.Task] = []
        self._sub_id_counter = 0

    async def start(self) -> None:
        """启动事件总线，启动消费者任务"""
        if self._running:
            return

        self._running = True
        self._consumer_tasks = [
            asyncio.create_task(self._consumer_loop()) for _ in range(self.num_consumers)
        ]
        logger.info(f"[QueuedEventBus] Started with {self.num_consumers} consumers")

    async def shutdown(self) -> None:
        """优雅关闭事件总线

        关闭流程：
        1. 停止接收新事件
        2. 等待现有队列排空
        3. 取消消费者任务
        4. 清理资源
        """
        if not self._running:
            return

        self._running = False
        logger.info("[QueuedEventBus] Shutting down...")

        # 等待队列排空（最多 5 秒）
        for _ in range(50):  # 5 seconds * 10 checks/sec
            if self._event_queue.empty():
                break
            await asyncio.sleep(0.1)

        # 取消消费者任务
        for task in self._consumer_tasks:
            task.cancel()

        # 等待任务完成
        if self._consumer_tasks:
            await asyncio.gather(*self._consumer_tasks, return_exceptions=True)

        self._consumer_tasks.clear()
        logger.info("[QueuedEventBus] Shutdown complete")

    def subscribe(
        self,
        callback: Callable[[BaseEvent], Any],
        event_types: list[str] | None = None,
    ) -> Callable[[], None]:
        """订阅事件

        与现有 EventBus API 兼容。

        Args:
            callback: 事件处理回调函数
            event_types: 只接收这些类型的事件，None 表示接收所有

        Returns:
            取消订阅函数
        """
        self._sub_id_counter += 1
        sub_id = f"sub_{self._sub_id_counter}"

        self._subscribers.append((sub_id, callback, event_types))
        logger.debug(f"[QueuedEventBus] Subscriber {sub_id} registered for {event_types}")

        def unsubscribe() -> None:
            self._subscribers = [
                (sid, cb, et) for sid, cb, et in self._subscribers if sid != sub_id
            ]
            logger.debug(f"[QueuedEventBus] Subscriber {sub_id} unregistered")

        return unsubscribe

    async def emit(self, event: BaseEvent, timeout: float | None = None) -> bool:
        """发射事件（带背压控制）

        将事件加入队列，等待消费者处理。
        队列满时会阻塞等待（背压）。

        Args:
            event: 要发射的事件
            timeout: 最大等待秒数，None 表示无限等待

        Returns:
            True 表示成功入队，False 表示超时

        Raises:
            RuntimeError: 如果事件总线未启动
        """
        if not self._running:
            raise RuntimeError("EventBus not started. Call start() first.")

        try:
            logger.debug(f"[emit] Enqueuing event: type={event.event_type}")
            await self._event_queue.enqueue(event, timeout=timeout)
            logger.debug(f"[emit] Event enqueued: type={event.event_type}")
            return True
        except TimeoutError:
            logger.warning(f"[QueuedEventBus] Emit timeout for event {event.event_type}")
            return False

    def emit_nowait(self, event: BaseEvent) -> bool:
        """非阻塞发射事件

        队列满时立即返回 False，不等待。

        Args:
            event: 要发射的事件

        Returns:
            True 表示成功入队，False 表示队列已满
        """
        if not self._running:
            raise RuntimeError("EventBus not started. Call start() first.")

        try:
            asyncio.create_task(self._event_queue.enqueue(event, block=False))
            return True
        except QueueFull:
            return False

    async def _consumer_loop(self) -> None:
        """消费者循环，从队列消费事件并分发给订阅者"""
        while self._running:
            try:
                async for event in self._event_queue.consume():
                    await self._dispatch(event)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"[QueuedEventBus] Consumer error: {e}")

    async def _dispatch(self, event: BaseEvent) -> None:
        """分发事件到匹配的订阅者"""
        logger.debug(
            f"[_dispatch] Dispatching event: type={event.event_type}, subscribers={len(self._subscribers)}"
        )
        matched = False
        for sub_id, callback, event_types in self._subscribers:
            # 检查事件类型匹配
            if event_types and event.event_type not in event_types:
                logger.debug(
                    f"[_dispatch] Skipping {sub_id}: {event.event_type} not in {event_types}"
                )
                continue
            matched = True
            logger.debug(f"[_dispatch] Calling {sub_id} for {event.event_type}")

            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
                logger.debug(f"[_dispatch] {sub_id} completed successfully")
            except Exception as e:
                logger.exception(f"[QueuedEventBus] Handler error: {e}")
        if not matched:
            # 忽略 WebSocket 广播事件（这些事件直接发送到客户端，不需要 EventBus 处理）
            if event.event_type not in (
                "stream:delta",
                "status:change",
                "dialog:snapshot",
                "agent:tool_call",
                "agent:tool_result",
                "error",
            ):
                logger.warning(f"[_dispatch] No subscriber matched for event {event.event_type}")

    @property
    def is_running(self) -> bool:
        """事件总线是否正在运行"""
        return self._running

    def get_stats(self) -> dict:
        """获取队列统计信息

        Returns:
            包含队列深度、消费者数、订阅者数的字典
        """
        return {
            "running": self._running,
            "queue_size": self._event_queue.qsize(),
            "queue_maxsize": self.maxsize,
            "num_consumers": len(self._consumer_tasks),
            "num_subscribers": len(self._subscribers),
        }
