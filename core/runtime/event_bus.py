"""
EventBus - 统一事件总线

解耦模块间通信，支持过滤订阅。
基于 Hanako 架构设计思想。
"""

import asyncio
import logging
from typing import Callable, Optional, List, Dict, Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

from core.models.events import BaseEvent, EventPriority
from core.models.types import EventBusStatsDict

logger = logging.getLogger(__name__)


@dataclass
class EventFilter:
    """事件过滤器"""
    event_types: Optional[List[str]] = None
    dialog_id: Optional[str] = None
    min_priority: EventPriority = EventPriority.BACKGROUND
    
    def matches(self, event: BaseEvent) -> bool:
        """检查事件是否匹配过滤器"""
        # 检查优先级 (数值越小优先级越高)
        if event.priority.value > self.min_priority.value:
            return False
        
        # 检查事件类型
        if self.event_types:
            if event.event_type not in self.event_types:
                return False
        
        # 检查对话 ID (事件无 dialog_id 字段时放行)
        if self.dialog_id:
            event_dialog_id: Optional[str] = getattr(event, 'dialog_id', None)
            if event_dialog_id is not None and event_dialog_id != self.dialog_id:
                return False
        
        return True


class EventBus:
    """
    事件总线 - 发布订阅模式
    
    解耦模块间通信，支持:
    - 异步事件分发
    - 按类型/优先级过滤订阅
    - 按对话 ID 过滤订阅
    """
    
    def __init__(self, max_workers: int = 4):
        self._subscribers: Dict[str, List[tuple[int, Callable, EventFilter]]] = {}
        self._global_subscribers: List[tuple[int, Callable, EventFilter]] = []
        self._next_id = 0
        self._lock = asyncio.Lock()
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._running = True
    
    def subscribe(
        self,
        callback: Callable[[BaseEvent], Any],
        event_types: Optional[List[str]] = None,
        dialog_id: Optional[str] = None,
        min_priority: EventPriority = EventPriority.BACKGROUND
    ) -> Callable:
        """
        订阅事件
        
        Args:
            callback: 回调函数 (event) -> None
            event_types: 只接收这些类型的事件
            dialog_id: 只接收该对话的事件
            min_priority: 只接收该优先级及以上的事件
            
        Returns:
            取消订阅函数
        """
        self._next_id += 1
        sub_id = self._next_id
        
        filter_obj = EventFilter(
            event_types=event_types,
            dialog_id=dialog_id,
            min_priority=min_priority
        )
        
        # 如果有特定类型，按类型索引；否则加入全局订阅者
        if event_types and len(event_types) == 1:
            event_type = event_types[0]
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append((sub_id, callback, filter_obj))
        else:
            self._global_subscribers.append((sub_id, callback, filter_obj))
        
        logger.debug(f"[EventBus] Subscriber {sub_id} registered for types={event_types}, dialog={dialog_id}")
        
        # 返回取消订阅函数
        def unsubscribe():
            self._unsubscribe(sub_id, event_types)
        
        return unsubscribe
    
    def _unsubscribe(self, sub_id: int, event_types: Optional[List[str]]):
        """取消订阅"""
        if event_types and len(event_types) == 1:
            event_type = event_types[0]
            if event_type in self._subscribers:
                self._subscribers[event_type] = [
                    s for s in self._subscribers[event_type] if s[0] != sub_id
                ]
        else:
            self._global_subscribers = [
                s for s in self._global_subscribers if s[0] != sub_id
            ]
        logger.debug(f"[EventBus] Subscriber {sub_id} unregistered")
    
    def emit(self, event: BaseEvent) -> None:
        """
        发射事件 (异步分发，不等待)
        
        Args:
            event: 要发射的事件
        """
        if not self._running:
            logger.warning("[EventBus] Cannot emit event, bus is stopped")
            return
        
        # 异步分发，不阻塞发射者
        asyncio.create_task(self._dispatch(event, async_mode=True))
    
    async def _dispatch(self, event: BaseEvent, async_mode: bool = True):
        """分发事件到所有匹配的订阅者
        
        Args:
            event: 事件
            async_mode: 是否异步处理非关键事件
        """
        event_type = event.event_type
        
        # 收集匹配的订阅者
        callbacks: List[tuple[Callable, BaseEvent]] = []
        
        # 特定类型订阅者
        if event_type in self._subscribers:
            for sub_id, callback, filter_obj in self._subscribers[event_type]:
                if filter_obj.matches(event):
                    callbacks.append((callback, event))
        
        # 全局订阅者
        for sub_id, callback, filter_obj in self._global_subscribers:
            if filter_obj.matches(event):
                callbacks.append((callback, event))
        
        # 分发
        if not callbacks:
            return
        
        # 高优先级事件始终同步处理
        if event.priority == EventPriority.CRITICAL or not async_mode:
            for callback, evt in callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(evt)
                    else:
                        callback(evt)
                except Exception as e:
                    logger.exception(f"[EventBus] Error in event handler: {e}")
        else:
            # 其他优先级异步处理
            tasks = []
            for callback, evt in callbacks:
                tasks.append(asyncio.create_task(self._handle_callback(callback, evt)))
            # 等待所有任务完成
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _handle_callback(self, callback: Callable, event: BaseEvent):
        """处理单个回调"""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(event)
            else:
                # 在线程池中运行同步回调
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(self._executor, callback, event)
        except Exception as e:
            logger.exception(f"[EventBus] Error in event handler: {e}")
    
    async def emit_and_wait(self, event: BaseEvent, timeout: Optional[float] = None) -> None:
        """
        发射事件并等待所有处理器完成
        
        Args:
            event: 要发射的事件
            timeout: 超时时间 (秒)
        """
        if not self._running:
            return
        
        # Dispatch in sync mode (wait for all handlers)
        if timeout:
            await asyncio.wait_for(self._dispatch(event, async_mode=False), timeout=timeout)
        else:
            await self._dispatch(event, async_mode=False)
    
    def shutdown(self):
        """关闭事件总线"""
        self._running = False
        self._executor.shutdown(wait=True)
        logger.info("[EventBus] Shutdown complete")
    
    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._running
    
    def get_stats(self) -> EventBusStatsDict:
        """获取统计信息"""
        return EventBusStatsDict(
            running=self._running,
            typed_subscribers={
                k: len(v) for k, v in self._subscribers.items()
            },
            global_subscribers=len(self._global_subscribers),
            total_subscribers=sum(len(v) for v in self._subscribers.values()) + len(self._global_subscribers),
        )
