"""
事件管理器 - 简化版，直接使用 OpenAI 格式

数据流:
    Agent -> ChatMessage (OpenAI格式) -> WebSocket -> 前端
"""

from loguru import logger
from typing import Callable, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
import json

from pydantic import BaseModel

# OpenAI 风格类型
from ..models.openai_types import ChatMessage, ChatEvent


class PushTypeMap(BaseModel):
    """推送类型映射"""
    message: bool = True
    system: bool = True
    stream_token: bool = True
    tool_call: bool = True
    tool_result: bool = True
    thinking: bool = True


class DialogSessionData(BaseModel):
    """对话框会话数据模型"""
    id: str
    title: str
    messages: list[dict[str, Any]]
    created_at: str
    updated_at: str


class ChatEventMessageData(BaseModel):
    """聊天事件消息数据"""
    type: str
    dialog_id: str
    message: dict[str, Any]
    timestamp: float


@dataclass
class DialogSession:
    """对话框会话 - 简化版"""
    id: str
    title: str
    messages: list[ChatMessage] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def add_message(self, message: ChatMessage):
        self.messages.append(message)
        self.updated_at = datetime.now().isoformat()

    def to_dict(self) -> dict[str, Any]:
        return DialogSessionData(
            id=self.id,
            title=self.title,
            messages=[m.model_dump() for m in self.messages],
            created_at=self.created_at,
            updated_at=self.updated_at,
        ).model_dump()


class EventManager:
    """事件管理器 - 简化版，直接使用 OpenAI 格式"""

    _instance: Optional['EventManager'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._subscribers: dict[str, list[Callable]] = {}
        self._dialogs: dict[str, DialogSession] = {}
        self._websocket_clients: list[Any] = []
        self._initialized = True

    # ========== 订阅/发布 ==========

    def subscribe(self, event_type: str, callback: Callable) -> Callable:
        """订阅事件"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

        def unsubscribe():
            self._subscribers[event_type].remove(callback)

        return unsubscribe

    def emit(self, event_type: str, data: Any):
        """发布事件"""
        if event_type in self._subscribers:
            for callback in self._subscribers[event_type]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        asyncio.create_task(callback(data))
                    else:
                        callback(data)
                except Exception as e:
                    logger.warning(f"Event callback error: {e}")

    # ========== WebSocket 客户端管理 ==========

    def add_websocket_client(self, client: Any):
        """添加 WebSocket 客户端"""
        if client not in self._websocket_clients:
            self._websocket_clients.append(client)

    def remove_websocket_client(self, client: Any):
        """移除 WebSocket 客户端"""
        if client in self._websocket_clients:
            self._websocket_clients.remove(client)

    async def broadcast_to_clients(self, message: dict[str, Any]):
        """广播消息到所有 WebSocket 客户端"""
        if not self._websocket_clients:
            return

        dead_clients = []
        for client in self._websocket_clients:
            try:
                await client.send(json.dumps(message, ensure_ascii=False))
            except Exception as e:
                logger.error(f"Failed to send to client: {e}")
                dead_clients.append(client)

        # 清理断开的客户端
        for client in dead_clients:
            self.remove_websocket_client(client)

    # ========== OpenAI 风格消息处理 ==========

    async def send_chat_event(self, event: ChatEvent):
        """
        发送 ChatEvent 到前端

        这是主要的消息发送接口，直接使用 OpenAI 格式。
        """
        message_data = ChatEventMessageData(
            type=event.type,
            dialog_id=event.dialog_id,
            message=event.message.model_dump(),
            timestamp=event.timestamp,
        ).model_dump()

        # 添加到对话框历史
        dialog = self._dialogs.get(event.dialog_id)
        if dialog:
            dialog.add_message(event.message)

        # 广播到 WebSocket 客户端
        await self.broadcast_to_clients(message_data)

    def add_chat_message(self, dialog_id: str, message: ChatMessage):
        """添加 OpenAI 风格消息到对话框"""
        dialog = self._dialogs.get(dialog_id)
        if dialog:
            dialog.add_message(message)

    # ========== 对话框管理 ==========

    def create_dialog(self, dialog_id: str, title: str = "New Dialog") -> DialogSession:
        """创建新对话框"""
        dialog = DialogSession(id=dialog_id, title=title)
        self._dialogs[dialog_id] = dialog
        return dialog

    def get_dialog(self, dialog_id: str) -> Optional[DialogSession]:
        """获取对话框"""
        return self._dialogs.get(dialog_id)

    def get_all_dialogs(self) -> list[DialogSession]:
        """获取所有对话框"""
        return list(self._dialogs.values())

    def to_client_dialog_dict(self, dialog: DialogSession) -> dict[str, Any]:
        """将对话框转换为客户端格式"""
        if not dialog:
            return {}
        return {
            "id": dialog.id,
            "title": dialog.title,
            "messages": [m.model_dump() for m in dialog.messages],
            "created_at": dialog.created_at,
            "updated_at": dialog.updated_at,
        }

    # ========== 推送类型控制 (兼容性) ==========

    def get_push_type_map(self) -> PushTypeMap:
        """获取推送类型映射 (兼容性方法)"""
        # 默认所有类型都推送
        return PushTypeMap()

    def update_push_type_map(self, updates: dict[str, bool]) -> PushTypeMap:
        """更新推送类型映射 (兼容性方法)"""
        current = self.get_push_type_map()
        for key, value in updates.items():
            if hasattr(current, key):
                setattr(current, key, bool(value))
        return current


# 全局事件管理器实例
event_manager = EventManager()
