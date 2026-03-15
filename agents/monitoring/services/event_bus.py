"""
EventBus - 异步事件总线服务

职责:
- 事件分发
- 观察者管理
- 处理器路由
- 优先级队列
"""

from __future__ import annotations

import asyncio
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Optional, Any, Union
from queue import Queue as ThreadQueue
from loguru import logger

try:
    from ..domain.event import MonitoringEvent, EventPriority
    from ...models.common_types import EventBusStats
except ImportError:
    from agents.monitoring.domain.event import MonitoringEvent, EventPriority
    from agents.models.common_types import EventBusStats


class EventObserver(ABC):
    """
    事件观察者接口

    实现此接口以接收事件通知。
    """

    @abstractmethod
    async def on_event(self, event: MonitoringEvent) -> None:
        """
        接收事件通知

        Args:
            event: 监控事件
        """
        raise NotImplementedError


@dataclass
class EventHandler:
    """
    事件处理器

    包含判断条件和处理函数。
    """
    can_handle: Callable[[MonitoringEvent], bool]
    """判断是否能处理该事件的函数"""
    handle: Callable[[MonitoringEvent], None]
    """处理事件的函数"""


class EventBus:
    """
    事件总线

    基于优先级队列的异步事件分发系统。
    支持观察者模式和处理器路由。

    Example:
        >>> bus = EventBus()
        >>>
        >>> class MyObserver(EventObserver):
        ...     async def on_event(self, event):
        ...         print(f"Received: {event.type}")
        >>>
        >>> observer = MyObserver()
        >>> bus.subscribe(observer, EventType.AGENT_STARTED)
        >>>
        >>> asyncio.create_task(bus.start_processing())
        >>> await bus.emit(event)
    """

    def __init__(self):
        # 优先级队列: (priority, timestamp, event)
        self._queue: asyncio.PriorityQueue[tuple[int, float, MonitoringEvent]] = asyncio.PriorityQueue()

        # 线程安全队列用于从子线程接收事件
        self._thread_queue: ThreadQueue = ThreadQueue()

        # 类型特定的观察者: event_type -> list of observers
        self._observers: Dict[str, List[EventObserver]] = {}

        # 全局观察者: 接收所有事件
        self._global_observers: List[EventObserver] = []

        # 事件处理器
        self._handlers: List[EventHandler] = []

        # 运行状态
        self._running: bool = False

        # WebSocket 处理器钩子
        self._websocket_handler: Optional[Callable[[MonitoringEvent], Union[None, Any]]] = None

        # 处理任务引用
        self._processing_task: Optional[asyncio.Task] = None

        # 主线程事件循环引用（用于从子线程调度）
        self._main_loop: Optional[asyncio.AbstractEventLoop] = None

    async def emit(self, event: MonitoringEvent) -> None:
        """
        发布事件到优先级队列（异步，必须在主线程事件循环中调用）

        Args:
            event: 要发布的事件
        """
        await self._queue.put((
            event.priority.value,
            event.timestamp.timestamp(),
            event
        ))
        logger.debug(f"[EventBus] Event queued: {event.type.value} (priority={event.priority.name})")

    def emit_sync(self, event: MonitoringEvent) -> None:
        """
        线程安全地发布事件（可从任何线程调用）

        Args:
            event: 要发布的事件
        """
        current_thread = threading.current_thread()
        thread_name = current_thread.name

        # 检查是否已经在主线程
        if current_thread is threading.main_thread():
            # 在主线程，直接使用异步方法
            try:
                loop = asyncio.get_running_loop()
                if loop.is_running():
                    asyncio.create_task(self.emit(event))
                    logger.info(f"[EventBus] Event emitted from main thread: {event.type.value}")
            except RuntimeError:
                logger.warning(f"[EventBus] No running loop in main thread, event dropped: {event.type.value}")
        else:
            # 在子线程，放入线程队列
            logger.info(f"[EventBus] Event queued from sub-thread ({thread_name}): {event.type.value}, dialog_id={event.dialog_id}")
            self._thread_queue.put(event)
            logger.info(f"[EventBus] Event added to thread queue, queue size: {self._thread_queue.qsize()}")

    async def start_processing(self) -> None:
        """
        启动事件处理循环

        在后台启动一个任务，持续从队列中取出事件并分发。
        """
        if self._running:
            logger.warning("[EventBus] Already running")
            return

        self._running = True
        self._main_loop = asyncio.get_running_loop()
        self._processing_task = asyncio.create_task(self._process_loop())
        logger.info("[EventBus] Processing started")

    async def stop_processing(self) -> None:
        """
        停止事件处理循环

        优雅地停止处理，等待当前事件处理完成。
        """
        if not self._running:
            return

        self._running = False

        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
            self._processing_task = None

        logger.info("[EventBus] Processing stopped")

    async def _process_loop(self) -> None:
        """
        事件处理主循环

        从优先级队列中取出事件并分发。
        """
        logger.info("[EventBus] Process loop started")
        loop_count = 0
        while self._running:
            loop_count += 1
            try:
                # 首先检查线程队列（从子线程接收的事件）
                if not self._thread_queue.empty():
                    try:
                        event = self._thread_queue.get_nowait()
                        logger.info(f"[EventBus] Processing event from thread queue: {event.type.value}")
                        await self._dispatch(event)
                        continue
                    except Exception as e:
                        logger.error(f"[EventBus] Error dispatching thread event: {e}")

                # 等待事件，超时1秒以便检查_running状态和线程队列
                try:
                    priority, timestamp, event = await asyncio.wait_for(
                        self._queue.get(), timeout=1.0
                    )
                    logger.info(f"[EventBus] Processing event from async queue: {event.type.value}")
                    await self._dispatch(event)
                except asyncio.TimeoutError:
                    # 超时，继续循环检查_running
                    continue

            except Exception as e:
                logger.error(f"[EventBus] Error in process loop: {e}")
        logger.info(f"[EventBus] Process loop ended, processed {loop_count} iterations")

    async def _dispatch(self, event: MonitoringEvent) -> None:
        """
        分发事件到所有观察者

        Args:
            event: 要分发的事件
        """
        logger.info(f"[EventBus] Dispatching: {event.type.value}, dialog_id={event.dialog_id}")

        # 1. WebSocket 广播（如果设置了）
        if self._websocket_handler:
            try:
                logger.info(f"[EventBus] Calling WebSocket handler for: {event.type.value}")
                # WebSocket handler may be sync or async
                result = self._websocket_handler(event)
                if asyncio.iscoroutine(result):
                    await result
                logger.info(f"[EventBus] WebSocket handler completed for: {event.type.value}")
            except Exception as e:
                logger.error(f"[EventBus] WebSocket handler error: {e}")
        else:
            logger.warning(f"[EventBus] No WebSocket handler set for event: {event.type.value}")

        # 2. 特定类型的观察者
        for observer in self._observers.get(event.type.value, []):
            try:
                await observer.on_event(event)
            except Exception as e:
                logger.error(f"[EventBus] Observer error: {e}")

        # 3. 全局观察者
        for observer in self._global_observers:
            try:
                await observer.on_event(event)
            except Exception as e:
                logger.error(f"[EventBus] Global observer error: {e}")

        # 4. 处理器路由
        for handler in self._handlers:
            try:
                if handler.can_handle(event):
                    handler.handle(event)
            except Exception as e:
                logger.error(f"[EventBus] Handler error: {e}")

    def subscribe(
        self,
        observer: EventObserver,
        event_type: Optional[Any] = None
    ) -> None:
        """
        订阅事件

        Args:
            observer: 事件观察者
            event_type: 要订阅的事件类型，None表示订阅所有事件
        """
        if event_type is None:
            self._global_observers.append(observer)
            logger.debug(f"[EventBus] Global subscriber added: {type(observer).__name__}")
        else:
            # 支持 EventType enum 或字符串
            type_key = event_type.value if hasattr(event_type, 'value') else str(event_type)
            if type_key not in self._observers:
                self._observers[type_key] = []
            self._observers[type_key].append(observer)
            logger.debug(f"[EventBus] Subscriber added for {type_key}: {type(observer).__name__}")

    def unsubscribe(
        self,
        observer: EventObserver,
        event_type: Optional[Any] = None
    ) -> bool:
        """
        取消订阅

        Args:
            observer: 要取消的观察者
            event_type: 要取消订阅的事件类型，None表示从全局取消

        Returns:
            True 如果成功找到并移除
        """
        if event_type is None:
            if observer in self._global_observers:
                self._global_observers.remove(observer)
                return True
        else:
            type_key = event_type.value if hasattr(event_type, 'value') else str(event_type)
            if type_key in self._observers and observer in self._observers[type_key]:
                self._observers[type_key].remove(observer)
                return True
        return False

    def add_handler(self, handler: EventHandler) -> None:
        """
        添加事件处理器

        Args:
            handler: 事件处理器
        """
        self._handlers.append(handler)
        logger.debug(f"[EventBus] Handler added: {handler}")

    def remove_handler(self, handler: EventHandler) -> bool:
        """
        移除事件处理器

        Args:
            handler: 要移除的处理器

        Returns:
            True 如果成功移除
        """
        if handler in self._handlers:
            self._handlers.remove(handler)
            return True
        return False

    def set_websocket_handler(self, handler: Callable[[MonitoringEvent], Union[None, Any]]) -> None:
        """
        设置 WebSocket 处理器

        该处理器会接收到所有事件，用于向前端广播。

        Args:
            handler: 处理函数
        """
        self._websocket_handler = handler
        logger.info("[EventBus] WebSocket handler set")

    def get_stats(self) -> dict[str, Any]:
        """
        获取统计信息

        Returns:
            统计字典
        """
        stats = EventBusStats(
            running=self._running,
            queue_size=self._queue.qsize(),
            typed_observers={k: len(v) for k, v in self._observers.items()},
            global_observers=len(self._global_observers),
            handlers=len(self._handlers),
        )
        return stats.model_dump()


# 全局事件总线实例
event_bus = EventBus()
