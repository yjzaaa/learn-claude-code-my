"""
WebSocket Manager - WebSocket 事件格式化

【注意】广播已统一由 EventHandlers 处理
此模块仅保留事件格式化功能，供参考使用
"""

from typing import Any, Optional, Union

from langchain_core.messages import BaseMessage, message_to_dict
from pydantic import BaseModel

from backend.domain.models.events.websocket import (
    WSSnapshotEvent,
    WSDialogSnapshot,
    WSDialogMetadata,
    WSStreamTruncatedEvent,
    WSAckEvent,
    WSErrorEvent,
    WSStatusChangeEvent,
    WSMessageAddedEvent,
    WSNodeUpdateEvent,
    WSErrorDetail,
)


class WebSocketBroadcaster:
    """WebSocket 事件广播器 - 使用 LangChain 标准格式

    统一使用 broadcast.py 的缓冲广播系统。
    """

    async def broadcast(self, event: Union[BaseModel, dict]) -> None:
        """广播事件到 WebSocket 客户端

        统一使用 broadcast.py 的广播系统（带缓冲和流量控制）
        """
        from backend.interfaces.websocket.broadcast import broadcast as _broadcast

        if isinstance(event, BaseModel):
            event_dict = event.model_dump(by_alias=True)
        else:
            event_dict = event

        await _broadcast(event_dict)

    async def broadcast_snapshot(
        self,
        dialog_id: str,
        messages: list[BaseMessage],
        metadata: Optional[WSDialogMetadata] = None
    ) -> None:
        """广播对话快照 - 使用 LangChain 格式"""
        snapshot = WSDialogSnapshot(
            id=dialog_id,
            title="Dialog",
            status="active",
            messages=[message_to_dict(m) for m in messages],
            metadata=metadata or WSDialogMetadata(
                model="",
                agent_name="Agent"
            ),
            created_at="",
            updated_at=""
        )
        event = WSSnapshotEvent(
            dialog_id=dialog_id,
            data=snapshot,
            timestamp=self._ts()
        )
        await self.broadcast(event)

    async def broadcast_delta(
        self,
        dialog_id: str,
        message_id: str,
        content: str = "",
        reasoning: str = "",
    ) -> None:
        """广播流式增量

        Args:
            dialog_id: 对话 ID
            message_id: 消息 ID
            content: 文本内容增量
            reasoning: 推理内容增量
        """
        # 统一格式：delta 包含 content 和 reasoning
        event = {
            "type": "stream:delta",
            "dialog_id": dialog_id,
            "message_id": message_id,
            "chunkIndex": 0,
            "delta": {
                "content": content,
                "reasoning": reasoning,
            },
            "timestamp": self._ts()
        }
        await self.broadcast(event)

    async def broadcast_status_change(
        self,
        dialog_id: str,
        from_status: str,
        to_status: str
    ) -> None:
        """广播状态变更"""
        event = WSStatusChangeEvent.model_validate({
            "type": "status:change",
            "dialog_id": dialog_id,
            "from": from_status,
            "to": to_status,
            "timestamp": self._ts(),
        })
        await self.broadcast(event)

    async def broadcast_stream_start(
        self,
        dialog_id: str,
        message_id: str,
        message: Optional[BaseMessage] = None
    ) -> None:
        """广播流开始 - 使用 LangChain 格式"""
        # 提取 role 和 metadata 以匹配前端格式
        role = "assistant"
        metadata = {}
        if message:
            if hasattr(message, 'type'):
                role = message.type
            elif isinstance(message, dict):
                role = message.get('type', 'assistant')

        # 前端期望的格式
        event = {
            "type": "stream:start",
            "dialog_id": dialog_id,
            "message_id": message_id,
            "role": role,
            "metadata": metadata,
            "timestamp": self._ts()
        }
        await self.broadcast(event)

    async def broadcast_stream_end(
        self,
        dialog_id: str,
        message_id: str,
        message: Optional[BaseMessage] = None
    ) -> None:
        """广播流结束 - 使用 LangChain 格式"""
        # 提取消息内容
        final_content = ""
        if message:
            if hasattr(message, 'content'):
                final_content = message.content
            elif isinstance(message, dict):
                final_content = message.get('content', '')

        # 前端期望 camelCase 字段名
        event = {
            "type": "stream:end",
            "dialog_id": dialog_id,
            "message_id": message_id,
            "finalContent": final_content,  # camelCase 匹配前端
            "timestamp": self._ts()
        }
        await self.broadcast(event)

    async def broadcast_stream_truncated(
        self,
        dialog_id: str,
        message_id: str,
        reason: str
    ) -> None:
        """广播流截断"""
        event = WSStreamTruncatedEvent(
            dialog_id=dialog_id,
            message_id=message_id,
            reason=reason,
            timestamp=self._ts()
        )
        await self.broadcast(event)

    async def broadcast_ack(
        self,
        dialog_id: str,
        client_id: str,
        message: Optional[BaseMessage] = None
    ) -> None:
        """广播消息确认 - 使用 LangChain 格式"""
        event = WSAckEvent(
            dialog_id=dialog_id,
            client_id=client_id,
            message=message_to_dict(message) if message else None,
            timestamp=self._ts()
        )
        await self.broadcast(event)

    async def broadcast_error(
        self,
        dialog_id: str,
        code: str,
        message: str
    ) -> None:
        """广播错误"""
        event = WSErrorEvent(
            dialog_id=dialog_id,
            error=WSErrorDetail(code=code, message=message),
            timestamp=self._ts()
        )
        await self.broadcast(event)

    async def broadcast_message_added(
        self,
        dialog_id: str,
        message: BaseMessage,
    ) -> None:
        """广播新消息添加事件 - 使用 LangChain 格式"""
        event = WSMessageAddedEvent(
            dialog_id=dialog_id,
            message=message_to_dict(message),
            timestamp=self._ts()
        )
        await self.broadcast(event)

    async def broadcast_node_update(
        self,
        dialog_id: str,
        node: str,
        messages: list[dict[str, Any]],
    ) -> None:
        """广播节点更新事件 - updates 模式专用"""
        event = WSNodeUpdateEvent(
            dialog_id=dialog_id,
            node=node,
            messages=messages,
            timestamp=self._ts(),
        )
        await self.broadcast(event)

    @staticmethod
    def _ts() -> int:
        return int(__import__('time').time() * 1000)


ws_broadcaster = WebSocketBroadcaster()
