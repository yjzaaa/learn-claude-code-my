"""
统一数据模型 - 前后端类型对齐

定义与前端 realtime-message.ts 完全对应的 Python 类型
确保字段名、类型、值完全一致
"""

from __future__ import annotations

from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Any, Optional, Dict, List
from datetime import datetime
import uuid
import json


class MessageType(str, Enum):
    """消息类型 - 与前端 RealtimeMessageType 对齐"""
    USER_MESSAGE = "user_message"
    ASSISTANT_TEXT = "assistant_text"
    ASSISTANT_THINKING = "assistant_thinking"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    SYSTEM_EVENT = "system_event"
    STREAM_TOKEN = "stream_token"
    DIALOG_START = "dialog_start"
    DIALOG_END = "dialog_end"


class MessageStatus(str, Enum):
    """消息状态 - 与前端 MessageStatus 对齐"""
    PENDING = "pending"
    STREAMING = "streaming"
    COMPLETED = "completed"
    ERROR = "error"


class AgentType(str, Enum):
    """代理类型 - 与前端 AgentType 对齐"""
    MASTER = "master"
    SQL_EXECUTOR = "sql_executor"
    SCHEMA_EXPLORER = "schema_explorer"
    DATA_VALIDATOR = "data_validator"
    ANALYZER = "analyzer"
    SKILL_LOADER = "skill_loader"
    DEFAULT = "default"


@dataclass
class RealtimeMessage:
    """
    实时消息 - 与前端 RealtimeMessage 接口对齐

    字段映射:
    - id: string
    - type: MessageType
    - content: string
    - status: MessageStatus
    - tool_name?: string
    - tool_input?: Record<string, any>
    - timestamp: string (ISO format)
    - metadata?: Record<string, any>
    - parent_id?: string
    - stream_tokens?: string[]
    - agent_type?: AgentType | string
    """
    id: str
    type: MessageType
    content: str
    status: MessageStatus = MessageStatus.PENDING
    tool_name: Optional[str] = None
    tool_input: Optional[Dict[str, Any]] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
    parent_id: Optional[str] = None
    stream_tokens: List[str] = field(default_factory=list)
    agent_type: Optional[str] = None  # 支持 AgentType 或 "worker:xxx" 格式

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，用于 JSON 序列化"""
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
            "agent_type": self.agent_type,
        }

    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RealtimeMessage":
        """从字典创建实例"""
        return cls(
            id=data["id"],
            type=MessageType(data.get("type", "system_event")),
            content=data.get("content", ""),
            status=MessageStatus(data.get("status", "pending")),
            tool_name=data.get("tool_name"),
            tool_input=data.get("tool_input"),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            metadata=data.get("metadata", {}),
            parent_id=data.get("parent_id"),
            stream_tokens=data.get("stream_tokens", []),
            agent_type=data.get("agent_type"),
        )

    @classmethod
    def create(
        cls,
        msg_type: MessageType,
        content: str = "",
        status: MessageStatus = MessageStatus.PENDING,
        agent_type: Optional[str] = None,
        parent_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        tool_input: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "RealtimeMessage":
        """工厂方法：创建新消息"""
        return cls(
            id=str(uuid.uuid4()),
            type=msg_type,
            content=content,
            status=status,
            agent_type=agent_type,
            parent_id=parent_id,
            tool_name=tool_name,
            tool_input=tool_input,
            metadata=metadata or {},
        )

    def update_content(self, content: str) -> "RealtimeMessage":
        """更新内容"""
        self.content = content
        return self

    def append_token(self, token: str) -> "RealtimeMessage":
        """追加流式 token"""
        self.stream_tokens.append(token)
        self.content = "".join(self.stream_tokens)
        return self

    def complete(self, final_content: Optional[str] = None) -> "RealtimeMessage":
        """标记为完成"""
        self.status = MessageStatus.COMPLETED
        if final_content is not None:
            self.content = final_content
        return self

    def fail(self, error_message: str = "") -> "RealtimeMessage":
        """标记为错误"""
        self.status = MessageStatus.ERROR
        if error_message:
            self.content = error_message
        return self


@dataclass
class DialogSession:
    """
    对话会话 - 与前端 DialogSession 接口对齐

    字段映射:
    - id: string
    - title: string
    - messages: RealtimeMessage[]
    - status: MessageStatus
    - created_at: string
    - updated_at: string
    """
    id: str
    title: str
    messages: List[RealtimeMessage] = field(default_factory=list)
    status: MessageStatus = MessageStatus.PENDING
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def add_message(self, message: RealtimeMessage) -> None:
        """添加消息并更新时间戳"""
        self.messages.append(message)
        self.updated_at = datetime.now().isoformat()

    def get_message(self, message_id: str) -> Optional[RealtimeMessage]:
        """根据 ID 获取消息"""
        for msg in self.messages:
            if msg.id == message_id:
                return msg
        return None

    def update_message(self, message_id: str, **updates: Any) -> bool:
        """更新消息字段"""
        msg = self.get_message(message_id)
        if msg:
            for key, value in updates.items():
                if hasattr(msg, key):
                    setattr(msg, key, value)
            self.updated_at = datetime.now().isoformat()
            return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "title": self.title,
            "messages": [m.to_dict() for m in self.messages],
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class WebSocketEvent:
    """
    WebSocket 事件基类

    前端通过 type 字段区分事件类型
    """
    type: str
    dialog_id: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "dialog_id": self.dialog_id,
            "timestamp": self.timestamp,
        }


@dataclass
class MessageAddedEvent(WebSocketEvent):
    """消息添加事件 - 对应前端 MessageAddedEvent"""
    message: RealtimeMessage = field(default_factory=lambda: RealtimeMessage.create(MessageType.SYSTEM_EVENT))

    def __post_init__(self):
        if not self.type:
            self.type = "message_added"

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base["message"] = self.message.to_dict()
        return base


@dataclass
class MessageUpdatedEvent(WebSocketEvent):
    """消息更新事件 - 对应前端 MessageUpdatedEvent"""
    message: RealtimeMessage = field(default_factory=lambda: RealtimeMessage.create(MessageType.SYSTEM_EVENT))

    def __post_init__(self):
        if not self.type:
            self.type = "message_updated"

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base["message"] = self.message.to_dict()
        return base


@dataclass
class StreamTokenEvent(WebSocketEvent):
    """流式 token 事件 - 对应前端 StreamTokenMessage"""
    message_id: str = ""
    token: str = ""
    current_content: str = ""

    def __post_init__(self):
        if not self.type:
            self.type = "stream_token"

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "message_id": self.message_id,
            "token": self.token,
            "current_content": self.current_content,
        })
        return base


class AgentState:
    """
    Agent 运行状态

    封装 is_running, stop_requested 等状态管理
    """
    def __init__(self):
        self._is_running: bool = False
        self._stop_requested: bool = False
        self._current_dialog_id: Optional[str] = None
        self._current_agent_type: Optional[str] = None

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def stop_requested(self) -> bool:
        return self._stop_requested

    @property
    def current_dialog_id(self) -> Optional[str]:
        return self._current_dialog_id

    @property
    def current_agent_type(self) -> Optional[str]:
        return self._current_agent_type

    def start(self, dialog_id: str, agent_type: str = "default") -> None:
        """开始运行"""
        self._is_running = True
        self._stop_requested = False
        self._current_dialog_id = dialog_id
        self._current_agent_type = agent_type

    def stop(self) -> None:
        """请求停止"""
        self._stop_requested = True

    def reset(self) -> None:
        """重置状态"""
        self._is_running = False
        self._stop_requested = False
        self._current_dialog_id = None
        self._current_agent_type = None

    def check_should_stop(self) -> bool:
        """检查是否应该停止"""
        return self._stop_requested


__all__ = [
    "MessageType",
    "MessageStatus",
    "AgentType",
    "RealtimeMessage",
    "DialogSession",
    "WebSocketEvent",
    "MessageAddedEvent",
    "MessageUpdatedEvent",
    "StreamTokenEvent",
    "AgentState",
]
