"""Event Handlers - 事件处理器

处理事件驱动架构中的各种事件。
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from backend.infrastructure.container import container
from backend.domain.models.events.agent_events import (
    AgentExecuteRequest,
    AgentProgressEvent,
    AgentCompleteEvent,
    AgentErrorEvent,
)
from backend.domain.models.types import (
    WSSnapshotEvent,
    WSStreamDeltaEvent,
    WSDeltaContent,
    WSErrorEvent,
    WSErrorDetail,
    WSRoundsLimitEvent,
    make_status_change,
)
from backend.domain.services.dialog_service import (
    timestamp_ms,
    build_dialog_snapshot,
    create_streaming_placeholder,
)

if TYPE_CHECKING:
    from backend.infrastructure.event_bus import QueuedEventBus

logger = logging.getLogger(__name__)


class EventHandlers:
    """事件处理器集合

    集中管理所有事件处理器。
    """

    def __init__(self, event_bus: QueuedEventBus | None = None):
        self.event_bus = event_bus
        self._subscribed = False

    def register_all(self) -> None:
        """注册所有事件处理器"""
        if not self.event_bus or self._subscribed:
            return

        # 订阅 Agent 执行相关事件
        self.event_bus.subscribe(
            self._handle_agent_progress,
            event_types=["AgentProgressEvent"]
        )
        self.event_bus.subscribe(
            self._handle_agent_complete,
            event_types=["AgentCompleteEvent"]
        )
        self.event_bus.subscribe(
            self._handle_agent_error,
            event_types=["AgentErrorEvent"]
        )
        self.event_bus.subscribe(
            self._handle_execute_request,
            event_types=["AgentExecuteRequest"]
        )

        # 订阅原有事件
        self.event_bus.subscribe(
            self._on_rounds_limit,
            event_types=["AgentRoundsLimitReached"]
        )

        self._subscribed = True
        logger.info("[EventHandlers] All handlers registered")

    async def _handle_agent_progress(self, event: AgentProgressEvent) -> None:
        """处理 Agent 进度事件"""
        from backend.interfaces.websocket.broadcast import broadcast

        dialog_id = event.dialog_id
        msg_id = event.message_id

        # 更新累积内容
        container.append_accumulated(dialog_id, event.delta)

        # 更新流式消息
        sm = container.get_streaming_message(dialog_id)
        if sm is not None:
            sm["content"] = event.accumulated

        # 广播增量
        delta_sequence = len(event.accumulated)
        await broadcast(WSStreamDeltaEvent(
            type="stream:delta",
            dialog_id=dialog_id,
            message_id=msg_id,
            delta=WSDeltaContent(content=event.delta, reasoning=""),
            timestamp=timestamp_ms(),
            sequence=delta_sequence,
        ))

    async def _handle_agent_complete(self, event: AgentCompleteEvent) -> None:
        """处理 Agent 完成事件"""
        from backend.interfaces.websocket.broadcast import broadcast

        dialog_id = event.dialog_id

        # 发送状态变更
        container.set_status(dialog_id, "completed")
        await broadcast(make_status_change(dialog_id, "thinking", "completed", timestamp_ms()))

        # 清理
        container.set_streaming_message(dialog_id, None)
        container.set_status(dialog_id, "idle")

    async def _handle_agent_error(self, event: AgentErrorEvent) -> None:
        """处理 Agent 错误事件"""
        from backend.interfaces.websocket.broadcast import broadcast

        dialog_id = event.dialog_id

        container.set_streaming_message(dialog_id, None)
        container.set_status(dialog_id, "error")

        await broadcast(WSErrorEvent(
            type="error",
            dialog_id=dialog_id,
            error=WSErrorDetail(code=event.error_type, message=event.error_message),
            timestamp=timestamp_ms(),
        ))
        await broadcast(make_status_change(dialog_id, "thinking", "error", timestamp_ms()))

    async def _handle_execute_request(self, event: AgentExecuteRequest) -> None:
        """处理 Agent 执行请求"""
        dialog_id = event.dialog_id
        content = event.content
        message_id = event.message_id

        # 设置状态
        container.set_status(dialog_id, "thinking")
        container.set_streaming_message(
            dialog_id,
            create_streaming_placeholder(message_id)
        )

        from backend.interfaces.websocket.broadcast import broadcast
        await broadcast(make_status_change(dialog_id, "idle", "thinking", timestamp_ms()))

        # 广播 snapshot，让前端获取 streaming_message
        if container.session_manager:
            snap = build_dialog_snapshot(
                dialog_id,
                container.session_manager,
                container.get_status(dialog_id),
                container.get_streaming_message(dialog_id)
            )
            if snap:
                await broadcast(WSSnapshotEvent(
                    type="dialog:snapshot",
                    data=snap,
                    timestamp=timestamp_ms(),
                ))

        # 执行 Agent
        runtime = container.runtime
        if not runtime:
            logger.error("[EventHandlers] Runtime not available")
            return

        try:
            async for runtime_event in runtime.send_message(
                dialog_id, content, stream=True, message_id=message_id
            ):
                if runtime_event.type == "text_delta":
                    chunk = runtime_event.data
                    if isinstance(chunk, list):
                        chunk = "".join(str(c) for c in chunk)
                    elif not isinstance(chunk, str):
                        chunk = str(chunk)

                    # 更新累积内容
                    accumulated = container.append_accumulated(dialog_id, chunk)

                    # 发射进度事件
                    if self.event_bus:
                        await self.event_bus.emit(
                            AgentProgressEvent(
                                dialog_id=dialog_id,
                                message_id=message_id,
                                delta=chunk,
                                accumulated=accumulated,
                            ),
                            timeout=0.5,
                        )

                elif runtime_event.type == "complete":
                    # 发送完成事件
                    if self.event_bus:
                        await self.event_bus.emit(
                            AgentCompleteEvent(
                                dialog_id=dialog_id,
                                message_id=message_id,
                                final_content=container.get_accumulated(dialog_id),
                            ),
                            timeout=0.5,
                        )

                elif runtime_event.type == "error":
                    raise Exception(str(runtime_event.data))

        except Exception as exc:
            logger.exception("[EventHandlers] Error running dialog %s: %s", dialog_id, exc)
            if self.event_bus:
                await self.event_bus.emit(
                    AgentErrorEvent(
                        dialog_id=dialog_id,
                        message_id=message_id,
                        error_type="agent_error",
                        error_message=str(exc),
                    ),
                    timeout=0.5,
                )

    async def _on_rounds_limit(self, event) -> None:
        """处理轮次限制事件"""
        from backend.interfaces.websocket.broadcast import broadcast

        await broadcast(WSRoundsLimitEvent(
            type="agent:rounds_limit_reached",
            dialog_id=event.dialog_id,
            rounds=event.rounds,
            timestamp=timestamp_ms(),
        ))


__all__ = ["EventHandlers"]
