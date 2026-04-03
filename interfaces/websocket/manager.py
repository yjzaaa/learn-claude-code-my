"""
WebSocket Manager - WebSocket 连接管理

处理 WebSocket 连接、订阅和广播。
使用 LangChain 标准格式进行消息序列化。
"""

import json
from typing import Any, Optional, Set, Union
from fastapi import WebSocket, WebSocketDisconnect

from loguru import logger
from langchain_core.messages import BaseMessage, message_to_dict
from pydantic import BaseModel

from core.models.websocket_models import (
    WSSnapshotEvent,
    WSDialogSnapshot,
    WSDialogMetadata,
    WSStreamDeltaEvent,
    WSDeltaContent,
    WSStreamStartEvent,
    WSStreamEndEvent,
    WSStreamTruncatedEvent,
    WSAckEvent,
    WSErrorEvent,
    WSStatusChangeEvent,
    WSMessageAddedEvent,
    WSNodeUpdateEvent,
    WSErrorDetail,
)


class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self) -> None:
        self._dialog_subs: dict[str, Set[WebSocket]] = dict()
        self._global_subs: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket, dialog_id: Optional[str] = None) -> None:
        """接受连接"""
        await websocket.accept()
        if dialog_id:
            if dialog_id not in self._dialog_subs:
                self._dialog_subs[dialog_id] = set()
            self._dialog_subs[dialog_id].add(websocket)
        else:
            self._global_subs.add(websocket)

    def subscribe_dialog(self, websocket: WebSocket, dialog_id: str) -> None:
        """订阅特定对话"""
        if dialog_id not in self._dialog_subs:
            self._dialog_subs[dialog_id] = set()
        self._dialog_subs[dialog_id].add(websocket)

    def disconnect(self, websocket: WebSocket, dialog_id: Optional[str] = None) -> None:
        """断开连接"""
        if dialog_id and dialog_id in self._dialog_subs:
            self._dialog_subs[dialog_id].discard(websocket)
        else:
            self._global_subs.discard(websocket)

    async def broadcast_to_dialog(self, dialog_id: str, message: str) -> None:
        """广播到特定对话的订阅者"""
        if dialog_id not in self._dialog_subs:
            return
        disconnected: list[WebSocket] = []
        for ws in list(self._dialog_subs[dialog_id]):
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            self._dialog_subs[dialog_id].discard(ws)

    async def broadcast(self, message: str) -> None:
        """广播到所有订阅者"""
        disconnected: list[WebSocket] = []
        for ws in list(self._global_subs):
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            self._global_subs.discard(ws)


class WebSocketBroadcaster:
    """WebSocket 事件广播器 - 使用 LangChain 标准格式"""

    def __init__(self):
        self._conn_mgr = ConnectionManager()

    @property
    def connection_manager(self) -> ConnectionManager:
        return self._conn_mgr

    async def broadcast(self, event: Union[BaseModel, dict], dialog_id: Optional[str] = None) -> None:
        """广播事件到 WebSocket 客户端"""
        if isinstance(event, BaseModel):
            text = event.model_dump_json(by_alias=True)
        else:
            text = json.dumps(event, default=str)
        if dialog_id:
            await self._conn_mgr.broadcast_to_dialog(dialog_id, text)
        else:
            await self._conn_mgr.broadcast(text)

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
        await self.broadcast(event, dialog_id)

    async def broadcast_delta(
        self,
        dialog_id: str,
        message_id: str,
        delta: str,
        is_reasoning: bool = False
    ) -> None:
        """广播流式增量"""
        event = WSStreamDeltaEvent(
            dialog_id=dialog_id,
            message_id=message_id,
            delta=WSDeltaContent(content=delta, reasoning=""),
            timestamp=self._ts()
        )
        await self.broadcast(event, dialog_id)

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
        await self.broadcast(event, dialog_id)

    async def broadcast_stream_start(
        self,
        dialog_id: str,
        message_id: str,
        message: Optional[BaseMessage] = None
    ) -> None:
        """广播流开始 - 使用 LangChain 格式"""
        event = WSStreamStartEvent(
            dialog_id=dialog_id,
            message_id=message_id,
            message=message_to_dict(message) if message else None,
            timestamp=self._ts()
        )
        await self.broadcast(event, dialog_id)

    async def broadcast_stream_end(
        self,
        dialog_id: str,
        message_id: str,
        message: Optional[BaseMessage] = None
    ) -> None:
        """广播流结束 - 使用 LangChain 格式"""
        event = WSStreamEndEvent(
            dialog_id=dialog_id,
            message_id=message_id,
            message=message_to_dict(message) if message else None,
            timestamp=self._ts()
        )
        await self.broadcast(event, dialog_id)

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
        await self.broadcast(event, dialog_id)

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
        await self.broadcast(event, dialog_id)

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
        await self.broadcast(event, dialog_id)

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
        await self.broadcast(event, dialog_id)

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
        await self.broadcast(event, dialog_id)

    @staticmethod
    def _ts() -> int:
        return int(__import__('time').time() * 1000)


ws_broadcaster = WebSocketBroadcaster()
