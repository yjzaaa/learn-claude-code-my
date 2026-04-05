"""
WebSocket Server - WebSocket 服务器

处理 WebSocket 连接和消息转发。
"""

import json
from typing import Any, Dict, Optional, Set

from backend.infrastructure.logging import get_logger
from fastapi import WebSocket, WebSocketDisconnect

from backend.application.engine import AgentEngine
from backend.domain.models.shared.types import WSStreamDeltaMessage, WSDialogCreatedMessage, WSEventMessage
from backend.infrastructure.event_bus import EventBus
from backend.domain.models.events import (
    DialogCreated, MessageReceived, StreamDelta,
    MessageCompleted, ToolCallStarted, ToolCallCompleted
)

logger = get_logger(__name__)


class ConnectionManager:
    """WebSocket 连接管理器"""
    
    def __init__(self):
        # 对话订阅: dialog_id -> set of websockets
        self._dialog_subs: Dict[str, Set[WebSocket]] = {}
        # 全局订阅
        self._global_subs: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket, dialog_id: Optional[str] = None):
        """接受连接"""
        await websocket.accept()
        
        if dialog_id:
            if dialog_id not in self._dialog_subs:
                self._dialog_subs[dialog_id] = set()
            self._dialog_subs[dialog_id].add(websocket)
        else:
            self._global_subs.add(websocket)
    
    def disconnect(self, websocket: WebSocket, dialog_id: Optional[str] = None):
        """断开连接"""
        if dialog_id and dialog_id in self._dialog_subs:
            self._dialog_subs[dialog_id].discard(websocket)
        else:
            self._global_subs.discard(websocket)
    
    async def broadcast_to_dialog(self, dialog_id: str, message: str):
        """广播到特定对话的订阅者"""
        if dialog_id not in self._dialog_subs:
            return
        
        disconnected = []
        for ws in self._dialog_subs[dialog_id]:
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.append(ws)
        
        # 清理断开连接
        for ws in disconnected:
            self._dialog_subs[dialog_id].discard(ws)
    
    async def broadcast(self, message: str):
        """广播到所有订阅者"""
        disconnected = []
        
        for ws in self._global_subs:
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.append(ws)
        
        for ws in disconnected:
            self._global_subs.discard(ws)


class WebSocketServer:
    """WebSocket 服务器"""
    
    def __init__(self, engine: AgentEngine):
        self._engine = engine
        self._conn_mgr = ConnectionManager()
        self._unsubscribe = None
    
    async def start(self):
        """启动 WebSocket 服务器"""
        # 订阅引擎事件
        self._unsubscribe = self._engine.subscribe(
            self._on_event,
            event_types=[
                'DialogCreated',
                'MessageReceived',
                'StreamDelta',
                'MessageCompleted',
                'ToolCallStarted',
                'ToolCallCompleted',
                'ErrorOccurred'
            ]
        )
        logger.info("[WebSocketServer] Started")
    
    async def stop(self):
        """停止 WebSocket 服务器"""
        if self._unsubscribe:
            self._unsubscribe()
        logger.info("[WebSocketServer] Stopped")
    
    async def handle_client(self, websocket: WebSocket, dialog_id: Optional[str] = None):
        """
        处理客户端连接
        
        Args:
            websocket: WebSocket 连接
            dialog_id: 可选的对话 ID (订阅特定对话)
        """
        await self._conn_mgr.connect(websocket, dialog_id)
        
        try:
            while True:
                # 接收消息
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # 处理消息
                await self._handle_message(websocket, message, dialog_id)
                
        except WebSocketDisconnect:
            self._conn_mgr.disconnect(websocket, dialog_id)
            logger.info(f"[WebSocketServer] Client disconnected")
    
    async def _handle_message(
        self,
        websocket: WebSocket,
        message: Dict[str, Any],
        dialog_id: Optional[str] = None
    ):
        """处理客户端消息"""
        msg_type = message.get("type")

        if msg_type == "send_message":
            # 发送消息
            target_dialog = message.get("dialog_id") or dialog_id
            content = message.get("content", "")

            if target_dialog:
                async for chunk in self._engine.send_message(target_dialog, content):
                    await websocket.send_text(json.dumps(WSStreamDeltaMessage(
                        type="stream_delta",
                        dialog_id=target_dialog,
                        content=chunk,
                    )))

        elif msg_type == "create_dialog":
            # 创建对话
            user_input = message.get("user_input", "")
            new_dialog_id = await self._engine.create_dialog(user_input)

            await websocket.send_text(json.dumps(WSDialogCreatedMessage(
                type="dialog_created",
                dialog_id=new_dialog_id,
            )))
        
        elif msg_type == "subscribe":
            # 订阅特定对话
            sub_dialog_id = message.get("dialog_id")
            if sub_dialog_id:
                await self._conn_mgr.connect(websocket, sub_dialog_id)
    
    async def _on_event(self, event) -> None:
        """处理引擎事件并转发到 WebSocket 客户端"""
        # 序列化事件
        message = WSEventMessage(
            type=event.event_type,
            data=event.to_dict(),
        )
        
        json_msg = json.dumps(message)
        
        # 广播到特定对话或全局
        dialog_id: Optional[str] = getattr(event, 'dialog_id', None)
        if dialog_id:
            await self._conn_mgr.broadcast_to_dialog(dialog_id, json_msg)
        else:
            await self._conn_mgr.broadcast(json_msg)
