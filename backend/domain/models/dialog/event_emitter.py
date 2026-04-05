"""Event Emitter - 事件发射器

处理流式事件的发射和转发。
"""

from typing import Optional, Dict, Any, Callable, Awaitable

from backend.infrastructure.logging import get_logger
from .session import DialogSession

logger = get_logger(__name__)

EventHandler = Callable[['EventEmitter.Event'], Awaitable[None]]


class EventEmitter:
    """事件发射器

    职责:
    - 转发内容 delta（不存储）
    - 转发推理 delta
    - 转发工具调用/结果事件
    """

    class Event:
        """事件数据类"""
        def __init__(
            self,
            type: str,
            dialog_id: str,
            data: Dict[str, Any],
        ):
            self.type = type
            self.dialog_id = dialog_id
            self.data = data

    def __init__(self, event_handler: Optional[EventHandler] = None):
        self._event_handler = event_handler

    async def emit_delta(
        self,
        dialog_id: str,
        delta: str,
        message_id: Optional[str] = None,
    ) -> None:
        """转发内容 delta (不存储)"""
        self._emit(self.Event(
            type="delta",
            dialog_id=dialog_id,
            data={"delta": delta, "message_id": message_id},
        ))

    async def emit_reasoning_delta(
        self,
        dialog_id: str,
        reasoning: str,
        message_id: Optional[str] = None,
    ) -> None:
        """转发推理 delta (不存储)"""
        self._emit(self.Event(
            type="reasoning_delta",
            dialog_id=dialog_id,
            data={"reasoning": reasoning, "message_id": message_id},
        ))

    async def emit_tool_call(
        self,
        dialog_id: str,
        tool_name: str,
        tool_input: Dict[str, Any],
        tool_call_id: Optional[str] = None,
    ) -> None:
        """转发工具调用事件"""
        self._emit(self.Event(
            type="tool_call",
            dialog_id=dialog_id,
            data={
                "name": tool_name,
                "input": tool_input,
                "tool_call_id": tool_call_id,
            },
        ))

    async def emit_tool_result(
        self,
        dialog_id: str,
        tool_call_id: str,
        result: Any,
        duration_ms: Optional[int] = None,
    ) -> None:
        """转发工具结果事件"""
        self._emit(self.Event(
            type="tool_result",
            dialog_id=dialog_id,
            data={
                "tool_call_id": tool_call_id,
                "result": str(result) if result is not None else None,
                "duration_ms": duration_ms,
            },
        ))

    def _emit(self, event: Event) -> None:
        """发送事件"""
        if not self._event_handler:
            return

        import asyncio

        async def _send():
            try:
                await self._event_handler(event)
            except Exception as e:
                logger.error(f"[EventEmitter] Failed to emit event: {e}")

        try:
            asyncio.create_task(_send())
        except Exception as e:
            logger.error(f"[EventEmitter] Failed to create task: {e}")


__all__ = ["EventEmitter"]
