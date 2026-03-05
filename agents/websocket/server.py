"""
FastAPI WebSocket服务器

提供基于FastAPI的WebSocket实时通信服务
"""

from typing import Dict, List, Optional, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import json
import asyncio
import uuid
from datetime import datetime

from .event_manager import (
    event_manager,
    RealTimeMessage,
    DialogSession,
    MessageType,
    MessageStatus,
)


class ConnectionManager:
    """WebSocket连接管理器"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.dialog_subscriptions: Dict[str, List[str]] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        event_manager.add_websocket_client(self._create_client_wrapper(client_id))
        print(f"Client {client_id} connected")

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        # 清理订阅
        for dialog_id, clients in self.dialog_subscriptions.items():
            if client_id in clients:
                clients.remove(client_id)
        event_manager.remove_websocket_client(self._create_client_wrapper(client_id))
        print(f"Client {client_id} disconnected")

    def _create_client_wrapper(self, client_id: str):
        """创建客户端包装器用于事件管理器"""
        class ClientWrapper:
            def __init__(self, manager: 'ConnectionManager', cid: str):
                self.manager = manager
                self.client_id = cid

            async def send(self, message: str):
                if self.client_id in self.manager.active_connections:
                    await self.manager.active_connections[self.client_id].send_text(message)

        return ClientWrapper(self, client_id)

    async def send_personal_message(self, message: Dict[str, Any], client_id: str):
        """发送个人消息"""
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_text(json.dumps(message, ensure_ascii=False))

    async def broadcast(self, message: Dict[str, Any]):
        """广播消息到所有客户端"""
        disconnected = []
        for client_id, connection in self.active_connections.items():
            try:
                await connection.send_text(json.dumps(message, ensure_ascii=False))
            except Exception:
                disconnected.append(client_id)

        # 清理断开的连接
        for client_id in disconnected:
            self.disconnect(client_id)

    async def broadcast_to_dialog(self, dialog_id: str, message: Dict[str, Any]):
        """广播消息到订阅特定对话框的客户端"""
        clients = self.dialog_subscriptions.get(dialog_id, [])
        print(f"[ConnectionManager] Broadcasting to dialog {dialog_id}, clients: {clients}")
        disconnected = []

        for client_id in clients:
            if client_id in self.active_connections:
                try:
                    await self.active_connections[client_id].send_text(
                        json.dumps(message, ensure_ascii=False)
                    )
                    print(f"[ConnectionManager] Message sent to client {client_id}")
                except Exception as e:
                    print(f"[ConnectionManager] Failed to send to client {client_id}: {e}")
                    disconnected.append(client_id)
            else:
                print(f"[ConnectionManager] Client {client_id} not in active connections")
                disconnected.append(client_id)

        # 清理断开的连接
        for client_id in disconnected:
            if client_id in clients:
                clients.remove(client_id)

    def subscribe_to_dialog(self, client_id: str, dialog_id: str):
        """订阅对话框"""
        print(f"[ConnectionManager] Client {client_id} subscribing to dialog {dialog_id}")
        if dialog_id not in self.dialog_subscriptions:
            self.dialog_subscriptions[dialog_id] = []
        if client_id not in self.dialog_subscriptions[dialog_id]:
            self.dialog_subscriptions[dialog_id].append(client_id)
            print(f"[ConnectionManager] Subscription added. Current subs for {dialog_id}: {self.dialog_subscriptions[dialog_id]}")
        else:
            print(f"[ConnectionManager] Client {client_id} already subscribed to {dialog_id}")

    def unsubscribe_from_dialog(self, client_id: str, dialog_id: str):
        """取消订阅对话框"""
        if dialog_id in self.dialog_subscriptions:
            if client_id in self.dialog_subscriptions[dialog_id]:
                self.dialog_subscriptions[dialog_id].remove(client_id)


# 全局连接管理器
connection_manager = ConnectionManager()


class MessageHandler:
    """消息处理器 - 处理WebSocket消息"""

    @staticmethod
    async def handle_message(websocket: WebSocket, client_id: str, message: Dict[str, Any]):
        """处理收到的消息"""
        msg_type = message.get("type")

        handlers = {
            "subscribe_dialog": MessageHandler._handle_subscribe_dialog,
            "unsubscribe_dialog": MessageHandler._handle_unsubscribe_dialog,
            "user_input": MessageHandler._handle_user_input,
            "ping": MessageHandler._handle_ping,
        }

        handler = handlers.get(msg_type)
        if handler:
            await handler(websocket, client_id, message)
        else:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": f"Unknown message type: {msg_type}"
            }))

    @staticmethod
    async def _handle_subscribe_dialog(websocket: WebSocket, client_id: str, message: Dict[str, Any]):
        """处理订阅对话框请求"""
        dialog_id = message.get("dialog_id")
        if dialog_id:
            connection_manager.subscribe_to_dialog(client_id, dialog_id)
            dialog = event_manager.get_dialog(dialog_id)
            await websocket.send_text(json.dumps({
                "type": "dialog_subscribed",
                "dialog_id": dialog_id,
                "dialog": dialog.to_dict() if dialog else None,
            }))

    @staticmethod
    async def _handle_unsubscribe_dialog(websocket: WebSocket, client_id: str, message: Dict[str, Any]):
        """处理取消订阅对话框请求"""
        dialog_id = message.get("dialog_id")
        if dialog_id:
            connection_manager.unsubscribe_from_dialog(client_id, dialog_id)
            await websocket.send_text(json.dumps({
                "type": "dialog_unsubscribed",
                "dialog_id": dialog_id,
            }))

    @staticmethod
    async def _handle_user_input(websocket: WebSocket, client_id: str, message: Dict[str, Any]):
        """处理用户输入"""
        dialog_id = message.get("dialog_id")
        content = message.get("content")

        if dialog_id and content:
            # 创建用户消息
            user_message = RealTimeMessage(
                id=str(uuid.uuid4()),
                type=MessageType.USER_MESSAGE,
                content=content,
                status=MessageStatus.COMPLETED,
            )

            event_manager.add_message_to_dialog(dialog_id, user_message)

            # 触发用户输入事件
            event_manager.emit("user_input", {
                "dialog_id": dialog_id,
                "client_id": client_id,
                "content": content,
                "message_id": user_message.id,
            })

    @staticmethod
    async def _handle_ping(websocket: WebSocket, client_id: str, message: Dict[str, Any]):
        """处理ping请求"""
        await websocket.send_text(json.dumps({"type": "pong"}))


def create_websocket_app() -> FastAPI:
    """创建FastAPI应用"""
    app = FastAPI(title="Agent WebSocket Server")

    # CORS配置
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.websocket("/ws/{client_id}")
    async def websocket_endpoint(websocket: WebSocket, client_id: str):
        await connection_manager.connect(websocket, client_id)
        try:
            while True:
                data = await websocket.receive_text()
                try:
                    message = json.loads(data)
                    await MessageHandler.handle_message(websocket, client_id, message)
                except json.JSONDecodeError:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "Invalid JSON"
                    }))
        except WebSocketDisconnect:
            connection_manager.disconnect(client_id)

    @app.get("/api/dialogs")
    async def get_dialogs():
        """获取所有对话框"""
        dialogs = event_manager.get_all_dialogs()
        return {
            "dialogs": [d.to_dict() for d in dialogs]
        }

    @app.post("/api/dialogs")
    async def create_dialog(title: str = "New Dialog"):
        """创建新对话框"""
        dialog_id = str(uuid.uuid4())
        dialog = event_manager.create_dialog(dialog_id, title)

        # 广播新对话框创建
        await connection_manager.broadcast({
            "type": "dialog_created",
            "dialog": dialog.to_dict()
        })

        return dialog.to_dict()

    @app.get("/api/dialogs/{dialog_id}")
    async def get_dialog(dialog_id: str):
        """获取特定对话框"""
        dialog = event_manager.get_dialog(dialog_id)
        if dialog:
            return dialog.to_dict()
        return {"error": "Dialog not found"}, 404

    @app.delete("/api/dialogs/{dialog_id}")
    async def delete_dialog(dialog_id: str):
        """删除对话框"""
        # 这里可以实现删除逻辑
        await connection_manager.broadcast({
            "type": "dialog_deleted",
            "dialog_id": dialog_id
        })
        return {"status": "deleted"}

    return app


# 创建应用实例
websocket_app = create_websocket_app()


async def start_websocket_server(host: str = "0.0.0.0", port: int = 8001):
    """启动WebSocket服务器"""
    import uvicorn
    config = uvicorn.Config(websocket_app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


# ========== Agent集成辅助函数 ==========

class AgentMessageBridge:
    """
    Agent消息桥接器

    用于将Agent循环中的消息发送到WebSocket
    """

    def __init__(self, dialog_id: str):
        self.dialog_id = dialog_id
        self.current_message_id: Optional[str] = None

    async def send_user_message(self, content: str) -> RealTimeMessage:
        """发送用户消息"""
        message = RealTimeMessage(
            id=str(uuid.uuid4()),
            type=MessageType.USER_MESSAGE,
            content=content,
            status=MessageStatus.COMPLETED,
        )
        event_manager.add_message_to_dialog(self.dialog_id, message)
        return message

    async def start_assistant_response(self) -> RealTimeMessage:
        """开始助手响应"""
        message = RealTimeMessage(
            id=str(uuid.uuid4()),
            type=MessageType.ASSISTANT_TEXT,
            content="",
            status=MessageStatus.STREAMING,
        )
        self.current_message_id = message.id
        event_manager.add_message_to_dialog(self.dialog_id, message)
        return message

    async def send_stream_token(self, token: str):
        """发送流式token"""
        if self.current_message_id:
            dialog = event_manager.get_dialog(self.dialog_id)
            if dialog:
                for msg in dialog.messages:
                    if msg.id == self.current_message_id:
                        msg.stream_tokens.append(token)
                        msg.content = "".join(msg.stream_tokens)
                        # 广播流式更新
                        await connection_manager.broadcast_to_dialog(
                            self.dialog_id,
                            {
                                "type": "stream_token",
                                "dialog_id": self.dialog_id,
                                "message_id": self.current_message_id,
                                "token": token,
                                "current_content": msg.content,
                            }
                        )
                        # 同时触发消息更新事件，确保消息状态同步
                        event_manager.update_message_in_dialog(
                            self.dialog_id,
                            self.current_message_id,
                            {"content": msg.content, "stream_tokens": msg.stream_tokens}
                        )
                        break

    async def send_thinking(self, content: str):
        """发送思考过程"""
        message = RealTimeMessage(
            id=str(uuid.uuid4()),
            type=MessageType.ASSISTANT_THINKING,
            content=content,
            status=MessageStatus.COMPLETED,
            parent_id=self.current_message_id,
        )
        event_manager.add_message_to_dialog(self.dialog_id, message)
        return message

    async def send_tool_call(self, tool_name: str, tool_input: Dict[str, Any]) -> RealTimeMessage:
        """发送工具调用"""
        message = RealTimeMessage(
            id=str(uuid.uuid4()),
            type=MessageType.TOOL_CALL,
            content=f"调用工具: {tool_name}",
            tool_name=tool_name,
            tool_input=tool_input,
            status=MessageStatus.PENDING,
            parent_id=self.current_message_id,
        )
        event_manager.add_message_to_dialog(self.dialog_id, message)
        return message

    async def send_tool_result(self, tool_call_id: str, result: str):
        """发送工具结果"""
        message = RealTimeMessage(
            id=str(uuid.uuid4()),
            type=MessageType.TOOL_RESULT,
            content=result,
            status=MessageStatus.COMPLETED,
            parent_id=tool_call_id,
        )
        event_manager.add_message_to_dialog(self.dialog_id, message)

        # 更新工具调用状态
        event_manager.update_message_in_dialog(
            self.dialog_id,
            tool_call_id,
            {"status": MessageStatus.COMPLETED}
        )
        return message

    async def complete_assistant_response(self, final_content: Optional[str] = None):
        """完成助手响应"""
        if self.current_message_id:
            updates = {"status": MessageStatus.COMPLETED}
            if final_content:
                updates["content"] = final_content
            event_manager.update_message_in_dialog(
                self.dialog_id,
                self.current_message_id,
                updates
            )
            self.current_message_id = None

    async def send_system_event(self, content: str, metadata: Optional[Dict] = None):
        """发送系统事件"""
        message = RealTimeMessage(
            id=str(uuid.uuid4()),
            type=MessageType.SYSTEM_EVENT,
            content=content,
            status=MessageStatus.COMPLETED,
            metadata=metadata or {},
        )
        event_manager.add_message_to_dialog(self.dialog_id, message)
        return message
