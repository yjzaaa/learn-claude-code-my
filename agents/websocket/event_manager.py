"""
事件管理器 - 实现观察者模式

提供发布订阅机制，解耦消息产生和消费
"""

from typing import Callable, Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
from enum import Enum
import json


class MessageType(Enum):
    """消息类型枚举"""
    USER_MESSAGE = "user_message"
    ASSISTANT_TEXT = "assistant_text"
    ASSISTANT_THINKING = "assistant_thinking"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    SYSTEM_EVENT = "system_event"
    STREAM_TOKEN = "stream_token"
    DIALOG_START = "dialog_start"
    DIALOG_END = "dialog_end"


class MessageStatus(Enum):
    """消息状态枚举"""
    PENDING = "pending"
    STREAMING = "streaming"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class RealTimeMessage:
    """实时消息数据结构"""
    id: str
    type: MessageType
    content: str
    status: MessageStatus = MessageStatus.PENDING
    tool_name: Optional[str] = None
    tool_input: Optional[Dict] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
    parent_id: Optional[str] = None
    stream_tokens: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "content": self.content,
            "status": self.status.value,
            "tool_name": self.tool_name,
            "tool_input": self.tool_input,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
            "parent_id": self.parent_id,
            "stream_tokens": self.stream_tokens,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


@dataclass
class DialogSession:
    """对话框会话"""
    id: str
    title: str
    messages: List[RealTimeMessage] = field(default_factory=list)
    status: MessageStatus = MessageStatus.PENDING
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def add_message(self, message: RealTimeMessage):
        self.messages.append(message)
        self.updated_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "messages": [m.to_dict() for m in self.messages],
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class EventManager:
    """
    事件管理器 - 实现发布订阅模式

    单例模式确保全局唯一实例
    """
    _instance: Optional['EventManager'] = None
    _lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._subscribers: Dict[str, List[Callable]] = {}
        self._dialogs: Dict[str, DialogSession] = {}
        self._websocket_clients: List[Any] = []
        self._initialized = True

    # ========== 订阅/发布 ==========

    def subscribe(self, event_type: str, callback: Callable) -> Callable:
        """
        订阅事件

        Args:
            event_type: 事件类型
            callback: 回调函数

        Returns:
            取消订阅函数
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

        def unsubscribe():
            self._subscribers[event_type].remove(callback)

        return unsubscribe

    def emit(self, event_type: str, data: Any):
        """
        发布事件

        Args:
            event_type: 事件类型
            data: 事件数据
        """
        if event_type in self._subscribers:
            for callback in self._subscribers[event_type]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        asyncio.create_task(callback(data))
                    else:
                        callback(data)
                except Exception as e:
                    print(f"Event callback error: {e}")

    # ========== WebSocket客户端管理 ==========

    def add_websocket_client(self, client: Any):
        """添加WebSocket客户端"""
        if client not in self._websocket_clients:
            self._websocket_clients.append(client)

    def remove_websocket_client(self, client: Any):
        """移除WebSocket客户端"""
        if client in self._websocket_clients:
            self._websocket_clients.remove(client)

    async def broadcast_to_clients(self, message: Dict[str, Any]):
        """广播消息到所有WebSocket客户端"""
        if not self._websocket_clients:
            return

        dead_clients = []
        for client in self._websocket_clients:
            try:
                import loguru as logger
                logger.debug(f"[EventManager] Broadcasting message to client: {message}")
                await client.send(json.dumps(message, ensure_ascii=False))
            except Exception:
                dead_clients.append(client)

        # 清理断开的客户端
        for client in dead_clients:
            self.remove_websocket_client(client)

    # ========== 对话框管理 ==========

    def create_dialog(self, dialog_id: str, title: str = "New Dialog") -> DialogSession:
        """创建新对话框"""
        dialog = DialogSession(id=dialog_id, title=title)
        self._dialogs[dialog_id] = dialog
        return dialog

    def get_dialog(self, dialog_id: str) -> Optional[DialogSession]:
        """获取对话框"""
        return self._dialogs.get(dialog_id)

    def add_message_to_dialog(self, dialog_id: str, message: RealTimeMessage):
        """添加消息到对话框"""
        dialog = self._dialogs.get(dialog_id)
        if dialog:
            dialog.add_message(message)
            # 广播消息更新（使用 create_task 或调度到事件循环）
            message_data = {
                "type": "message_added",
                "dialog_id": dialog_id,
                "message": message.to_dict()
            }
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.broadcast_to_clients(message_data))
                    # 同时广播给订阅该对话框的客户端
                    from .server import connection_manager
                    loop.create_task(connection_manager.broadcast_to_dialog(dialog_id, message_data))
                else:
                    # 如果事件循环不在运行，存储待发送消息
                    pass
            except RuntimeError:
                # 没有事件循环，忽略广播
                pass
            except Exception as e:
                print(f"[EventManager] Error broadcasting message: {e}")

    def update_message_in_dialog(self, dialog_id: str, message_id: str, updates: Dict[str, Any]):
        """更新对话框中的消息"""
        dialog = self._dialogs.get(dialog_id)
        if dialog:
            for msg in dialog.messages:
                if msg.id == message_id:
                    for key, value in updates.items():
                        if hasattr(msg, key):
                            setattr(msg, key, value)
                    # 广播消息更新
                    message_data = {
                        "type": "message_updated",
                        "dialog_id": dialog_id,
                        "message": msg.to_dict()
                    }
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            loop.create_task(self.broadcast_to_clients(message_data))
                            # 同时广播给订阅该对话框的客户端
                            from .server import connection_manager
                            loop.create_task(connection_manager.broadcast_to_dialog(dialog_id, message_data))
                    except RuntimeError:
                        pass
                    except Exception as e:
                        print(f"[EventManager] Error broadcasting message update: {e}")
                    break

    def get_all_dialogs(self) -> List[DialogSession]:
        """获取所有对话框"""
        return list(self._dialogs.values())


# 全局事件管理器实例
event_manager = EventManager()
